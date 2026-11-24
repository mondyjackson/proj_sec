from tests.helpers import is_remediation_prompt
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from proj_sec.common import load_kdes
from proj_sec.extractor import _parse_response, extract_kdes, validate_documents
from proj_sec.pdfio import Section
from proj_sec.prompts import BUILDERS
from scripts import check_extraction
from tests.helpers import TEXT, make_pdf


class ExtractionFormatTests(unittest.TestCase):
    def test_all_styles_show_both_required_keys_and_json_escaped_title(self):
        section = Section('1.1.1', 'Ensure "quoted" path \\ exists', 'Create a separate partition.')
        for style, builder in BUILDERS.items():
            with self.subTest(style=style):
                prompt = builder(section)
                template = prompt.split('Required response structure (schema, not a completed extraction):\n')[-1].splitlines()[0]
                value = json.loads(template)
                self.assertEqual(value['name'], section.title)
                self.assertEqual(value['requirements'], ['<exact source excerpt>'])

    def test_actual_name_only_failure_remains_rejected(self):
        section = Section('1.1.1', 'Ensure a separate partition for containers has been created', 'Create a partition.')
        raw = '```json\n{"name": "Create a separate partition for containers"}\n```'
        with self.assertRaisesRegex(ValueError, 'at least one requirement'):
            _parse_response(raw, section)
        with self.assertRaisesRegex(ValueError, 'at least one requirement'):
            _parse_response(json.dumps({'name': section.title}), section)

    def test_retry_does_not_embed_bad_output_and_preserves_failed_audit(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            pdf = root / 'cis.pdf'
            make_pdf(pdf, TEXT)
            prompts = []
            def invalid(prompt):
                prompts.append(prompt)
                return '{"name":"UNIQUE_INVALID_SHORT_NAME"}'
            out = root / 'out'
            with self.assertRaisesRegex(ValueError, 'at least one requirement'):
                extract_kdes(validate_documents(pdf, pdf), out, invalid, retries=1)
            self.assertEqual(len(prompts), 2)
            self.assertIn('Correction required', prompts[1])
            self.assertNotIn('UNIQUE_INVALID_SHORT_NAME', prompts[1])
            self.assertIn('UNIQUE_INVALID_SHORT_NAME', (out / 'llm-output.txt').read_text())
            self.assertIn('Correction required', (out / 'PROMPT.md').read_text())
            self.assertFalse(list(out.rglob('*-kdes.yaml')))
            self.assertFalse(list((out / 'cache').glob('*.json')))

    def test_sampled_check_is_labeled_and_caches_valid_results_only(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            pdf = root / 'cis.pdf'
            make_pdf(pdf, TEXT)
            calls = []
            class Generator:
                identity = 'controlled-test-double'
                def __init__(self, *args, **kwargs):
                    pass
                def __enter__(self):
                    return self
                def __exit__(self, *args):
                    pass
                def __call__(self, prompt):
                    calls.append(prompt)
                    name = prompt.split('Element name: ')[-1].splitlines()[0]
                    return json.dumps({'name': name, 'requirements': ['Set USER app.' if is_remediation_prompt(prompt) else 'Containers should run as a non-root user.']})
            output = root / 'sample'
            with patch('scripts.check_extraction.GemmaGenerator', Generator):
                result = check_extraction.main(['--pdf', str(pdf), '--output', str(output), '--model-cache', str(root / 'cache')])
            self.assertEqual(result, 0)
            self.assertEqual(len(calls), 6)
            status = json.loads((output / 'check-status.json').read_text())
            self.assertTrue(status['diagnostic_only'])
            self.assertEqual(status['checked_sections'], 1)
            self.assertEqual(status['total_sections'], 2)
            self.assertEqual(status['status'], 'passed')
            for style in BUILDERS:
                self.assertEqual(len(load_kdes(output / style / 'left-cis-kdes.yaml')), 1)

    def test_invalid_sample_limit_cannot_silently_create_empty_yaml(self):
        for limit in (0, -1, True, 1.5):
            with self.subTest(limit=limit):
                with self.assertRaisesRegex(ValueError, 'section_limit'):
                    extract_kdes((), 'unused', lambda p: '', section_limit=limit)


if __name__ == '__main__':
    unittest.main()
