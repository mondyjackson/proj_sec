"""Restore the reviewed final outputs, including the 15 identical scan CSVs."""
import argparse
import hashlib
from pathlib import Path, PurePosixPath
import shutil
import zipfile

PREFIX = PurePosixPath('outputs/final')


def digest(path):
    with path.open('rb') as stream:
        return hashlib.file_digest(stream, 'sha256').hexdigest()


def restore(bundle, output):
    output = output.expanduser().resolve()
    with zipfile.ZipFile(bundle) as archive:
        entries = archive.infolist()
        if sum(i.file_size for i in entries) > 200_000_000:
            raise ValueError('Result bundle exceeds the expanded size limit')
        plan, seen = [], set()
        for info in entries:
            rel = PurePosixPath(info.filename)
            if rel.is_absolute() or '..' in rel.parts or '\\' in info.filename:
                raise ValueError('Unsafe archive path')
            if not rel.is_relative_to(PREFIX):
                raise ValueError('Unexpected result archive prefix')
            if info.is_dir():
                continue
            rel = rel.relative_to(PREFIX)
            target = output / str(rel)
            if rel in seen or target.is_symlink() or not target.resolve().is_relative_to(output):
                raise ValueError('Duplicate path or unsafe destination')
            seen.add(rel)
            with archive.open(info) as stream:
                expected = hashlib.file_digest(stream, 'sha256').hexdigest()
            if target.exists() and (not target.is_file() or digest(target) != expected):
                raise ValueError(f'Existing file differs; choose a fresh output directory: {target}')
            plan.append((info, target))
        hashes = {}
        for line in archive.read('outputs/final/csv-sha256.txt').decode().splitlines():
            sha, name = line.split(None, 1)
            rel = PurePosixPath(name.strip())
            if '..' in rel.parts or not rel.is_relative_to(PREFIX) or rel.name != 'results.csv':
                raise ValueError('Unsafe CSV manifest path')
            if len(sha) != 64 or any(c not in '0123456789abcdef' for c in sha):
                raise ValueError('Invalid CSV digest')
            target = output / str(rel.relative_to(PREFIX))
            if target.is_symlink() or not target.resolve().is_relative_to(output) or target in hashes:
                raise ValueError('Unsafe or duplicate CSV destination')
            if target.exists() and digest(target) != sha:
                raise ValueError(f'Existing CSV differs: {target}')
            hashes[target] = sha
        if len(hashes) != 15 or len(set(hashes.values())) != 1:
            raise ValueError('Expected 15 scan CSVs sharing one verified digest')
        with archive.open('outputs/final/v0-v1/zero-shot/results.csv') as stream:
            if hashlib.file_digest(stream, 'sha256').hexdigest() != next(iter(hashes.values())):
                raise ValueError('Included CSV does not match the supplied hashes')
        for info, target in plan:
            if target.exists():
                continue
            target.parent.mkdir(parents=True, exist_ok=True)
            with archive.open(info) as source, target.open('xb') as destination:
                shutil.copyfileobj(source, destination)
        seed = output / 'v0-v1/zero-shot/results.csv'
        for target, sha in hashes.items():
            if not target.exists():
                target.parent.mkdir(parents=True, exist_ok=True)
                shutil.copyfile(seed, target)
            if digest(target) != sha:
                raise ValueError(f'Restored CSV hash mismatch: {target}')
    print(f'Restored final reports and all 15 hash-verified scan CSVs to {output}')


if __name__ == '__main__':
    root = Path(__file__).resolve().parents[1]
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--bundle', type=Path, default=root/'submission/final-results.zip')
    parser.add_argument('--output', type=Path, default=root/'outputs/final')
    args = parser.parse_args()
    restore(args.bundle, args.output)
