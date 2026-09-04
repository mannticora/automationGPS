"""Verificación de coordenadas GPS contra Google Maps.

Usa la API de Google Places (`Find Place From Text`) si `GOOGLE_MAPS_API_KEY` está
configurada en `.env` (más robusto y recomendado); si no, cae a scraping de Google
Maps con Playwright, leyendo las coordenadas que Google embebe en la URL del
resultado (patrón `@lat,lon,zoom`).
"""
import re
import time

import requests
from loguru import logger

from config import Config
from validators import haversine_distance_m

_PLACE_URL_COORD_PATTERN = re.compile(r"@(-?\d+\.\d+),(-?\d+\.\d+)")
_MIN_METERS_TO_FLAG_CORRECTION = 1.0


class GoogleMapsHandler:
    """Valida si un negocio existe cerca de unas coordenadas dadas."""

    def __init__(self, playwright=None, headless: bool | None = None):
        """`playwright` es requerido solo cuando no hay `GOOGLE_MAPS_API_KEY` configurada."""
        self._use_api = bool(Config.GOOGLE_MAPS_API_KEY)
        self._browser = None
        if not self._use_api:
            if playwright is None:
                raise ValueError(
                    "GOOGLE_MAPS_API_KEY no está configurada: se requiere una instancia "
                    "de Playwright para el modo de scraping."
                )
            resolved_headless = Config.HEADLESS_MODE if headless is None else headless
            self._browser = playwright.chromium.launch(headless=resolved_headless)

    def validate_in_google_maps(self, business_name: str, lat: float, lon: float,
                                 search_radius_m: int | None = None) -> dict:
        """Verifica si `business_name` existe cerca de (lat, lon).

        Devuelve `{"found": bool, "gps_corregido": (lat, lon) | None,
        "distance_m": float | None, "maps_link": str, "notes": str}`.
        """
        radius = search_radius_m or Config.GOOGLE_MAPS_SEARCH_RADIUS
        time.sleep(Config.DELAY_GOOGLE_MAPS)
        if self._use_api:
            return self._validate_via_api(business_name, lat, lon, radius)
        return self._validate_via_browser(business_name, lat, lon, radius)

    def _validate_via_api(self, business_name: str, lat: float, lon: float, radius: int) -> dict:
        params = {
            "input": business_name,
            "inputtype": "textquery",
            "locationbias": f"circle:{radius}@{lat},{lon}",
            "fields": "name,geometry,formatted_address",
            "key": Config.GOOGLE_MAPS_API_KEY,
        }
        response = requests.get(
            "https://maps.googleapis.com/maps/api/place/findplacefromtext/json",
            params=params,
            timeout=15,
        )
        response.raise_for_status()
        payload = response.json()
        candidates = payload.get("candidates", [])
        maps_link = f"https://www.google.com/maps/search/?api=1&query={lat},{lon}"

        if not candidates:
            logger.warning(f"Google Places no encontró '{business_name}' cerca de ({lat}, {lon}).")
            return {
                "found": False,
                "gps_corregido": None,
                "distance_m": None,
                "maps_link": maps_link,
                "notes": f"Google Places no encontró '{business_name}' cerca de las coordenadas actuales.",
            }

        location = candidates[0]["geometry"]["location"]
        found_lat, found_lon = location["lat"], location["lng"]
        distance_m = round(haversine_distance_m(lat, lon, found_lat, found_lon), 1)
        return {
            "found": True,
            "gps_corregido": (found_lat, found_lon) if distance_m > _MIN_METERS_TO_FLAG_CORRECTION else None,
            "distance_m": distance_m,
            "maps_link": f"https://www.google.com/maps/search/?api=1&query={found_lat},{found_lon}",
            "notes": candidates[0].get("formatted_address", ""),
        }

    def _validate_via_browser(self, business_name: str, lat: float, lon: float, radius: int) -> dict:
        page = self._browser.new_page()
        search_url = f"https://www.google.com/maps/search/{business_name}+near+{lat},{lon}"
        try:
            page.goto(search_url)
            page.wait_for_timeout(3000)
            current_url = page.url
            match = _PLACE_URL_COORD_PATTERN.search(current_url)

            if not match:
                logger.warning(f"No se pudo confirmar visualmente '{business_name}' en Google Maps.")
                return {
                    "found": False,
                    "gps_corregido": None,
                    "distance_m": None,
                    "maps_link": search_url,
                    "notes": f"No se pudo confirmar visualmente '{business_name}' en Google Maps.",
                }

            found_lat, found_lon = float(match.group(1)), float(match.group(2))
            distance_m = round(haversine_distance_m(lat, lon, found_lat, found_lon), 1)
            return {
                "found": True,
                "gps_corregido": (found_lat, found_lon) if distance_m > _MIN_METERS_TO_FLAG_CORRECTION else None,
                "distance_m": distance_m,
                "maps_link": current_url,
                "notes": "",
            }
        finally:
            page.close()

    def close(self) -> None:
        """Cierra el navegador interno (no-op si se está usando la API de Places)."""
        if self._browser:
            self._browser.close()
