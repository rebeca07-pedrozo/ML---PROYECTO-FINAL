/**
 * TABLERO DE NEVERAS FEMSA — aplicación web de Google Apps Script
 * Proyecto final de Machine Learning
 *
 * ───────────────────────────────────────────────────────────────────────────
 *  CÓMO PUBLICARLO (5 minutos)
 * ───────────────────────────────────────────────────────────────────────────
 *  1. Abre tu Google Sheets e importa el CSV:
 *       Archivo > Importar > Subir > tablero_tiendas.csv
 *       Tipo de importación: INSERTAR NUEVA HOJA   ·   Separador: Coma
 *     Renombra esa pestaña exactamente como:   tablero_tiendas
 *
 *     ⚠️ Si ves 28.0 convertido en 280 o 4.2 en 42, cambia el idioma de la hoja:
 *        Archivo > Configuración > Configuración regional > Estados Unidos
 *        y vuelve a importar.
 *
 *  2. Extensiones > Apps Script.
 *
 *  3. En el editor crea DOS archivos con estos nombres exactos:
 *       · codigo.gs      → pega este archivo
 *       · tablero.html   → (+ > HTML)  pega el otro archivo
 *     Borra el Codigo.gs de ejemplo que trae Google si te queda otro.
 *
 *  4. Guarda (💾).
 *
 *  5. Implementar > Nueva implementación > ⚙️ > Aplicación web
 *       Ejecutar como:        Yo
 *       Quién tiene acceso:   Cualquier usuario con el enlace
 *     > Implementar > autoriza (Revisar permisos > tu cuenta >
 *       Configuración avanzada > Ir a … > Permitir)
 *
 *  6. Copia la URL de la aplicación web. Esa URL ES EL TABLERO.
 *
 *  Para ver cambios después de editar: Implementar > Gestionar implementaciones
 *  > ✏️ > Versión: Nueva versión > Implementar.
 *  Para probar sin publicar: Implementar > Probar implementaciones.
 * ───────────────────────────────────────────────────────────────────────────
 */

// ============================ PARÁMETROS ============================

/** Pestaña con los datos de tablero_tiendas.csv */
var HOJA_DATOS = 'tablero_tiendas';

/** Pestaña opcional con importancia_heterogeneidad.csv (columnas: variable, importancia).
 *  Si no existe, el tablero oculta ese gráfico sin fallar. */
var HOJA_IMPORTANCIA = 'importancia';

/** Supuestos económicos del caso */
var MARGEN       = 0.25;
var COSTO_NEVERA = 60000;

// ============================ PUNTO DE ENTRADA ============================

/** Google llama a esta función cuando alguien abre la URL de la aplicación web. */
function doGet() {
  var t = HtmlService.createTemplateFromFile('tablero');

  try {
    t.datos = JSON.stringify(construirPayload());
    t.error = null;
  } catch (err) {
    t.datos = 'null';
    t.error = JSON.stringify(String(err && err.message ? err.message : err));
  }

  return t.evaluate()
    .setTitle('Plan de Neveras FEMSA')
    .addMetaTag('viewport', 'width=device-width, initial-scale=1');
}

// ============================ LECTURA DE LA HOJA ============================

/**
 * Lee la hoja, arma las agregaciones y devuelve el objeto que consume tablero.html.
 * Se hace todo aquí (del lado del servidor) para mandar al navegador solo lo necesario:
 * las 1.000 tiendas seleccionadas, no las 12.700.
 */
function construirPayload() {
  var ss = SpreadsheetApp.getActiveSpreadsheet();
  var sh = ss.getSheetByName(HOJA_DATOS);

  if (!sh) {
    var nombres = ss.getSheets().map(function (s) { return '"' + s.getName() + '"'; }).join(', ');
    throw new Error('No encuentro la pestaña "' + HOJA_DATOS + '". ' +
      'Las pestañas de este archivo son: ' + nombres + '. ' +
      'Importa tablero_tiendas.csv y renombra esa pestaña como "' + HOJA_DATOS + '".');
  }

  var v = sh.getDataRange().getValues();
  if (v.length < 2) throw new Error('La pestaña "' + HOJA_DATOS + '" está vacía.');

  var idx = {};
  v[0].forEach(function (c, i) { idx[String(c).trim()] = i; });

  ['id_tienda', 'region', 'ciudad', 'tipo_negocio', 'zona', 'latitud', 'longitud',
   'temperatura_media_c', 'clientes_prom_dia', 'ventas_femsa_cop_mes',
   'efecto_pct_ventas', 'ganancia_estimada_cop_mes', 'ranking',
   'riesgo_cambio', 'seleccionada'].forEach(function (c) {
    if (!(c in idx)) {
      throw new Error('Falta la columna "' + c + '" en la pestaña "' + HOJA_DATOS +
        '". ¿Importaste tablero_tiendas.csv completo?');
    }
  });

  var N = function (x) { var n = Number(x); return isNaN(n) ? 0 : n; };
  var S = function (x) { return String(x === null || x === undefined ? '' : x).trim(); };
  var esSi = function (x) {
    var s = S(x).toUpperCase();
    return s === 'SÍ' || s === 'SI' || s === 'TRUE' || s === 'VERDADERO';
  };

  var tiendas = [];                 // solo las seleccionadas: lo que viaja al navegador
  var nElegibles = 0, nRentables = 0;
  var sumaEfectoTodas = 0;
  // Comparacion con las reglas simples: las columnas en_regla_* marcan que tiendas
  // elegiria cada regla, asi que la ganancia de cada estrategia sale de la misma hoja.
  var ganSel = 0, ganVentas = 0, ganTrafico = 0;
  var hayReglas = ('en_regla_ventas' in idx) && ('en_regla_trafico' in idx);
  var bandas = [
    { banda: '< 16 °C',  max: 16, suma: 0, n: 0 },
    { banda: '16-20 °C', max: 20, suma: 0, n: 0 },
    { banda: '20-24 °C', max: 24, suma: 0, n: 0 },
    { banda: '24-28 °C', max: 28, suma: 0, n: 0 },
    { banda: '> 28 °C',  max: 1e9, suma: 0, n: 0 }
  ];

  for (var i = 1; i < v.length; i++) {
    var r = v[i];
    if (S(r[idx.id_tienda]) === '') continue;
    nElegibles++;

    var gan = N(r[idx.ganancia_estimada_cop_mes]);
    var efe = N(r[idx.efecto_pct_ventas]);
    var tmp = N(r[idx.temperatura_media_c]);
    if (gan > 0) nRentables++;
    sumaEfectoTodas += efe;

    for (var b = 0; b < bandas.length; b++) {
      if (tmp < bandas[b].max) { bandas[b].suma += efe; bandas[b].n++; break; }
    }

    if (hayReglas) {
      if (esSi(r[idx.en_regla_ventas]))  ganVentas  += gan;
      if (esSi(r[idx.en_regla_trafico])) ganTrafico += gan;
    }

    if (esSi(r[idx.seleccionada])) {
      ganSel += gan;
      tiendas.push({
        id:  S(r[idx.id_tienda]),
        reg: S(r[idx.region]),
        ciu: S(r[idx.ciudad]),
        tip: S(r[idx.tipo_negocio]),
        zon: S(r[idx.zona]),
        lat: Math.round(N(r[idx.latitud])  * 1000) / 1000,
        lon: Math.round(N(r[idx.longitud]) * 1000) / 1000,
        tmp: tmp,
        cli: N(r[idx.clientes_prom_dia]),
        ven: N(r[idx.ventas_femsa_cop_mes]),
        efe: efe,
        gan: gan,
        rnk: N(r[idx.ranking]),
        rsg: S(r[idx.riesgo_cambio])
      });
    }
  }

  if (!tiendas.length) {
    throw new Error('Ninguna fila tiene seleccionada = "Sí". ' +
      'Revisa que el CSV se haya importado completo y sin dañar los acentos.');
  }

  return {
    tiendas: tiendas,
    reglas: hayReglas ? [
      { nombre: 'Modelo causal\n(nuestra lista)', ganancia: ganSel },
      { nombre: 'Regla: mayores\nventas',         ganancia: ganVentas },
      { nombre: 'Regla: mayor\ntráfico',          ganancia: ganTrafico }
    ] : [],
    temp: bandas.map(function (b) {
      return { banda: b.banda, efecto: b.n ? Math.round(b.suma / b.n * 10) / 10 : 0, n: b.n };
    }),
    importancia: leerImportancia(ss),
    meta: {
      nElegibles:   nElegibles,
      nRentables:   nRentables,
      efectoTodas:  nElegibles ? Math.round(sumaEfectoTodas / nElegibles * 10) / 10 : 0,
      margen:       MARGEN,
      costoNevera:  COSTO_NEVERA,
      actualizado:  Utilities.formatDate(new Date(), Session.getScriptTimeZone(),
                      "dd/MM/yyyy 'a las' HH:mm")
    }
  };
}

/** Pestaña opcional de importancia de variables. Devuelve [] si no existe. */
function leerImportancia(ss) {
  var sh = ss.getSheetByName(HOJA_IMPORTANCIA);
  if (!sh) return [];
  try {
    var v = sh.getDataRange().getValues();
    if (v.length < 2) return [];
    var idx = {};
    v[0].forEach(function (c, i) { idx[String(c).trim()] = i; });
    if (!('variable' in idx) || !('importancia' in idx)) return [];
    return v.slice(1)
      .filter(function (r) { return String(r[idx.variable]).trim() !== ''; })
      .map(function (r) {
        return { variable: String(r[idx.variable]), importancia: Number(r[idx.importancia]) || 0 };
      })
      .sort(function (a, b) { return b.importancia - a.importancia; })
      .slice(0, 8);
  } catch (e) {
    return [];
  }
}

// ============================ EXTRAS ============================

/** Menú en la hoja con un acceso directo a la URL publicada. */
function onOpen() {
  SpreadsheetApp.getUi()
    .createMenu('🧊 Tablero Neveras')
    .addItem('Abrir el tablero', 'abrirTablero')
    .addToUi();
}

function abrirTablero() {
  var url = ScriptApp.getService().getUrl();
  var ui = SpreadsheetApp.getUi();
  if (!url) {
    ui.alert('Todavía no está publicado',
      'Ve a Implementar > Nueva implementación > Aplicación web.',
      ui.ButtonSet.OK);
    return;
  }
  var html = HtmlService.createHtmlOutput(
    '<p style="font-family:sans-serif">El tablero está en:</p>' +
    '<p><a href="' + url + '" target="_blank">' + url + '</a></p>')
    .setWidth(460).setHeight(140);
  ui.showModalDialog(html, 'Tablero de Neveras');
}

/** Para revisar desde el editor que la hoja se lee bien (Ejecutar > probarLectura). */
function probarLectura() {
  var p = construirPayload();
  Logger.log('Tiendas seleccionadas: %s', p.tiendas.length);
  Logger.log('Elegibles: %s · rentables: %s', p.meta.nElegibles, p.meta.nRentables);
  Logger.log('Primera tienda: %s', JSON.stringify(p.tiendas[0]));
  Logger.log('Importancia: %s filas', p.importancia.length);
}
