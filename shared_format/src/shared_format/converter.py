"""
Core serialization/deserialization for JSON, TOON, and TRON formats.

All three benchmarks (MCPToolBenchPP, MCP-Universe, StableToolBench) delegate
to these functions so that identical input data produces identical output.
"""

import json
import logging
import re
from enum import Enum
from typing import Any

logger = logging.getLogger(__name__)


class ToolFormat(str, Enum):
    """Supported serialization formats."""
    JSON = "json"
    TOON = "toon"
    TRON = "tron"


def serialize(data: Any, fmt: ToolFormat) -> str:
    """Convert a Python dict/list/value to the target format string.

    Args:
        data: The Python object to serialize.
        fmt: Target format (JSON, TOON, or TRON).

    Returns:
        Serialized string in the target format.
    """
    if fmt == ToolFormat.JSON:
        return json.dumps(data)
    elif fmt == ToolFormat.TOON:
        from toon_format import encode
        return encode(data)
    elif fmt == ToolFormat.TRON:
        from tron import TRON
        return TRON.stringify(data)
    return json.dumps(data)


def deserialize(text: str, fmt: ToolFormat) -> Any:
    """Parse a format string back to a Python object.

    Args:
        text: The string to parse.
        fmt: Format of the input string.

    Returns:
        Parsed Python object (dict, list, etc.).
    """
    if fmt == ToolFormat.JSON:
        return json.loads(text)
    elif fmt == ToolFormat.TOON:
        from toon_format import decode
        return decode(text)
    elif fmt == ToolFormat.TRON:
        from tron import TRON
        return TRON.parse(text)
    return json.loads(text)


def deserialize_lenient(text: str, fmt: ToolFormat) -> Any:
    """Try target format first, fall back to JSON, fall back to {}.

    Args:
        text: The string to parse.
        fmt: Expected format of the input string.

    Returns:
        Parsed Python object, or empty dict on failure.
    """
    try:
        return deserialize(text, fmt)
    except Exception:
        try:
            return json.loads(text)
        except Exception as e:
            logger.error("Failed to parse as %s or JSON: %s", fmt.value, e)
            return {}


class FormatViolation(ValueError):
    """Raised when text cannot be parsed as the requested format.

    Distinct from generic ValueError so call sites can count violations
    separately from other parse errors.
    """

    def __init__(self, fmt: ToolFormat, original_exc: Exception, snippet: str):
        self.fmt = fmt
        self.original_exc = original_exc
        self.snippet = snippet
        super().__init__(
            f"format violation: expected {fmt.value}: "
            f"{type(original_exc).__name__}: {original_exc} | "
            f"snippet={snippet[:200]!r}"
        )


def _looks_like_json_or_tron(text: str) -> bool:
    """Lightweight shape check: JSON/TRON tool-call payloads start with '{' or '['."""
    stripped = text.lstrip()
    return stripped.startswith(("{", "["))


def deserialize_strict(text: str, fmt: ToolFormat) -> Any:
    """Parse text as the given format. No JSON fallback, no empty-dict fallback.

    Use this when a parse failure should be surfaced as a real failure (e.g.
    tool-call output that the model emitted in the wrong format). Pair with
    a try/except FormatViolation block to count the violation.

    Includes a lightweight shape check: TOON's parser is permissive and will
    accept JSON-shaped text by interpreting '{...}' as a degenerate string key.
    If the caller asks for TOON and the text starts with '{' or '[' (a JSON
    or TRON tool-call payload), treat that as a format violation.

    Args:
        text: The string to parse.
        fmt: Expected format of the input string.

    Returns:
        Parsed Python object.

    Raises:
        FormatViolation: if text is not valid in the given format.
    """
    if fmt == ToolFormat.TOON and _looks_like_json_or_tron(text):
        raise FormatViolation(
            fmt,
            ValueError("text starts with '{' or '['; looks like JSON/TRON, not TOON"),
            text,
        )
    # Equalize JSON's and TRON's leniency. The two formats had asymmetric
    # strictness in their default parsers — TRON's tokenizer accepts trailing
    # commas while json.loads does not. LLMs (especially Python-trained ones)
    # emit trailing commas frequently, which inflated JSON's format-violation
    # rate vs TRON for the same model output. We treat trailing commas as
    # legal in both formats by normalizing them away before strict-parse.
    # TOON has no braces so the regex is a no-op there.
    text = _normalize_for_strict_parse(text, fmt)
    try:
        return deserialize(text, fmt)
    except Exception as e:
        raise FormatViolation(fmt, e, text) from e


_TRAILING_COMMA_RE = re.compile(r",(\s*[}\]])")


def _normalize_for_strict_parse(text: str, fmt: "ToolFormat") -> str:
    """Apply the same set of forgiving normalizations to JSON and TRON before
    strict-parse so the two formats are compared on equal footing.

    Currently: strip trailing commas (immediately before } or ]). This is the
    one syntactic divergence we observed between json.loads and tron-python:
    TRON's tokenizer accepts `{"a":1,}` while JSON rejects it. LLMs commonly
    emit trailing commas, so penalizing only JSON for them would unfairly
    inflate JSON's format-violation rate.
    """
    if fmt is ToolFormat.TOON:
        return text
    prev = None
    while prev != text:
        prev = text
        text = _TRAILING_COMMA_RE.sub(r"\1", text)
    return text


_EMPTY_INLINE_LITERALS = {"{}", "{ }", "[]", "[ ]", ""}

# Match a TRON class definition header. TRON syntax is `class Name: f1,f2;` —
# permissive on whitespace, parents, and trailing punctuation. Only used to
# detect whether *any* class was declared, not to validate syntax.
_TRON_CLASS_DEF_RE = re.compile(
    r"\bclass\s+[A-Za-z_]\w*\s*(?:\([^)]*\))?\s*:", re.IGNORECASE
)


def tron_uses_class_when_possible(raw_text: str, parsed_value) -> bool:
    """Did the TRON output use class definitions where they would compress?

    Returns True when:
      - the parsed value has no group of 2+ structurally-identical objects
        (compression would not help), OR
      - the raw text declares at least one class definition.

    Returns False only when there is a clear missed opportunity: 2+
    same-shape dicts in the output and zero class definitions in the
    raw text. That case represents the model emitting plain JSON when
    TRON's compression feature applies, which the experiment counts
    as not-actually-using-TRON.
    """
    if _TRON_CLASS_DEF_RE.search(raw_text):
        return True

    shape_counts = {}

    def visit(node):
        if isinstance(node, dict):
            shape = tuple(sorted(node.keys()))
            shape_counts[shape] = shape_counts.get(shape, 0) + 1
            for v in node.values():
                visit(v)
        elif isinstance(node, list):
            for v in node:
                visit(v)

    visit(parsed_value)
    repeated_shape = any(c >= 2 and len(s) > 0 for s, c in shape_counts.items())
    return not repeated_shape


def coerce_empty_inline_literal(value):
    """If value is a string that looks like an empty inline literal, return {}.

    Why this exists: TOON's spec uses indentation, not braces, so `arguments:`
    (bare key, no value) is the canonical empty-object. LLMs trained on JSON
    instead emit `arguments: {}`, which a strict TOON parser stores as the
    string `'{}'`. This helper coerces those obvious-empty literals back to
    `{}` at the agent boundary, so a single TOON spec gotcha around empty
    objects doesn't dominate the format-failure rate. Anything else stays
    a string and the caller can decide whether to treat that as a violation.
    """
    if isinstance(value, str) and value.strip() in _EMPTY_INLINE_LITERALS:
        return {}
    return value
