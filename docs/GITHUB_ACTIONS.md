# GitHub Actions validation

Current workflows and actual logs: https://github.com/mondyjackson/proj_sec/actions

The version 0.5.0 implementation runs the full test suite, including real
Hadolint integration, on push, pull_request, and manual dispatch. A dependent
Linux job builds the native executable, checks its version and comparison
command, and uploads a permissions-preserving archive with a checksum.

The complete local 122-test transcript is retained in
coverage-review-unit-tests.txt. The actual GitHub transcript and platform
archive are available from the successful final published commit's workflow.
Artifacts are named test-results and proj-sec-linux-x86_64. These contain
actual execution output rather than a hand-written passing-test summary.
Native Mac 0.5.0 code and real Gemma smoke evidence are separately verified in
MAC_EXECUTABLE.md and mac-smoke-v0.5.0/.

Historical successful checkpoints:

- Version 0.5.0 initial implementation, 119 tests and Linux build:
  https://github.com/mondyjackson/proj_sec/actions/runs/45493270353
- Version 0.4.0 model-selected implementation, 103 tests and Linux build:
  https://github.com/mondyjackson/proj_sec/actions/runs/45441968501
- Version 0.3.0 initial implementation, 97 tests:
  https://github.com/mondyjackson/proj_sec/actions/runs/45426078503

A local git pull does not produce a GitHub Actions event. Use
scripts/pull_and_test.py for tests after successful local pulls, including
already-up-to-date pulls. The optional post-merge hook has narrower
merge/fast-forward and virtualenv coverage, as documented in README.md.
