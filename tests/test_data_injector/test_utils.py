# tests/test_data_injector/test_utils.py
import pytest

from pyre.data_injector.utils import parse_bool, parse_list, unflatten


class TestUnflatten:
    def test_single_level_key_unchanged(self):
        assert unflatten({"name": "Alice"}) == {"name": "Alice"}

    def test_dot_notation_becomes_nested(self):
        result = unflatten({"address.city": "London", "address.postcode": "EC1"})
        assert result == {"address": {"city": "London", "postcode": "EC1"}}

    def test_three_levels_deep(self):
        result = unflatten({"a.b.c": 42})
        assert result == {"a": {"b": {"c": 42}}}

    def test_mixed_flat_and_nested(self):
        result = unflatten({"name": "Bob", "address.city": "York"})
        assert result == {"name": "Bob", "address": {"city": "York"}}

    def test_empty_dict(self):
        assert unflatten({}) == {}

    def test_custom_separator(self):
        result = unflatten({"address__city": "Leeds"}, separator="__")
        assert result == {"address": {"city": "Leeds"}}


class TestParseBool:
    def test_true_strings(self):
        for val in ("true", "True", "TRUE", "yes", "YES", "1"):
            assert parse_bool(val) is True

    def test_false_strings(self):
        for val in ("false", "False", "FALSE", "no", "NO", "0"):
            assert parse_bool(val) is False

    def test_bool_passthrough(self):
        assert parse_bool(True) is True
        assert parse_bool(False) is False

    def test_invalid_raises(self):
        with pytest.raises(ValueError, match="Cannot parse"):
            parse_bool("maybe")


class TestParseList:
    def test_csv_string(self):
        assert parse_list()("a, b, c") == ["a", "b", "c"]

    def test_list_passthrough(self):
        assert parse_list()(["x", "y"]) == ["x", "y"]

    def test_custom_separator(self):
        assert parse_list(sep="|")("a|b|c") == ["a", "b", "c"]
