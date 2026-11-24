from __future__ import annotations

import csv
import io
from pathlib import Path

from .common import NO_NAMES, NO_REQUIREMENTS, load_kdes, name_key, normalize, write_text


def load_yaml_pair(first: Path | str, second: Path | str) -> tuple[dict, dict]:
    """Task 2, function 1: load and validate both KDE YAML documents."""
    return load_kdes(first), load_kdes(second)


def _index(document: dict) -> dict:
    indexed = {}
    for element in document.values():
        key = name_key(element["name"])
        name, requirements = indexed.setdefault(key, (normalize(element["name"]), set()))
        requirements.update(normalize(requirement) for requirement in element["requirements"])
    return indexed


def _csv(rows) -> str:
    buffer = io.StringIO(newline="")
    csv.writer(buffer, lineterminator="\n").writerows(rows)
    return buffer.getvalue()


def compare_names(documents: tuple[dict, dict], output: Path | str) -> Path:
    """Task 2, function 2: write the symmetric difference of element names."""
    left, right = map(_index, documents)
    names = [(left.get(key) or right[key])[0] for key in sorted(left.keys() ^ right.keys())]
    return write_text(output, _csv((name,) for name in names) if names else NO_NAMES + "\n")


def compare_requirements(documents: tuple[dict, dict], output: Path | str) -> Path:
    """Task 2, function 3: write changed NAME,REQU tuples using CSV quoting."""
    left, right = map(_index, documents)
    rows = []
    for key in sorted(left.keys() | right.keys()):
        name = (left.get(key) or right[key])[0]
        old = left.get(key, ("", set()))[1]
        new = right.get(key, ("", set()))[1]
        rows.extend((name, requirement) for requirement in sorted(old ^ new))
    return write_text(output, _csv(rows) if rows else NO_REQUIREMENTS + "\n")
