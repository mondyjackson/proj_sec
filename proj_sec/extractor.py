from __future__ import annotations

import hashlib
import json
import re
from pathlib import Path
from typing import Callable

import yaml

from .common import MODEL_ID, PROMPT_TYPES, normalize, write_json, write_text
from .pdfio import Document, Section, read_pdf, split_sections
from .prompts import BUILDERS
from .selection import candidate_excerpts, candidates, parse_ids, source_kind


def validate_documents(first: Path | str, second: Path | str) -> tuple[Document, Document]:
    """Task 1, function 1: validate and read both inputs, including identical PDFs."""
    left = read_pdf(first)
    right = left if Path(first).resolve() == Path(second).resolve() else read_pdf(second)
    return left, right


def write_llm_log(records: list[dict], path: Path | str) -> Path:
    """Task 1, function 6: save all actual requests and raw model responses."""
    blocks = []
    for record in records:
        blocks.append(
            f"*LLM Name*\n{record['model']}\n"
            f"*Prompt Used*\n{record['prompt']}\n"
            f"*Prompt Type*\n{record['prompt_type']}\n"
            f"*LLM Output*\n{record['output']}\n"
            f"*Source*\n{record.get('source', '')}\n"
            f"*Status*\n{record.get('status', 'unvalidated')}\n"
            f"*Cached*\n{record.get('cached', False)}\n"
            f"*Syntax Repair*\n{record.get('syntax_repair') or 'none'}\n"
            f"*Element Name Source*\n{record.get('element_name_source', 'not recorded')}\n"
            f"*Source Element Name*\n{record.get('source_element_name', 'not recorded')}\n"
            f"*Model Element Name*\n{json.dumps(record.get('model_element_name'), ensure_ascii=False)}\n"
            f"*Model Name Differs*\n{record.get('model_name_differs', False)}\n"
            f"*Output Format*\n{record.get('output_format', 'not recorded')}\n"
            f"*Model Selected IDs*\n{json.dumps(record.get('selected_ids'))}\n"
            f"*Model Selected Requirements*\n{json.dumps(record.get('model_selected_requirements'), ensure_ascii=False)}\n"
            f"*Included Source IDs*\n{json.dumps(record.get('included_source_ids'))}\n"
            f"*Included Source Requirements*\n{json.dumps(record.get('included_source_requirements'), ensure_ascii=False)}\n"
            f"*Context Added IDs*\n{json.dumps(record.get('context_added_ids'))}\n"
            f"*Coverage Policy*\n{record.get('coverage_policy', 'not recorded')}\n"
            f"*Decoding Constraint*\n{record.get('decoding_constraint', 'unconstrained')}\n"
        )
    return write_text(path, "\n".join(blocks))


def _decode_response(raw: str) -> tuple[object, str | None]:
    text = raw.strip()
    if text.startswith("```"):
        fenced = re.fullmatch(r"```(?:json)?[ \t]*\r?\n(.*?)\r?\n?```", text,
                              flags=re.DOTALL | re.IGNORECASE)
        if fenced is None:
            raise ValueError("Gemma response is not a complete JSON object")
        text = fenced.group(1).strip()
    try:
        return json.loads(text), None
    except (ValueError, TypeError) as original:
        # Accept one requirements object followed solely by redundant closing
        # delimiters. Never discard trailing text, another value, or an opener.
        if text.startswith("{"):
            try:
                value, end = json.JSONDecoder().raw_decode(text)
            except (ValueError, TypeError):
                pass
            else:
                trailing = text[end:].strip()
                if (isinstance(value, dict) and set(value) in ({"requirements"}, {"name", "requirements"})
                        and re.fullmatch(r"[\]}\s]{1,32}", trailing)):
                    return value, "removed redundant closing delimiters after complete JSON object"
        # The observed response closed its complete requirements array but
        # omitted exactly the outer object's final brace. Never add a value,
        # quotation mark, array bracket, or more than one closing brace.
        if text.startswith("{") and text.endswith("]"):
            try:
                value = json.loads(text + "}")
            except (ValueError, TypeError):
                pass
            else:
                if isinstance(value, dict) and set(value) in ({"requirements"}, {"name", "requirements"}):
                    return value, "appended one missing final object brace"
        raise ValueError("Gemma response is not a complete JSON object") from original


def _parse_legacy_response(raw: str, section) -> dict:
    value, _ = _decode_response(raw)
    if not isinstance(value, dict):
        raise ValueError("Gemma response must be a JSON object with requirements")
    # The PDF heading identifies this source block before the LLM is called.
    # Names are source metadata; only requirement selection depends on Gemma.
    # Keep the model's own label in the audit instead of using it as the KDE key.
    requirements = value.get("requirements")
    if not isinstance(requirements, list) or not requirements:
        raise ValueError("Gemma must return at least one requirement")
    source = normalize(section.text)
    cleaned = []
    for requirement in requirements:
        if not isinstance(requirement, str) or not normalize(requirement):
            raise ValueError("Requirements must be nonempty strings")
        requirement = normalize(requirement)
        if requirement not in source:
            raise ValueError("Gemma returned a requirement without a matching source excerpt")
        if requirement not in cleaned:
            cleaned.append(requirement)
    remediation = re.search(r"(?:^|\n)Remediation:[ \t]*\n(.*)\Z", section.text, re.DOTALL)
    if remediation and (remediation_text := normalize(remediation.group(1))):
        if not any(r in remediation_text or remediation_text in r for r in cleaned):
            raise ValueError("Gemma omitted the Remediation actions; include exact excerpts from Remediation")
    return {"name": section.title, "requirements": sorted(cleaned), "source_ids": [section.cis_id]}




def _analyze_response(raw: str, section: Section, *,
                      retain_description_context: bool = False) -> tuple[dict, dict]:
    stripped = raw.strip()
    if stripped.startswith("```") and "\n" in stripped:
        stripped = stripped.split("\n", 1)[1].lstrip()
    # Legacy objects remain readable for cache reuse; new requests use IDs.
    legacy = stripped.startswith("{") and not re.match(r'\{\s*"ids"\s*:', stripped)
    if legacy:
        value = _parse_legacy_response(raw, section)
        decoded, repair = _decode_response(raw)
        selected = value["requirements"]
        model_name = decoded.get("name")
        metadata = {"output_format": "legacy-json", "syntax_repair": repair,
                    "model_element_name": model_name, "model_name_differs": model_name != section.title,
                    "selected_ids": None, "model_selected_requirements": selected}
    else:
        spans = candidate_excerpts(section)
        ids = parse_ids(raw, len(spans), allow_empty=source_kind(section) == "Description")
        selected = [spans[i - 1] for i in ids]
        value = {"name": section.title, "requirements": selected, "source_ids": [section.cis_id]}
        metadata = {"output_format": "source-excerpt-ids", "syntax_repair": None,
                    "model_element_name": None, "model_name_differs": False,
                    "selected_ids": ids, "model_selected_requirements": selected}
    metadata.update({"element_name_source": "PDF heading", "source_element_name": section.title,
                     "context_added_ids": [], "included_source_ids": metadata["selected_ids"],
                     "coverage_policy": "model-selected-description"})
    if retain_description_context and source_kind(section) == "Description":
        # Description can contain conditions or paths absent from Remediation
        # (for example /lib64 in CIS 5.6). Preserve that source context for a
        # recommendation with a Remediation block. The caller must still
        # validate a nonempty Gemma selection in Remediation before exporting.
        # NONE remains the model's actual selection; added text is audited.
        spans = candidate_excerpts(section)
        included = list(range(1, len(spans) + 1))
        value["requirements"] = sorted(set(spans))
        metadata.update({"coverage_policy": "retain-description-context-for-remediation",
                         "included_source_ids": included,
                         "included_source_requirements": spans,
                         "context_added_ids": [i for i in included if i not in metadata["selected_ids"]]
                         if metadata["selected_ids"] is not None else None})
    remediation = re.search(r"(?:^|\n)Remediation:[ \t]*\n(.*)\Z", section.text, re.DOTALL)
    if remediation and normalize(remediation.group(1)):
        # Gemma must identify an actual requirement before source expansion.
        if not selected:
            raise ValueError("Gemma must identify a requirement in Remediation")
        all_remediation = candidate_excerpts(Section(section.cis_id, section.title, "Remediation:\n" + remediation.group(1)))
        if source_kind(section) == "Remediation":
            value["requirements"] = sorted(set(all_remediation))
        else:
            value["requirements"] = sorted(set(selected + all_remediation))
        included = list(range(1, len(all_remediation) + 1))
        metadata.update({"coverage_policy": "retain-complete-remediation",
                         "included_source_ids": included,
                         "context_added_ids": [i for i in included if i not in metadata["selected_ids"]]
                         if metadata["selected_ids"] is not None else None,
                         "included_source_requirements": all_remediation})
    return value, metadata


def _parse_response(raw: str, section) -> dict:
    return _analyze_response(raw, section)[0]


def _source_blocks(section: Section) -> list[tuple[str, Section]]:
    matches = list(re.finditer(
        r"^(Description|Remediation):[ \t]*\n(.*?)(?=^(?:Description|Remediation):|\Z)",
        section.text, re.MULTILINE | re.DOTALL))
    if not matches:
        return [("Source", section)]
    blocks = [(m.group(1), Section(section.cis_id, section.title,
                                   m.group(1) + ":\n" + m.group(2).strip()))
              for m in matches if normalize(m.group(2))]
    if not blocks:
        raise ValueError(f"No nonempty source blocks for {section.cis_id}")
    return blocks


def extract_kdes(documents: tuple[Document, Document], output_dir: Path | str,
                 generate: Callable[[str], str], *, prompt_types=PROMPT_TYPES,
                 model_identity: str = MODEL_ID, retries: int = 2,
                 cache_dir: Path | str | None = None,
                 section_limit: int | None = None, progress: Callable[[dict], None] | None = None) -> dict[str, tuple[Path, Path]]:
    """Task 1, function 5: run each prompt strategy and save document-named YAMLs.

    A supplied generator permits isolated unit tests. The production CLI always
    uses the required Gemma worker; it does not provide a mock-inference mode.
    """
    output_dir = Path(output_dir)
    if not prompt_types or any(style not in BUILDERS for style in prompt_types):
        raise ValueError("Unknown or empty prompt type selection")
    if section_limit is not None and (isinstance(section_limit, bool)
                                      or not isinstance(section_limit, int) or section_limit < 1):
        raise ValueError("section_limit must be a positive integer or None")
    if isinstance(retries, bool) or not isinstance(retries, int) or retries < 0:
        raise ValueError("retries must be a nonnegative integer")
    sections_by_hash = {doc.sha256: split_sections(doc)[:section_limit] for doc in documents}
    records, outputs, prompt_blocks = [], {}, {style: [] for style in prompt_types}
    cache_dir = Path(cache_dir) if cache_dir is not None else output_dir / "cache"
    cache_dir.mkdir(parents=True, exist_ok=True)

    def flush_audit():
        write_llm_log(records, output_dir / "llm-output.txt")
        write_text(output_dir / "PROMPT.md", "# Actual extraction prompts\n\n" + "\n".join(
            f"## {style}\n\n" + "\n".join(prompt_blocks[style]) for style in prompt_types))

    for style in prompt_types:
        paths = []
        for side, document in zip(("left", "right"), documents):
            elements = {}
            for index, section in enumerate(sections_by_hash[document.sha256], 1):
                merged_requirements = set()
                blocks = _source_blocks(section)
                has_remediation = any(field == "Remediation" for field, _ in blocks)
                for field, part in blocks:
                    retain_description = field == "Description" and has_remediation
                    prompt = BUILDERS[style](part, output_format="ids")
                    key = hashlib.sha256(("source-selection-trie-v1\n" + model_identity + "\n" + field + "\n" + prompt).encode()).hexdigest()
                    cache_file = cache_dir / f"{key}.json"
                    previous_key = hashlib.sha256(("source-selection-v1\n" + model_identity + "\n" + field + "\n" + prompt).encode()).hexdigest()
                    previous_file = cache_dir / f"{previous_key}.json"
                    legacy_prompt = BUILDERS[style](part)
                    legacy_key = hashlib.sha256(("source-block-v1\n" + model_identity + "\n" + field + "\n" + legacy_prompt).encode()).hexdigest()
                    legacy_file = cache_dir / f"{legacy_key}.json"
                    existing = next((path for path in (cache_file, previous_file, legacy_file) if path.exists()), None)
                    event = {"file": document.path.name, "side": side, "cis_id": section.cis_id,
                             "prompt_type": style, "source_field": field, "section": index,
                             "sections": len(sections_by_hash[document.sha256])}
                    if progress:
                        progress({**event, "status": "starting"})
                    if existing is not None:
                        cached = json.loads(existing.read_text(encoding="utf-8"))
                        value, metadata = _analyze_response(
                            cached["raw"], part, retain_description_context=retain_description)
                        metadata["decoding_constraint"] = cached.get("decoding_constraint", "unconstrained")
                        used_prompt = cached.get("prompt_used", legacy_prompt if existing == legacy_file else prompt)
                        prompt_blocks[style].append(f"### Cached request: {side}, {section.cis_id}/{field}\n\n```text\n{used_prompt}\n```\n")
                        records.append({"model": MODEL_ID, "prompt": used_prompt, "prompt_type": style,
                                        "output": cached["raw"], "source": f"{side}/{document.path.name}:{section.cis_id}/{field}",
                                        "status": "validated", "cached": True, **metadata})
                    else:
                        used_prompt = prompt
                        prompt_blocks[style].append(f"### {side}: {document.path.name}, {section.cis_id}/{field}\n\n```text\n{prompt}\n```\n")
                        for attempt in range(retries + 1):
                            select = getattr(generate, "select_ids", None)
                            if callable(select):
                                raw = select(used_prompt, len(candidate_excerpts(part)),
                                             allow_empty=source_kind(part) == "Description")
                                decoding_constraint = "source-id-trie-v1"
                            else:
                                raw = generate(used_prompt)
                                decoding_constraint = "unconstrained-test-generator"
                            record = {"model": MODEL_ID, "prompt": used_prompt, "prompt_type": style,
                                      "output": raw, "source": f"{side}/{document.path.name}:{section.cis_id}/{field}",
                                      "status": "unvalidated", "cached": False}
                            records.append(record)
                            try:
                                # Preserve any bounded legacy syntax note even if
                                # later source/content validation rejects the response.
                                try:
                                    record["syntax_repair"] = _decode_response(raw)[1]
                                except ValueError:
                                    pass
                                value, metadata = _analyze_response(
                                    raw, part, retain_description_context=retain_description)
                            except ValueError as exc:
                                record["status"] = str(exc)
                                flush_audit()
                                if progress:
                                    progress({**event, "status": "validation-failed", "attempt": attempt + 1, "error": str(exc)})
                                if attempt == retries:
                                    raise ValueError(f"{document.path.name}, {section.cis_id}/{field}, {style}: {exc}") from exc
                                used_prompt = (prompt + f"\nCorrection required (attempt {attempt + 2}): {exc}.\n"
                                               "Return only existing excerpt numbers separated by commas. Do not rewrite source text.\n")
                                prompt_blocks[style].append(f"### Correction attempt: {side}, {section.cis_id}/{field}\n\n```text\n{used_prompt}\n```\n")
                            else:
                                metadata["decoding_constraint"] = decoding_constraint
                                record.update(metadata)
                                record["status"] = "validated"
                                write_json(cache_file, {"raw": raw, "prompt_used": used_prompt,
                                                      "model_identity": model_identity, "source_field": field, **metadata})
                                break
                    merged_requirements.update(value["requirements"])
                    flush_audit()
                    if progress:
                        progress({**event, "status": "cache-hit" if records[-1]["cached"] else "validated"})
                if not merged_requirements:
                    raise ValueError(f"{document.path.name}, {section.cis_id}: no requirements selected")
                elements[f"element{index}"] = {"name": section.title,
                                                "requirements": sorted(merged_requirements),
                                                "source_ids": [section.cis_id]}
            path = output_dir / style / f"{side}-{document.path.stem}-kdes.yaml"
            write_text(path, yaml.safe_dump(elements, allow_unicode=True, sort_keys=False))
            paths.append(path)
        outputs[style] = tuple(paths)
    flush_audit()
    return outputs
