"""Parser for TRON format."""

from typing import Any

from .tokenizer import tokenize
from .types import ClassDefinition, Token, TokenType


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
    tokens = tokenize(text)
    parser = Parser(tokens)
    return parser.parse()


class Parser:
    """Recursive descent parser for TRON format."""

    def __init__(self, tokens: list[Token]) -> None:
        self._tokens = tokens
        self._current = 0
        self._classes: dict[str, ClassDefinition] = {}

    def parse(self) -> Any:
        """Parse the token stream and return the resulting object."""
        # 0. Skip leading newlines/semicolons
        while self._match(TokenType.SEMICOLON) or self._match(TokenType.NEWLINE):
            pass

        # 1. Parse Header (Class Definitions)
        while self._match(TokenType.CLASS):
            self._parse_class_definition()
            # Optional separators between classes
            while self._match(TokenType.SEMICOLON) or self._match(TokenType.NEWLINE):
                pass

        # Skip any remaining newlines/semicolons before data
        while self._match(TokenType.SEMICOLON) or self._match(TokenType.NEWLINE):
            pass

        # 2. Parse Data
        if self._is_at_end():
            raise SyntaxError("Unexpected end of input: No data section found")

        data = self._parse_value()

        # Ensure no extra data
        while self._match(TokenType.NEWLINE) or self._match(TokenType.SEMICOLON):
            pass

        if not self._is_at_end():
            token = self._peek()
            raise SyntaxError(
                f"Unexpected token after data: {token.value} at {token.line}:{token.column}"
            )

        return data

    def _parse_class_definition(self) -> None:
        """Parse a class definition from the header."""
        # Expect Identifier (ClassName)
        name_token = self._consume(TokenType.IDENTIFIER, "Expect class name.")
        class_name = name_token.value

        # Check for class inheritance: class ChildClass(ParentClass): ...
        parent_properties: list[str] = []
        if self._match(TokenType.LPAREN):
            parent_name_token = self._consume(
                TokenType.IDENTIFIER, "Expect parent class name."
            )
            parent_class_name = parent_name_token.value

            parent_class_def = self._classes.get(parent_class_name)
            if parent_class_def is None:
                raise SyntaxError(
                    f"Undefined parent class: {parent_class_name} at "
                    f"{parent_name_token.line}:{parent_name_token.column}"
                )

            parent_properties = list(parent_class_def.properties)
            self._consume(TokenType.RPAREN, "Expect ')' after parent class name.")

        # Expect Colon
        self._consume(TokenType.COLON, "Expect ':' after class name.")

        properties: list[str] = []

        # Parse Properties
        while (
            not self._check(TokenType.SEMICOLON)
            and not self._check(TokenType.CLASS)
            and not self._is_at_end()
        ):
            if self._match(TokenType.NEWLINE):
                # If next token is CLASS, we are done
                if self._check(TokenType.CLASS):
                    break
                # If next token is EOF, done
                if self._is_at_end():
                    break
                # If next token is Identifier followed by '(', it's Data
                if self._check(TokenType.IDENTIFIER) and self._check_next(
                    TokenType.LPAREN
                ):
                    break
                # If next token is NOT Identifier/String, it's likely Data
                if not self._check(TokenType.IDENTIFIER) and not self._check(
                    TokenType.STRING
                ):
                    break
                # Otherwise, it's a property on a new line
                continue

            if self._match(TokenType.COMMA):
                continue

            if self._check(TokenType.IDENTIFIER) or self._check(TokenType.STRING):
                prop_token = self._advance()
                properties.append(prop_token.value)
            else:
                break  # End of properties

        # Combine parent properties (if any) with own properties
        all_properties = parent_properties + properties
        self._classes[class_name] = ClassDefinition(
            name=class_name, properties=all_properties
        )

    def _parse_value(self) -> Any:
        """Parse a value (primitive, array, object, or class instantiation)."""
        if self._match(TokenType.NULL):
            return None
        if self._match(TokenType.TRUE):
            return True
        if self._match(TokenType.FALSE):
            return False

        if self._check(TokenType.NUMBER):
            value_str = self._advance().value
            # Parse as float first, then check if it's an integer
            num = float(value_str)
            if num.is_integer() and "." not in value_str and "e" not in value_str.lower():
                return int(num)
            return num

        if self._check(TokenType.STRING):
            return self._advance().value

        if self._match(TokenType.LBRACKET):
            return self._parse_array()

        if self._match(TokenType.LBRACE):
            return self._parse_object()

        if self._check(TokenType.IDENTIFIER):
            # Class Instantiation
            return self._parse_class_instantiation()

        token = self._peek()
        raise SyntaxError(
            f"Unexpected token in value: {token.value} at {token.line}:{token.column}"
        )

    def _parse_array(self) -> list[Any]:
        """Parse an array value."""
        arr: list[Any] = []
        if not self._check(TokenType.RBRACKET):
            while True:
                while self._match(TokenType.NEWLINE):
                    pass

                if self._check(TokenType.RBRACKET):
                    break

                arr.append(self._parse_value())

                while self._match(TokenType.NEWLINE):
                    pass

                if not self._match(TokenType.COMMA):
                    break

        self._consume(TokenType.RBRACKET, "Expect ']' after array.")
        return arr

    def _parse_object(self) -> dict[str, Any]:
        """Parse a JSON-style object value."""
        obj: dict[str, Any] = {}
        if not self._check(TokenType.RBRACE):
            while True:
                while self._match(TokenType.NEWLINE):
                    pass

                if self._check(TokenType.RBRACE):
                    break

                key_token = self._consume(TokenType.STRING, "Expect string key in object.")
                key = key_token.value

                self._consume(TokenType.COLON, "Expect ':' after key.")

                value = self._parse_value()
                obj[key] = value

                while self._match(TokenType.NEWLINE):
                    pass

                if not self._match(TokenType.COMMA):
                    break

        self._consume(TokenType.RBRACE, "Expect '}' after object.")
        return obj

    def _parse_class_instantiation(self) -> dict[str, Any]:
        """Parse a class instantiation."""
        class_name_token = self._consume(TokenType.IDENTIFIER, "Expect class name.")
        class_name = class_name_token.value

        class_def = self._classes.get(class_name)
        if class_def is None:
            raise SyntaxError(
                f"Undefined class: {class_name} at "
                f"{class_name_token.line}:{class_name_token.column}"
            )

        self._consume(TokenType.LPAREN, "Expect '(' after class name.")

        obj: dict[str, Any] = {}
        assigned_props: set[str] = set()
        positional_index = 0
        seen_named_arg = False

        if not self._check(TokenType.RPAREN):
            while True:
                while self._match(TokenType.NEWLINE):
                    pass

                if self._check(TokenType.RPAREN):
                    break

                # Check if this is a named argument
                is_named_arg = (
                    self._check(TokenType.IDENTIFIER) or self._check(TokenType.STRING)
                ) and self._check_next(TokenType.EQUALS)

                if is_named_arg:
                    seen_named_arg = True
                    prop_name_token = self._advance()
                    prop_name = prop_name_token.value

                    # Verify property exists in class
                    if prop_name not in class_def.properties:
                        raise SyntaxError(
                            f"Unknown property '{prop_name}' for class {class_name} at "
                            f"{prop_name_token.line}:{prop_name_token.column}"
                        )

                    # Verify property hasn't been assigned yet
                    if prop_name in assigned_props:
                        raise SyntaxError(
                            f"Property '{prop_name}' already assigned for class {class_name} at "
                            f"{prop_name_token.line}:{prop_name_token.column}"
                        )

                    self._consume(TokenType.EQUALS, "Expect '=' after property name.")
                    value = self._parse_value()
                    obj[prop_name] = value
                    assigned_props.add(prop_name)
                else:
                    # Positional argument
                    if seen_named_arg:
                        token = self._peek()
                        raise SyntaxError(
                            f"Positional argument cannot appear after named argument at "
                            f"{token.line}:{token.column}"
                        )

                    if positional_index >= len(class_def.properties):
                        token = self._peek()
                        raise SyntaxError(
                            f"Too many arguments for class {class_name} at "
                            f"{token.line}:{token.column}"
                        )

                    value = self._parse_value()
                    prop_name = class_def.properties[positional_index]
                    obj[prop_name] = value
                    assigned_props.add(prop_name)
                    positional_index += 1

                while self._match(TokenType.NEWLINE):
                    pass

                if not self._match(TokenType.COMMA):
                    break

        # Verify all properties are assigned
        if len(assigned_props) < len(class_def.properties):
            missing_props = [p for p in class_def.properties if p not in assigned_props]
            raise SyntaxError(
                f"Missing arguments for class {class_name}: {', '.join(missing_props)}"
            )

        self._consume(TokenType.RPAREN, "Expect ')' after arguments.")
        return obj

    # Helper methods
    def _match(self, token_type: TokenType) -> bool:
        """Check if current token matches type and advance if so."""
        if self._check(token_type):
            self._advance()
            return True
        return False

    def _check(self, token_type: TokenType) -> bool:
        """Check if current token matches type without consuming."""
        if self._is_at_end():
            return False
        return self._peek().type == token_type

    def _check_next(self, token_type: TokenType) -> bool:
        """Check if next token matches type without consuming."""
        if self._current + 1 >= len(self._tokens):
            return False
        return self._tokens[self._current + 1].type == token_type

    def _advance(self) -> Token:
        """Consume current token and return it."""
        if not self._is_at_end():
            self._current += 1
        return self._previous()

    def _is_at_end(self) -> bool:
        """Check if we've reached the end of tokens."""
        return self._peek().type == TokenType.EOF

    def _peek(self) -> Token:
        """Return current token without consuming."""
        return self._tokens[self._current]

    def _previous(self) -> Token:
        """Return previously consumed token."""
        return self._tokens[self._current - 1]

    def _consume(self, token_type: TokenType, message: str) -> Token:
        """Consume token of expected type or raise error."""
        if self._check(token_type):
            return self._advance()
        token = self._peek()
        raise SyntaxError(f"{message} Found {token.value} at {token.line}:{token.column}")
