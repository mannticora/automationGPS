"""Tests unitarios para scripts/utils.py (funciones puras)."""
import pytest
from utils import parse_case_ids


class TestParseCaseIds:
    def test_single_range(self):
        assert parse_case_ids("1778-1782") == ["1778", "1779", "1780", "1781", "1782"]

    def test_comma_separated(self):
        assert parse_case_ids("1778,1780,1782") == ["1778", "1780", "1782"]

    def test_mixed_range_and_list(self):
        assert parse_case_ids("1778-1780,1790") == ["1778", "1779", "1780", "1790"]

    def test_single_id(self):
        assert parse_case_ids("1777") == ["1777"]

    def test_strips_whitespace(self):
        assert parse_case_ids(" 1778 - 1780 , 1790 ") == ["1778", "1779", "1780", "1790"]

    def test_invalid_range_end_before_start_raises(self):
        with pytest.raises(ValueError):
            parse_case_ids("1782-1778")

    def test_non_numeric_raises(self):
        with pytest.raises(ValueError):
            parse_case_ids("abc")

    def test_empty_string_returns_empty_list(self):
        assert parse_case_ids("") == []
