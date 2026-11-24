from tests.helpers import is_remediation_prompt
import json
from pathlib import Path
import tempfile
import unittest

from proj_sec.common import load_kdes
from proj_sec.extractor import _parse_response, extract_kdes, validate_documents
from proj_sec.pdfio import Section
from tests.helpers import TEXT, make_pdf


class SourceHeadingNameTests(unittest.TestCase):
    def setUp(self):
        self.section = Section('1.1.9', 'Ensure auditing is configured for the original source heading',
                               'Description:\nAudit this file, if applicable.')

    def test_source_heading_is_used_when_model_label_differs_or_is_missing(self):
        for label in ('Shortened model heading', None, 42):
            with self.subTest(label=label):
                value = {'name': label, 'requirements': ['Audit this file, if applicable.']}
                result = _parse_response(json.dumps(value), self.section)
                self.assertEqual(result['name'], self.section.title)
                self.assertEqual(result['source_ids'], ['1.1.9'])
        result = _parse_response(json.dumps({'requirements': ['Audit this file, if applicable.']}), self.section)
        self.assertEqual(result['name'], self.section.title)

    def test_source_heading_does_not_make_unmatched_or_missing_requirements_valid(self):
        for value in ({'name': 'Other heading', 'requirements': ['Invented auditing command.']},
                      {'name': 'Other heading'}, {'requirements': []}):
            with self.subTest(value=value):
                with self.assertRaises(ValueError):
                    _parse_response(json.dumps(value), self.section)

    def test_mismatched_model_label_is_preserved_without_redundant_retry(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            pdf = root / 'cis.pdf'
            make_pdf(pdf, TEXT)
            calls = []
            def generate(prompt):
                requirement = 'Set USER app.' if is_remediation_prompt(prompt) else 'Containers should run as a non-root user.'
                raw = json.dumps({'name': 'Shortened model heading', 'requirements': [requirement]})
                calls.append(raw)
                return raw
            options = {'prompt_types': ('zero-shot',), 'section_limit': 1,
                       'cache_dir': root / 'cache', 'model_identity': 'controlled-test-double'}
            documents = validate_documents(pdf, pdf)
            results = extract_kdes(documents, root / 'first', generate, **options)
            self.assertEqual(len(calls), 2)
            element = load_kdes(results['zero-shot'][0])['element1']
            self.assertEqual(element['name'], 'Ensure that a user for the container has been created')
            self.assertEqual(set(element['requirements']), {'Containers should run as a non-root user.', 'Set USER app.'})
            log = (root / 'first/llm-output.txt').read_text()
            self.assertIn('*Element Name Source*\nPDF heading', log)
            self.assertIn('*Model Element Name*\n"Shortened model heading"', log)
            self.assertIn('*Model Name Differs*\nTrue', log)
            cached = [json.loads(p.read_text()) for p in (root / 'cache').glob('*.json')]
            self.assertEqual({entry['raw'] for entry in cached}, set(calls))
            self.assertTrue(all(entry['model_name_differs'] for entry in cached))
            extract_kdes(documents, root / 'second', generate, **options)
            self.assertEqual(len(calls), 2)

    def test_requirements_only_response_supports_the_same_bounded_punctuation_repairs(self):
        raw = json.dumps({'requirements': ['Audit this file, if applicable.']})
        for response in (raw, raw + ']}', raw[:-1]):
            with self.subTest(response=response):
                result = _parse_response(response, self.section)
                self.assertEqual(result['name'], self.section.title)
                self.assertEqual(result['requirements'], ['Audit this file, if applicable.'])

    def test_non_object_response_cannot_be_used_as_requirements(self):
        with self.assertRaisesRegex(ValueError, 'integers'):
            _parse_response('["Audit this file, if applicable."]', self.section)


if __name__ == '__main__':
    unittest.main()
