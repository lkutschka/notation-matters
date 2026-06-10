"""Type definitions for TRON serialization format."""

from dataclasses import dataclass
from enum import Enum, auto
from typing import TypeAlias


class TokenType(Enum):
    """Token types for TRON lexical analysis."""

    CLASS = auto()
    IDENTIFIER = auto()
    STRING = auto()
    NUMBER = auto()
    TRUE = auto()
    FALSE = auto()
    NULL = auto()
    LPAREN = auto()
    RPAREN = auto()
    LBRACKET = auto()
    RBRACKET = auto()
    LBRACE = auto()
    RBRACE = auto()
    COMMA = auto()
    COLON = auto()
    SEMICOLON = auto()
    EQUALS = auto()
    NEWLINE = auto()
    EOF = auto()


@dataclass
class Token:
    """A lexical token with type, value, and position information."""

    type: TokenType
    value: str
    line: int
    column: int


@dataclass
class ClassDefinition:
    """A TRON class definition with name and property list."""

    name: str
    properties: list[str]


# TronValue represents any valid TRON value
TronValue: TypeAlias = (
    str | int | float | bool | None | list["TronValue"] | dict[str, "TronValue"]
)
