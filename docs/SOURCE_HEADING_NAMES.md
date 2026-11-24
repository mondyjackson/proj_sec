# Source headings identify KDEs

The real Mac run completed eight recommendations in v0's zero-shot pass, then
stopped at 1.1.9/Description because Gemma did not copy the provided heading
exactly after three attempts. Many earlier name-copy failures had recovered on
retry. This copying constraint was an implementation choice, not a project
requirement stated in the supplied assignment.

Each source request already corresponds to a known PDF recommendation heading
and identifier. The parser now assigns the KDE name from that source metadata.
Gemma's requirement selections must still form a nonempty list of exact source
excerpts and satisfy the current source-block validation. A different, missing,
or malformed model label cannot replace the source name. A name alone cannot
supply missing requirements, and a known source heading cannot make an
invented or wrong-block requirement valid.

Raw model output is retained unchanged. Audit and cache metadata separately
record the source heading, the model label, the PDF origin of the final name,
and a model-name mismatch flag. The source-derived name does not masquerade as
something Gemma generated. The resulting YAML still has name, requirements,
and source_ids under each element, with one KDE per source recommendation.

Valid JSON requirements-only objects can be attached to the known heading.
The two narrowly bounded punctuation repairs also allow that schema. They do
not add requirement values. Malformed JSON, empty lists, fabricated excerpts,
and responses from the wrong source block remain errors.

Prompts, model settings, and source-block cache keys are unchanged. Previously
validated results can be reused. This update addresses heading-copy failures;
full extraction and manual source-coverage review remain to be completed.
