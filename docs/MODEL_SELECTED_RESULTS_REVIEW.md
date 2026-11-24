# Review of the uploaded version 0.4.0 Mac extraction

The user applied the model-selected update, passed 103 tests on the Mac, and completed all five pairs into outputs/model-selected. This review checks that uploaded result set; it is not a new inference run.

## Verified evidence

- All 30 YAML files match an independent replay of the previously uploaded real Gemma responses.
- All 7,044 repeated response entries are validated cache hits. Original prompts and raw outputs are unchanged.
- All 3,522 exported KDEs contain only their actual model-selected requirements: 9,514 strings across repeated outputs.
- Input identities and source sections match fresh extraction of all three supplied PDFs.
- Source context and unselected-excerpt review flags are separate from primary requirements and agree with the raw responses.
- Both identical-document pairs produce identical YAMLs and no comparator differences.
- All 15 derived Hadolint rule configurations match the earlier full scans. The cached scanner results can be reused when the actual binary, input content, and configuration still match.

## Comparator results

Counts are symmetric-difference rows, not distinct semantic changes.

| Pair | Name differences | Zero-shot requirement rows | Few-shot requirement rows | Chain-of-thought requirement rows |
| --- | ---: | ---: | ---: | ---: |
| v0-v1 | 2 | 27 | 24 | 23 |
| v0-v2 | 3 | 31 | 29 | 26 |
| v1-v2 | 1 | 4 | 5 | 3 |
| v1-v1 | 0 | 0 | 0 | 0 |
| v2-v2 | 0 | 0 | 0 | 0 |

Changed-document pairs yield NO MAPPING FOUND; identical pairs yield NO DIFFERENCES FOUND. Both cases request ALL rules under the assignment fallback.

## Semantic limitations

This review establishes faithful extraction of actual model selections and exact source provenance. It does not establish full semantic accuracy or complete requirement coverage. Review flags identify unselected source excerpts; they are not a count of extraction mistakes, since some unselected text is background.

- CIS 5.6: zero-shot and chain-of-thought omit the Description that contains the /lib64 addition; those styles miss that path-list change. Few-shot retains it.
- CIS 2.2: no style selects all five Remediation candidates. Selected excerpts omit some configuration settings, commands, conditions, or NET_RAW instructions depending on the style.
- KDE names are derived from PDF headings; Gemma selects requirement excerpts. This is an extractive implementation rather than free-form model generation of every field.

Human review labels from separate diagnostics are not injected into final model requirements. Extra source text is not automatically promoted into requirements to conceal omissions.

## Pending work

The 0.4.0 comparison/scanner pipeline and native Mac executable still require their own completion and verification. The published final-results archive and Mac binary are currently historical version 0.3.0 artifacts. This document does not certify submission readiness.

Full extraction validation, including all YAML hashes, is recorded in model-selected-extraction-validation.json.

Uploaded extraction archive SHA-256: 0ab863a32a75d3f259c3978e7d8818d6aa8bbf1e9d5bfacbe4a4c52340fe38f0
Code revision used: 476ffa1f62fd44d3de84d031ebb55de4b4193a8a
