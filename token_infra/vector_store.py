"""VectorStore abstraction with optional ChromaDB backend."""

from __future__ import annotations

from typing import Any, Dict, List, Optional

from memory.vector_index import VectorIndex

try:  # pragma: no cover - optional dependency
    import chromadb
except Exception:  # pragma: no cover - optional dependency
    chromadb = None


class VectorStore:
    """Semantic vector storage with optional chromadb and built-in fallback."""

    def __init__(self, collection_name: str = "claude-swarm", prefer_chromadb: bool = True) -> None:
        self.collection_name = collection_name
        self.prefer_chromadb = prefer_chromadb
        self._fallback = VectorIndex()
        self._metadata: Dict[str, Dict[str, Any]] = {}
        self.backend = "fallback"
        self._collection = None

        if prefer_chromadb and chromadb is not None:
            client = chromadb.Client()
            self._collection = client.get_or_create_collection(name=collection_name)
            self.backend = "chromadb"

    def add_document(self, key: str, text: str, metadata: Optional[Dict[str, Any]] = None) -> None:
        """Store document in configured backend."""
        info = metadata or {}
        if self.backend == "chromadb" and self._collection is not None:
            self._collection.upsert(ids=[key], documents=[text], metadatas=[info])
            return
        self._fallback.add(key, text)
        self._metadata[key] = info

    def query(self, query_text: str, top_k: int = 3) -> List[Dict[str, Any]]:
        """Return ranked similar documents."""
        if self.backend == "chromadb" and self._collection is not None:
            result = self._collection.query(query_texts=[query_text], n_results=top_k)
            ids = result.get("ids", [[]])[0]
            docs = result.get("documents", [[]])[0]
            scores = result.get("distances", [[]])[0]
            meta = result.get("metadatas", [[]])[0]
            rows: List[Dict[str, Any]] = []
            for idx, doc_id in enumerate(ids):
                rows.append(
                    {
                        "key": doc_id,
                        "text": docs[idx] if idx < len(docs) else "",
                        "score": 1.0 - float(scores[idx]) if idx < len(scores) else 0.0,
                        "metadata": meta[idx] if idx < len(meta) else {},
                    }
                )
            return rows

        entries = self._fallback.search(query_text, top_k=top_k)
        return [
            {
                "key": entry.key,
                "text": entry.text,
                "score": 0.0,
                "metadata": self._metadata.get(entry.key, {}),
            }
            for entry in entries
        ]
