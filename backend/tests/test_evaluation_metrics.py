from app.evaluation.metrics import (
    answer_relevance_heuristic,
    citation_correctness,
    extract_cited_numbers,
    groundedness_heuristic,
    mean_reciprocal_rank,
    precision_at_k,
    recall_at_k,
)


def test_recall_at_k_full_hit():
    assert recall_at_k(["a", "b", "c"], ["a"], k=3) == 1.0


def test_recall_at_k_partial_hit():
    assert recall_at_k(["a", "b"], ["a", "c"], k=2) == 0.5


def test_recall_at_k_no_expected_is_trivially_satisfied():
    assert recall_at_k(["a"], [], k=3) == 1.0


def test_precision_at_k():
    assert precision_at_k(["a", "b", "c"], ["a"], k=3) == 1 / 3


def test_precision_at_k_empty_retrieved():
    assert precision_at_k([], ["a"], k=3) == 0.0


def test_mrr_first_position():
    assert mean_reciprocal_rank(["a", "b"], ["a"]) == 1.0


def test_mrr_second_position():
    assert mean_reciprocal_rank(["b", "a"], ["a"]) == 0.5


def test_mrr_no_match():
    assert mean_reciprocal_rank(["b", "c"], ["a"]) == 0.0


def test_citation_correctness_all_correct():
    assert citation_correctness(["doc1", "doc1"], ["doc1"]) == 1.0


def test_citation_correctness_partial():
    assert citation_correctness(["doc1", "doc2"], ["doc1"]) == 0.5


def test_citation_correctness_no_citations_scores_zero():
    assert citation_correctness([], ["doc1"]) == 0.0


def test_groundedness_heuristic_high_for_supported_claim():
    context = "Employees may carry forward up to 10 unused PTO days into the following year."
    answer = "Employees may carry forward up to 10 unused PTO days."
    assert groundedness_heuristic(answer, context) > 0.8


def test_groundedness_heuristic_low_for_unsupported_claim():
    context = "Employees may carry forward up to 10 unused PTO days."
    answer = "The company headquarters relocated to Mars in 2030."
    assert groundedness_heuristic(answer, context) < 0.3


def test_answer_relevance_heuristic_high_when_answer_addresses_question():
    question = "How many PTO days carry over?"
    answer = "You can carry over up to 10 PTO days."
    assert answer_relevance_heuristic(answer, question) > 0.5


def test_extract_cited_numbers():
    assert extract_cited_numbers("Point one [1]. Point two [2]. Repeat [1].") == [1, 2]


def test_extract_cited_numbers_none():
    assert extract_cited_numbers("No citations.") == []
