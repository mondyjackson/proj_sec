# Version 0.4.0 submission progress

| Area | Verified evidence |
| --- | --- |
| Extractor | Five completed pair runs; 30 YAMLs; actual Gemma selections only; fresh PDF/source checks; original raw-response provenance |
| Comparator | All 15 report sets independently regenerated; both identical pairs have no differences |
| Executor | All 15 cached scan runs completed; 397,567 paths each; CSV bytes match the independently audited data |
| Tests | 103 tests passed on the Mac and in the version 0.4.0 GitHub workflow; current commits also trigger CI |
| Mac executable | Native version 0.4.0 and real Gemma MPS/bfloat16 smoke passed; uploaded ARM64 bytes, mode, and hashes verified |
| Handoff | Public source, restoration helpers, final outputs, original model logs, and native Mac archive parts |

Remaining user action: review the documented limitations and submit through the
instructor form. Known model omissions, partial mappings, parser/tool errors,
and the distinction between GitHub push/PR events and local git pull remain.
See ../SUBMISSION.md. Successful execution does not guarantee a grade.
