# 🔍 Revisión manual — Case ID 1777 (Autoservicio calva)

**Fecha de revisión:** 2026-09-04
**URL:** https://censobaterias.pricepointmonitor.com/revisar.php?id=70112

---

## 7. Marcas de baterías

4 marcas registradas. Ninguna marcada como clonada; todas con el mismo proveedor
capturado ("Zaragoza"); el campo "Marca correcta" coincide en las 4 con la marca
capturada (sin discrepancia señalada por el encuestador):

| Marca | ¿Clonada? (OBCLON) | Proveedor (PROVMAR) | Inventario (INVBAT) | Vendidas 30d (BATVEN) | Marca correcta |
|---|---|---|---|---|---|
| FULL POWER | No | Zaragoza | 10 | 20 | FULL POWER ✓ |
| GONHER | No | Zaragoza | 10 | 5 | GONHER ✓ |
| GONHER PRIME | No | Zaragoza | 5 | 1 | GONHER PRIME ✓ |
| LTH | No | Zaragoza | 15 | 10 | LTH ✓ |

---

## 13. Fotos

**Ninguna de las 6 fotos tiene imagen cargada** — los 6 campos muestran
"(sin foto)" y se confirmó en el DOM que no hay ningún `<img>` en la sección:

| Campo | Estado |
|---|---|
| Fachada (FOTO_FACHADA) | Sin foto |
| Interior (FOTO_INTERIOR) | Sin foto |
| Exhibidor (FOTO_EXHIBIDOR) | Sin foto |
| Exhibidor 2 (FOTO_EXHIBIDOR_2) | Sin foto |
| Negocio (FOTO_NEGOCIO) | Sin foto |
| Material POP (MATERIAL_POP) | Sin foto |

No hay fotos que analizar para identificar baterías visibles en anaquel/exhibidor
— la sección está completamente vacía. Esto significa que las 4 marcas de la
sección 7 fueron capturadas sin evidencia fotográfica que las respalde.

---

## Otras señales relevantes para el veredicto

- **GPS:** Validado ✓ — coincide con "AUTO SERVICIO CALVA" en Google Maps a ~12.8m
  (ver reporte Excel de la automatización).
- **Estatus del negocio:** Operando.
- **⚠️ Folio duplicado:** NEG_FOLIO "CL - 960509" ya existe en **Case ID 1125** —
  vale la pena que el equipo confirme si es una re-encuesta legítima del mismo
  negocio o un error de captura/duplicado.
- **ENCVIS (Encuesta visible):** marcada como "Completa" por el encuestador, pese
  a la ausencia total de fotos.

---

## Recomendación de veredicto

**Calidad sugerida: `EN_RECUPERACION`** (no `APROBADA` ni `CANCELADA`).

**Por qué:**
- La ubicación (GPS) y el negocio están verificados y son reales — no amerita
  `CANCELADA`.
- Pero la encuesta **no tiene ninguna fotografía de respaldo** (ni fachada, ni
  interior, ni exhibidores) para verificar visualmente las 4 marcas capturadas
  en la sección 7, ni confirmar el POP o el estado del negocio — no debería
  aprobarse sin esa evidencia mínima.
- El folio duplicado (Case ID 1125) es una señal adicional a revisar antes de
  aprobar.

**Tipo de encuesta sugerido: `EN_RECUPERACION`** (para que coincida con el
veredicto de calidad — la encuesta necesita que el encuestador regrese a
levantar las fotos faltantes).

⚠️ **No se modificó nada en la plataforma.** Esta es una recomendación para que
el equipo decida; seleccionar y guardar estos valores en
`revisar.php?id=70112` requiere confirmación explícita antes de hacerlo.
