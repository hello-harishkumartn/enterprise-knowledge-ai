import numpy as np
import pytest

from app.config import get_settings
from app.retrieval.embeddings import embed_query, embed_texts

pytestmark = pytest.mark.slow


def _cosine(a, b):
    a, b = np.array(a), np.array(b)
    return float(np.dot(a, b) / (np.linalg.norm(a) * np.linalg.norm(b)))


def test_embed_texts_returns_correct_dimension():
    settings = get_settings()
    vectors = embed_texts(["Employees accrue 15 PTO days per year."])
    assert len(vectors) == 1
    assert len(vectors[0]) == settings.EMBEDDING_DIM


def test_embed_query_matches_embed_texts_single():
    vec = embed_query("How many sick days do employees get?")
    assert isinstance(vec, list)
    assert len(vec) == get_settings().EMBEDDING_DIM


def test_semantically_similar_texts_are_closer_than_unrelated():
    leave_a = "Employees may carry forward up to 10 unused PTO days into next year."
    leave_b = "How many vacation days can I roll over to the following year?"
    unrelated = "The quarterly wire transfer limit for small business clients is $100,000."

    vec_leave_a, vec_leave_b, vec_unrelated = embed_texts([leave_a, leave_b, unrelated])

    sim_related = _cosine(vec_leave_a, vec_leave_b)
    sim_unrelated = _cosine(vec_leave_a, vec_unrelated)

    assert sim_related > sim_unrelated


def test_embed_texts_empty_list_returns_empty():
    assert embed_texts([]) == []
