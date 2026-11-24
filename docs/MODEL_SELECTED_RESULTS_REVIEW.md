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

## Completed final pipeline and executable

All five version 0.4.0 run-mode pipelines subsequently completed. All 15
scans reused 178,527 cached unique results with zero new scanner executions;
CSV hashes match the earlier independently audited bytes. Known parse/tool
errors remain explicit. The native Mac executable returned 0.4.0 and passed
real Gemma smoke-model on MPS/bfloat16. Final artifacts are bundled in the
repository. See FINAL_RESULTS_REVIEW.md and MAC_EXECUTABLE.md.

Full extraction validation, including all YAML hashes, is recorded in
model-selected-extraction-validation.json; complete final validation is in
final-v0.4.0-validation.json. These checks do not certify complete semantic accuracy.
