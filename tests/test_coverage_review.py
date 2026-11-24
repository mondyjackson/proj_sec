import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

import pandas as pd

from proj_sec.cli import main
from proj_sec.common import COLUMNS, load_kdes
from proj_sec.coverage_review import instruction_evidence, proposal_evidence, refine_pair, review_block, text_coverage
from proj_sec.extractor import extract_kdes, validate_documents
from tests.helpers import TEXT, make_pdf


class Generator:
    identity = 'isolated-test-generator'

    def __init__(self, responses):
        self.responses = iter(responses)
        self.calls = []

    def select_ids(self, prompt, count, *, allow_empty):
        self.calls.append((prompt, count, allow_empty))
        return next(self.responses)


def block(spans, prior=None):
    return {'file': 'test.pdf', 'cis_id': 'example', 'source_field': 'Remediation',
            'prompt_type': 'zero-shot', 'source_excerpts': spans,
            'model_selected_requirements': prior or []}


class CoverageReviewTests(unittest.TestCase):
    def test_none_cannot_be_backfilled_by_the_evidence_gate(self):
        with tempfile.TemporaryDirectory() as tmp:
            model = Generator(['NONE'])
            result = review_block(block(['Disable public access.']), model, tmp)
            self.assertEqual(result['requirements'], [])
            self.assertEqual(result['unresolved_source_ids'], [1])
            self.assertEqual(len(model.calls), 1)

    def test_model_proposals_are_filtered_and_raw_response_is_preserved(self):
        with tempfile.TemporaryDirectory() as tmp:
            result = review_block(block(['Disable public access.', 'The service is called Example.']),
                                  Generator(['1,2\n']), tmp)
            self.assertEqual(result['requirements'], ['Disable public access.'])
            request = result['reviews'][0]
            self.assertEqual(request['raw_output'], '1,2\n')
            self.assertEqual(request['proposed_source_ids'], [1, 2])
            self.assertEqual(request['rejected'][0]['source_id'], 2)

    def test_second_pass_preserves_original_numbering_and_does_not_retry_rejected_ids(self):
        with tempfile.TemporaryDirectory() as tmp:
            result = review_block(block(['Disable public access.', 'The service is called Example.',
                                         'Require authentication.']), Generator(['1,2', '1']), tmp)
            self.assertEqual(result['reviews'][1]['remaining_source_ids'], [3])
            self.assertEqual(result['reviews'][1]['accepted'][0]['source_id'], 3)
            self.assertEqual(result['after_states'], ['full', 'missing', 'full'])

    def test_cache_is_revalidated_and_does_not_need_inference(self):
        with tempfile.TemporaryDirectory() as tmp:
            item = block(['Disable public access.'])
            first = review_block(item, Generator(['1']), tmp)
            model = Generator([])
            second = review_block(item, model, tmp)
            self.assertEqual(first['requirements'], second['requirements'])
            self.assertFalse(model.calls)
            self.assertTrue(second['reviews'][0]['cached'])
            cache = next(Path(tmp).glob('*.json'))
            saved = json.loads(cache.read_text()); saved['raw_output'] = '99'
            cache.write_text(json.dumps(saved))
            with self.assertRaises(ValueError):
                review_block(item, Generator([]), tmp)

    def test_cache_with_wrong_prompt_is_rejected(self):
        with tempfile.TemporaryDirectory() as tmp:
            item = block(['Disable public access.'])
            review_block(item, Generator(['1']), tmp)
            cache = next(Path(tmp).glob('*.json'))
            saved = json.loads(cache.read_text()); saved['prompt'] += 'altered'
            cache.write_text(json.dumps(saved))
            with self.assertRaisesRegex(ValueError, 'identity mismatch'):
                review_block(item, Generator([]), tmp)

    def test_large_blocks_offer_every_candidate_in_worker_supported_batches(self):
        with tempfile.TemporaryDirectory() as tmp:
            model = Generator(['NONE', '1'])
            result = review_block(block([f'Disable test setting {i}.' for i in range(13)]),
                                  model, tmp, passes=1)
            self.assertEqual([c[1] for c in model.calls], [12, 1])
            self.assertEqual(result['reviews'][1]['accepted'][0]['source_id'], 13)

    def test_legacy_fragments_can_jointly_cover_a_source_span(self):
        spans = ['Disable public access. Require authentication.']
        self.assertEqual(text_coverage(spans, ['Disable public access.', 'Require authentication.']), ['full'])
        self.assertEqual(text_coverage(spans, ['Disable public access.']), ['partial'])
        with self.assertRaises(ValueError):
            text_coverage(spans, ['Invent a rule.'])

    def test_conditional_no_action_and_need_clauses_are_kept_when_proposed(self):
        for text in ['If the default meets your needs, no action is necessary.',
                     'Under unusual load, you might need a larger queue.']:
            self.assertIsNotNone(instruction_evidence(text))
        self.assertIsNone(instruction_evidence('The service is named QueueService.'))

    def test_a_supporting_referent_requires_an_adjacent_selected_instruction(self):
        spans = ['The broad-access flag grants every privilege.',
                 'For this reason you should ensure that it is not used.']
        self.assertIsNotNone(proposal_evidence(1, spans, [spans[1]]))
        self.assertIsNone(proposal_evidence(1, spans, []))
        self.assertIsNone(proposal_evidence(1, spans + ['Run the service.'], ['Run the service.']))

    def test_description_of_a_capability_is_not_an_operator_instruction(self):
        for text in ['The tool can generate a report.',
                     'iptables is used to set up, maintain, and inspect tables.',
                     'You do not need to change this setting.']:
            self.assertIsNone(instruction_evidence(text))

    def test_final_yaml_and_logs_contain_baseline_and_only_accepted_proposals(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp); pdf = root / 'test.pdf'; output = root / 'out'
            text = TEXT.replace('Set USER app.', 'Set USER app. The service is called Example. Require authentication.')
            make_pdf(pdf, text)
            outputs = extract_kdes(validate_documents(pdf, pdf), output, lambda p: '1',
                                   section_limit=1, model_identity='initial-test')
            initial = json.loads((output / 'llm-records.json').read_text())
            model = Generator(['1,2'] * 3)
            refine_pair(outputs, output, model, cache_dir=root / 'review-cache')
            for paths in outputs.values():
                self.assertEqual(load_kdes(paths[0]), load_kdes(paths[1]))
                requirements = load_kdes(paths[0])['element1']['requirements']
                self.assertIn('Require authentication.', requirements)
                self.assertNotIn('The service is called Example.', requirements)
            combined = json.loads((output / 'llm-records.json').read_text())
            self.assertEqual(combined[:len(initial)], initial)
            self.assertEqual(len(combined), len(initial) + 6)
            self.assertIn('*Rejected Review Proposals*', (output / 'llm-output.txt').read_text())
            self.assertEqual((output / 'PROMPT.md').read_text().count('\n## '), 3)
            context = json.loads((output / 'source-context.json').read_text())
            self.assertTrue(all('final_requirements' in b for b in context['blocks']))
            status = json.loads((output / 'coverage-review.json').read_text())
            self.assertEqual(status['status'], 'completed-needs-quality-review')
            self.assertEqual(status['new_model_requests'], 3)

    def test_review_refuses_inconsistent_initial_yaml_before_model_calls(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp); pdf = root / 'test.pdf'; output = root / 'out'
            make_pdf(pdf, TEXT)
            outputs = extract_kdes(validate_documents(pdf, pdf), output, lambda p: '1', section_limit=1)
            path = outputs['zero-shot'][0]
            path.write_text(path.read_text().replace('Set USER app.', 'Invented setting.'))
            model = Generator([])
            with self.assertRaisesRegex(ValueError, 'does not match'):
                refine_pair(outputs, output, model, cache_dir=root / 'review-cache')
            self.assertFalse(model.calls)

    def test_a_failed_review_does_not_mark_itself_complete(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp); pdf = root / 'test.pdf'; output = root / 'out'
            make_pdf(pdf, TEXT.replace('Set USER app.', 'Set USER app. Require authentication.'))
            outputs = extract_kdes(validate_documents(pdf, pdf), output, lambda p: '1', section_limit=1)
            before = outputs['zero-shot'][0].read_bytes()
            with self.assertRaises(ValueError):
                refine_pair(outputs, output, Generator(['99']), cache_dir=root / 'review-cache')
            self.assertEqual(outputs['zero-shot'][0].read_bytes(), before)
            self.assertEqual(json.loads((output / 'coverage-review.json').read_text())['status'], 'incomplete')

    def test_initial_model_review_model_and_scanner_never_overlap(self):
        events = []
        class Model:
            active = None
            identity = 'test'
            def __init__(self, *args, **kwargs):
                self.dtype = kwargs['dtype']
                if Model.active is not None:
                    raise AssertionError('Two model contexts overlap')
            def __enter__(self):
                Model.active = self.dtype; events.append(('open', self.dtype)); return self
            def __exit__(self, *args):
                events.append(('close', self.dtype)); Model.active = None
        def initial(*args, **kwargs):
            self.assertEqual(Model.active, 'bfloat16'); return {'zero-shot': ('l.yaml', 'r.yaml')}
        def review(*args, **kwargs):
            self.assertEqual(Model.active, 'float32'); return args[0]
        def scan(*args, **kwargs):
            self.assertIsNone(Model.active)
            frame = pd.DataFrame(columns=COLUMNS); frame.attrs['scan_status'] = 'completed'; return frame
        with tempfile.TemporaryDirectory() as tmp:
            with patch('proj_sec.cli.GemmaGenerator', Model), \
                    patch('proj_sec.cli._prepare', return_value=(('left', 'right'), [])), \
                    patch('proj_sec.cli.extract_kdes', side_effect=initial), \
                    patch('proj_sec.cli.refine_pair', side_effect=review), \
                    patch('proj_sec.cli._compare', return_value=('n.txt', 'r.txt', 'h.txt')), \
                    patch('proj_sec.cli.run_hadolint', side_effect=scan):
                result = main(['run', 'l.pdf', 'r.pdf', '--dockerfiles', 'test.zip',
                               '--output', tmp, '--dtype', 'bfloat16'])
        self.assertEqual(result, 0)
        self.assertEqual(events, [('open', 'bfloat16'), ('close', 'bfloat16'),
                                  ('open', 'float32'), ('close', 'float32')])


if __name__ == '__main__':
    unittest.main()
