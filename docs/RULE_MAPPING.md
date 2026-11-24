# CIS-to-Hadolint mapping policy

These mappings support **Hadolint 2.12.0 and 2.15.1**. A KDE name is the benchmark
recommendation title without its number and assessment suffix. The model
extracts requirement excerpts within that recommendation. Task 1 covers all
recommendations, including host and runtime controls; this table restricts
only the Task 3 mapping.

| CIS recommendation | Hadolint | Coverage and limits |
| --- | --- | --- |
| 4.1: Ensure that a user for the container has been created | DL3002 | Detects an explicitly configured final root user. It does not establish that a user exists inside the image, and does not prove compliance when USER is absent. |
| 4.3: Ensure that unnecessary packages are not installed in the container | DL3015 | Checks apt-get install's use of --no-install-recommends. This covers avoiding recommended packages, not whether every installed package is necessary. |
| 4.6: Ensure that HEALTHCHECK instructions have been added to container images | DL3057 | Checks for a missing HEALTHCHECK in the Dockerfile. It cannot prove healthcheck quality or infer every property inherited from a base image. This rule is ignored by default upstream, so the scan enables it explicitly. |
| 4.9: Ensure that COPY is used instead of ADD in Dockerfiles | DL3020 | Checks ADD for local files/folders. Hadolint allows archive use cases, so this is narrower than a universal ban on ADD. |

Unlisted controls return **NO MAPPING FOUND** when no supported mapping
remains. Version pinning is not treated as proof that an image is trusted or a
package is cryptographically verified. Host auditing, runtime permissions,
image scanning, signatures, and secret detection do not gain invented rule
coverage. Hadolint 2.12.0 does not include the newer DL3064 secret rule.
Hadolint 2.15.1 includes DL3064, but this project does not add a CIS mapping
for it; it can appear in a fallback full scan.

When a requirement changes within a mapped element, run that element's
associated check. This is a documented approximation; the mapping does not
assert that Hadolint can verify every sentence in that element.

## Running selected rules

The supported Hadolint versions accept an ignore list. A temporary
configuration ignores all DL0000–DL9999 and SC0000–SC9999 IDs except the
selected IDs. Hadolint's configuration accepts textual rule IDs. This is
checked against real full and selected scans in the integration tests; the
program fails if a scan returns an unrelated rule. Parse errors are recorded in evidence and the manifest, never treated as
clean scans. DL1000 stays enabled even for selected-rule scans. No shell commands are constructed from ZIP
member names, and no Dockerfiles are executed.

For the two fallback markers, the ignore list is empty and both opt-in
DL1001 and DL3057 are enabled. Other configurable rules retain upstream
default settings; no organization-specific label schema or registry allowlist
is invented. Ignore pragmas inside a Dockerfile are disabled so input files
cannot suppress the selected checks.

## DefaultSeverity and COUNT

The CSV uses default severities from the rule catalog for the detected version, not an
overridden effective severity. DL3057 therefore reports **ignore** in
DefaultSeverity even though it is enabled as a warning for this scan.
ShellCheck findings retain the unmodified severity returned by Hadolint.
COUNT groups findings by original ZIP member path, default severity, and ID.
Clean files appear in scan-files.jsonl; they do not receive invented
zero-count finding rows.

Sources:

- https://github.com/hadolint/hadolint/tree/v2.12.0
- https://github.com/hadolint/hadolint/blob/v2.12.0/README.md
- https://github.com/hadolint/hadolint/blob/v2.12.0/src/Hadolint/Config/Configuration.hs
- https://github.com/hadolint/hadolint/tree/v2.15.1/src/Hadolint/Rule
