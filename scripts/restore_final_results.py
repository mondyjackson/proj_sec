"""Restore the exact verified five-pair outputs and all 15 scan CSV paths."""
import argparse
import hashlib
import io
import json
from pathlib import Path, PurePosixPath
import shutil
import zipfile

PAIRS = ('v0-v1', 'v0-v2', 'v1-v2', 'v1-v1', 'v2-v2')
STYLES = ('zero-shot', 'few-shot', 'chain-of-thought')


def digest(path):
    with path.open('rb') as stream:
        return hashlib.file_digest(stream, 'sha256').hexdigest()


def archive_from_parts(source):
    source = Path(source)
    manifest = json.loads((source / 'manifest.json').read_text())
    if not 0 < manifest['archive_bytes'] <= 100_000_000:
        raise ValueError('Result archive exceeds the size limit')
    chunks = []
    for part in manifest['parts']:
        name = part['name']
        if Path(name).name != name or '\\' in name:
            raise ValueError('Invalid result part filename')
        data = (source / name).read_bytes()
        if len(data) != part['bytes'] or hashlib.sha256(data).hexdigest() != part['sha256']:
            raise ValueError(f'Result part checksum mismatch: {name}')
        chunks.append(data)
    data = b''.join(chunks)
    if len(data) != manifest['archive_bytes'] or hashlib.sha256(data).hexdigest() != manifest['archive_sha256']:
        raise ValueError('Result archive checksum mismatch')
    return io.BytesIO(data)


def safe_relative(name):
    rel = PurePosixPath(name)
    if rel.is_absolute() or '..' in rel.parts or '\\' in name or not rel.parts:
        raise ValueError('Unsafe result path')
    return rel


def restore(bundle, output):
    output = Path(output).expanduser().resolve()
    with zipfile.ZipFile(bundle) as archive:
        entries = archive.infolist()
        if len(entries) > 1000 or sum(i.file_size for i in entries) > 512_000_000:
            raise ValueError('Result bundle exceeds the expanded size limit')
        names = [i.filename for i in entries]
        if len(names) != len(set(names)):
            raise ValueError('Duplicate archive entry')
        manifest = json.loads(archive.read('csv-manifest.json'))
        if manifest.get('format') != 'proj-sec-reviewed-results-v1':
            raise ValueError('Unexpected CSV manifest format')
        csvs = manifest['csv_paths']
        required = {f'{pair}/{style}/results.csv' for pair in PAIRS for style in STYLES}
        if set(csvs) != required:
            raise ValueError('Expected exactly the 15 assigned scan CSV paths')
        members = {}
        for relative, info in csvs.items():
            safe_relative(relative)
            member = info['archive_member']
            rel = safe_relative(member)
            expected = info['sha256']
            if (rel.parent != PurePosixPath('shared-csv') or rel.name != expected + '.csv'
                    or len(expected) != 64 or any(c not in '0123456789abcdef' for c in expected)):
                raise ValueError('Invalid CSV member/digest')
            if member not in members:
                entry = archive.getinfo(member)
                with archive.open(entry) as stream:
                    actual = hashlib.file_digest(stream, 'sha256').hexdigest()
                members[member] = (actual, entry.file_size)
            if members[member] != (expected, info['bytes']):
                raise ValueError('CSV content does not match its manifest')
        plan, seen = [], set()

        def destination(relative, sha):
            relative = safe_relative(relative)
            target = output / str(relative)
            if (relative in seen or target.is_symlink()
                    or not target.resolve().is_relative_to(output)):
                raise ValueError('Duplicate path or unsafe destination')
            seen.add(relative)
            if target.exists() and (not target.is_file() or digest(target) != sha):
                raise ValueError(f'Existing file differs; choose a fresh output directory: {target}')
            return target

        for entry in entries:
            rel = safe_relative(entry.filename)
            if entry.is_dir():
                continue
            if entry.filename == 'csv-manifest.json':
                continue
            if rel.parts[0] == 'shared-csv':
                if entry.filename not in members:
                    raise ValueError('Unreferenced scan CSV')
                continue
            if rel.parts[0] != 'coverage-final' or len(rel.parts) < 2:
                raise ValueError('Unexpected result archive prefix')
            with archive.open(entry) as stream:
                sha = hashlib.file_digest(stream, 'sha256').hexdigest()
            plan.append((entry.filename, destination(str(PurePosixPath(*rel.parts[1:])), sha)))
        csv_plan = [(info['archive_member'], destination(relative, info['sha256']))
                    for relative, info in csvs.items()]
        # All checks, including every existing-file conflict, finish before writes.
        for member, target in plan:
            if target.exists():
                continue
            target.parent.mkdir(parents=True, exist_ok=True)
            with archive.open(member) as source, target.open('xb') as stream:
                shutil.copyfileobj(source, stream)
        seeds = {}
        for member, target in csv_plan:
            if not target.exists():
                target.parent.mkdir(parents=True, exist_ok=True)
                with target.open('xb') as stream:
                    if member in seeds:
                        with seeds[member].open('rb') as seed:
                            shutil.copyfileobj(seed, stream)
                    else:
                        with archive.open(member) as source:
                            shutil.copyfileobj(source, stream)
            seeds.setdefault(member, target)
            if digest(target) != members[member][0]:
                raise ValueError(f'Restored CSV hash mismatch: {target}')
    print(f'Restored verified final reports and all 15 scan CSV paths to {output}')


if __name__ == '__main__':
    root = Path(__file__).resolve().parents[1]
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--bundle', type=Path, help='Optional original compact ZIP instead of repository parts')
    parser.add_argument('--output', type=Path, default=root / 'outputs/coverage-final')
    args = parser.parse_args()
    restore(args.bundle if args.bundle else archive_from_parts(root / 'submission/results'), args.output)
