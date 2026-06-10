"""Tests for class name generation."""

from tron.stringify import exported_for_unit_testing

generate_class_name = exported_for_unit_testing["generate_class_name"]


class TestSingleLetterRange:
    def test_generate_all_single_letters(self):
        letters = "ABCDEFGHIJKLMNOPQRSTUVWXYZ"
        for i in range(26):
            assert generate_class_name(i) == letters[i]


class TestFirstCycleWithSuffix:
    def test_generate_all_letters_with_1_suffix(self):
        letters = "ABCDEFGHIJKLMNOPQRSTUVWXYZ"
        for i in range(26):
            assert generate_class_name(26 + i) == letters[i] + "1"


class TestSecondCycleWithSuffix:
    def test_generate_a2_z2_for_indices_52_77(self):
        assert generate_class_name(52) == "A2"
        assert generate_class_name(53) == "B2"
        assert generate_class_name(77) == "Z2"

    def test_generate_all_letters_with_2_suffix(self):
        letters = "ABCDEFGHIJKLMNOPQRSTUVWXYZ"
        for i in range(26):
            assert generate_class_name(52 + i) == letters[i] + "2"
