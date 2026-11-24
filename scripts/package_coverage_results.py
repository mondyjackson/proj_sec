"""Package five completed reviewed runs, storing identical scan CSVs once."""
import argparse
import hashlib
import json
from pathlib import Path
import sys
import zipfile

PAIRS = ('v0-v1', 'v0-v2', 'v1-v2', 'v1-v1', 'v2-v2')
STYLES = ('zero-shot', 'few-shot', 'chain-of-thought')
PAIR_FILES = ('input-inventory.json', 'llm-output.txt', 'llm-records.json',
              'initial-llm-output.txt', 'initial-llm-records.json', 'PROMPT.md',
              'source-context.json', 'extraction-review.json', 'coverage-review.json',
              'review-decisions.json', 'run-status.json', 'model-runtime.json')
SCAN_FILES = ('element-names.txt', 'element-requirements.txt', 'hadolint-rules.txt',
              'scan-manifest.json', 'scan-status.json', 'scan-errors.jsonl')


def sha256(path):
    digest = hashlib.sha256()
    with path.open('rb') as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b''):
            digest.update(chunk)
    return digest.hexdigest()


def package_results(source, destination):
    source, destination = Path(source).resolve(), Path(destination).resolve()
    files, csvs, statuses = [], {}, {}
    for pair in PAIRS:
        directory = source / pair
        status = json.loads((directory / 'run-status.json').read_text())
        review = json.loads((directory / 'coverage-review.json').read_text())
        if status.get('command') != 'run' or not status.get('status', '').startswith('completed'):
            raise ValueError(f'Run is incomplete: {pair}')
        if review.get('status') != 'completed-needs-quality-review':
            raise ValueError(f'Omission review is incomplete: {pair}')
        statuses[pair] = {'run': status['status'], 'review': review['status']}
        files += [directory / name for name in PAIR_FILES if (directory / name).is_file()]
        files += list(directory.glob('*-source-sections.json'))
        for style in STYLES:
            scan = directory / style
            for required in ('element-names.txt', 'element-requirements.txt', 'hadolint-rules.txt',
                             'scan-manifest.json', 'scan-status.json', 'results.csv'):
                if not (scan / required).is_file():
                    raise ValueError(f'Missing pipeline result: {pair}/{style}/{required}')
            yaml_files = list(scan.glob('*-kdes.yaml'))
            if len(yaml_files) != 2:
                raise ValueError(f'Expected two KDE YAMLs: {pair}/{style}')
            files += yaml_files + [scan / name for name in SCAN_FILES if (scan / name).is_file()]
            csv = scan / 'results.csv'
            digest = sha256(csv)
            csvs[str(csv.relative_to(source))] = {'sha256': digest,
                'bytes': csv.stat().st_size, 'archive_member': f'shared-csv/{digest}.csv'}
    destination.parent.mkdir(parents=True, exist_ok=True)
    temporary = destination.with_suffix(destination.suffix + '.tmp')
    manifest = {'format': 'proj-sec-reviewed-results-v1', 'statuses': statuses,
                'csv_paths': csvs, 'original_csv_paths': len(csvs),
                'unique_csv_files': len({c['sha256'] for c in csvs.values()}),
                'limitations': 'Completed scans can contain documented scan errors. '
                               'Source fidelity and review status do not guarantee semantic completeness.'}
    with zipfile.ZipFile(temporary, 'w', compression=zipfile.ZIP_DEFLATED) as archive:
        for path in sorted(set(files)):
            archive.write(path, 'coverage-final/' + str(path.relative_to(source)))
        stored = set()
        for relative, info in csvs.items():
            if info['archive_member'] not in stored:
                archive.write(source / relative, info['archive_member'])
                stored.add(info['archive_member'])
        archive.writestr('csv-manifest.json', json.dumps(manifest, indent=2) + '\n')
    with zipfile.ZipFile(temporary) as archive:
        damaged = archive.testzip()
        if damaged:
            raise ValueError(f'Corrupt archive member: {damaged}')
    temporary.replace(destination)
    return manifest


def main():
    root = Path(__file__).resolve().parents[1]
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--source', type=Path, default=root / 'outputs/coverage-final')
    parser.add_argument('--output', type=Path, default=root / 'Proj_Sec_Coverage_Final.zip')
    args = parser.parse_args()
    try:
        result = package_results(args.source, args.output)
    except (OSError, ValueError) as exc:
        print('ERROR:', exc, file=sys.stderr)
        return 1
    print(f'{args.output}: {args.output.stat().st_size:,} bytes; '
          f'{result["original_csv_paths"]} CSV paths stored as {result["unique_csv_files"]} unique file(s).')
    print('Upload this ZIP for the final results review.')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
