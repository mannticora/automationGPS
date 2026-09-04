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
