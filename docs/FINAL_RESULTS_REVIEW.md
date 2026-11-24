# Review of the final Mac pipeline outputs

This review uses the supplied Proj_Sec_Final_Review.zip, produced after applying
the Description-context correction and running all five pairs in run mode.
It is distinct from the historical Hadolint 2.12.0 baseline. The final scanner
is native Mac Hadolint 2.15.1; Gemma is google/gemma-3-1b-it with MPS/bfloat16.

## Extractor and comparator

All 30 YAMLs have the expected recommendation counts: v0 has 117, v1 has 117,
and v2 has 118. Across the repeated pair/style outputs, they contain 3,522 KDEs
and 12,510 requirement strings. All 7,044 model audit entries validate.
Source headings, identifiers, model-selected excerpts, explicitly added source
context, and the exported YAMLs reconcile. Every exported requirement string
is present in the corresponding source after whitespace normalization. Both
Description and Remediation source candidates are retained under the documented
coverage policy. This is source context, not a claim of complete model selection.

Every comparison and mapping report was independently regenerated from the
uploaded YAMLs and matched byte for byte. For each of the three prompt styles:

| Pair | Name differences | Requirement tuple differences | Mapping |
| --- | ---: | ---: | --- |
| v0/v1 | 2 | 27 | NO MAPPING FOUND |
| v0/v2 | 3 | 32 | NO MAPPING FOUND |
| v1/v2 | 1 | 5 | NO MAPPING FOUND |
| v1/v1 | 0 | 0 | NO DIFFERENCES FOUND |
| v2/v2 | 0 | 0 | NO DIFFERENCES FOUND |

The /lib64 change is retained in all three styles. Identical-document pairs
produce identical YAMLs and the required no-difference markers. Counts measure
exact source-text differences, including PDF text-extraction artifacts; they
are not counts of distinct semantic security changes.

The differences do not match the implemented, deliberately narrow Dockerfile
rule mappings. Under the assignment, both no-mapping and no-difference cases
therefore require all-rule scans. Identical scanner CSVs across all 15 outputs
are expected for this input and configuration.

## Scanner results and known errors

Each scan accounts for the entire supplied archive:

| Measure | Per scan |
| --- | ---: |
| Candidate Dockerfiles | 397,567 |
| Distinct contents | 178,527 |
| Duplicate original files reusing matching content results | 219,040 |
| Files parsed by Hadolint | 395,019 |
| Files with actual DL1000 parser findings | 2,546 |
| Files affected by an upstream runtime exception | 2 |
| Encoding errors | 0 |
| CSV rows | 1,598,633 |
| Findings, including parser findings | 2,284,489 |

Parsed files can have linter findings; parsed does not mean clean. Parser
failures can reflect malformed source or syntax unsupported by this scanner.
Those files are retained as DL1000 errors, not silently dropped or rewritten.

Two original paths have identical content and cause the same upstream
Data.Text.Internal.Fusion.Common.index: Index too large exception in
Hadolint.Rule.DL3000:

- dokcerfiles/278746914.Dockerfile
- dokcerfiles/5ebbc604b27076c59dd0a03f37d186921de5fa60.Dockerfile

Their content SHA-256 is
8fd6e00faa555c739e65d4f42e68d3e3a49cbcc844da1ec857388a7b2a0410d1.
The exception was independently reproduced using unmodified archive bytes and
the Linux Hadolint 2.15.1 executable. The older 2.12.0 baseline documented the
same two inputs. No findings are invented for files the tool could not scan.

Consequently, all final scan statuses are completed-with-tool-errors, and each
pair's run status is completed-with-scan-errors. The pipeline reached the end
and accounts for all original paths, but it is not an error-free tool run.
Its evidence distinguishes these tool failures from ordinary linter findings
and parser errors. A rerun with the unchanged scanner would reuse those results
and would not resolve the reproducible upstream defect.

## Independent validation and limits

The uploaded SHA-256 list contains all 15 CSVs. Their common hash is:

68815c2948c5e57800246a992d4523bdf78015d43ae56cbd43f0891f6eaaf99e

The included v0/v1 zero-shot CSV matches this hash. Every included CSV row was
checked for the required four columns, valid original archive path, positive
integer count, uniqueness and ordering, and version-specific DL default
severity. The parser-error paths match scan-errors.jsonl exactly. Row and
finding totals agree with every manifest. A deterministic, evenly distributed
256-file sample was independently rescanned with Linux Hadolint 2.15.1 using
the same configuration, and its per-file rule counts matched the Mac CSV.

The compact review ZIP intentionally omitted the full hadolint-findings.jsonl
and scan-files.jsonl logs. This review therefore does not claim independent
row-by-row reconciliation against all raw findings. Preserve those original
logs on the Mac with the final outputs. Detailed machine-readable review
results are in final-results-validation.json.

## Submission work still required

The README contains the user-provided individual contributor details. The
public repository and successful GitHub Actions test/build run are verified;
see GITHUB_ACTIONS.md for the actual run and retained log. The workflow built
and smoke-tested the Linux x86_64 executable. The native Apple Silicon macOS build
also passed its version and real Gemma worker checks, and its archive hash,
ARM64 header, and executable permissions were verified; see MAC_EXECUTABLE.md.
The TA target operating system is unspecified; select the matching platform
artifact. Final review and form submission remain with the user.
