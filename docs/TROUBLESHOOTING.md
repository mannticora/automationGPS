# 🔧 TROUBLESHOOTING — Problemas Comunes

## ⚠️ Estado actual (2026-09-04): Login rechazado por la plataforma

Durante el desarrollo inicial, **las credenciales disponibles para el usuario de
automatización fueron rechazadas** por `https://censobaterias.pricepointmonitor.com/`
con el mensaje `Correo o contraseña incorrectos.`, en dos combinaciones distintas
probadas manualmente contra la página real.

**Impacto:** no fue posible verificar en vivo los selectores del listado de casos
pendientes ni del detalle de un caso (Sección 1 "Geo Location", Sección 10 "Datos
del negocio"). El código en `scripts/browser_automation.py` implementa esos pasos
usando los selectores descritos en la especificación original
(`table tbody tr`, `[data-section='1']`, `[data-section='10']`), pero **no están
verificados contra el DOM real** — sí lo está el formulario de login.

**Antes de correr `--mode=validate` o `--mode=test` contra la plataforma real:**
1. Confirmar con el equipo/administrador de la plataforma que el usuario de
   automatización tiene credenciales válidas y permisos de lectura.
2. Correr un test manual: `python scripts/main.py --mode=test --case-id=1777 --headless=false`
   y observar visualmente si el login funciona.
3. Si el login funciona pero la extracción de datos falla, inspeccionar el DOM real
   del listado y del detalle de un caso (clic derecho → Inspeccionar) y ajustar los
   selectores en `browser_automation.py::get_pending_cases`,
   `browser_automation.py::find_case_by_id` y `browser_automation.py::extract_case_data`.

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

## Los selectores de listado/detalle no encuentran nada (`0 casos encontrados`)

**Causa probable:** la plataforma cambió su HTML, o los selectores del prompt
original no coinciden con el DOM real (ver aviso arriba).

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
