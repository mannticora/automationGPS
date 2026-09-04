# 📅 Daily Progress

## 2026-09-04

**Hecho:**
- Definida la especificación completa del flujo (login → listado de pendientes →
  validación GPS por caso vs. Google Maps → reporte Excel).
- Implementado el proyecto completo en `scripts/`: `config.py`, `logger_config.py`,
  `utils.py`, `browser_automation.py`, `google_maps_handler.py`, `validators.py`,
  `excel_generator.py`, `main.py`.
- Verificado en vivo el formulario de login de
  `https://censobaterias.pricepointmonitor.com/` (selectores `input[name='email']`,
  `input[name='password']`, `form.login-form button[type='submit']`, banner de
  error `.alert-error`) y confirmados en el código.
- Tests unitarios de `validators.py` (21 tests, parseo de coordenadas, distancia
  Haversine, decisión de estado) — todos en verde.
- Generación de Excel probada manualmente con datos de ejemplo — formato, colores
  por estado e hipervínculo a Google Maps funcionan correctamente.
- Documentación (`README.md`, `docs/SETUP.md`, `docs/FLUJO_TRABAJO.md`,
  `docs/TROUBLESHOOTING.md`) y estructura lista para subir a GitHub.

**Bloqueo encontrado:**
- El login contra la plataforma real fue rechazado (`Correo o contraseña
  incorrectos.`) con dos combinaciones de credenciales distintas probadas durante
  el desarrollo. Como consecuencia:
  - No se pudo verificar en vivo el Case ID 1777 (AUTOSERVICIO CALVA).
  - Los selectores del listado de casos y del detalle de un caso
    (`get_pending_cases`, `find_case_by_id`, `extract_case_data`) quedaron
    implementados según la especificación original, **sin verificar contra el
    DOM real**.
  - La fixture `tests/test_data/sample_case_1777.json` usa coordenadas de
    EJEMPLO, no datos reales extraídos de la plataforma.
- Decisión: pausar la validación en vivo, dejar el bloqueo documentado aquí y en
  `docs/TROUBLESHOOTING.md`, y publicar el proyecto (código + documentación) en
  GitHub para compartirlo con el equipo mientras se resuelve el acceso.

**Próximos pasos (completados más tarde el mismo día, ver entrada siguiente):**
1. ~~Conseguir credenciales válidas para el usuario de automatización.~~
2. ~~Correr `python scripts/main.py --mode=test --case-id=1777 --headless=false`
   y confirmar visualmente el login.~~
3. ~~Ajustar los selectores de listado/detalle en `browser_automation.py` según el
   DOM real si no coinciden con lo documentado.~~
4. ~~Reemplazar la fixture de ejemplo por los datos reales del Case ID 1777 una vez
   verificados.~~
5. ~~Correr una validación completa (`--mode=validate --limit=10`) y revisar el
   Excel generado.~~

---

## 2026-09-04 (continuación) — Login resuelto, verificación en vivo completa

**Hecho:**
- Confirmado el email correcto: `ai.automation01@inmega.com` (visible en el campo
  AUDITOR del propio formulario de revisión una vez logueados). La contraseña fue
  actualizada por el equipo de la plataforma.
- Login verificado en vivo, tanto por navegador interactivo como por
  `scripts/main.py` con Playwright.
- **Case ID 1777 (Autoservicio calva) extraído y validado end-to-end:**
  GPS actual `19.3200134,-99.0798081` → coincide con "AUTO SERVICIO CALVA" en
  Google Maps a **~12.8 m** → `Validado ✓`. Fixture de test actualizada con estos
  datos reales.
- Corrida adicional de `--mode=validate --limit=3` contra 3 casos pendientes
  reales (1777, 1778, 1779) — los tres con resultados sensatos, incluyendo el
  caso límite de un negocio sin nombre capturado (1779 → `❌ No encontrado`,
  correcto: no hay nombre que buscar).
- **Dos bugs reales encontrados y corregidos** durante esta verificación (detalle
  en `docs/TROUBLESHOOTING.md`):
  1. `browser.new_page()` creaba un `BrowserContext` nuevo sin cookies de sesión
     por cada página → el detalle de caso se abría deslogueado. Corregido
     reutilizando un único `BrowserContext`.
  2. La búsqueda `+near+lat,lon` en Google Maps no funciona (Google la trata como
     texto literal) y su página de "no encontrado" igual contiene un patrón
     `@lat,lon,zoom` en la URL — producía correcciones falsas a >20km de
     distancia. Corregido usando `.../search/{negocio}/@{lat},{lon},16z` y
     leyendo las coordenadas exactas del `href` de cada resultado
     (`!3d{lat}!4d{lon}`), con selección del resultado por coincidencia de
     nombre cuando es posible.
  3. (Menor) `google_maps_handler.GoogleMapsHandler` no heredaba el override
     `--headless` pasado a `main.py`; ahora se propaga correctamente.
  4. (Menor) `excel_generator`/`validators`: la columna "GPS Corregido" se
     rellenaba incluso en casos `Validado ✓`; ahora solo se muestra cuando el
     caso realmente requiere corrección.
- Instalado Playwright + Chromium en el entorno de desarrollo (el pin
  `playwright==1.47.0` no tenía wheel para Python 3.13 en Windows; se relajó a
  `playwright>=1.47.0` en `requirements.txt`).
- Suite de tests ampliada a 26 tests (se agregó cobertura de
  `validators.validate_case` con dobles de prueba) — todos en verde.
- Documentación (README, FLUJO_TRABAJO, TROUBLESHOOTING, Project_Overview) y
  código actualizados y subidos a GitHub.

**Próximos pasos:**
1. Ejecutar una validación completa sin `--limit` (los 6 casos pendientes reales)
   y revisar el Excel resultante con el equipo.
2. Evaluar si vale la pena mejorar el matching de nombre en
   `_pick_best_candidate` (p. ej. tolerancia a acentos/typos) dado el caso 1778,
   donde el resultado más cercano no coincidió de nombre exacto.
3. Fase 2: actualización automática del campo "GPS correcto" (`#gps_correcto`) en
   la plataforma para los casos que requieran corrección.

---

## 2026-09-04 (continuación) — Corrección de criterio: "GPS Corregido" siempre visible

**Contexto:** el usuario replicó el proceso a mano en Case ID 1777 — entró a
Google Maps con la coordenada de "Geo Location", vio que el pin no caía sobre el
negocio, encontró "AUTOSERVICIO CALVA" cerca, y copió las coordenadas del pin del
negocio para pegarlas en el campo "GPS correcto (lat, lon)" de la plataforma
(manualmente, sin automatizar esa escritura).

Esto reveló que el criterio que se había fijado más temprano hoy ("no mostrar
GPS Corregido si el caso ya está Validado ✓ dentro de tolerancia") no encaja con
el flujo real de trabajo: el equipo quiere ver **siempre** la coordenada que
Google Maps confirma para el negocio — la misma que copiarían a mano — sin
importar si la diferencia es pequeña. Se revirtió ese criterio:
`validators.validate_case` ahora reporta `gps_corregido` en cuanto
`google_maps_handler` encuentra el negocio, independientemente del `status`
(solo se omite si no se encontró el negocio, o si la diferencia es <1m).

También se acordó con el usuario que las notas de este proyecto en
`docs/OBSIDIAN_VAULT/` se sincronizan automáticamente (sin que lo pida cada vez)
a su vault real de Obsidian, en
`...\OneDrive - Inmega Investigacion De Mercados S.C\07_2026\Documentos\Obsidian Vault\Proyecto GPS Baterias\`.

**Recordatorio:** la automatización sigue sin escribir nada en la plataforma —
solo lee y reporta. La actualización del campo "GPS correcto" en
`revisar.php?id=...` la hace el equipo manualmente con el dato del Excel.

---

## 2026-09-04 (continuación) — Revisión manual de calidad, Case ID 1777

Revisión manual (no automatizada) de las secciones 7 (Marcas de baterías) y 13
(Fotos) del Case ID 1777, a pedido del usuario. Detalle completo en
[[Revision_Case_1777]]. Resumen:

- 4 marcas registradas (FULL POWER, GONHER, GONHER PRIME, LTH), sin
  inconsistencias entre lo capturado y "Marca correcta".
- **Sin ninguna fotografía cargada** en las 6 secciones de fotos (Fachada,
  Interior, Exhibidor, Exhibidor 2, Negocio, Material POP) — no hay evidencia
  visual que respalde las marcas capturadas.
- Folio "CL - 960509" duplicado con Case ID 1125 — señal a revisar.
- Recomendación de veredicto: **Calidad = EN_RECUPERACION**, **Tipo de encuesta
  = EN_RECUPERACION** (por falta total de fotos), pendiente de que el equipo lo
  confirme y lo capture manualmente en la plataforma — no se modificó nada en
  `revisar.php?id=70112`.

---

## 2026-09-04 (continuación) — Marcas/fotos/veredicto ahora en el Excel automatizado

El usuario pidió que la revisión manual anterior (marcas, fotos, veredicto de
calidad) se automatizara y se sumara al mismo Excel de GPS, en vez de quedar
solo en una nota aparte. Se implementó:

- `browser_automation.CensoBateriasClient.extract_case_data` ahora también lee,
  en la misma visita a la página de detalle: Sección 5 (Estatus del negocio,
  `<p>` tras el `<h2>`), Sección 7 (marcas registradas, filas `<td>` de la tabla
  bajo `<h2>7. Marcas de baterías</h2>`) y Sección 13 (fotos faltantes, vía
  `.foto-card[data-campo=...]` — tiene foto si contiene `<img>`, falta si
  contiene `.foto-vacia`).
- `validators.suggest_quality_verdict(gps_status, business_status,
  missing_photos, total_photo_fields) -> (calidad, tipo_encuesta)`: función pura
  que sugiere el veredicto (nunca lo aplica en la plataforma). Reglas en
  `docs/FLUJO_TRABAJO.md`.
- `excel_generator.py`: 5 columnas nuevas — Estatus Negocio, Marcas Registradas,
  Fotos Faltantes, Calidad Sugerida, Tipo Encuesta Sugerido.
- Verificado en vivo contra Case ID 1777: el Excel generado coincide
  exactamente con la revisión manual de antes (4 marcas, 6/6 fotos faltantes,
  Calidad Sugerida = Tipo Encuesta Sugerido = EN_RECUPERACION).
- Suite de tests ampliada a 33 (7 tests nuevos para `suggest_quality_verdict`).
- Recordatorio: sigue sin escribirse nada en la plataforma; el equipo captura
  el veredicto manualmente si está de acuerdo con la sugerencia.

---

## 2026-09-04 (continuación) — Observaciones + validación de Case ID 1778 a 1782

Se agregó `observaciones_calidad` (texto explicando el porqué del veredicto,
pensado para pegarse en OBSERVACIONES_CALIDAD) a `suggest_quality_verdict`
(ahora devuelve una 3-tupla), como nueva columna "Observaciones" en el Excel.
También se agregó `--case-ids` a `main.py` (acepta rangos y listas, ej.
`1778-1782` o `1778,1780,1782`, vía la nueva `utils.parse_case_ids`) para poder
validar un conjunto específico de casos sin depender del listado de pendientes.

**Bug encontrado y corregido:** al validar Case ID 1779, 1781 y 1782 (negocios
"Cerrado definitivo"), `extract_case_data` fallaba con
`strict mode violation` — la plataforma agrega un `<p class="tag-alerta">` de
advertencia adicional en la Sección 5 cuando el negocio no está "Operando", y
el XPath sin índice capturaba ambos `<p>`. Corregido con `following-sibling::p[1]`
en `_labeled_value` y `_extract_business_status`. Detalle en
`docs/TROUBLESHOOTING.md`.

**Resultado de Case ID 1778 a 1782 (verificado en vivo, con el fix aplicado):**

| Case ID | Negocio | Estado GPS | Calidad Sugerida | Tipo Encuesta |
|---|---|---|---|---|
| 1778 | Acumuladores Rodriguez | Validado ✓ (14.5m) | EN_RECUPERACION | EN_RECUPERACION |
| 1779 | *(sin nombre, negocio cerrado)* | ❌ No encontrado | CANCELADA | NEGADA |
| 1780 | Baterias hersa | Validado ✓ (5m) | EN_RECUPERACION | EN_RECUPERACION |
| 1781 | *(sin nombre, negocio cerrado)* | ❌ No encontrado | CANCELADA | NEGADA |
| 1782 | *(sin nombre, negocio cerrado)* | ❌ No encontrado | CANCELADA | NEGADA |

Los 5 casos coinciden con lo que ya se sabía del listado (1779/1781/1782
figuraban como "Cerrado definitivo" y sin nombre de negocio capturado). 1778 y
1780 sí están operando, pero igual quedan `EN_RECUPERACION` por no tener
ninguna de las 6 fotos requeridas.

**Pendiente:** el usuario va a dar retroalimentación sobre las sugerencias de
Calidad/Tipo de encuesta de estos 5 casos antes de que el equipo las capture en
la plataforma. Suite ampliada a 41 tests.

---

## 2026-09-04 (continuación) — Nombre original, distancias absurdas, y sub-agente de Street View

El usuario revisó manualmente el Case ID 1780 en Google Maps/Street View: el
rótulo real dice "Venta de baterías HERSA", mientras la plataforma lo capturó
como "BATERIAS ERSA" (le falta la H) en el campo original y "Baterias hersa"
en el campo editado. Pidió (1) mostrar el nombre original en el Excel, y (2)
crear una skill/sub-agente para revisar visualmente (Street View) los casos
donde la búsqueda por texto en Google Maps no confirma el negocio.

**Cambios de código:**

1. `extract_case_data` ahora también lee "NEG_NOMBRE_NEGOCIO (precargado)"
   (el nombre tal como se capturó en campo) como `business_name_original`,
   nueva columna "Nombre Negocio (Original)" en el Excel.
2. **Bug real encontrado:** para Case ID 1779/1781/1782 el campo editable
   (`nomneg`) estaba vacío, pero el original SÍ tenía nombre ("ACUMULADORES
   OCOTE", "REFACCIONARIA VELÁZQUEZ", "ÁNGELES BIKERS") — `validate_case`
   buscaba en Google Maps con el nombre editado (vacío) en vez de usar el
   original como respaldo. Corregido: `search_name = business_name or
   business_name_original`.
3. **Otro bug real:** con el fix anterior, 1779 y 1781 empezaron a "encontrar"
   resultados en Maps a **1.2km y 15.7km** de distancia — casi seguro negocios
   distintos con nombre parecido en otra parte de la ciudad, no una corrección
   real de GPS. Se agregó `DISTANT_MATCH_STATUS` ("❓ Coincidencia lejana"):
   si el resultado más cercano está a más de 2km (`max_trusted_distance_m`),
   ya no se marca como "Requiere corrección" sino aparte, y
   `suggest_quality_verdict` lo trata igual que "no encontrado".
4. **Hallazgo de datos (no corregible desde el código):** varios campos de
   texto de la plataforma tienen caracteres acentuados corrompidos como "?"
   (ej. "?NGELES BIKERS" en vez de "ÁNGELES BIKERS", visto también antes en
   "PE??SCOLA" y "MEC?NICO") — parece ser un problema de codificación en el
   origen de los datos de la plataforma, no de la extracción. Esto rompe la
   búsqueda en Maps para esos casos (1782 sigue sin encontrarse). Documentado
   en TROUBLESHOOTING.md.

**Sub-agente de verificación por Street View (el "skill" pedido):** se creó y
guardó el workflow `verificar-street-view` — dado un lote de casos
(case_id, nombre editado, nombre original, lat, lon), lanza un sub-agente por
caso que usa el navegador para comparar el rótulo real de la fachada contra el
nombre registrado. Detalle técnico importante: el visor 3D interactivo de
Street View NO renderiza en este entorno (falla el contexto WebGPU) — se usa
en su lugar el método de imágenes estáticas
(`streetviewpixels-pa.googleapis.com/v1/thumbnail?...&panoid=...&yaw=...`),
obtenido siguiendo `maps.google.com/maps?layer=c&cbll=lat,lon` y extrayendo el
`panoid` de la URL resultante — confiable y no requiere WebGL.

Resultados de la primera corrida (Case ID 1778, 1779, 1781, 1782):

| Case ID | Street View | Veredicto | Nota |
|---|---|---|---|
| 1778 | Disponible | ✓ Coincide | Rótulo "ACUMULADORES RODRIGUEZ" confirmado visualmente |
| 1779 | No disponible | — | Google confirma "no hay imágenes de Street View" en el punto exacto |
| 1781 | Resolvió a un panorama ~1.5km lejos | Indeterminado | Sin nombre registrado con qué comparar, y probable falta de cobertura real en el punto exacto |
| 1782 | No disponible | — | Google confirma "no hay imágenes de Street View" |

La falta de cobertura real de Street View en 1779/1781/1782 es consistente con
que sean negocios "Cerrado definitivo" en zonas con poca cobertura — refuerza
(sin poder confirmar al 100%) el veredicto CANCELADA ya sugerido por el
estatus del negocio. `excel_generator.append_street_view_verdicts()` agrega
estos hallazgos como columna "Verificación Street View" al Excel existente
(post-proceso, no parte del pipeline automático sin supervisión).

Suite ampliada a 47 tests (nuevo fallback de nombre, nuevo estado de distancia
lejana). Reporte final: `output/reporte_1778_1782_final.xlsx`.
