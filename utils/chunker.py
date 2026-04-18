"""Text chunking helpers for token-budgeted context segmentation."""

from __future__ import annotations

from typing import List


def chunk_text(text: str, max_tokens: int, overlap_tokens: int = 0) -> List[str]:
    """Split text into chunks based on approximate token count with overlap."""
    words = text.split()
    if max_tokens <= 0:
        raise ValueError("max_tokens must be positive")
    if overlap_tokens >= max_tokens:
        raise ValueError("overlap_tokens must be smaller than max_tokens")

    chunks: List[str] = []
    start = 0
    while start < len(words):
        end = min(len(words), start + max_tokens)
        chunks.append(" ".join(words[start:end]))
        if end == len(words):
            break
        start = end - overlap_tokens
    return chunks
