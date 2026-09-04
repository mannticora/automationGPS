# 🔧 TROUBLESHOOTING — Problemas Comunes

## ✅ Resuelto (2026-09-04): bloqueo de login

El bloqueo inicial de login (credenciales rechazadas) se resolvió tras actualizar
la contraseña del usuario de automatización. Con `ai.automation01@inmega.com` y la
contraseña vigente, el flujo completo fue verificado en vivo contra Case ID 1777
(AUTOSERVICIO CALVA) y contra un lote de 3 casos pendientes reales:
login → listado → extracción → validación en Google Maps → Excel. Ver el detalle
en [docs/OBSIDIAN_VAULT/Daily_Progress.md](OBSIDIAN_VAULT/Daily_Progress.md).

Durante esa verificación se encontraron y corrigieron dos bugs reales (no
hipotéticos) que vale la pena conocer si vuelves a tocar este código:

1. **`browser.new_page()` no comparte sesión.** `Browser.new_page()` en Playwright
   crea un `BrowserContext` nuevo (sin cookies) por cada llamada. El login se hacía
   en un contexto y `extract_case_data` abría el detalle en otro, así que la
   plataforma redirigía a `/login`. Solución: un único `BrowserContext` compartido
   (`self.context`), con `self.context.new_page()` para cualquier página nueva.
2. **Google Maps con `+near+lat,lon` no funciona.** Google trata "near" como texto
   literal; cuando no encuentra nada, muestra una vista de mapa genérica que igual
   contiene un patrón `@lat,lon,zoom` en la URL — leerlo a ciegas producía
   "encontrados" falsos a decenas de km de distancia. Solución: usar
   `.../search/{negocio}/@{lat},{lon},16z` (centra el mapa ahí) y leer las
   coordenadas exactas embebidas en el `href` de cada resultado
   (`a[href*="/maps/place/"]`, patrón `!3d{lat}!4d{lon}`), no en la URL de la página.

---

## ✅ Resuelto (2026-09-04): `strict mode violation` al extraer Estatus del negocio

Al validar los Case ID 1779, 1781 y 1782 (negocios con "Cerrado definitivo" en
el listado), `extract_case_data` fallaba con:

```
Error: strict mode violation: locator("//h2[...]/following-sibling::p")
resolved to 2 elements
```

**Causa:** cuando el negocio NO está "Operando", la plataforma agrega un
`<p class="tag-alerta">⚠ El negocio no está "Operando"...</p>` como un segundo
`<p>` hermano dentro de la misma sección — el XPath sin índice devolvía ambos
párrafos y Playwright rechaza `text_content()` sobre un locator con más de un
elemento.

**Solución:** se agregó `[1]` al XPath (`following-sibling::p[1]`) tanto en
`_labeled_value` (usado para "Geo Location") como en `_extract_business_status`,
para tomar siempre solo el primer `<p>` — que es el valor real del campo.

---

## ✅ Resuelto (2026-09-04): nombre editable vacío impedía buscar en Google Maps

Para Case ID 1779, 1781 y 1782 el campo editable `#nomneg` (Sección 10) estaba
vacío, así que `validate_case` buscaba en Google Maps con una cadena vacía y
siempre reportaba "No encontrado" — aunque sí existía un nombre "precargado"
(capturado en campo originalmente) para esos casos.

**Solución:** se agregó `business_name_original` (lee "NEG_NOMBRE_NEGOCIO
(precargado)") y `validate_case` ahora usa `business_name or
business_name_original` como término de búsqueda. Nueva columna "Nombre
Negocio (Original)" en el Excel para poder comparar ambos.

## ✅ Resuelto (2026-09-04): "correcciones" de GPS a varios kilómetros de distancia

Al usar el nombre original como respaldo (fix anterior), algunos casos
empezaron a "encontrar" un resultado en Google Maps a **más de 1km o incluso
15km** de las coordenadas registradas — casi seguro un negocio distinto con
nombre parecido en otra parte de la ciudad, no un error real de GPS.

**Solución:** `build_case_status` ahora recibe `max_trusted_distance_m`
(por defecto 2000m). Si la distancia al resultado más cercano supera ese
límite, el estado es `❓ Coincidencia lejana (revisar manualmente)` en vez de
`⚠️ Requiere corrección`, y `suggest_quality_verdict` lo trata igual que "no
encontrado" (no sugiere `APROBADA` con una coincidencia tan lejana).

## ⚠️ Conocido, no corregible desde el código: caracteres acentuados corrompidos ("?")

Algunos campos de texto de la plataforma (nombres de negocio, direcciones,
giros) contienen literalmente el carácter `?` donde debería haber una vocal
acentuada o "Ñ" — ej. `"?NGELES BIKERS"` en vez de `"ÁNGELES BIKERS"`,
`"PE??SCOLA 32"` en vez de `"PEÑÍSCOLA 32"`, `"TALLER MEC?NICO"` en vez de
`"TALLER MECÁNICO"`. Se confirmó que esto **ya viene así en el HTML que sirve
la plataforma** (se ve igual en `get_page_text` de una página fresca, no es un
problema de decodificación en Python/Playwright) — parece un problema de
codificación en el origen de los datos de la plataforma (posible
Windows-1252 ↔ UTF-8 mal manejado en algún punto de su backend).

**Impacto:** rompe la búsqueda en Google Maps para esos casos (el `?` literal
no coincide con nada). No hay una forma confiable de adivinar el carácter
correcto desde el código — si es importante, hay que corregirlo manualmente
en la plataforma o reportarlo a quien la mantiene.

---

## 🔍 Verificación visual con Street View (sub-agente) — cuándo usarla y limitaciones

Para casos donde Google Maps no encuentra el negocio, o lo encuentra sin
coincidencia exacta de nombre, existe un workflow guardado
(`verificar-street-view`, ver `docs/FLUJO_TRABAJO.md`) que usa un sub-agente
por caso para leer visualmente el rótulo de la fachada. Cosas a tener en
cuenta:

- **El visor 3D de Street View no renderiza en este entorno** (falla el
  contexto WebGPU — pantalla negra). El workflow usa en su lugar imágenes
  estáticas del panorama (`streetviewpixels-pa.googleapis.com/.../thumbnail`),
  que sí funcionan.
- **No toda ubicación tiene cobertura real de Street View.** Cuando no la hay,
  Google puede redirigir a una fotoesfera interior de un negocio cercano no
  relacionado, o a un panorama real pero de una calle a más de 1km de
  distancia — hay que verificar que las coordenadas del panorama resuelto
  coincidan razonablemente con las del caso antes de confiar en lo que se ve.
- Si el nombre registrado (editado y original) está vacío, el sub-agente no
  tiene con qué comparar el rótulo — en ese caso solo puede describir lo que
  ve, no calificar coincidencia/no coincidencia.

---

## Error: "Login falló: Correo o contraseña incorrectos"

**Causa:** credenciales inválidas en `.env`, o la contraseña fue rotada.

**Solución:**
1. Verificar `CENSO_EMAIL` y `CENSO_PASSWORD` en `.env` (sin espacios extra).
2. Probar el login manualmente en el navegador con esas mismas credenciales.
3. Si sigue fallando, solicitar credenciales actualizadas — **no reintentar login
   repetidamente de forma automática**, para evitar bloqueos de la cuenta por
   demasiados intentos fallidos.

---

## Error: `ModuleNotFoundError: No module named 'playwright'` (u otro paquete)

**Solución:**
```bash
pip install -r scripts/requirements.txt
```

## Error: `Executable doesn't exist ... chromium` (Playwright)

**Solución:** Playwright necesita descargar el binario del navegador la primera vez:
```bash
playwright install chromium
```

## Error: `ValueError: Faltan variables de entorno requeridas: CENSO_EMAIL, CENSO_PASSWORD`

**Causa:** no existe `.env`, o le faltan las credenciales.

**Solución:**
```bash
cp .env.example .env
# Editar .env y completar CENSO_EMAIL / CENSO_PASSWORD
```

## Error al instalar Playwright: `Microsoft Visual C++ 14.0 or greater is required` (greenlet)

**Causa:** `playwright==1.47.0` (u otra versión antigua) no tiene wheel
precompilado para tu versión de Python (p. ej. Python 3.13 en Windows) y `pip`
intenta compilar `greenlet` desde código fuente.

**Solución:** instalar sin fijar versión exacta (`pip install --upgrade playwright`,
`requirements.txt` ya usa `playwright>=1.47.0`), o instalar
[Microsoft C++ Build Tools](https://visualstudio.microsoft.com/visual-cpp-build-tools/)
si necesitas una versión específica.

## Los selectores de listado/detalle no encuentran nada (`0 casos encontrados`)

**Causa probable:** la plataforma cambió su HTML desde la última verificación
(2026-09-04) — ver la nota de estado al inicio de este documento y los
comentarios al inicio de `scripts/browser_automation.py`.

**Solución:**
1. Correr con `--headless=false --log-level=DEBUG` para observar el navegador.
2. Inspeccionar el HTML real de la tabla de casos y del formulario de detalle.
3. Ajustar los selectores en `scripts/browser_automation.py`.
4. Si `SCREENSHOT_ON_ERROR=true`, revisar `logs/screenshots/` — cada error de
   extracción guarda una captura con el Case ID en el nombre del archivo.

## El reporte Excel sale vacío

**Causa:** no se procesó ningún caso (login falló, no hay casos con el estado de
`FILTRO_ESTADO`, o `--case-id` no existe en el listado).

**Solución:** revisar `logs/automation.log` de la corrida — cada caso registra su
resultado (`Case ID X -> <estado>`), y los errores de login/extracción quedan
registrados con nivel `ERROR`.

## Google Maps no encuentra el negocio (`found: false`)

**Causa:** nombre del negocio con errores tipográficos en la plataforma, negocio
sin presencia en Google Maps, o el radio de búsqueda (`GOOGLE_MAPS_SEARCH_RADIUS`)
es muy pequeño.

**Solución:** aumentar `GOOGLE_MAPS_SEARCH_RADIUS` en `.env`, o revisar manualmente
el `maps_link` generado en el Excel (columna "Enlace Google Maps").
