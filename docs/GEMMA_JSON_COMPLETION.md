# Gemma JSON completion and remediation check

The Mac diagnostic showed a complete name and requirements array followed by
a Markdown closing fence, with just the JSON object's final } missing. The
requirements copied Description background and omitted Remediation. The model
worker's deprecation/greedy-generation warnings were separate from these
observable content and format problems.

The parser now accepts exactly one narrowly bounded repair: if adding a single
terminal } produces one complete JSON object with exactly name and requirements,
it proceeds to normal name, nonempty-list, and exact-source validation. It does
not close strings or arrays, add values, correct names, accept multiple JSON
objects, or ignore trailing prose. The raw model response is never rewritten;
its syntax repair is recorded separately in the audit and cache.

When a section has nonempty Remediation, at least one selected excerpt must
come from that block (or include the complete block). Description-only output
fails validation and is retried. Prompts emphasize remediation and its distinct
conditions, and remind the model to close both the array and object. This is a
coverage safeguard, not proof that every security obligation was extracted.
Human review against the source remains required.

The first real-PDF diagnostic should be rerun on the Mac. Existing model
weights, inputs, final output folders, and old logs are preserved by the update.
Changed prompts produce new cache identities; no cache deletion is required.
