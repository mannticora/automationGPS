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
    "business_name": "Autoservicio calva",# campo editable "nomneg" (Sección 10)
    "business_name_original": "AUTOSERVICIO CALVA", # campo "precargado", tal como se capturó en campo
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
    "observaciones_calidad": "No se cargó ninguna de las 6 fotos requeridas (...)",
}
```

`gps_corregido` se reporta **siempre** que Google Maps encuentre el negocio (sin
importar el `status`) — el equipo lo copia manualmente al campo "GPS correcto
(lat, lon)" de la plataforma como parte de su propio control de calidad, incluso
en casos ya `Validado ✓`. Solo queda en `None` cuando no se encontró el negocio en
Maps, o cuando la diferencia con `gps_actual` es menor a 1 metro (el mismo punto).

La búsqueda en Google Maps usa `business_name` (nombre editado); si ese campo
quedó vacío pero sí existe un `business_name_original` (nombre "precargado"),
se usa ese como respaldo — buscar con una cadena vacía nunca encuentra nada.

Si el resultado más cercano por nombre está a más de 2km (`max_trusted_distance_m`
en `build_case_status`) del `gps_actual`, el estado no es "Requiere corrección"
sino `❓ Coincidencia lejana (revisar manualmente)` — a esa distancia es mucho
más probable que sea un negocio distinto con nombre parecido en otra parte de
la ciudad que un error real de captura de GPS.

### Marcas, fotos y veredicto de calidad sugerido

Además de la validación GPS, `extract_case_data` también lee la Sección 5
(Estatus del negocio), la Sección 7 (Marcas de baterías registradas) y la
Sección 13 (qué fotos faltan, de las 6 requeridas: Fachada, Interior, Exhibidor,
Exhibidor 2, Negocio, Material POP). `validators.suggest_quality_verdict`
combina esas señales con el resultado de GPS para **sugerir** una Calidad
(`APROBADA` / `EN_RECUPERACION` / `CANCELADA`), un Tipo de encuesta y un texto
de `observaciones_calidad` (pensado para pegarse tal cual en el campo
OBSERVACIONES_CALIDAD de la plataforma) — nunca los aplica: son solo una
recomendación para que un humano decida y los capture manualmente en
`revisar.php`. Reglas, en orden:

1. Negocio "Cerrado definitivo" o "No aparece" → `CANCELADA` / `NEGADA`.
2. Error al extraer o validar el caso → `EN_RECUPERACION` / `INCIDENCIA`.
3. Ninguna foto cargada (0/6) → `EN_RECUPERACION` / `EN_RECUPERACION`.
4. Faltan algunas fotos, o el negocio no se encontró de forma confiable en Maps
   (no encontrado, o "coincidencia lejana" a más de 2km) →
   `EN_RECUPERACION` / `INCIDENCIA`.
5. En cualquier otro caso → `APROBADA` / `COMPLETA`.

### Verificación visual con Street View (sub-agente)

Cuando la búsqueda por texto en Google Maps no encuentra el negocio, o lo
encuentra sin coincidencia exacta de nombre, se puede pedir una segunda
verificación **visual**: un workflow guardado (`verificar-street-view`) que
lanza un sub-agente por caso para leer el rótulo real de la fachada y
compararlo contra el nombre registrado. Esto es un paso manual/asistido (no
corre solo dentro de `main.py`), pensado para invocarse cuando haya dudas
sobre un lote de casos.

**Nota técnica importante:** el visor 3D interactivo de Street View (el mapa
de `google.com/maps` con WebGL) no renderiza en el navegador de este entorno
(falla la creación de contexto WebGPU). El método que sí funciona:

1. Navegar a `https://www.google.com/maps?layer=c&cbll={lat},{lon}` — Google
   redirige al panorama más cercano a esas coordenadas.
2. Si la página muestra "No hay imágenes de Street View disponibles en este
   lugar", no hay cobertura ahí — parar.
3. Si no, leer la URL resultante y extraer el parámetro `panoid=...`.
4. Navegar directamente a imágenes estáticas del panorama (sin WebGL):
   `https://streetviewpixels-pa.googleapis.com/v1/thumbnail?cb_client=maps_sv.tactile&w=900&h=600&pitch=0&panoid=<PANOID>&yaw={0,90,180,270}`
   — cada una es una foto JPEG normal; se revisan las 4 para cubrir los 360°.
5. Comparar cualquier rótulo/letrero legible contra el nombre registrado
   (editado y original), tolerando diferencias de ortografía/mayúsculas.

Los resultados (`{case_id, street_view_available, visible_signage,
match_verdict, notes}`) se agregan al Excel existente con
`excel_generator.append_street_view_verdicts(ruta_excel, resultados)`, como
columna "Verificación Street View" — no se generan automáticamente, hay que
correr el workflow y pegar los resultados explícitamente.

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
Case ID 1777 (AUTOSERVICIO CALVA) y los Case ID 1778 a 1782 (2 validados, 3 con
negocio "Cerrado definitivo"). Detalles de los selectores exactos en los
docstrings de `browser_automation.py` y `google_maps_handler.py`; los bugs no
obvios encontrados durante esas verificaciones (contexto de navegador no
compartido, búsqueda "near" de Google Maps, `<p>` duplicado en la Sección 5
cuando el negocio está cerrado) están documentados en
[TROUBLESHOOTING.md](TROUBLESHOOTING.md).
