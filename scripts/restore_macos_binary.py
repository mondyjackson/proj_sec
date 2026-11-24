"""Restore the exact, runtime-tested Apple Silicon macOS executable."""
import argparse
import hashlib
import io
import json
from pathlib import Path
import tarfile


def restore(source, output):
    manifest = json.loads((source/'manifest.json').read_text())
    chunks = []
    for part in manifest['parts']:
        name = part['name']
        if Path(name).name != name:
            raise ValueError('Invalid part filename')
        content = (source/name).read_bytes()
        if len(content) != part['bytes'] or hashlib.sha256(content).hexdigest() != part['sha256']:
            raise ValueError(f'Part checksum mismatch: {name}')
        chunks.append(content)
    archive = b''.join(chunks)
    if len(archive) != manifest['archive_bytes'] or hashlib.sha256(archive).hexdigest() != manifest['archive_sha256']:
        raise ValueError('Mac archive checksum mismatch')
    with tarfile.open(fileobj=io.BytesIO(archive), mode='r:gz') as tar:
        members = tar.getmembers()
        if len(members) != 1 or members[0].name != 'proj-sec' or not members[0].isfile():
            raise ValueError('Expected exactly one regular executable')
        binary = tar.extractfile(members[0]).read()
    if len(binary) != manifest['binary_bytes'] or hashlib.sha256(binary).hexdigest() != manifest['binary_sha256']:
        raise ValueError('Mac executable checksum mismatch')
    output = output.expanduser().resolve()
    archive_name = manifest['archive']
    if Path(archive_name).name != archive_name:
        raise ValueError('Invalid archive filename')
    targets = [(output/'proj-sec', binary), (output/archive_name, archive)]
    for path, content in targets:
        if path.is_symlink() or (path.exists() and (not path.is_file() or path.read_bytes() != content)):
            raise ValueError(f'Existing file differs; choose a fresh --output directory: {path}')
    output.mkdir(parents=True, exist_ok=True)
    for path, content in targets:
        if not path.exists():
            path.write_bytes(content)
    (output/'proj-sec').chmod(0o755)
    print(f'Restored verified macOS ARM64 executable: {output / "proj-sec"}')
    print(f'Archive SHA-256: {manifest["archive_sha256"]}')
    print('This binary requires Apple Silicon macOS. Use the Linux Actions artifact on Linux.')


if __name__ == '__main__':
    root = Path(__file__).resolve().parents[1]
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, default=root/'dist')
    args = parser.parse_args()
    restore(root/'submission/macos', args.output)
