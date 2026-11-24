"""Run the five assigned pairs, sharing validated model and scanner caches."""
import argparse
from pathlib import Path
import shutil
import subprocess
import sys

PAIRS = ((0, 1), (0, 2), (1, 2), (1, 1), (2, 2))


def _default_hadolint():
    # Prefer an installed native scanner; retain the local installer fallback.
    return shutil.which('hadolint') or str(
        Path(__file__).resolve().parents[1] / 'tools'
        / ('hadolint.exe' if sys.platform == 'win32' else 'hadolint'))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--mode', choices=('prepare', 'extract', 'run'), default='prepare')
    parser.add_argument('--input-dir', type=Path, default=Path('data'))
    parser.add_argument('--output', type=Path, default=Path('outputs/final'))
    parser.add_argument('--device', choices=('auto', 'cpu', 'mps', 'cuda'), default='auto')
    parser.add_argument('--dtype', choices=('auto', 'float32', 'float16', 'bfloat16'), default='auto')
    parser.add_argument('--hadolint', default=_default_hadolint())
    parser.add_argument('--workers', type=int, default=2)
    args = parser.parse_args()
    root = Path(__file__).resolve().parents[1]
    for left, right in PAIRS:
        command = [sys.executable, str(root / 'main.py'), args.mode,
                   str(args.input_dir / f'docker-cis-v{left}.pdf'),
                   str(args.input_dir / f'docker-cis-v{right}.pdf'),
                   '--output', str(args.output / f'v{left}-v{right}')]
        if args.mode != 'prepare':
            command += ['--device', args.device, '--dtype', args.dtype, '--model-cache', '.cache/gemma']
        if args.mode == 'run':
            command += ['--dockerfiles', str(args.input_dir / 'dockerfiles.zip'),
                        '--hadolint', args.hadolint, '--workers', str(args.workers),
                        '--scan-cache', '.cache/hadolint.sqlite3']
        print(f'Starting {args.mode}: v{left}/v{right}', flush=True)
        subprocess.run(command, check=True)
    print(f'All five pairs finished in {args.mode} mode. Inspect output status files and quality before submission.')


if __name__ == '__main__':
    main()
