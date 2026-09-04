# 🚀 SETUP — Guía de Instalación

## Requisitos Previos

- **Sistema Operativo:** Windows 10+, macOS 10.15+, o Linux (Ubuntu 20.04+)
- **Python:** 3.9 o superior
- **Git:** Instalado y configurado
- **RAM:** Mínimo 4GB
- **Conexión:** Internet estable (Playwright descarga Chromium en el setup)

---

## Paso 1: Clonar el Repositorio

```bash
git clone https://github.com/mannticora/automationGPS.git
cd automationGPS
```

---

## Paso 2: Crear Ambiente Virtual

```bash
# Linux / macOS
python3 -m venv venv
source venv/bin/activate

# Windows (PowerShell)
python -m venv venv
venv\Scripts\Activate.ps1
```

**Verificar que esté activo:**
```
(venv) $ python --version
```

---

## Paso 3: Instalar Dependencias

```bash
pip install --upgrade pip
pip install -r scripts/requirements.txt
```

**Dependencias principales:**
- `playwright` — Automatización del navegador
- `openpyxl` — Generación de Excel
- `python-dotenv` — Manejo de variables de entorno
- `requests` — Cliente HTTP (usado si se configura Google Places API)
- `loguru` — Sistema de logging
- `pytest` — Tests unitarios

---

## Paso 4: Configurar Credenciales

```bash
cp .env.example .env
```

Editar `.env` y completar, como mínimo:
```env
CENSO_EMAIL=tu_email@ejemplo.com
CENSO_PASSWORD=tu_password_aqui
```

⚠️ **`.env` nunca se sube al repositorio** (está en `.gitignore`). Ver
[docs/TROUBLESHOOTING.md](TROUBLESHOOTING.md) si el login falla con "Correo o
contraseña incorrectos".

---

## Paso 5: Descargar el Navegador (Playwright)

```bash
playwright install chromium
```

Esto toma ~500MB y 2-5 minutos la primera vez.

---

## Paso 6: Verificar Instalación

```bash
python -c "import playwright, openpyxl, dotenv, loguru; print('Dependencias OK')"
python scripts/main.py --dry-run
```

`--dry-run` valida la configuración de `.env` sin conectarse a la plataforma.

---

## Paso 7: Correr los Tests Unitarios

```bash
python -m pytest tests/ -v
```

Estos tests cubren `scripts/validators.py` (parseo de coordenadas, distancias,
estado de validación) y no requieren navegador ni credenciales.

---

## Paso 8: Primer Test Real (requiere credenciales válidas)

```bash
python scripts/main.py --mode=test --case-id=1777 --headless=false
```

Si el login falla, revisar [docs/TROUBLESHOOTING.md](TROUBLESHOOTING.md).

---

## 📁 Estructura Post-Setup

```
automationGPS/
├── venv/                  # Ambiente virtual
├── scripts/                # Código fuente
├── .env                     # Credenciales locales (NO versionado)
├── .env.example            # Plantilla de credenciales
├── output/                  # Reportes generados
├── logs/                    # Logs de ejecución
└── tests/                   # Tests unitarios
```

---

## 🎯 Checklist Final

- [ ] Python 3.9+ instalado
- [ ] Ambiente virtual activo
- [ ] `pip list` muestra `playwright`, `openpyxl`, `loguru`, etc.
- [ ] `.env` existe con credenciales propias
- [ ] `playwright install chromium` completó sin errores
- [ ] `python scripts/main.py --dry-run` no lanza errores
- [ ] `python -m pytest tests/ -v` pasa en verde

---

**Actualizado:** 2026-09-04
