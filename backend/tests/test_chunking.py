from app.ingestion.chunking import chunk_blocks, count_tokens
from app.ingestion.parsers import ParsedBlock


def test_chunk_blocks_respects_target_token_budget():
    long_paragraph = "This is a sentence about company policy. " * 50
    blocks = [ParsedBlock(text=long_paragraph, section="Policy", page_number=1)]

    chunks = chunk_blocks(blocks, target_tokens=60, overlap_tokens=10)

    assert len(chunks) > 1
    for chunk in chunks[:-1]:
        # allow a little slack since sentences aren't split mid-word
        assert chunk.token_count <= 80


def test_chunk_blocks_never_splits_short_paragraphs_unnecessarily():
    blocks = [
        ParsedBlock(text="Short paragraph one.", section="Intro", page_number=1),
        ParsedBlock(text="Short paragraph two.", section="Intro", page_number=1),
    ]

    chunks = chunk_blocks(blocks, target_tokens=300, overlap_tokens=40)

    assert len(chunks) == 1
    assert "Short paragraph one." in chunks[0].content
    assert "Short paragraph two." in chunks[0].content


def test_chunk_blocks_groups_by_section_boundary():
    blocks = [
        ParsedBlock(text="Leave carries over up to 10 days.", section="Carryover", page_number=1),
        ParsedBlock(text="Sick leave is 10 days per year.", section="Sick Leave", page_number=1),
    ]

    chunks = chunk_blocks(blocks, target_tokens=300, overlap_tokens=40)

    assert len(chunks) == 2
    assert chunks[0].section == "Carryover"
    assert chunks[1].section == "Sick Leave"


def test_chunk_preserves_page_number():
    blocks = [ParsedBlock(text="Some page-specific content.", section=None, page_number=7)]
    chunks = chunk_blocks(blocks, target_tokens=300, overlap_tokens=40)
    assert chunks[0].page_number == 7


def test_count_tokens_nonzero_for_text():
    assert count_tokens("hello world") > 0
    assert count_tokens("") == 0


def test_chunk_blocks_empty_input_returns_empty():
    assert chunk_blocks([], target_tokens=300, overlap_tokens=40) == []
