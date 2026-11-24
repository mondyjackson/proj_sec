"""Install checksum-verified Hadolint 2.12.0 for the current platform."""
import argparse
import hashlib
import platform
import subprocess
import urllib.request
from pathlib import Path


def select_asset(system, machine, allow_rosetta=False):
    machine = machine.lower()
    if system == 'Darwin' and machine in ('arm64', 'aarch64'):
        if not allow_rosetta:
            raise ValueError('Hadolint 2.12.0 uses its Intel Mac build on Apple Silicon. Re-run with --allow-rosetta if you want to use that build; Rosetta must already be installed.')
        return 'Darwin-x86_64'
    platforms = {('Linux', 'x86_64'): 'Linux-x86_64', ('Linux', 'aarch64'): 'Linux-arm64',
                 ('Linux', 'arm64'): 'Linux-arm64', ('Darwin', 'x86_64'): 'Darwin-x86_64',
                 ('Windows', 'amd64'): 'Windows-x86_64.exe', ('Windows', 'x86_64'): 'Windows-x86_64.exe'}
    if (system, machine) not in platforms:
        raise ValueError(f'No pinned release asset for {system}/{machine}')
    return platforms[system, machine]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, default=Path('tools'))
    parser.add_argument('--allow-rosetta', action='store_true', help='Use the Intel Mac binary on Apple Silicon; requires an existing Rosetta installation')
    args = parser.parse_args()
    system, machine = platform.system(), platform.machine().lower()
    try:
        asset = select_asset(system, machine, args.allow_rosetta)
    except ValueError as exc:
        raise SystemExit(str(exc)) from exc
    if system == 'Darwin' and machine in ('arm64', 'aarch64'):
        probe = subprocess.run(['/usr/bin/arch', '-x86_64', '/usr/bin/true'], capture_output=True)
        if probe.returncode:
            raise SystemExit('Rosetta is unavailable. Run softwareupdate --install-rosetta, review its license prompt, and then retry this command. No system installation was started by this script.')
    name = 'hadolint-' + asset
    base = 'https://github.com/hadolint/hadolint/releases/download/v2.12.0/'
    with urllib.request.urlopen(base + name, timeout=120) as response:
        content = response.read()
    with urllib.request.urlopen(base + name + '.sha256', timeout=30) as response:
        expected = response.read().decode().split()[0]
    actual = hashlib.sha256(content).hexdigest()
    if actual != expected:
        raise SystemExit('Hadolint checksum mismatch; nothing was installed')
    args.output.mkdir(parents=True, exist_ok=True)
    path = args.output / ('hadolint.exe' if system == 'Windows' else 'hadolint')
    path.write_bytes(content)
    path.chmod(0o755)
    subprocess.run([str(path.resolve()), '--version'], check=True)
    print(f'Installed {path.resolve()} (2.12.0, SHA256 {actual})')


if __name__ == '__main__':
    main()
