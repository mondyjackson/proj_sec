# Version 0.5.0 verified submission artifacts

The exact uploaded Proj_Sec_Coverage_Final.zip is stored in two raw parts under
results/. Its manifest records byte counts and SHA-256 hashes. The archive's
SHA-256 is e138374e8c6da694526b1a7dad9f6d60db56c6c6f79991ec18ee909c5debad11.
Its size is 19,434,639 bytes. Every included file is byte-identical to the upload.

```bash
python scripts/restore_final_results.py
```

This restores outputs/coverage-final, including all 30 YAMLs, prompts, actual
model responses, source/review traces, comparison/mapping reports, scan metadata,
and all 15 CSV paths. Identical CSV bytes are stored once with a manifest and
restored to each original path. The helper validates paths/checksums and refuses
to overwrite differing files. Restoring these bytes does not perform or invent
new inference or scans. See docs/COVERAGE_FINAL_VALIDATION.json and
RESTORE_V0.5_VALIDATION.json for independent verification.

The exact native macOS ARM64 archive is stored in three raw parts under macos/.
Use python scripts/restore_macos_binary.py to reconstruct it and the executable.
The manifest records the original archive and binary hashes. Actual native
real-model smoke evidence is retained under docs/mac-smoke-v0.5.0.

Full optional per-content/per-file scanner evidence remains in the user's Mac
run directories. The compact bundle retains error inventories and statuses,
including 2,546 parser failures and two upstream tool-error files per scan.
Instructor datasets, model weights, authentication, and local caches are absent.
Historical 0.4.0 artifacts remain available through repository history.
