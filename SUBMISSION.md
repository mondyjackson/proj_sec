# Submission handoff

Public repository: https://github.com/mondyjackson/proj_sec

## Contents

- Required extractor, comparator, and executor functions and their tests.
- All three prompt styles and actual real Gemma response logs.
- All five assigned input pairs, including v1/v1 and v2/v2, in the final result bundle.
- Complete contributor details in README.md.
- Pinned Python requirements, local pull/test helpers, and GitHub Actions.
- Actual successful GitHub test logs and a Linux PyInstaller artifact.
- The user's runtime-tested native Mac PyInstaller archive and checksum manifest.

The instructor PDFs, Dockerfile dataset, model credentials, and model weights
are not committed. Supply authorized inputs separately when rerunning.

## Restore the reviewed outputs

```bash
python scripts/restore_final_results.py
```

This restores the 30 YAMLs, actual prompts/LLM logs, comparator/mapping reports,
scan statuses/error inventories, and all 15 identical, hash-verified CSV paths.
The CSV copies use about 1.5 GB. No model or scanner rerun is needed to restore them.

## Restore the verified Mac executable

```bash
python scripts/restore_macos_binary.py
./dist/proj-sec --version
```

The helper reconstructs dist/proj-sec and dist/proj-sec-macos-arm64.tar.gz
with the original verified bytes and executable permissions. Version output is
0.3.0. See docs/MAC_EXECUTABLE.md for the real Gemma smoke-test evidence and
full checksum. Linux users should select the Linux executable artifact from
the successful Actions run linked in docs/GITHUB_ACTIONS.md.

To rerun the complete pipeline, follow README.md for the external model-enabled
Python environment, Gemma authentication, input paths, and Hadolint setup.

## Known result limitations

All original 397,567 Dockerfile paths are accounted for in every scan. The
final outputs explicitly retain 2,546 DL1000 parser failures and two files
affected by a reproducible upstream Hadolint exception. Their statuses are
completed-with-tool-errors/completed-with-scan-errors, not error-free scans.
See docs/FINAL_RESULTS_REVIEW.md for provenance, counts, and independent checks.
Actual model selections and source context added by code remain distinguished.

## Final user step

Review the repository and submit its URL and requested deliverables through
the instructor's form: https://forms.office.com/r/fMQeqiUbK3

The supplied assignment states December 1, 2026, 11:59 PM CST as the deadline.
The submission form has not been submitted by this project preparation process.
