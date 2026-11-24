from __future__ import annotations

import csv
import io
import json
import re
import stat
import subprocess
import shutil
import zipfile
from pathlib import Path, PurePosixPath

import pandas as pd

from .common import (COLUMNS, NO_DIFFERENCES, NO_MAPPING, NO_NAMES, NO_REQUIREMENTS,
                     external_environment, name_key, write_text)

# Deliberately narrow, partial mappings. See docs/RULE_MAPPING.md.
MAPPINGS = (
    (r"^ensure that a user for the container has been created$", "DL3002"),
    (r"^ensure that unnecessary packages are not installed in the container$", "DL3015"),
    (r"^ensure that healthcheck instructions have been added to container images$", "DL3057"),
    (r"^ensure that copy is used instead of add in dockerfiles$", "DL3020"),
)


def _rows(text: str, width: int) -> list[tuple]:
    rows = list(csv.reader(io.StringIO(text, newline=""), strict=True))
    if not rows or any(len(row) != width or any(not cell.strip() for cell in row) for row in rows):
        raise ValueError(f"Expected nonempty CSV tuples with {width} field(s)")
    return [tuple(row) for row in rows]


def load_difference_reports(names: Path | str, requirements: Path | str) -> tuple[str, str]:
    """Task 3, function 1: load and validate the two comparator TEXT files."""
    texts = []
    for path, marker, width in ((names, NO_NAMES, 1), (requirements, NO_REQUIREMENTS, 2)):
        path = Path(path)
        if path.stat().st_size > 10_000_000:
            raise ValueError("Difference report exceeds the 10 MB input limit")
        text = path.read_text(encoding="utf-8").strip()
        if text != marker:
            _rows(text, width)
        texts.append(text)
    return tuple(texts)


def map_hadolint_rules(reports: tuple[str, str], output: Path | str) -> Path:
    """Task 3, function 2: map only supported Dockerfile-related differences."""
    names, requirements = reports
    if names == NO_NAMES and requirements == NO_REQUIREMENTS:
        return write_text(output, NO_DIFFERENCES + "\n")
    changed_names = []
    if names != NO_NAMES:
        changed_names.extend(row[0] for row in _rows(names, 1))
    if requirements != NO_REQUIREMENTS:
        changed_names.extend(row[0] for row in _rows(requirements, 2))
    rules = sorted({rule for name in changed_names for pattern, rule in MAPPINGS
                    if re.fullmatch(pattern, name_key(name))})
    return write_text(output, "\n".join(rules) + "\n" if rules else NO_MAPPING + "\n")


def _selection(path: Path | str) -> set[str] | None:
    text = Path(path).read_text(encoding="utf-8").strip()
    if text in (NO_DIFFERENCES, NO_MAPPING):
        return None
    lines = text.splitlines()
    if not lines or any(not re.fullmatch(r"(?:DL|SC)\d{4}", line) for line in lines):
        raise ValueError("Expected rule IDs or an exact no-difference/no-mapping marker")
    return set(lines)


def _config(selected: set[str] | None) -> dict:
    # Both supported Hadolint versions accept an ignore list. Their rule codes
    # are text values. Ignore every DL/SC code except the chosen allowlist.
    ignored = [] if selected is None else [
        code for prefix in ("DL", "SC") for number in range(10000)
        if (code := f"{prefix}{number:04d}") not in selected and code != "DL1000"
    ]
    overrides = {}
    if selected is None or "DL3057" in selected:
        overrides["warning"] = ["DL3057"]  # Missing HEALTHCHECK is opt-in upstream.
    if selected is None or "DL1001" in selected:
        overrides["style"] = ["DL1001"]
    return {"ignored": ignored, "override": overrides, "disable-ignore-pragma": True}


def _members(archive: zipfile.ZipFile) -> list[zipfile.ZipInfo]:
    members = archive.infolist()
    if len(members) > 1_000_000 or sum(info.file_size for info in members) > 1_000_000_000:
        raise ValueError("ZIP exceeds the member count or expanded size limit")
    files, seen = [], set()
    for info in members:
        name = info.filename
        path = PurePosixPath(name)
        if path.is_absolute() or ".." in path.parts or "\\" in name or ":" in name:
            raise ValueError(f"Unsafe ZIP path: {name}")
        if stat.S_ISLNK(info.external_attr >> 16):
            raise ValueError(f"ZIP symbolic links are not supported: {name}")
        if info.flag_bits & 1:
            raise ValueError("Encrypted ZIP entries are not supported")
        if info.is_dir() or name.startswith("__MACOSX/") or path.name.startswith("."):
            continue
        if name in seen:
            raise ValueError(f"Duplicate ZIP member: {name}")
        seen.add(name)
        if info.file_size > 2_000_000:
            raise ValueError(f"ZIP member exceeds 2 MB: {name}")
        files.append(info)
    return files  # Preserve archive order for efficient reads; CSV is sorted later.



def _hadolint_catalog(version_output: str) -> dict[str, str]:
    versions = json.loads(Path(__file__).with_name("hadolint_rules.json").read_text())["versions"]
    # Require an exact supported stable release, including the patch number.
    match = re.search(r"(?<![\w.])(\d+\.\d+\.\d+)(?![\w.+-])", version_output)
    version = match.group(1) if match else None
    if version not in versions:
        raise ValueError("Supported Hadolint versions: " + ", ".join(sorted(versions))
                         + "; received " + repr(version_output.strip()))
    return versions[version]["default_severities"]


def run_hadolint(mapping: Path | str, archive_path: Path | str, *,
                  hadolint: str = "hadolint", evidence_dir: Path | str | None = None,
                  timeout: float = 60, cache_path: Path | str | None = None,
                  workers: int = 4, batch_size: int = 256, progress=None) -> pd.DataFrame:
    """Task 3, function 3: run bounded batches, preserving every original path."""
    from .scan_engine import scan_archive
    selected = _selection(mapping)
    env = {key: value for key, value in external_environment().items() if not key.startswith("HADOLINT_")}
    resolved = shutil.which(hadolint)
    if resolved is None:
        raise FileNotFoundError(f"Hadolint executable not found: {hadolint}")
    version_run = subprocess.run([resolved, "--version"], capture_output=True, text=True,
                                 timeout=timeout, check=True, env=env)
    catalog = _hadolint_catalog(version_run.stdout)
    if selected and any(code.startswith("DL") and code not in catalog for code in selected):
        raise ValueError("Selected DL rule is not in the catalog for this Hadolint version")
    return scan_archive(archive_path, _members, selected, _config(selected), catalog,
                        hadolint=resolved, version=version_run.stdout.strip(), env=env,
                        evidence_dir=evidence_dir, cache_path=cache_path, workers=workers,
                        batch_size=batch_size, timeout=timeout, progress=progress)


def export_csv(results: pd.DataFrame, output: Path | str) -> Path:
    """Task 3, function 4: export the four required CSV columns."""
    if list(results.columns) != COLUMNS:
        raise ValueError(f"Expected CSV columns {COLUMNS}")
    if not results.empty:
        if results[COLUMNS[:3]].isna().any().any() or results["COUNT"].isna().any():
            raise ValueError("CSV results must not contain missing values")
        if any(not isinstance(n, (int, float)) or n < 1 or int(n) != n for n in results["COUNT"]):
            raise ValueError("COUNT must contain positive integers")
    return write_text(output, results.to_csv(index=False, lineterminator="\n"))
