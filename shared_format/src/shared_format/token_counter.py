"""
Canonical token counting using tiktoken cl100k_base.

All three benchmarks use this function so that token counts are
measured identically regardless of which benchmark is running.
"""

import logging

logger = logging.getLogger(__name__)

_encoding = None


def count_tokens(text: str) -> int:
    """Count tokens using tiktoken's cl100k_base encoder.

    Falls back to len(text) // 4 if tiktoken is unavailable.

    Args:
        text: The string to count tokens for.

    Returns:
        Number of tokens.
    """
    global _encoding
    if not text:
        return 0
    try:
        import tiktoken
        if _encoding is None:
            _encoding = tiktoken.get_encoding("cl100k_base")
        return len(_encoding.encode(text))
    except Exception as e:
        logger.debug("tiktoken unavailable, using len//4 fallback: %s", e)
        return max(1, len(text) // 4)
