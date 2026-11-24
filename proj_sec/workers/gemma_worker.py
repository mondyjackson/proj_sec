"""JSON-lines worker run by the model-enabled virtual environment's Python."""
import contextlib
import itertools
import json
import sys
import traceback


SELECTION_CONSTRAINT = "source-id-trie-v1"
MAX_SELECTION_CANDIDATES = 12


def allowed_id_outputs(candidate_count, allow_empty=False):
    if (isinstance(candidate_count, bool) or not isinstance(candidate_count, int)
            or not 1 <= candidate_count <= MAX_SELECTION_CANDIDATES):
        raise ValueError("Selection candidate count must be between 1 and 12")
    if not isinstance(allow_empty, bool):
        raise ValueError("allow_empty must be a boolean")
    outputs = [",".join(map(str, ids))
               for size in range(1, candidate_count + 1)
               for ids in itertools.combinations(range(1, candidate_count + 1), size)]
    if allow_empty:
        outputs.append("NONE")
    return outputs


def build_selection_trie(tokenizer, candidate_count, allow_empty, eos_token_id):
    if not isinstance(eos_token_id, int):
        raise ValueError("An EOS token is required for constrained selection")
    trie, longest = {}, 0
    for text in allowed_id_outputs(candidate_count, allow_empty):
        tokens = tokenizer.encode(text, add_special_tokens=False)
        if (not tokens or eos_token_id in tokens
                or tokenizer.decode(tokens, skip_special_tokens=True).strip() != text):
            raise ValueError("Tokenizer cannot round-trip a canonical source-ID selection")
        longest = max(longest, len(tokens) + 1)
        node = trie
        for token in [*tokens, eos_token_id]:
            node = node.setdefault(int(token), {})
    return trie, longest


def selection_prefix_fn(trie, prompt_length, eos_token_id):
    def allowed_tokens(batch_id, input_ids):
        node = trie
        for token in input_ids[prompt_length:].tolist():
            if int(token) not in node:
                raise ValueError("Generated source-ID prefix is outside the selection grammar")
            node = node[int(token)]
        return list(node) if node else [eos_token_id]
    return allowed_tokens


def main():
    protocol = sys.stdout
    with contextlib.redirect_stdout(sys.stderr):
        import torch
        from transformers import AutoModelForCausalLM, AutoTokenizer

        torch.manual_seed(42)
        model_name = sys.argv[1]
        device = sys.argv[2]
        revision = None if sys.argv[3] == "local" else sys.argv[3]
        if device == "auto":
            device = "cuda" if torch.cuda.is_available() else (
                "mps" if hasattr(torch.backends, "mps") and torch.backends.mps.is_available() else "cpu")
        dtype_name = sys.argv[4] if len(sys.argv) > 4 else "auto"
        if dtype_name == "auto":
            dtype_name = "float16" if device == "cuda" else "float32"
        if dtype_name not in ("float32", "float16", "bfloat16"):
            raise ValueError("Unsupported model dtype")
        dtype = getattr(torch, dtype_name)
        tokenizer = AutoTokenizer.from_pretrained(model_name, revision=revision)
        model = AutoModelForCausalLM.from_pretrained(model_name, revision=revision, torch_dtype=dtype, low_cpu_mem_usage=True).to(device).eval()
        revision = getattr(model.config, "_commit_hash", None)
        selection_tries = {}
        for line in sys.stdin:
            try:
                request = json.loads(line)
                messages = [{"role": "user", "content": request["prompt"]}]
                inputs = tokenizer.apply_chat_template(messages, add_generation_prompt=True,
                            tokenize=True, return_dict=True, return_tensors="pt").to(device)
                new_tokens = int(request.get("max_new_tokens", 1024))
                length = inputs["input_ids"].shape[-1]
                context_limit = min(getattr(model.config, "max_position_embeddings", 32768), 32768)
                if length + new_tokens > context_limit:
                    raise ValueError("Prompt plus output budget exceeds Gemma's context window")
                generation_args = {"max_new_tokens": new_tokens, "do_sample": False,
                                   "pad_token_id": tokenizer.eos_token_id}
                constraint = request.get("selection_constraint")
                if constraint is not None:
                    if not isinstance(constraint, dict) or constraint.get("kind") != SELECTION_CONSTRAINT:
                        raise ValueError("Unknown source selection constraint")
                    count = constraint.get("candidate_count")
                    allow_empty = constraint.get("allow_empty", False)
                    allowed_id_outputs(count, allow_empty)  # Validate before using values as a cache key.
                    eos = tokenizer.eos_token_id
                    cache_key = (count, allow_empty, eos)
                    if cache_key not in selection_tries:
                        selection_tries[cache_key] = build_selection_trie(tokenizer, count, allow_empty, eos)
                    trie, longest = selection_tries[cache_key]
                    if new_tokens < longest:
                        raise ValueError("Output budget is too small for the allowed source-ID selections")
                    generation_args.update({"prefix_allowed_tokens_fn": selection_prefix_fn(trie, length, eos),
                                            "eos_token_id": eos, "num_beams": 1,
                                            "forced_bos_token_id": None, "forced_eos_token_id": None,
                                            "min_length": 0, "min_new_tokens": 0})
                with torch.inference_mode():
                    generated = model.generate(**inputs, **generation_args)
                tail = generated[0][length:]
                if len(tail) >= new_tokens and int(tail[-1]) not in [tokenizer.eos_token_id, tokenizer.pad_token_id]:
                    raise ValueError("Gemma output reached its token limit; extraction may be truncated")
                response = {"output": tokenizer.decode(tail, skip_special_tokens=True),
                            "revision": revision, "device": device, "dtype": dtype_name,
                            "decoding_constraint": SELECTION_CONSTRAINT if constraint is not None else "unconstrained"}
                if constraint is not None and response["output"].strip() not in allowed_id_outputs(count, allow_empty):
                    raise ValueError("Generated selection is outside the allowed source-ID language")
            except Exception as exc:
                response = {"error": str(exc)}
            protocol.write(json.dumps(response) + "\n")
            protocol.flush()


if __name__ == "__main__":
    try:
        main()
    except Exception:
        traceback.print_exc(file=sys.stderr)
        sys.exit(1)
