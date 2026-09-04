"""Funciones utilitarias compartidas: creación de carpetas, reintentos y capturas de pantalla."""
import functools
import time
from pathlib import Path

from loguru import logger

from config import Config


def parse_case_ids(spec: str) -> list[str]:
    """Convierte una lista/rango de Case IDs en una lista de strings.

    Acepta comas y rangos con guion, combinables: "1778-1782" -> ["1778", ...,
    "1782"]; "1778,1780,1782" -> esos tres; "1778-1780,1790" -> ["1778","1779",
    "1780","1790"]. Lanza ValueError si algún fragmento no es un entero ni un
    rango `inicio-fin` válido.
    """
    ids: list[str] = []
    for part in spec.split(","):
        part = part.strip()
        if not part:
            continue
        if "-" in part:
            start_str, _, end_str = part.partition("-")
            start, end = int(start_str.strip()), int(end_str.strip())
            if end < start:
                raise ValueError(f"Rango inválido (fin < inicio): {part!r}")
            ids.extend(str(i) for i in range(start, end + 1))
        else:
            int(part)  # valida que sea numérico; conservamos el string original
            ids.append(part)
    return ids


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
