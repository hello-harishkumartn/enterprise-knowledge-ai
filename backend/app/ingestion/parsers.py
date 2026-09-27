"""Format-specific parsers that all normalize to the same `ParsedBlock` shape.

A block is a single paragraph-ish unit of text plus the metadata the chunker
needs to make heading-aware, page-aware chunks: which heading it falls under
and (when the format has real pagination) which page it came from.
"""
import re
from dataclasses import dataclass
from pathlib import Path

from docx import Document as DocxDocument
from markdown_it import MarkdownIt
from pypdf import PdfReader

_md = MarkdownIt()


@dataclass
class ParsedBlock:
    text: str
    section: str | None = None
    page_number: int | None = None


class UnsupportedFormatError(ValueError):
    pass


def parse_document(file_path: str | Path, file_format: str) -> list[ParsedBlock]:
    file_format = file_format.lower().lstrip(".")
    file_path = Path(file_path)
    if file_format == "pdf":
        return _parse_pdf(file_path)
    if file_format == "docx":
        return _parse_docx(file_path)
    if file_format in ("md", "markdown"):
        return _parse_markdown(file_path.read_text(encoding="utf-8"))
    if file_format == "txt":
        return _parse_txt(file_path.read_text(encoding="utf-8"))
    raise UnsupportedFormatError(f"Unsupported document format: {file_format}")


def _clean(text: str) -> str:
    text = text.replace("\r\n", "\n").replace("\r", "\n")
    text = re.sub(r"[ \t]+", " ", text)
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()


def _parse_pdf(file_path: Path) -> list[ParsedBlock]:
    # pypdf's extract_text() gives one line per visual line of text, not one
    # blank-line-delimited block per paragraph — PDFs have no semantic
    # paragraph markers, only positioned glyphs, so unlike DOCX/Markdown/TXT
    # there is no `\n\n` to split on here. Consecutive non-heading lines are
    # accumulated into a paragraph and flushed on the next heading or blank
    # line, mirroring how the other formats build up paragraph blocks.
    reader = PdfReader(str(file_path))
    blocks: list[ParsedBlock] = []
    current_section: str | None = None
    for page_number, page in enumerate(reader.pages, start=1):
        raw = page.extract_text() or ""
        raw = _clean(raw)
        if not raw:
            continue

        paragraph_lines: list[str] = []

        def flush_paragraph(section: str | None = None, page_number: int = page_number):
            # paragraph_lines is mutated in place (not reassigned) and this
            # is always called synchronously within the same page iteration,
            # so the "stale closure" case B023 warns about doesn't apply.
            if paragraph_lines:  # noqa: B023
                blocks.append(
                    ParsedBlock(text=" ".join(paragraph_lines), section=section, page_number=page_number)  # noqa: B023
                )
                paragraph_lines.clear()  # noqa: B023

        for line in raw.split("\n"):
            line = line.strip()
            if not line:
                flush_paragraph(current_section)
                continue
            if _looks_like_heading(line):
                flush_paragraph(current_section)
                current_section = line
                continue
            paragraph_lines.append(line)
        flush_paragraph(current_section)
    return blocks


def _parse_docx(file_path: Path) -> list[ParsedBlock]:
    doc = DocxDocument(str(file_path))
    blocks: list[ParsedBlock] = []
    current_section: str | None = None
    for para in doc.paragraphs:
        text = para.text.strip()
        if not text:
            continue
        style = (para.style.name or "").lower() if para.style else ""
        if "heading" in style or "title" in style:
            current_section = text
            continue
        blocks.append(ParsedBlock(text=text, section=current_section, page_number=None))
    return blocks


def _parse_markdown(raw: str) -> list[ParsedBlock]:
    raw = _clean(raw)
    tokens = _md.parse(raw)
    blocks: list[ParsedBlock] = []
    section_stack: list[tuple[int, str]] = []  # (level, text)
    i = 0
    pending_heading_level: int | None = None
    while i < len(tokens):
        tok = tokens[i]
        if tok.type == "heading_open":
            pending_heading_level = int(tok.tag[1])
        elif tok.type == "inline" and pending_heading_level is not None:
            heading_text = tok.content.strip()
            section_stack = [s for s in section_stack if s[0] < pending_heading_level]
            section_stack.append((pending_heading_level, heading_text))
            pending_heading_level = None
        elif tok.type == "inline":
            text = tok.content.strip()
            if text:
                section = " > ".join(s[1] for s in section_stack) or None
                blocks.append(ParsedBlock(text=text, section=section, page_number=None))
        i += 1
    return blocks


def _parse_txt(raw: str) -> list[ParsedBlock]:
    raw = _clean(raw)
    blocks: list[ParsedBlock] = []
    current_section: str | None = None
    for para in raw.split("\n\n"):
        para = para.strip()
        if not para:
            continue
        if _looks_like_heading(para):
            current_section = para
            continue
        blocks.append(ParsedBlock(text=para, section=current_section, page_number=None))
    return blocks


def _looks_like_heading(text: str) -> bool:
    if len(text) > 90 or "\n" in text:
        return False
    if text.endswith((".", ",", ";")):
        return False
    words = text.split()
    if not words:
        return False
    if text.isupper() and len(words) <= 12:
        return True
    if re.match(r"^(\d+\.)+\s*\S", text) and len(words) <= 12:
        return True
    title_case_words = sum(1 for w in words if w[:1].isupper())
    return len(words) <= 10 and title_case_words / len(words) >= 0.7
