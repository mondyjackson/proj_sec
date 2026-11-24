import hashlib
import io
import json
from pathlib import Path
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import patch

from proj_sec.extractor import _source_blocks, extract_kdes, validate_documents
from proj_sec.model import GemmaGenerator
from proj_sec.pdfio import split_sections
from proj_sec.prompts import BUILDERS
from proj_sec.workers.gemma_worker import allowed_id_outputs, build_selection_trie, selection_prefix_fn
from tests.helpers import TEXT, make_pdf


class CharTokenizer:
    def encode(self, text, add_special_tokens=False):
        return [ord(char) for char in text]

    def decode(self, tokens, skip_special_tokens=True):
        return ''.join(chr(token) for token in tokens if token != 0)


class Ids:
    def __init__(self, values):
        self.values = values

    def __getitem__(self, key):
        return Ids(self.values[key])

    def tolist(self):
        return self.values


class ConstrainedSelectionTests(unittest.TestCase):
    def test_single_excerpt_has_exactly_one_nonempty_completion(self):
        self.assertEqual(allowed_id_outputs(1), ['1'])
        self.assertEqual(set(allowed_id_outputs(1, True)), {'1', 'NONE'})
        self.assertEqual(len(allowed_id_outputs(3)), 7)
        for count in (0, 13, True, 1.5):
            with self.subTest(count=count):
                with self.assertRaises(ValueError):
                    allowed_id_outputs(count)

    def test_every_path_in_the_token_trie_is_a_valid_complete_selection(self):
        tokenizer = CharTokenizer()
        trie, longest = build_selection_trie(tokenizer, 3, True, 0)
        complete = set()
        def walk(node, prefix):
            for token, child in node.items():
                if token == 0:
                    complete.add(tokenizer.decode(prefix))
                else:
                    walk(child, prefix + [token])
        walk(trie, [])
        self.assertEqual(complete, set(allowed_id_outputs(3, True)))
        self.assertEqual(longest, max(len(text) + 1 for text in complete))

    def test_prefix_callback_handles_id_one_and_ten_without_allowing_id_eleven(self):
        tokenizer = CharTokenizer()
        trie, _ = build_selection_trie(tokenizer, 10, False, 0)
        callback = selection_prefix_fn(trie, 2, 0)
        one = callback(0, Ids([99, 100, ord('1')]))
        self.assertIn(0, one)  # ID 1 can finish here.
        self.assertIn(ord('0'), one)  # ID 10 can continue here.
        self.assertEqual(callback(0, Ids([99, 100, ord('1'), ord('0')])), [0])
        with self.assertRaisesRegex(ValueError, 'outside the selection grammar'):
            callback(0, Ids([99, 100, ord('1'), ord('1')]))

    def test_tokenizer_round_trip_is_required(self):
        class BadTokenizer(CharTokenizer):
            def decode(self, tokens, skip_special_tokens=True):
                return 'wrong'
        with self.assertRaisesRegex(ValueError, 'round-trip'):
            build_selection_trie(BadTokenizer(), 1, False, 0)

    def test_generator_sends_selection_constraint_and_requires_worker_acknowledgment(self):
        with tempfile.TemporaryDirectory() as tmp:
            generator = GemmaGenerator(tmp)
            stream = io.StringIO()
            generator.process = SimpleNamespace(stdin=stream)
            generator.responses.put(json.dumps({'output': '1', 'decoding_constraint': 'source-id-trie-v1'}))
            self.assertEqual(generator.select_ids('select an excerpt', 1), '1')
            request = json.loads(stream.getvalue())
            self.assertEqual(request['selection_constraint'], {'kind': 'source-id-trie-v1', 'candidate_count': 1, 'allow_empty': False})
            generator.responses.put(json.dumps({'output': '1'}))
            with self.assertRaisesRegex(RuntimeError, 'did not confirm'):
                generator.select_ids('select an excerpt', 1)

    def test_invalid_selection_request_is_rejected_before_loading_the_model(self):
        generator = GemmaGenerator('unused')
        with patch.object(generator, '_start') as start:
            with self.assertRaises(ValueError):
                generator.select_ids('prompt', 13)
            start.assert_not_called()

    def test_extractor_uses_the_constrained_generator_method(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            pdf = root / 'cis.pdf'
            make_pdf(pdf, TEXT)
            class Generator:
                calls = []
                def __call__(self, prompt):
                    raise AssertionError('Production ID requests must use constrained selection.')
                def select_ids(self, prompt, candidate_count, *, allow_empty=False):
                    self.calls.append((candidate_count, allow_empty))
                    return '1'
            generator = Generator()
            extract_kdes(validate_documents(pdf, pdf), root / 'out', generator,
                         section_limit=1, prompt_types=('zero-shot',), model_identity='controlled-test-double')
            self.assertEqual(generator.calls, [(1, True), (1, False)])
            self.assertIn('*Decoding Constraint*\nsource-id-trie-v1', (root / 'out/llm-output.txt').read_text())

    def test_previously_valid_numeric_cache_is_reused_with_original_mode(self):
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
                prompt = BUILDERS['zero-shot'](part, output_format='ids')
                key = hashlib.sha256(('source-selection-v1\n' + identity + '\n' + field + '\n' + prompt).encode()).hexdigest()
                (cache / f'{key}.json').write_text(json.dumps({'raw': '1', 'prompt_used': prompt, 'model_identity': identity}))
            def no_generation(prompt):
                self.fail('Valid numeric cache should have been reused.')
            extract_kdes(documents, root / 'out', no_generation, cache_dir=cache, model_identity=identity,
                         section_limit=1, prompt_types=('zero-shot',))
            log = (root / 'out/llm-output.txt').read_text()
            self.assertIn('*Cached*\nTrue', log)
            self.assertIn('*Decoding Constraint*\nunconstrained', log)


if __name__ == '__main__':
    unittest.main()
