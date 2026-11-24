# Verified native Mac executable

The supplied PyInstaller executable is version 0.3.0 for Apple Silicon macOS.
The user built it from the reviewed project in the proj-sec Conda environment.
The user then ran:

```text
./dist/proj-sec --version
0.3.0

./dist/proj-sec smoke-model --model-python "$CONDA_PREFIX/bin/python" --device mps --dtype bfloat16 --max-new-tokens 256 --output outputs/binary-smoke
Real Gemma smoke test passed
```

This verifies real Gemma invocation through the frozen executable with the
existing model-enabled Python environment. It is separate from the earlier
Python source runs and the GitHub Linux binary smoke checks.

The uploaded archive was independently inspected on Linux without executing
the Mac program. Its checksum matches the user's shasum output, it contains
exactly one regular file named proj-sec, its permissions are 0755, and its
Mach-O header identifies the ARM64 CPU type. Mac runtime claims above come
from the user's terminal output; no Mac execution is claimed on Linux.

| Property | Value |
| --- | --- |
| Archive | proj-sec-macos-arm64.tar.gz |
| Archive bytes | 28,837,069 |
| Executable bytes | 29,240,880 |
| Architecture | macOS ARM64 |
| Mode | 0755 |
| Version | 0.3.0 |
| Real Gemma smoke test | Passed, MPS/bfloat16 |

Archive SHA-256:

```text
8a8fddc8deeab94112ea208d3354fec00cb5355daa8136a7dfc7f757b4586a76
```

The exact archive bytes are stored in three parts under submission/macos/.
To restore both the original archive and its executable from a fresh checkout:

```bash
python scripts/restore_macos_binary.py
./dist/proj-sec --version
```

The helper checks every part, the complete archive, and the executable against
the recorded SHA-256 values. It restores the executable bit and refuses to
overwrite differing files. It does not run the restored program.

For new model inference, activate a model-enabled Python environment and
authenticate for the required Gemma model as documented in README.md. For a
Python virtualenv, pass --model-python "$VIRTUAL_ENV/bin/python"; the tested
Conda command is shown above. The binary keeps model packages in that external
environment. Use an appropriate supported Hadolint executable for scans.

The Mac executable is not a Linux or Windows binary. The successful GitHub
Actions run also supplies a Linux x86_64 executable with checksums. The TA's
operating system was not specified; select the matching platform artifact.
