# 🔧 FLUJO DE TRABAJO — Arquitectura Interna

## Objetivo

Automatizar la validación de coordenadas GPS de negocios registrados en la
plataforma de censo de baterías, contrastándolas contra Google Maps y generando
un reporte Excel con los resultados.

---

## Diagrama de flujo

```
1. Login (browser_automation.CensoBateriasClient.login)
   ↓
2. Obtener casos:
   - modo "validate": listado de pendientes (get_pending_cases)
   - modo "test":      un único Case ID (find_case_by_id)
   ↓
3. Para cada caso (validators.validate_case):
   a. Extraer negocio + coordenadas actuales (extract_case_data)
   b. Verificar en Google Maps (google_maps_handler.validate_in_google_maps)
      - ¿Existe el negocio cerca de las coordenadas actuales? → Validado ✓
      - ¿Existe pero en otra ubicación? → ⚠️ Requiere corrección + coordenadas nuevas
      - ¿No se encuentra? → ❌ No encontrado
   ↓
4. Generar Excel (excel_generator.generate_excel_report)
   ↓
5. Logs de toda la corrida en logs/automation.log
```

---

## Módulos

| Archivo | Responsabilidad |
|---|---|
| `main.py` | CLI y orquestación del flujo completo |
| `config.py` | Carga y valida configuración desde `.env` |
| `logger_config.py` | Configura loguru (consola + archivo rotativo) |
| `browser_automation.py` | Login, listado y extracción de datos vía Playwright |
| `google_maps_handler.py` | Verificación GPS contra Google Maps (API o scraping) |
| `validators.py` | Parseo/validación de coordenadas (puro) + orquestación por caso |
| `excel_generator.py` | Generación del reporte `.xlsx` con estilos |
| `utils.py` | Reintentos, capturas de pantalla, creación de carpetas |

---

## El diccionario `case`

Todo el pipeline gira alrededor de un `dict` por caso, que se va enriqueciendo:

```python
{
    "case_id": "1777",
    "url": "/cases/1777",                 # asignado al listar/buscar el caso
    "business_name": "AUTOSERVICIO CALVA",# asignado al extraer datos
    "gps_actual": (-0.2345, -78.5123),
    "gps_corregido": (-0.2350, -78.5130), # o None si coincide
    "distance_error": 62.4,               # metros, o None
    "status": "⚠️ Requiere corrección",
    "maps_link": "https://www.google.com/maps/...",
    "notes": "",
}
```

---

## Dos formas de verificar en Google Maps

1. **API de Google Places** (`GOOGLE_MAPS_API_KEY` configurada en `.env`):
   más rápido y confiable, usa `Find Place From Text`.
2. **Scraping con Playwright** (sin API key, por defecto): abre
   `google.com/maps/search/{negocio}+near+{lat},{lon}` y lee las coordenadas
   que Google embebe en la URL del resultado (`@lat,lon,zoom`).

---

## Manejo de errores

- Cada caso se procesa de forma aislada: un error en un caso (`❌ Error` en el
  Excel) no interrumpe el procesamiento de los demás.
- `utils.retry` reintenta operaciones de red hasta `MAX_REINTENTOS` veces.
- `utils.take_screenshot` guarda capturas en `logs/screenshots/` cuando
  `SCREENSHOT_ON_ERROR=true`.

---

## ⚠️ Selectores pendientes de verificación

El login (`browser_automation.CensoBateriasClient.login`) está verificado contra
el DOM real de la plataforma. El listado de casos y el detalle de un caso usan
selectores tomados de la especificación original, **sin verificar en vivo**
porque las credenciales disponibles durante el desarrollo fueron rechazadas. Ver
[TROUBLESHOOTING.md](TROUBLESHOOTING.md) antes de correr contra producción.
