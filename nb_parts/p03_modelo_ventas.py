# ===================== MODULO 3 =====================
md(r"""
---
# Módulo 3 — Modelo de ventas

**Objetivo:** predecir `ventas_femsa_cop_mes` con al menos tres algoritmos, incluido un modelo base lineal,
compararlos con validación cruzada e interpretar las variables más importantes.

**Qué pregunta responde este modelo:** *¿cuánto vende una tienda, dadas sus características actuales?*
Es un modelo **descriptivo/predictivo**, no causal: aquí sí puede ver las variables de nevera, porque
describe la realidad tal como está. No lo usamos para decidir dónde poner neveras —para eso está el
módulo 4— pero nos sirve para tres cosas:

1. Verificar que las variables de la base realmente explican las ventas (si no, no habría señal).
2. Saber qué variables mueven las ventas, como insumo del tablero.
3. Fijar el techo de desempeño predictivo contra el cual comparar los modelos del módulo 4.

**Objetivo en logaritmo.** Entrenamos sobre `log(ventas)` por el Hallazgo 1: en niveles, el 1 % de tiendas
más grandes domina el error cuadrático y el modelo se vuelve malo para el 99 % restante. Reportamos las
métricas en las dos escalas: en log (para comparar modelos) y en COP (para interpretar el error).
""")

code(r"""
# ----------------------------- 3.1 Preparacion de las matrices -----------------------------
from sklearn.linear_model import RidgeCV
from sklearn.tree import DecisionTreeRegressor
from sklearn.ensemble import RandomForestRegressor, HistGradientBoostingRegressor
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import StandardScaler, OneHotEncoder
from sklearn.compose import ColumnTransformer
from sklearn.metrics import r2_score, mean_absolute_error, root_mean_squared_error
from sklearn.inspection import permutation_importance

y_log = np.log(df['ventas_femsa_cop_mes'].values)        # objetivo en logaritmo
y_cop = df['ventas_femsa_cop_mes'].values.astype(float)  # objetivo en COP

Xv_arb, IDXC = codificar_arboles(df, X_VENTAS)   # matriz para arboles
Xv_lin = df[X_VENTAS].copy()                     # DataFrame crudo para el pipeline lineal

tr, te = idx_train, idx_test
print(f'X_VENTAS: {len(X_VENTAS)} variables | train {len(tr):,} | test {len(te):,}')

# Preprocesador del modelo lineal: estandarizar numericas + one-hot a categoricas
prep_lineal = ColumnTransformer([
    ('num', StandardScaler(), NUMERICAS),
    ('cat', OneHotEncoder(handle_unknown='ignore', sparse_output=False), CATEGORICAS)])

MODELOS = {
 'Lineal (Ridge)'      : ('lin', Pipeline([('prep', prep_lineal),
                                           ('mod', RidgeCV(alphas=np.logspace(-2, 3, 20)))])),
 'Árbol de decisión'   : ('arb', DecisionTreeRegressor(max_depth=10, min_samples_leaf=50, random_state=SEED)),
 'Random Forest'       : ('arb', RandomForestRegressor(n_estimators=200, min_samples_leaf=5,
                                                      max_features=0.4, random_state=SEED, n_jobs=-1)),
 'Gradient Boosting'   : ('arb', HistGradientBoostingRegressor(max_iter=400, learning_rate=0.06,
                                                      max_leaf_nodes=31, min_samples_leaf=20,
                                                      l2_regularization=1.0,
                                                      categorical_features=IDXC, random_state=SEED)),
}
print('Modelos a comparar:', ', '.join(MODELOS))
""")

code(r"""
# ----------------------------- 3.2 Validacion cruzada 5-fold sobre TRAIN -----------------------------
# Comparamos los modelos con la misma particion de folds (misma semilla) para que la comparacion sea valida.
filas = []
pred_oof = {}
for nombre, (tipo, modelo) in MODELOS.items():
    X = Xv_arb if tipo == 'arb' else Xv_lin
    cv_res = cross_validate(modelo, X.iloc[tr], y_log[tr], cv=CV_REG,
                            scoring=['r2', 'neg_root_mean_squared_error', 'neg_mean_absolute_error'],
                            n_jobs=1, return_train_score=True)
    # predicciones fuera de fold, para graficos y para el error en COP
    oof = cross_val_predict(modelo, X.iloc[tr], y_log[tr], cv=CV_REG, n_jobs=1)
    pred_oof[nombre] = oof
    smear = np.exp(y_log[tr] - oof).mean()              # correccion de Duan al volver a COP
    filas.append({'modelo': nombre,
                  'R2_cv': cv_res['test_r2'].mean(), 'R2_sd': cv_res['test_r2'].std(),
                  'R2_train': cv_res['train_r2'].mean(),
                  'RMSE_log': -cv_res['test_neg_root_mean_squared_error'].mean(),
                  'MAE_log': -cv_res['test_neg_mean_absolute_error'].mean(),
                  'MAE_COP': mean_absolute_error(y_cop[tr], np.exp(oof) * smear),
                  'MAPE_%': (np.abs(np.exp(oof)*smear - y_cop[tr]) / y_cop[tr]).mean() * 100})
    print(f'  {nombre:22s} listo  (R2 cv = {cv_res["test_r2"].mean():.4f})')

comp = pd.DataFrame(filas).sort_values('R2_cv', ascending=False).reset_index(drop=True)
print('\n===== COMPARACIÓN POR VALIDACIÓN CRUZADA (5 folds, sobre train) =====\n')
print(comp.to_string(index=False, formatters={
    'R2_cv':'{:.4f}'.format, 'R2_sd':'{:.4f}'.format, 'R2_train':'{:.4f}'.format,
    'RMSE_log':'{:.4f}'.format, 'MAE_log':'{:.4f}'.format,
    'MAE_COP':'{:,.0f}'.format, 'MAPE_%':'{:.1f}'.format}))
""")

code(r"""
# ----------------------------- 3.3 Grafico de la comparacion -----------------------------
fig, ax = plt.subplots(1, 2, figsize=(13, 4.2))
o = comp.sort_values('R2_cv')
col = [C_ML if m == comp.modelo.iloc[0] else '#9aa0a6' for m in o.modelo]
ax[0].barh(o.modelo, o.R2_cv, xerr=o.R2_sd, color=col, capsize=3)
ax[0].set(title='R² en validación cruzada (escala log)', xlabel='R²', xlim=(0, .8))
for i, (v, s) in enumerate(zip(o.R2_cv, o.R2_sd)):
    ax[0].text(v + s + .01, i, f'{v:.3f}', va='center', fontsize=8)

mejor = comp.modelo.iloc[0]
ax[1].scatter(y_log[tr], pred_oof[mejor], s=3, alpha=.08, color=C_CON)
lims = [y_log[tr].min(), y_log[tr].max()]
ax[1].plot(lims, lims, 'k--', lw=1)
ax[1].set(title=f'{mejor}: predicho vs real (fuera de fold)',
          xlabel='log(ventas) real', ylabel='log(ventas) predicho')
plt.tight_layout(); plt.show()

print(f'Mejor modelo por R² de validación cruzada: {mejor}')
print(f'\nSobreajuste (R² train − R² cv):')
for _, r in comp.iterrows():
    print(f'  {r.modelo:22s} {r.R2_train - r.R2_cv:+.4f}')
""")

code(r"""
# ----------------------------- 3.4 Evaluacion final en TEST -----------------------------
# El test no se uso para elegir modelo: es la prueba honesta de desempeno.
res_test = []
MODELO_VENTAS = None
for nombre, (tipo, modelo) in MODELOS.items():
    X = Xv_arb if tipo == 'arb' else Xv_lin
    m = modelo.fit(X.iloc[tr], y_log[tr])
    p = m.predict(X.iloc[te])
    smear = np.exp(y_log[tr] - m.predict(X.iloc[tr])).mean()
    res_test.append({'modelo': nombre,
                     'R2_test': r2_score(y_log[te], p),
                     'RMSE_log_test': root_mean_squared_error(y_log[te], p),
                     'MAE_COP_test': mean_absolute_error(y_cop[te], np.exp(p)*smear)})
    if nombre == mejor:
        MODELO_VENTAS, SMEAR_VENTAS = m, smear

test_tab = pd.DataFrame(res_test).sort_values('R2_test', ascending=False)
print('===== DESEMPEÑO EN TEST (20 % reservado) =====\n')
print(test_tab.to_string(index=False, formatters={
    'R2_test':'{:.4f}'.format, 'RMSE_log_test':'{:.4f}'.format, 'MAE_COP_test':'{:,.0f}'.format}))

mejor_r2 = test_tab.R2_test.iloc[0]
base_r2  = test_tab.loc[test_tab.modelo == 'Lineal (Ridge)', 'R2_test'].iloc[0]
print(f'\nGanancia del mejor modelo sobre el base lineal: {mejor_r2 - base_r2:+.4f} de R²'
      f'  ({(mejor_r2-base_r2)/base_r2:+.1%} relativo)')
""")

code(r"""
# ----------------------------- 3.5 Importancia de variables -----------------------------
# Permutation importance: cuanto empeora el R2 del TEST al barajar cada variable.
# Es comparable entre modelos y no premia a las variables de alta cardinalidad.
sub = np.random.RandomState(SEED).choice(te, size=min(6000, len(te)), replace=False)
pi = permutation_importance(MODELO_VENTAS, Xv_arb.loc[sub], y_log[sub],
                            n_repeats=5, random_state=SEED, scoring='r2', n_jobs=1)
imp = (pd.DataFrame({'variable': X_VENTAS, 'importancia': pi.importances_mean,
                     'sd': pi.importances_std})
         .sort_values('importancia', ascending=False).reset_index(drop=True))

print(f'Importancia por permutación — {mejor} (caída de R² en test)\n')
print(imp.head(18).to_string(index=False, formatters={'importancia':'{:.4f}'.format,'sd':'{:.4f}'.format}))

fig, ax = plt.subplots(figsize=(8, 6))
top = imp.head(18).sort_values('importancia')
colores = [C_CON if 'nevera' in v else C_ML if v in ('temperatura_media_c','clientes_prom_dia') else '#9aa0a6'
           for v in top.variable]
ax.barh(top.variable, top.importancia, xerr=top.sd, color=colores, capsize=2)
ax.set(title=f'Variables más importantes — {mejor}', xlabel='caída de R² al permutar')
plt.tight_layout(); plt.show()
""")

code(r"""
# ----------------------------- 3.6 Interpretacion: coeficientes del modelo lineal -----------------------------
# El modelo lineal en log da una lectura directa: el coeficiente es ~% de cambio en ventas.
lin = MODELOS['Lineal (Ridge)'][1].fit(Xv_lin.iloc[tr], y_log[tr])
nombres = (NUMERICAS + list(lin.named_steps['prep'].named_transformers_['cat']
                            .get_feature_names_out(CATEGORICAS)))
coef = pd.DataFrame({'variable': nombres, 'coef': lin.named_steps['mod'].coef_})
coef['efecto_%'] = (np.exp(coef.coef) - 1) * 100
coef['abs'] = coef.coef.abs()

print('Coeficientes del modelo lineal (variables numéricas estandarizadas:')
print('el efecto es el cambio en ventas al subir 1 desviación estándar)\n')
print(coef[coef.variable.isin(NUMERICAS)].nlargest(12, 'abs')[['variable','coef','efecto_%']]
      .to_string(index=False, formatters={'coef':'{:+.4f}'.format,'efecto_%':'{:+.1f}%'.format}))
print('\nCategóricas con mayor efecto:')
print(coef[~coef.variable.isin(NUMERICAS)].nlargest(8, 'abs')[['variable','coef','efecto_%']]
      .to_string(index=False, formatters={'coef':'{:+.4f}'.format,'efecto_%':'{:+.1f}%'.format}))

coef.drop(columns='abs').to_csv(f'{RUTA_SALIDAS}/coeficientes_modelo_lineal.csv', index=False)
imp.to_csv(f'{RUTA_SALIDAS}/importancia_variables.csv', index=False)
comp.merge(test_tab, on='modelo').to_csv(f'{RUTA_SALIDAS}/metricas_modelos_ventas.csv', index=False)
print(f'\nGuardados: importancia_variables.csv, metricas_modelos_ventas.csv, coeficientes_modelo_lineal.csv')
""")

md(r"""
### Lectura del módulo 3

**Comparación de modelos.** En test, el modelo base lineal explica el **66,1 %** de la varianza de
`log(ventas)`, el Random Forest el **69,1 %** y el *Gradient Boosting* el **70,6 %**. La mejora del boosting
sobre el lineal es real pero modesta (**+4,5 puntos de R²**, +6,8 % relativo): **la relación entre las
características de la tienda y sus ventas es en buena medida multiplicativa y suave**, que es precisamente
lo que un modelo lineal en logaritmo captura bien. El árbol de decisión individual queda incluso por debajo
del lineal (65,4 %), lo que confirma que la ganancia del bosque y del boosting viene de promediar muchos
árboles, no de la no linealidad por sí sola.

Vale la pena mirar la columna de sobreajuste: el Random Forest alcanza R² = 0,88 en entrenamiento contra
0,70 en validación cruzada (una brecha de 18 puntos), mientras el boosting se queda en 4,5 puntos y el
lineal en 0,2. El bosque memoriza; por eso lo descartamos aunque su desempeño en test sea aceptable.

El error típico es grande en términos absolutos (MAE ≈ COP 438.000) porque las ventas van de 15.000 a 42
millones. En términos relativos el mejor modelo se equivoca alrededor de un **41 %** en una tienda típica:
suficiente para ordenar tiendas, insuficiente para prometer un pronóstico puntual.

**Variables importantes.** Las que más pesan son las de **escala y tráfico** (`clientes_prom_dia`,
`n_referencias_total`, `area_m2`, `poblacion_500m`, `num_empleados`), seguidas por **temperatura** y por las
**variables de nevera**. El coeficiente lineal de `nevera_femsa` es positivo y grande, pero —y esto es
central para el proyecto— **ese coeficiente no es el efecto causal de instalar una nevera**: está capturando
también que FEMSA puso sus neveras en las mejores tiendas (Hallazgo 3). Interpretarlo como efecto sería
exactamente el error que el módulo 4 corrige.

**Por qué este modelo no decide la lista.** Un modelo de ventas responde "¿cuánto vende esta tienda?". La
pregunta de negocio es "¿cuánto *más* vendería con una nevera?". Son preguntas distintas y la segunda no se
contesta con la primera. Si usáramos este modelo para elegir, escogeríamos las tiendas que más venden, que es
una de las dos reglas simples que el módulo 6 derrota.
""")
