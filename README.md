# 🔋 Automatización GPS - Proyecto Baterías

> Herramienta de validación automática de coordenadas GPS en la plataforma de censo de baterías.

## 📌 Estado del Proyecto

**Fase:** MVP — verificado en vivo contra la plataforma real
**Última actualización:** 2026-09-04

✅ Flujo completo (login → listado → validación GPS vs. Google Maps → Excel)
probado contra Case ID 1777 (AUTOSERVICIO CALVA) y un lote de casos pendientes
reales. Ver el detalle en
[docs/OBSIDIAN_VAULT/Daily_Progress.md](docs/OBSIDIAN_VAULT/Daily_Progress.md) y
los bugs encontrados/corregidos durante la verificación en
[docs/TROUBLESHOOTING.md](docs/TROUBLESHOOTING.md).

---

## 🎯 ¿Qué hace?

1. Accede a `https://censobaterias.pricepointmonitor.com/`
2. Extrae casos pendientes de validación
3. Verifica coordenadas GPS en Google Maps (API de Places o scraping)
4. Identifica discrepancias y localiza ubicaciones correctas
5. Genera un Excel con validaciones y recomendaciones

---

## 🚀 Quick Start

```bash
git clone https://github.com/mannticora/automationGPS.git
cd automationGPS

python -m venv venv
source venv/bin/activate        # Windows: venv\Scripts\Activate.ps1

pip install -r scripts/requirements.txt
playwright install chromium

cp .env.example .env            # y completar CENSO_EMAIL / CENSO_PASSWORD
```

### Ejecutar

```bash
# Validar configuración sin conectarse a la plataforma
python scripts/main.py --dry-run

# Probar un único caso, con navegador visible
python scripts/main.py --mode=test --case-id=1777 --headless=false

# Validación completa (headless), máximo 10 casos
python scripts/main.py --mode=validate --limit=10

# Con logging detallado
python scripts/main.py --mode=validate --log-level=DEBUG

# Reporte con nombre personalizado
python scripts/main.py --output=mi_reporte_custom.xlsx
```

**Salida esperada:**
```
✓ Login exitoso.
✓ Validando Case ID 1777...
✓ Case ID 1777 -> Validado ✓
✓ Excel guardado: output/reporte_validaciones_20260904_143000.xlsx
```

Ver más ejemplos en [scripts/README.md](scripts/README.md).

---

## 📂 Estructura del Proyecto

```
automationGPS/
├── README.md
├── .env.example
├── .gitignore
├── docs/
│   ├── SETUP.md                 # Guía de instalación detallada
│   ├── FLUJO_TRABAJO.md         # Arquitectura interna del flujo
│   ├── TROUBLESHOOTING.md       # Problemas comunes y soluciones
│   └── OBSIDIAN_VAULT/
│       ├── Project_Overview.md
│       └── Daily_Progress.md
├── scripts/
│   ├── main.py                  # Punto de entrada / CLI
│   ├── validators.py            # Lógica de validación GPS
│   ├── browser_automation.py    # Playwright: login, listado, extracción
│   ├── google_maps_handler.py   # Verificación contra Google Maps
│   ├── excel_generator.py       # Generación de reportes
│   ├── utils.py                 # Reintentos, capturas, carpetas
│   ├── config.py                # Configuración desde .env
│   ├── logger_config.py         # Setup de loguru
│   ├── requirements.txt
│   └── README.md                # Ejemplos de uso de cada módulo
├── output/                      # Reportes generados (.xlsx, no versionado)
├── logs/                        # Logs de ejecución (no versionado)
└── tests/
    ├── conftest.py
    ├── test_validators.py
    └── test_data/
        └── sample_case_1777.json
```

---

## 🔐 Configuración de Credenciales

```bash
cp .env.example .env
```

```env
CENSO_EMAIL=tu_email@ejemplo.com
CENSO_PASSWORD=tu_password_aqui

# Opcional: usa la API de Google Places en vez de scraping
GOOGLE_MAPS_API_KEY=

HEADLESS_MODE=true
TIMEOUT_SEGUNDOS=60
MAX_REINTENTOS=3
```

⚠️ `.env` nunca se sube al repositorio (está en `.gitignore`). Nunca se
hardcodean credenciales en el código: todo se lee desde variables de entorno
vía `scripts/config.py`.

---

## 📊 Ejemplo de Output

Resultados reales de una corrida contra la plataforma (2026-09-04):

| Case ID | Negocio | GPS Actual | GPS Corregido | Estado | Distancia (m) | Notas |
|---------|---------|-----------|---------------|--------|--------------|-------|
| 1777 | Autoservicio calva | 19.3200134, -99.0798081 | 19.3200715, -99.0797028 | Validado ✓ | 12.8 | Coincide con 'AUTO SERVICIO CALVA' en Google Maps |
| 1778 | Acumuladores Rodriguez | 19.3194452, -99.0795619 | 19.319486, -99.0794311 | Validado ✓ | 14.5 | Sin coincidencia exacta de nombre; resultado más cercano |
| 1779 | *(sin nombre en la plataforma)* | 19.3587083, -99.1132417 | | ❌ No encontrado | | Google Maps no encontró resultados |

`GPS Corregido` se reporta siempre que Google Maps encuentre el negocio, incluso
en casos `Validado ✓` — el equipo la usa para actualizar manualmente el campo
"GPS correcto (lat, lon)" de la plataforma. La automatización nunca escribe en la
plataforma por sí sola.

---

## 🧪 Testing

```bash
python -m pytest tests/ -v
```

Los tests cubren `scripts/validators.py` (parseo de coordenadas, distancia
Haversine, decisión de estado) y corren sin navegador ni credenciales.

---

## 📚 Documentación Detallada

- **[docs/SETUP.md](docs/SETUP.md)** — Instalación paso a paso
- **[docs/FLUJO_TRABAJO.md](docs/FLUJO_TRABAJO.md)** — Cómo funciona internamente
- **[docs/TROUBLESHOOTING.md](docs/TROUBLESHOOTING.md)** — Errores comunes y el bloqueo actual de login
- **[docs/OBSIDIAN_VAULT/](docs/OBSIDIAN_VAULT/)** — Notas y avance diario del proyecto

---

## 📈 Roadmap

- ✅ Fase 1: Validación y reporte (MVP)
- 🔄 Fase 2: Actualización automática de coordenadas
- 🔄 Fase 3: Alertas + dashboard de monitoreo
- 🔄 Fase 4: Integraciones con otros sistemas

---

## 📄 Licencia

Uso interno — INMEGA.
