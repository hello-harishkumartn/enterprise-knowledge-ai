"""Heading/paragraph-aware chunker.

Deliberately NOT a fixed-N-character splitter. Blocks are grouped by their
section heading, then paragraphs are greedily packed into chunks up to
`target_tokens`, splitting on paragraph boundaries (or sentence boundaries
for a single oversized paragraph) rather than mid-sentence. A short token
overlap is carried into the next chunk of the same section so retrieval
doesn't lose context that sits right on a chunk boundary.
"""
import re
from dataclasses import dataclass

import tiktoken

from app.ingestion.parsers import ParsedBlock

_encoding = tiktoken.get_encoding("cl100k_base")

_SENTENCE_SPLIT = re.compile(r"(?<=[.!?])\s+")


def count_tokens(text: str) -> int:
    return len(_encoding.encode(text))


@dataclass
class Chunk:
    content: str
    section: str | None
    page_number: int | None
    token_count: int


def _split_oversized_paragraph(text: str, target_tokens: int) -> list[str]:
    sentences = _SENTENCE_SPLIT.split(text)
    parts: list[str] = []
    current: list[str] = []
    current_tokens = 0
    for sentence in sentences:
        sentence_tokens = count_tokens(sentence)
        if current and current_tokens + sentence_tokens > target_tokens:
            parts.append(" ".join(current))
            current, current_tokens = [], 0
        current.append(sentence)
        current_tokens += sentence_tokens
    if current:
        parts.append(" ".join(current))
    return parts


def chunk_blocks(
    blocks: list[ParsedBlock],
    target_tokens: int = 300,
    overlap_tokens: int = 40,
) -> list[Chunk]:
    if not blocks:
        return []

    # Group consecutive blocks that share the same section heading.
    groups: list[list[ParsedBlock]] = []
    for block in blocks:
        if groups and groups[-1][-1].section == block.section:
            groups[-1].append(block)
        else:
            groups.append([block])

    chunks: list[Chunk] = []
    for group in groups:
        section = group[0].section
        paragraphs: list[tuple[str, int | None]] = []
        for b in group:
            tokens = count_tokens(b.text)
            if tokens > target_tokens:
                for part in _split_oversized_paragraph(b.text, target_tokens):
                    paragraphs.append((part, b.page_number))
            else:
                paragraphs.append((b.text, b.page_number))

        current_texts: list[str] = []
        current_tokens = 0
        current_page: int | None = None

        def flush(section: str | None = section):
            # current_texts/current_page are `nonlocal`, not closed-over loop
            # variables — the `nonlocal` declaration is exactly the point.
            # flush() always runs synchronously within the same outer
            # iteration, so B023's "stale closure" concern doesn't apply.
            nonlocal current_texts, current_tokens, current_page
            if not current_texts:  # noqa: B023
                return
            content = "\n\n".join(current_texts)  # noqa: B023
            chunks.append(
                Chunk(
                    content=content,
                    section=section,
                    page_number=current_page,  # noqa: B023
                    token_count=count_tokens(content),
                )
            )

        for text, page in paragraphs:
            tokens = count_tokens(text)
            if current_texts and current_tokens + tokens > target_tokens:
                flush()
                # carry a small overlap forward for continuity
                overlap_text = current_texts[-1]
                if count_tokens(overlap_text) > overlap_tokens:
                    words = overlap_text.split()
                    overlap_text = " ".join(words[-overlap_tokens:])
                current_texts = [overlap_text] if overlap_tokens > 0 else []
                current_tokens = count_tokens(overlap_text) if current_texts else 0
                current_page = page
            if current_page is None:
                current_page = page
            current_texts.append(text)
            current_tokens += tokens
        flush()

    return chunks
