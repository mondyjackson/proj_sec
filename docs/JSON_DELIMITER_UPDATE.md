# Redundant JSON closing delimiters

The real Mac run completed both source fields for seven recommendations in
v0's zero-shot pass. At 1.1.8/Description the model returned the exact heading
and source excerpt, with a valid JSON object followed by an extra ]} suffix.
The original parser rejected that response after corrective retries.

The updated parser uses Python's JSONDecoder.raw_decode to locate exactly one
complete root object. It accepts a remaining suffix only when that suffix is
no more than 32 characters composed entirely of closing square brackets,
closing braces, or whitespace. The decoded object must have exactly the two
expected keys before ordinary name/list/source validation runs. Arbitrary
trailing prose, another JSON value, openers, incomplete strings, or incomplete
arrays are not accepted. The earlier one-missing-final-brace repair remains.

Every raw response is retained unchanged, and each syntactic repair is recorded
in the cache and audit. No heading or requirement text is replaced or filled in.
The regression test includes the exact observed heading and requirement.

The update changes no model prompts, model identity, source-block cache keys,
or worker settings. Previously validated blocks remain reusable on resume.
It still requires a completed real full extraction and coverage review.
