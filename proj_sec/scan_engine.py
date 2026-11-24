"""Bounded Hadolint batches with a resumable, content-addressed SQLite cache."""
from __future__ import annotations

from collections import Counter, deque
from concurrent.futures import ThreadPoolExecutor
import hashlib
import json
from pathlib import Path
import re
import sqlite3
import subprocess
import tempfile
import time
import zipfile

import pandas as pd
import yaml

from .common import COLUMNS, write_json


def scan_archive(archive_path, members, selected, configuration, catalog, *,
                 hadolint, version, env, evidence_dir, cache_path, workers,
                 batch_size, timeout, progress):
    if not 1 <= workers <= 16 or not 1 <= batch_size <= 1024:
        raise ValueError("workers must be 1..16 and batch_size must be 1..1024")
    started = time.monotonic()
    binary_sha = hashlib.sha256(Path(hadolint).read_bytes()).hexdigest()
    fingerprint = hashlib.sha256(json.dumps({
        'schema': 1, 'binary_sha256': binary_sha, 'config': configuration,
    }, sort_keys=True).encode()).hexdigest()
    evidence = Path(evidence_dir) if evidence_dir is not None else None
    if evidence:
        evidence.mkdir(parents=True, exist_ok=True)
        write_json(evidence / 'scan-status.json', {'status': 'incomplete', 'archive': str(archive_path)})
    cache_path = Path(cache_path) if cache_path else (evidence / 'scan-cache.sqlite3' if evidence else None)
    if cache_path:
        cache_path.parent.mkdir(parents=True, exist_ok=True)
    db = sqlite3.connect(str(cache_path) if cache_path else ':memory:')
    db.execute('CREATE TABLE IF NOT EXISTS scans (config TEXT, digest TEXT, result TEXT, PRIMARY KEY(config,digest))')
    content_counts, statuses, files = {}, {}, []
    cached = executed = skipped = 0
    skipped_sample = []
    last_report = 0.0

    def report(force=False):
        nonlocal last_report
        now = time.monotonic()
        if progress and (force or now - last_report >= 10):
            progress({'candidates': len(files), 'unique_completed': len(content_counts),
                      'unique_executed': executed, 'unique_cached': cached,
                      'elapsed_seconds': round(now - started, 1)})
            last_report = now

    raw_log = file_log = error_log = None
    try:
        with tempfile.TemporaryDirectory(prefix='proj-sec-') as temporary:
            temp = Path(temporary)
            config_path = temp / 'hadolint.yaml'
            config_path.write_text(yaml.safe_dump(configuration), encoding='utf-8')
            if evidence:
                raw_log = (evidence / 'hadolint-findings.jsonl').open('w', encoding='utf-8')
                file_log = (evidence / 'scan-files.jsonl').open('w', encoding='utf-8')
                error_log = (evidence / 'scan-errors.jsonl').open('w', encoding='utf-8')

            def run_batch(batch):
                paths = [str(path) for _, path in batch]
                runtime_error = None
                try:
                    result = subprocess.run([
                        hadolint, '--config', str(config_path), '--format', 'json',
                        '--no-fail', '--disable-ignore-pragma', *paths,
                    ], capture_output=True, text=True, encoding='utf-8', timeout=timeout, env=env)
                    if result.returncode:
                        if 'CallStack' in result.stderr or 'Exception' in result.stderr:
                            runtime_error = result.stderr.strip()[:4000]
                        else:
                            raise RuntimeError(f'Hadolint failed: {result.stderr.strip()}')
                except subprocess.TimeoutExpired:
                    runtime_error = f'Hadolint exceeded {timeout} seconds'
                if runtime_error:
                    if len(batch) > 1:
                        middle = len(batch) // 2
                        return run_batch(batch[:middle]) + run_batch(batch[middle:])
                    digest, path = batch[0]
                    path.unlink()
                    return [(digest, {'status': 'tool-error', 'findings': [], 'error': runtime_error})]
                try:
                    entries = json.loads(result.stdout)
                except ValueError as exc:
                    raise RuntimeError('Hadolint returned invalid JSON') from exc
                if not isinstance(entries, list):
                    raise RuntimeError('Hadolint JSON must be a list of findings')
                by_path = {path: [] for path in paths}
                for entry in entries:
                    if not isinstance(entry, dict) or not all(k in entry for k in ('file', 'code', 'level', 'message', 'line')):
                        raise RuntimeError('Malformed Hadolint finding')
                    if entry['file'] not in by_path:
                        raise RuntimeError('Hadolint returned a file outside the batch')
                    if selected is not None and entry['code'] not in selected and entry['code'] != 'DL1000':
                        raise RuntimeError(f"Hadolint returned a rule outside the selection: {entry['code']}")
                    by_path[entry['file']].append({k: v for k, v in entry.items() if k != 'file'})
                records = []
                for digest, path in batch:
                    findings = by_path[str(path)]
                    status = 'parse-error' if any(f['code'] == 'DL1000' for f in findings) else 'scanned'
                    records.append((digest, {'status': status, 'findings': findings}))
                    path.unlink()
                return records

            def accept(digest, result, from_cache=False):
                nonlocal cached, executed
                if from_cache:
                    cached += 1
                else:
                    executed += result['status'] != 'encoding-error'
                    db.execute('INSERT OR REPLACE INTO scans VALUES (?,?,?)',
                               (fingerprint, digest, json.dumps(result, ensure_ascii=False)))
                statuses[digest] = result['status']
                counts = Counter((catalog.get(f['code'], f['level']), f['code']) for f in result['findings']
                                 if selected is None or f['code'] in selected)
                content_counts[digest] = [(level, code, number) for (level, code), number in sorted(counts.items())]
                if raw_log:
                    raw_log.write(json.dumps({'sha256': digest, **result}, ensure_ascii=False) + '\n')
                report()

            pending, batch, seen = deque(), [], set()
            with ThreadPoolExecutor(max_workers=workers) as pool, zipfile.ZipFile(archive_path) as archive:
                infos = members(archive)
                excluded_entries = len(archive.infolist()) - len(infos)
                for info in infos:
                    raw = archive.read(info)
                    recognizable = 'dockerfile' in Path(info.filename).name.lower()
                    encoding_error = None
                    try:
                        text = raw.decode('utf-8-sig')
                    except UnicodeDecodeError as exc:
                        text = None
                        encoding_error = str(exc)
                    if (text is None and not recognizable) or (text is not None and not recognizable and
                            not re.search(r'^\s*FROM\s+\S', text, re.MULTILINE | re.IGNORECASE)):
                        skipped += 1
                        if len(skipped_sample) < 20:
                            skipped_sample.append(info.filename)
                        continue
                    digest = hashlib.sha256(raw).hexdigest()
                    files.append((info.filename, digest))
                    if digest in seen:
                        continue
                    seen.add(digest)
                    cached_row = db.execute('SELECT result FROM scans WHERE config=? AND digest=?',
                                            (fingerprint, digest)).fetchone()
                    if cached_row:
                        accept(digest, json.loads(cached_row[0]), True)
                        continue
                    if text is None:
                        accept(digest, {'status': 'encoding-error', 'findings': [], 'error': encoding_error})
                        continue
                    path = temp / digest
                    path.write_bytes(text.encode('utf-8'))
                    batch.append((digest, path))
                    if len(batch) == batch_size:
                        pending.append(pool.submit(run_batch, batch))
                        batch = []
                    if len(pending) >= workers * 2:
                        for key, result in pending.popleft().result():
                            accept(key, result)
                        db.commit()
                if batch:
                    pending.append(pool.submit(run_batch, batch))
                for future in pending:
                    for key, result in future.result():
                        accept(key, result)
                    db.commit()
            if not files:
                raise ValueError('No Dockerfiles were found in the ZIP')
            rows, summary = [], Counter()
            for name, digest in files:
                status = statuses[digest]
                summary[status] += 1
                rows.extend((name, severity, code, number) for severity, code, number in content_counts[digest])
                if file_log:
                    file_log.write(json.dumps({'file': name, 'sha256': digest, 'status': status}, ensure_ascii=False) + '\n')
                if error_log and status != 'scanned':
                    error_log.write(json.dumps({'file': name, 'sha256': digest, 'status': status}) + '\n')
            frame = pd.DataFrame.from_records(rows, columns=COLUMNS)
            if not frame.empty:
                frame.sort_values(COLUMNS[:3], inplace=True, ignore_index=True)
            status = ('completed-with-tool-errors' if summary['tool-error'] else
                      'completed-with-input-errors' if summary['parse-error'] or summary['encoding-error'] else 'completed')
            manifest = {
                'status': status, 'version': version, 'binary_sha256': binary_sha, 'config_sha256': fingerprint,
                'archive': Path(archive_path).name, 'archive_bytes': Path(archive_path).stat().st_size,
                'selected_rules': sorted(selected) if selected is not None else 'ALL',
                'candidate_files': len(files), 'scanned_files': summary['scanned'] + summary['parse-error'],
                'parsed_files': summary['scanned'], 'parse_error_files': summary['parse-error'],
                'encoding_error_files': summary['encoding-error'], 'tool_error_files': summary['tool-error'],
                'skipped_files': skipped, 'excluded_archive_entries': excluded_entries, 'skipped_sample': skipped_sample,
                'unique_contents': len(seen), 'duplicate_files_reused': len(files) - len(seen),
                'unique_executed': executed, 'unique_cache_hits': cached, 'csv_rows': len(frame),
                'finding_count': int(frame['COUNT'].sum()) if not frame.empty else 0,
                'elapsed_seconds': round(time.monotonic() - started, 2),
                'evidence_format': 'Raw findings once per SHA-256 in hadolint-findings.jsonl; scan-files.jsonl maps original paths to content/status. DL1000 is retained in ALL results; selected scans keep parse errors in evidence only.',
            }
            if evidence:
                write_json(evidence / 'scan-manifest.json', manifest)
                write_json(evidence / 'scan-status.json', {'status': status})
            report(True)
            frame.attrs['scan_status'] = status
            return frame
    finally:
        db.commit()
        db.close()
        for stream in (raw_log, file_log, error_log):
            if stream:
                stream.close()
