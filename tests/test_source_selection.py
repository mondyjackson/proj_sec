import hashlib
import json
from pathlib import Path
import tempfile
import unittest

from proj_sec.common import load_kdes, normalize
from proj_sec.extractor import _analyze_response, _parse_response, _source_blocks, extract_kdes, validate_documents
from proj_sec.pdfio import Section, split_sections
from proj_sec.prompts import BUILDERS
from proj_sec.selection import candidate_excerpts, parse_ids
from tests.helpers import TEXT, make_pdf


REMEDIATION = '''Edit the Docker daemon configuration file to ensure that icc is disabled. It should include
the following setting
"icc": false
Alernatively, run the docker daemon directly and pass --icc=false as an argument.
For Example,
dockerd --icc=false
Alternatively, you can follow the Docker documentation and create a custom network
and only join containers that need to communicate to that custom network. The --icc
parameter only applies to the default docker bridge, if custom networks are used then
the approach of segmenting networks should be adopted instead.
In order for this control to be fully effective, all containers connected to the docker0
bridge should drop the NET_RAW capability, otherwise a compromised container could
use raw ethernet packets to communicate with other containers despite this restriction.'''


class SourceSelectionTests(unittest.TestCase):
    def setUp(self):
        self.section = Section('2.2', 'Ensure network traffic is restricted between containers on the default bridge',
                               'Remediation:\n' + REMEDIATION)

    def test_real_partial_selections_preserve_all_remediation_and_record_added_context(self):
        spans = candidate_excerpts(self.section)
        self.assertEqual(len(spans), 5)
        for raw, selected in [('1, 3\n', [1, 3]), ('1,3,5\n', [1, 3, 5]), ('1, 4\n', [1, 4])]:
            with self.subTest(raw=raw):
                value, metadata = _analyze_response(raw, self.section)
                self.assertEqual(set(value['requirements']), set(spans))
                self.assertEqual(metadata['selected_ids'], selected)
                self.assertEqual(metadata['included_source_ids'], [1, 2, 3, 4, 5])
                self.assertEqual(metadata['context_added_ids'], [i for i in range(1, 6) if i not in selected])
                self.assertEqual(metadata['coverage_policy'], 'retain-complete-remediation')
                output = ' '.join(value['requirements'])
                self.assertIn('"icc": false', output)
                self.assertIn('dockerd --icc=false', output)
                self.assertIn('NET_RAW', output)
                self.assertIn('default docker bridge', output)
                self.assertTrue(all(requirement in normalize(REMEDIATION) for requirement in value['requirements']))

    def test_candidate_splitting_preserves_every_non_whitespace_character(self):
        spans = candidate_excerpts(self.section)
        self.assertEqual(''.join(''.join(s.split()) for s in spans), ''.join(REMEDIATION.split()))

    def test_description_remains_model_selected_and_can_have_no_obligations(self):
        section = Section('x', 'A source heading', 'Description:\nBackground information. Require administrator access.')
        value, metadata = _analyze_response('2', section)
        self.assertEqual(value['requirements'], ['Require administrator access.'])
        self.assertEqual(metadata['context_added_ids'], [])
        self.assertEqual(_parse_response('NONE', section)['requirements'], [])
        with self.assertRaises(ValueError):
            _parse_response('NONE', self.section)

    def test_bad_ids_and_arbitrary_prose_cannot_produce_source_requirements(self):
        for raw in ('0', '6', '-1', '[true]', '[1.5]', '1 because 3', '1,3 trailing text', '[]'):
            with self.subTest(raw=raw):
                with self.assertRaises(ValueError):
                    _parse_response(raw, self.section)
        self.assertEqual(parse_ids('```text\n1,3\n```', 5), [1, 3])
        self.assertEqual(parse_ids('{"ids":[1,3]}', 5), [1, 3])

    def test_prompt_builders_request_ids_and_keep_json_builders_for_old_cache_keys(self):
        for style, builder in BUILDERS.items():
            with self.subTest(style=style):
                prompt = builder(self.section, output_format='ids')
                self.assertIn('Return ONLY the selected excerpt numbers', prompt)
                self.assertIn('[5] In order for this control', prompt)
                self.assertNotIn('Required response structure', prompt)
                self.assertIn('Required response structure', builder(self.section))

    def test_legacy_cache_is_reused_without_claiming_a_new_prompt_was_sent(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            pdf = root / 'cis.pdf'
            make_pdf(pdf, TEXT)
            documents = validate_documents(pdf, pdf)
            section = split_sections(documents[0])[0]
            cache = root / 'cache'
            cache.mkdir()
            identity = 'same-model'
            for field, part in _source_blocks(section):
                prompt = BUILDERS['zero-shot'](part)
                key = hashlib.sha256(('source-block-v1\n' + identity + '\n' + field + '\n' + prompt).encode()).hexdigest()
                requirement = 'Set USER app.' if field == 'Remediation' else 'Containers should run as a non-root user.'
                (cache / f'{key}.json').write_text(json.dumps({'raw': json.dumps({'name': part.title, 'requirements': [requirement]}),
                                                            'prompt_used': prompt, 'model_identity': identity}))
            def no_generation(prompt):
                self.fail('A validated legacy cache response should have been reused.')
            result = extract_kdes(documents, root / 'out', no_generation, cache_dir=cache,
                                  model_identity=identity, section_limit=1, prompt_types=('zero-shot',))
            self.assertEqual(len(load_kdes(result['zero-shot'][0])), 1)
            log = (root / 'out/llm-output.txt').read_text()
            self.assertIn('*Cached*\nTrue', log)
            self.assertIn('*Output Format*\nlegacy-json', log)
            actual_prompts = (root / 'out/PROMPT.md').read_text()
            self.assertIn('Required response structure', actual_prompts)
            self.assertNotIn('Source excerpts:', actual_prompts)

    def test_numeric_responses_are_cached_with_actual_selections_and_context_policy(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            pdf = root / 'cis.pdf'
            make_pdf(pdf, TEXT)
            calls = []
            def generate(prompt):
                calls.append(prompt)
                self.assertIn('selected excerpt numbers', prompt)
                return '1\n'
            options = {'model_identity': 'same-model', 'cache_dir': root / 'cache',
                       'section_limit': 1, 'prompt_types': ('zero-shot',)}
            documents = validate_documents(pdf, pdf)
            extract_kdes(documents, root / 'one', generate, **options)
            extract_kdes(documents, root / 'two', generate, **options)
            self.assertEqual(len(calls), 2)
            cache = [json.loads(p.read_text()) for p in (root / 'cache').glob('*.json')]
            self.assertTrue(all(entry['raw'] == '1\n' for entry in cache))
            self.assertTrue(all(entry['selected_ids'] == [1] for entry in cache))
            log = (root / 'two/llm-output.txt').read_text()
            self.assertIn('*Model Selected IDs*\n[1]', log)
            self.assertIn('*Coverage Policy*\nretain-complete-remediation', log)


if __name__ == '__main__':
    unittest.main()
