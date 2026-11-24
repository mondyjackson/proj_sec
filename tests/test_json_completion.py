from tests.helpers import is_remediation_prompt
import json
from pathlib import Path
import tempfile
import unittest

from proj_sec.extractor import _decode_response, _parse_response, extract_kdes, validate_documents
from proj_sec.pdfio import Section
from tests.helpers import TEXT, make_pdf


class JsonCompletionTests(unittest.TestCase):
    def setUp(self):
        self.section = Section('1.1.1', 'Ensure a separate partition for containers has been created',
            'Description:\nContainers use /var/lib/docker.\n\nRemediation:\n'
            'For new installations, create a separate partition.\nFor existing systems, use LVM.')

    def test_only_final_object_brace_can_be_completed(self):
        value = {'name': self.section.title,
                 'requirements': ['For new installations, create a separate partition.',
                                  'For existing systems, use LVM.']}
        raw = '```json\n' + json.dumps(value)[:-1] + '\n```'
        decoded, repair = _decode_response(raw)
        self.assertEqual(decoded, value)
        self.assertEqual(repair, 'appended one missing final object brace')
        result = _parse_response(raw, self.section)
        self.assertEqual(set(result['requirements']), set(value['requirements']))

    def test_description_only_is_rejected_after_syntax_completion(self):
        raw = json.dumps({'name': self.section.title,
                          'requirements': ['Containers use /var/lib/docker.']})[:-1]
        with self.assertRaisesRegex(ValueError, 'omitted the Remediation'):
            _parse_response(raw, self.section)

    def test_completion_never_invents_missing_values_or_ignores_trailing_text(self):
        valid = json.dumps({'name': self.section.title,
                            'requirements': ['For existing systems, use LVM.']})
        bad = [valid[:-2], valid + ' trailing text', valid + valid,
               '```json\n' + valid, '{"name":"unfinished',
               '{"name":"x","requirements":["x"],"nested":[{}]']
        for raw in bad:
            with self.subTest(raw=raw):
                with self.assertRaisesRegex(ValueError, 'complete JSON object'):
                    _decode_response(raw)

    def test_completion_does_not_bypass_requirements_or_source_validation(self):
        for value, error in [({'name': 'Wrong name', 'requirements': []}, 'at least one requirement'),
                             ({'name': self.section.title, 'requirements': ['Invented LVM command.']}, 'matching source excerpt')]:
            with self.subTest(value=value):
                with self.assertRaisesRegex(ValueError, error):
                    _parse_response(json.dumps(value)[:-1], self.section)

    def test_cached_completion_keeps_original_raw_output_and_audit_note(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            pdf = root / 'cis.pdf'
            make_pdf(pdf, TEXT)
            generated = []
            def generate(prompt):
                name = prompt.split('Element name: ')[-1].splitlines()[0]
                requirement = ('Set USER app.' if '4.1\n' in prompt else 'Replace ADD with COPY.') if is_remediation_prompt(prompt) else ('Containers should run as a non-root user.' if '4.1\n' in prompt else 'Use COPY for local files.')
                raw = json.dumps({'name': name, 'requirements': [requirement]})[:-1]
                generated.append(raw)
                return raw
            extract_kdes(validate_documents(pdf, pdf), root / 'out', generate,
                         prompt_types=('zero-shot',), model_identity='controlled-test-double')
            self.assertEqual(len(generated), 4)
            cached = [json.loads(p.read_text()) for p in (root / 'out/cache').glob('*.json')]
            self.assertEqual({entry['raw'] for entry in cached}, set(generated))
            self.assertTrue(all(entry['syntax_repair'] == 'appended one missing final object brace' for entry in cached))
            log = (root / 'out/llm-output.txt').read_text()
            self.assertIn('*Syntax Repair*\nappended one missing final object brace', log)
            self.assertIn('*Cached*\nTrue', log)

    def test_wrong_block_content_is_logged_and_never_completes_the_element(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            pdf = root / 'cis.pdf'
            make_pdf(pdf, TEXT)
            name = 'Ensure that a user for the container has been created'
            raw = json.dumps({'name': name, 'requirements': ['Containers should run as a non-root user.']})[:-1]
            with self.assertRaisesRegex(ValueError, 'matching source excerpt'):
                extract_kdes(validate_documents(pdf, pdf), root / 'out', lambda prompt: raw,
                             prompt_types=('zero-shot',), retries=0)
            log = (root / 'out/llm-output.txt').read_text()
            self.assertIn(raw, log)
            self.assertIn('*Syntax Repair*\nappended one missing final object brace', log)
            self.assertIn('matching source excerpt', log)
            self.assertEqual(len(list((root / 'out/cache').glob('*.json'))), 1)  # Only the valid Description was cached.
            self.assertFalse(list((root / 'out').rglob('*-kdes.yaml')))


if __name__ == '__main__':
    unittest.main()
