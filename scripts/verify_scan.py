"""Reconcile CSV rows against raw Hadolint findings and the original-file inventory."""
import argparse
from collections import Counter
import csv
import json
from pathlib import Path


def verify(directory):
    directory = Path(directory)
    manifest = json.loads((directory / 'scan-manifest.json').read_text())
    catalog = json.loads((Path(__file__).resolve().parents[1] / 'proj_sec/hadolint_rules.json').read_text())['default_severities']
    selected = manifest['selected_rules']
    contents = {}
    with (directory / 'hadolint-findings.jsonl').open() as stream:
        for line in stream:
            record = json.loads(line)
            digest = record['sha256']
            if digest in contents:
                raise ValueError('Duplicate raw content evidence')
            contents[digest] = Counter((catalog.get(f['code'], f['level']), f['code']) for f in record['findings']
                                       if selected == 'ALL' or f['code'] in selected)
    paths, statuses, frequencies = {}, Counter(), Counter()
    with (directory / 'scan-files.jsonl').open() as stream:
        for line in stream:
            record = json.loads(line)
            name, digest = record['file'], record['sha256']
            if name in paths or digest not in contents:
                raise ValueError('Duplicate original path or missing content evidence')
            paths[name] = digest
            frequencies[digest] += 1
            statuses[record['status']] += 1
    expected_rows = sum(len(contents[digest]) * n for digest, n in frequencies.items())
    expected_findings = sum(sum(contents[digest].values()) * n for digest, n in frequencies.items())
    rows = findings = 0
    previous = None
    with (directory / 'results.csv').open(newline='') as stream:
        reader = csv.DictReader(stream)
        if reader.fieldnames != ['FilePath', 'DefaultSeverity', 'RULEID', 'COUNT']:
            raise ValueError('Incorrect CSV columns')
        for row in reader:
            key = row['FilePath'], row['DefaultSeverity'], row['RULEID']
            number = int(row['COUNT'])
            if previous is not None and key <= previous:
                raise ValueError('Unsorted or duplicated CSV row')
            if number < 1 or contents[paths[key[0]]][key[1:]] != number:
                raise ValueError(f'CSV count does not match raw findings: {key}')
            previous = key
            rows += 1
            findings += number
    checks = [len(paths) == manifest['candidate_files'], len(contents) == manifest['unique_contents'],
              rows == expected_rows == manifest['csv_rows'], findings == expected_findings == manifest['finding_count'],
              statuses['scanned'] == manifest['parsed_files'], statuses['parse-error'] == manifest['parse_error_files'],
              statuses['encoding-error'] == manifest['encoding_error_files'], statuses['tool-error'] == manifest['tool_error_files']]
    if not all(checks):
        raise ValueError('Manifest totals disagree with raw evidence or CSV')
    return {'verified': True, 'candidate_files': len(paths), 'unique_contents': len(contents),
            'csv_rows': rows, 'findings': findings, 'file_statuses': dict(statuses),
            'every_csv_row_matches_raw_evidence': True, 'all_original_file_paths_are_unique': True}


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('directory', type=Path)
    args = parser.parse_args()
    print(json.dumps(verify(args.directory), indent=2))
