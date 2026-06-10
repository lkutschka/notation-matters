"""TRON (Token Reduced Object Notation) - LLM-efficient serialization format."""

from typing import Any

from .parse import parse
from .stringify import stringify

__version__ = "0.1.0"


class TRON:
    """TRON serialization format for token-efficient data encoding."""

    @staticmethod
    def parse(text: str) -> Any:
        """
        Parse a TRON string into a Python object.

        Args:
            text: The TRON text to parse.

        Returns:
            The parsed Python object.

        Raises:
            SyntaxError: If the input is not valid TRON.
        """
        return parse(text)

    @staticmethod
    def stringify(value: Any) -> str:
        """
        Convert a Python object to TRON format.

        Args:
            value: The Python object to serialize.

        Returns:
            The TRON string representation.

        Raises:
            TypeError: If the value contains circular references or unsupported types.
        """
        return stringify(value)


__all__ = ["TRON", "parse", "stringify", "__version__"]
