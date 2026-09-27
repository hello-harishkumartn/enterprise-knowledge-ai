import pytest

from app.retrieval.reranker import rerank

pytestmark = pytest.mark.slow


def test_reranker_scores_relevant_passage_higher():
    query = "How many paid sick days do employees get per year?"
    candidates = [
        "Employees receive 10 paid sick days per calendar year, credited in full on January 1.",
        "The corporate travel platform should be used to book flights whenever available.",
    ]

    scores = rerank(query, candidates)

    assert len(scores) == 2
    assert scores[0] > scores[1]


def test_reranker_handles_empty_candidates():
    assert rerank("any query", []) == []
