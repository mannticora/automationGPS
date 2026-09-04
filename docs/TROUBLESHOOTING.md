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
