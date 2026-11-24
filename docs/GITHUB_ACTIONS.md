# Verified GitHub Actions execution

Repository: https://github.com/mondyjackson/proj_sec

Successful workflow run:
https://github.com/mondyjackson/proj_sec/actions/runs/45426078503

The push-triggered run tested source commit
35d9b1a1d6ded1708adaf049757ebbc9853bfdf0. Both jobs completed successfully:

- `test`: 97 tests passed in 7.802 seconds, including real Hadolint integration.
- `build-linux`: installed pinned build dependencies, built the PyInstaller
  executable on Ubuntu 22.04, ran its version command and a comparison smoke
  check, then packaged and uploaded the executable with a checksum.

The exact `test-results.txt` artifact was downloaded and its archive SHA-256
verified. Its unmodified contents are retained in github-actions-test-results.txt.
This records actual GitHub execution, separately from local or Mac test runs.

Workflow artifacts on that run:

| Artifact | GitHub artifact ID | ZIP bytes |
| --- | ---: | ---: |
| test-results | 14936767314 | 3,468 |
| proj-sec-linux-x86_64 | 14935574951 | 52,143,530 |

The Linux artifact contains proj-sec-linux-x86_64.tar.gz and CHECKSUMS.txt.
Extracting the tar archive preserves the executable bit. It is a Linux x86_64
binary; a native Mac executable must be built and checked separately on macOS.

GitHub reported artifact retention through February 22, 2027. The preserved
test log and linked workflow provide evidence after transient console output.
The workflow also runs on future pushes or pull requests and supports manual
dispatch. Local git-pull testing uses the documented helper/hook because
GitHub does not receive local pull events.
