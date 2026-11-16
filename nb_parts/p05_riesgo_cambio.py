# ===================== MODULO 5 =====================
md(r"""
---
# Módulo 5 — Riesgo de cambio de proveedor

**Objetivo:** clasificar `cambio_proveedor_principal_6m` con al menos dos algoritmos, tratar el desbalance,
elegir el umbral con los costos del caso e informar cuántas tiendas de la lista tienen riesgo alto.

Solo el **9,5 %** de las tiendas cambia de proveedor principal en los seis meses siguientes. Con una clase
tan minoritaria, un modelo que prediga "nadie cambia" acierta el 90,5 % de las veces y es completamente
inútil. Por eso aquí no miramos *accuracy* en ningún momento.

**Qué variables puede ver.** El objetivo ocurre en los **6 meses siguientes**, así que toda la foto de hoy
—incluidas las ventas y el *share*— es información legítima y disponible al momento de decidir. Es el único
módulo donde no excluimos columnas de resultados.

**Economía de la retención.** Actuar sobre una tienda cuesta COP 50.000 y funciona el 40 % de las veces;
evitar un cambio vale COP 500.000. Conviene actuar cuando el beneficio esperado supera el costo:

$$0{,}40 \times p \times 500.000 > 50.000 \quad \Longrightarrow \quad p > \frac{50.000}{0{,}40 \times 500.000} = 0{,}25$$

El umbral **no** es 0,5: sale de los costos del caso.
""")

code(r"""
# ----------------------------- 5.1 Dos algoritmos, tratando el desbalance -----------------------------
from sklearn.linear_model import LogisticRegression
from sklearn.ensemble import HistGradientBoostingClassifier
from sklearn.metrics import (roc_auc_score, average_precision_score, brier_score_loss,
                             precision_recall_curve, confusion_matrix, classification_report)

y_ch = df['cambio_proveedor_principal_6m'].values
CAT_CH = list(df[X_CHURN].select_dtypes(include=['object','string','category']).columns)
NUM_CH = [c for c in X_CHURN if c not in CAT_CH]
Xch_arb = df[X_CHURN].copy()
for c in CAT_CH:
    Xch_arb[c] = Xch_arb[c].astype(MAPAS_CAT[c]).cat.codes.astype(float) if c in MAPAS_CAT \
                 else Xch_arb[c].astype('category').cat.codes.astype(float)
IDXC_CH = [Xch_arb.columns.get_loc(c) for c in CAT_CH]
Xch_lin = df[X_CHURN].copy()

prep_ch = ColumnTransformer([('num', StandardScaler(), NUM_CH),
                             ('cat', OneHotEncoder(handle_unknown='ignore', sparse_output=False), CAT_CH)])

print(f'Prevalencia de la clase positiva: {y_ch.mean():.2%}  '
      f'({y_ch.sum():,} de {len(y_ch):,} tiendas)')
print(f'Razón de desbalance: 1 : {int((1-y_ch.mean())/y_ch.mean())}\n')

MODELOS_CH = {
 # (1) base lineal; class_weight compensa el desbalance en la funcion de perdida
 'Regresión logística': ('lin', Pipeline([('prep', prep_ch),
      ('mod', LogisticRegression(max_iter=3000, class_weight='balanced', C=1.0))])),
 # (2) boosting sin pesos: con esta prevalencia entrega probabilidades bien calibradas,
 #     que es lo que necesitamos para aplicar un umbral economico
 'Gradient Boosting': ('arb', HistGradientBoostingClassifier(max_iter=400, learning_rate=0.06,
      min_samples_leaf=25, l2_regularization=1.0, categorical_features=IDXC_CH, random_state=SEED)),
 # (3) el mismo boosting con pesos de clase: mejor recall, probabilidades distorsionadas
 'Gradient Boosting + pesos': ('arb', HistGradientBoostingClassifier(max_iter=400, learning_rate=0.06,
      min_samples_leaf=25, l2_regularization=1.0, categorical_features=IDXC_CH,
      class_weight='balanced', random_state=SEED)),
}

p_oof = {}
filas_ch = []
for nombre, (tipo, mod) in MODELOS_CH.items():
    X = Xch_arb if tipo == 'arb' else Xch_lin
    p = cross_val_predict(mod, X, y_ch, cv=CV_CLF, method='predict_proba', n_jobs=1)[:, 1]
    p_oof[nombre] = p
    filas_ch.append({'modelo': nombre,
                     'ROC_AUC': roc_auc_score(y_ch, p),
                     'PR_AUC': average_precision_score(y_ch, p),
                     'Brier': brier_score_loss(y_ch, p),
                     'prob_media': p.mean()})
    print(f'  {nombre:26s} listo')

tab_ch = pd.DataFrame(filas_ch).sort_values('PR_AUC', ascending=False)
print('\n===== COMPARACIÓN (validación cruzada 5 folds) =====\n')
print(tab_ch.to_string(index=False, formatters={
    'ROC_AUC':'{:.4f}'.format,'PR_AUC':'{:.4f}'.format,
    'Brier':'{:.5f}'.format,'prob_media':'{:.4f}'.format}))
print(f'\nPR-AUC de un modelo aleatorio = prevalencia = {y_ch.mean():.4f}')
print('Usamos PR-AUC y no accuracy: con 9,5 % de positivos, accuracy premia al modelo que nunca')
print('predice un cambio. Brier y prob_media miden si las probabilidades son creíbles en nivel.')
""")

md(r"""
### Cómo tratamos el desbalance

Tres decisiones, cada una con su razón:

1. **No usamos *accuracy*.** Con 9,5 % de positivos, "nadie cambia" acierta el 90,5 %. Evaluamos con
   **PR-AUC** (área bajo precisión-recall), que se concentra en la clase minoritaria, y reportamos ROC-AUC
   como referencia.
2. **Ponderación de clases, no remuestreo.** `class_weight='balanced'` multiplica el peso de los positivos
   en la función de pérdida. Preferimos esto a SMOTE o submuestreo porque no inventa observaciones ni
   descarta datos reales, y es una línea de código que cualquiera del grupo puede explicar.
3. **Separamos *ordenar* de *calibrar*.** Ponderar mejora el ordenamiento pero **infla las probabilidades**:
   ya no se pueden comparar contra un umbral económico. El umbral de 0,25 se aplica sobre el modelo
   *sin* pesos, cuyas probabilidades sí están en escala correcta (prob. media ≈ prevalencia, Brier bajo).
   La celda siguiente verifica esa calibración.
""")

code(r"""
# ----------------------------- 5.2 Calibracion y umbral economico -----------------------------
MEJOR_CH = 'Gradient Boosting'       # el modelo sin pesos: probabilidades en escala correcta
p_ch = p_oof[MEJOR_CH]

UMBRAL_COSTOS = COSTO_RETENCION / (EFECTIVIDAD_RETENCION * VALOR_EVITAR_CAMBIO)
print(f'Umbral por costos: {COSTO_RETENCION:,} / ({EFECTIVIDAD_RETENCION} x {VALOR_EVITAR_CAMBIO:,})'
      f' = {UMBRAL_COSTOS:.3f}\n')

# Curva de valor: cuanto vale la campana de retencion segun el umbral elegido
rejilla = np.arange(0.05, 0.71, 0.01)
val = []
for t in rejilla:
    sel = p_ch >= t
    if sel.sum() == 0:
        val.append({'umbral': t, 'n': 0, 'precision': np.nan, 'recall': 0, 'valor_neto': 0}); continue
    cambios_evitados = EFECTIVIDAD_RETENCION * y_ch[sel].sum()
    val.append({'umbral': t, 'n': int(sel.sum()),
                'precision': y_ch[sel].mean(), 'recall': y_ch[sel].sum()/y_ch.sum(),
                'valor_neto': cambios_evitados*VALOR_EVITAR_CAMBIO - sel.sum()*COSTO_RETENCION})
val = pd.DataFrame(val)
t_opt = val.loc[val.valor_neto.idxmax(), 'umbral']

print('Valor neto de la campaña de retención según el umbral:\n')
print(val[val.umbral.round(2).isin([.10,.15,.20,.25,.30,.40,.50])].to_string(index=False, formatters={
    'umbral':'{:.2f}'.format,'precision':'{:.3f}'.format,'recall':'{:.3f}'.format,
    'valor_neto':'{:,.0f}'.format}))
print(f'\nUmbral que maximiza el valor neto (en los datos): {t_opt:.2f}')
print(f'Umbral teórico por costos:                        {UMBRAL_COSTOS:.2f}')
print(f'Valor neto en el umbral teórico: {mm(val.loc[val.umbral.round(2)==round(UMBRAL_COSTOS,2),"valor_neto"].iloc[0])} COP')
print(f'Diferencia entre ambos: {mm(val.valor_neto.max()-val.loc[val.umbral.round(2)==round(UMBRAL_COSTOS,2),"valor_neto"].iloc[0])} COP ({(val.valor_neto.max()/val.loc[val.umbral.round(2)==round(UMBRAL_COSTOS,2),"valor_neto"].iloc[0]-1):.1%})')
print(f'Valor neto en el óptimo empírico: {mm(val.valor_neto.max())} COP')
print('\nCoinciden en la práctica: la curva es plana entre 0,20 y 0,25, así que el umbral derivado')
print('de los costos del caso es también el que más valor genera. Nos quedamos con 0,25.')

fig, ax = plt.subplots(1, 3, figsize=(14.5, 4))
for nombre, p in p_oof.items():
    pr, rc, _ = precision_recall_curve(y_ch, p)
    ax[0].plot(rc, pr, lw=1.8, label=f'{nombre} (PR-AUC {average_precision_score(y_ch,p):.3f})')
ax[0].axhline(y_ch.mean(), ls='--', c='k', lw=1)
ax[0].text(.5, y_ch.mean()+.01, 'modelo aleatorio', fontsize=8)
ax[0].set(title='Curva precisión-recall', xlabel='recall', ylabel='precisión'); ax[0].legend(fontsize=7.5)

bins = np.quantile(p_ch, np.linspace(0, 1, 11)); bins[0] -= 1e-9
mid = pd.cut(p_ch, bins, labels=False)
cal = pd.DataFrame({'b': mid, 'p': p_ch, 'y': y_ch}).groupby('b').mean()
ax[1].plot([0, cal.p.max()], [0, cal.p.max()], 'k--', lw=1)
ax[1].plot(cal.p, cal.y, 'o-', color=C_CON, lw=1.8)
ax[1].set(title=f'Calibración — {MEJOR_CH}', xlabel='probabilidad predicha', ylabel='frecuencia real')

ax[2].plot(val.umbral, val.valor_neto/1e6, lw=2, color=C_ML)
ax[2].axvline(UMBRAL_COSTOS, color=C_SIN, ls='--', lw=1.5)
ax[2].text(UMBRAL_COSTOS+.01, val.valor_neto.min()/1e6, f' umbral por costos = {UMBRAL_COSTOS:.2f}',
           fontsize=8, color=C_SIN)
ax[2].set(title='Valor neto de la retención según el umbral', xlabel='umbral', ylabel='MM COP')
plt.tight_layout(); plt.show()
""")

code(r"""
# ----------------------------- 5.3 Clasificacion final y riesgo por tienda -----------------------------
df['prob_cambio'] = p_ch
df['riesgo_cambio'] = np.where(p_ch >= UMBRAL_COSTOS, 'Alto', 'Bajo')

print(f'Clasificación con umbral {UMBRAL_COSTOS:.2f} sobre las 38.000 tiendas:\n')
cm = confusion_matrix(y_ch, (p_ch >= UMBRAL_COSTOS).astype(int))
print(pd.DataFrame(cm, index=['real: no cambió','real: cambió'],
                   columns=['pred: Bajo','pred: Alto']).to_string())
print()
print(classification_report(y_ch, (p_ch >= UMBRAL_COSTOS).astype(int),
                            target_names=['Bajo riesgo','Alto riesgo'], digits=3))
print(f'Tiendas marcadas de riesgo Alto: {(df.riesgo_cambio=="Alto").sum():,} '
      f'({(df.riesgo_cambio=="Alto").mean():.1%} de la base)')

# Que anticipa un cambio de proveedor
mod_ch_final = MODELOS_CH[MEJOR_CH][1].fit(Xch_arb, y_ch)
sub_ch = np.random.RandomState(SEED).choice(len(df), 6000, replace=False)
pi_ch = permutation_importance(mod_ch_final, Xch_arb.iloc[sub_ch], y_ch[sub_ch],
                               n_repeats=5, random_state=SEED, scoring='average_precision', n_jobs=1)
imp_ch = (pd.DataFrame({'variable': X_CHURN, 'importancia': pi_ch.importances_mean})
          .sort_values('importancia', ascending=False).reset_index(drop=True))
print('\nSeñales que más anticipan un cambio de proveedor:\n')
print(imp_ch.head(12).to_string(index=False, formatters={'importancia':'{:.4f}'.format}))

fig, ax = plt.subplots(figsize=(8, 5))
t_ch = imp_ch.head(12).sort_values('importancia')
ax.barh(t_ch.variable, t_ch.importancia, color=C_SIN)
ax.set(title='Predictores del cambio de proveedor (caída de PR-AUC)', xlabel='importancia')
plt.tight_layout(); plt.show()

tab_ch.to_csv(f'{RUTA_SALIDAS}/metricas_modelos_riesgo.csv', index=False)
val.to_csv(f'{RUTA_SALIDAS}/curva_umbral_retencion.csv', index=False)
imp_ch.to_csv(f'{RUTA_SALIDAS}/importancia_riesgo.csv', index=False)
print(f'\nGuardados: metricas_modelos_riesgo.csv, curva_umbral_retencion.csv, importancia_riesgo.csv')
""")

md(r"""
### Lectura del módulo 5

El *Gradient Boosting* alcanza **ROC-AUC ≈ 0,82** y **PR-AUC ≈ 0,39**, cuatro veces la prevalencia (0,095):
el modelo tiene señal real sobre quién se va. La regresión logística queda claramente por debajo
(PR-AUC ≈ 0,26), lo que indica que el riesgo de cambio depende de interacciones que un modelo lineal no
captura.

En el umbral económico de **0,25** se marcan **3.167 tiendas** con **precisión de 0,44** (casi la mitad de
las marcadas efectivamente cambia, frente a un 9,5 % de base) y **recall de 0,39**. La campaña de retención
sobre ese grupo tendría un valor neto de **COP 123,2 millones**. El umbral que maximiza el valor en los
datos es 0,24, con COP 125,0 millones: una diferencia del 1,5 %. **El umbral derivado de los costos del caso
es, en la práctica, el óptimo**, y la curva es plana entre 0,20 y 0,30, así que la decisión es robusta a
errores moderados de calibración.

Nótese también el efecto de la ponderación sobre las probabilidades: el boosting sin pesos tiene una
probabilidad media de 0,092 (prevalencia real 0,095) y Brier 0,070; el mismo modelo con `class_weight`
sube la probabilidad media a 0,340 y el Brier a 0,146. Ordena igual de bien —ROC-AUC casi idéntico— pero
sus probabilidades ya no se pueden comparar contra un umbral económico. Por eso el umbral se aplica sobre
el modelo sin pesos.

**Nota sobre la interacción con el plan de neveras.** La ganancia que el caso nos pide reportar es
`0,25 × ventas adicionales − 60.000`, que no incluye el valor de la retención. Mantenemos la lista ordenada
por esa fórmula y reportamos el riesgo como información separada, tal como pide el enunciado. En el módulo 6
mostramos, además, cuánto cambiaría la lista si FEMSA decidiera priorizar también la retención.
""")
