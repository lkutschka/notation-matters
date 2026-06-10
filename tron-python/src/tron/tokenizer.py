"""Lexical analyzer for TRON format."""

import re

from .types import Token, TokenType

# Pattern for valid identifiers
IDENTIFIER_START = re.compile(r"[a-zA-Z_]")
IDENTIFIER_CHAR = re.compile(r"[a-zA-Z0-9_]")


def tokenize(input_text: str) -> list[Token]:
    """
    Tokenize a TRON input string into a list of tokens.

    Args:
        input_text: The TRON text to tokenize.

    Returns:
        A list of Token objects.

    Raises:
        SyntaxError: If an unexpected character is encountered.
    """
    tokens: list[Token] = []
    cursor = 0
    line = 1
    column = 1
    length = len(input_text)

    while cursor < length:
        char = input_text[cursor]

        # Handle whitespace (space, tab, carriage return)
        if char in " \t\r":
            cursor += 1
            column += 1
            continue

        # Handle newline
        if char == "\n":
            tokens.append(Token(TokenType.NEWLINE, "\n", line, column))
            cursor += 1
            line += 1
            column = 1
            continue

        # Handle comments
        if char == "#":
            while cursor < length and input_text[cursor] != "\n":
                cursor += 1
            # Don't consume newline here, let the next iteration handle it
            continue

        # Handle symbols
        if char == "(":
            tokens.append(Token(TokenType.LPAREN, "(", line, column))
            cursor += 1
            column += 1
            continue
        if char == ")":
            tokens.append(Token(TokenType.RPAREN, ")", line, column))
            cursor += 1
            column += 1
            continue
        if char == "[":
            tokens.append(Token(TokenType.LBRACKET, "[", line, column))
            cursor += 1
            column += 1
            continue
        if char == "]":
            tokens.append(Token(TokenType.RBRACKET, "]", line, column))
            cursor += 1
            column += 1
            continue
        if char == "{":
            tokens.append(Token(TokenType.LBRACE, "{", line, column))
            cursor += 1
            column += 1
            continue
        if char == "}":
            tokens.append(Token(TokenType.RBRACE, "}", line, column))
            cursor += 1
            column += 1
            continue
        if char == ",":
            tokens.append(Token(TokenType.COMMA, ",", line, column))
            cursor += 1
            column += 1
            continue
        if char == ":":
            tokens.append(Token(TokenType.COLON, ":", line, column))
            cursor += 1
            column += 1
            continue
        if char == ";":
            tokens.append(Token(TokenType.SEMICOLON, ";", line, column))
            cursor += 1
            column += 1
            continue
        if char == "=":
            tokens.append(Token(TokenType.EQUALS, "=", line, column))
            cursor += 1
            column += 1
            continue

        # Handle strings
        if char == '"':
            value = ""
            start_column = column
            cursor += 1  # skip opening quote
            column += 1

            while cursor < length:
                c = input_text[cursor]
                if c == '"':
                    cursor += 1
                    column += 1
                    break
                if c == "\\":
                    cursor += 1
                    column += 1
                    if cursor >= length:
                        raise SyntaxError(
                            f"Unexpected end of input in string at {line}:{column}"
                        )
                    escaped = input_text[cursor]
                    # Handle escape sequences (JSON-compatible)
                    if escaped == '"':
                        value += '"'
                    elif escaped == "\\":
                        value += "\\"
                    elif escaped == "/":
                        value += "/"
                    elif escaped == "b":
                        value += "\b"
                    elif escaped == "f":
                        value += "\f"
                    elif escaped == "n":
                        value += "\n"
                    elif escaped == "r":
                        value += "\r"
                    elif escaped == "t":
                        value += "\t"
                    elif escaped == "u":
                        # Handle unicode escape
                        hex_str = input_text[cursor + 1 : cursor + 5]
                        if re.match(r"^[0-9a-fA-F]{4}$", hex_str):
                            value += chr(int(hex_str, 16))
                            cursor += 4
                            column += 4
                        else:
                            # Invalid escape, just keep it
                            value += "u"
                    else:
                        value += escaped

                    cursor += 1
                    column += 1
                else:
                    value += c
                    cursor += 1
                    column += 1

            tokens.append(Token(TokenType.STRING, value, line, start_column))
            continue

        # Handle numbers
        if char == "-" or ("0" <= char <= "9"):
            # For negative numbers, check that next char is a digit
            if char == "-" and (
                cursor + 1 >= length or not ("0" <= input_text[cursor + 1] <= "9")
            ):
                raise SyntaxError(f"Unexpected character '{char}' at {line}:{column}")

            value = char
            start_column = column
            cursor += 1
            column += 1

            while cursor < length:
                c = input_text[cursor]
                if (
                    ("0" <= c <= "9")
                    or c == "."
                    or c == "e"
                    or c == "E"
                    or c == "+"
                    or c == "-"
                ):
                    value += c
                    cursor += 1
                    column += 1
                else:
                    break

            tokens.append(Token(TokenType.NUMBER, value, line, start_column))
            continue

        # Handle identifiers and keywords
        if IDENTIFIER_START.match(char):
            value = char
            start_column = column
            cursor += 1
            column += 1

            while cursor < length and IDENTIFIER_CHAR.match(input_text[cursor]):
                value += input_text[cursor]
                cursor += 1
                column += 1

            # Check for keywords
            if value == "class":
                tokens.append(Token(TokenType.CLASS, value, line, start_column))
            elif value == "true":
                tokens.append(Token(TokenType.TRUE, value, line, start_column))
            elif value == "false":
                tokens.append(Token(TokenType.FALSE, value, line, start_column))
            elif value == "null":
                tokens.append(Token(TokenType.NULL, value, line, start_column))
            else:
                tokens.append(Token(TokenType.IDENTIFIER, value, line, start_column))
            continue

        raise SyntaxError(f"Unexpected character '{char}' at {line}:{column}")

    tokens.append(Token(TokenType.EOF, "", line, column))
    return tokens
