# Packaged version 0.4.0 submission checkpoint

Candidate source is version 0.5.0 with omission review. Follow
[docs/COVERAGE_REVIEW.md](docs/COVERAGE_REVIEW.md) to regenerate and verify the
five-pair results and native binary before replacing this checkpoint.
The restoration commands below intentionally restore the earlier 0.4.0 artifacts.

Public repository: https://github.com/mondyjackson/proj_sec

Jackson Mondy — individual submission. Contributor information is in README.md.

## Restore the completed outputs

```bash
python scripts/restore_final_results.py
```

This restores outputs/model-selected for all five assigned pairs and all three
prompt styles: 30 YAMLs, original prompts and actual Gemma response logs, separate
source-context/review files, comparison reports, mappings, scan manifests/error
inventories, and all 15 CSV paths. Identical CSV data is stored once and verified
against every recorded hash. Restored CSV copies occupy about 1.5 GB.
The helper refuses to overwrite differing files; use --output with a fresh
folder when preserving another result set.

## Restore the verified native Mac executable

```bash
python scripts/restore_macos_binary.py
./dist/proj-sec --version
```

Expected version: 0.4.0. The exact uploaded Mac archive and executable are
reconstructed from checksum-verified parts with executable permissions intact.
See docs/MAC_EXECUTABLE.md for hashes and actual Mac runtime evidence.
The executable needs Apple Silicon macOS and an activated model-enabled Python
environment for real Gemma inference. Model weights and Hadolint remain external.
Linux users can use the executable artifact from a successful GitHub Actions run.

## Verification and limits

All 103 tests passed on the user's Mac. The native version command returned
0.4.0 and real Gemma smoke-model passed on MPS/bfloat16. Actual smoke responses
are retained under docs/mac-smoke-v0.4.0. The repository workflow runs tests and
builds/smoke-tests a Linux executable; see docs/GITHUB_ACTIONS.md.

The five full pipeline runs completed using validated model/scanner caches.
Primary requirements contain only actual Gemma selections; background and
missed obligations remain possible. Source-fidelity checks do not establish
full semantic coverage. See docs/MODEL_SELECTED_RESULTS_REVIEW.md.
All 397,567 Dockerfile paths per scan are accounted for. Scan statuses explicitly
retain 2,546 parser failures and two files affected by an upstream Hadolint
exception; they are not reported as error-free scans. See docs/FINAL_RESULTS_REVIEW.md.

The instructor PDFs, Dockerfile dataset, credentials, model weights, and local
caches are not included in the public repository. Supply authorized inputs
separately for new inference/scans.

## Submit

Review the code, results, and documented limitations, then submit the repository
URL and requested deliverables through https://forms.office.com/r/fMQeqiUbK3.
The stated deadline is December 1, 2026, 11:59 PM CST. The form has not been
submitted by this preparation process. No grade or complete rubric compliance
is guaranteed by successful execution.
