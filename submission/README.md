# Final output bundle

`final-results.zip` is a losslessly recompressed copy of the compact review
bundle supplied after the five real Mac pipeline runs. Every extracted file
is byte-identical to that supplied bundle. Use the Python helper below to
read the archive compression format. It includes all 30 YAMLs, per-pair actual prompts
and raw model responses, inventories, difference reports, mapping reports,
scanner manifests/statuses/error inventories, and one complete scan CSV.

All 15 scan CSVs have the same SHA-256, recorded in the bundle. The scans use
the same dataset, Hadolint 2.15.1 binary/configuration, and all rules. To restore
the complete directory layout, including a separate identical CSV at every
pair/style output path, run from the repository root:

```bash
python scripts/restore_final_results.py
```

The helper validates archive paths, checks hashes, preserves matching existing
files, and refuses to overwrite differing files. The restored CSV copies use
about 1.5 GB in total. They reproduce supplied output bytes; restoration does
not run or fabricate new model inference or scanner findings.

Full optional per-content/per-file scanner logs are retained in the user's
original Mac output directories and are not in this compact bundle. The
instructor's Dockerfile dataset and model credentials are not included.

Final statuses retain the 2,546 parser failures and two original files affected
by the reproducible upstream Hadolint exception. See
[`docs/FINAL_RESULTS_REVIEW.md`](../docs/FINAL_RESULTS_REVIEW.md) for the reviewed
counts, limitations, and independent rescan evidence.
