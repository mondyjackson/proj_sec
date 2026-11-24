from tests.helpers import is_remediation_prompt
import json
from pathlib import Path
import tempfile
import unittest

from proj_sec.extractor import _decode_response, _parse_response, extract_kdes, validate_documents
from proj_sec.pdfio import Section
from tests.helpers import TEXT, make_pdf


class ExtraJsonDelimiterTests(unittest.TestCase):
    def setUp(self):
        self.section = Section('1.1.8',
            'Ensure auditing is configured for Docker files and directories - containerd.sock',
            'Description:\nAudit containerd.sock, if applicable.')
        self.value = {'name': self.section.title,
                      'requirements': ['Audit containerd.sock, if applicable.']}

    def test_observed_complete_object_with_extra_array_and_object_closers(self):
        raw = '```json\n' + json.dumps(self.value) + ']}\n```'
        value, note = _decode_response(raw)
        self.assertEqual(value, self.value)
        self.assertEqual(note, 'removed redundant closing delimiters after complete JSON object')
        self.assertEqual(_parse_response(raw, self.section)['requirements'], self.value['requirements'])

    def test_text_another_value_openers_and_unbounded_delimiters_are_rejected(self):
        for trailing in (' explanation', '\n{}', '\n[]', ', {}', '] null', ']42', '[', '{', '}' * 33):
            with self.subTest(trailing=trailing):
                with self.assertRaisesRegex(ValueError, 'complete JSON object'):
                    _decode_response(json.dumps(self.value) + trailing)

    def test_delimiter_repair_does_not_bypass_requirements_or_source_checks(self):
        for value, error in [({'name': 'Wrong heading', 'requirements': []}, 'at least one requirement'),
                             ({'name': self.section.title, 'requirements': ['Invented auditing obligation.']}, 'matching source excerpt')]:
            with self.subTest(value=value):
                with self.assertRaisesRegex(ValueError, error):
                    _parse_response(json.dumps(value) + ']}', self.section)

    def test_redundant_closers_remain_in_raw_cache_and_audit(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            pdf = root / 'cis.pdf'
            make_pdf(pdf, TEXT)
            calls = []
            def generate(prompt):
                name = prompt.split('Element name: ')[-1].splitlines()[0]
                requirement = 'Set USER app.' if is_remediation_prompt(prompt) else 'Containers should run as a non-root user.'
                raw = json.dumps({'name': name, 'requirements': [requirement]}) + ']}'
                calls.append(raw)
                return raw
            options = {'prompt_types': ('zero-shot',), 'section_limit': 1,
                       'cache_dir': root / 'cache', 'model_identity': 'controlled-test-double'}
            documents = validate_documents(pdf, pdf)
            extract_kdes(documents, root / 'first', generate, **options)
            extract_kdes(documents, root / 'second', generate, **options)
            self.assertEqual(len(calls), 2)
            cache = [json.loads(p.read_text()) for p in (root / 'cache').glob('*.json')]
            self.assertEqual({entry['raw'] for entry in cache}, set(calls))
            self.assertTrue(all('redundant closing delimiters' in entry['syntax_repair'] for entry in cache))
            log = (root / 'second/llm-output.txt').read_text()
            self.assertIn('*Cached*\nTrue', log)
            self.assertIn(']}', log)
            self.assertIn('*Syntax Repair*\nremoved redundant closing delimiters', log)


if __name__ == '__main__':
    unittest.main()
