"""Tests for VectorStore fallback backend."""

from token_infra.vector_store import VectorStore


def _make_store() -> VectorStore:
    return VectorStore(prefer_chromadb=False)


def test_add_and_query_returns_matching_documents():
    store = _make_store()
    store.add_document("doc1", "hello world")
    store.add_document("doc2", "goodbye world")
    results = store.query("hello")
    assert any(r["key"] == "doc1" for r in results)


def test_query_top_k_limits_results():
    store = _make_store()
    store.add_document("a", "alpha")
    store.add_document("b", "beta")
    store.add_document("c", "gamma")
    results = store.query("alpha beta gamma", top_k=1)
    assert len(results) == 1


def test_query_empty_store_returns_empty_list():
    store = _make_store()
    results = store.query("anything")
    assert results == []


def test_metadata_is_preserved():
    store = _make_store()
    store.add_document("doc1", "some text", metadata={"source": "test", "page": 1})
    results = store.query("some text")
    match = next(r for r in results if r["key"] == "doc1")
    assert match["metadata"] == {"source": "test", "page": 1}


def test_no_metadata_defaults_to_empty_dict():
    store = _make_store()
    store.add_document("doc1", "some text")
    results = store.query("some text")
    match = next(r for r in results if r["key"] == "doc1")
    assert match["metadata"] == {}


def test_multiple_documents_best_match_first():
    store = _make_store()
    store.add_document("d1", "alpha beta gamma")
    store.add_document("d2", "delta epsilon")
    store.add_document("d3", "alpha alpha alpha")
    results = store.query("alpha")
    assert results[0]["key"] == "d3"


def test_backend_is_fallback():
    store = _make_store()
    assert store.backend == "fallback"
