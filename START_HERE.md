# Start here

> Version 0.4.0 outputs and native Mac executable are complete. Start with [SUBMISSION.md](SUBMISSION.md) to restore the final artifacts. The setup/rerun guide below is for reproducing the work.


Read README.md for installation, execution, and contributor details.
All five real Mac pipeline runs have been reviewed; their outputs are bundled
under submission/. Restore them with `python scripts/restore_final_results.py`.
See docs/FINAL_RESULTS_REVIEW.md for actual results and known Hadolint errors.

The public checkout does not contain the instructor PDFs or Dockerfile dataset.
Place authorized copies in data/ to rerun the pipeline. The private source
handoff included the PDFs. TOMORROW_START_HERE.md is the earlier Mac setup guide;
its installation steps do not need repeating on the prepared Mac.

GitHub Actions passed all 97 tests and built the Linux executable; see
docs/GITHUB_ACTIONS.md. The native Mac executable also passed its version and
real Gemma smoke checks; restore it with `python scripts/restore_macos_binary.py`.
Use SUBMISSION.md for the final handoff and docs/MAC_EXECUTABLE.md for checksums.
