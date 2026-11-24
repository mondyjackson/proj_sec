# Required functions and acceptance evidence

| Task | Function | Source | Corresponding test |
| --- | --- | --- | --- |
| 1.1 | validate_documents | proj_sec/extractor.py | test_validate_documents |
| 1.2 | zero_shot_prompt | proj_sec/prompts.py | test_zero_shot_prompt |
| 1.3 | few_shot_prompt | proj_sec/prompts.py | test_few_shot_prompt |
| 1.4 | chain_of_thought_prompt | proj_sec/prompts.py | test_chain_of_thought_prompt |
| 1.5 | extract_kdes | proj_sec/extractor.py | test_extract_kdes |
| 1.6 | write_llm_log | proj_sec/extractor.py | test_write_llm_log |
| 2.1 | load_yaml_pair | proj_sec/comparator.py | test_load_yaml_pair |
| 2.2 | compare_names | proj_sec/comparator.py | test_compare_names |
| 2.3 | compare_requirements | proj_sec/comparator.py | test_compare_requirements |
| 3.1 | load_difference_reports | proj_sec/executor.py | test_load_difference_reports |
| 3.2 | map_hadolint_rules | proj_sec/executor.py | test_map_hadolint_rules |
| 3.3 | run_hadolint | proj_sec/executor.py | test_run_hadolint and real Hadolint integration tests |
| 3.4 | export_csv | proj_sec/executor.py | test_export_csv |

## Acceptance evidence

- Task 1: real authenticated Gemma extraction completed for all five pairs and
  three prompt styles. All 30 YAMLs and actual prompt/response audits reconcile
  with the source. Model selections and source context are recorded separately.
- Task 2: all 15 comparator report sets were regenerated independently and
  matched. Both identical-document pairs produce the specified no-difference
  markers. See FINAL_RESULTS_REVIEW.md.
- Task 3: all 397,567 original paths are accounted for in each final scan.
  Parser findings and the two upstream crash inputs are explicitly reported.
  The final 1,598,633-row CSV was validated, and an independent 256-file rescan
  matched. All 15 CSV hashes agree; the bundled results helper restores them.
- Task 4: contributor metadata is complete; the repository is public; the
  published GitHub workflow passed all 97 tests and produced the Linux binary
  and checksum artifact. Actual test logs are preserved; see GITHUB_ACTIONS.md.
- GitHub has no native local-pull event. CI runs on push, pull_request, and
  manual events. scripts/pull_and_test.py tests successful local pulls with the
  active interpreter, including already-up-to-date pulls; an optional post-merge
  hook covers merges/fast-forwards in an activated Python virtualenv.
- The KDE-per-recommendation design, separate output pair per style, deterministic
  context policy, partial rule mappings, and tool limitations are documented.
- The native Mac executable returned version 0.3.0 and passed real Gemma
  MPS/bfloat16 inference. Its uploaded archive checksum, ARM64 header, and
  executable permissions were verified. See MAC_EXECUTABLE.md. The TA platform
  is unspecified; select the matching Mac or Linux artifact.
- Submit the repository, binary, and required outputs through the instructor's
  form before December 1, 2026, 11:59 PM CST.
