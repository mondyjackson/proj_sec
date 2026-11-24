"""Explicitly install the repository's post-merge test hook without replacing others."""
import subprocess
from pathlib import Path

root = Path(__file__).resolve().parents[1]
result = subprocess.run(["git", "config", "--local", "--get", "core.hooksPath"],
                        cwd=root, capture_output=True, text=True)
if result.returncode not in (0, 1):
    raise SystemExit("Run this inside your project Git repository.")
if result.stdout.strip() not in ("", ".githooks"):
    raise SystemExit("An existing core.hooksPath is configured; integrate the hook manually.")
hooks = root / ".git" / "hooks"
if hooks.is_dir() and (hooks / "post-merge").exists() and not result.stdout.strip():
    raise SystemExit("An existing post-merge hook exists; integrate it manually.")
(root / ".githooks" / "post-merge").chmod(0o755)
subprocess.run(["git", "config", "--local", "core.hooksPath", ".githooks"], cwd=root, check=True)
print("Enabled local post-merge tests. Already-up-to-date pulls do not trigger this hook.")
