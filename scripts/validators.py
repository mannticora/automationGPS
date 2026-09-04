"""Lógica de validación de coordenadas GPS y orquestación de la validación por caso.

Las funciones de parseo/geometría son puras (sin efectos secundarios) para que sean
fáciles de probar sin necesidad de un navegador real — ver tests/test_validators.py.
"""
import math
import re

from loguru import logger

_COORD_PATTERN = re.compile(r"^\s*(-?\d+(?:\.\d+)?)\s*,\s*(-?\d+(?:\.\d+)?)\s*$")


def is_within_valid_range(lat: float, lon: float) -> bool:
    """Indica si (lat, lon) están dentro de rangos geográficos válidos."""
    return -90.0 <= lat <= 90.0 and -180.0 <= lon <= 180.0


def parse_coordinates(raw: str) -> tuple[float, float]:
    """Convierte un string "lat,lon" (con o sin espacios) en una tupla (lat, lon).

    Lanza ValueError si el formato no es reconocible o si las coordenadas quedan
    fuera de rango válido.
    """
    if not raw or not isinstance(raw, str):
        raise ValueError(f"Coordenadas vacías o inválidas: {raw!r}")

    match = _COORD_PATTERN.match(raw)
    if not match:
        raise ValueError(f"Formato de coordenadas no reconocido: {raw!r}")

    lat, lon = float(match.group(1)), float(match.group(2))
    if not is_within_valid_range(lat, lon):
        raise ValueError(f"Coordenadas fuera de rango válido: ({lat}, {lon})")
    return lat, lon


def haversine_distance_m(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """Calcula la distancia en metros entre dos puntos GPS usando la fórmula de Haversine."""
    earth_radius_m = 6371000.0
    phi1, phi2 = math.radians(lat1), math.radians(lat2)
    d_phi = math.radians(lat2 - lat1)
    d_lambda = math.radians(lon2 - lon1)
    a = math.sin(d_phi / 2) ** 2 + math.cos(phi1) * math.cos(phi2) * math.sin(d_lambda / 2) ** 2
    return 2 * earth_radius_m * math.asin(math.sqrt(a))


def coordinates_match(lat1: float, lon1: float, lat2: float, lon2: float, tolerance_m: float = 50.0) -> bool:
    """Indica si dos coordenadas son "la misma ubicación" dentro de una tolerancia en metros."""
    return haversine_distance_m(lat1, lon1, lat2, lon2) <= tolerance_m


DISTANT_MATCH_STATUS = "❓ Coincidencia lejana (revisar manualmente)"
_NOT_RELIABLY_FOUND_STATUSES = ("❌ No encontrado", DISTANT_MATCH_STATUS)
_DEFAULT_MAX_TRUSTED_DISTANCE_M = 2000.0


def build_case_status(found: bool, distance_m: float | None, tolerance_m: float = 50.0,
                       max_trusted_distance_m: float = _DEFAULT_MAX_TRUSTED_DISTANCE_M) -> str:
    """Decide el estado textual de un caso a partir del resultado de la búsqueda en Maps.

    Si el resultado más cercano por nombre está a más de `max_trusted_distance_m` (por
    defecto 2km), es mucho más probable que sea un negocio distinto con nombre parecido
    en otra parte de la ciudad que una corrección real de GPS — se marca aparte
    (`DISTANT_MATCH_STATUS`) en vez de sugerir esa coordenada como "corrección".
    """
    if not found:
        return "❌ No encontrado"
    if distance_m is None or distance_m <= tolerance_m:
        return "Validado ✓"
    if distance_m > max_trusted_distance_m:
        return DISTANT_MATCH_STATUS
    return "⚠️ Requiere corrección"


_CLOSED_BUSINESS_MARKERS = ("cerrado definitivo", "no aparece")


def suggest_quality_verdict(gps_status: str, business_status: str, missing_photos: list[str],
                             total_photo_fields: int) -> tuple[str, str, str]:
    """Sugiere `(calidad, tipo_encuesta, observaciones)` para que un humano revise.

    Es solo una RECOMENDACIÓN a partir de señales objetivas ya extraídas de la plataforma
    (estatus del negocio, resultado de GPS, fotos faltantes) — nunca se aplica sola en
    `revisar.php`; el texto de `observaciones` está pensado para pegarse tal cual en el
    campo OBSERVACIONES_CALIDAD de la plataforma si el equipo está de acuerdo. Reglas,
    en orden de prioridad:

    1. Negocio cerrado/inexistente (ESTNEG contiene "Cerrado definitivo" o "No aparece")
       -> `CANCELADA` / `NEGADA`.
    2. Error al extraer o validar el caso -> `EN_RECUPERACION` / `INCIDENCIA`.
    3. Ninguna de las fotos requeridas fue cargada -> `EN_RECUPERACION` / `EN_RECUPERACION`
       (falta toda evidencia visual).
    4. Faltan algunas fotos, o el negocio no se encontró de forma confiable en Google Maps
       (no encontrado, o el resultado más cercano está a más de 2km) -> `EN_RECUPERACION` / `INCIDENCIA`.
    5. En cualquier otro caso -> `APROBADA` / `COMPLETA`.
    """
    business_status_norm = (business_status or "").strip().casefold()
    missing_photos = missing_photos or []

    if any(marker in business_status_norm for marker in _CLOSED_BUSINESS_MARKERS):
        observaciones = (
            f'Negocio reportado como "{business_status}"; la encuesta no es válida para '
            "este censo."
        )
        return "CANCELADA", "NEGADA", observaciones

    if gps_status == "❌ Error":
        observaciones = (
            "No se pudo completar la validación automática (error al extraer datos de la "
            "plataforma o al consultar Google Maps); revisar el caso manualmente."
        )
        return "EN_RECUPERACION", "INCIDENCIA", observaciones

    if total_photo_fields and len(missing_photos) == total_photo_fields:
        observaciones = (
            f"No se cargó ninguna de las {total_photo_fields} fotos requeridas "
            f"({', '.join(missing_photos)}); sin evidencia visual de las marcas registradas."
        )
        return "EN_RECUPERACION", "EN_RECUPERACION", observaciones

    if missing_photos:
        observaciones = (
            f"Faltan {len(missing_photos)} de {total_photo_fields} fotos: "
            f"{', '.join(missing_photos)}."
        )
        if gps_status in _NOT_RELIABLY_FOUND_STATUSES:
            observaciones += " Además, el negocio no se encontró de forma confiable en Google Maps."
        return "EN_RECUPERACION", "INCIDENCIA", observaciones

    if gps_status in _NOT_RELIABLY_FOUND_STATUSES:
        observaciones = (
            "El negocio no se encontró de forma confiable en Google Maps cerca de las "
            "coordenadas registradas (sin resultado, o el más cercano está a una distancia "
            "no confiable); verificar ubicación manualmente."
        )
        return "EN_RECUPERACION", "INCIDENCIA", observaciones

    observaciones = "Ubicación validada en Google Maps y fotografías completas; sin observaciones."
    return "APROBADA", "COMPLETA", observaciones


def validate_case(client, maps_handler, case: dict, tolerance_m: float = 50.0) -> dict:
    """Orquesta la validación completa de un caso: extrae datos de la plataforma y
    los contrasta contra Google Maps. Modifica y devuelve `case` con los resultados.

    `client` es un `browser_automation.CensoBateriasClient` y `maps_handler` un
    `google_maps_handler.GoogleMapsHandler`. Cualquier error se captura y se refleja
    en case['status'] / case['notes'] en lugar de propagarse, para no interrumpir el
    procesamiento del resto de casos.
    """
    logger.info(f"Validando Case ID {case.get('case_id')}...")

    try:
        data = client.extract_case_data(case["case_id"], case.get("url"))
        case["business_name"] = data["business_name"]
        case["business_name_original"] = data.get("business_name_original", "")
        case["gps_actual"] = parse_coordinates(data["geo_location_raw"])
        case["business_status"] = data.get("business_status", "")
        case["brands"] = data.get("brands", [])
        case["missing_photos"] = data.get("missing_photos", [])
        case["total_photo_fields"] = data.get("total_photo_fields", 0)
    except Exception as exc:  # noqa: BLE001 - se registra y se continúa con el siguiente caso
        logger.error(f"Error extrayendo datos del Case ID {case.get('case_id')}: {exc}")
        case["status"] = "❌ Error"
        case["notes"] = str(exc)
        return case

    # El nombre editable (nomneg) puede quedar vacío aunque sí exista un nombre original
    # capturado en campo (NEG_NOMBRE_NEGOCIO precargado) — usarlo como respaldo evita
    # buscar en Google Maps con un nombre vacío cuando sí hay algo que buscar.
    search_name = case["business_name"] or case.get("business_name_original", "")
    try:
        result = maps_handler.validate_in_google_maps(
            business_name=search_name,
            lat=case["gps_actual"][0],
            lon=case["gps_actual"][1],
            search_radius_m=case.get("search_radius_m"),
        )
    except Exception as exc:  # noqa: BLE001 - idem
        logger.error(f"Error validando en Google Maps el Case ID {case.get('case_id')}: {exc}")
        case["status"] = "❌ Error"
        case["notes"] = str(exc)
        return case

    case["distance_error"] = result.get("distance_m")
    case["maps_link"] = result.get("maps_link")
    case["status"] = build_case_status(result.get("found", False), result.get("distance_m"), tolerance_m)
    case["notes"] = result.get("notes", "")
    # Siempre reportamos la coordenada verificada en Google Maps cuando exista (incluso en
    # casos "Validado ✓" dentro de tolerancia): el equipo la copia manualmente al campo
    # "GPS correcto (lat, lon)" de la plataforma como parte de su propio control de calidad.
    # google_maps_handler ya la omite si la diferencia es < 1m (prácticamente el mismo punto).
    case["gps_corregido"] = result.get("gps_corregido")

    case["calidad_sugerida"], case["tipo_encuesta_sugerido"], case["observaciones_calidad"] = suggest_quality_verdict(
        gps_status=case["status"],
        business_status=case.get("business_status", ""),
        missing_photos=case.get("missing_photos", []),
        total_photo_fields=case.get("total_photo_fields", 0),
    )

    logger.info(f"Case ID {case.get('case_id')} -> {case['status']} | Calidad sugerida: {case['calidad_sugerida']}")
    return case
