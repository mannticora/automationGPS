# scripts/ — Ejemplos de uso

Todos los comandos se ejecutan desde la raíz del proyecto, con el entorno virtual
activo y `.env` configurado (ver [../docs/SETUP.md](../docs/SETUP.md)).

## CLI (`main.py`)

```bash
# Solo valida la configuración de .env, sin conectarse a la plataforma
python scripts/main.py --dry-run

# Validar un único Case ID, con navegador visible (útil para depurar selectores)
python scripts/main.py --mode=test --case-id=1777 --headless=false

# Validación completa en modo headless (por defecto)
python scripts/main.py --mode=validate

# Limitar a los primeros 10 casos pendientes
python scripts/main.py --mode=validate --limit=10

# Logging detallado para depuración
python scripts/main.py --mode=validate --log-level=DEBUG

# Nombre de archivo de salida personalizado
python scripts/main.py --mode=validate --output=mi_reporte_custom.xlsx
```

## Usando los módulos por separado

### `config.py` — configuración desde `.env`

```python
from config import Config

Config.validate()          # lanza ValueError si faltan credenciales
print(Config.CENSO_URL, Config.HEADLESS_MODE, Config.MAX_REINTENTOS)
```

### `validators.py` — parseo y validación de coordenadas (sin navegador)

```python
from validators import parse_coordinates, haversine_distance_m, build_case_status

lat, lon = parse_coordinates("-0.2345,-78.5123")
distancia_m = haversine_distance_m(lat, lon, -0.2350, -78.5130)
estado = build_case_status(found=True, distance_m=distancia_m)
```

### `excel_generator.py` — generar un reporte a partir de una lista de casos

```python
from excel_generator import generate_excel_report

cases = [
    {
        "case_id": "1777",
        "business_name": "AUTOSERVICIO CALVA",
        "gps_actual": (-0.2345, -78.5123),
        "gps_corregido": None,
        "status": "Validado ✓",
        "distance_error": 12.3,
        "maps_link": "https://www.google.com/maps/search/?api=1&query=-0.2345,-78.5123",
        "notes": "",
    },
]
ruta = generate_excel_report(cases, "reporte_ejemplo.xlsx")
```

### `browser_automation.py` — flujo completo con Playwright

```python
from playwright.sync_api import sync_playwright
from browser_automation import CensoBateriasClient

with sync_playwright() as playwright:
    client = CensoBateriasClient(playwright, headless=False)
    client.login()
    caso = client.find_case_by_id("1777")
    datos = client.extract_case_data(caso["case_id"], caso["url"])
    print(datos)  # {"business_name": ..., "geo_location_raw": ...}
    client.close()
```

## Tests

```bash
python -m pytest ../tests/ -v
```
