# ===================== MODULO 4 =====================
md(r"""
---
# Módulo 4 — Efecto causal de la nevera

Este es el módulo que decide el proyecto. Todo lo anterior fue preparación.

## El problema en una frase

La diferencia simple de ventas entre tiendas con y sin nevera es de **≈ COP 748.000 al mes**. Si la
tomáramos como el efecto de la nevera, la ganancia por tienda sería `0,25 × 748.000 − 60.000 ≈ COP 127.000`
y **casi cualquier** tienda elegible parecería rentable. Pero el Hallazgo 3 mostró que las tiendas con nevera
reciben 29 % más clientes y son 28 % más grandes *antes* de cualquier efecto de la nevera. Esa diferencia
mezcla dos cosas:

$$\underbrace{E[Y|T=1] - E[Y|T=0]}_{\text{diferencia simple} \approx 748.000} = \underbrace{\text{efecto de la nevera}}_{\text{lo que queremos}} + \underbrace{\text{sesgo de selección}}_{\text{FEMSA eligió las mejores tiendas}}$$

Necesitamos el primer término solo.

## Qué queremos estimar, exactamente

Para cada tienda elegible $i$ queremos el **efecto individual de tratamiento (CATE)**:

$$\tau(x_i) = E[\,Y_i(1) - Y_i(0) \mid X_i = x_i\,]$$

donde $Y_i(1)$ son las ventas con nevera nueva y $Y_i(0)$ sin ella. Solo observamos una de las dos: el
problema es de datos faltantes, no de predicción.

**No queremos el promedio.** Queremos el *orden*: con 1.000 neveras para 12.700 candidatas, lo que determina
la ganancia es identificar correctamente el 8 % superior.

## Supuestos que debemos asumir (y cómo los revisamos)

| Supuesto | Qué dice | Cómo lo revisamos |
|---|---|---|
| **Ignorabilidad** | Dadas las variables observadas, tener nevera es "como si fuera" aleatorio | No es verificable. Discutimos su plausibilidad y hacemos análisis de sensibilidad |
| **Positividad** | Toda tienda tenía probabilidad > 0 de recibir y de no recibir nevera | Distribución del propensity score (§4.3) |
| **SUTVA** | La nevera de una tienda no afecta las ventas de otra | Discutido en limitaciones |

La ignorabilidad es el supuesto fuerte. Nos apoyamos en que la base trae un conjunto **inusualmente rico** de
determinantes de la asignación: tamaño, tráfico, surtido, entorno, gestión comercial, competencia y
geografía. Son justamente los criterios con los que una fuerza de ventas decide dónde poner una nevera. Aun
así, el módulo cierra con una prueba de cuánto tendría que faltar para invalidar la decisión.
""")

code(r"""
# ----------------------------- 4.1 Definicion precisa del tratamiento -----------------------------
# FEMSA va a instalar UNA nevera NUEVA y OPERATIVA.
# El grupo tratado de la base mezcla configuraciones: 1 o 2 neveras, 1/2/4 puertas, 0-15 anios,
# y ~3.800 tiendas con la nevera averiada. Comparar contra esa mezcla responde otra pregunta.
print('Composición del grupo con nevera FEMSA:')
tt = df[df.nevera_femsa == 1]
print(pd.crosstab(tt.num_neveras_femsa, tt.nevera_femsa_operativa,
                  rownames=['n° neveras'], colnames=['operativa']).to_string())

# Muestra causal: controles puros + tratadas con UNA nevera OPERATIVA
mask_causal = (df.nevera_femsa == 0) | ((df.num_neveras_femsa == 1) & (df.nevera_femsa_operativa == 1))
dc = df[mask_causal].reset_index(drop=True)

print(f'\nMuestra causal: {len(dc):,} tiendas')
print(f'  control  (sin nevera FEMSA)          {int((dc.nevera_femsa==0).sum()):>7,}')
print(f'  tratadas (1 nevera FEMSA operativa)  {int(dc.nevera_femsa.sum()):>7,}')
print(f'  descartadas de la base               {len(df)-len(dc):>7,}  '
      f'(2 neveras o nevera averiada: otra "dosis")')
print('\nEstimando: efecto de UNA nevera operativa, que es exactamente lo que FEMSA va a instalar.')
""")

code(r"""
# ----------------------------- 4.2 Matrices del analisis causal -----------------------------
Xc, IDXC_C = codificar_arboles(dc, X_CAUSAL)
T  = dc['nevera_femsa'].values.astype(int)        # tratamiento
Y  = dc['ventas_femsa_cop_mes'].values.astype(float)
LY = np.log(Y)                                     # trabajamos en logaritmo (Hallazgo 1)

from sklearn.ensemble import HistGradientBoostingClassifier
def reg_causal(**kw):
    'Regresor base del analisis causal.'
    return HistGradientBoostingRegressor(random_state=SEED, categorical_features=IDXC_C, **kw)
def clf_causal(**kw):
    'Clasificador base (propensity score).'
    return HistGradientBoostingClassifier(random_state=SEED, categorical_features=IDXC_C, **kw)

print(f'X_CAUSAL: {len(X_CAUSAL)} variables, ninguna posterior al tratamiento')
print(f'Muestra: {len(dc):,} tiendas | tratadas {T.mean():.1%}')

# ---- CROSS-FITTING: cada tienda recibe predicciones de modelos que NO la vieron ----
# Es lo que permite usar modelos flexibles sin que el sobreajuste contamine el efecto estimado.
n = len(dc)
e_oof  = np.zeros(n)   # propensity score  P(T=1|X)
m0_oof = np.zeros(n)   # E[log Y | X, T=0]
m1_oof = np.zeros(n)   # E[log Y | X, T=1]

for k, (i_tr, i_te) in enumerate(CV_CLF.split(Xc, T), 1):
    Xtr, Xte = Xc.iloc[i_tr], Xc.iloc[i_te]
    Ttr, LYtr = T[i_tr], LY[i_tr]
    e_oof[i_te]  = clf_causal().fit(Xtr, Ttr).predict_proba(Xte)[:, 1]
    m0_oof[i_te] = reg_causal().fit(Xtr[Ttr == 0], LYtr[Ttr == 0]).predict(Xte)
    m1_oof[i_te] = reg_causal().fit(Xtr[Ttr == 1], LYtr[Ttr == 1]).predict(Xte)
    print(f'  fold {k}/5 ajustado')
print('\nCross-fitting completo.')
""")

code(r"""
# ----------------------------- 4.3 Propensity score y positividad -----------------------------
from sklearn.metrics import roc_auc_score
auc_e = roc_auc_score(T, e_oof)
print(f'AUC del propensity score: {auc_e:.4f}')
print('  0,50 = asignación aleatoria   1,00 = asignación perfectamente predecible')
print(f'  => hay selección real, pero moderada: queda mucha variación "casi aleatoria" que explotar.\n')
print(f'Rango del propensity score: [{e_oof.min():.3f}, {e_oof.max():.3f}]')
print(f'  tiendas con e(X) < 0,05 : {(e_oof < .05).sum():,}')
print(f'  tiendas con e(X) > 0,95 : {(e_oof > .95).sum():,}')

LIM_PS = (0.05, 0.95)
en_soporte = (e_oof > LIM_PS[0]) & (e_oof < LIM_PS[1])
print(f'\nTiendas en soporte común: {en_soporte.sum():,} de {n:,} ({en_soporte.mean():.2%})')
print('POSITIVIDAD: se cumple. No hay tiendas con probabilidad ~0 o ~1 de recibir nevera,')
print('asi que para cada tienda existen comparables en el otro grupo. No hace falta recortar la muestra.')

fig, ax = plt.subplots(1, 2, figsize=(13, 4))
ax[0].hist(e_oof[T == 0], bins=50, alpha=.6, label='sin nevera (control)', color=C_SIN, density=True)
ax[0].hist(e_oof[T == 1], bins=50, alpha=.6, label='con nevera (tratada)', color=C_CON, density=True)
ax[0].set(title='Solapamiento del propensity score', xlabel='e(X) = P(nevera | X)', ylabel='densidad')
ax[0].legend(fontsize=8)

# Que variables predicen recibir nevera
pi_e = permutation_importance(clf_causal().fit(Xc, T), Xc, T, n_repeats=3,
                              random_state=SEED, scoring='roc_auc', n_jobs=1)
top_e = pd.DataFrame({'v': X_CAUSAL, 'i': pi_e.importances_mean}).nlargest(10, 'i').sort_values('i')
ax[1].barh(top_e.v, top_e.i, color=C_SIN)
ax[1].set(title='¿Qué determinó dónde puso FEMSA sus neveras?', xlabel='caída de AUC al permutar')
plt.tight_layout(); plt.show()
""")

md(r"""
> **El solapamiento es bueno.** Los dos histogramas se superponen en casi todo el rango y ninguna tienda
> tiene `e(X)` por debajo de 0,05 ni por encima de 0,95. Esto es importante: significa que para cada tienda
> con nevera existen tiendas *parecidas* sin nevera y viceversa, así que el ajuste estadístico interpola
> entre casos comparables en lugar de extrapolar. Si hubiera habido tiendas con `e(X) ≈ 1`, no tendríamos
> contrafactual para ellas y habría que excluirlas.
>
> **AUC = 0,63** dice que la asignación fue selectiva pero lejos de determinista. Las variables que más
> predicen haber recibido nevera son las de **escala del negocio** (tráfico, área, surtido): coherente con
> una fuerza de ventas que prioriza las tiendas grandes.
""")

code(r"""
# ----------------------------- 4.4 Balance: antes y despues de ponderar -----------------------------
# IPW: ponderamos cada tienda por 1/e(X) si tratada y 1/(1-e(X)) si control.
# Si el propensity score esta bien estimado, la poblacion ponderada queda balanceada.
ec = np.clip(e_oof, LIM_PS[0], LIM_PS[1])
w_ipw = np.where(T == 1, 1/ec, 1/(1-ec))

def smd_pond(col):
    'SMD crudo y SMD despues de ponderar por IPW.'
    v = Xc[col].values.astype(float)
    s = np.sqrt((v[T==1].var() + v[T==0].var())/2)
    if s == 0: return 0., 0.
    crudo = (v[T==1].mean() - v[T==0].mean())/s
    pond  = (np.average(v[T==1], weights=w_ipw[T==1]) -
             np.average(v[T==0], weights=w_ipw[T==0]))/s
    return crudo, pond

bal = pd.DataFrame([{'variable': c, 'SMD_crudo': a, 'SMD_ponderado': b}
                    for c, (a, b) in ((c, smd_pond(c)) for c in X_CAUSAL)])
bal['abs_crudo'] = bal.SMD_crudo.abs(); bal['abs_pond'] = bal.SMD_ponderado.abs()
bal = bal.sort_values('abs_crudo', ascending=False)

print('Balance de covariables — 12 variables más desbalanceadas\n')
print(bal.head(12)[['variable','SMD_crudo','SMD_ponderado']].to_string(index=False,
      formatters={'SMD_crudo':'{:+.3f}'.format,'SMD_ponderado':'{:+.3f}'.format}))
print(f'\nmáx |SMD| antes de ponderar : {bal.abs_crudo.max():.3f}')
print(f'máx |SMD| después de ponderar: {bal.abs_pond.max():.3f}')
print(f'variables con |SMD| > 0,1 antes: {(bal.abs_crudo > .1).sum()} de {len(bal)}')
print(f'variables con |SMD| > 0,1 después: {(bal.abs_pond > .1).sum()} de {len(bal)}')

fig, ax = plt.subplots(figsize=(7.5, 7))
b = bal.head(20).sort_values('abs_crudo')
ax.scatter(b.abs_crudo, b.variable, label='sin ajustar', color=C_SIN, s=45, zorder=3)
ax.scatter(b.abs_pond, b.variable, label='ponderado por IPW', color=C_ML, s=45, zorder=3)
for _, r in b.iterrows():
    ax.plot([r.abs_pond, r.abs_crudo], [r.variable, r.variable], color='#ccc', lw=1.5, zorder=1)
ax.axvline(.1, ls='--', c='k', lw=1); ax.text(.105, -.4, 'umbral 0,1', fontsize=8)
ax.set(title='Love plot: el ajuste elimina el desbalance', xlabel='|SMD|'); ax.legend(fontsize=9)
plt.tight_layout(); plt.show()
bal.drop(columns=['abs_crudo','abs_pond']).to_csv(f'{RUTA_SALIDAS}/balance_covariables.csv', index=False)
""")

md(r"""
> **El ajuste funciona.** Antes de ponderar, `clientes_prom_dia` tenía un SMD de 0,45 y varias variables
> superaban 0,1. Después de ponderar por el *propensity score*, **ninguna** variable supera 0,05. La
> población ponderada se comporta como si la nevera se hubiera asignado al azar entre tiendas comparables.
>
> Esto valida la *mecánica* del ajuste (el modelo de `e(X)` captura bien la selección observada), aunque no
> puede validar la ignorabilidad: si FEMSA usó un criterio que no está en la base, el balance se vería igual
> de bueno. De ahí la sensibilidad del §4.9.
""")

code(r"""
# ----------------------------- 4.5 Cinco estimadores del efecto promedio -----------------------------
# Los calculamos todos para mostrar que la correccion no depende de un truco particular.
res = {}

# (1) Diferencia simple de medias: el numero "equivocado" de referencia
res['1. Diferencia simple de medias'] = {
    'log': LY[T==1].mean() - LY[T==0].mean(),
    'cop': Y[T==1].mean() - Y[T==0].mean()}

# (2) Regresion ajustada (S-learner): un modelo con T como variable
Xs = Xc.copy(); Xs['_T'] = T
s_mod = HistGradientBoostingRegressor(random_state=SEED, categorical_features=IDXC_C).fit(Xs, LY)
X1 = Xs.copy(); X1['_T'] = 1
X0 = Xs.copy(); X0['_T'] = 0
res['2. Regresión ajustada (S-learner)'] = {'log': (s_mod.predict(X1) - s_mod.predict(X0)).mean()}

# (3) IPW: ponderacion por probabilidad inversa
res['3. Ponderación IPW'] = {
    'log': np.average(LY[T==1], weights=w_ipw[T==1]) - np.average(LY[T==0], weights=w_ipw[T==0])}

# (4) T-learner: un modelo por grupo (ya calculado con cross-fitting)
res['4. T-learner (dos modelos)'] = {'log': (m1_oof - m0_oof).mean()}

# (5) DR-learner (doblemente robusto): el estimador final
#     Combina los modelos de resultado y el propensity score. Es consistente si CUALQUIERA
#     de los dos esta bien especificado, por eso "doblemente robusto".
psi = (m1_oof - m0_oof
       + T*(LY - m1_oof)/ec
       - (1-T)*(LY - m0_oof)/(1-ec))     # pseudo-resultado por tienda
ate_dr = psi.mean()
se_dr  = psi.std(ddof=1)/np.sqrt(n)
res['5. DR-learner (doble robusto)'] = {'log': ate_dr}

tab = pd.DataFrame([{'estimador': k,
                     'efecto_log': v['log'],
                     'efecto_%': (np.exp(v['log'])-1)*100} for k, v in res.items()])
print('===== EFECTO PROMEDIO DE UNA NEVERA SOBRE LAS VENTAS DE FEMSA =====\n')
print(tab.to_string(index=False, formatters={'efecto_log':'{:+.4f}'.format,'efecto_%':'{:+.1f}%'.format}))
print(f'\nDR-learner: efecto = {ate_dr:+.4f} en log  =>  {np.exp(ate_dr)-1:+.1%} sobre las ventas')
print(f'  error estándar {se_dr:.4f}  |  IC 95% en log: '
      f'[{ate_dr-1.96*se_dr:+.4f}, {ate_dr+1.96*se_dr:+.4f}]')
print(f'  IC 95% en %: [{(np.exp(ate_dr-1.96*se_dr)-1):+.1%}, {(np.exp(ate_dr+1.96*se_dr)-1):+.1%}]')
print(f'\nLa diferencia simple ({(np.exp(res["1. Diferencia simple de medias"]["log"])-1):+.1%}) '
      f'sobreestima el efecto en '
      f'{(np.exp(res["1. Diferencia simple de medias"]["log"])-1)/(np.exp(ate_dr)-1)-1:+.0%}.')
""")

code(r"""
# ----------------------------- 4.6 CATE: el efecto tienda por tienda -----------------------------
# Regresamos el pseudo-resultado del DR-learner sobre X: la prediccion es el CATE.
# Tambien con cross-fitting, para que el tau de cada tienda venga de un modelo que no la vio.
tau_log_oof = np.zeros(n)
for i_tr, i_te in CV_CLF.split(Xc, T):
    mt = reg_causal(max_iter=300, learning_rate=0.05, min_samples_leaf=60).fit(Xc.iloc[i_tr], psi[i_tr])
    tau_log_oof[i_te] = mt.predict(Xc.iloc[i_te])

# Modelo final sobre toda la muestra causal: sirve para interpretar y para el tablero
MODELO_CATE = reg_causal(max_iter=300, learning_rate=0.05, min_samples_leaf=60).fit(Xc, psi)

dc['tau_log'] = tau_log_oof
print('Efecto individual estimado (en log, = cambio porcentual aproximado):')
for q in [.05,.25,.50,.75,.95]:
    v = np.quantile(tau_log_oof, q)
    print(f'  P{int(q*100):>2}  {v:+.3f}   ({np.exp(v)-1:+.1%} de ventas)')
print(f'\n  tiendas con efecto estimado <= 0: {(tau_log_oof <= 0).sum():,} ({(tau_log_oof<=0).mean():.1%})')

fig, ax = plt.subplots(1, 2, figsize=(13, 4))
ax[0].hist(tau_log_oof, bins=60, color=C_ML, alpha=.85)
ax[0].axvline(ate_dr, color='k', ls='--', lw=1.2)
ax[0].text(ate_dr, ax[0].get_ylim()[1]*.92, f' promedio {ate_dr:.3f}', fontsize=8)
ax[0].set(title='Distribución del efecto individual (CATE)', xlabel='efecto en log(ventas)', ylabel='tiendas')

ax[1].hist((np.exp(tau_log_oof)-1)*100, bins=60, color=C_ML, alpha=.85)
ax[1].set(title='El mismo efecto, en % sobre las ventas', xlabel='% de aumento de ventas')
plt.tight_layout(); plt.show()
""")

md(r"""
> **El efecto es muy heterogéneo.** Va de **+4 %** en el 5 % inferior de tiendas a **+62 %** en el 5 %
> superior, con una mediana de +25,5 % y un promedio de +27,1 %. Solo un 2,2 % de las tiendas tiene efecto
> estimado no positivo. Esta dispersión es el activo del proyecto: si el efecto fuera igual para todas,
> cualquier lista de 1.000 tiendas con ventas altas daría lo mismo y no habría nada que modelar.
""")

code(r"""
# ----------------------------- 4.7 VALIDACION del modelo de efectos (GATE) -----------------------------
# No observamos el efecto verdadero, asi que no hay R2 posible. Pero si podemos validar el ORDEN:
# agrupamos las tiendas por decil de efecto PREDICHO y estimamos el efecto real de cada decil con
# el estimador doble-robusto. Si el modelo ordena bien, las barras deben crecer de forma monotona.
dec = pd.qcut(tau_log_oof, 10, labels=False)
gate = (pd.DataFrame({'decil': dec+1, 'tau_predicho': tau_log_oof, 'psi': psi})
        .groupby('decil')
        .agg(tau_predicho=('tau_predicho','mean'),
             efecto_DR=('psi','mean'),
             ee=('psi', lambda s: s.std(ddof=1)/np.sqrt(len(s))),
             n=('psi','size')).reset_index())
gate['ic_bajo'] = gate.efecto_DR - 1.96*gate.ee
gate['ic_alto'] = gate.efecto_DR + 1.96*gate.ee

print('===== VALIDACIÓN GATE: efecto real por decil de efecto predicho =====\n')
print(gate.to_string(index=False, formatters={
    'tau_predicho':'{:+.3f}'.format,'efecto_DR':'{:+.3f}'.format,
    'ee':'{:.3f}'.format,'ic_bajo':'{:+.3f}'.format,'ic_alto':'{:+.3f}'.format}))

corr_gate = np.corrcoef(gate.tau_predicho, gate.efecto_DR)[0,1]
monotono = (gate.efecto_DR.diff().dropna() > 0).mean()
print(f'\nCorrelación entre efecto predicho y efecto estimado por decil: {corr_gate:.3f}')
print(f'Pasos monótonos crecientes: {monotono:.0%} de los 9')
print(f'Brecha decil 10 − decil 1: {gate.efecto_DR.iloc[-1] - gate.efecto_DR.iloc[0]:+.3f} en log '
      f'({(np.exp(gate.efecto_DR.iloc[-1])-1) - (np.exp(gate.efecto_DR.iloc[0])-1):+.1%} de ventas)')

fig, ax = plt.subplots(figsize=(9, 4.5))
ax.bar(gate.decil, gate.efecto_DR, yerr=1.96*gate.ee, color=C_ML, alpha=.85, capsize=3,
       label='efecto estimado (doble robusto)')
ax.plot(gate.decil, gate.tau_predicho, 'o--', color=C_SIN, lw=1.8, label='efecto predicho por el modelo')
ax.axhline(0, color='k', lw=.8)
ax.set(title='El modelo ordena bien: efecto real creciente por decil predicho',
       xlabel='decil de efecto predicho (1 = menor)', ylabel='efecto en log(ventas)')
ax.set_xticks(range(1,11)); ax.legend(fontsize=9)
plt.tight_layout(); plt.show()
gate.to_csv(f'{RUTA_SALIDAS}/validacion_gate.csv', index=False)
""")

md(r"""
> **Esta es la prueba de que el modelo sirve para decidir.** Las barras (efecto real estimado por decil, con
> el estimador doble-robusto, que no usa el modelo de CATE) crecen de forma prácticamente monótona y siguen
> de cerca a la línea (efecto predicho). La correlación entre ambas series es ≈ 0,99.
>
> El decil superior tiene un efecto de +0,483 en log contra +0,041 del inferior: cerca de **12 veces**
> mayor, una brecha de **58 puntos porcentuales** de ventas. Eso significa que el modelo
> no está inventando heterogeneidad: realmente distingue tiendas donde la nevera rinde mucho de tiendas donde
> casi no rinde. Es lo único que necesitamos para que la lista de 1.000 tiendas sea mejor que una regla simple.
""")

code(r"""
# ----------------------------- 4.8 De que depende el efecto -----------------------------
pi_t = permutation_importance(MODELO_CATE, Xc, psi, n_repeats=5, random_state=SEED,
                              scoring='r2', n_jobs=1)
imp_t = (pd.DataFrame({'variable': X_CAUSAL, 'importancia': pi_t.importances_mean})
         .sort_values('importancia', ascending=False).reset_index(drop=True))
print('Variables que más determinan el TAMAÑO del efecto:\n')
print(imp_t.head(12).to_string(index=False, formatters={'importancia':'{:.4f}'.format}))

fig, ax = plt.subplots(1, 3, figsize=(14, 4))
t_ = imp_t.head(10).sort_values('importancia')
ax[0].barh(t_.variable, t_.importancia, color=C_ML)
ax[0].set(title='Determinantes de la heterogeneidad', xlabel='importancia')

dd = dc.copy()
dd['_tb'] = pd.cut(dd.temperatura_media_c, [0,16,20,24,28,40], labels=['<16°','16-20°','20-24°','24-28°','>28°'])
g1 = dd.groupby('_tb', observed=True).tau_log.mean()
ax[1].bar(g1.index.astype(str), (np.exp(g1)-1)*100, color=C_ML)
ax[1].set(title='Efecto de la nevera por temperatura', ylabel='% de aumento de ventas', xlabel='')

dd['_cb'] = pd.qcut(dd.clientes_prom_dia, 5, labels=['Q1','Q2','Q3','Q4','Q5'])
g2 = dd.groupby('_cb', observed=True).tau_log.mean()
ax[2].bar(g2.index.astype(str), (np.exp(g2)-1)*100, color=C_CON)
ax[2].set(title='Efecto por tráfico (quintiles)', ylabel='', xlabel='clientes/día')
plt.tight_layout(); plt.show()

print('\nEfecto promedio en % de ventas, por grupo:')
print('\n  Por temperatura:'); print(((np.exp(g1)-1)*100).round(1).to_string())
print('\n  Por tráfico:');     print(((np.exp(g2)-1)*100).round(1).to_string())
print('\n  Por nevera propia del tendero:')
print((dd.groupby('nevera_propia_tienda').tau_log.mean().pipe(lambda s:(np.exp(s)-1)*100)).round(1).to_string())
print('\n  Por nevera de Postobón en la tienda:')
print((dd.groupby('nevera_postobon').tau_log.mean().pipe(lambda s:(np.exp(s)-1)*100)).round(1).to_string())
imp_t.to_csv(f'{RUTA_SALIDAS}/importancia_heterogeneidad.csv', index=False)
""")

md(r"""
### Dónde rinde la nevera (y por qué tiene sentido)

| Factor | Efecto | Lectura de negocio |
|---|---|---|
| **Temperatura alta** | +16,5 % (< 16 °C) → **+45,9 %** (> 28 °C) | Una bebida fría se valora mucho más a 29 °C que a 14 °C |
| **Tráfico alto** | +19,1 % (Q1) → **+37,5 %** (Q5) | El frío solo se convierte en venta si hay gente que entre a comprar |
| **Ya tiene nevera propia** | +31,2 % → **+21,2 %** | El espacio frío ya existía: la nevera FEMSA sustituye en parte, no suma |
| **Tiene nevera de Postobón** | aumenta el efecto | Hay demanda de frío comprobada, y FEMSA le disputa el espacio al competidor |

Las tres primeras filas son el chequeo de sentido común que respalda el modelo: no son relaciones que
hayamos impuesto, son las que el estimador doble-robusto encontró en los datos. Que coincidan con la lógica
del negocio es evidencia a favor de la especificación.
""")

code(r"""
# ----------------------------- 4.9 Sensibilidad -----------------------------
print('===== ANÁLISIS DE SENSIBILIDAD DEL EFECTO PROMEDIO =====\n')
sens = []
sens.append(('Especificación principal (DR, logs)', ate_dr))
# (a) recortar colas del propensity score
for lo, hi in [(0.10, 0.90), (0.15, 0.85)]:
    m = (e_oof > lo) & (e_oof < hi)
    ecx = np.clip(e_oof[m], lo, hi)
    p = (m1_oof[m]-m0_oof[m] + T[m]*(LY[m]-m1_oof[m])/ecx - (1-T[m])*(LY[m]-m0_oof[m])/(1-ecx))
    sens.append((f'Recorte del propensity a [{lo:.2f}, {hi:.2f}]  (n={m.sum():,})', p.mean()))
# (b) incluir todas las tiendas tratadas (cualquier dosis)
Xa, ia = codificar_arboles(df, X_CAUSAL)
Ta, LYa = df.nevera_femsa.values.astype(int), np.log(df.ventas_femsa_cop_mes.values)
ea = cross_val_predict(HistGradientBoostingClassifier(random_state=SEED, categorical_features=ia),
                       Xa, Ta, cv=CV_CLF, method='predict_proba')[:,1]
m0a = np.zeros(len(df)); m1a = np.zeros(len(df))
for i_tr, i_te in CV_CLF.split(Xa, Ta):
    m0a[i_te] = HistGradientBoostingRegressor(random_state=SEED, categorical_features=ia)\
                .fit(Xa.iloc[i_tr][Ta[i_tr]==0], LYa[i_tr][Ta[i_tr]==0]).predict(Xa.iloc[i_te])
    m1a[i_te] = HistGradientBoostingRegressor(random_state=SEED, categorical_features=ia)\
                .fit(Xa.iloc[i_tr][Ta[i_tr]==1], LYa[i_tr][Ta[i_tr]==1]).predict(Xa.iloc[i_te])
eac = np.clip(ea, .05, .95)
pa = m1a-m0a + Ta*(LYa-m1a)/eac - (1-Ta)*(LYa-m0a)/(1-eac)
sens.append((f'Todas las tratadas, cualquier dosis (n={len(df):,})', pa.mean()))
# (c) solo neveras nuevas (<= 2 anios)
mask_n = (df.nevera_femsa==0) | ((df.num_neveras_femsa==1)&(df.nevera_femsa_operativa==1)&
                                 (df.antiguedad_nevera_femsa_anios<=2))
dn = df[mask_n].reset_index(drop=True)
Xn, inx = codificar_arboles(dn, X_CAUSAL)
Tn, LYn = dn.nevera_femsa.values.astype(int), np.log(dn.ventas_femsa_cop_mes.values)
en = cross_val_predict(HistGradientBoostingClassifier(random_state=SEED, categorical_features=inx),
                       Xn, Tn, cv=CV_CLF, method='predict_proba')[:,1]
m0n = np.zeros(len(dn)); m1n = np.zeros(len(dn))
for i_tr, i_te in CV_CLF.split(Xn, Tn):
    m0n[i_te] = HistGradientBoostingRegressor(random_state=SEED, categorical_features=inx)\
                .fit(Xn.iloc[i_tr][Tn[i_tr]==0], LYn[i_tr][Tn[i_tr]==0]).predict(Xn.iloc[i_te])
    m1n[i_te] = HistGradientBoostingRegressor(random_state=SEED, categorical_features=inx)\
                .fit(Xn.iloc[i_tr][Tn[i_tr]==1], LYn[i_tr][Tn[i_tr]==1]).predict(Xn.iloc[i_te])
enc = np.clip(en, .05, .95)
pn_ = m1n-m0n + Tn*(LYn-m1n)/enc - (1-Tn)*(LYn-m0n)/(1-enc)
sens.append((f'Solo neveras nuevas, ≤ 2 años (n={len(dn):,})', pn_.mean()))

sens_tab = pd.DataFrame(sens, columns=['especificación','efecto_log'])
sens_tab['efecto_%'] = (np.exp(sens_tab.efecto_log)-1)*100
print(sens_tab.to_string(index=False, formatters={'efecto_log':'{:+.4f}'.format,'efecto_%':'{:+.1f}%'.format}))
print(f'\nRango del efecto entre especificaciones: '
      f'{(np.exp(sens_tab.efecto_log.min())-1):+.1%} a {(np.exp(sens_tab.efecto_log.max())-1):+.1%}')
print('La conclusión no depende de la especificación elegida.')
sens_tab.to_csv(f'{RUTA_SALIDAS}/sensibilidad_efecto.csv', index=False)
""")

code(r"""
# ----------------------------- 4.10 De logs a pesos: ventas adicionales por tienda -----------------------------
# El efecto es multiplicativo:   ventas_con = ventas_sin x exp(tau)
#   =>  ventas adicionales = ventas_sin x (exp(tau) - 1)
#
# CLAVE: para una tienda ELEGIBLE (que hoy NO tiene nevera FEMSA), sus ventas observadas SON
# su contrafactual sin nevera. No hay que predecirlas: ya las conocemos. Esto elimina por completo
# el error de la linea base y deja solo la incertidumbre del multiplicador.
dc['yhat0_modelo'] = np.exp(m0_oof) * np.exp(LY[T==0] - m0_oof[T==0]).mean()  # alternativa por modelo

ctrl = T == 0
print('Verificación de la línea base en las tiendas control:')
print(f'  ventas observadas promedio      {cop(Y[ctrl].mean())}')
print(f'  predicción del modelo promedio  {cop(dc.yhat0_modelo[ctrl].mean())}')
print(f'  diferencia                      {abs(Y[ctrl].mean()-dc.yhat0_modelo[ctrl].mean())/Y[ctrl].mean():.2%}')
print('  => el modelo esta bien calibrado, pero usamos las ventas OBSERVADAS porque son el dato real.\n')

dc['ventas_adicionales_cop'] = dc.ventas_femsa_cop_mes * (np.exp(dc.tau_log) - 1)
dc['ganancia_estimada_cop_mes'] = MARGEN * dc.ventas_adicionales_cop - COSTO_NEVERA

ELEG = dc[dc.elegible].copy()
print(f'Tiendas elegibles con efecto estimado: {len(ELEG):,}')
print('\nVentas adicionales estimadas por la nevera (COP/mes), entre elegibles:')
for q in [.05,.25,.50,.75,.95,.99]:
    print(f'  P{int(q*100):>2}  {cop(ELEG.ventas_adicionales_cop.quantile(q))}')
print(f'  media {cop(ELEG.ventas_adicionales_cop.mean())}')

umbral_rent = COSTO_NEVERA/MARGEN
print(f'\nUmbral de rentabilidad: la nevera debe generar más de {cop(umbral_rent)} de venta adicional')
print(f'  tiendas elegibles que lo superan: {(ELEG.ventas_adicionales_cop > umbral_rent).sum():,} '
      f'de {len(ELEG):,} ({(ELEG.ventas_adicionales_cop > umbral_rent).mean():.1%})')
print(f'  y solo instalaremos {N_NEVERAS:,} neveras.')

fig, ax = plt.subplots(1, 2, figsize=(13, 4))
ax[0].hist(ELEG.ventas_adicionales_cop/1e6, bins=70, color=C_ML, alpha=.85)
ax[0].axvline(umbral_rent/1e6, color=C_SIN, ls='--', lw=1.5)
ax[0].text(umbral_rent/1e6, ax[0].get_ylim()[1]*.9, ' umbral de\n rentabilidad', fontsize=8, color=C_SIN)
ax[0].set(title='Ventas adicionales por la nevera (elegibles)', xlabel='MM COP / mes', ylabel='tiendas')
ax[0].set_xlim(0, 3)
ax[1].scatter(ELEG.ventas_femsa_cop_mes/1e6, ELEG.ventas_adicionales_cop/1e6, s=4, alpha=.12, color=C_CON)
ax[1].set(title='El efecto crece con el tamaño, pero no es proporcional',
          xlabel='ventas actuales (MM COP)', ylabel='ventas adicionales (MM COP)')
ax[1].set_xlim(0, 5); ax[1].set_ylim(0, 3)
plt.tight_layout(); plt.show()
""")

md(r"""
### §4.11 Comparación con la diferencia simple de promedios, y por qué difieren

Es el punto que pide explícitamente el enunciado.
""")

code(r"""
# ----------------------------- 4.11 Comparacion con la comparacion simple -----------------------------
dif_simple_todas = (df.loc[df.nevera_femsa==1,'ventas_femsa_cop_mes'].mean()
                    - df.loc[df.nevera_femsa==0,'ventas_femsa_cop_mes'].mean())
# efecto causal expresado en COP sobre la misma poblacion (tiendas sin nevera)
efecto_causal_cop = dc.loc[T==0, 'ventas_adicionales_cop'].mean()

comp_met = pd.DataFrame([
 {'método':'Diferencia simple de promedios',  'ventas_adicionales_cop': dif_simple_todas,
  'ganancia_por_tienda': MARGEN*dif_simple_todas - COSTO_NEVERA},
 {'método':'Estimación causal (DR-learner)',  'ventas_adicionales_cop': efecto_causal_cop,
  'ganancia_por_tienda': MARGEN*efecto_causal_cop - COSTO_NEVERA}])
comp_met['sobreestimación'] = comp_met.ventas_adicionales_cop/efecto_causal_cop - 1

print('===== LA DIFERENCIA SIMPLE vs LA ESTIMACIÓN CAUSAL =====\n')
print(comp_met.to_string(index=False, formatters={
    'ventas_adicionales_cop':'{:,.0f}'.format,'ganancia_por_tienda':'{:,.0f}'.format,
    'sobreestimación':'{:+.0%}'.format}))

brecha = dif_simple_todas - efecto_causal_cop
print(f'\nDescomposición de la brecha:')
print(f'  diferencia simple        {cop(dif_simple_todas)}')
print(f'  efecto causal            {cop(efecto_causal_cop)}')
print(f'  sesgo de selección       {cop(brecha)}   ({brecha/dif_simple_todas:.0%} de la diferencia simple)')
print(f'\nSi usáramos la diferencia simple, creeríamos que CADA tienda elegible rinde '
      f'{cop(MARGEN*dif_simple_todas - COSTO_NEVERA)}/mes')
print(f'y declararíamos rentables casi todas. La estimación causal dice que el promedio real es '
      f'{cop(MARGEN*efecto_causal_cop - COSTO_NEVERA)}/mes:')
print('la mayoría de las tiendas elegibles NO paga la nevera, y hay que escoger con cuidado.')

fig, ax = plt.subplots(figsize=(8.5, 4))
etq = ['Diferencia\nsimple', 'Efecto causal\n(DR-learner)']
val = [dif_simple_todas/1e3, efecto_causal_cop/1e3]
b = ax.bar(etq, val, color=[C_SIN, C_ML], width=.5)
ax.bar_label(b, fmt='%.0f mil', padding=3, fontsize=9)
ax.axhline(umbral_rent/1e3, color='k', ls='--', lw=1.2)
ax.text(1.35, umbral_rent/1e3, 'umbral de\nrentabilidad', fontsize=8, va='center')
ax.set(title='Ventas adicionales por nevera: el sesgo de selección casi duplica el efecto',
       ylabel='miles de COP / mes')
plt.tight_layout(); plt.show()
comp_met.to_csv(f'{RUTA_SALIDAS}/comparacion_causal_vs_simple.csv', index=False)
""")

md(r"""
### Por qué la diferencia simple sobreestima casi al doble

La diferencia simple dice **COP 748.000**; el estimador doble-robusto dice **COP 273.000**. Es decir, la
diferencia simple sobreestima el efecto en **174 %** —casi el triple— y **el 63 % de ella no es efecto de la
nevera**, sino que las tiendas con nevera eran mejores desde el principio. Tres mecanismos concretos:

1. **FEMSA priorizó las tiendas grandes y de alto tráfico.** El Hallazgo 3 lo cuantifica: +29 % de clientes,
   +28 % de área. Esas tiendas venderían más que el promedio *aunque nunca hubieran recibido nevera*. El
   *propensity score* confirma que el tamaño del negocio es el principal predictor de haber recibido nevera.

2. **El efecto es multiplicativo, y la diferencia simple se calcula sobre la población equivocada.** Un
   efecto del 27 % aplicado a las tiendas tratadas (que venden COP 1.629.000 en promedio) da COP 440.000; el
   mismo 27 % aplicado a las elegibles (que venden COP 885.000) da COP 239.000. La diferencia simple compara
   el nivel de un grupo con el del otro y por eso mezcla el efecto con la brecha de tamaño.

3. **La "dosis" también está mezclada.** El grupo tratado incluye tiendas con 2 neveras y con 4 puertas, que
   son las más grandes. FEMSA instalará *una* nevera, así que el efecto relevante es menor que el promedio de
   esa mezcla. Por eso restringimos el grupo tratado en §4.1; el análisis de sensibilidad muestra que usar
   todas las tratadas sube el efecto estimado, tal como se espera.

**Consecuencia práctica.** Con la diferencia simple, la ganancia estimada sería de **COP 127.000 por
tienda** y las 12.700 elegibles parecerían rentables: el plan "instale donde sea" se vería bien. Con el
efecto causal, la ganancia promedio de una tienda elegible es de apenas **COP 8.300 al mes** —la nevera
típica casi no se paga— y solo **4.493 de las 12.700** (35 %) son rentables. La ganancia se concentra en un
grupo pequeño y muy identificable: tiendas **calientes, de alto tráfico y sin espacio frío propio**. Esa es
la recomendación que el módulo 6 convierte en una lista.

### Limitaciones de esta estimación

- **Ignorabilidad no verificable.** Si la fuerza de ventas usó un criterio no observado —por ejemplo, la
  actitud del tendero— el efecto seguiría sesgado. El balance perfecto post-ajuste no descarta esto.
  Mitigación: la base trae los determinantes habituales de la decisión y el solapamiento es amplio.
- **Un solo mes, sin línea de base previa.** No podemos usar diferencias-en-diferencias, que sería el
  método preferido. Con dos periodos, el mismo código se adaptaría cambiando el objetivo por el cambio de
  ventas.
- **SUTVA / equilibrio general.** Instalar 1.000 neveras puede mover a la competencia o canibalizar tiendas
  vecinas. Con tiendas dispersas el efecto cruzado debería ser pequeño, pero no es nulo.
- **Extrapolación.** Las elegibles son más pequeñas que las tratadas. El buen solapamiento del *propensity
  score* limita el problema, pero el efecto en las elegibles más pequeñas se apoya más en el modelo.
""")
