from __future__ import annotations

import json
import os
import re
import unicodedata
from pathlib import Path

import yaml

MODEL_ID = "google/gemma-3-1b-it"
MODEL_REVISION = "dcc83ea841ab6100d6b47a070329e1ba4cf78752"
PROMPT_TYPES = ("zero-shot", "few-shot", "chain-of-thought")
NO_NAMES = "NO DIFFERENCES IN REGARDS TO ELEMENT NAMES"
NO_REQUIREMENTS = "NO DIFFERENCES IN REGARDS TO ELEMENT REQUIREMENTS"
NO_DIFFERENCES = "NO DIFFERENCES FOUND"
NO_MAPPING = "NO MAPPING FOUND"
COLUMNS = ["FilePath", "DefaultSeverity", "RULEID", "COUNT"]


def external_environment() -> dict[str, str]:
    """Undo frozen-loader library-path changes before invoking external tools."""
    env = dict(os.environ)
    for key in ("LD_LIBRARY_PATH", "DYLD_LIBRARY_PATH"):
        if key + "_ORIG" in env:
            env[key] = env[key + "_ORIG"]
        elif getattr(__import__("sys"), "frozen", False):
            env.pop(key, None)
    return env


def normalize(text: str) -> str:
    return " ".join(unicodedata.normalize("NFKC", text).split())


def name_key(text: str) -> str:
    return normalize(text).casefold()


def write_text(path: Path | str, text: str) -> Path:
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(text, encoding="utf-8")
    temporary.replace(path)
    return path


def write_json(path: Path | str, value) -> Path:
    return write_text(path, json.dumps(value, ensure_ascii=False, indent=2) + "\n")


class UniqueLoader(yaml.SafeLoader):
    pass


def _unique_mapping(loader, node, deep=False):
    result = {}
    for key_node, value_node in node.value:
        key = loader.construct_object(key_node, deep=deep)
        if not isinstance(key, str):
            raise ValueError("YAML keys must be strings")
        if key in result:
            raise ValueError(f"Duplicate YAML key: {key}")
        result[key] = loader.construct_object(value_node, deep=deep)
    return result


UniqueLoader.add_constructor(yaml.resolver.BaseResolver.DEFAULT_MAPPING_TAG, _unique_mapping)


def load_kdes(path: Path | str) -> dict:
    path = Path(path)
    if path.stat().st_size > 10_000_000:
        raise ValueError("YAML exceeds the 10 MB input limit")
    raw = path.read_text(encoding="utf-8")
    # Aliases are unnecessary for the flat KDE schema and can form recursive graphs.
    if any(isinstance(token, (yaml.tokens.AliasToken, yaml.tokens.AnchorToken))
           for token in yaml.scan(raw)):
        raise ValueError("YAML aliases and anchors are not supported")
    data = yaml.load(raw, Loader=UniqueLoader)
    if not isinstance(data, dict):
        raise ValueError("KDE YAML must contain a dictionary")
    for key, value in data.items():
        if not re.fullmatch(r"element\d+", key) or not isinstance(value, dict):
            raise ValueError("Expected element<number> dictionaries")
        if not isinstance(value.get("name"), str) or not normalize(value["name"]):
            raise ValueError(f"Invalid element name: {key}")
        requirements = value.get("requirements")
        if not isinstance(requirements, list) or not requirements:
            raise ValueError(f"Expected a nonempty requirements list: {key}")
        if any(not isinstance(r, str) or not normalize(r) for r in requirements):
            raise ValueError(f"Invalid requirement: {key}")
    return data
