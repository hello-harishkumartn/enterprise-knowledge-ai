"""Turns the `[n]` markers the LLM was instructed to emit into real citation
objects, resolved strictly against the context that was actually sent —
never fabricated. A `[n]` the model hallucinates outside the given range is
dropped rather than guessed at.
"""
import re
from dataclasses import dataclass

from app.context.builder import BuiltContext

_CITATION_RE = re.compile(r"\[(\d+)\]")


@dataclass
class Citation:
    number: int
    document_id: str
    document_name: str
    section: str | None
    page_number: int | None
    passage: str

    def to_dict(self) -> dict:
        return {
            "number": self.number,
            "document_id": self.document_id,
            "document_name": self.document_name,
            "section": self.section,
            "page_number": self.page_number,
            "passage": self.passage,
        }


def extract_citations(answer_text: str, context: BuiltContext) -> list[Citation]:
    by_number = {cc.citation_number: cc.chunk for cc in context.chunks}
    cited_numbers = sorted({int(n) for n in _CITATION_RE.findall(answer_text)})

    citations: list[Citation] = []
    for number in cited_numbers:
        chunk = by_number.get(number)
        if chunk is None:
            continue  # hallucinated / out-of-range marker — never fabricate a source for it
        citations.append(
            Citation(
                number=number,
                document_id=chunk.document_id,
                document_name=chunk.document_name,
                section=chunk.section,
                page_number=chunk.page_number,
                passage=chunk.content,
            )
        )
    return citations
