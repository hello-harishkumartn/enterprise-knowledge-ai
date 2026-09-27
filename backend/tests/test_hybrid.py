from app.retrieval.fusion import reciprocal_rank_fusion
from app.retrieval.types import RetrievedChunk


def make_chunk(chunk_id: str, **kwargs) -> RetrievedChunk:
    return RetrievedChunk(
        chunk_id=chunk_id,
        document_id=f"doc-{chunk_id}",
        document_name=f"Document {chunk_id}",
        content=f"content {chunk_id}",
        section=None,
        page_number=1,
        document_type="policy",
        department="HR",
        category="hr_policy",
        allowed_roles=["admin", "employee"],
        **kwargs,
    )


def test_chunk_ranked_first_in_both_lists_wins_fusion():
    vector_results = [make_chunk("a", vector_rank=1, vector_score=0.9), make_chunk("b", vector_rank=2, vector_score=0.8)]
    keyword_results = [make_chunk("a", keyword_rank=1, keyword_score=5.0), make_chunk("b", keyword_rank=2, keyword_score=4.0)]

    fused = reciprocal_rank_fusion(vector_results, keyword_results)

    assert fused[0].chunk_id == "a"
    assert fused[0].fused_score > fused[1].fused_score


def test_fusion_merges_scores_for_chunk_present_in_both_lists():
    vector_results = [make_chunk("a", vector_rank=1, vector_score=0.9)]
    keyword_results = [make_chunk("a", keyword_rank=3, keyword_score=2.0)]

    fused = reciprocal_rank_fusion(vector_results, keyword_results)

    assert len(fused) == 1
    assert fused[0].vector_rank == 1
    assert fused[0].keyword_rank == 3
    assert fused[0].fused_score == pytest_approx_sum(1, 3)


def pytest_approx_sum(vector_rank: int, keyword_rank: int, k: int = 60) -> float:
    return 1.0 / (k + vector_rank) + 1.0 / (k + keyword_rank)


def test_fusion_includes_chunk_present_in_only_one_list():
    vector_results = [make_chunk("a", vector_rank=1, vector_score=0.9)]
    keyword_results: list[RetrievedChunk] = []

    fused = reciprocal_rank_fusion(vector_results, keyword_results)

    assert len(fused) == 1
    assert fused[0].chunk_id == "a"
    assert fused[0].keyword_rank is None


def test_fusion_empty_inputs():
    assert reciprocal_rank_fusion([], []) == []
