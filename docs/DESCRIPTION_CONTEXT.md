# Description coverage after the completed Mac extraction

## What the supplied results establish

The user supplied Proj_Sec_Extraction_Results.zip after all five assigned pairs
finished in extract mode. Review verified all 30 YAML files, 3,522 exported KDEs,
and 7,044 validated source-block audit entries. Counts are across repeated pair
outputs, not distinct recommendations or fresh model calls. Each original PDF
has 117, 117, or 118 recommendations respectively. The inventories and recorded
source sections match fresh extraction of the supplied PDF bytes. Every exported
requirement is a source excerpt, and all Remediation candidates are present.
Repeated documents have consistent YAMLs; both identical-document pairs have
identical outputs for all three prompt styles. The original model-runtime files
record google/gemma-3-1b-it, revision dcc83ea841ab6100d6b47a070329e1ba4cf78752,
MPS, bfloat16, and source-id-trie-v1 for newly constrained generation. Older
validated numeric/JSON responses are reused and labeled with their original mode.

## Coverage failure found during review

Valid source IDs did not establish semantic completeness. For example, in CIS
5.6 the newer Description adds /lib64 to the sensitive host-directory list.
Zero-shot and chain-of-thought omitted that Description while the associated
Remediation contains only a generic prohibition on sensitive mounts. As a result,
those two styles missed the directory-list change. Some old JSON selections
also shortened Description qualifiers even though the selected substring was
verbatim. The original results therefore passed syntax and source-fidelity
checks but were not complete with respect to Description content.

## Corrected policy and provenance

For a recommendation with a nonempty Remediation block, retain its complete
Description as explicit source context as well as the complete Remediation.
Each source block must still have a valid real model response. Remediation must
contain a nonempty valid model selection before the KDE can be exported. NONE
in Description remains an empty model selection in the audit; it is not relabeled
as a model-selected requirement. The audit separately records included source
IDs/text, context added, and retain-description-context-for-remediation policy.
Without Remediation, Description remains model-selected; NONE cannot create a KDE.

This is a hybrid source-context policy, not evidence that Gemma independently
identified every included requirement. It prioritizes preserving source changes
and qualifying context, and includes some background prose. On the supplied
PDFs, the complete context causes final requirement lists to agree across the
three styles even when their actual model selections differ. The original
prompts and responses stay separately recorded for each style. No requirements
are paraphrased or invented. Existing valid model responses and cache keys are
reused; this correction does not require a new inference run.

## Verification

All 97 unit/integration tests passed with real Hadolint 2.15.1, including tests
that reproduce the missed /lib64 change with NONE Description responses,
preserve omitted qualifiers from legacy responses, verify cached resumption,
and reject recommendations without a valid model-identified requirement.

An offline replay of the uploaded responses applied the revised context policy
to all five pairs and all three styles. It made no new model calls. Every source
candidate from both fields was present in the recomputed YAMLs and every included
string was a source excerpt. The /lib64 change was detected in all three styles,
and both identical pairs still produced no differences. Expected symmetric
difference counts (individual NAME,REQU tuples count separately) are:

| Pair | Name differences | Requirement differences | Mapping |
| --- | ---: | ---: | --- |
| v0/v1 | 2 | 27 | NO MAPPING FOUND |
| v0/v2 | 3 | 32 | NO MAPPING FOUND |
| v1/v2 | 1 | 5 | NO MAPPING FOUND |
| v1/v1 | 0 | 0 | NO DIFFERENCES FOUND |
| v2/v2 | 0 | 0 | NO DIFFERENCES FOUND |

These counts are the same for all three styles. Difference counts measure exact
text, including PDF text-extraction artifacts; they are not counts of distinct
semantic security changes. No supported Dockerfile-rule mapping applies to
these particular differences, so the assignment requires all-rule Hadolint scans.

Regenerate the user's final outputs from the preserved local cache after applying
the source update. Do not submit the verification replay as a new model run.
Final Dockerfile scans, repository/Actions, team metadata, and the target-platform
PyInstaller executable still need separate completion and verification.
