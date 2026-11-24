# Numbered selection and source coverage

> Historical version 0.3.0 policy and evidence. Version 0.4.0 exports only actual model selections and stores source context separately. See [MODEL_SELECTED_REQUIREMENTS.md](MODEL_SELECTED_REQUIREMENTS.md).


## Observed problem and model evidence

Free-form JSON extraction failed on punctuation and exact copying, including
quoted configuration and command examples in CIS 2.2. The Mac diagnostic then
asked the same required google/gemma-3-1b-it model to choose numbered source
excerpts. Six of six replies were valid ID lists across two recommendations
and all three prompt styles. See mac-selection-check.json for the user-supplied
raw selections. Format validity did not establish coverage: the 2.2 selections
were 1,3 (zero-shot), 1,3,5 (few-shot), and 1,4 (chain-of-thought), omitting
some configuration settings, command examples, bridge limitations, or NET_RAW.

## Final extraction policy

1. Parse each source heading as the KDE identifier and name.
2. Process Description and Remediation separately per prompt style.
3. Normalize whitespace and split source into numbered exact excerpts. Every
   non-whitespace source character must survive splitting.
4. Ask real Gemma to select requirement-bearing excerpt IDs. Reject nonexistent
   IDs and arbitrary prose. NONE is permitted only for Description.
5. After Gemma identifies at least one Remediation requirement, retain the entire
   Remediation source and its associated Description as explicitly added context.
   Both fields can contain obligations, commands, conditions, or path lists.
   The output partitions that source into exact excerpts. Without a Remediation
   block, Description remains model-selected.
6. Merge both fields into one KDE per recommendation. Do not combine prompt
   styles. An absent model response or invalid selection cannot complete a KDE.

The source-context rules are deterministic coverage safeguards, not a
claim that Gemma selected every included excerpt. They favor recall over brevity
and can retain explanations alongside obligations. Audit/cache fields separately
record raw output, model-selected IDs/requirements, included source IDs, added
context IDs, and coverage policy. Source text added by code is never presented
as raw LLM output. No external requirements are invented.

## Caches and compatibility

Fresh constrained requests use the source-selection-trie-v1 namespace. Valid
source-selection-v1 numeric entries and source-block-v1 JSON responses are revalidated and reused when the model, field,
and original JSON prompt match. Their actual old prompts stay in the audit;
no numeric request is falsely claimed for a cache hit. The original JSON prompt
builders are retained unchanged for this lookup. Source coverage expansion is
applied to reused responses too. Malformed/unmatched legacy output
is still rejected. Existing valid work is not discarded or fabricated.

## Evidence limits

The supplied Mac results subsequently confirmed all five real full-document
extraction runs completed. Review found Description omissions despite valid
ID syntax. The complete-source-context correction and its offline replay are
documented in DESCRIPTION_CONTEXT.md. Local unit/integration tests verify
copying, source context, cache compatibility, and Hadolint behavior. These
checks do not establish completed final Dockerfile scans or submission readiness.


## Constrained decoding

The production worker now uses a token trie to restrict generated responses to
valid ascending source-ID sequences, with NONE allowed for Description. Syntax
validity does not establish semantic completeness. See CONSTRAINED_SELECTION.md
for the exact-version API/protocol regression and subsequent Mac evidence.
