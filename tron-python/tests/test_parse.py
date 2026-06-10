"""Tests for TRON parse function."""

import pytest

from tron import TRON


class TestParsePrimitives:
    def test_parse_number(self):
        assert TRON.parse("123") == 123

    def test_parse_string(self):
        assert TRON.parse('"hello"') == "hello"

    def test_parse_true(self):
        assert TRON.parse("true") is True

    def test_parse_false(self):
        assert TRON.parse("false") is False

    def test_parse_null(self):
        assert TRON.parse("null") is None


class TestParseArrays:
    def test_parse_array(self):
        assert TRON.parse("[1,2,3]") == [1, 2, 3]


class TestParseObjects:
    def test_parse_empty_object(self):
        assert TRON.parse("{}") == {}

    def test_parse_json_object(self):
        assert TRON.parse('{"a": 1, "b": 2}') == {"a": 1, "b": 2}


class TestParseClasses:
    def test_parse_object_with_class(self):
        tron = """
class Point: x, y
Point(1, 2)
"""
        assert TRON.parse(tron) == {"x": 1, "y": 2}

    def test_parse_class_with_newline_delimited_properties(self):
        tron = """
class Point:
  x
  y
Point(1, 2)
"""
        assert TRON.parse(tron) == {"x": 1, "y": 2}

    def test_parse_nested_objects(self):
        tron = """
class Outer: inner
class Inner: val
{"test1": Outer({"test2": Inner(1)})}
"""
        assert TRON.parse(tron) == {"test1": {"inner": {"test2": {"val": 1}}}}

    def test_parse_semicolons(self):
        tron = """
class Inner: val; class Outer: inner; Outer(Inner(1))
"""
        assert TRON.parse(tron) == {"inner": {"val": 1}}

    def test_ignore_trailing_commas_and_semicolons(self):
        tron = """
class Outer: inner,;
class Inner:
  val1,
  val2,;

Outer(Inner([1,2,], {"key": "value",},),)
"""
        assert TRON.parse(tron) == {"inner": {"val1": [1, 2], "val2": {"key": "value"}}}


class TestParseExtendingClasses:
    def test_parse_extending_classes(self):
        tron = """
class Base:
  index

class Order(Base):
  items,total

class Product(Base):
  name,price,quantity

Order(
  "ord-123",
  [
    Product(1,"Widget",19.99,2),
    Product(2,"Gadget",29.99,1),
    Product(3,"Gizmo",39.99,1)
  ],
  109.96
)
"""
        expected = {
            "index": "ord-123",
            "items": [
                {"index": 1, "name": "Widget", "price": 19.99, "quantity": 2},
                {"index": 2, "name": "Gadget", "price": 29.99, "quantity": 1},
                {"index": 3, "name": "Gizmo", "price": 39.99, "quantity": 1},
            ],
            "total": 109.96,
        }
        assert TRON.parse(tron) == expected


class TestNamingValidation:
    def test_parse_class_names_with_letters_numbers_and_underscores(self):
        tron = """
class My_Class_1: value
My_Class_1(10)
"""
        assert TRON.parse(tron) == {"value": 10}

    def test_fail_if_class_name_starts_with_number(self):
        tron = """
class 1Class: value
1Class(10)
"""
        with pytest.raises(SyntaxError):
            TRON.parse(tron)

    def test_fail_if_class_name_contains_invalid_characters(self):
        tron = """
class My-Class: value
My-Class(10)
"""
        with pytest.raises(SyntaxError):
            TRON.parse(tron)

    def test_parse_class_definitions_with_quoted_property_names(self):
        tron = """
class Test: "key-1", key_2
Test(1, 2)
"""
        result = TRON.parse(tron)
        assert result == {"key-1": 1, "key_2": 2}

    def test_fail_if_unquoted_property_name_starts_with_number(self):
        tron = """
class MyClass: 1value
MyClass(10)
"""
        with pytest.raises(SyntaxError):
            TRON.parse(tron)

    def test_fail_if_unquoted_property_name_contains_invalid_characters(self):
        tron = """
class MyClass: my-value
MyClass(10)
"""
        with pytest.raises(SyntaxError):
            TRON.parse(tron)


class TestNamedArguments:
    def test_parse_class_with_named_arguments(self):
        tron = """
class MyClass: a,b
[
  MyClass(a=1, b=2),
  MyClass(b=4, "a"=3) # quoted property name is allowed
]
"""
        assert TRON.parse(tron) == [{"a": 1, "b": 2}, {"a": 3, "b": 4}]

    def test_parse_class_with_named_arguments_after_positional(self):
        tron = """
class MyClass: a,b
MyClass(1, b=2)
"""
        assert TRON.parse(tron) == {"a": 1, "b": 2}

    def test_fail_if_positional_argument_after_named(self):
        tron = """
class MyClass: a,b
MyClass(a=1, 2)
"""
        with pytest.raises(SyntaxError):
            TRON.parse(tron)

    def test_fail_if_not_all_arguments_assigned(self):
        tron = """
class MyClass: a,b
[MyClass(a=1), MyClass(b=2)]
"""
        with pytest.raises(SyntaxError):
            TRON.parse(tron)

    def test_fail_if_argument_name_not_valid(self):
        tron = """
class MyClass: a,b
MyClass(a=1, b=2, c=3)
"""
        with pytest.raises(SyntaxError):
            TRON.parse(tron)

    def test_fail_if_argument_name_occurs_multiple_times(self):
        tron = """
class MyClass: a,b
MyClass(a=1, b=2, a=3)
"""
        with pytest.raises(SyntaxError):
            TRON.parse(tron)
