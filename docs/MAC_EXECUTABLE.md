# Verified version 0.4.0 Apple Silicon executable

The user built the executable on native macOS ARM64 in the proj-sec Conda
environment. The built executable returned 0.4.0 and this real-model check passed:

```bash
./dist/proj-sec smoke-model --model-python "$CONDA_PREFIX/bin/python" --device mps --dtype bfloat16 --max-new-tokens 256 --output outputs/binary-smoke-0.4.0
```

The uploaded model-runtime.json records google/gemma-3-1b-it, pinned revision
dcc83ea841ab6100d6b47a070329e1ba4cf78752, MPS, and bfloat16. Actual raw prompt,
model response, runtime metadata, and parsed smoke output are retained in
mac-smoke-v0.4.0/. Runtime execution was performed on the user's Mac; the cloud
review checked uploaded bytes and evidence and did not execute macOS code on Linux.

Archive: proj-sec-macos-arm64-v0.4.0.tar.gz (28,836,387 bytes).
SHA-256: 6c3e9ea4641ef5c67dc1f21a5e414d9b1d7026ee879545695f224abf01b7ab26

Executable: proj-sec (29,240,192 bytes), ARM64 Mach-O, mode 0755.
SHA-256: 40d079d161e610ef8da88875faef09a5ce42de6239898cc354409b9becf6d5ae

```bash
python scripts/restore_macos_binary.py
./dist/proj-sec --version
```

The original archive is retained in three raw parts under submission/macos.
manifest.json records every part, archive, and executable checksum. The restore
helper validates all hashes and refuses to overwrite differing files.
The executable runs Gemma using an external activated model-enabled Python
interpreter; weights, authentication, and Hadolint are not embedded.
Use the Linux Actions artifact on Linux. The TA operating system is unspecified.
