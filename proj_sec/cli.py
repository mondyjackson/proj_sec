from __future__ import annotations

import argparse
import importlib.metadata
import json
import logging
import platform
import shutil
import sys
from pathlib import Path

from . import __version__
from .common import MODEL_ID, write_json
from .comparator import compare_names, compare_requirements, load_yaml_pair
from .executor import export_csv, load_difference_reports, map_hadolint_rules, run_hadolint
from .extractor import extract_kdes, validate_documents
from .coverage_review import POLICY as REVIEW_POLICY, refine_pair
from .model import GemmaGenerator
from .pdfio import section_dicts


def _prepare(args):
    documents = validate_documents(args.first, args.second)
    inventory = []
    for side, document in zip(("left", "right"), documents):
        sections = section_dicts(document)
        path = Path(args.output) / f"{side}-{document.path.stem}-source-sections.json"
        write_json(path, sections)
        inventory.append({"side": side, "file": document.path.name, "sha256": document.sha256,
                          "pages": document.pages, "recommendations": len(sections),
                          "source_sections": path.name})
    write_json(Path(args.output) / "input-inventory.json", inventory)
    return documents, inventory


def _compare(first, second, output):
    documents = load_yaml_pair(first, second)
    names = compare_names(documents, Path(output) / "element-names.txt")
    requirements = compare_requirements(documents, Path(output) / "element-requirements.txt")
    mapping = map_hadolint_rules(load_difference_reports(names, requirements), Path(output) / "hadolint-rules.txt")
    return names, requirements, mapping


def _doctor(args):
    versions = {}
    for package in ("pypdf", "PyYAML", "pandas", "torch", "transformers", "accelerate", "pyinstaller"):
        try:
            versions[package] = importlib.metadata.version(package)
        except importlib.metadata.PackageNotFoundError:
            versions[package] = "not installed in this interpreter"
    print(json.dumps({"python": sys.version, "platform": platform.platform(),
                      "required_model": MODEL_ID, "packages": versions,
                      "hadolint": shutil.which(args.hadolint),
                      "note": "This checks local setup only; it does not verify model access."}, indent=2))


def build_parser():
    parser = argparse.ArgumentParser(description="Compare CIS Docker requirements and scan Dockerfiles.")
    parser.add_argument("--version", action="version", version=__version__)
    sub = parser.add_subparsers(dest="command", required=True)
    doctor = sub.add_parser("doctor", help="Report installed dependencies without downloading a model")
    doctor.add_argument("--hadolint", default="hadolint")
    for command in ("prepare", "extract", "run"):
        item = sub.add_parser(command, help={"prepare": "Validate PDFs and inventory every CIS recommendation",
                            "extract": "Run all three Gemma prompt strategies", "run": "Run extraction, comparison, and scanning"}[command])
        item.add_argument("first", type=Path)
        item.add_argument("second", type=Path)
        item.add_argument("--output", type=Path, required=True)
        if command != "prepare":
            item.add_argument("--model-cache", type=Path, default=Path(".cache/gemma"))
            item.add_argument("--model-python", help="Python executable in the model-enabled virtual environment")
            item.add_argument("--model-path", help="Optional local copy of google/gemma-3-1b-it")
            item.add_argument("--device", choices=("auto", "cpu", "cuda", "mps"), default="auto")
            item.add_argument("--dtype", choices=("auto", "float32", "float16", "bfloat16"), default="auto")
            item.add_argument("--max-new-tokens", type=int, default=1024)
            item.add_argument("--no-omission-review", action="store_true", help="Run the initial extraction alone for comparison")
            item.add_argument("--review-cache", type=Path, default=Path(".cache/gemma-omission-review-check-v1"))
            item.add_argument("--review-dtype", choices=("auto", "float32", "float16", "bfloat16"), default="float32")
            item.add_argument("--review-passes", type=int, choices=(1, 2, 3), default=2)
        if command == "run":
            item.add_argument("--dockerfiles", type=Path, required=True)
            item.add_argument("--hadolint", default="hadolint")
    compare = sub.add_parser("compare", help="Compare two existing KDE YAML files")
    compare.add_argument("first", type=Path)
    compare.add_argument("second", type=Path)
    compare.add_argument("--output", type=Path, required=True)
    scan = sub.add_parser("scan", help="Map comparator reports and scan a Dockerfile ZIP")
    scan.add_argument("names", type=Path)
    scan.add_argument("requirements", type=Path)
    scan.add_argument("--dockerfiles", type=Path, required=True)
    scan.add_argument("--output", type=Path, required=True)
    scan.add_argument("--hadolint", default="hadolint")
    for item in (scan, sub.choices["run"]):
        item.add_argument("--scan-cache", type=Path, default=Path(".cache/hadolint.sqlite3"))
        item.add_argument("--workers", type=int, default=4)
        item.add_argument("--batch-size", type=int, default=256)
    smoke = sub.add_parser("smoke-model", help="Test one short real Gemma extraction before a full run")
    smoke.add_argument("--output", type=Path, required=True)
    smoke.add_argument("--model-python")
    smoke.add_argument("--model-path")
    smoke.add_argument("--device", choices=("auto", "cpu", "cuda", "mps"), default="auto")
    smoke.add_argument("--dtype", choices=("auto", "float32", "float16", "bfloat16"), default="auto")
    smoke.add_argument("--max-new-tokens", type=int, default=1024)
    return parser


def main(argv=None):
    logging.getLogger("pypdf").setLevel(logging.ERROR)
    args = build_parser().parse_args(argv)
    if getattr(args, "max_new_tokens", 1024) <= 0:
        raise SystemExit("--max-new-tokens must be positive")
    try:
        if args.command == "doctor":
            _doctor(args)
        elif args.command == "prepare":
            _, inventory = _prepare(args)
            print(json.dumps(inventory, indent=2))
        elif args.command == "compare":
            for path in _compare(args.first, args.second, args.output):
                print(path)
        elif args.command == "scan":
            mapping = map_hadolint_rules(load_difference_reports(args.names, args.requirements),
                                        args.output / "hadolint-rules.txt")
            results = run_hadolint(mapping, args.dockerfiles, hadolint=args.hadolint, evidence_dir=args.output, cache_path=args.scan_cache, workers=args.workers, batch_size=args.batch_size, progress=lambda status: print(json.dumps(status), flush=True))
            print(export_csv(results, args.output / "results.csv"))
            print(f"Scan status: {results.attrs.get('scan_status', 'unknown')}; see scan-manifest.json")
        else:
            with GemmaGenerator(args.output, python=args.model_python, device=args.device,
                                model_path=args.model_path, max_new_tokens=args.max_new_tokens, dtype=args.dtype) as generator:
                if args.command == "smoke-model":
                    from .pdfio import Section
                    from .prompts import zero_shot_prompt
                    from .extractor import _parse_response, write_llm_log
                    section = Section("example", "Restrict access", "Description:\nOnly administrators may access the service.")
                    prompt = zero_shot_prompt(section)
                    response = generator(prompt)
                    write_llm_log([{"model": MODEL_ID, "prompt": prompt, "prompt_type": "zero-shot", "output": response}],
                                  args.output / "llm-output.txt")
                    result = _parse_response(response, section)
                    write_json(args.output / "model-smoke.json", result)
                    print("Real Gemma smoke test passed")
                else:
                    status_path = args.output / "run-status.json"
                    write_json(status_path, {"status": "incomplete", "command": args.command})
                    documents, inventory = _prepare(args)
                    print("Validated PDFs; starting real Gemma extraction. Results are cached for resume.", flush=True)
                    outputs = extract_kdes(documents, args.output, generator, model_identity=generator.identity,
                                           cache_dir=args.model_cache,
                                           progress=lambda state: print(json.dumps(state), flush=True))
            if args.command != "smoke-model":
                if not args.no_omission_review:
                    print("Initial model closed; reviewing omitted source excerpts with real Gemma.", flush=True)
                    with GemmaGenerator(args.output, python=args.model_python, device=args.device,
                                        model_path=args.model_path, max_new_tokens=512,
                                        dtype=args.review_dtype) as reviewer:
                        outputs = refine_pair(outputs, args.output, reviewer, cache_dir=args.review_cache,
                                              passes=args.review_passes,
                                              progress=lambda state: print(json.dumps(state), flush=True))
                scan_statuses = {}
                if args.command == "run":
                    for style, pair in outputs.items():
                        directory = args.output / style
                        _, _, mapping = _compare(*pair, directory)
                        results = run_hadolint(mapping, args.dockerfiles, hadolint=args.hadolint, evidence_dir=directory, cache_path=args.scan_cache, workers=args.workers, batch_size=args.batch_size, progress=lambda status: print(json.dumps(status), flush=True))
                        export_csv(results, directory / "results.csv")
                        scan_statuses[style] = results.attrs.get("scan_status", "unknown")
                write_json(status_path, {"status": "completed-with-scan-errors" if any(s != "completed" for s in scan_statuses.values()) else "completed", "command": args.command,
                                        "scan_statuses": scan_statuses,
                                        "model": MODEL_ID, "inputs": inventory,
                                        "requirements_policy": "model-selected-only" if args.no_omission_review else REVIEW_POLICY,
                                        "prompt_types": list(outputs)})
                print(f"Completed {args.command}: {args.output}")
    except (Exception, KeyboardInterrupt) as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1
    return 0
