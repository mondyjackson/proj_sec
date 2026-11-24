# Restrict Gemma to valid source-ID sequences

## Observed failure

The Mac run passed CIS 2.2 after switching to numbered selection, then stopped
at 2.3/Remediation. That block has one excerpt containing the logging-level
configuration and command. An unconstrained response was empty or outside the
valid 1..1 selection range after retries. Prior validated blocks remained cached.

## Decoder constraint

Fresh production ID requests now use Transformers' prefix_allowed_tokens_fn.
The worker constructs a token trie containing every nonempty ascending subset
of the valid IDs, expressed as comma-separated numbers. Description also allows
NONE. The model's logits still determine the chosen valid completion; the trie
excludes nonexistent IDs, repeated/backward IDs, prose, and malformed output.
A one-excerpt Remediation request has one valid completion: 1.

The worker validates tokenizer encode/decode round trips, includes an explicit
EOS transition, and checks the final decoded output against the allowed
language. It caches tries by candidate count and empty-selection policy.
Counts are limited to 12 to bound enumeration. The supplied PDFs' audited
maximum is 10 excerpts in any source block. Output budgets must accommodate
the longest permitted completion. Failures produce explicit errors.

The frontend requires the worker to acknowledge source-id-trie-v1. Audit,
model-runtime, and new cache metadata record the actual decoding mode.
Prompt styles and source excerpt construction are unchanged. This constrains
output syntax; it does not prove a model choice is semantically complete.
Source-context coverage and manual review still apply. The later Description
coverage correction is documented in DESCRIPTION_CONTEXT.md.

## Existing work and cache identity

New constrained requests use source-selection-trie-v1 cache keys. Valid
source-selection-v1 numeric entries and source-block-v1 JSON entries remain
fallbacks and are revalidated. Their original unconstrained mode and actual
prompts are preserved. The base model/precision identity stays unchanged for
those lookups. Completed responses need not be regenerated. The model files,
Hugging Face authentication, and installed package versions are unchanged.

## Verification and limits

All code/scanner regression tests pass. An additional offline test exercises
the complete worker protocol and actual generate() API using Torch 2.9.0+cpu,
Transformers 4.57.1, a tiny randomly initialized Gemma3ForCausalLM, and a
character tokenizer. A deliberate logit bias produced invalid 99 without the
constraint and valid 1 for a single-excerpt request with the constraint. Other
candidate counts and the Description NONE option were also checked.

This API test is not an evaluation of the required pretrained model or MPS.
Subsequently, the supplied Mac results confirmed completed extraction for all
five assigned pairs with the required pretrained model on MPS/bfloat16. Source
review identified a separate Description-coverage issue; it is corrected and
verified by replaying the supplied responses, as described in DESCRIPTION_CONTEXT.md.
Production extraction continues
to use google/gemma-3-1b-it; there is no random-model extraction fallback.
The optional regression can be reproduced with model dependencies installed:

```bash
python scripts/check_generation_api.py
```

Reference:
https://huggingface.co/docs/transformers/v4.57.1/en/main_classes/text_generation#transformers.GenerationMixin.generate
