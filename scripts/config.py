"""Configuración centralizada del proyecto, cargada desde variables de entorno (.env).

Ningún valor sensible debe hardcodearse aquí: todo se lee de `.env` (ver `.env.example`).
"""
import os
from pathlib import Path

from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parent.parent
load_dotenv(BASE_DIR / ".env")


def _get_bool(name: str, default: bool) -> bool:
    """Lee una variable de entorno booleana ('true'/'false', case-insensitive)."""
    value = os.getenv(name)
    if value is None:
        return default
    return value.strip().lower() in ("1", "true", "yes", "on")


def _get_int(name: str, default: int) -> int:
    """Lee una variable de entorno entera, usando `default` si falta o es inválida."""
    try:
        return int(os.getenv(name, default))
    except (TypeError, ValueError):
        return default


def _get_float(name: str, default: float) -> float:
    """Lee una variable de entorno decimal, usando `default` si falta o es inválida."""
    try:
        return float(os.getenv(name, default))
    except (TypeError, ValueError):
        return default


class Config:
    """Agrupa toda la configuración leída de `.env` como atributos de clase."""

    # Plataforma Censo Baterías
    CENSO_URL = os.getenv("CENSO_URL", "https://censobaterias.pricepointmonitor.com/")
    CENSO_EMAIL = os.getenv("CENSO_EMAIL", "")
    CENSO_PASSWORD = os.getenv("CENSO_PASSWORD", "")

    # Comportamiento de Playwright / RPA
    HEADLESS_MODE = _get_bool("HEADLESS_MODE", True)
    TIMEOUT_SEGUNDOS = _get_int("TIMEOUT_SEGUNDOS", 60)
    MAX_REINTENTOS = _get_int("MAX_REINTENTOS", 3)
    SCREENSHOT_ON_ERROR = _get_bool("SCREENSHOT_ON_ERROR", True)
    BROWSER_TYPE = os.getenv("BROWSER_TYPE", "chromium")

    # Logging
    LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO")
    LOG_FILE = os.getenv("LOG_FILE", "logs/automation.log")
    LOG_MAX_SIZE_MB = _get_int("LOG_MAX_SIZE_MB", 50)

    # Output
    OUTPUT_DIR = os.getenv("OUTPUT_DIR", "output/")
    EXCEL_FILENAME_PATTERN = os.getenv("EXCEL_FILENAME_PATTERN", "reporte_validaciones_%Y%m%d_%H%M%S.xlsx")
    INCLUDE_SCREENSHOTS = _get_bool("INCLUDE_SCREENSHOTS", False)

    # Procesamiento
    CASOS_PROCESADOS_LIMITE = _get_int("CASOS_PROCESADOS_LIMITE", 100)
    DELAY_ENTRE_CASOS = _get_float("DELAY_ENTRE_CASOS", 2)
    DELAY_GOOGLE_MAPS = _get_float("DELAY_GOOGLE_MAPS", 1)

    # Filtros del listado
    FILTRO_ESTADO = os.getenv("FILTRO_ESTADO", "pending")
    ORDEN_POR = os.getenv("ORDEN_POR", "case_id")
    ORDEN_ASCENDENTE = _get_bool("ORDEN_ASCENDENTE", True)

    # Google Maps
    GOOGLE_MAPS_API_KEY = os.getenv("GOOGLE_MAPS_API_KEY", "")
    GOOGLE_MAPS_SEARCH_RADIUS = _get_int("GOOGLE_MAPS_SEARCH_RADIUS", 500)

    # Ambiente
    AMBIENTE = os.getenv("AMBIENTE", "development")
    DEBUG = _get_bool("DEBUG", False)

    @classmethod
    def validate(cls) -> None:
        """Valida que la configuración mínima requerida esté presente.

        Lanza ValueError con un mensaje claro si falta algo esencial (credenciales).
        """
        required = {"CENSO_EMAIL": cls.CENSO_EMAIL, "CENSO_PASSWORD": cls.CENSO_PASSWORD}
        missing = [name for name, value in required.items() if not value]
        if missing:
            raise ValueError(
                f"Faltan variables de entorno requeridas: {', '.join(missing)}. "
                f"Copia .env.example a .env y complétalas."
            )
