export const meta = {
  name: 'verificar-street-view',
  description: 'Verifica visualmente en Google Street View (imagen estática) si el negocio de cada caso coincide con el nombre registrado en la plataforma',
  whenToUse: 'Cuando la validación por búsqueda de texto en Google Maps no encontró el negocio o no tuvo una coincidencia de nombre exacta, y se quiere una segunda verificación visual (leer el rótulo real de la fachada) antes de decidir un veredicto de calidad.',
  phases: [{ title: 'Verificar' }],
}

// Uso: Workflow({ name: 'verificar-street-view', args: { cases: [
//   { case_id: '1780', business_name: 'Baterias hersa', business_name_original: 'BATERIAS ERSA', lat: 19.365518, lon: -99.1161249 },
//   ...
// ] } })
// El resultado (array de {case_id, street_view_available, visible_signage, match_verdict, notes})
// se puede pegar en excel_generator.append_street_view_verdicts(ruta_excel, resultado) para
// agregarlo como columna "Verificación Street View" al Excel de validaciones ya generado.
// Ver docs/FLUJO_TRABAJO.md ("Verificación visual con Street View (sub-agente)") y
// docs/TROUBLESHOOTING.md para el porqué del método de imágenes estáticas (el visor 3D no
// renderiza en el entorno de navegador de Claude Code — falla el contexto WebGPU).

const VERDICT_SCHEMA = {
  type: 'object',
  properties: {
    case_id: { type: 'string' },
    street_view_available: { type: 'boolean' },
    visible_signage: { type: 'string', description: 'Texto legible de rótulos/anuncios en la fachada, o cadena vacía si no se vio ninguno' },
    match_verdict: { type: 'string', enum: ['coincide', 'coincide_parcial', 'no_coincide', 'sin_street_view', 'indeterminado'] },
    notes: { type: 'string', description: 'Explicación breve (1-2 frases) de la conclusión, en español' },
  },
  required: ['case_id', 'street_view_available', 'match_verdict', 'notes'],
}

const cases = args.cases

log('Verificando ' + cases.length + ' caso(s) contra Street View...')

const results = await parallel(cases.map((c) => async () => {
  const prompt = [
    'Vas a verificar visualmente, usando imágenes estáticas de Google Street View, si el negocio del Case ID ' + c.case_id + ' existe en el sitio y si el rótulo/fachada coincide con el nombre registrado en una plataforma de censo.',
    '',
    'Datos del caso:',
    '- Nombre registrado (campo editable "nomneg"): "' + (c.business_name || '(vacío, no capturado)') + '"',
    '- Nombre original (campo "precargado", tal como se capturó en campo): "' + (c.business_name_original || '(vacío, no capturado)') + '"',
    '- Coordenadas GPS a verificar: ' + c.lat + ', ' + c.lon,
    '',
    'IMPORTANTE: el visor 3D interactivo de Street View (maps.google.com con el mapa/WebGL) NO renderiza en este entorno de navegador (falla la creación de contexto WebGPU). NO intentes usarlo. En vez de eso, usa este método probado, que sí funciona (imágenes estáticas, sin WebGL):',
    '',
    '1. Navega a: https://www.google.com/maps?layer=c&cbll=' + c.lat + ',' + c.lon,
    '   Esto redirige automáticamente al panorama de Street View más cercano a esas coordenadas (o a una foto de negocio cercana si no hay Street View real).',
    '2. Lee el texto de la página (get_page_text o read_page). Si aparece un aviso como "No hay imágenes de Street View disponibles en este lugar" (o equivalente en inglés), reporta street_view_available=false, match_verdict="sin_street_view", visible_signage="", notes explicando que no hay cobertura, y TERMINA aquí — no sigas al paso 3.',
    '3. Si NO aparece ese aviso, obtén la URL actual de la página (usa javascript_tool con "location.href") y extrae de ella el parámetro panoid=XXXXXXXXXXXXXXXXXXXXXX (una cadena alfanumérica larga, puede incluir - y _). IMPORTANTE: verifica que las coordenadas que trae esa misma URL resultante estén razonablemente cerca (unas pocas decenas de metros) de las coordenadas objetivo — si el panorama resuelto está a cientos de metros o kilómetros, probablemente Google saltó a otra ubicación por falta de cobertura real en el punto exacto; repórtalo como tal en las notas y considera match_verdict="indeterminado" en vez de afirmar una coincidencia.',
    '4. Con ese panoid, navega directamente (con la herramienta de navegación) a estas 4 URLs de imagen estática, una por una, para ver la panorámica completa desde distintos ángulos (sustituye <PANOID> por el valor real):',
    '   - https://streetviewpixels-pa.googleapis.com/v1/thumbnail?cb_client=maps_sv.tactile&w=900&h=600&pitch=0&panoid=<PANOID>&yaw=0',
    '   - https://streetviewpixels-pa.googleapis.com/v1/thumbnail?cb_client=maps_sv.tactile&w=900&h=600&pitch=0&panoid=<PANOID>&yaw=90',
    '   - https://streetviewpixels-pa.googleapis.com/v1/thumbnail?cb_client=maps_sv.tactile&w=900&h=600&pitch=0&panoid=<PANOID>&yaw=180',
    '   - https://streetviewpixels-pa.googleapis.com/v1/thumbnail?cb_client=maps_sv.tactile&w=900&h=600&pitch=0&panoid=<PANOID>&yaw=270',
    '   Cada una es simplemente una imagen JPEG — tómale una captura de pantalla (computer screenshot) y obsérvala directamente.',
    '5. En cada imagen, busca cualquier rótulo, anuncio pintado, o letrero de negocio legible en las fachadas visibles. Ignora anuncios de terceros/publicidad genérica (ej. refrescos, cerveza) que no sean el nombre del negocio mismo.',
    '6. Compara el texto que veas con los nombres registrados (editado y original) de arriba. Ten en cuenta que pueden diferir en ortografía, mayúsculas/minúsculas, o palabras adicionales como "Venta de baterías X" en vez de solo "X" — considera eso una coincidencia parcial o total según qué tan cercano sea, no lo descartes solo por no ser idéntico carácter por carácter.',
    '7. Devuelve tu conclusión con el schema pedido: match_verdict "coincide" (el nombre visible corresponde claramente), "coincide_parcial" (corresponde con diferencias menores de redacción/ortografía), "no_coincide" (se ve un negocio distinto o un local vacío/cerrado), "sin_street_view" (sin cobertura, ver paso 2), o "indeterminado" (había Street View pero ninguna imagen mostró un rótulo legible, o el panorama resuelto no corresponde geográficamente al punto exacto).',
    '',
    'Responde solo con el resultado estructurado.',
  ].join('\n')

  const result = await agent(prompt, { schema: VERDICT_SCHEMA, label: 'streetview:' + c.case_id, phase: 'Verificar' })
  return result ? Object.assign({}, c, result) : Object.assign({}, c, { street_view_available: false, match_verdict: 'indeterminado', visible_signage: '', notes: 'El sub-agente no devolvió resultado (error o fue omitido).' })
}))

return results
