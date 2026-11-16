# ===================== MODULO 7 =====================
md(r"""
---
# Módulo 7 — Exportación de resultados

Esta sección produce los archivos de la entrega y los insumos del tablero. Todo queda en la carpeta
`salidas/`.

| Archivo | Para qué | Filas |
|---|---|---|
| `lista_grupoX.csv` | **Entregable oficial**: las 1.000 tiendas | 1.000 |
| `tablero_tiendas.csv` | Hoja principal del tablero: todas las elegibles con su efecto, ganancia y riesgo | 12.700 |
| `tablero_kpis.csv` | Indicadores de resumen para las tarjetas del tablero | ~20 |
| `comparacion_reglas.csv` | Nuestra lista vs las reglas simples | 4 |
| `importancia_variables.csv` | Importancia en el modelo de ventas | ~47 |
| `importancia_heterogeneidad.csv` | Qué determina el tamaño del efecto | ~41 |
| `importancia_riesgo.csv` | Predictores del cambio de proveedor | ~107 |
| `metricas_modelos_ventas.csv` | Comparación de algoritmos del módulo 3 | 4 |
| `metricas_modelos_riesgo.csv` | Comparación de algoritmos del módulo 5 | 3 |
| `validacion_gate.csv` | Validación del modelo causal por decil | 10 |
| `curva_umbral_retencion.csv` | Valor neto de la retención por umbral | ~66 |
| `balance_covariables.csv` | SMD antes/después del ajuste | ~41 |
| `sensibilidad_efecto.csv`, `sensibilidad_decision.csv` | Robustez | ~5 / ~9 |
| `diccionario_salidas.csv` | Qué significa cada columna del tablero | ~25 |
""")

code(r"""
# ----------------------------- 7.1 Entregable oficial: lista_grupoX.csv -----------------------------
# Exactamente 1.000 filas y las tres columnas que pide el enunciado.
lista_entrega = (LISTA[['id_tienda','ganancia_estimada_cop_mes','riesgo_cambio']]
                 .copy()
                 .sort_values('ganancia_estimada_cop_mes', ascending=False)
                 .reset_index(drop=True))
lista_entrega['ganancia_estimada_cop_mes'] = lista_entrega.ganancia_estimada_cop_mes.round(0).astype('int64')

# --- VALIDACIONES DEL ENTREGABLE (una lista mal armada se califica con 0) ---
ids_elegibles = set(df.loc[df.elegible, 'id_tienda'])
v = {
 'exactamente 1.000 filas'          : len(lista_entrega) == 1000,
 'sin id_tienda repetidos'          : lista_entrega.id_tienda.duplicated().sum() == 0,
 'todas las tiendas son elegibles'  : set(lista_entrega.id_tienda).issubset(ids_elegibles),
 'ninguna tiene nevera FEMSA'       : df.set_index('id_tienda').loc[lista_entrega.id_tienda,'nevera_femsa'].sum() == 0,
 'regla Postobón y < 12 m² respetada':
     not ((df.set_index('id_tienda').loc[lista_entrega.id_tienda,'nevera_postobon'] == 1) &
          (df.set_index('id_tienda').loc[lista_entrega.id_tienda,'area_m2'] < AREA_MIN_SI_POSTOBON)).any(),
 'columnas exactas'                 : list(lista_entrega.columns) == ['id_tienda','ganancia_estimada_cop_mes','riesgo_cambio'],
 'sin valores faltantes'            : int(lista_entrega.isna().sum().sum()) == 0,
 'riesgo_cambio solo Alto/Bajo'     : set(lista_entrega.riesgo_cambio.unique()) <= {'Alto','Bajo'},
}
print('===== VALIDACIÓN DEL ENTREGABLE =====\n')
for k, ok in v.items():
    print(('  OK  ' if ok else ' FALLA') + f' | {k}')
assert all(v.values()), 'El entregable no cumple los requisitos.'

ruta_lista = f'{RUTA_SALIDAS}/lista_grupo{GRUPO}.csv'
lista_entrega.to_csv(ruta_lista, index=False, encoding='utf-8')
print(f'\nGuardado: {ruta_lista}')
print(f'  {len(lista_entrega):,} filas  |  ganancia total {cop(lista_entrega.ganancia_estimada_cop_mes.sum())} / mes')
print(f'  riesgo Alto: {(lista_entrega.riesgo_cambio=="Alto").sum()}  |  '
      f'riesgo Bajo: {(lista_entrega.riesgo_cambio=="Bajo").sum()}')
print('\nPrimeras 10 filas:')
print(lista_entrega.head(10).to_string(index=False))
if GRUPO == 'X':
    print('\n  *** RECORDATORIO: cambiar la variable GRUPO en el módulo 0 por su número de grupo ***')
""")

code(r"""
# ----------------------------- 7.2 Hoja principal del tablero -----------------------------
# Un archivo con TODAS las elegibles (no solo las 1.000) para que el tablero permita explorar
# la decision: filtros por region/ciudad/tipo, mapa, consulta por id_tienda y comparacion de reglas.
COLS_TABLERO = ['id_tienda','region','departamento','ciudad','zona','tipo_negocio',
                'latitud','longitud','estrato','temperatura_media_c','area_m2','poblacion_500m',
                'clientes_prom_dia','n_referencias_total','antiguedad_anios','num_empleados',
                'nevera_postobon','nevera_propia_tienda','nevera_otras_marcas',
                'visitas_mes_femsa','pct_quiebre_femsa','indice_precio_femsa',
                'ventas_femsa_cop_mes','ventas_postobon_cop_mes','share_femsa_valor']

tablero = ELEG[[c for c in COLS_TABLERO if c in ELEG.columns]].copy()
tablero['efecto_pct_ventas']        = ((np.exp(ELEG.tau_log)-1)*100).round(2)
tablero['ventas_adicionales_cop_mes'] = ELEG.ventas_adicionales_cop.round(0).astype('int64')
tablero['ganancia_estimada_cop_mes']  = ELEG.ganancia_estimada_cop_mes.round(0).astype('int64')
tablero['ranking']                  = ELEG.ranking
tablero['seleccionada']             = np.where(ELEG.seleccionada, 'Sí', 'No')
tablero['prob_cambio']              = ELEG.prob_cambio.round(4)
tablero['riesgo_cambio']            = ELEG.riesgo_cambio
tablero['rentable']                 = np.where(ELEG.ganancia_estimada_cop_mes > 0, 'Sí', 'No')
# marcas de las reglas simples, para que el tablero compare sin recalcular
tablero['en_regla_ventas']          = np.where(tablero.id_tienda.isin(regla_ventas.id_tienda), 'Sí', 'No')
tablero['en_regla_trafico']         = np.where(tablero.id_tienda.isin(regla_trafico.id_tienda), 'Sí', 'No')
# redondeo de montos para que Google Sheets no los lea como texto
for c in ['ventas_femsa_cop_mes','ventas_postobon_cop_mes']:
    tablero[c] = tablero[c].round(0).astype('int64')

tablero = tablero.sort_values('ranking').reset_index(drop=True)
tablero.to_csv(f'{RUTA_SALIDAS}/tablero_tiendas.csv', index=False, encoding='utf-8')
print(f'Guardado: {RUTA_SALIDAS}/tablero_tiendas.csv')
print(f'  {len(tablero):,} filas x {tablero.shape[1]} columnas (todas las elegibles)')
print(f'  seleccionadas: {(tablero.seleccionada=="Sí").sum():,}')
print('\nColumnas:')
print(textwrap.fill(', '.join(tablero.columns), 100))
print('\nPrimeras 5 filas (columnas clave):')
print(tablero[['id_tienda','region','ciudad','tipo_negocio','ventas_femsa_cop_mes',
               'efecto_pct_ventas','ganancia_estimada_cop_mes','ranking','seleccionada',
               'riesgo_cambio']].head().to_string(index=False))
""")

code(r"""
# ----------------------------- 7.3 KPIs para las tarjetas del tablero -----------------------------
kpis = [
 ('Neveras a instalar',                     N_NEVERAS,                                 'tiendas'),
 ('Tiendas elegibles',                      len(ELEG),                                 'tiendas'),
 ('Tiendas elegibles rentables',            int((ELEG.ganancia_estimada_cop_mes>0).sum()), 'tiendas'),
 ('Ganancia mensual total estimada',        round(G_TOTAL),                            'COP/mes'),
 ('Ganancia anual estimada',                round(G_TOTAL*12),                         'COP/año'),
 ('Ganancia promedio por tienda',           round(LISTA.ganancia_estimada_cop_mes.mean()), 'COP/mes'),
 ('Ganancia de la tienda n° 1.000',         round(LISTA.ganancia_estimada_cop_mes.min()),  'COP/mes'),
 ('Ventas adicionales totales',             round(LISTA.ventas_adicionales_cop.sum()),  'COP/mes'),
 ('Costo total de las neveras',             N_NEVERAS*COSTO_NEVERA,                     'COP/mes'),
 ('Retorno sobre el costo',                 round(G_TOTAL/(N_NEVERAS*COSTO_NEVERA), 2), 'veces'),
 ('Efecto promedio de la nevera',           round((np.exp(ate_dr)-1)*100, 1),           '% de ventas'),
 ('Efecto por diferencia simple (sesgado)', round((np.exp(res['1. Diferencia simple de medias']['log'])-1)*100, 1), '% de ventas'),
 ('Ganancia regla "mayores ventas"',        round(g_v),                                 'COP/mes'),
 ('Ganancia regla "mayor tráfico"',         round(g_t),                                 'COP/mes'),
 ('Ganancia selección aleatoria',           round(g_a),                                 'COP/mes'),
 ('Ventaja sobre la mejor regla simple',    round(g_ml - max(g_v, g_t)),                'COP/mes'),
 ('Ventaja sobre la mejor regla simple (%)',round((g_ml/max(g_v,g_t)-1)*100, 1),        '%'),
 ('Tiendas de riesgo Alto en la lista',     int((LISTA.riesgo_cambio=='Alto').sum()),   'tiendas'),
 ('Umbral de riesgo por costos',            UMBRAL_COSTOS,                              'probabilidad'),
 ('R² del mejor modelo de ventas',          round(mejor_r2, 4),                         'R² en test (log)'),
 ('ROC-AUC del modelo de riesgo',           round(tab_ch.ROC_AUC.iloc[0], 4),           'AUC'),
 ('PR-AUC del modelo de riesgo',            round(tab_ch.PR_AUC.iloc[0], 4),            'AUC'),
]
kpi_df = pd.DataFrame(kpis, columns=['indicador','valor','unidad'])
kpi_df.to_csv(f'{RUTA_SALIDAS}/tablero_kpis.csv', index=False, encoding='utf-8')
print('===== INDICADORES PARA EL TABLERO =====\n')
print(kpi_df.assign(valor=kpi_df.valor.map(lambda x: f'{x:,.4f}'.rstrip('0').rstrip('.')
                                           if isinstance(x, float) else f'{x:,}'))
      .to_string(index=False, justify='left'))

# Agregados por region / ciudad / tipo, listos para graficar en el tablero
for dim in ['region','ciudad','tipo_negocio','zona']:
    agg = (tablero[tablero.seleccionada=='Sí'].groupby(dim)
           .agg(tiendas=('id_tienda','size'),
                ganancia_total=('ganancia_estimada_cop_mes','sum'),
                ganancia_promedio=('ganancia_estimada_cop_mes','mean'),
                efecto_pct_promedio=('efecto_pct_ventas','mean'),
                riesgo_alto=('riesgo_cambio', lambda s:(s=='Alto').sum()))
           .round(1).sort_values('ganancia_total', ascending=False).reset_index())
    agg.to_csv(f'{RUTA_SALIDAS}/tablero_por_{dim}.csv', index=False, encoding='utf-8')
print(f'\nGuardados: tablero_kpis.csv y agregados por region, ciudad, tipo_negocio y zona')
""")

code(r"""
# ----------------------------- 7.4 Diccionario de las salidas -----------------------------
dicc_salidas = pd.DataFrame([
 ('id_tienda','Identificador único de la tienda','texto'),
 ('region / departamento / ciudad','Ubicación comercial y administrativa','texto'),
 ('zona','Urbana, Periurbana o Rural','texto'),
 ('tipo_negocio','Formato del punto de venta','texto'),
 ('latitud / longitud','Coordenadas para el mapa del tablero','grados'),
 ('estrato','Estrato socioeconómico predominante (1 a 6)','entero'),
 ('temperatura_media_c','Temperatura media de la ubicación','°C'),
 ('area_m2','Área del local','m²'),
 ('poblacion_500m','Personas en un radio de 500 m','personas'),
 ('clientes_prom_dia','Clientes promedio por día abierto','clientes/día'),
 ('n_referencias_total','Referencias en el surtido','referencias'),
 ('nevera_postobon','La tienda tiene nevera de Postobón (0/1)','binaria'),
 ('nevera_propia_tienda','El tendero tiene nevera propia (0/1)','binaria'),
 ('ventas_femsa_cop_mes','Ventas actuales de FEMSA, sin nevera','COP/mes'),
 ('efecto_pct_ventas','Aumento estimado de ventas al instalar la nevera','%'),
 ('ventas_adicionales_cop_mes','Ventas adicionales estimadas por la nevera','COP/mes'),
 ('ganancia_estimada_cop_mes','0,25 × ventas adicionales − 60.000','COP/mes'),
 ('ranking','Posición de la tienda al ordenar por ganancia estimada (1 = mejor)','entero'),
 ('seleccionada','Sí = está entre las 1.000 elegidas','Sí/No'),
 ('rentable','Sí = la ganancia estimada es positiva','Sí/No'),
 ('prob_cambio','Probabilidad estimada de cambiar de proveedor en 6 meses','0 a 1'),
 ('riesgo_cambio','Alto si prob_cambio ≥ 0,25 (umbral por costos del caso)','Alto/Bajo'),
 ('en_regla_ventas','Sí = la regla simple de mayores ventas también la elegiría','Sí/No'),
 ('en_regla_trafico','Sí = la regla simple de mayor tráfico también la elegiría','Sí/No'),
], columns=['columna','definicion','unidad'])
dicc_salidas.to_csv(f'{RUTA_SALIDAS}/diccionario_salidas.csv', index=False, encoding='utf-8')
print('Guardado: diccionario_salidas.csv')
print(dicc_salidas.to_string(index=False))
""")

code(r"""
# ----------------------------- 7.5 Resumen final e inventario de archivos -----------------------------
print('='*78)
print('RESUMEN EJECUTIVO'.center(78))
print('='*78)
dif_simple_pct = (np.exp(res['1. Diferencia simple de medias']['log'])-1)
resumen_txt = [
 '',
 'PREGUNTA   En cuales 1.000 tiendas instalar las neveras y cuanto se gana al mes.',
 '',
 f'RESPUESTA  Las 1.000 tiendas de {RUTA_SALIDAS}/lista_grupo{GRUPO}.csv.',
 f'           Ganancia mensual estimada: {cop(G_TOTAL)}  ({mm(G_TOTAL)} COP)',
 f'           Ganancia anual estimada:   {mm(G_TOTAL*12)} COP',
 f'           Retorno sobre el costo de las neveras: {G_TOTAL/(N_NEVERAS*COSTO_NEVERA):.2f}x',
 '',
 f'METODO     El efecto de la nevera se estima con un DR-learner (doblemente robusto)',
 f'           con cross-fitting sobre {len(X_CAUSAL)} variables previas al tratamiento. El efecto',
 f'           promedio es {(np.exp(ate_dr)-1):+.1%} de las ventas, frente a {dif_simple_pct:+.1%} que sugiere la',
 f'           diferencia simple de promedios: el sesgo de seleccion explica cerca de',
 f'           la mitad de esa brecha.',
 '',
 f'VALOR      Frente a la mejor regla simple, el modelo agrega {mm(g_ml-max(g_v,g_t))} COP/mes',
 f'           ({g_ml/max(g_v,g_t)-1:+.1%}), equivalente a {mm((g_ml-max(g_v,g_t))*12)} COP al anio.',
 '',
 f'PERFIL     Tiendas calientes ({LISTA.temperatura_media_c.mean():.1f} C de media), de alto trafico',
 f'           ({LISTA.clientes_prom_dia.mean():.0f} clientes/dia) y sin espacio frio propio: solo',
 f'           {LISTA.nevera_propia_tienda.mean():.0%} tiene nevera propia.',
 '',
 f'RIESGO     {(LISTA.riesgo_cambio=="Alto").sum():,} de las 1.000 tiendas tienen riesgo alto de cambiar de',
 f'           proveedor en 6 meses. Se recomienda cruzarlas con la campania de retencion.',
 '',
]
print(chr(10).join(resumen_txt))
print('='*78)

arch = sorted(os.listdir(RUTA_SALIDAS))
print(f'\nARCHIVOS GENERADOS EN {RUTA_SALIDAS}/ ({len(arch)}):\n')
for a in arch:
    print(f'  {os.path.getsize(f"{RUTA_SALIDAS}/{a}")/1024:>8.1f} KB  {a}')
""")

code(r"""
# ----------------------------- 7.6 Descargar los archivos (solo en Colab) -----------------------------
# Descomentar el bloque que necesiten.

# --- A) Descargar solo el entregable oficial ---
# from google.colab import files
# files.download(f'{RUTA_SALIDAS}/lista_grupo{GRUPO}.csv')

# --- B) Descargar todas las salidas en un ZIP ---
# import shutil
# shutil.make_archive('salidas_proyecto_neveras', 'zip', RUTA_SALIDAS)
# from google.colab import files
# files.download('salidas_proyecto_neveras.zip')

# --- C) Copiar las salidas a Google Drive (requiere drive.mount en el módulo 0) ---
# import shutil
# destino = '/content/drive/MyDrive/proyecto_ml/salidas'
# os.makedirs(destino, exist_ok=True)
# for a in os.listdir(RUTA_SALIDAS):
#     shutil.copy(f'{RUTA_SALIDAS}/{a}', destino)
# print('Copiado a', destino)

print('Cuaderno terminado.')
print(f'\nEntregable oficial: {RUTA_SALIDAS}/lista_grupo{GRUPO}.csv')
print(f'Insumo del tablero: {RUTA_SALIDAS}/tablero_tiendas.csv')
print('\nPara el tablero en Google Sheets:')
print('  Archivo > Importar > subir tablero_tiendas.csv > Insertar nueva hoja')
print('  Repetir con tablero_kpis.csv y comparacion_reglas.csv.')
""")

md(r"""
---
## Cómo sigue el trabajo del grupo

**Para armar el tablero** (Streamlit, Dash o Power BI / Google Sheets):

- `tablero_tiendas.csv` es la hoja principal: trae las **12.700 elegibles** con su efecto estimado,
  ganancia, ranking, riesgo y coordenadas. La columna `seleccionada` marca las 1.000 elegidas.
  Alcanza para los requisitos del enunciado:
  - *filtros por región, ciudad y tipo de negocio* → columnas `region`, `ciudad`, `tipo_negocio`
  - *mapa de las 1.000 tiendas* → `latitud`, `longitud`, filtrando `seleccionada = Sí`
  - *ganancia estimada* → `ganancia_estimada_cop_mes`
  - *riesgo de cambio* → `riesgo_cambio`, `prob_cambio`
  - *consulta por id_tienda* → `id_tienda`
- `comparacion_reglas.csv` → la sección *comparación con reglas simples*.
- `importancia_variables.csv` e `importancia_heterogeneidad.csv` → la sección *importancia de variables*.
  La segunda es la más interesante para el tablero: muestra qué hace que una nevera rinda.
- `tablero_kpis.csv` → tarjetas de resumen.
- `tablero_por_region.csv`, `tablero_por_ciudad.csv`, `tablero_por_tipo_negocio.csv`,
  `tablero_por_zona.csv` → gráficos agregados sin recalcular nada.

**Para el informe gerencial:** el resumen ejecutivo de la celda 7.5 trae las cifras principales ya
redactadas; los supuestos están en la portada y las limitaciones al final del módulo 4.

**Antes de entregar:** cambiar `GRUPO = 'X'` en el módulo 0 por el número del grupo, para que el archivo
salga con el nombre correcto.
""")
