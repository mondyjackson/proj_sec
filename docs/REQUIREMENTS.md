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

## Historical checklist

The checklist below describes the earlier development checkpoint. The current
extractor, comparator, scanner, and contributor acceptance evidence is in
FINAL_RESULTS_REVIEW.md and PROGRESS.md. The real five-pair runs and contributor
metadata are now complete; executable verification and actual GitHub Actions
execution remain to be confirmed separately.

- The authenticated model smoke test passed on the Mac. Full-document extraction remains pending.
- Run real Gemma extraction with all three styles and review coverage, including context added by the complete-Remediation policy.
- Run final mapped scans after Gemma extraction; the standalone full-dataset baseline is regenerated and independently verified.
- Run the five specified PDF pair combinations, including both identical pairs.
- Review whether the instructor accepts a KDE per CIS recommendation and a
  separate pair of YAMLs per prompt style. The assignment leaves strategy
  selection/combination underspecified.
- Confirm the intended git-pull automation behavior. GitHub has no native
  local-pull event; CI and an optional local hook/helper are supplied.
- Confirm the TA's operating system and test a matching PyInstaller build.
- Enter the team's names, BannerIDs, and university email addresses.
- Create the public GitHub repository and obtain actual successful Actions logs.
- Submit through the instructor's form before December 1, 2026, 11:59 PM CST.
