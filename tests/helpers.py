from pathlib import Path

from pypdf import PdfWriter
from pypdf.generic import DecodedStreamObject, DictionaryObject, NameObject


def make_pdf(path: Path, text: str):
    writer = PdfWriter()
    page = writer.add_blank_page(width=612, height=792)
    font = DictionaryObject({NameObject("/Type"): NameObject("/Font"),
                             NameObject("/Subtype"): NameObject("/Type1"),
                             NameObject("/BaseFont"): NameObject("/Helvetica")})
    page[NameObject("/Resources")] = DictionaryObject({
        NameObject("/Font"): DictionaryObject({NameObject("/F1"): writer._add_object(font)})})
    stream = DecodedStreamObject()
    commands = ["BT /F1 10 Tf 12 TL 50 750 Td"]
    for line in text.splitlines():
        escaped = line.replace("\\", "\\\\").replace("(", "\\(").replace(")", "\\)")
        commands.append(f"({escaped}) Tj T*")
    stream.set_data(("\n".join(commands) + "\nET").encode("ascii"))
    page[NameObject("/Contents")] = writer._add_object(stream)
    writer.write(path)


TEXT = """Page 1
Internal Only - General
4.1 Ensure that a user for the container has been created (Manual)
Profile Applicability:
Level 1
Description:
Containers should run as a non-root user.
Rationale:
Limit privileges.
Remediation:
Set USER app.
Default Value:
Root.
CIS Controls:
6.1 Establish an Access Granting Process
Grant access on hire.
4.9 Ensure that COPY is used instead of ADD in Dockerfiles
(Manual)
Profile Applicability:
Level 1
Description:
Use COPY for local files.
Remediation:
Replace ADD with COPY.
References:
https://example.invalid
"""


def is_remediation_prompt(prompt):
    """Recognize either request format for the small fixed test PDF."""
    if '<source>\nRemediation:' in prompt:
        return True
    actual = prompt.split('Source excerpts:\n')[-1]
    return actual.startswith('[1] Set USER app.') or actual.startswith('[1] Replace ADD with COPY.')
