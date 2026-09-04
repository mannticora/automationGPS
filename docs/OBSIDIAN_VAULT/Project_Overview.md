# 🔋 Proyecto Automatización GPS - Baterías

## Información Base

- **Proyecto:** Validación automática de coordenadas GPS
- **Cliente:** INMEGA
- **Plataforma:** https://censobaterias.pricepointmonitor.com/
- **Estado:** 🟢 MVP — verificado en vivo contra la plataforma real y Google Maps
- **Fase actual:** Fase 1 — Validación y reporte (sin actualización de BD)

---

## 🎯 Objetivo

Automatizar la validación de coordenadas GPS de negocios en la plataforma de
censo de baterías, verificando que coincidan con su ubicación real en Google
Maps y generando un reporte de inconsistencias para corrección manual.

---

## 📋 Flujo Principal

```
1. Acceso a plataforma
   ↓
2. Extracción de casos pendientes
   ↓
3. Para cada caso:
   - Leer coordenadas GPS actuales
   - Verificar en Google Maps
   - Si no coincide → Buscar ubicación correcta
   ↓
4. Generar Excel con validaciones
   ↓
5. Logs + Reporte
```

---

## 🔑 Credenciales

Las credenciales del usuario de automatización **no se documentan aquí ni en
ningún archivo del repositorio**. Se configuran localmente en `.env` (plantilla
en `.env.example`, nunca versionado — ver `.gitignore`).

---

## 🗂️ Estructura de Carpetas

```
automationGPS/
├── scripts/
│   ├── main.py                 # Orquestador principal
│   ├── validators.py           # Lógica de validación
│   ├── browser_automation.py   # Control del navegador
│   ├── google_maps_handler.py  # Integración Maps
│   ├── excel_generator.py      # Generación de reportes
│   ├── config.py                # Configuración desde .env
│   ├── logger_config.py         # Setup de logs
│   └── utils.py                  # Funciones comunes
├── docs/
│   └── OBSIDIAN_VAULT/
├── tests/
├── output/
└── logs/
```

---

## 🧪 Caso de Prueba Base

**Case ID:** 1777
**Negocio:** Autoservicio calva
**Estado:** ✅ Validado en vivo — GPS actual (19.3200134, -99.0798081) coincide con
'AUTO SERVICIO CALVA' en Google Maps a ~12.8m. Detalle en
[Daily_Progress.md](Daily_Progress.md) del 2026-09-04. La fixture
`tests/test_data/sample_case_1777.json` usa estos datos reales.

---

## 🛠️ Stack Tecnológico

| Componente | Tecnología | Razón |
|-----------|-----------|-------|
| Automatización | Playwright | Rápido, moderno, sin dependencias externas |
| Lenguaje | Python 3.9+ | Ecosistema de datos + RPA consolidado |
| Reports | openpyxl | Generación de Excel sin dependencias |
| Logs | loguru | Simple, rotación automática, legible |
| Config | python-dotenv | Credenciales fuera del código |
| Docs | Markdown + Obsidian | Versionable, legible, integrable con GitHub |
| Versionamiento | Git + GitHub | Control de cambios, colaboración |

---

## 🔄 Próximas Fases

- **Fase 2:** Actualización automática de GPS en la plataforma
- **Fase 3:** Alertas + dashboard de monitoreo
- **Fase 4:** Integraciones con otros sistemas

---

## 🔗 Enlaces Útiles

- [Repositorio GitHub](https://github.com/mannticora/automationGPS)
- [Plataforma](https://censobaterias.pricepointmonitor.com/)
- [Documentación Playwright](https://playwright.dev/)

---

**Última revisión:** 2026-09-04
