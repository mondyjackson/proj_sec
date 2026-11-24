# Native Mac Hadolint update

Hadolint 2.15.1 starts successfully on Jackson's Mac using Homebrew.
Full Mac scan/test execution still needs local verification.

The scanner accepts exactly stable 2.12.0 and 2.15.1 and loads a separate
catalog extracted from each version's tagged upstream rule source. In 2.15.1,
DL3005 is removed, DL3062 through DL3065 and DL3067 default to warning, and
DL3066 defaults to info. Existing rule severities otherwise match 2.12.0.
DL3057 and DL1001 remain explicitly enabled, preserving upstream default
severity in CSV output. Selected scans continue to exclude unrelated rules.

The five-pair runner prefers a Hadolint executable on PATH, then the local
tools directory; explicit --hadolint still takes priority. Unsupported versions
are rejected before any scan. Cache identities already include binary content
and configuration hashes, so old scanner findings cannot be reused by a
new binary.

Original Linux 2.12.0 baseline reports are historical evidence, not 2.15.1
final outputs. Gemma work and submission requirements remain unchanged.

Upstream sources:
- https://github.com/hadolint/hadolint/tree/v2.12.0/src/Hadolint/Rule
- https://github.com/hadolint/hadolint/tree/v2.15.1/src/Hadolint/Rule

After applying the update, run from the folder containing main.py:

```bash
HADOLINT_BIN="$(command -v hadolint)" python -m unittest discover -s tests -v
```
