"""Build the platform-native executable; model packages stay in the active venv."""
import subprocess
import sys
from pathlib import Path

root = Path(__file__).resolve().parents[1]
subprocess.run([
    sys.executable, "-m", "PyInstaller", "--noconfirm", "--clean", "--onefile",
    "--name", "proj-sec", "--paths", str(root),
    "--add-data", f"{root / 'proj_sec' / 'hadolint_rules.json'}:proj_sec",
    "--add-data", f"{root / 'proj_sec' / 'workers' / 'gemma_worker.py'}:proj_sec/workers",
    "--exclude-module", "torch", "--exclude-module", "transformers",
    "--exclude-module", "accelerate", str(root / "main.py"),
], cwd=root, check=True)
