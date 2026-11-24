# Submission progress

| Area | Verified | Remaining |
| --- | --- | --- |
| Extractor | Five real Gemma pair runs; three styles; 30 YAMLs; source context and actual model-response audit | No new model run needed for reviewed outputs |
| Comparator | All 15 reports independently regenerated; identical-document cases produce no differences | None for reviewed inputs |
| Executor | 397,567 paths per scan; 1,598,633 CSV rows; independent 256-file rescan matches; known input/tool failures documented | Retain the explicit error limitations |
| Tests | 97 tests passed on the user's Mac and on GitHub with real Hadolint integration; actual CI log retained | None for the published source |
| Repository | Contributor details, public repository, final results bundle, and successful Actions artifacts verified | None for source publication |
| Executable | Linux PyInstaller build and CLI smoke checks passed on GitHub | Complete and smoke-test native Mac build; confirm grading-platform compatibility |

See FINAL_RESULTS_REVIEW.md for current data validation. Historical evidence
such as DATASET_VALIDATION.md describes the earlier Hadolint 2.12.0 baseline;
it does not replace the final Mac Hadolint 2.15.1 results.
