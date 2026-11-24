# Extract Description and Remediation separately

The combined-source request repeatedly selected Description and omitted
Remediation. On Jackson's M1 Mac, the separate-source diagnostic passed all six
requests: two source fields times three prompt styles. Remediation responses
included both new-installation and existing-system conditions for CIS 1.1.1.
This is direct user-supplied runtime evidence for that recommendation only.

The production extractor now uses the same request boundaries and prompt
builders. Each response is checked against its own block. Valid excerpts are
merged and deduplicated under the source heading to produce one KDE per
recommendation for each prompt style. Both present blocks must validate; a
failure caches earlier valid work but cannot complete the element or document.

Logs and progress include the source field. Every original response, including
any missing-brace completion note, remains in the audit. All prompts and
corrections are recorded. Prompt styles are never mixed together.

Cache keys include a source-block namespace, the full model identity, source
field, and exact rendered prompt. Identical prompts can share responses across
PDF versions; every cache hit is revalidated against the current source. A
changed title, source text, style, model, or precision cannot reuse that entry.
Combined-source responses use older keys and are not reused.

The first real recommendation and the code regression suite have passed.
Full-document Gemma extraction and manual coverage review remain pending.
The model may include descriptive background among selected excerpts or omit
an obligation; source validation alone does not establish semantic completeness.
