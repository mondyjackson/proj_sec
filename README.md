# Proj Sec

**Current submission: version 0.5.0.** All five assigned pipeline runs and the native Apple Silicon executable are verified. The default pipeline uses real Gemma omission review with a language-evidence gate. Only actual model selections can enter the final requirements.

Public repository: https://github.com/mondyjackson/proj_sec

Restore the verified five-pair outputs into outputs/coverage-final, including all 30 YAMLs and all 15 scan CSV paths:

```bash
python scripts/restore_final_results.py
```

The exact uploaded result archive is stored as checksum-verified parts under [submission/results](submission/results). See [SUBMISSION.md](SUBMISSION.md) for the complete handoff, [submission/README.md](submission/README.md) for archive details, and [docs/COVERAGE_REVIEW.md](docs/COVERAGE_REVIEW.md) for exact-text coverage and limitations. The review covers the parsed Description and Remediation fields against an assistant-reviewed reference; it does not establish independent semantic accuracy. Some initial background selections remain.

**M1 Mac setup:** start with [TOMORROW_START_HERE.md](TOMORROW_START_HERE.md).

Compare CIS Docker Benchmark requirements with **google/gemma-3-1b-it**, then
map relevant changes to Hadolint checks and export scan results. Supported
scanner versions are 2.12.0 and 2.15.1, with version-specific rule catalogs.

The remote model revision is pinned to
`dcc83ea841ab6100d6b47a070329e1ba4cf78752` for repeatable cache identities.

**Status:** all five real Gemma extraction runs and all 15 comparator/scanner
outputs have been reviewed. The final Hadolint 2.15.1 scans account for 397,567
Dockerfiles, including 2,546 parser failures and two files sharing a reproducible
upstream runtime error. They are explicitly flagged, not reported as clean scans.
See docs/FINAL_RESULTS_REVIEW.md. Actual GitHub Actions tests and the Linux
build succeeded; see [docs/GITHUB_ACTIONS.md](docs/GITHUB_ACTIONS.md). Native
Mac version and real Gemma worker checks also passed; see [docs/MAC_EXECUTABLE.md](docs/MAC_EXECUTABLE.md). The older 2.12.0 dataset baseline is
separate historical evidence in docs/DATASET_VALIDATION.md.

## Team

Individual submission; no teammates.

| Name | BannerID | University email |
| --- | --- | --- |
| Jackson Mondy | 904314490 | jbm0138@auburn.edu |

## Environment

The core and scanner were checked on Linux x86_64 with Python 3.12. The
user completed real Gemma extraction on native Apple Silicon Python 3.12.16,
using MPS/bfloat16 for initial extraction and MPS/float32 for omission review,
with sequential model workers in the proj-sec Conda environment. Authenticated model
access is required for new inference. Use Python 3.12 for the supplied core
dependency lock.

Create and activate a virtual environment:

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.txt
```

On Windows use `py -3.12 -m venv .venv` and activate with
`.venv\Scripts\Activate.ps1` in PowerShell. Use `python` for subsequent commands.

For core development without model packages, install requirements-core.txt
instead. For a CPU-only Linux PyTorch installation, follow the platform-specific
instructions at https://pytorch.org/get-started/locally/ rather than downloading
unneeded CUDA dependencies. Check that the resulting version matches the pin.

Install the pinned Hadolint release:

```bash
python scripts/install_hadolint.py --output tools
python main.py doctor --hadolint tools/hadolint
```

Windows uses tools/hadolint.exe. On Apple Silicon, use the native Homebrew
Hadolint 2.15.1 build instead:

```bash
brew install hadolint
hadolint --version
python main.py doctor --hadolint hadolint
```

Use --hadolint hadolint in direct scan/run commands on this Mac instead of
--hadolint tools/hadolint. The five-pair runner now prefers Hadolint on PATH
and falls back to the tools directory only when none is found. See the Mac guide.
Existing 2.12.0 scan evidence stays valid for that version; rerun final scans
with the chosen binary. The scanner cache includes the binary's SHA-256.

## Gemma access

Log into Hugging Face and accept the usage conditions at
https://huggingface.co/google/gemma-3-1b-it. Authenticate from the active virtual
environment with `hf auth login`. Do not commit credentials. If you already
have the model locally, supply --model-path with that copy of the required model.

Before a full extraction, run one short real-model check:

```bash
python main.py smoke-model --output outputs/model-smoke
```

This downloads/loads the real model. Errors are recorded in gemma-worker.log.
The application does not substitute synthetic responses when access fails.

The smoke-model command uses one short synthetic input. Before a full PDF run,
check the actual first CIS recommendation with all three prompt styles:

```bash
python scripts/check_extraction.py --device mps --dtype bfloat16
```

This diagnostic samples one recommendation and writes to outputs/extraction-check.
It is not a complete assignment output. Valid results share the normal cache.
New requests ask Gemma to select numbered source excerpts. The production
worker constrains generation to valid ID sequences using a token trie;
Description also permits NONE. Python copies the selected text and serializes
YAML, so quoted settings and commands do not need to be reproduced inside
model-generated JSON. The decoder mode is recorded in the runtime and audit.
See docs/CONSTRAINED_SELECTION.md for the implementation and evidence limits. Description and Remediation are
processed separately for all three prompt styles.

Only excerpts actually selected by Gemma are exported in `requirements`.
Complete Description and Remediation text is recorded separately in
`source-context.json`. It is not input to requirement comparison.
`extraction-review.json` flags source excerpts not selected by the model;
these may be background or missed obligations and require human review.
The initial NONE response and partial selections remain unchanged in their audit.
The default omission-review stage can add excerpts only when Gemma actually
selects them in a recorded review response and the language-evidence gate accepts
them. Python never fills an omission solely from a reference answer or source text.
See [docs/COVERAGE_REVIEW.md](docs/COVERAGE_REVIEW.md) for the current policy and
[docs/MODEL_SELECTED_REQUIREMENTS.md](docs/MODEL_SELECTED_REQUIREMENTS.md) for the
version 0.4.0 baseline policy.

KDE names come from PDF headings. Every original model response remains in the
audit, alongside source provenance, selected IDs, included IDs, and coverage
policy. A valid ID list proves source fidelity; it does not prove the model
selected every obligation. Full extraction and source review remain required.

Existing validated JSON responses can be reused through the legacy cache key.
Their actual original prompts and raw outputs stay in the audit, and the same
initial model-selected policy applies before omission review. Invalid responses are not cached.
The earlier bounded JSON punctuation repairs are for legacy responses only.

## Inputs and execution

Put the three PDFs and the instructor's Dockerfile ZIP in data/. Keep them
outside the public repository. The application accepts an archive regardless
of whether the instructor's downloaded name is dockerfiles.zip or dokcerfiles.zip.

Validate PDFs and inspect section counts before model work:

```bash
python main.py prepare data/docker-cis-v0.pdf data/docker-cis-v1.pdf --output outputs/preflight
```

Run extraction alone before reviewing model output:

```bash
python main.py extract data/docker-cis-v0.pdf data/docker-cis-v1.pdf --output outputs/v0-v1
```

Run the whole pipeline:

```bash
python main.py run data/docker-cis-v0.pdf data/docker-cis-v1.pdf --dockerfiles data/dockerfiles.zip --hadolint tools/hadolint --output outputs/v0-v1
```

Repeat for v0/v2, v1/v2, v1/v1, and v2/v2 with separate output directories.
Validated model responses are cached in .cache/gemma and shared across pair
folders and document versions when model identity, source field, and complete
prompt match exactly. Every cache hit is revalidated against the current source.
Constrained ID requests have a separate namespace and retain fallback access
to both previous valid numeric selections and the source-block JSON cache. Earlier combined-source cache
entries are not reused. --model-cache selects another directory. Scanner results
use .cache/hadolint.sqlite3 and are keyed by exact Hadolint binary, rule
configuration, and raw content hash. Rerunning resumes matching requests. Use a new empty --model-cache directory when changing local model weights
at the same --model-path; local weight changes are not automatically
fingerprinted. Use explicit --device and --dtype settings for repeatable runs.

The frozen executable runs Gemma through the activated virtualenv or Conda
environment's Python.
Use --model-python to select that interpreter explicitly if needed. Model weights
and Hadolint are external dependencies; the executable does not embed them.

## Outputs

The output directory contains source-context.json, extraction-review.json,
input-inventory.json, source-section JSONs,
PROMPT.md with the exact requests, llm-output.txt with the four required labeled
fields, cache/, and one directory for each prompt style. Each style directory
contains a document-named left/right YAML pair, both difference TEXT files,
hadolint-rules.txt, results.csv, raw findings, a per-file evidence log, and a scan manifest.

All three styles are run independently. Their outputs are retained and compared
separately rather than merging incompatible model responses. A run-status.json
record distinguishes incomplete work from a completed command.

Each CIS recommendation is one KDE. Code assigns its name from the source
heading without the number and Manual/Automated suffix. For each prompt style,
Gemma selects numbered excerpts from Description and Remediation independently.
Only actual selections from both fields are merged into the KDE requirements.
Both present blocks must validate; an empty Description selection is allowed,
but a Remediation response must identify a requirement before the KDE can be
exported. A final KDE must have at least one model-selected requirement.

The source splitter preserves every non-whitespace character. Programmatic
copying preserves the text of selected excerpts, including configuration quotes
and commands. Supplemental context is stored separately; it does not make the
model output more complete. A syntactically valid selection can miss an explicit
instruction or select background text. Review the actual outputs before submission.

Requirements are compared as sets, preserving case within commands. Names
ignore whitespace and letter case. The comparator writes the symmetric
difference: both removed and added requirements appear as NAME,REQU CSV tuples
without a header. Quoting protects embedded commas. This meets the tuple format;
the reports do not label the change direction.

## Tests

```bash
python -m unittest discover -s tests -v
```

For real Hadolint integration tests, put a supported binary on PATH or set
HADOLINT_BIN to its absolute path. Those integration tests are skipped when no
binary is installed. Unit tests use explicit controlled doubles, including the
extractor test; they do not establish real Gemma output quality.

See docs/REQUIREMENTS.md for one-to-one coverage of the 13 required functions
and docs/RULE_MAPPING.md for the mapping limitations and severity handling.

## GitHub Actions and local git pull

The supplied workflow runs tests on push, pull_request, and manual dispatch,
including real Hadolint tests without needing model credentials. After tests pass, a separate job builds a Linux executable and uploads it as
an artifact with a checksum. Actual test logs are also retained as an artifact.
Current run logs and platform artifacts are available in
[GitHub Actions](https://github.com/mondyjackson/proj_sec/actions).
Version 0.5.0 passed 122 local tests, including real Hadolint and restoration
checks; the transcript is in docs/coverage-review-unit-tests.txt. The native Mac
artifact is verified separately in docs/MAC_EXECUTABLE.md. See
[docs/GITHUB_ACTIONS.md](docs/GITHUB_ACTIONS.md) for current and historical CI evidence.

A local git pull is not a native GitHub Actions trigger. An optional post-merge
hook runs tests after pulls that merge or fast-forward new commits:

```bash
python scripts/enable_pull_tests.py
```

It does not run on already-up-to-date pulls or cover every rebase scenario.
For guaranteed tests after a successful pull, including up-to-date pulls, use:

```bash
python scripts/pull_and_test.py
```

The hook expects a Python virtualenv. From Conda, use the pull_and_test.py
helper so tests run with the active Conda interpreter. GitHub itself does not
receive events from a local pull; the workflow and local helper cover their
respective environments explicitly.

## Executable

To restore the exact verified Apple Silicon Mac build and original archive:

```bash
python scripts/restore_macos_binary.py
./dist/proj-sec --version
```

See [SUBMISSION.md](SUBMISSION.md) for the complete handoff, result restoration,
and matching platform artifacts. To build locally instead:


```bash
python -m pip install -r requirements-build.txt
python scripts/build.py
./dist/proj-sec --help
```

PyInstaller must run on the target operating system. A Linux binary does not
run on macOS or Windows. The core executable uses the active virtual
environment's external model worker, so keep the model requirements installed.
The source includes the worker and the build copies it into the executable.

## Submission

Deadline: **December 1, 2026, 11:59 PM CST**.
The final submission needs a public GitHub repository, actual successful CI
logs, completed team information, real output artifacts, and a verified
PyInstaller executable. No Dockerfile dataset upload is required in the repo.

Submission form: https://forms.office.com/r/fMQeqiUbK3

## Large archives and Mac memory

The scanner supports the supplied archive's 397,567 Dockerfiles, ignoring Mac
metadata. Batches and workers are bounded, duplicate SHA-256 content shares a
scan, and every original path is retained. Runtime crashes/timeouts trigger
smaller retries to isolate affected files; errors are recorded explicitly.
Other execution errors stop the run and leave its status incomplete.

Use --workers and --batch-size to tune scanning. Raw results are stored once
per content in hadolint-findings.jsonl; scan-files.jsonl maps original names to
content/status. scan-errors.jsonl lists affected paths. DL1000 appears in ALL
results; selected scans retain parse errors in evidence while limiting CSV
rows to the selected rules. CSV COUNT remains per original file.

The model supports --dtype auto, float32, float16, or bfloat16. Precision is part
of its cache identity. On the M1, test MPS bfloat16 support before choosing the
lower-memory option. Supplied Mac results confirm all five extraction pairs
completed using the required pretrained Gemma model on MPS/bfloat16. The
Description-context correction was verified separately by replaying those
recorded responses without new inference. Gemma is closed
before scanning to avoid holding the model and large dataframes simultaneously.

Use scripts/run_all_pairs.py --mode prepare to inventory all five pairs,
--mode extract to produce/review YAMLs, and --mode run to finish the pipeline.
The default mode is prepare and does not download or run Gemma.

The source handoff can be packaged with `python scripts/package_project.py`.
The optional --include-linux-binary flag includes the locally built executable;
it does not make that binary runnable on macOS. GitHub Actions also prepares
a Linux artifact after successful tests once the repository is published.
