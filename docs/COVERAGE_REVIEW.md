# Omission review in version 0.5.0

The default extract/run pipeline first performs the original three independent
Gemma extraction strategies, closes that model worker, and then uses the same
required Gemma model to review omitted candidate excerpts. The review uses at
most two passes per source block by default. A language-evidence heuristic
validates proposed additions. It cannot add an excerpt that Gemma did not select.

The model is google/gemma-3-1b-it at the same pinned revision as the initial
extractor. Review prompts request source IDs, with independent zero-shot,
few-shot, and internally staged chain-of-thought variants. Exact subset decoding
validates syntax; it does not establish semantic correctness. The gate recognizes
instructions, commands, recommendations, applicability clauses, conditional
no-action exceptions, and supporting referents of adjacent selected instructions.
It uses no CIS identifiers, expected labels, or reference answers.

## Evidence from the three supplied PDF versions

The real Mac omission-review run completed 2,112 distinct document/style/source
blocks without errors in 689.8 seconds. It executed 244 new requests and reused
493 cached request occurrences. Repeated prompts across PDF versions account
for cache reuse. Its raw responses and actual proposal IDs were independently
replayed offline. All 30 candidate YAMLs, all 30 comparator reports, and the
review TEXT log reproduced the uploaded bytes. No fresh inference was performed
during that validation.

The first gate accepted 587 proposal occurrences and rejected 317. The updated
gate also preserves 27 already model-proposed applicability/supporting-context
occurrences. This changes acceptance decisions, not model responses or prompts.
Offline replay confirmed that no additional inference request was needed.

| Prompt style | Initial fully covered action occurrences | Reviewed fully covered action occurrences |
| --- | ---: | ---: |
| zero-shot | 691/1,017 | 1,017/1,017 |
| few-shot | 898/1,017 | 1,017/1,017 |
| chain-of-thought | 887/1,017 | 1,017/1,017 |

All 21 qualifier occurrences per style are also fully covered after the updated
gate. Accepted additions include no excerpts labeled background in this reference.

These are exact source-text coverage counts against an assistant-reviewed
reference, not an instructor gold standard, independent semantic accuracy, or a
predicted grade. The reference comprises 415 distinct candidate excerpts in the
parsed Description and Remediation fields: 338 action/instruction excerpts,
7 qualifiers, 65 background passages, 4 formatting fragments, and 1 ambiguous
default-layout statement. Occurrences repeat shared text across PDF versions.
The gate was developed using this corpus, so these results do not establish
performance on unseen documents. Other PDF fields are outside this audit.

The initial model's background selections are retained and flagged, rather than
silently relabeled as rejected model decisions. These remain a precision
limitation. Complete source is preserved for inspection. KDE names still come
from PDF headings, with one KDE per CIS recommendation. This structural choice
and source-ID decoding differ from unrestricted prose extraction.

## Run and inspect

```bash
caffeinate -i python scripts/run_all_pairs.py --mode run --device mps --dtype bfloat16 --output outputs/coverage-final
```

Initial extraction uses the existing .cache/gemma responses. Review defaults to
float32 and 512 output tokens, reusing .cache/gemma-omission-review-check-v1 from
the real full-review run. Raw-response cache keys include the full prompt and
model identity. The evidence policy is recalculated from raw selections; cached
acceptance decisions are never trusted. Baseline and review workers run
sequentially, and both close before Hadolint starts. The scanner retains its
separate content/rule/configuration cache.

Each pair contains:

- the final document-named YAMLs, comparisons, mappings, and scan CSVs;
- llm-output.txt and llm-records.json with all initial and review responses;
- initial-llm-output.txt and initial-llm-records.json for the baseline;
- PROMPT.md with exactly three strategy sections containing every used prompt;
- review-decisions.json with proposed/accepted/rejected IDs and evidence;
- source-context.json with unchanged baseline model_selected_requirements and
  separate final_requirements;
- coverage-review.json and extraction-review.json with status and limitations.

Only final_requirements and exported YAMLs describe the reviewed result.
Unselected source excerpts may be background or missed requirements; review
flags do not by themselves establish either classification. --no-omission-review
is available for baseline comparisons. --review-dtype and --review-passes allow
explicit runtime choices.

The user completed the integrated version 0.5.0 five-pair run. All 30 YAMLs,
45 comparison/mapping reports, 7,044 original response occurrences, and 2,454
review-response occurrences match the verified replay. All review responses and
scanner results were valid cache hits; no new inference or scanner execution
was needed. The same documented parse/tool errors remain.

The native 0.5.0 archive is also verified. Its 12 frozen project modules and
external model worker match the reviewed source, and the uploaded real Gemma
smoke response passed source validation. See MAC_EXECUTABLE.md,
COVERAGE_FINAL_VALIDATION.json, and NATIVE_V0.5_VALIDATION.json. Earlier
0.4.0 review documents are historical evidence, not the current output bundle.

After the five-pair run, create a compact review archive with:

```bash
python scripts/package_coverage_results.py
```

This writes Proj_Sec_Coverage_Final.zip in the project folder. It includes the
actual logs, prompts, YAMLs, comparisons, mappings, scan status/errors, and CSV
contents. Identical CSVs are stored once with a SHA-256 manifest for all 15 paths.
Large per-file scanner evidence remains in the original run directories.
