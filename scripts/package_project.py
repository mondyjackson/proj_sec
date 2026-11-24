"""Build a private handoff ZIP; dataset, credentials, and environments stay out."""
import argparse
from pathlib import Path
import zipfile


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, default=Path('../Proj_Sec_Project.zip'))
    parser.add_argument('--include-baseline', action='store_true')
    parser.add_argument('--include-evidence', action='store_true')
    parser.add_argument('--include-linux-binary', action='store_true')
    args = parser.parse_args()
    root = Path(__file__).resolve().parents[1]
    files = []
    for name in ('main.py', 'README.md', 'START_HERE.md', 'TOMORROW_START_HERE.md', 'PROMPT.md',
                 'requirements.txt', 'requirements-core.txt', 'requirements-model.txt',
                 'requirements-build.txt', '.gitignore'):
        files.append(root / name)
    for folder in ('proj_sec', 'scripts', 'tests', 'examples', '.github', '.githooks', 'docs'):
        files += [p for p in (root / folder).rglob('*') if p.is_file() and '__pycache__' not in p.parts
                  and p.suffix != '.pyc']
    files += sorted((root / 'data').glob('*.pdf'))
    if args.include_baseline:
        baseline = root / 'outputs/dataset-baseline'
        for name in ('results.csv', 'scan-manifest.json', 'scan-status.json', 'scan-errors.jsonl',
                     'element-names.txt', 'element-requirements.txt', 'hadolint-rules.txt', 'README.md'):
            path = baseline / name
            if path.is_file():
                files.append(path)
        if args.include_evidence:
            files += [baseline / name for name in ('scan-files.jsonl', 'hadolint-findings.jsonl')]
    if args.include_linux_binary:
        files.append(root / 'dist/proj-sec')
    target = args.output.resolve()
    temporary = target.with_suffix('.new.zip')
    with zipfile.ZipFile(temporary, 'w', compression=zipfile.ZIP_DEFLATED, compresslevel=9) as archive:
        for path in sorted(set(files)):
            archive.write(path, str(Path('proj_sec') / path.relative_to(root)))
    with zipfile.ZipFile(temporary) as archive:
        damaged = archive.testzip()
        if damaged:
            raise RuntimeError(f'Corrupt package member: {damaged}')
        if any(name.endswith('dockerfiles.zip') for name in archive.namelist()):
            raise RuntimeError('The instructor dataset must not be embedded')
    temporary.replace(target)
    print(f'{target}: {target.stat().st_size} bytes, {len(set(files))} files')


if __name__ == '__main__':
    main()
