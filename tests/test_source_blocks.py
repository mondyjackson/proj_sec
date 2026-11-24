from tests.helpers import is_remediation_prompt
import json
from pathlib import Path
import tempfile
import unittest

from proj_sec.common import load_kdes
from proj_sec.extractor import _source_blocks, extract_kdes, validate_documents
from proj_sec.pdfio import Section
from tests.helpers import TEXT, make_pdf


def response_for_block(prompt):
    if 'Source excerpts:\n' in prompt:
        return '1'
    name = prompt.split('Element name: ')[-1].splitlines()[0]
    source = prompt.split('<source>\n', 1)[1].split('\n</source>', 1)[0]
    return json.dumps({'name': name, 'requirements': [source.split(':\n', 1)[1]]})


class SourceBlockTests(unittest.TestCase):
    def test_description_and_remediation_are_merged_into_one_element_per_style(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            pdf = root / 'cis.pdf'
            make_pdf(pdf, TEXT)
            calls = []
            def generate(prompt):
                calls.append(prompt)
                return response_for_block(prompt)
            results = extract_kdes(validate_documents(pdf, pdf), root / 'out', generate,
                                   model_identity='controlled-test-double', section_limit=1)
            self.assertEqual(len(calls), 6)
            for left, right in results.values():
                elements = load_kdes(left)
                self.assertEqual(len(elements), 1)
                self.assertEqual(elements, load_kdes(right))
                self.assertEqual(set(elements['element1']['requirements']),
                                 {'Containers should run as a non-root user.', 'Set USER app.'})
            log = (root / 'out/llm-output.txt').read_text()
            self.assertIn(':4.1/Description', log)
            self.assertIn(':4.1/Remediation', log)

    def test_failed_remediation_does_not_complete_yaml_and_resumes_description_cache(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            pdf = root / 'cis.pdf'
            make_pdf(pdf, TEXT)
            calls = []
            fail_remediation = True
            def generate(prompt):
                calls.append(prompt)
                if fail_remediation and is_remediation_prompt(prompt):
                    return 'not JSON'
                return response_for_block(prompt)
            documents = validate_documents(pdf, pdf)
            options = {'prompt_types': ('zero-shot',), 'section_limit': 1,
                       'retries': 0, 'cache_dir': root / 'cache', 'model_identity': 'same-model'}
            with self.assertRaisesRegex(ValueError, '4.1/Remediation'):
                extract_kdes(documents, root / 'out', generate, **options)
            self.assertFalse(list((root / 'out').rglob('*-kdes.yaml')))
            self.assertEqual(len(list((root / 'cache').glob('*.json'))), 1)
            fail_remediation = False
            result = extract_kdes(documents, root / 'out', generate, **options)
            self.assertEqual(len(calls), 3)
            self.assertTrue(is_remediation_prompt(calls[-1]))
            self.assertEqual(len(load_kdes(result['zero-shot'][0])), 1)

    def test_identical_prompts_reuse_cache_across_different_pdf_hashes(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            first, second = root / 'first.pdf', root / 'second.pdf'
            make_pdf(first, TEXT)
            make_pdf(second, TEXT.replace('Page 1', 'Page 2'))
            first_docs = validate_documents(first, first)
            second_docs = validate_documents(second, second)
            self.assertNotEqual(first_docs[0].sha256, second_docs[0].sha256)
            calls = []
            def generate(prompt):
                calls.append(prompt)
                return response_for_block(prompt)
            options = {'prompt_types': ('zero-shot',), 'cache_dir': root / 'cache', 'model_identity': 'same-model'}
            extract_kdes(first_docs, root / 'one', generate, **options)
            self.assertEqual(len(calls), 4)
            extract_kdes(second_docs, root / 'two', generate, **options)
            self.assertEqual(len(calls), 4)
            self.assertIn('second.pdf:4.1/Description', (root / 'two/llm-output.txt').read_text())

    def test_excerpt_from_the_other_block_is_rejected(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            pdf = root / 'cis.pdf'
            make_pdf(pdf, TEXT)
            def wrong_block(prompt):
                name = prompt.split('Element name: ')[-1].splitlines()[0]
                return json.dumps({'name': name, 'requirements': ['Set USER app.']})
            with self.assertRaisesRegex(ValueError, 'matching source excerpt'):
                extract_kdes(validate_documents(pdf, pdf), root / 'out', wrong_block,
                             section_limit=1, prompt_types=('zero-shot',), retries=0)

    def test_single_field_and_unlabeled_source_are_retained(self):
        for source, expected in [('Remediation:\nSet USER app.', 'Remediation'),
                                 ('Description:\nRun without root.', 'Description'),
                                 ('Run without root.', 'Source')]:
            with self.subTest(source=source):
                blocks = _source_blocks(Section('4.1', 'Create a user', source))
                self.assertEqual(len(blocks), 1)
                self.assertEqual(blocks[0][0], expected)
                self.assertEqual(blocks[0][1].text, source)


if __name__ == '__main__':
    unittest.main()
