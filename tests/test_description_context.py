import tempfile
import unittest
from pathlib import Path

from proj_sec.common import load_kdes
from proj_sec.comparator import compare_requirements, load_yaml_pair
from proj_sec.extractor import _analyze_response, extract_kdes, validate_documents
from proj_sec.pdfio import Section
from tests.helpers import TEXT, is_remediation_prompt, make_pdf


class DescriptionContextTests(unittest.TestCase):
    def test_none_is_logged_as_none_while_source_condition_is_retained(self):
        section = Section('5.6', 'Restrict mounts',
                          'Description:\nDo not mount sensitive directories.\n/\n/lib\n/lib64')
        value, metadata = _analyze_response('NONE', section, retain_description_context=True)
        self.assertIn('/lib64', ' '.join(value['requirements']))
        self.assertEqual(metadata['selected_ids'], [])
        self.assertEqual(metadata['model_selected_requirements'], [])
        self.assertEqual(metadata['context_added_ids'], metadata['included_source_ids'])
        self.assertEqual(metadata['coverage_policy'], 'retain-description-context-for-remediation')

    def test_partial_legacy_copy_preserves_omitted_qualifier_as_source_context(self):
        section = Section('x', 'Audit configuration',
                          'Description:\nAudit /etc/service.conf if applicable.')
        raw = '{"name":"Audit configuration","requirements":["Audit /etc/service.conf"]}'
        value, metadata = _analyze_response(raw, section, retain_description_context=True)
        self.assertEqual(value['requirements'], ['Audit /etc/service.conf if applicable.'])
        self.assertEqual(metadata['model_selected_requirements'], ['Audit /etc/service.conf'])

    def test_real_observed_lib64_change_is_detected_with_none_description_and_cached_resume(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            old, new = root/'old.pdf', root/'new.pdf'
            old_text = TEXT.replace('Containers should run as a non-root user.',
                                    'Do not mount sensitive directories / /lib /usr.')
            new_text = old_text.replace('/ /lib /usr.', '/ /lib /lib64 /usr.')
            make_pdf(old, old_text)
            make_pdf(new, new_text)
            calls = []
            def generate(prompt):
                calls.append(prompt)
                return '1' if is_remediation_prompt(prompt) else 'NONE'
            options = dict(model_identity='test-double', cache_dir=root/'cache',
                           section_limit=1, prompt_types=('zero-shot',))
            docs = validate_documents(old, new)
            paths = extract_kdes(docs, root/'one', generate, **options)['zero-shot']
            self.assertEqual(len(calls), 3)
            diff = compare_requirements(load_yaml_pair(*paths), root/'requirements.txt').read_text()
            self.assertIn('/lib64', diff)
            self.assertIn('/ /lib /usr.', diff)
            def no_generation(prompt):
                self.fail('The completed responses must be reused without inference.')
            refreshed = extract_kdes(docs, root/'two', no_generation, **options)['zero-shot']
            self.assertEqual(load_kdes(paths[0]), load_kdes(refreshed[0]))
            self.assertEqual(load_kdes(paths[1]), load_kdes(refreshed[1]))
            log = (root/'two/llm-output.txt').read_text()
            self.assertIn('*LLM Output*\nNONE', log)
            self.assertIn('*Model Selected Requirements*\n[]', log)
            self.assertIn('*Coverage Policy*\nretain-description-context-for-remediation', log)

    def test_missing_model_requirement_still_cannot_complete_recommendation(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            pdf = root/'cis.pdf'
            make_pdf(pdf, TEXT)
            with self.assertRaises(ValueError):
                extract_kdes(validate_documents(pdf, pdf), root/'out', lambda prompt: 'NONE',
                             section_limit=1, prompt_types=('zero-shot',), retries=0)
            self.assertFalse(list((root/'out').rglob('*-kdes.yaml')))

    def test_description_without_remediation_does_not_turn_none_into_requirement(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            pdf = root/'cis.pdf'
            make_pdf(pdf, TEXT.split('Remediation:', 1)[0])
            with self.assertRaisesRegex(ValueError, 'no requirements selected'):
                extract_kdes(validate_documents(pdf, pdf), root/'out', lambda prompt: 'NONE',
                             section_limit=1, prompt_types=('zero-shot',), retries=0)
            self.assertFalse(list((root/'out').rglob('*-kdes.yaml')))


if __name__ == '__main__':
    unittest.main()
