"""Tests for TRON stringify function."""

import pytest

from tron import TRON


class TestStringifyPrimitives:
    def test_stringify_number(self):
        assert TRON.stringify(123) == "123"

    def test_stringify_string(self):
        assert TRON.stringify("hello") == '"hello"'

    def test_stringify_true(self):
        assert TRON.stringify(True) == "true"

    def test_stringify_false(self):
        assert TRON.stringify(False) == "false"

    def test_stringify_null(self):
        assert TRON.stringify(None) == "null"


class TestStringifyArrays:
    def test_stringify_number_array(self):
        assert TRON.stringify([1, 2, 3]) == "[1,2,3]"

    def test_stringify_string_array(self):
        assert TRON.stringify(["a", "b"]) == '["a","b"]'


class TestStringifyObjects:
    def test_stringify_empty_object(self):
        assert TRON.stringify({}) == "{}"

    def test_reuse_classes_for_same_structure(self):
        obj = [{"x": 1, "y": 2, "z": 3}, {"x": 3, "y": 4, "z": 5}]
        tron = TRON.stringify(obj)
        assert "class A: x,y,z" in tron
        assert "[A(1,2,3),A(3,4,5)]" in tron

    def test_handle_nested_objects(self):
        obj = {
            "a": {"x": 1, "y": 2, "z": 3},
            "b": {"y": 4, "x": 3, "z": 5},
            "c": {"x": 2, "y": 4, "z": 6},
        }
        tron = TRON.stringify(obj)
        assert "class A: x,y,z" in tron
        assert '{"a":A(1,2,3),"b":A(3,4,5),"c":A(2,4,6)}' in tron


class TestStringifyUndefined:
    def test_stringify_none_at_top_level(self):
        # This is intentionally different from JSON which returns undefined
        assert TRON.stringify(None) == "null"

    def test_stringify_none_in_array(self):
        assert TRON.stringify([None]) == "[null]"

    def test_stringify_none_in_object(self):
        # None values are filtered out (like undefined in JS)
        assert TRON.stringify({"a": None}) == "{}"

    def test_stringify_object_with_none_value(self):
        tron = TRON.stringify({"a": None, "b": 1, "c": 2, "d": 3})
        assert tron == '{"b":1,"c":2,"d":3}'


class TestStringifyErrors:
    def test_throw_on_circular_reference(self):
        obj: dict = {"a": {}}
        obj["a"]["parent"] = obj  # type: ignore
        with pytest.raises(TypeError):
            TRON.stringify(obj)


class TestStringifySpecialCharacters:
    def test_quote_property_names_with_special_characters(self):
        obj = [
            {"1a": 1, "a1": 2, "valid_name": 3, "foo-bar": 4},
            {"1a": 1, "a1": 2, "valid_name": 3, "foo-bar": 4},
        ]
        tron = TRON.stringify(obj)
        # Check that the class definition quotes "foo-bar" and "1a"
        assert 'class A: "1a",a1,valid_name,"foo-bar"' in tron


class TestConditionalClassDefinition:
    def test_use_json_syntax_for_single_occurring_object(self):
        obj = {"x": 1, "y": 2, "z": 3}
        tron = TRON.stringify(obj)
        assert tron == '{"x":1,"y":2,"z":3}'

    def test_use_json_syntax_for_single_property_objects(self):
        obj = [{"x": 1}, {"x": 2}, {"x": 3}]
        tron = TRON.stringify(obj)
        assert tron == '[{"x":1},{"x":2},{"x":3}]'

    def test_define_class_for_2_property_objects_appearing_twice(self):
        obj = [{"x": 1, "y": 2}, {"x": 3, "y": 4}]
        tron = TRON.stringify(obj)
        assert "class A: x,y" in tron
        assert "[A(1,2),A(3,4)]" in tron

    def test_handle_mixed_scenarios_with_different_property_counts(self):
        obj = {
            "single": {"a": 1},
            "oneTwice": [{"b": 2}, {"b": 3}],
            "twoTwice": [{"d": 4, "e": 5}, {"d": 6, "e": 7}],
            "threeOnce": {"f": 8, "g": 9, "h": 10},
        }
        tron = TRON.stringify(obj)
        # twoTwice: class (2 properties, occurs twice)
        assert "class A: d,e" in tron
        assert (
            '{"single":{"a":1},"oneTwice":[{"b":2},{"b":3}],'
            '"twoTwice":[A(4,5),A(6,7)],"threeOnce":{"f":8,"g":9,"h":10}}'
        ) in tron
