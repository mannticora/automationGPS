"""Verificación de coordenadas GPS contra Google Maps.

Usa la API de Google Places (`Find Place From Text`) si `GOOGLE_MAPS_API_KEY` está
configurada en `.env` (más robusto y recomendado); si no, cae a scraping de Google
Maps con Playwright.

Nota sobre el scraping (verificado en vivo 2026-09-04): buscar con
`.../search/{negocio}+near+{lat},{lon}` NO funciona — Google interpreta "near" como
texto literal y, cuando no encuentra nada, redirige a una vista de mapa genérica que
igual contiene un patrón `@lat,lon,zoom` en la URL (falso positivo de "encontrado").
El patrón que sí funciona es `.../search/{negocio}/@{lat},{lon},16z`, que centra el
mapa en las coordenadas y ordena los resultados por relevancia/cercanía; cada
resultado (`a[href*="/maps/place/"]`) trae sus coordenadas exactas embebidas como
`!3d{lat}!4d{lon}` en el propio href.
"""
import re
import time
from urllib.parse import quote_plus

import requests
from loguru import logger

from config import Config
from validators import haversine_distance_m

_PLACE_LINK_COORD_PATTERN = re.compile(r"!3d(-?\d+\.\d+)!4d(-?\d+\.\d+)")
_MIN_METERS_TO_FLAG_CORRECTION = 1.0
_MAX_CANDIDATES_TO_INSPECT = 5


def _normalize(text: str) -> str:
    """Normaliza un nombre de negocio para compararlo de forma tolerante a mayúsculas y espacios."""
    return re.sub(r"\s+", "", text.strip().casefold())


def _pick_best_candidate(candidates: list[dict], business_name: str) -> tuple[dict, bool]:
    """Elige, entre los primeros resultados, el que mejor coincide de nombre con `business_name`.

    Devuelve `(candidato, coincidencia_de_nombre)`. Si ninguno coincide de nombre,
    cae al primero (el más relevante/cercano según Google) y lo marca como tal.
    """
    target = _normalize(business_name)
    for candidate in candidates:
        name = _normalize(candidate["name"])
        if target == name or target in name or name in target:
            return candidate, True
    return candidates[0], False


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
        # Centra el mapa en (lat, lon) y busca el negocio; NO usar "+near+lat,lon" (ver nota
        # de módulo) porque Google lo trata como texto literal y no filtra por ubicación.
        zoom = 16
        search_url = f"https://www.google.com/maps/search/{quote_plus(business_name)}/@{lat},{lon},{zoom}z"
        try:
            page.goto(search_url)
            page.wait_for_timeout(3000)

            links = page.locator("a[href*='/maps/place/']")
            count = min(links.count(), _MAX_CANDIDATES_TO_INSPECT)
            candidates = []
            for i in range(count):
                href = links.nth(i).get_attribute("href") or ""
                name = (links.nth(i).text_content() or "").strip()
                coord_match = _PLACE_LINK_COORD_PATTERN.search(href)
                if name and coord_match:
                    candidates.append({
                        "name": name,
                        "lat": float(coord_match.group(1)),
                        "lon": float(coord_match.group(2)),
                        "href": href,
                    })

            if not candidates:
                logger.warning(f"Google Maps no encontró resultados para '{business_name}' cerca de ({lat}, {lon}).")
                return {
                    "found": False,
                    "gps_corregido": None,
                    "distance_m": None,
                    "maps_link": search_url,
                    "notes": f"Google Maps no encontró resultados para '{business_name}' cerca de las coordenadas actuales.",
                }

            best, name_matched = _pick_best_candidate(candidates, business_name)
            distance_m = round(haversine_distance_m(lat, lon, best["lat"], best["lon"]), 1)
            notes = (
                f"Coincide con '{best['name']}' en Google Maps."
                if name_matched
                else f"Sin coincidencia exacta de nombre; usando el resultado más cercano: '{best['name']}'."
            )
            return {
                "found": True,
                "gps_corregido": (best["lat"], best["lon"]) if distance_m > _MIN_METERS_TO_FLAG_CORRECTION else None,
                "distance_m": distance_m,
                "maps_link": best["href"],
                "notes": notes,
            }
        finally:
            page.close()

    def close(self) -> None:
        """Cierra el navegador interno (no-op si se está usando la API de Places)."""
        if self._browser:
            self._browser.close()
