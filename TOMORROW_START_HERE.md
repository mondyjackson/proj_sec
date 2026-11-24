# Start here on your Mac

> Version 0.4.0 outputs and native Mac executable are complete. Start with [SUBMISSION.md](SUBMISSION.md) to restore the final artifacts. The setup/rerun guide below is for reproducing the work.


This package is prepared for Jackson's MacBook Air M1 (2020), 8 GB RAM.
It contains the project source, tests, three input PDFs, and setup instructions.
It is a development checkpoint; real Gemma extraction and final submission
verification are still required.

## 1. Open the project

Unzip the downloaded package. In VS Code choose File > Open Folder and select
`proj_sec`, the folder containing `main.py` and this file. Open Terminal > New
Terminal. Commands below assume that folder is the terminal's current directory.

If the prompt shows `~`, type `cd ` (including the trailing space), drag the
extracted `proj_sec` folder from Finder into Terminal, then press Return.
Check the folder with:

```bash
pwd
ls main.py requirements-core.txt
```

## 2. Create and activate a native Python environment

You already have Conda. Run these one at a time:

```bash
conda create -n proj-sec python=3.12 pip -y
conda activate proj-sec
python --version
python -c "import platform; print(platform.machine())"
```

Expected: Python 3.12.x and `arm64`. Your prompt should start with `(proj-sec)`.
If an existing environment prevents creation, activate it and run the two checks.
If the architecture says `x86_64`, stop here and share that output so we can
switch to native Apple Silicon Python before installing PyTorch.

In VS Code press Cmd+Shift+P > Python: Select Interpreter and choose the
`proj-sec` Conda environment.

## 3. Install the core and check the inputs

```bash
python -m pip install -r requirements-core.txt
python main.py doctor
python scripts/run_all_pairs.py --mode prepare
```

The prepare command validates all five assigned PDF pairs without loading a
model. The PDFs are already in `data/`. Expected recommendation counts are
117 for v0, 117 for v1, and 118 for v2. No requirement YAMLs are claimed by this
preparation step.

## 4. Set up the pinned scanner

On Apple Silicon, use Homebrew's native Hadolint 2.15.1 build:

```bash
brew install hadolint
hadolint --version
HADOLINT_BIN="$(command -v hadolint)" python -m unittest discover -s tests -v
```

Supported scanner versions are exactly 2.12.0 and 2.15.1, each with a separate
upstream default-severity catalog. If Homebrew installs another version, stop
and check compatibility before scanning. The older 2.12.0 Intel Mac binary
crashed during its version check on this Mac; do not rerun that installer here.
Other platforms can continue to use the checksum-verified 2.12.0 installer.

The five-pair runner prefers Hadolint on PATH, then falls back to tools/hadolint
(or tools/hadolint.exe on Windows). An explicit --hadolint path takes priority.
The doctor's successful path lookup does not itself verify scanner execution.
Unit tests do not establish real model-output quality.

## 5. Unlock the required model

1. Sign into your own Hugging Face account.
2. Open [google/gemma-3-1b-it](https://huggingface.co/google/gemma-3-1b-it).
3. Review and accept the model access conditions. Wait for access if approval
   is required.
4. Create a read-access token in your Hugging Face account settings.

Install the model dependencies and authenticate in Terminal:

```bash
python -m pip install -r requirements-model.txt
hf auth login
```

Paste the token only into the terminal's login prompt. Do not put it in chat,
source files, or GitHub. We need your account for this step; the program does
not bypass the model's access controls.

## 6. Check the M1 backend, then run one short real extraction

```bash
python -c "import torch; print('MPS:', torch.backends.mps.is_available()); print(torch.ones(1, device='mps', dtype=torch.bfloat16))"
```

If this reports MPS available and prints a tensor, use the lower-memory
bfloat16 configuration for the required model:

```bash
python main.py smoke-model --device mps --dtype bfloat16 --max-new-tokens 256 --output outputs/model-smoke
```

The first run downloads weights and can take time. Close unnecessary large
apps on the 8 GB Mac. The smoke test must finish with `Real Gemma smoke test
passed` before starting long PDF runs. If access, memory, or backend errors
occur, keep `outputs/model-smoke/gemma-worker.log` and share the error message
without credentials. We can move Gemma inference to Colab if needed; it has
not yet been tested on this Mac.

## 7. Extract, review, and finish the five pairs

The synthetic smoke test does not establish that Gemma handles real CIS text.
First check the actual first recommendation with all three prompt styles:

```bash
python scripts/check_extraction.py --device mps --dtype bfloat16
```

This diagnostic writes sampled output to outputs/extraction-check and clearly
labels it as diagnostic-only. If it fails, inspect llm-output.txt there and
resolve the issue before a full run. If it passes, review the selected excerpts.

After the real PDF check succeeds:

```bash
python scripts/run_all_pairs.py --mode extract --device mps --dtype bfloat16
```

This runs all three prompt styles with separate Description and Remediation
requests. New requests use numbered excerpt selection with a decoding
constraint that allows only valid source-ID sequences. After a requirement is
identified, complete source Remediation is retained as explicitly logged context
to preserve commands and conditions. Description remains model-selected.
Validated responses are shared across pairs and document versions; the previous
source-block JSON cache remains reusable. The Mac selection diagnostic returned
six valid ID lists, but some omitted requirements, which is why the complete
Remediation context policy is used. Full-document inference still needs review. Check the generated
YAML requirements against the PDFs before treating them as final.

Place your instructor's original ZIP at `data/dockerfiles.zip` without
extracting it, then run:

```bash
python scripts/run_all_pairs.py --mode run --device mps --dtype bfloat16 --workers 2
```

The five pairs are v0/v1, v0/v2, v1/v2, v1/v1, and v2/v2. Model requests and
scanner results are cached for resume. Gemma closes before scanning begins.
Check each `run-status.json`, each scan manifest, and all no-difference cases.
A completed scan with input/tool errors is labeled explicitly; affected files
are not silently treated as clean.

## Still needed for submission

- Review actual Gemma outputs and the five final runs.
- Fill in BannerID, Auburn email, and any teammates in README.md.
- Publish the authorized public GitHub repository and verify successful
  Actions logs.
- Confirm the TA's operating system, build with PyInstaller on that platform,
  and verify the executable. A Linux binary is not a Mac application.
- Submit the required repository/artifacts through the course form by
  December 1, 2026, 11:59 PM CST.

## Tomorrow's first checkpoint

Get through steps 1–3 and send the Python version, architecture, and the result
of the PDF preparation command. Then we can handle model login and the smoke
test together. No private token needs to be shared.

References: [Conda environments](https://docs.conda.io/projects/conda/en/stable/user-guide/tasks/manage-environments.html),
[Gemma 3 in Transformers 4.57.1](https://huggingface.co/docs/transformers/v4.57.1/en/model_doc/gemma3),
[PyTorch MPS](https://docs.pytorch.org/docs/2.9/notes/mps.html),
[Hadolint 2.12.0](https://github.com/hadolint/hadolint/releases/tag/v2.12.0).
