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
    validate_case,
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


class _FakeClient:
    """Doble de prueba para browser_automation.CensoBateriasClient."""

    def __init__(self, business_name: str, geo_location_raw: str):
        self._data = {"business_name": business_name, "geo_location_raw": geo_location_raw}

    def extract_case_data(self, case_id, url=None):
        return self._data


class _BrokenClient:
    """Simula un fallo de extracción (selector roto, timeout, etc.)."""

    def extract_case_data(self, case_id, url=None):
        raise RuntimeError("boom")


class _FakeMapsHandler:
    """Doble de prueba para google_maps_handler.GoogleMapsHandler."""

    def __init__(self, result: dict):
        self._result = result

    def validate_in_google_maps(self, business_name, lat, lon, search_radius_m=None):
        return self._result


class TestValidateCase:
    def test_validated_case_still_reports_verified_gps(self):
        """Caso real Case ID 1777 (AUTOSERVICIO CALVA): ~12.8m de distancia, dentro de tolerancia.

        Aunque el caso quede "Validado ✓", la coordenada verificada en Google Maps se
        reporta igual: el equipo la copia manualmente al campo "GPS correcto" de la
        plataforma como parte de su control de calidad, sin importar si ya estaba
        dentro de tolerancia.
        """
        client = _FakeClient("AUTOSERVICIO CALVA", "19.3200134,-99.0798081")
        maps_handler = _FakeMapsHandler({
            "found": True,
            "gps_corregido": (19.3200715, -99.0797028),
            "distance_m": 12.8,
            "maps_link": "https://maps.example/autoservicio-calva",
            "notes": "Coincide con 'AUTO SERVICIO CALVA' en Google Maps.",
        })
        result = validate_case(client, maps_handler, {"case_id": "1777"})
        assert result["status"] == "Validado ✓"
        assert result["gps_corregido"] == (19.3200715, -99.0797028)
        assert result["distance_error"] == 12.8

    def test_requires_correction_keeps_gps_corregido(self):
        client = _FakeClient("NEGOCIO X", "0.0,0.0")
        maps_handler = _FakeMapsHandler({
            "found": True,
            "gps_corregido": (0.01, 0.01),
            "distance_m": 1500.0,
            "maps_link": "https://maps.example/negocio-x",
            "notes": "",
        })
        result = validate_case(client, maps_handler, {"case_id": "9999"})
        assert result["status"] == "⚠️ Requiere corrección"
        assert result["gps_corregido"] == (0.01, 0.01)

    def test_not_found_reports_error_free_not_found_status(self):
        client = _FakeClient("NEGOCIO FANTASMA", "0.0,0.0")
        maps_handler = _FakeMapsHandler({
            "found": False, "gps_corregido": None, "distance_m": None,
            "maps_link": "https://maps.example/busqueda", "notes": "No encontrado.",
        })
        result = validate_case(client, maps_handler, {"case_id": "1111"})
        assert result["status"] == "❌ No encontrado"
        assert result["gps_corregido"] is None

    def test_extraction_error_sets_error_status_and_notes(self):
        result = validate_case(_BrokenClient(), _FakeMapsHandler({}), {"case_id": "0000"})
        assert result["status"] == "❌ Error"
        assert "boom" in result["notes"]

    def test_invalid_coordinates_from_platform_sets_error_status(self):
        client = _FakeClient("NEGOCIO Y", "no-son-coordenadas")
        result = validate_case(client, _FakeMapsHandler({}), {"case_id": "2222"})
        assert result["status"] == "❌ Error"


def test_sample_case_1777_fixture_loads():
    """La fixture de Case ID 1777 (AUTOSERVICIO CALVA) debe ser JSON válido y consistente."""
    fixture_path = Path(__file__).parent / "test_data" / "sample_case_1777.json"
    data = json.loads(fixture_path.read_text(encoding="utf-8"))
    assert data["case_id"] == "1777"
    assert data["business_name"].strip().casefold() == "autoservicio calva"
    lat, lon = parse_coordinates(data["geo_location_raw"])
    assert is_within_valid_range(lat, lon)
