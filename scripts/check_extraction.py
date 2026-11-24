"""Check real Gemma on a small PDF sample before starting the five-pair run."""
import argparse
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from proj_sec.common import MODEL_ID, PROMPT_TYPES, write_json
from proj_sec.extractor import extract_kdes, validate_documents
from proj_sec.model import GemmaGenerator
from proj_sec.pdfio import split_sections


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--pdf', type=Path, default=Path('data/docker-cis-v0.pdf'))
    parser.add_argument('--sections', type=int, default=1)
    parser.add_argument('--output', type=Path, default=Path('outputs/extraction-check'))
    parser.add_argument('--device', choices=('auto', 'cpu', 'mps', 'cuda'), default='auto')
    parser.add_argument('--dtype', choices=('auto', 'float32', 'float16', 'bfloat16'), default='auto')
    parser.add_argument('--max-new-tokens', type=int, default=1024)
    parser.add_argument('--model-python')
    parser.add_argument('--model-path')
    parser.add_argument('--model-cache', type=Path, default=Path('.cache/gemma'))
    args = parser.parse_args(argv)
    if args.sections < 1 or args.max_new_tokens < 1:
        parser.error('--sections and --max-new-tokens must be positive')
    status = {'status': 'incomplete', 'diagnostic_only': True, 'model': MODEL_ID,
              'requested_sections': args.sections, 'prompt_types': list(PROMPT_TYPES)}
    write_json(args.output / 'check-status.json', status)
    try:
        documents = validate_documents(args.pdf, args.pdf)
        sections = split_sections(documents[0])
        selected = sections[:args.sections]
        status.update({'input_sha256': documents[0].sha256, 'total_sections': len(sections),
                       'checked_sections': len(selected), 'cis_ids': [s.cis_id for s in selected]})
        print(f'Checking {len(selected)} recommendation(s) with all three prompt styles; diagnostic output only.', flush=True)
        with GemmaGenerator(args.output, python=args.model_python, device=args.device,
                            model_path=args.model_path, dtype=args.dtype,
                            max_new_tokens=args.max_new_tokens) as generator:
            outputs = extract_kdes(documents, args.output, generator,
                                   model_identity=generator.identity, cache_dir=args.model_cache,
                                   section_limit=args.sections,
                                   progress=lambda state: print(json.dumps(state), flush=True))
        status.update({'status': 'passed', 'output_styles': list(outputs)})
        write_json(args.output / 'check-status.json', status)
        print('Real PDF extraction check passed for all three prompt styles.')
        print('This sampled check does not establish complete PDF extraction or requirement coverage.')
        return 0
    except (Exception, KeyboardInterrupt) as exc:
        status.update({'status': 'failed', 'error': str(exc)})
        write_json(args.output / 'check-status.json', status)
        print(f'ERROR: {exc}', file=sys.stderr)
        print(f'See {args.output / "llm-output.txt"} and {args.output / "gemma-worker.log"}.', file=sys.stderr)
        return 1


if __name__ == '__main__':
    raise SystemExit(main())
