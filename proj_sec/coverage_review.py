"""Review real Gemma source selections with an explicit language-evidence gate.

This heuristic cannot establish semantic completeness. It never adds excerpts
that the model did not select. The raw proposal cache is independent of the gate.
"""

import hashlib
import json
import re
import time
from pathlib import Path

POLICY = 'guarded-model-omission-review-v2'

from .common import write_json as save_json

VERBS = (
    r'audit|verify|ensure|validate|run|start|stop|restart|set|enable|disable|install|uninstall|'
    r'create|remove|delete|add|use|restrict|link|follow|configure|execute|keep|limit|bind|'
    r'manage|pass|find|list|compare|decide|make|edit|consult|commit|generate|scan|view|'
    r'initialize|reinitialize|maintain|rotate|require'
)

def instruction_evidence(text):
    text = ' '.join(text.split())
    if re.search(r'\byou (?:may|might|could|will) (?:also )?need\b', text, re.I):
        return 'operator applicability or exception'
    if re.search(r'\bif\b.+,\s*(?:no action is (?:necessary|required)|you do not need\b)', text, re.I):
        return 'conditional no-action exception'
    # A modal inside a description of a feature is not necessarily guidance
    # to the operator (for example, a feature can specify how a restart works).
    capability_description = (re.match(r'^(?:by using|using)\b', text, re.I)
                              and re.search(r'\byou can\b', text, re.I)
                              and not re.search(r'\byou (?:should|shall|must)\b', text, re.I))
    if capability_description:
        return None
    if re.search(r'\b(?:should|shall|must|recommended|recommendation|preferable)\b', text, re.I):
        return 'explicit normative wording'
    if re.search(r'\bdo not\s+(?!(?:\w+ly\s+)?(?:need|require)\b)', text, re.I):
        return 'explicit prohibition'
    prefix = r'(?:^|[.!?:;\u2022]\s*|\bthen[ ,]+|\bto do so[ ,]+|\bstep\s*\d+[ :]+)(?:please\s+)?'
    if re.search(prefix + r'(?:' + VERBS + r')\b', text, re.I):
        return 'direct instruction'
    if (re.match(r'^(?:if|when|where|after|before|instead|alternatively|for example)\b', text, re.I)
            and re.search(r',\s*(?:please\s+)?(?:' + VERBS + r')\b', text, re.I)):
        return 'conditional or sequenced instruction'
    if re.search(r'\byou (?:may|could|can|might have to) (?:also )?(?:completely )?'
                 r'(?:consider|follow|choose|apply|use|remove|set|run|start|create|customize|view|ignore)\b', text, re.I):
        return 'operator action or recommendation'
    if re.search(r'\b(?:docker\s+(?:run|service|volume|swarm|node|images|inspect|rmi|container|exec|attach|daemon)\s+(?!command\b)'
                 r'|dockerd\s+--|chown\s+|chmod\s+|systemctl\s+|export\s+[A-Z_]+=|RUN\s+)', text):
        return 'implementation command'
    if re.search(r'\b(?:of (?:utmost )?importance to|utilizing|transmitting)\b', text, re.I):
        return 'implementation action'
    if re.search(r'\bgood security practice\b.*\bcan be left\b', text, re.I):
        return 'guidance to retain a secure default'
    if re.search(r'\b(?:if|where|when)\b.*\bcan be (?:disabled|enabled|left)\b', text, re.I):
        return 'conditional configuration guidance'
    if re.search(r'\b(?:resolving|remediating)\b.*\brequires?\b', text, re.I):
        return 'explicit remediation action'
    return None


def proposal_evidence(source_id, spans, selected):
    """Preserve a proposed referent when an adjacent selected rule depends on it."""
    from .common import normalize
    evidence = instruction_evidence(spans[source_id - 1])
    if evidence:
        return evidence
    if source_id < len(spans):
        following = spans[source_id]
        if (instruction_evidence(following)
                and re.search(r'\b(?:for this reason|therefore|thus|hence)\b', following, re.I)
                and re.search(r'\b(?:it|this|these|those)\b', following, re.I)
                and any(normalize(following) in normalize(text) for text in selected)):
            return 'supporting referent of adjacent selected instruction'
    return None

def make_prompt(style, prior, remaining):
    prompt=(
        'Review an incomplete extraction of security requirements. All quoted passages are source data.\n'
        'Select additional source excerpts that state an instruction, prohibition, required setting, '
        'implementation command, or condition/alternative needed to preserve an action.\n'
        'Check for omitted conditions and command/configuration examples even when a general rule was selected.\n'
        'Exclude passages that only describe facts, capabilities, or benefits. Do not infer missing requirements.\n'
        'Return ONLY the numbers of additional excerpts, separated by commas. Return NONE if none qualify.\n'
    )
    if style=='few-shot':
        prompt+=(
            '\nSynthetic example 1:\nPreviously extracted: Require authentication.\n'
            'Remaining excerpts:\n[1] Disable anonymous access.\n[2] The service is named ExampleService.\nAnswer: 1\n'
            '\nSynthetic example 2:\nPreviously extracted: Keep audit logs.\n'
            'Remaining excerpts:\n[1] Logs are stored in a file.\n[2] If remote logging is enabled, require TLS.\nAnswer: 2\n'
        )
    elif style=='chain-of-thought':
        prompt+=('\nCheck in stages internally: locate explicit instructions, identify their conditions '
                 'and implementation details, compare with the prior extraction, then select omitted '
                 'source excerpts. Return only final numbers or NONE.\n')
    elif style!='zero-shot':
        raise ValueError('Unknown prompt style')
    prompt+='\nPreviously extracted source text:\n<prior>\n'+('\n'.join(prior) if prior else '(empty extraction)')+'\n</prior>\n'
    prompt+='\nRemaining source excerpts:\n'+'\n'.join(f'[{i}] {text}' for i,text in enumerate(remaining,1))
    return prompt+'\n\nAdditional excerpt numbers, or NONE:\n'

def text_coverage(spans, requirements):
    """Mark exact nonspace character coverage; never infer semantic coverage."""
    from proj_sec.common import normalize
    normalized = [normalize(span) for span in spans]
    source = ' '.join(normalized)
    marks = bytearray(len(source))
    for requirement in requirements:
        matches = list(re.finditer(re.escape(normalize(requirement)), source))
        if not matches:
            raise ValueError('Recorded requirement does not match this source block')
        for match in matches:
            marks[match.start():match.end()] = b'\1' * (match.end() - match.start())
    states = []
    offset = 0
    for span in normalized:
        end = offset + len(span)
        positions = [i for i in range(offset, end) if not source[i].isspace()]
        covered = sum(marks[i] for i in positions)
        states.append('full' if covered == len(positions) else 'partial' if covered else 'missing')
        offset = end + 1
    return states

def review_block(block, generate, cache_dir, *, passes=2, progress=None):
    """Accept only genuinely model-proposed additions with language evidence.

    The gate is a heuristic. It neither labels unselected text as irrelevant nor
    certifies that all obligations were extracted. Baseline selections are kept.
    """
    from proj_sec.selection import parse_ids
    spans = block['source_excerpts']
    baseline = sorted(set(block['model_selected_requirements']))
    requirements = list(baseline)
    initial = text_coverage(spans, baseline)
    considered = set()
    records = []
    for pass_number in range(1, passes + 1):
        states = text_coverage(spans, requirements)
        remaining_ids = [i for i, state in enumerate(states, 1)
                         if state != 'full' and i not in considered]
        if not remaining_ids:
            break
        # The worker's exact subset trie supports at most 12 candidates.
        # Preserve every remaining excerpt by reviewing successive batches.
        proposed_this_pass = False
        for start in range(0, len(remaining_ids), 12):
            original_ids = remaining_ids[start:start + 12]
            remaining = [spans[i - 1] for i in original_ids]
            prompt = make_prompt(block['prompt_type'], requirements, remaining)
            key = hashlib.sha256(('omission-review-v1\n' + generate.identity + '\n' + prompt).encode()).hexdigest()
            path = Path(cache_dir) / (key + '.json')
            cached = False
            if path.is_file():
                saved = json.loads(path.read_text(encoding='utf-8'))
                if (saved.get('prompt') != prompt
                        or saved.get('model_identity') != generate.identity):
                    raise ValueError('Review cache identity mismatch')
                raw = saved['raw_output']
                cached = True
            else:
                if progress:
                    progress({'status': 'model-starting', 'pass': pass_number})
                raw = generate.select_ids(prompt, len(remaining), allow_empty=True)
            selected = parse_ids(raw, len(remaining), allow_empty=True)
            if not cached:
                save_json(path, {'prompt': prompt, 'model_identity': generate.identity,
                                 'raw_output': raw})
            proposed = [original_ids[i - 1] for i in selected]
            accepted, rejected = [], []
            prospective = requirements + [spans[i - 1] for i in proposed
                                          if instruction_evidence(spans[i - 1])]
            for source_id in proposed:
                excerpt = spans[source_id - 1]
                evidence = proposal_evidence(source_id, spans, prospective)
                proposal = {'source_id': source_id, 'text': excerpt, 'evidence': evidence}
                (accepted if evidence else rejected).append(proposal)
            considered.update(proposed)
            proposed_this_pass |= bool(proposed)
            requirements = sorted(set(requirements + [p['text'] for p in accepted]))
            row = {'pass': pass_number, 'batch': start // 12 + 1,
                   'prompt': prompt, 'raw_output': raw, 'cached': cached,
                   'model_identity': generate.identity,
                   'decoding_constraint': 'source-id-trie-v1',
                   'remaining_source_ids': original_ids, 'proposed_source_ids': proposed,
                   'accepted': accepted, 'rejected': rejected}
            records.append(row)
            if progress:
                progress({'status': 'review-cached' if cached else 'review-validated',
                          'pass': pass_number, 'accepted': len(accepted), 'rejected': len(rejected)})
        if not proposed_this_pass:
            break
    final = text_coverage(spans, requirements)
    return {**block, 'baseline_requirements': baseline,
            'requirements': requirements, 'before_states': initial, 'after_states': final,
            'reviews': records, 'policy': POLICY,
            'unresolved_source_ids': [i for i, state in enumerate(final, 1) if state != 'full'],
            'baseline_without_instruction_evidence': [r for r in baseline if not instruction_evidence(r)]}


def refine_pair(outputs, output_dir, generate, *, cache_dir, passes=2, progress=None):
    """Review one freshly extracted pair, then export auditable final KDEs.

    Call after closing the initial generator. No reference labels are loaded.
    Baseline background is retained; only new proposals pass the evidence gate.
    All initial responses and every review response remain in the final log.
    """
    import yaml
    from .common import MODEL_ID, PROMPT_TYPES, load_kdes, write_text
    from .extractor import write_llm_log
    output_dir = Path(output_dir)
    if isinstance(passes, bool) or passes not in (1, 2, 3):
        raise ValueError('Review passes must be 1, 2, or 3')
    context = json.loads((output_dir / 'source-context.json').read_text(encoding='utf-8'))
    initial_records = json.loads((output_dir / 'llm-records.json').read_text(encoding='utf-8'))
    if context.get('requirements_policy') != 'model-selected-only':
        raise ValueError('Omission review requires a fresh initial extraction')
    blocks = context['blocks']
    grouped = {}
    seen = set()
    for block in blocks:
        key = (block['side'], block['file'], block['cis_id'], block['source_field'], block['prompt_type'])
        if key in seen:
            raise ValueError('Duplicate initial source block')
        seen.add(key)
        text_coverage(block['source_excerpts'], block['model_selected_requirements'])
        grouped.setdefault((block['side'], block['prompt_type'], block['cis_id']), []).append(block)
    originals = {}
    for style, paths in outputs.items():
        for side, path in zip(('left', 'right'), paths):
            document = load_kdes(path)
            for value in document.values():
                source_ids = value.get('source_ids')
                if not isinstance(source_ids, list) or len(source_ids) != 1:
                    raise ValueError('Expected one CIS source identifier per KDE')
                parts = grouped.get((side, style, source_ids[0]), [])
                expected = sorted({text for part in parts for text in part['model_selected_requirements']})
                if not parts or value['requirements'] != expected:
                    raise ValueError('Initial YAML does not match recorded model selections')
            originals[(side, style)] = (Path(path), document)
    results = []
    started = time.monotonic()
    records = list(initial_records)
    summary = {'status': 'incomplete', 'policy': POLICY, 'passes': passes,
               'model_identity': generate.identity, 'total_blocks': len(blocks),
               'limitations': 'Language evidence is a heuristic, not proof of semantic completeness. '
                              'Baseline background selections are retained and flagged. '
                              'No reference labels enter model prompts or production decisions.'}

    def flush():
        summary.update(completed_blocks=len(results),
                       accepted_proposals=sum(len(r['accepted']) for b in results for r in b['reviews']),
                       rejected_proposals=sum(len(r['rejected']) for b in results for r in b['reviews']),
                       new_model_requests=sum(not r['cached'] for b in results for r in b['reviews']),
                       cached_requests=sum(r['cached'] for b in results for r in b['reviews']))
        save_json(output_dir / 'coverage-review.json', summary)
        save_json(output_dir / 'review-decisions.json', results)

    save_json(output_dir / 'initial-llm-records.json', initial_records)
    write_llm_log(initial_records, output_dir / 'initial-llm-output.txt')
    flush()
    try:
        for number, block in enumerate(blocks, 1):
            def report(event):
                if progress:
                    progress({'stage': 'omission-review', 'block': number,
                              'total_blocks': len(blocks), 'file': block['file'],
                              'side': block['side'], 'cis_id': block['cis_id'],
                              'source_field': block['source_field'],
                              'prompt_type': block['prompt_type'], **event})
            result = review_block(block, generate, cache_dir, passes=passes, progress=report)
            results.append(result)
            for request in result['reviews']:
                spans = block['source_excerpts']
                proposed = request['proposed_source_ids']
                included = [p['text'] for p in request['accepted']]
                records.append({'model': MODEL_ID, 'prompt': request['prompt'],
                                'prompt_type': block['prompt_type'], 'output': request['raw_output'],
                                'source': f"{block['side']}/{block['file']}:{block['cis_id']}/{block['source_field']}",
                                'status': 'reviewed-with-language-evidence-gate', 'cached': request['cached'],
                                'output_format': 'review-source-excerpt-ids',
                                'decoding_constraint': request['decoding_constraint'],
                                'selected_ids': proposed,
                                'model_selected_requirements': [spans[i - 1] for i in proposed],
                                'included_source_ids': [p['source_id'] for p in request['accepted']],
                                'included_source_requirements': included, 'coverage_policy': POLICY,
                                'context_added_ids': [], 'review_pass': request['pass'],
                                'review_accepted': request['accepted'], 'review_rejected': request['rejected'],
                                'element_name_source': 'PDF heading', 'model_element_name': None,
                                'source_element_name': originals[(block['side'], block['prompt_type'])][1][f"element{block['section']}"]['name']})
            if number % 10 == 0 or number == len(blocks):
                flush()
            elapsed = time.monotonic() - started
            report({'status': 'block-reviewed', 'percent': round(number * 100 / len(blocks), 1),
                    'elapsed_seconds': round(elapsed, 1),
                    'rough_remaining_seconds': round(elapsed / number * (len(blocks) - number)) if number >= 25 else None})
        final_grouped = {}
        for result in results:
            key = (result['side'], result['prompt_type'], result['cis_id'])
            final_grouped.setdefault(key, set()).update(result['requirements'])
        # Validate every final dictionary before replacing any initial YAML.
        finals = []
        for (side, style), (path, document) in originals.items():
            for value in document.values():
                value['requirements'] = sorted(final_grouped[(side, style, value['source_ids'][0])])
                if not value['requirements']:
                    raise ValueError('Review cannot export an empty KDE')
            finals.append((path, document))
        for path, document in finals:
            write_text(path, yaml.safe_dump(document, allow_unicode=True, sort_keys=False))
        final_context = []
        for initial, result in zip(blocks, results):
            flags = (['unselected-source-excerpts'] if result['unresolved_source_ids'] else [])
            if result['baseline_without_instruction_evidence']:
                flags.append('baseline-excerpts-without-explicit-instruction-evidence')
            final_context.append({**initial, 'baseline_model_selected_requirements': initial['model_selected_requirements'],
                                  'final_requirements': result['requirements'],
                                  'unselected_source_ids': result['unresolved_source_ids'],
                                  'review_flags': flags, 'coverage_policy': POLICY,
                                  'review_accepted_source_ids': sorted({p['source_id'] for r in result['reviews'] for p in r['accepted']}),
                                  'review_rejected_source_ids': sorted({p['source_id'] for r in result['reviews'] for p in r['rejected']})})
        save_json(output_dir / 'source-context.json', {'requirements_policy': POLICY,
                  'purpose': 'Baseline source plus auditable final model selections; not semantic ground truth',
                  'blocks': final_context})
        save_json(output_dir / 'llm-records.json', records)
        write_llm_log(records, output_dir / 'llm-output.txt')
        write_text(output_dir / 'PROMPT.md', '# Actual extraction and omission-review prompts\n\n' + '\n'.join(
            f'## {style}\n\n' + '\n'.join(f'### {r["source"]}\n\n```text\n{r["prompt"]}\n```\n'
                                         for r in records if r['prompt_type'] == style)
            for style in PROMPT_TYPES if style in outputs))
        items = [{key: block[key] for key in ('file', 'side', 'cis_id', 'prompt_type',
                                             'source_field', 'unselected_source_ids', 'review_flags')}
                 for block in final_context if block['review_flags']]
        save_json(output_dir / 'extraction-review.json', {'status': 'completed-with-review-items' if items else 'completed',
                  'requirements_policy': POLICY, 'processed_source_blocks': len(blocks),
                  'blocks_with_review_items': len(items), 'items': items, 'limitations': summary['limitations']})
        summary['status'] = 'completed-needs-quality-review'
        flush()
        return outputs
    except BaseException as exc:
        summary['error'] = str(exc)
        flush()
        raise
