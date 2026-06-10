"""
Local token counting utility.
Delegates to shared_format's canonical tiktoken cl100k_base counter.
"""
from shared_format import count_tokens as _shared_count_tokens


def count_tokens(text: str) -> int:
    """Count tokens using shared_format's canonical tiktoken cl100k_base counter."""
    return _shared_count_tokens(text)
