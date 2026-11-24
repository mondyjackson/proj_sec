# Verified version 0.5.0 Apple Silicon executable

The user built the executable on native macOS ARM64 in the proj-sec Conda
environment and produced a valid real-model smoke result with:

```bash
./dist/proj-sec smoke-model --model-python "$CONDA_PREFIX/bin/python" --device mps --dtype bfloat16 --max-new-tokens 256 --output outputs/binary-smoke-0.5.0
```

The uploaded binary was independently inspected as an ARM64 Mach-O. Its frozen
version is 0.5.0. All 12 bundled project-module code objects and the external
Gemma worker agree with the reviewed source. See NATIVE_V0.5_VALIDATION.json.
Native execution occurred on the user's Mac; Linux inspection did not execute
ARM64 machine code.

Actual prompt, raw Gemma response, parsed result, runtime metadata, and worker
log are retained in mac-smoke-v0.5.0/. The runtime records google/gemma-3-1b-it,
pinned revision dcc83ea841ab6100d6b47a070329e1ba4cf78752, MPS, and bfloat16.
The raw log is written before parsing and therefore retains its initial
unvalidated status; model-smoke.json is written only after successful parsing
and source validation. The recorded response was independently revalidated.

Archive: proj-sec-macos-arm64-v0.5.0.tar.gz (28,851,444 bytes).
SHA-256: 69c1744b15384cb0892635dcd8cc91857783f78d7447e50143d9177daccea7b2

Executable: proj-sec (29,255,216 bytes), ARM64 Mach-O, mode 0755.
SHA-256: 75cd1e6b2ed37c5eece946d541d3c1e6660f1fdd76ea1c4cf6dbeac852d399ee

```bash
python scripts/restore_macos_binary.py
./dist/proj-sec --version
```

The exact original archive is retained in three raw parts under submission/macos.
The helper validates every part, archive, and executable hash and refuses to
overwrite differing files. Real inference uses an external activated model-enabled
Python interpreter. Weights, credentials, and Hadolint are not embedded.
Use the GitHub Actions Linux artifact on Linux. The TA operating system is unknown.
