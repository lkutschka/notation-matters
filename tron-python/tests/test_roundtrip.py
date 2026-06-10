"""Tests for TRON round-trip (stringify then parse)."""

from tron import TRON


class TestRoundTrip:
    def test_preserve_data(self):
        data = {
            "users": [
                {"id": 1, "name": "Alice", "active": True},
                {"id": 2, "name": "Bob", "active": False},
            ],
            "meta": {"page": 1, "total": 2},
        }
        tron = TRON.stringify(data)
        parsed = TRON.parse(tron)
        assert parsed == data
