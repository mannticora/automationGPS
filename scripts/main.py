"""Orquestador principal: login, extracción de casos, validación GPS y generación de reporte.

Ejemplos de uso:
    python main.py --dry-run
    python main.py --mode=test --case-id=1777 --headless=false
    python main.py --mode=validate --limit=10
    python main.py --mode=validate --log-level=DEBUG
    python main.py --case-ids=1778-1782 --output=reporte_1778_1782.xlsx
    python main.py --output=mi_reporte_custom.xlsx
"""
import argparse
import sys
import time

from loguru import logger
from playwright.sync_api import sync_playwright

from browser_automation import CaseNotFoundError, CensoBateriasClient, LoginError
from config import Config
from excel_generator import generate_excel_report
from google_maps_handler import GoogleMapsHandler
from logger_config import setup_logging
from utils import ensure_dirs, parse_case_ids
from validators import validate_case


def parse_args() -> argparse.Namespace:
    """Define y parsea los argumentos de línea de comandos."""
    parser = argparse.ArgumentParser(description="Validación automática de coordenadas GPS - Censo Baterías")
    parser.add_argument("--mode", choices=["validate", "test"], default="validate",
                         help="'validate' procesa los casos pendientes; 'test' procesa un único --case-id.")
    parser.add_argument("--case-id", help="Case ID específico a validar (requerido con --mode=test).")
    parser.add_argument("--case-ids", help="Lista/rango de Case IDs a validar, ej. '1778-1782' o '1778,1780,1782'. "
                                            "Tiene prioridad sobre --mode/--case-id.")
    parser.add_argument("--headless", choices=["true", "false"], default=None,
                         help="Sobrescribe HEADLESS_MODE de .env.")
    parser.add_argument("--limit", type=int, default=None, help="Máximo de casos a procesar en modo 'validate'.")
    parser.add_argument("--output", default=None, help="Nombre/ruta del Excel de salida.")
    parser.add_argument("--log-level", default=None, help="Sobrescribe LOG_LEVEL de .env (DEBUG, INFO, ...).")
    parser.add_argument("--dry-run", action="store_true",
                         help="Solo valida la configuración; no se conecta a la plataforma.")
    return parser.parse_args()


def _build_maps_handler(playwright, headless: bool | None) -> GoogleMapsHandler:
    """Crea el handler de Google Maps, pasando Playwright solo si hace falta para scraping."""
    return GoogleMapsHandler(
        playwright=None if Config.GOOGLE_MAPS_API_KEY else playwright,
        headless=headless,
    )


def main() -> None:
    """Punto de entrada del script."""
    args = parse_args()
    setup_logging(args.log_level)
    ensure_dirs()

    try:
        Config.validate()
    except ValueError as exc:
        logger.error(str(exc))
        sys.exit(1)

    if args.dry_run:
        logger.success("Configuración válida. (--dry-run: no se realizó ninguna conexión)")
        return

    headless = None if args.headless is None else args.headless == "true"
    cases: list[dict] = []

    with sync_playwright() as playwright:
        client = CensoBateriasClient(playwright, headless=headless)
        maps_handler = _build_maps_handler(playwright, headless)
        try:
            client.login()

            if args.case_ids:
                try:
                    ids = parse_case_ids(args.case_ids)
                except ValueError as exc:
                    logger.error(f"--case-ids inválido: {exc}")
                    sys.exit(1)
                for case_id in ids:
                    try:
                        cases.append(client.find_case_by_id(case_id))
                    except CaseNotFoundError as exc:
                        logger.warning(str(exc))
            elif args.mode == "test":
                if not args.case_id:
                    logger.error("--mode=test requiere --case-id.")
                    sys.exit(1)
                try:
                    cases = [client.find_case_by_id(args.case_id)]
                except CaseNotFoundError as exc:
                    logger.error(str(exc))
                    sys.exit(1)
            else:
                cases = client.get_pending_cases(limit=args.limit or Config.CASOS_PROCESADOS_LIMITE)

            for case in cases:
                validate_case(client, maps_handler, case)
                time.sleep(Config.DELAY_ENTRE_CASOS)

        except LoginError as exc:
            logger.error(f"No se pudo iniciar sesión: {exc}")
            sys.exit(1)
        finally:
            maps_handler.close()
            client.close()

    if cases:
        output_path = generate_excel_report(cases, args.output)
        logger.success(f"Proceso completo. Reporte: {output_path}")
    else:
        logger.warning("No se procesó ningún caso; no se generó reporte.")


if __name__ == "__main__":
    main()
