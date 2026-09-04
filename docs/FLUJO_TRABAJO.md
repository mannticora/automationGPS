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
    "business_name": "Autoservicio calva",# asignado al extraer datos
    "gps_actual": (19.3200134, -99.0798081),
    "gps_corregido": (19.3200715, -99.0797028), # coordenada verificada en Maps; None si no se encontró el negocio o la diferencia es <1m
    "distance_error": 12.8,               # metros, o None
    "status": "Validado ✓",
    "maps_link": "https://www.google.com/maps/place/...",
    "notes": "Coincide con 'AUTO SERVICIO CALVA' en Google Maps.",
    "business_status": "Operando (...)",          # Sección 5 (ESTNEG), texto tal cual
    "brands": ["FULL POWER", "GONHER", "GONHER PRIME", "LTH"], # Sección 7
    "missing_photos": ["Fachada", "Interior", ...],            # Sección 13, etiquetas sin foto
    "total_photo_fields": 6,
    "calidad_sugerida": "EN_RECUPERACION",        # ver suggest_quality_verdict
    "tipo_encuesta_sugerido": "EN_RECUPERACION",
}
```

`gps_corregido` se reporta **siempre** que Google Maps encuentre el negocio (sin
importar el `status`) — el equipo lo copia manualmente al campo "GPS correcto
(lat, lon)" de la plataforma como parte de su propio control de calidad, incluso
en casos ya `Validado ✓`. Solo queda en `None` cuando no se encontró el negocio en
Maps, o cuando la diferencia con `gps_actual` es menor a 1 metro (el mismo punto).

### Marcas, fotos y veredicto de calidad sugerido

Además de la validación GPS, `extract_case_data` también lee la Sección 5
(Estatus del negocio), la Sección 7 (Marcas de baterías registradas) y la
Sección 13 (qué fotos faltan, de las 6 requeridas: Fachada, Interior, Exhibidor,
Exhibidor 2, Negocio, Material POP). `validators.suggest_quality_verdict`
combina esas señales con el resultado de GPS para **sugerir** una Calidad
(`APROBADA` / `EN_RECUPERACION` / `CANCELADA`) y un Tipo de encuesta a capturar
en la plataforma — nunca los aplica: son solo una recomendación para que un
humano decida y los capture manualmente en `revisar.php`. Reglas, en orden:

1. Negocio "Cerrado definitivo" o "No aparece" → `CANCELADA` / `NEGADA`.
2. Error al extraer o validar el caso → `EN_RECUPERACION` / `INCIDENCIA`.
3. Ninguna foto cargada (0/6) → `EN_RECUPERACION` / `EN_RECUPERACION`.
4. Faltan algunas fotos, o el negocio no se encontró en Maps →
   `EN_RECUPERACION` / `INCIDENCIA`.
5. En cualquier otro caso → `APROBADA` / `COMPLETA`.

---

## Dos formas de verificar en Google Maps

1. **API de Google Places** (`GOOGLE_MAPS_API_KEY` configurada en `.env`):
   más rápido y confiable, usa `Find Place From Text`.
2. **Scraping con Playwright** (sin API key, por defecto): abre
   `google.com/maps/search/{negocio}/@{lat},{lon},16z` (centra el mapa ahí y
   busca el negocio) y lee las coordenadas exactas embebidas en el `href` de
   cada resultado (`a[href*="/maps/place/"]`, patrón `!3d{lat}!4d{lon}`).
   *No* usar `+near+{lat},{lon}`: Google lo trata como texto literal — ver
   [TROUBLESHOOTING.md](TROUBLESHOOTING.md).

---

## Manejo de errores

- Cada caso se procesa de forma aislada: un error en un caso (`❌ Error` en el
  Excel) no interrumpe el procesamiento de los demás.
- `utils.retry` reintenta operaciones de red hasta `MAX_REINTENTOS` veces.
- `utils.take_screenshot` guarda capturas en `logs/screenshots/` cuando
  `SCREENSHOT_ON_ERROR=true`.

---

## ✅ Selectores verificados en vivo (2026-09-04)

Todo el flujo (login, listado "Cola de revisión", detalle de un caso y búsqueda en
Google Maps) fue verificado contra la plataforma real y contra Google Maps, usando
Case ID 1777 (AUTOSERVICIO CALVA) y un lote de 3 casos pendientes reales. Detalles
de los selectores exactos en los docstrings de `browser_automation.py` y
`google_maps_handler.py`; dos bugs no obvios encontrados durante esa verificación
(contexto de navegador no compartido, búsqueda "near" de Google Maps) están
documentados en [TROUBLESHOOTING.md](TROUBLESHOOTING.md).
