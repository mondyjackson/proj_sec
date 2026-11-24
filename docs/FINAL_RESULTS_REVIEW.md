# Version 0.4.0 final result review

The uploaded Proj_Sec_Final_Review_v0.4.0.zip was checked against the previously
verified model-selected extraction, fresh instructor PDF reads, independently
regenerated comparison/mapping reports, and earlier independently audited scan
bytes. Validation found no inconsistencies. See final-v0.4.0-validation.json
and model-selected-extraction-validation.json for exact records and hashes.

All 30 YAML files contain only actual Gemma-selected requirements. All 7,044
repeated response entries retain their original prompts and raw outputs.
The five full runs use cached responses; they are not new inference runs.
See MODEL_SELECTED_RESULTS_REVIEW.md for per-style differences and semantic limits.

All 15 scan manifests record Hadolint 2.15.1, ALL rules, 397,567 candidate paths,
178,527 unique contents, zero new scanner executions, and 178,527 cache hits.
The binary/configuration identities match the original reviewed scans.
All 15 CSV hashes are 68815c2948c5e57800246a992d4523bdf78015d43ae56cbd43f0891f6eaaf99e.
The complete CSV has 1,598,633 rows and 2,284,489 findings.

Every scan retains 2,546 parser failures and two tool-error files sharing one
content hash. The statuses remain completed-with-tool-errors and
completed-with-scan-errors. Error paths/statuses/content hashes match the
original audit. The earlier independent 256-file Hadolint 2.15.1 rescan applies
to these identical CSV bytes. Full per-content/per-file scanner logs are
retained on the user's Mac and omitted from the compact public bundle.

The native Mac 0.4.0 executable and its real Gemma smoke evidence were also
verified; see MAC_EXECUTABLE.md. Model omissions, partial rule mappings, and
the local-pull/Actions event distinction remain documented limitations.
