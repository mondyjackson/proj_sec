# Version 0.5.0 submission handoff

Public repository: https://github.com/mondyjackson/proj_sec

Jackson Mondy, individual submission. Contributor details are in README.md.

## Restore verified outputs

```bash
python scripts/restore_final_results.py
```

This reconstructs the exact verified outputs/coverage-final layout: all five
assigned pairs, all three prompt styles, 30 YAMLs, actual initial/review prompts
and raw responses, source-context and review metadata, difference/mapping
reports, scan manifests/status/error inventories, and all 15 scan CSV paths.
Identical CSV data is stored once in the compact archive and restored to every
original output path. The restore helper checks hashes, preserves matching
files, and refuses to overwrite differing files. Use --output with a fresh
folder to retain another result set. CSV copies occupy about 1.5 GB.

## Restore the native Apple Silicon executable

```bash
python scripts/restore_macos_binary.py
./dist/proj-sec --version
```

Expected version: 0.5.0. The helper reconstructs the exact uploaded archive and
executable, checks all hashes, and restores mode 0755. See docs/MAC_EXECUTABLE.md
for artifact hashes and native smoke evidence. The binary requires Apple Silicon
macOS. Activate a model-enabled Python environment for real Gemma inference;
weights, authentication, and Hadolint remain external. Linux users can download
the executable artifact from the current successful GitHub Actions run.

## Verification and limits

The source passed 122 local tests, including real Hadolint checks. All five
integrated Mac pipeline runs were independently checked against the recorded
Gemma responses and supplied PDF source. All 30 YAMLs and 45 comparison/mapping
reports reproduce the verified result. The real native binary smoke response
is retained in docs/mac-smoke-v0.5.0. Independent binary inspection found exact
agreement with all 12 reviewed frozen project modules and the external worker.

All action and qualifier excerpt occurrences in the assistant-reviewed
Description/Remediation reference are covered by all three styles. This is an
in-sample exact-text coverage measure, not instructor gold labels, independent
semantic accuracy, a grade prediction, or a claim about every PDF field.
Baseline background remains. See docs/COVERAGE_REVIEW.md and the linked audit
JSONs. Task 1 still uses PDF headings for KDE names and source-ID selection.

All 397,567 Dockerfile paths per scan are accounted for. Each scan explicitly
retains 2,546 parser failures and two files affected by the same reproducible
upstream Hadolint exception. The CSVs are unchanged verified scanner results,
not claims of error-free scans. See docs/FINAL_RESULTS_REVIEW.md.

The instructor PDFs, Dockerfile dataset, credentials, model weights, and local
caches are excluded from the repository. Supply authorized inputs separately
for new inference and scans. The literal local git pull requirement is handled
by the documented helper/hook; GitHub Actions has no local-pull event. See
README.md for execution and docs/RULE_MAPPING.md for conservative rule mapping.

## Submit

Review the source, outputs, and limitations, then submit the repository URL and
requested deliverables through https://forms.office.com/r/fMQeqiUbK3.
The stated deadline is December 1, 2026, 11:59 PM CST. This preparation has not
submitted the form.
