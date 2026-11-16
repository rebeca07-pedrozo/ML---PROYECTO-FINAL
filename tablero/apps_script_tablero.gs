/**
 * TABLERO DE NEVERAS FEMSA — generador de hojas de resumen
 * Proyecto final de Machine Learning
 *
 * QUÉ HACE
 *   Lee la hoja con los datos de tablero_tiendas.csv y crea automáticamente:
 *     · "Resumen"        tarjetas de KPIs
 *     · "Por region"     ganancia y efecto por región     + gráfico
 *     · "Por ciudad"     lo mismo por ciudad              + gráfico
 *     · "Por tipo"       lo mismo por tipo de negocio     + gráfico
 *     · "Por riesgo"     conteo de riesgo alto / bajo     + gráfico
 *     · "Consulta"       buscador por id_tienda
 *
 * CÓMO USARLO
 *   1. Archivo > Importar > Subir > tablero_tiendas.csv
 *      En "Tipo de importación" elige INSERTAR NUEVA HOJA.
 *      Renombra esa hoja como:  tablero_tiendas
 *   2. Extensiones > Apps Script
 *   3. Borra todo lo que haya y pega ESTE archivo completo.
 *   4. Guarda (disquete) y ejecuta la función  construirTablero
 *      La primera vez Google pide permisos: Revisar permisos > tu cuenta >
 *      Configuración avanzada > Ir a (nombre del proyecto) > Permitir.
 *   5. Vuelve a la hoja: aparece el menú "🧊 Tablero Neveras" arriba.
 *
 * OJO CON LOS DECIMALES
 *   Si al importar ves 4.2 convertido en 42, cambia el idioma de la hoja:
 *   Archivo > Configuración > Configuración regional > Estados Unidos, y reimporta.
 */

// ============================ PARÁMETROS ============================

var HOJA_DATOS = 'tablero_tiendas';   // nombre de la hoja con el CSV importado

// Supuestos económicos del caso (solo para mostrarlos en el resumen)
var MARGEN               = 0.25;
var COSTO_NEVERA         = 60000;
var VALOR_EVITAR_CAMBIO  = 500000;
var COSTO_RETENCION      = 50000;
var EFECTIVIDAD          = 0.40;

// ============================ MENÚ ============================

function onOpen() {
  SpreadsheetApp.getUi()
    .createMenu('🧊 Tablero Neveras')
    .addItem('Construir / actualizar tablero', 'construirTablero')
    .addItem('Solo actualizar resumen', 'hojaResumen')
    .addSeparator()
    .addItem('Buscar una tienda por id', 'buscarTienda')
    .addToUi();
}

// ============================ PRINCIPAL ============================

function construirTablero() {
  var t0 = new Date();
  var d = leerDatos();
  hojaResumen(d);
  hojaDimension(d, 'region',       'Por region');
  hojaDimension(d, 'ciudad',       'Por ciudad');
  hojaDimension(d, 'tipo_negocio', 'Por tipo');
  hojaRiesgo(d);
  hojaConsulta();
  SpreadsheetApp.getActive().setActiveSheet(hoja('Resumen'));
  SpreadsheetApp.getUi().alert(
    'Tablero listo',
    'Se crearon las hojas de resumen a partir de ' + d.filas.length + ' tiendas.\n\n' +
    'Tiempo: ' + ((new Date() - t0) / 1000).toFixed(1) + ' s',
    SpreadsheetApp.getUi().ButtonSet.OK);
}

// ============================ LECTURA ============================

/** Lee la hoja de datos y devuelve {cab, idx, filas, sel} */
function leerDatos() {
  var sh = SpreadsheetApp.getActive().getSheetByName(HOJA_DATOS);
  if (!sh) {
    throw new Error('No encuentro la hoja "' + HOJA_DATOS + '". ' +
      'Importa tablero_tiendas.csv como hoja nueva y ponle ese nombre exacto.');
  }
  var v = sh.getDataRange().getValues();
  if (v.length < 2) throw new Error('La hoja "' + HOJA_DATOS + '" está vacía.');

  var cab = v[0].map(function (c) { return String(c).trim(); });
  var idx = {};
  cab.forEach(function (c, i) { idx[c] = i; });

  ['id_tienda', 'region', 'ciudad', 'tipo_negocio', 'ganancia_estimada_cop_mes',
   'efecto_pct_ventas', 'riesgo_cambio', 'seleccionada'].forEach(function (c) {
    if (!(c in idx)) throw new Error('Falta la columna "' + c + '" en ' + HOJA_DATOS + '.');
  });

  var filas = v.slice(1).filter(function (r) { return r[idx.id_tienda] !== ''; });
  // "sel" = solo las 1.000 tiendas elegidas; es lo que se grafica
  var sel = filas.filter(function (r) {
    var s = String(r[idx.seleccionada]).trim().toUpperCase();
    return s === 'SÍ' || s === 'SI' || s === 'TRUE' || s === 'VERDADERO';
  });
  if (!sel.length) {
    throw new Error('Ninguna fila tiene seleccionada = Sí. ¿Se importó bien el CSV?');
  }
  return { cab: cab, idx: idx, filas: filas, sel: sel };
}

/** Devuelve la hoja; la crea vacía si no existe, y la limpia si ya existía. */
function hoja(nombre) {
  var ss = SpreadsheetApp.getActive();
  var sh = ss.getSheetByName(nombre);
  if (!sh) return ss.insertSheet(nombre);
  sh.clear();
  sh.getCharts().forEach(function (c) { sh.removeChart(c); });
  return sh;
}

function suma(arr, f) { return arr.reduce(function (a, r) { return a + (Number(f(r)) || 0); }, 0); }

// ============================ RESUMEN ============================

function hojaResumen(d) {
  d = d || leerDatos();
  var I = d.idx, sh = hoja('Resumen');

  var gan   = suma(d.sel, function (r) { return r[I.ganancia_estimada_cop_mes]; });
  var efe   = suma(d.sel, function (r) { return r[I.efecto_pct_ventas]; }) / d.sel.length;
  var alto  = d.sel.filter(function (r) { return String(r[I.riesgo_cambio]).trim() === 'Alto'; }).length;
  var rent  = d.filas.filter(function (r) { return Number(r[I.ganancia_estimada_cop_mes]) > 0; }).length;
  var ganEl = d.filas.map(function (r) { return Number(r[I.ganancia_estimada_cop_mes]) || 0; });
  var minSel = Math.min.apply(null, d.sel.map(function (r) {
    return Number(r[I.ganancia_estimada_cop_mes]) || 0; }));

  sh.getRange('A1').setValue('PLAN DE NEVERAS FEMSA — RESUMEN')
    .setFontSize(16).setFontWeight('bold');
  sh.getRange('A2').setValue('Generado automáticamente desde la hoja "' + HOJA_DATOS + '" · ' +
    Utilities.formatDate(new Date(), Session.getScriptTimeZone(), 'dd/MM/yyyy HH:mm'))
    .setFontColor('#6c757d').setFontSize(10);

  var kpis = [
    ['INDICADOR', 'VALOR', 'UNIDAD'],
    ['Neveras a instalar',              d.sel.length,              'tiendas'],
    ['Tiendas elegibles',               d.filas.length,            'tiendas'],
    ['Tiendas elegibles rentables',     rent,                      'tiendas'],
    ['Ganancia mensual total',          gan,                       'COP/mes'],
    ['Ganancia anual',                  gan * 12,                  'COP/año'],
    ['Ganancia promedio por tienda',    gan / d.sel.length,        'COP/mes'],
    ['Ganancia de la tienda n° ' + d.sel.length, minSel,           'COP/mes'],
    ['Costo total de las neveras',      d.sel.length * COSTO_NEVERA, 'COP/mes'],
    ['Retorno sobre el costo',          gan / (d.sel.length * COSTO_NEVERA), 'veces'],
    ['Efecto promedio en la selección', efe / 100,                 '% de ventas'],
    ['Tiendas de riesgo alto',          alto,                      'tiendas'],
    ['% de riesgo alto en la lista',    alto / d.sel.length,       '%']
  ];
  sh.getRange(4, 1, kpis.length, 3).setValues(kpis);
  sh.getRange(4, 1, 1, 3).setFontWeight('bold').setBackground('#15233a').setFontColor('#ffffff');

  // formatos: pesos sin decimales, porcentajes con uno
  sh.getRange('B8:B12').setNumberFormat('$ #,##0');
  sh.getRange('B13').setNumberFormat('0.00" x"');
  sh.getRange('B14').setNumberFormat('0.0%');
  sh.getRange('B16').setNumberFormat('0.0%');
  sh.getRange('B5:B7').setNumberFormat('#,##0');
  sh.getRange('B15').setNumberFormat('#,##0');

  var sup = kpis.length + 5;
  sh.getRange(sup, 1).setValue('SUPUESTOS DEL CASO').setFontWeight('bold');
  sh.getRange(sup + 1, 1, 5, 2).setValues([
    ['Margen de FEMSA sobre ventas',        MARGEN],
    ['Costo de cada nevera (COP/mes)',      COSTO_NEVERA],
    ['Valor de evitar un cambio (COP)',     VALOR_EVITAR_CAMBIO],
    ['Costo de una acción de retención',    COSTO_RETENCION],
    ['Efectividad de la retención',         EFECTIVIDAD]
  ]);
  sh.getRange(sup + 1, 2).setNumberFormat('0%');
  sh.getRange(sup + 5, 2).setNumberFormat('0%');
  sh.getRange(sup + 2, 2, 3, 1).setNumberFormat('$ #,##0');

  var f = sup + 7;
  sh.getRange(f, 1).setValue('Ganancia = ' + MARGEN + ' × ventas adicionales − ' +
    COSTO_NEVERA + ' COP').setFontColor('#6c757d').setFontStyle('italic');

  sh.setColumnWidth(1, 300); sh.setColumnWidth(2, 150); sh.setColumnWidth(3, 120);
  sh.setFrozenRows(4);
}

// ============================ AGREGADOS POR DIMENSIÓN ============================

function hojaDimension(d, campo, nombreHoja) {
  var I = d.idx, sh = hoja(nombreHoja);
  if (!(campo in I)) { sh.getRange('A1').setValue('Falta la columna ' + campo); return; }

  var m = {};
  d.sel.forEach(function (r) {
    var k = String(r[I[campo]]);
    if (!m[k]) m[k] = { n: 0, gan: 0, efe: 0, alto: 0 };
    m[k].n++;
    m[k].gan += Number(r[I.ganancia_estimada_cop_mes]) || 0;
    m[k].efe += Number(r[I.efecto_pct_ventas]) || 0;
    if (String(r[I.riesgo_cambio]).trim() === 'Alto') m[k].alto++;
  });

  var filas = Object.keys(m).map(function (k) {
    return [k, m[k].n, m[k].gan, m[k].gan / m[k].n, m[k].efe / m[k].n / 100, m[k].alto];
  }).sort(function (a, b) { return b[2] - a[2]; });

  sh.getRange(1, 1).setValue('GANANCIA POR ' + campo.toUpperCase().replace('_', ' '))
    .setFontSize(14).setFontWeight('bold');
  var cab = [[campo, 'tiendas', 'ganancia total', 'ganancia promedio',
              'efecto promedio', 'riesgo alto']];
  sh.getRange(3, 1, 1, 6).setValues(cab)
    .setFontWeight('bold').setBackground('#15233a').setFontColor('#ffffff');
  sh.getRange(4, 1, filas.length, 6).setValues(filas);
  sh.getRange(4, 3, filas.length, 2).setNumberFormat('$ #,##0');
  sh.getRange(4, 5, filas.length, 1).setNumberFormat('0.0%');
  sh.setColumnWidth(1, 190);
  sh.setFrozenRows(3);

  // gráfico de barras nativo de Sheets
  var n = Math.min(filas.length, 15);
  var ch = sh.newChart().asBarChart()
    .addRange(sh.getRange(3, 1, n + 1, 1))
    .addRange(sh.getRange(3, 3, n + 1, 1))
    .setNumHeaders(1)
    .setOption('title', 'Ganancia mensual por ' + campo.replace('_', ' '))
    .setOption('legend', { position: 'none' })
    .setOption('colors', ['#2a78d6'])
    .setOption('hAxis', { title: 'COP / mes' })
    .setOption('width', 620).setOption('height', 24 * n + 120)
    .setPosition(3, 8, 0, 0)
    .build();
  sh.insertChart(ch);
}

// ============================ RIESGO ============================

function hojaRiesgo(d) {
  var I = d.idx, sh = hoja('Por riesgo');
  var alto = d.sel.filter(function (r) { return String(r[I.riesgo_cambio]).trim() === 'Alto'; });
  var bajo = d.sel.length - alto.length;

  sh.getRange(1, 1).setValue('RIESGO DE CAMBIO DE PROVEEDOR')
    .setFontSize(14).setFontWeight('bold');
  sh.getRange(2, 1).setValue(
    'Umbral por costos: p ≥ ' + (COSTO_RETENCION / (EFECTIVIDAD * VALOR_EVITAR_CAMBIO)).toFixed(2) +
    '  =  ' + COSTO_RETENCION + ' / (' + EFECTIVIDAD + ' × ' + VALOR_EVITAR_CAMBIO + ')')
    .setFontColor('#6c757d').setFontStyle('italic');

  sh.getRange(4, 1, 3, 3).setValues([
    ['riesgo', 'tiendas', 'ganancia'],
    ['Bajo', bajo, suma(d.sel.filter(function (r) {
       return String(r[I.riesgo_cambio]).trim() !== 'Alto'; }),
       function (r) { return r[I.ganancia_estimada_cop_mes]; })],
    ['Alto', alto.length, suma(alto, function (r) { return r[I.ganancia_estimada_cop_mes]; })]
  ]);
  sh.getRange(4, 1, 1, 3).setFontWeight('bold').setBackground('#15233a').setFontColor('#ffffff');
  sh.getRange(5, 3, 2, 1).setNumberFormat('$ #,##0');

  // valor de una campaña de retención sobre las tiendas de riesgo alto de la lista
  if ('prob_cambio' in I) {
    var esperado = suma(alto, function (r) { return r[I.prob_cambio]; });
    sh.getRange(8, 1).setValue('VALOR DE RETENER LAS DE RIESGO ALTO DE LA LISTA').setFontWeight('bold');
    sh.getRange(9, 1, 4, 2).setValues([
      ['Cambios esperados sin actuar',   esperado],
      ['Cambios evitados (40 %)',        esperado * EFECTIVIDAD],
      ['Costo de la campaña',            alto.length * COSTO_RETENCION],
      ['Valor neto',                     esperado * EFECTIVIDAD * VALOR_EVITAR_CAMBIO
                                          - alto.length * COSTO_RETENCION]
    ]);
    sh.getRange(9, 2, 2, 1).setNumberFormat('#,##0.0');
    sh.getRange(11, 2, 2, 1).setNumberFormat('$ #,##0');
  }
  sh.setColumnWidth(1, 300); sh.setColumnWidth(2, 140); sh.setColumnWidth(3, 160);

  var ch = sh.newChart().asPieChart()
    .addRange(sh.getRange(4, 1, 3, 2)).setNumHeaders(1)
    .setOption('title', 'Riesgo de cambio en las tiendas seleccionadas')
    .setOption('pieHole', 0.55)
    .setOption('colors', ['#0ca30c', '#d03b3b'])
    .setOption('width', 460).setOption('height', 320)
    .setPosition(4, 5, 0, 0).build();
  sh.insertChart(ch);
}

// ============================ CONSULTA POR ID ============================

function hojaConsulta() {
  var sh = hoja('Consulta');
  // (devuelve sh al final: buscarTienda lo usa)
  sh.getRange('A1').setValue('CONSULTA POR ID_TIENDA').setFontSize(14).setFontWeight('bold');
  sh.getRange('A3').setValue('Escribe un id_tienda aquí →').setFontWeight('bold');
  sh.getRange('B3').setValue('T02355')
    .setBackground('#fff4e5').setBorder(true, true, true, true, false, false);
  sh.getRange('A5').setFormula(
    '=IFERROR(TRANSPOSE(' + HOJA_DATOS + '!A1:AJ1),"")');
  sh.getRange('B5').setFormula(
    '=IFERROR(TRANSPOSE(FILTER(' + HOJA_DATOS + '!A2:AJ,' +
    'EXACT(UPPER(' + HOJA_DATOS + '!A2:A),UPPER($B$3)))),' +
    '"No existe esa tienda entre las elegibles")');
  sh.getRange('A5:A60').setFontWeight('bold');
  sh.setColumnWidth(1, 240); sh.setColumnWidth(2, 260);
  sh.getRange('D3').setValue(
    'Solo aparecen tiendas ELEGIBLES. Las que ya tienen nevera FEMSA no están en esta base.')
    .setFontColor('#6c757d').setFontStyle('italic');
  return sh;
}

function buscarTienda() {
  var ui = SpreadsheetApp.getUi();
  var r = ui.prompt('Buscar tienda', 'Escribe el id_tienda (ej. T02355):', ui.ButtonSet.OK_CANCEL);
  if (r.getSelectedButton() !== ui.Button.OK) return;
  var id = r.getResponseText().trim().toUpperCase();
  var sh = SpreadsheetApp.getActive().getSheetByName('Consulta') || hojaConsulta();
  sh.getRange('B3').setValue(id);
  SpreadsheetApp.getActive().setActiveSheet(sh);
}
