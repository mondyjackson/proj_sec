# Model-selected requirements, version 0.4.0

The primary KDE requirements now contain exactly the actual Gemma-selected
source excerpts. Deterministic inclusion of complete Description/Remediation
blocks has been removed. Source headings still supply KDE names; Python copies
selected text and serializes YAML. This is extractive selection, not free-form
model generation of all names and requirements.

## Why this changed

The earlier implementation preserved all source context after a valid model
selection. Its audit distinguished that context from the original model output,
but the exported requirements were not exclusively selected by Gemma.
Version 0.4.0 separates those roles.

Mac diagnostics found real semantic errors. A revised 66-decision sample
matched 41 reviewed labels: zero-shot 12/22, few-shot 19/22, chain-of-thought
10/22. For "You should remove any untrusted users from the docker group",
Gemma's notes identified the action but its final constrained decision was NONE.
A small subsequent unrestricted check returned YES for that action but also YES
for the background fact "Docker considers a private registry either secure or
insecure." These observations do not establish a reliable answer-format fix.
The diagnostic prompts are not substituted for the existing production prompts.

## Output and review

- YAML requirements: only actual selected excerpts, separately for each style.
- source-context.json: complete source blocks, candidate excerpts, actual
  model selections, source hashes and locations, and unselected source IDs.
- extraction-review.json: completion status and blocks with unselected excerpts
  or no model selection. These are review items, not automatic model corrections.
- llm-output.txt and PROMPT.md: actual original requests/responses, including
  cache provenance. No new request is attributed to a reused response.

NONE in Description stays an empty model selection even when Remediation exists.
Remediation still requires a valid nonempty selection. A KDE without any
model-selected requirement fails instead of being filled from source.
Partial legacy JSON selections also stay partial; their omitted context is
available only in the supplemental source file.

Unselected excerpts can be irrelevant background or genuine missed obligations.
Selecting every excerpt is also not proof of semantic accuracy. The review report
does not certify full coverage. In particular, if Gemma omits the Description
containing /lib64, the comparator may miss that change; it is not silently repaired.

## Reuse and regeneration

The production prompts, model settings, and raw-response cache namespaces have
not changed. Matching genuine responses can be revalidated and reused.
Old cached included-source metadata is ignored; requirements are recomputed
from each raw response under the model-selected-only policy.

Keep historical version 0.3.0 outputs separately. After applying the update,
generate a separate result set:

```bash
caffeinate -i python scripts/run_all_pairs.py --mode extract --device mps --dtype bfloat16 --output outputs/model-selected
```

A cache miss invokes real Gemma. This replay is not a new inference run where
responses are cached. Inspect all five extraction-review.json reports and the
actual selected requirements before deciding whether to regenerate comparisons
and scans. Prior scan CSVs must not be assumed valid for changed mappings.

The final public archive and native Mac executable now contain version 0.4.0.
All five run-mode pipelines, the user's 103 tests, and the real native Mac
version/Gemma smoke checks completed. See MODEL_SELECTED_RESULTS_REVIEW.md,
FINAL_RESULTS_REVIEW.md, and MAC_EXECUTABLE.md for evidence and limitations.
No rubric score or full-document accuracy is established by unit tests.
