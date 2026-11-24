# Gemma response-format update

Observed on the real first CIS recommendation: Gemma returned a shortened name
and omitted the requirements field on both original attempts. The prior
synthetic smoke test had passed but did not exercise this real input.

All three prompts now end with a JSON response schema that includes the exact
heading and a mandatory nonempty requirements array. Zero-shot retains no
worked extraction examples. The validator still rejects renamed elements,
missing requirements, paraphrases, and source-unmatched excerpts. No fields
are filled in automatically when Gemma omits them.

Retries reiterate the exact response shape and validation error without
embedding a bad response for the small model to imitate. There are up to two
correction attempts. Exact prompts and raw responses remain in the audit
files even if extraction stops. Changed prompts naturally have new cache keys;
there is no need to delete existing valid caches or redownload model weights.

scripts/check_extraction.py samples the first real recommendation with all
three styles, uses the actual Gemma worker, and labels the output as diagnostic
only. Its output is separate from outputs/final. The five-pair run remains
complete by default and now prints per-recommendation progress.

Unit tests use explicit controlled doubles. Passing them cannot establish that
the revised prompt works with real Gemma; the local diagnostic must verify it.
