# Verified GitHub Actions execution

Repository workflows: https://github.com/mondyjackson/proj_sec/actions

The version 0.4.0 model-selected implementation passed this actual workflow:
https://github.com/mondyjackson/proj_sec/actions/runs/45441968501

The run tested commit 476ffa1f62fd44d3de84d031ebb55de4b4193a8a.
All 103 tests passed in 12.691 seconds, including real Hadolint integration.
The Linux job built the native Linux executable, checked its version and a
comparison command, and uploaded a permissions-preserving archive and checksum.
The user's Mac separately passed all 103 tests in 8.374 seconds and its native
0.4.0 executable passed real Gemma smoke-model; see MAC_EXECUTABLE.md.

Every subsequent push/PR also runs the full workflow. Use the workflows link
above to inspect the final published commit's test logs and Linux artifact.
Artifacts are named test-results and proj-sec-linux-x86_64. They contain the
actual unittest transcript and Linux tar archive/CHECKSUMS.txt respectively.

The initial historical version 0.3.0 run is retained separately:
https://github.com/mondyjackson/proj_sec/actions/runs/45426078503
Its unmodified 97-test artifact is preserved as github-actions-test-results.txt;
it is historical evidence, not the current 103-test transcript.

The workflow runs on push, pull_request, and manual dispatch. Local git pull
does not create a native GitHub Actions event. Use scripts/pull_and_test.py
for tests after successful local pulls, including already-up-to-date pulls.
The optional post-merge hook has narrower merge/fast-forward and virtualenv
coverage, as documented in README.md.
