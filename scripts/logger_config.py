"""Configuración de logging con loguru: consola con color + archivo rotativo en logs/."""
import sys
from pathlib import Path

from loguru import logger

from config import Config

_CONSOLE_FORMAT = (
    "<green>{time:YYYY-MM-DD HH:mm:ss}</green> | "
    "<level>{level: <8}</level> | "
    "<cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> - "
    "<level>{message}</level>"
)
_FILE_FORMAT = "{time:YYYY-MM-DD HH:mm:ss} | {level: <8} | {name}:{function}:{line} - {message}"


def setup_logging(log_level: str | None = None):
    """Configura los sinks de loguru (consola + archivo) y devuelve el logger listo para usar.

    Se debe llamar una única vez, al arrancar `main.py`. El resto de módulos solo
    necesitan `from loguru import logger`.
    """
    level = (log_level or Config.LOG_LEVEL).upper()

    logger.remove()
    logger.add(sys.stderr, level=level, colorize=True, format=_CONSOLE_FORMAT)

    log_path = Path(Config.LOG_FILE)
    log_path.parent.mkdir(parents=True, exist_ok=True)
    logger.add(
        log_path,
        level=level,
        format=_FILE_FORMAT,
        rotation=f"{Config.LOG_MAX_SIZE_MB} MB",
        retention=10,
        encoding="utf-8",
    )

    logger.debug(f"Logging inicializado (nivel={level}, archivo={log_path}).")
    return logger
