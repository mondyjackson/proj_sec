import json
import tempfile
import unittest
from pathlib import Path

from proj_sec.common import NO_REQUIREMENTS, load_kdes
from proj_sec.comparator import compare_requirements, load_yaml_pair
from proj_sec.extractor import _analyze_response, extract_kdes, validate_documents
from proj_sec.pdfio import Section
from tests.helpers import TEXT, is_remediation_prompt, make_pdf


class DescriptionContextTests(unittest.TestCase):
    def test_none_preserves_source_context_without_creating_a_requirement(self):
        section = Section('5.6', 'Restrict mounts',
                          'Description:\nDo not mount sensitive directories.\n/\n/lib\n/lib64')
        value, metadata = _analyze_response('NONE', section, retain_description_context=True)
        self.assertEqual(value['requirements'], [])
        self.assertIn('/lib64', ' '.join(metadata['source_context_requirements']))
        self.assertEqual(metadata['selected_ids'], [])
        self.assertEqual(metadata['model_selected_requirements'], [])
        self.assertEqual(metadata['context_added_ids'], [])
        self.assertEqual(metadata['coverage_policy'], 'model-selected-only')
        self.assertIn('no-model-selection', metadata['review_flags'])

    def test_partial_legacy_copy_does_not_backfill_an_omitted_qualifier(self):
        section = Section('x', 'Audit configuration',
                          'Description:\nAudit /etc/service.conf if applicable.')
        raw = '{"name":"Audit configuration","requirements":["Audit /etc/service.conf"]}'
        value, metadata = _analyze_response(raw, section, retain_description_context=True)
        self.assertEqual(value['requirements'], ['Audit /etc/service.conf'])
        self.assertEqual(metadata['source_context_requirements'],
                         ['Audit /etc/service.conf if applicable.'])
        self.assertEqual(metadata['unselected_source_ids'], [1])

    def test_missed_lib64_change_is_flagged_separately_and_not_injected_on_resume(self):
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
            self.assertEqual(diff.strip(), NO_REQUIREMENTS)
            self.assertNotIn('/lib64', ' '.join(load_kdes(paths[1])['element1']['requirements']))
            context = json.loads((root/'one/source-context.json').read_text())['blocks']
            missed = next(b for b in context if b['side'] == 'right'
                          and b['source_field'] == 'Description')
            self.assertIn('/lib64', ' '.join(missed['source_excerpts']))
            self.assertEqual(missed['model_selected_requirements'], [])
            self.assertIn('no-model-selection', missed['review_flags'])
            review = json.loads((root/'one/extraction-review.json').read_text())
            self.assertEqual(review['status'], 'completed-with-review-items')
            def no_generation(prompt):
                self.fail('The completed responses must be reused without inference.')
            refreshed = extract_kdes(docs, root/'two', no_generation, **options)['zero-shot']
            self.assertEqual(load_kdes(paths[0]), load_kdes(refreshed[0]))
            self.assertEqual(load_kdes(paths[1]), load_kdes(refreshed[1]))
            self.assertEqual(json.loads((root/'two/source-context.json').read_text())['blocks'], context)
            log = (root/'two/llm-output.txt').read_text()
            self.assertIn('*LLM Output*\nNONE', log)
            self.assertIn('*Model Selected Requirements*\n[]', log)
            self.assertIn('*Coverage Policy*\nmodel-selected-only', log)

    def test_missing_model_requirement_still_cannot_complete_recommendation(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            pdf = root/'cis.pdf'
            make_pdf(pdf, TEXT)
            with self.assertRaises(ValueError):
                extract_kdes(validate_documents(pdf, pdf), root/'out', lambda prompt: 'NONE',
                             section_limit=1, prompt_types=('zero-shot',), retries=0)
            self.assertFalse(list((root/'out').rglob('*-kdes.yaml')))
            review = json.loads((root/'out/extraction-review.json').read_text())
            self.assertEqual(review['status'], 'incomplete')

    def test_description_without_remediation_does_not_turn_none_into_requirement(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            pdf = root/'cis.pdf'
            make_pdf(pdf, TEXT.split('Remediation:', 1)[0])
            with self.assertRaisesRegex(ValueError, 'no requirements selected'):
                extract_kdes(validate_documents(pdf, pdf), root/'out', lambda prompt: 'NONE',
                             section_limit=1, prompt_types=('zero-shot',), retries=0)
            self.assertFalse(list((root/'out').rglob('*-kdes.yaml')))

    def test_old_cache_coverage_metadata_cannot_restore_automatic_additions(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            pdf = root/'cis.pdf'
            make_pdf(pdf, TEXT.replace('Containers should run as a non-root user.',
                                      'Background information. Containers should run as a non-root user.'))
            docs = validate_documents(pdf, pdf)
            options = dict(model_identity='test-double', cache_dir=root/'cache',
                           section_limit=1, prompt_types=('zero-shot',))
            def generate(prompt):
                return '1' if is_remediation_prompt(prompt) else '2'
            first = extract_kdes(docs, root/'one', generate, **options)['zero-shot']
            for path in (root/'cache').glob('*.json'):
                cached = json.loads(path.read_text())
                cached.update(coverage_policy='retain-complete-remediation',
                              included_source_requirements=['Background information.'],
                              context_added_ids=[1])
                path.write_text(json.dumps(cached))
            def no_generation(prompt):
                self.fail('Raw responses must be reused, without new calls or context additions.')
            second = extract_kdes(docs, root/'two', no_generation, **options)['zero-shot']
            self.assertEqual(load_kdes(first[0]), load_kdes(second[0]))
            requirements = load_kdes(second[0])['element1']['requirements']
            self.assertNotIn('Background information.', requirements)
            self.assertIn('Containers should run as a non-root user.', requirements)

    def test_complete_selections_finish_without_source_coverage_review_items(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            pdf = root/'cis.pdf'
            make_pdf(pdf, TEXT)
            extract_kdes(validate_documents(pdf, pdf), root/'out', lambda prompt: '1',
                         section_limit=1, prompt_types=('zero-shot',))
            review = json.loads((root/'out/extraction-review.json').read_text())
            self.assertEqual(review['status'], 'completed')
            self.assertEqual(review['items'], [])
            # This is source coverage only, not a claim of model accuracy.


if __name__ == '__main__':
    unittest.main()
