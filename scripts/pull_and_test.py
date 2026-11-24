"""Run git pull and tests even when Git reports the checkout is already up to date."""
import subprocess
import sys
from pathlib import Path

root = Path(__file__).resolve().parents[1]
subprocess.run(["git", "pull", *sys.argv[1:]], cwd=root, check=True)
subprocess.run([sys.executable, "-m", "unittest", "discover", "-s", "tests", "-v"], cwd=root, check=True)
