"""Offline API/protocol regression with a tiny random Gemma model, not pretrained weights.

This is a generation-constraint test only. It does not perform project
extraction or substitute for google/gemma-3-1b-it in the application.
Requires the optional model dependencies. No model/tokenizer download occurs.
"""
import argparse
import contextlib
import io
import json
from pathlib import Path
import sys
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, default=Path('outputs/generation-api-check.json'))
    args = parser.parse_args(argv)
    import torch
    import transformers
    from transformers import AutoModelForCausalLM, AutoTokenizer, BatchEncoding, Gemma3TextConfig
    from proj_sec.workers import gemma_worker as worker

    class CharacterTokenizer:
        eos_token_id = 0
        pad_token_id = 0
        def encode(self, text, add_special_tokens=False):
            return [ord(char) for char in text]
        def decode(self, tokens, skip_special_tokens=True):
            return ''.join(chr(int(token)) for token in tokens if int(token) != 0)
        def apply_chat_template(self, messages, **kwargs):
            ids = torch.tensor([[72, 101, 108, 108, 111]], dtype=torch.long)
            return BatchEncoding({'input_ids': ids, 'attention_mask': torch.ones_like(ids)})

    tokenizer = CharacterTokenizer()
    torch.manual_seed(42)
    config = Gemma3TextConfig(vocab_size=128, hidden_size=32, intermediate_size=64,
        num_hidden_layers=1, num_attention_heads=4, num_key_value_heads=2, head_dim=8,
        max_position_embeddings=256, bos_token_id=1, eos_token_id=0, pad_token_id=0)
    model = AutoModelForCausalLM.from_config(config).eval()
    # Deliberately favor an invalid ID for small candidate sets. The prefix
    # constraint must override this model preference without changing weights
    # in the real application. This modification exists only in this test.
    bias = torch.zeros(config.vocab_size)
    bias[ord('9')] = 1000.0
    model.lm_head.bias = torch.nn.Parameter(bias)
    inputs = tokenizer.apply_chat_template([])
    with torch.inference_mode():
        unconstrained = model.generate(**inputs, max_new_tokens=2, do_sample=False,
                                       eos_token_id=0, pad_token_id=0)
    baseline = tokenizer.decode(unconstrained[0][inputs['input_ids'].shape[-1]:])
    assert baseline not in worker.allowed_id_outputs(1)

    cases = [(1, False), (2, False), (5, False), (10, False), (2, True)]
    requests = [{'prompt': 'Synthetic API/protocol check', 'max_new_tokens': 128,
                 'selection_constraint': {'kind': worker.SELECTION_CONSTRAINT,
                                          'candidate_count': count, 'allow_empty': empty}}
                for count, empty in cases]
    protocol = io.StringIO()
    with patch.object(AutoTokenizer, 'from_pretrained', return_value=tokenizer), \
         patch.object(AutoModelForCausalLM, 'from_pretrained', return_value=model), \
         patch.object(sys, 'argv', ['gemma_worker.py', 'synthetic-api-check', 'cpu', 'local', 'float32']), \
         patch.object(sys, 'stdin', io.StringIO(''.join(json.dumps(request) + '\n' for request in requests))), \
         patch.object(sys, 'stdout', protocol):
        worker.main()
    replies = [json.loads(line) for line in protocol.getvalue().splitlines()]
    assert len(replies) == len(cases)
    results = []
    for (count, empty), reply in zip(cases, replies):
        assert 'error' not in reply, reply
        assert reply['decoding_constraint'] == worker.SELECTION_CONSTRAINT
        assert reply['output'].strip() in worker.allowed_id_outputs(count, empty), reply
        results.append({'candidate_count': count, 'allow_empty': empty,
                        'output': reply['output'], 'allowed_completion': True,
                        'worker_constraint_acknowledged': True})
    report = {'test_scope': 'Tiny randomly initialized Gemma3ForCausalLM and character tokenizer; API/protocol regression only',
              'required_pretrained_model_tested': False,
              'runtime': {'torch': torch.__version__, 'transformers': transformers.__version__},
              'unconstrained_output_with_invalid_id_bias': baseline,
              'single_candidate_constraint_output': results[0]['output'], 'results': results}
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, indent=2) + '\n')
    print(json.dumps(report, indent=2))
    print('Generation API and worker protocol checks passed; real pretrained Mac inference remains separate.')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
