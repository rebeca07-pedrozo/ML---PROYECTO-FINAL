# ===================== PORTADA =====================
md(r"""
# Proyecto final de Machine Learning — Plan de neveras FEMSA

**Pregunta de negocio:** ¿en cuáles **1.000 tiendas** debe FEMSA instalar sus 1.000 neveras nuevas, y cuánto ganaría cada mes?

Este cuaderno corre **de principio a fin** desde la base original (`base_refrescos_nevera.csv`) y produce
todos los archivos que alimentan el tablero y la entrega.

---

## Cómo se organiza

| Módulo | Contenido | Puntos |
|---|---|---|
| 0 | Configuración, carga y validación de la base | — |
| 1 | Análisis exploratorio | 10 |
| 2 | Preparación de datos y control de fuga | 10 |
| 3 | Modelo de ventas (3+ algoritmos, validación cruzada) | 15 |
| 4 | **Efecto causal de la nevera** (el corazón del proyecto) | 20 |
| 5 | Riesgo de cambio de proveedor | 10 |
| 6 | Decisión: las 1.000 tiendas y la ganancia | 10 |
| 7 | Exportación de resultados para el tablero | — |

## Supuestos económicos del caso

| Supuesto | Valor |
|---|---|
| Margen de FEMSA sobre ventas al público | 25 % |
| Costo de cada nevera | COP 60.000 / mes |
| Valor de evitar un cambio de proveedor | COP 500.000 |
| Costo de una acción de retención | COP 50.000 |
| Efectividad de la retención | 40 % |

$$\text{Ganancia mensual} = 0{,}25 \times \text{Ventas adicionales por la nevera} - 60.000$$

**Tienda elegible:** `nevera_femsa = 0`, excepto si tiene nevera de Postobón y menos de 12 m².

## Reproducibilidad

Semilla fija `SEED = 42` en todos los modelos y particiones. Correr *Entorno de ejecución → Ejecutar todo*
reproduce exactamente los mismos números y los mismos 1.000 id_tienda.

---

### Declaración de uso de IA

Este proyecto se desarrolló con apoyo de un asistente de IA (Claude) en las siguientes tareas:
exploración inicial de la base, redacción del código del cuaderno, elección y discusión de los
estimadores causales, y redacción de los textos explicativos. Las decisiones de modelación
(definición del tratamiento, variables excluidas por fuga, estimador final, criterio de selección de las
1.000 tiendas) fueron revisadas, verificadas y asumidas por el grupo. Todos los integrantes pueden
explicar y modificar cualquier celda de este cuaderno.
""")

# ===================== MODULO 0 =====================
md(r"""
---
# Módulo 0 — Configuración y carga de datos
""")

code(r"""
# Dependencias. En Google Colab pandas, numpy, scikit-learn y matplotlib ya vienen instalados.
# Esta celda solo asegura una version minima de scikit-learn.
import sys, subprocess
try:
    import sklearn
    assert tuple(int(x) for x in sklearn.__version__.split('.')[:2]) >= (1, 3)
except Exception:
    subprocess.run([sys.executable, '-m', 'pip', 'install', '-q', 'scikit-learn>=1.3'], check=False)

import numpy as np, pandas as pd, matplotlib as mpl, matplotlib.pyplot as plt, sklearn, warnings, os, json, textwrap
warnings.filterwarnings('ignore')
print('pandas', pd.__version__, '| numpy', np.__version__, '| scikit-learn', sklearn.__version__)
""")

code(r"""
# ----------------------------- PARAMETROS DEL PROYECTO -----------------------------
SEED = 42                      # semilla fija: reproducibilidad
np.random.seed(SEED)

MARGEN               = 0.25     # margen de FEMSA sobre ventas al publico
COSTO_NEVERA         = 60_000   # COP por nevera por mes
VALOR_EVITAR_CAMBIO  = 500_000  # COP por evitar un cambio de proveedor
COSTO_RETENCION      = 50_000   # COP por accion de retencion
EFECTIVIDAD_RETENCION= 0.40     # 40 %
N_NEVERAS            = 1_000    # neveras a instalar
AREA_MIN_SI_POSTOBON = 12.0     # m2: si tiene nevera Postobon y area < 12 no es elegible

GRUPO = 'X'                     # <<< CAMBIAR por el numero de su grupo (ej. '3')

# Estetica de los graficos
plt.rcParams.update({'figure.dpi':110, 'figure.figsize':(9,4.5), 'axes.grid':True,
                     'grid.alpha':.25, 'axes.spines.top':False, 'axes.spines.right':False,
                     'font.size':10, 'axes.titlesize':11, 'axes.titleweight':'bold'})
C_SIN, C_CON, C_ML, C_R1, C_R2 = '#d1495b', '#0b7285', '#2b8a3e', '#e8973a', '#8d6ab5'

def cop(x, dec=0):
    'Formatea un numero como pesos colombianos.'
    return f'$ {x:,.{dec}f}'.replace(',', '.')

def mm(x):
    'Formatea en millones de COP.'
    return f'{x/1e6:,.1f} MM'.replace(',', '.')

RUTA_SALIDAS = 'salidas'
os.makedirs(RUTA_SALIDAS, exist_ok=True)
print('Parametros cargados. Semilla =', SEED)
""")

md(r"""
### Carga de la base

La celda busca el archivo en varias rutas. En Colab hay tres opciones:

1. **Subir el archivo** (más simple): se abre el selector si no encuentra la base.
2. **Google Drive**: descomentar el bloque de `drive.mount` y ajustar `RUTA_DRIVE`.
3. **Ruta local**: si se corre fuera de Colab, dejar el CSV en `datos/`.
""")

code(r"""
RUTA_DRIVE = '/content/drive/MyDrive/proyecto_ml/base_refrescos_nevera.csv'  # ajustar si usan Drive

# --- Opcion 2: Google Drive (descomentar las 2 lineas) ---
# from google.colab import drive
# drive.mount('/content/drive')

CANDIDATAS = ['base_refrescos_nevera.csv', 'datos/base_refrescos_nevera.csv',
              '/content/base_refrescos_nevera.csv', RUTA_DRIVE]

ruta = next((p for p in CANDIDATAS if os.path.exists(p)), None)

if ruta is None:
    try:                                    # Opcion 1: subir el archivo en Colab
        from google.colab import files
        print('Suba base_refrescos_nevera.csv')
        sub = files.upload()
        ruta = list(sub.keys())[0]
    except ImportError:
        raise FileNotFoundError('Coloque base_refrescos_nevera.csv en el directorio de trabajo.')

df = pd.read_csv(ruta)
print(f'Base cargada desde: {ruta}')
print(f'Filas: {df.shape[0]:,}   Columnas: {df.shape[1]}')
""")

code(r"""
# ----------------------------- VALIDACION DE INTEGRIDAD -----------------------------
chequeos = {
    'filas = 38.000'                  : len(df) == 38_000,
    'columnas = 109'                  : df.shape[1] == 109,
    'id_tienda sin duplicados'        : df['id_tienda'].duplicated().sum() == 0,
    'sin valores faltantes'           : int(df.isna().sum().sum()) == 0,
    'objetivo ventas presente'        : 'ventas_femsa_cop_mes' in df.columns,
    'objetivo cambio presente'        : 'cambio_proveedor_principal_6m' in df.columns,
    'tratamiento nevera_femsa binario': set(df['nevera_femsa'].unique()) <= {0, 1},
}
for k, v in chequeos.items():
    print(('  OK  ' if v else ' FALLA') + f' | {k}')
assert all(chequeos.values()), 'La base no cumple la estructura esperada.'
print('\nBase validada: 0 faltantes, 0 duplicados.')
""")

# ===================== MODULO 1 =====================
md(r"""
---
# Módulo 1 — Análisis exploratorio

**Objetivo:** entender las tiendas, las ventas y las neveras, y mostrar en qué se diferencian las tiendas
con nevera y sin nevera. Esa diferencia es la que justifica todo el módulo 4.

Buscamos cinco cosas concretas para la decisión:

1. ¿Cómo se distribuyen las ventas de FEMSA? (define cómo modelamos)
2. ¿Cuántas tiendas son elegibles y cómo se ven?
3. ¿En qué se diferencian las tiendas con y sin nevera? (sesgo de selección)
4. ¿Qué variables parecen amplificar el efecto de una nevera? (heterogeneidad)
5. ¿Cuánto riesgo de cambio de proveedor hay?
""")

code(r"""
# ----------------------------- 1.1 Panorama general -----------------------------
grupos = {
 'Identificación y geografía': ['id_tienda','region','departamento','ciudad','latitud','longitud'],
 'Entorno'    : ['zona','estrato','temperatura_media_c','poblacion_500m','n_tiendas_competencia_500m',
                 'dist_hard_discount_km','cerca_colegio','cerca_parada_transporte',
                 'cerca_universidad_oficinas','dist_cedi_km'],
 'Tienda'     : ['tipo_negocio','area_m2','antiguedad_anios','dias_abre_semana','horas_abre_dia',
                 'num_empleados','tiene_datafono','acepta_pago_digital','ofrece_domicilios',
                 'tiene_mesas_consumo','vende_licor','n_referencias_total','nevera_propia_tienda',
                 'nevera_otras_marcas'],
 'Tráfico'    : ['clientes_prom_dia'],
 'Gestión comercial': ['visitas_mes_femsa','visitas_mes_postobon','pct_quiebre_femsa','pct_quiebre_postobon',
                 'credito_femsa','credito_postobon','material_pop_femsa','material_pop_postobon',
                 'promos_activas_femsa','promos_activas_postobon','indice_precio_femsa','indice_precio_postobon'],
 'Neveras'    : ['nevera_femsa','nevera_postobon','num_neveras_femsa','num_neveras_postobon',
                 'presencia_neveras','puertas_nevera_femsa','puertas_nevera_postobon',
                 'antiguedad_nevera_femsa_anios','antiguedad_nevera_postobon_anios',
                 'nevera_femsa_operativa','nevera_postobon_operativa'],
}
grupos['Resultados'] = [c for c in df.columns
                        if c not in sum(grupos.values(), []) and c != 'cambio_proveedor_principal_6m']
grupos['Objetivo'] = ['cambio_proveedor_principal_6m']

print('Columnas por grupo del diccionario:')
for g, cols in grupos.items():
    print(f'  {g:28s} {len(cols):>3} columnas')
print(f'  {"TOTAL":28s} {sum(len(c) for c in grupos.values()):>3}')

print('\nCobertura geográfica y de formato:')
for c in ['region','departamento','ciudad','tipo_negocio','zona']:
    print(f'  {c:14s} {df[c].nunique():>3} valores   ej.: {", ".join(map(str, df[c].unique()[:3]))}')
""")

code(r"""
# ----------------------------- 1.2 Distribucion de las ventas de FEMSA -----------------------------
v = df['ventas_femsa_cop_mes']
print('Ventas FEMSA por tienda-mes (COP):')
print(f'  media     {cop(v.mean())}')
print(f'  mediana   {cop(v.median())}')
print(f'  P5 - P95  {cop(v.quantile(.05))}  a  {cop(v.quantile(.95))}')
print(f'  maximo    {cop(v.max())}')
print(f'  asimetria en niveles  {v.skew():.2f}')
print(f'  asimetria en log      {np.log(v).skew():.2f}   <-- casi simetrica')

fig, ax = plt.subplots(1, 2, figsize=(12, 4))
ax[0].hist(v/1e6, bins=80, color=C_CON, alpha=.85)
ax[0].set(title='Ventas FEMSA mensuales (millones COP)', xlabel='MM COP / mes', ylabel='tiendas')
ax[0].set_xlim(0, 10)
ax[1].hist(np.log(v), bins=80, color=C_CON, alpha=.85)
ax[1].set(title='log(Ventas FEMSA) — simétrica', xlabel='log(COP / mes)', ylabel='tiendas')
plt.tight_layout(); plt.show()
""")

md(r"""
> **Hallazgo 1 — las ventas son log-normales.** En niveles la distribución es muy asimétrica
> (asimetría ≈ 4,4); en logaritmo es prácticamente simétrica (≈ 0,0). Esto tiene dos consecuencias que
> usamos en todo el cuaderno:
>
> - El **modelo de ventas** (módulo 3) se entrena sobre `log(ventas)`: los errores se vuelven homocedásticos
>   y una tienda gigante deja de dominar el ajuste.
> - El **efecto de la nevera** (módulo 4) se comporta como un **porcentaje**, no como un monto fijo. Una
>   nevera que sube las ventas un 30 % vale COP 90.000 en una tienda de 300.000 y COP 900.000 en una de
>   3.000.000. Esa es la razón por la que la selección de tiendas importa tanto.
""")

code(r"""
# ----------------------------- 1.3 El parque de neveras -----------------------------
fig, ax = plt.subplots(1, 3, figsize=(13.5, 4))

pres = df['presencia_neveras'].value_counts()
ax[0].bar(pres.index, pres.values, color=[C_CON,'#4c9f70',C_SIN,'#9aa0a6'])
ax[0].set(title='Presencia de neveras', ylabel='tiendas'); ax[0].tick_params(axis='x', rotation=20)
for i, val in enumerate(pres.values):
    ax[0].text(i, val, f'{val:,}'.replace(',','.'), ha='center', va='bottom', fontsize=8)

cob = pd.DataFrame({'FEMSA':[df.nevera_femsa.mean()], 'Postobón':[df.nevera_postobon.mean()],
                    'Propia':[df.nevera_propia_tienda.mean()], 'Otras marcas':[df.nevera_otras_marcas.mean()]}).T[0]
ax[1].barh(cob.index, cob.values*100, color=[C_CON,C_SIN,'#9aa0a6','#c9ada7'])
ax[1].set(title='Cobertura de neveras (% de tiendas)', xlabel='%')
for i, val in enumerate(cob.values*100):
    ax[1].text(val, i, f' {val:.1f}%', va='center', fontsize=8)

t = df[df.nevera_femsa == 1]
ax[2].hist(t.antiguedad_nevera_femsa_anios, bins=30, color=C_CON, alpha=.85)
ax[2].set(title='Antigüedad de la nevera FEMSA instalada', xlabel='años')
plt.tight_layout(); plt.show()

print(f'Tiendas con nevera FEMSA : {df.nevera_femsa.sum():,}  ({df.nevera_femsa.mean():.1%})')
print(f'Tiendas sin nevera FEMSA : {(df.nevera_femsa==0).sum():,}  ({(df.nevera_femsa==0).mean():.1%})')
print('\nVentas FEMSA promedio según configuración de la nevera instalada:')
print(t.groupby('puertas_nevera_femsa')['ventas_femsa_cop_mes'].agg(['mean','count'])
       .rename(columns={'mean':'ventas_prom','count':'tiendas'}).round(0).to_string())
print('\nSegún si la nevera funciona:')
print(t.groupby('nevera_femsa_operativa')['ventas_femsa_cop_mes'].agg(['mean','count'])
       .rename(columns={'mean':'ventas_prom','count':'tiendas'}).round(0).to_string())
""")

md(r"""
> **Hallazgo 2 — la "nevera" no es una sola cosa.** Entre las tiendas tratadas hay neveras de 1, 2 y 4
> puertas, de 0 a 15 años, y unas 3.800 que **no funcionan**. Las ventas crecen con el número de puertas y
> caen cuando la nevera no es operativa. Como FEMSA va a instalar **una nevera nueva y operativa**, en el
> módulo 4 definimos el tratamiento con precisión y no mezclamos todas las configuraciones.
""")

code(r"""
# ----------------------------- 1.4 Tiendas con nevera vs sin nevera -----------------------------
# Esta es la tabla mas importante del EDA: muestra que las neveras NO se asignaron al azar.
def dme(col):
    'Diferencia de medias estandarizada (SMD) entre tiendas con y sin nevera FEMSA.'
    a, b = df.loc[df.nevera_femsa == 1, col], df.loc[df.nevera_femsa == 0, col]
    s = np.sqrt((a.var() + b.var()) / 2)
    return a.mean(), b.mean(), (a.mean() - b.mean()) / s if s > 0 else 0.0

comp_vars = ['ventas_femsa_cop_mes','clientes_prom_dia','area_m2','n_referencias_total','poblacion_500m',
             'num_empleados','horas_abre_dia','estrato','visitas_mes_femsa','temperatura_media_c',
             'n_tiendas_competencia_500m','antiguedad_anios','nevera_propia_tienda','nevera_postobon',
             'tiene_datafono','pct_quiebre_femsa']
tabla = pd.DataFrame([dict(zip(['variable','con_nevera','sin_nevera','SMD'], (c,)+dme(c))) for c in comp_vars])
tabla['SMD_abs'] = tabla.SMD.abs()
tabla = tabla.sort_values('SMD_abs', ascending=False)
print('Tiendas CON nevera FEMSA vs SIN nevera FEMSA\n')
print(tabla[['variable','con_nevera','sin_nevera','SMD']].to_string(index=False,
      formatters={'con_nevera':'{:,.2f}'.format,'sin_nevera':'{:,.2f}'.format,'SMD':'{:+.3f}'.format}))

d_naive = (df.loc[df.nevera_femsa==1,'ventas_femsa_cop_mes'].mean()
           - df.loc[df.nevera_femsa==0,'ventas_femsa_cop_mes'].mean())
print(f'\nDiferencia simple de ventas promedio: {cop(d_naive)} / mes')
print(f'Si fuera causal, la ganancia por tienda seria {cop(MARGEN*d_naive - COSTO_NEVERA)} / mes.')

fig, ax = plt.subplots(figsize=(8, 5))
t2 = tabla.sort_values('SMD_abs')
ax.barh(t2.variable, t2.SMD_abs, color=np.where(t2.SMD_abs > .1, C_SIN, '#9aa0a6'))
ax.axvline(.1, ls='--', c='k', lw=1)
ax.text(.105, 0, ' umbral 0,1', fontsize=8)
ax.set(title='Desbalance entre tiendas con y sin nevera (|SMD|)', xlabel='|SMD|')
plt.tight_layout(); plt.show()
""")

md(r"""
> **Hallazgo 3 — el sesgo de selección es grande y medible.** Las tiendas que ya tienen nevera FEMSA
> reciben **+29 % más clientes**, son **~28 % más grandes** y tienen más referencias en el surtido. Varias
> variables superan el umbral habitual de |SMD| > 0,1, que es el que se usa para declarar un desbalance
> preocupante.
>
> La diferencia simple de ventas (≈ COP 748.000) **no es el efecto de la nevera**: mezcla el efecto real con
> el hecho de que FEMSA puso sus neveras en las mejores tiendas. Tomar ese número como causal llevaría a
> estimar una ganancia de ~COP 127.000 por tienda y a declarar rentables casi todas las tiendas. El módulo 4
> corrige exactamente esto.
>
> Nota útil: `temperatura_media_c` tiene SMD ≈ 0,00 — **no** predice quién recibió nevera, pero más adelante
> veremos que sí determina **cuánto sirve** la nevera. Es una variable de heterogeneidad pura.
""")

code(r"""
# ----------------------------- 1.5 Donde parece servir mas una nevera -----------------------------
# Comparamos ventas con/sin nevera dentro de grupos homogeneos: una primera pista de heterogeneidad.
fig, ax = plt.subplots(1, 3, figsize=(14, 4))

df['_temp_bin'] = pd.cut(df.temperatura_media_c, [0,16,20,24,28,40],
                         labels=['<16°','16-20°','20-24°','24-28°','>28°'])
g = df.groupby(['_temp_bin','nevera_femsa'], observed=True)['ventas_femsa_cop_mes'].mean().unstack()/1e6
g.plot(kind='bar', ax=ax[0], color=[C_SIN, C_CON], width=.8)
ax[0].set(title='Ventas por temperatura', xlabel='temperatura media', ylabel='MM COP / mes')
ax[0].legend(['sin nevera','con nevera'], fontsize=8); ax[0].tick_params(axis='x', rotation=0)

df['_traf_bin'] = pd.qcut(df.clientes_prom_dia, 5, labels=['Q1','Q2','Q3','Q4','Q5'])
g = df.groupby(['_traf_bin','nevera_femsa'], observed=True)['ventas_femsa_cop_mes'].mean().unstack()/1e6
g.plot(kind='bar', ax=ax[1], color=[C_SIN, C_CON], width=.8)
ax[1].set(title='Ventas por tráfico (quintiles)', xlabel='clientes/día', ylabel='')
ax[1].legend(['sin nevera','con nevera'], fontsize=8); ax[1].tick_params(axis='x', rotation=0)

g = (df.groupby(['region','nevera_femsa'])['ventas_femsa_cop_mes'].mean().unstack()/1e6)
g['brecha'] = g[1] - g[0]
g = g.sort_values('brecha')
ax[2].barh(g.index, g.brecha, color=C_ML)
ax[2].set(title='Brecha de ventas con/sin nevera por región', xlabel='MM COP / mes')
plt.tight_layout(); plt.show()

print('Brecha de ventas (con − sin nevera) por región, en COP/mes:')
print((g.brecha*1e6).round(0).sort_values(ascending=False).to_string())
print('\nTemperatura media por región:')
print(df.groupby('region').temperatura_media_c.mean().round(1).sort_values(ascending=False).to_string())
df.drop(columns=['_temp_bin','_traf_bin'], inplace=True)
""")

md(r"""
> **Hallazgo 4 — el calor y el tráfico mandan.** La brecha de ventas entre tiendas con y sin nevera crece
> fuertemente con la temperatura y con el tráfico. Caribe (≈ 28 °C de media) muestra la brecha más grande y
> Eje Cafetero la más pequeña. Esto es intuitivo —una bebida fría vale más donde hace calor y donde pasa
> mucha gente— y anticipa el resultado del módulo 4: **el efecto es heterogéneo**, así que la lista de
> 1.000 tiendas no debe ser simplemente "las más grandes".
>
> Ojo: estas brechas todavía están contaminadas por el sesgo de selección. Son una pista, no una estimación.
""")

code(r"""
# ----------------------------- 1.6 Tiendas elegibles -----------------------------
df['elegible'] = (df.nevera_femsa == 0) & ~((df.nevera_postobon == 1) & (df.area_m2 < AREA_MIN_SI_POSTOBON))

n_sin   = int((df.nevera_femsa == 0).sum())
n_excl  = int(((df.nevera_femsa == 0) & (df.nevera_postobon == 1) & (df.area_m2 < AREA_MIN_SI_POSTOBON)).sum())
n_elig  = int(df.elegible.sum())
print('Embudo de elegibilidad')
print(f'  Tiendas en la base                         {len(df):>7,}')
print(f'  Con nevera FEMSA (no elegibles)           -{int(df.nevera_femsa.sum()):>7,}')
print(f'  Sin nevera FEMSA                           {n_sin:>7,}')
print(f'  Nevera Postobón y < 12 m² (no cabe otra)  -{n_excl:>7,}')
print(f'  ELEGIBLES                                  {n_elig:>7,}')
print(f'\nSe instalan {N_NEVERAS:,} neveras => solo el {N_NEVERAS/n_elig:.1%} de las elegibles la recibe.')
print('La restricción es fuerte: hay que ordenar bien, no solo acertar el signo.\n')

E = df[df.elegible]
print('Perfil de las elegibles frente al resto de la base:')
perfil = pd.DataFrame({'elegibles': E[comp_vars[:12]].mean(), 'toda_la_base': df[comp_vars[:12]].mean()})
print(perfil.round(2).to_string())

print(f'\nTasa de cambio de proveedor en los próximos 6 meses: {df.cambio_proveedor_principal_6m.mean():.2%}')
print(f'  entre elegibles: {E.cambio_proveedor_principal_6m.mean():.2%}')
print('  => clase muy desbalanceada; el módulo 5 lo trata explícitamente.')
""")

md(r"""
> **Hallazgo 5 — hay 12.700 tiendas elegibles para 1.000 neveras.** Solo el 7,9 % de las candidatas recibe
> nevera. Con esa restricción, lo que decide la ganancia no es acertar el promedio del efecto sino
> **ordenar bien** las 12.700 tiendas. Un modelo que estime bien el efecto promedio pero ordene mal
> desperdicia dinero.
>
> Además, las elegibles son en promedio más pequeñas que las tiendas ya atendidas (885.000 vs 1.629.000 COP
> de venta mensual), así que no podemos extrapolar sobre ellas el efecto medido en las grandes sin cuidado.
""")

