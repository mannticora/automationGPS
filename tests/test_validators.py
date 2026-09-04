"""Tests unitarios para scripts/validators.py (funciones puras, sin navegador ni red)."""
import json
from pathlib import Path

import pytest
from validators import (
    build_case_status,
    coordinates_match,
    haversine_distance_m,
    is_within_valid_range,
    parse_coordinates,
)


class TestParseCoordinates:
    def test_valid_comma_separated(self):
        assert parse_coordinates("-0.2345,-78.5123") == (-0.2345, -78.5123)

    def test_valid_with_space_after_comma(self):
        assert parse_coordinates("-0.2345, -78.5123") == (-0.2345, -78.5123)

    def test_valid_positive_values(self):
        assert parse_coordinates("19.4326,-99.1332") == (19.4326, -99.1332)

    def test_empty_string_raises(self):
        with pytest.raises(ValueError):
            parse_coordinates("")

    def test_none_raises(self):
        with pytest.raises(ValueError):
            parse_coordinates(None)

    def test_garbage_format_raises(self):
        with pytest.raises(ValueError):
            parse_coordinates("no-es-una-coordenada")

    def test_out_of_range_latitude_raises(self):
        with pytest.raises(ValueError):
            parse_coordinates("200.0,50.0")

    def test_out_of_range_longitude_raises(self):
        with pytest.raises(ValueError):
            parse_coordinates("50.0,-200.0")


class TestIsWithinValidRange:
    def test_valid_coordinates(self):
        assert is_within_valid_range(-0.2345, -78.5123) is True

    def test_invalid_latitude(self):
        assert is_within_valid_range(120.0, -78.5123) is False

    def test_invalid_longitude(self):
        assert is_within_valid_range(-0.2345, -200.0) is False

    def test_boundary_values_are_valid(self):
        assert is_within_valid_range(90.0, 180.0) is True
        assert is_within_valid_range(-90.0, -180.0) is True


class TestHaversineDistance:
    def test_same_point_is_zero(self):
        assert haversine_distance_m(-0.2345, -78.5123, -0.2345, -78.5123) == pytest.approx(0.0, abs=1e-6)

    def test_one_degree_latitude_is_about_111km(self):
        distance = haversine_distance_m(0.0, 0.0, 1.0, 0.0)
        assert distance == pytest.approx(111195, rel=0.01)


class TestCoordinatesMatch:
    def test_within_tolerance(self):
        assert coordinates_match(-0.2345, -78.5123, -0.23451, -78.51231, tolerance_m=50) is True

    def test_outside_tolerance(self):
        assert coordinates_match(-0.2345, -78.5123, -0.5, -79.0, tolerance_m=50) is False


class TestBuildCaseStatus:
    def test_not_found(self):
        assert build_case_status(found=False, distance_m=None) == "❌ No encontrado"

    def test_validated_within_tolerance(self):
        assert build_case_status(found=True, distance_m=10.0, tolerance_m=50.0) == "Validado ✓"

    def test_requires_correction_beyond_tolerance(self):
        assert build_case_status(found=True, distance_m=500.0, tolerance_m=50.0) == "⚠️ Requiere corrección"

    def test_found_without_distance_counts_as_validated(self):
        assert build_case_status(found=True, distance_m=None) == "Validado ✓"


def test_sample_case_1777_fixture_loads():
    """La fixture de Case ID 1777 (AUTOSERVICIO CALVA) debe ser JSON válido y consistente."""
    fixture_path = Path(__file__).parent / "test_data" / "sample_case_1777.json"
    data = json.loads(fixture_path.read_text(encoding="utf-8"))
    assert data["case_id"] == "1777"
    assert data["business_name"] == "AUTOSERVICIO CALVA"
    lat, lon = parse_coordinates(data["geo_location_raw"])
    assert is_within_valid_range(lat, lon)
