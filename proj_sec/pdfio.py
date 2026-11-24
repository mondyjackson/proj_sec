from __future__ import annotations

import hashlib
import re
from dataclasses import asdict, dataclass
from pathlib import Path

from pypdf import PdfReader

from .common import normalize


@dataclass(frozen=True)
class Section:
    cis_id: str
    title: str
    text: str


@dataclass(frozen=True)
class Document:
    path: Path
    sha256: str
    pages: int
    text: str


def read_pdf(path: Path | str) -> Document:
    path = Path(path).expanduser().resolve()
    if not path.is_file() or path.suffix.lower() != ".pdf":
        raise ValueError(f"Expected an existing PDF file: {path}")
    if path.stat().st_size > 50_000_000:
        raise ValueError("PDF exceeds the 50 MB input limit")
    content = path.read_bytes()
    if b"%PDF-" not in content[:1024]:
        raise ValueError(f"File does not have a PDF header: {path.name}")
    try:
        reader = PdfReader(path)
        if reader.is_encrypted:
            raise ValueError("Encrypted PDFs are not supported")
        if not 1 <= len(reader.pages) <= 1000:
            raise ValueError("Expected between 1 and 1000 PDF pages")
        pages = [page.extract_text() or "" for page in reader.pages]
    except Exception as exc:
        raise ValueError(f"Cannot read PDF {path.name}: {exc}") from exc
    text = "\n".join(pages)
    if not normalize(text):
        raise ValueError(f"No extractable text in {path.name}; OCR would be required")
    return Document(path, hashlib.sha256(content).hexdigest(), len(pages), text)


def split_sections(document: Document) -> list[Section]:
    lines = [line.strip() for line in document.text.splitlines()]
    text = "\n".join(line for line in lines
                     if not re.fullmatch(r"Page\s+\d+", line)
                     and line != "Internal Only - General")
    # The Profile Applicability marker distinguishes real controls from TOC entries.
    heading = re.compile(r"^(\d+(?:\.\d+){1,3})[ \t]+(.+)$")
    lines = text.splitlines()
    matches = []
    for index, line in enumerate(lines):
        start = heading.match(line)
        if not start:
            continue
        title_lines = [start.group(2)]
        for end in range(index + 1, min(index + 9, len(lines))):
            if heading.match(lines[end]):
                break
            if lines[end] == "Profile Applicability:":
                title = normalize(" ".join(title_lines))
                if re.search(r"\((Manual|Automated)\)$", title):
                    title = re.sub(r"\s*\((Manual|Automated)\)$", "", title)
                    matches.append((index, end + 1, start.group(1), title))
                break
            title_lines.append(lines[end])
    if not matches:
        raise ValueError(f"No CIS recommendation sections found in {document.path.name}")
    sections = []
    seen = set()
    for i, match in enumerate(matches):
        start, end, cis_id, title = match
        if cis_id in seen:
            raise ValueError(f"Repeated recommendation identifier: {cis_id}")
        seen.add(cis_id)
        body = "\n".join(lines[end:matches[i + 1][0] if i + 1 < len(matches) else len(lines)])
        fields = []
        for field in ("Description", "Remediation"):
            found = re.search(
                rf"^{field}:\s*\n(.*?)(?=^(?:Rationale|Impact|Audit|Remediation|Default Value|References|CIS Controls):|\Z)",
                body, re.MULTILINE | re.DOTALL,
            )
            if found and normalize(found.group(1)):
                fields.append(field + ":\n" + found.group(1).strip())
        if not fields:
            raise ValueError(f"No Description or Remediation text for {cis_id}")
        sections.append(Section(cis_id, title, "\n\n".join(fields)))
    return sections


def section_dicts(document: Document) -> list[dict]:
    return [asdict(section) for section in split_sections(document)]
