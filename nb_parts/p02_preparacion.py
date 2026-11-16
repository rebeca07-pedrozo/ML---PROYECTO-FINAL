# ===================== MODULO 2 =====================
md(r"""
---
# Módulo 2 — Preparación de datos y control de fuga

Aquí se decide **qué variables puede ver cada modelo**. Es el módulo que más silenciosamente arruina un
proyecto: si dejamos entrar una columna que contiene la respuesta, el modelo saca R² = 1 y no sirve para nada.

Distinguimos **tres** conjuntos de variables, porque los tres modelos del proyecto responden preguntas
distintas y por lo tanto tienen derecho a ver cosas distintas:

| Conjunto | Para qué | Qué excluye |
|---|---|---|
| `X_VENTAS` | Módulo 3: predecir `ventas_femsa_cop_mes` | Todo lo que *contiene* la respuesta |
| `X_CAUSAL` | Módulo 4: efecto de la nevera | Lo anterior **+** todo lo posterior al tratamiento |
| `X_CHURN`  | Módulo 5: predecir cambio de proveedor | Nada (todo es previo a la ventana de 6 meses) |
""")

code(r"""
# ----------------------------- 2.1 Fuga directa: verificar las identidades -----------------------------
# No basta sospechar: comprobamos numericamente que ciertas columnas SON la respuesta.
SKU_FEMSA = ['cocacola_400ml','cocacola_1500ml','cocacola_ret_1250ml','cocacola_sinazucar_400ml',
             'quatro_400ml','sprite_400ml','brisa_600ml','delvalle_fresh_400ml','powerade_500ml','fuze_tea_400ml']
SKU_POSTOBON = ['colombiana_400ml','manzana_400ml','manzana_1500ml','pepsi_400ml','sevenup_400ml',
                'cristal_600ml','hit_500ml','mr_tea_500ml','squash_500ml','speedmax_250ml']

identidades = {
 'sum(cop_<sku FEMSA>) == ventas_femsa_cop_mes':
    np.allclose(df[['cop_'+s for s in SKU_FEMSA]].sum(axis=1), df.ventas_femsa_cop_mes),
 'sum(u_<sku FEMSA>) == unidades_femsa_mes':
    np.allclose(df[['u_'+s for s in SKU_FEMSA]].sum(axis=1), df.unidades_femsa_mes),
 'ventas_femsa + ventas_postobon == ventas_bebidas':
    np.allclose(df.ventas_femsa_cop_mes + df.ventas_postobon_cop_mes, df.ventas_bebidas_cop_mes),
 'ventas_bebidas + ventas_otras == ventas_totales':
    np.allclose(df.ventas_bebidas_cop_mes + df.ventas_otras_categorias_cop_mes, df.ventas_totales_tienda_cop_mes),
 'share_femsa_valor == ventas_femsa / ventas_bebidas':
    np.allclose(df.share_femsa_valor, df.ventas_femsa_cop_mes/df.ventas_bebidas_cop_mes, atol=1e-3),
}
print('Identidades contables verificadas sobre las 38.000 filas:\n')
for k, v in identidades.items():
    print(('  CONFIRMADA  ' if v else '  no se cumple') + f' | {k}')
print('\nConclusión: las columnas u_*, cop_* y los agregados de ventas no son "variables predictoras":')
print('son la respuesta escrita de otra forma. Usarlas daria R2 ~ 1 y un modelo inservible.')
""")

code(r"""
# ----------------------------- 2.2 Definicion de los conjuntos de variables -----------------------------
COLS_SKU = [c for c in df.columns if c.startswith(('u_','cop_'))]          # 40 columnas de SKU

# (a) Fuga directa del objetivo de ventas: contiene ventas_femsa por construccion
FUGA_DIRECTA = COLS_SKU + ['unidades_femsa_mes','ventas_femsa_cop_mes','ventas_bebidas_cop_mes',
                           'share_femsa_valor','n_skus_activos_femsa','ventas_totales_tienda_cop_mes',
                           'ticket_promedio_cop','ventas_por_m2_cop','peso_bebidas_en_ventas',
                           'proveedor_principal']

# (b) Resultados del MISMO mes que no contienen la respuesta pero son simultaneos a ella.
#     No son causa de las ventas de FEMSA: son consecuencia de las mismas decisiones de la tienda.
#     Incluirlos infla el R2 sin aportar nada accionable y contamina el analisis causal.
RESULTADOS_SIMULTANEOS = ['unidades_postobon_mes','ventas_postobon_cop_mes','n_skus_activos_postobon',
                          'ventas_otras_categorias_cop_mes']

# (c) Variables que describen la nevera FEMSA: son el tratamiento o funcion directa de el.
#     En el modulo 4 deben salir TODAS, o el modelo "explicaria" el efecto con ellas mismas.
COLS_TRATAMIENTO = ['nevera_femsa','num_neveras_femsa','puertas_nevera_femsa',
                    'antiguedad_nevera_femsa_anios','nevera_femsa_operativa','presencia_neveras']

# (d) Identificadores y objetivos
NO_PREDICTORAS = ['id_tienda','cambio_proveedor_principal_6m','elegible']

# --- Conjunto para el MODULO 3 (modelo de ventas) ---
# Si incluye las variables de nevera: describe la realidad actual (cuanto vende una tienda tal como esta).
X_VENTAS = [c for c in df.columns if c not in FUGA_DIRECTA + RESULTADOS_SIMULTANEOS + NO_PREDICTORAS]

# --- Conjunto para el MODULO 4 (efecto causal) ---
# Solo variables PREVIAS o ajenas a la decision de instalar la nevera FEMSA.
X_CAUSAL = [c for c in X_VENTAS if c not in COLS_TRATAMIENTO]

# --- Conjunto para el MODULO 5 (riesgo de cambio) ---
# El objetivo ocurre en los 6 meses SIGUIENTES: toda la foto de hoy es informacion legitima.
X_CHURN = [c for c in df.columns if c not in ['id_tienda','cambio_proveedor_principal_6m','elegible']]

print(f'Columnas totales en la base         : {df.shape[1]}')
print(f'  excluidas por fuga directa        : {len(FUGA_DIRECTA)}')
print(f'  excluidas por simultaneidad       : {len(RESULTADOS_SIMULTANEOS)}')
print(f'  identificadores y objetivos       : {len(NO_PREDICTORAS)}')
print()
print(f'X_VENTAS (modulo 3)  : {len(X_VENTAS):>3} variables')
print(f'X_CAUSAL (modulo 4)  : {len(X_CAUSAL):>3} variables  (= X_VENTAS - {len(COLS_TRATAMIENTO)} de nevera FEMSA)')
print(f'X_CHURN  (modulo 5)  : {len(X_CHURN):>3} variables')
print('\nVariables de X_CAUSAL:')
print(textwrap.fill(', '.join(X_CAUSAL), 100))
""")

md(r"""
### Por qué cada exclusión

**(a) Fuga directa — 50 columnas.** `ventas_femsa_cop_mes` es exactamente la suma de las 10 columnas
`cop_<sku FEMSA>`, verificado arriba. Por la misma vía entran `ventas_bebidas_cop_mes`,
`ventas_totales_tienda_cop_mes`, `ticket_promedio_cop`, `ventas_por_m2_cop`, `peso_bebidas_en_ventas`,
`share_femsa_valor` y `proveedor_principal`: todas se calculan *usando* la respuesta. Dejar cualquiera de
ellas produce un R² cercano a 1 que no se puede usar para decidir nada, porque para una tienda nueva no
conoceríamos esos valores.

**(b) Resultados simultáneos — 4 columnas.** Las ventas de Postobón del mismo mes no contienen la respuesta,
pero tampoco la *causan*: son el resultado paralelo de las mismas condiciones de la tienda. En el análisis
causal son peores aún: una nevera de FEMSA puede **quitarle** ventas a Postobón, así que
`ventas_postobon_cop_mes` está afectada por el tratamiento. Condicionar sobre una variable afectada por el
tratamiento sesga el efecto estimado (es un *colisionador*). Las excluimos de los dos módulos.

**(c) Variables del tratamiento — 6 columnas.** `num_neveras_femsa`, `puertas_nevera_femsa`,
`antiguedad_nevera_femsa_anios`, `nevera_femsa_operativa` y `presencia_neveras` son funciones determinísticas
de `nevera_femsa`: valen 0 (o "Ninguna"/"Solo Postobón") en todas las tiendas sin nevera. Si el modelo causal
las viera, podría reproducir el tratamiento a partir de ellas y el efecto estimado se volvería incoherente.
Se usan en el módulo 3 (donde solo describimos la realidad) y se excluyen en el módulo 4.

**Lo que sí conservamos en `X_CAUSAL`:** las variables de nevera de **Postobón** y las de nevera propia /
otras marcas. Son competencia por el espacio frío y están determinadas antes de nuestra decisión, así que son
confusores legítimos que *debemos* controlar, no fuga.
""")

code(r"""
# ----------------------------- 2.3 Codificacion -----------------------------
# Dos codificaciones segun la familia de modelo:
#   - arboles (RandomForest, HistGradientBoosting): codigos enteros + declaracion de categoricas
#   - lineales (Ridge): one-hot, porque un codigo entero impondria un orden falso
CATEGORICAS = list(df[X_VENTAS].select_dtypes(include=['object','string','category']).columns)
NUMERICAS   = [c for c in X_VENTAS if c not in CATEGORICAS]
print(f'Categóricas ({len(CATEGORICAS)}): {CATEGORICAS}')
print(f'Numéricas   ({len(NUMERICAS)})')
print('\nCardinalidad de las categóricas:')
for c in CATEGORICAS:
    print(f'  {c:14s} {df[c].nunique():>3} niveles')

# Mapas de categorias fijos (reproducibilidad: el mismo codigo en cualquier corrida)
MAPAS_CAT = {c: pd.CategoricalDtype(categories=sorted(df[c].unique()), ordered=False) for c in CATEGORICAS}

def codificar_arboles(datos, columnas):
    'Devuelve X numerico (codigos enteros) y los indices de las columnas categoricas.'
    X = datos[columnas].copy()
    cats = [c for c in columnas if c in MAPAS_CAT]
    for c in cats:
        X[c] = X[c].astype(MAPAS_CAT[c]).cat.codes.astype(float)
    return X, [X.columns.get_loc(c) for c in cats]

X_arb, IDX_CAT = codificar_arboles(df, X_VENTAS)
print(f'\nMatriz para árboles: {X_arb.shape}, categóricas en posiciones {IDX_CAT}')
print('Sin valores faltantes:', int(X_arb.isna().sum().sum()) == 0)
""")

code(r"""
# ----------------------------- 2.4 Particion de datos -----------------------------
from sklearn.model_selection import train_test_split, KFold, StratifiedKFold, cross_validate, cross_val_predict

# Particion 80/20 estratificada por tratamiento y por tramo de ventas, para que train y test
# tengan la misma mezcla de tiendas grandes/pequenas y con/sin nevera.
estrato_part = (df.nevera_femsa.astype(str) + '_' +
                pd.qcut(df.ventas_femsa_cop_mes, 5, labels=False).astype(str))
idx_train, idx_test = train_test_split(df.index.values, test_size=0.20,
                                       random_state=SEED, stratify=estrato_part)
df['particion'] = np.where(df.index.isin(idx_train), 'train', 'test')

CV_REG = KFold(5, shuffle=True, random_state=SEED)             # para modelos de regresion
CV_CLF = StratifiedKFold(5, shuffle=True, random_state=SEED)   # para clasificacion

print(f'Train: {len(idx_train):,} tiendas   Test: {len(idx_test):,} tiendas')
print('\nComprobación del balance de la partición:')
chk = df.groupby('particion').agg(
    nevera_femsa=('nevera_femsa','mean'),
    ventas_media=('ventas_femsa_cop_mes','mean'),
    elegibles=('elegible','mean'),
    tasa_cambio=('cambio_proveedor_principal_6m','mean'))
print(chk.round(4).to_string())
print('\nValidación cruzada: 5 folds, shuffle, semilla', SEED)
""")

md(r"""
**Nota sobre el uso de la partición.** Para la comparación de modelos del módulo 3 usamos validación cruzada
de 5 *folds* sobre `train` (así cada modelo se evalúa con 5 estimaciones y podemos ver la dispersión) y
reservamos `test` como prueba final de que no sobreajustamos la selección de modelo.

Para el módulo 4 el enfoque es distinto: no hay "respuesta correcta" observable para el efecto causal, así
que no sirve un *hold-out* clásico. Allí usamos **cross-fitting** (muestras cruzadas): cada tienda recibe
predicciones de modelos que nunca la vieron. Se explica en su sección.
""")
