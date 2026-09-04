"""Funciones utilitarias compartidas: creación de carpetas, reintentos y capturas de pantalla."""
import functools
import time
from pathlib import Path

from loguru import logger

from config import Config


def ensure_dirs() -> None:
    """Crea las carpetas de salida (output/, logs/, logs/screenshots) si no existen."""
    for directory in (Config.OUTPUT_DIR, Path(Config.LOG_FILE).parent, "logs/screenshots"):
        Path(directory).mkdir(parents=True, exist_ok=True)


def retry(times: int | None = None, delay: float = 2.0, exceptions: tuple = (Exception,)):
    """Decorador que reintenta una función ante excepciones, con espera entre intentos.

    `times` por defecto usa `Config.MAX_REINTENTOS`. Relanza la última excepción si
    se agotan los intentos.
    """

    def decorator(func):
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            attempts = times if times is not None else Config.MAX_REINTENTOS
            last_exc: Exception | None = None
            for attempt in range(1, attempts + 1):
                try:
                    return func(*args, **kwargs)
                except exceptions as exc:  # noqa: BLE001 - queremos capturar y reintentar
                    last_exc = exc
                    logger.warning(f"Intento {attempt}/{attempts} falló en {func.__name__}: {exc}")
                    if attempt < attempts:
                        time.sleep(delay)
            logger.error(f"{func.__name__} falló tras {attempts} intentos.")
            raise last_exc

        return wrapper

    return decorator


def take_screenshot(page, name: str) -> str | None:
    """Guarda una captura de pantalla de `page` en logs/screenshots/{name}.png.

    No hace nada (devuelve None) si `Config.SCREENSHOT_ON_ERROR` es False o si `page`
    ya está cerrada. Nunca lanza excepción: una captura fallida no debe tumbar el flujo.
    """
    if not Config.SCREENSHOT_ON_ERROR:
        return None
    ensure_dirs()
    path = Path("logs/screenshots") / f"{name}.png"
    try:
        page.screenshot(path=str(path))
        logger.info(f"Captura guardada: {path}")
        return str(path)
    except Exception as exc:  # noqa: BLE001 - una captura fallida no debe romper el flujo
        logger.warning(f"No se pudo guardar la captura '{name}': {exc}")
        return None
