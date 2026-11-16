# ===================== MODULO 6 =====================
md(r"""
---
# Módulo 6 — Decisión: las 1.000 tiendas

**Objetivo:** elegir exactamente 1.000 tiendas elegibles, estimar la ganancia mensual total y compararla con
dos reglas simples: mayores ventas actuales y mayor tráfico.

**Criterio.** Ordenamos las 12.700 tiendas elegibles por la ganancia mensual estimada

$$\text{ganancia}_i = 0{,}25 \times \widehat{\text{ventas adicionales}}_i - 60.000$$

y tomamos las 1.000 primeras. Como la restricción es de **cantidad** (1.000 neveras) y no de presupuesto,
maximizar la suma de las 1.000 mayores ganancias individuales es exactamente la decisión óptima dado nuestro
modelo.
""")

code(r"""
# ----------------------------- 6.1 Construccion de la lista -----------------------------
# Partimos de las elegibles con su efecto estimado y les pegamos el riesgo de cambio del modulo 5
ELEG = (dc[dc.elegible]
        .merge(df[['id_tienda','prob_cambio','riesgo_cambio']], on='id_tienda', how='left')
        .reset_index(drop=True))
assert ELEG.prob_cambio.notna().all(), 'faltan probabilidades de cambio'
assert len(ELEG) == int(df.elegible.sum()), 'se perdieron tiendas elegibles'

ELEG = ELEG.sort_values('ganancia_estimada_cop_mes', ascending=False).reset_index(drop=True)
ELEG['ranking'] = np.arange(1, len(ELEG)+1)
ELEG['seleccionada'] = ELEG.ranking <= N_NEVERAS

LISTA = ELEG[ELEG.seleccionada].copy()

print(f'===== LISTA FINAL: {len(LISTA):,} TIENDAS =====\n')
G_TOTAL = LISTA.ganancia_estimada_cop_mes.sum()
print(f'Ganancia mensual total estimada  {cop(G_TOTAL)}   ({mm(G_TOTAL)} COP)')
print(f'Ganancia anualizada              {mm(G_TOTAL*12)} COP')
print(f'Ganancia promedio por tienda     {cop(LISTA.ganancia_estimada_cop_mes.mean())} / mes')
print(f'Ganancia de la tienda n° 1.000   {cop(LISTA.ganancia_estimada_cop_mes.min())} / mes  (la peor de la lista)')
print(f'Ganancia de la tienda n° 1       {cop(LISTA.ganancia_estimada_cop_mes.max())} / mes')
print()
print(f'Ventas adicionales totales       {mm(LISTA.ventas_adicionales_cop.sum())} COP / mes')
print(f'Costo total de las neveras       {mm(N_NEVERAS*COSTO_NEVERA)} COP / mes')
print(f'Retorno sobre el costo           {G_TOTAL/(N_NEVERAS*COSTO_NEVERA):.2f}x')
print()
print(f'Tiendas elegibles rentables (ganancia > 0): {(ELEG.ganancia_estimada_cop_mes>0).sum():,} '
      f'de {len(ELEG):,}')
print(f'=> las 1.000 neveras alcanzan para cubrir solo el '
      f'{N_NEVERAS/(ELEG.ganancia_estimada_cop_mes>0).sum():.0%} de las tiendas rentables.')
print(f'\nRiesgo de cambio de proveedor en la lista:')
print(f'  riesgo Alto: {(LISTA.riesgo_cambio=="Alto").sum():,} tiendas '
      f'({(LISTA.riesgo_cambio=="Alto").mean():.1%})')
print(f'  riesgo Bajo: {(LISTA.riesgo_cambio=="Bajo").sum():,} tiendas')
print(f'  (en el total de elegibles el riesgo Alto es {(ELEG.riesgo_cambio=="Alto").mean():.1%})')
""")

code(r"""
# ----------------------------- 6.2 Comparacion con las dos reglas simples -----------------------------
# Regla 1: las 1.000 elegibles con mayores ventas actuales de FEMSA
# Regla 2: las 1.000 elegibles con mayor trafico (clientes/dia)
# Las tres listas se valoran con EL MISMO modelo de efecto, que es la unica comparacion justa:
# cambia solo el criterio de seleccion.
regla_ventas  = ELEG.nlargest(N_NEVERAS, 'ventas_femsa_cop_mes')
regla_trafico = ELEG.nlargest(N_NEVERAS, 'clientes_prom_dia')
aleatoria     = ELEG.sample(N_NEVERAS, random_state=SEED)

def resumen(nombre, s):
    return {'estrategia': nombre,
            'ganancia_total_mes': s.ganancia_estimada_cop_mes.sum(),
            'ganancia_prom_tienda': s.ganancia_estimada_cop_mes.mean(),
            'ventas_adicionales_mes': s.ventas_adicionales_cop.sum(),
            'tiendas_no_rentables': int((s.ganancia_estimada_cop_mes <= 0).sum()),
            'riesgo_alto': int((s.riesgo_cambio == 'Alto').sum()),
            'ventas_actuales_prom': s.ventas_femsa_cop_mes.mean(),
            'temperatura_prom': s.temperatura_media_c.mean()}

cmp_reglas = pd.DataFrame([
    resumen('Modelo de efecto causal (nuestra lista)', LISTA),
    resumen('Regla simple: mayores ventas actuales', regla_ventas),
    resumen('Regla simple: mayor tráfico', regla_trafico),
    resumen('Selección aleatoria', aleatoria)])
cmp_reglas['vs_mejor_regla'] = (cmp_reglas.ganancia_total_mes /
    cmp_reglas.ganancia_total_mes.iloc[1:3].max() - 1)

print('===== NUESTRA LISTA vs LAS REGLAS SIMPLES =====\n')
print(cmp_reglas[['estrategia','ganancia_total_mes','ganancia_prom_tienda',
                  'tiendas_no_rentables','riesgo_alto']].to_string(index=False, formatters={
    'ganancia_total_mes':'{:,.0f}'.format,'ganancia_prom_tienda':'{:,.0f}'.format}))

g_ml = cmp_reglas.ganancia_total_mes.iloc[0]
g_v  = cmp_reglas.ganancia_total_mes.iloc[1]
g_t  = cmp_reglas.ganancia_total_mes.iloc[2]
g_a  = cmp_reglas.ganancia_total_mes.iloc[3]
print(f'\nNuestra lista:            {mm(g_ml)} COP / mes')
print(f'Regla "mayores ventas":   {mm(g_v)} COP / mes   -> nuestra lista la supera en {g_ml/g_v-1:+.1%}')
print(f'Regla "mayor tráfico":    {mm(g_t)} COP / mes   -> nuestra lista la supera en {g_ml/g_t-1:+.1%}')
print(f'Selección aleatoria:      {mm(g_a)} COP / mes   -> nuestra lista la supera en {g_ml/g_a-1:+.1%}')
print(f'\nValor del modelo frente a la mejor regla simple: '
      f'{mm(g_ml-max(g_v,g_t))} COP / mes = {mm((g_ml-max(g_v,g_t))*12)} COP / año')
print(f'\nSolapamiento de tiendas con nuestra lista:')
print(f'  regla "mayores ventas": {len(set(LISTA.id_tienda)&set(regla_ventas.id_tienda)):,} de 1.000')
print(f'  regla "mayor tráfico":  {len(set(LISTA.id_tienda)&set(regla_trafico.id_tienda)):,} de 1.000')
""")

code(r"""
# ----------------------------- 6.3 Graficos de la decision -----------------------------
fig = plt.figure(figsize=(14, 8.5))
gs = fig.add_gridspec(2, 3, hspace=.42, wspace=.3)

# (a) comparacion de estrategias
ax = fig.add_subplot(gs[0, 0])
o = cmp_reglas.iloc[::-1]
etq = ['Aleatoria','Mayor\ntráfico','Mayores\nventas','Modelo\ncausal']
b = ax.barh(etq, o.ganancia_total_mes/1e6, color=[C_R2, C_R1, C_R1, C_ML])
ax.bar_label(b, fmt='%.0f MM', padding=3, fontsize=8)
ax.set(title='Ganancia mensual total por estrategia', xlabel='MM COP / mes')

# (b) curva de ganancia acumulada
ax = fig.add_subplot(gs[0, 1:])
for nm, s, c in [('Modelo causal', LISTA, C_ML),
                 ('Regla: mayores ventas', regla_ventas.sort_values('ganancia_estimada_cop_mes', ascending=False), C_R1),
                 ('Regla: mayor tráfico', regla_trafico.sort_values('ganancia_estimada_cop_mes', ascending=False), C_R2)]:
    ax.plot(np.arange(1, len(s)+1), s.ganancia_estimada_cop_mes.cumsum()/1e6, lw=2, label=nm, color=c)
ax.set(title='Ganancia acumulada al instalar las neveras en orden',
       xlabel='neveras instaladas', ylabel='MM COP / mes'); ax.legend(fontsize=8.5)

# (c) ganancia marginal: donde dejaria de convenir
ax = fig.add_subplot(gs[1, 0])
ax.plot(ELEG.ranking, ELEG.ganancia_estimada_cop_mes/1e3, lw=1.5, color=C_CON)
ax.axhline(0, color='k', lw=.8)
ax.axvline(N_NEVERAS, color=C_SIN, ls='--', lw=1.5)
ax.text(N_NEVERAS+180, ELEG.ganancia_estimada_cop_mes.max()/1e3*.75, '1.000\nneveras',
        fontsize=8, color=C_SIN)
n_rent = int((ELEG.ganancia_estimada_cop_mes > 0).sum())
ax.axvline(n_rent, color='k', ls=':', lw=1.2)
ax.text(n_rent+180, 30, f'punto de equilibrio\n({n_rent:,} tiendas)', fontsize=8)
ax.set(title='Ganancia marginal por tienda (ordenadas)', xlabel='ranking', ylabel='miles de COP / mes')

# (d) perfil comparado
ax = fig.add_subplot(gs[1, 1])
perf = pd.DataFrame({
 'Modelo causal':[LISTA.temperatura_media_c.mean(), LISTA.clientes_prom_dia.mean()/4,
                  LISTA.ventas_femsa_cop_mes.mean()/1e5, LISTA.nevera_propia_tienda.mean()*100],
 'Mayores ventas':[regla_ventas.temperatura_media_c.mean(), regla_ventas.clientes_prom_dia.mean()/4,
                  regla_ventas.ventas_femsa_cop_mes.mean()/1e5, regla_ventas.nevera_propia_tienda.mean()*100]},
 index=['Temp. (°C)','Clientes/día ÷4','Ventas (×100 mil)','% con nevera propia'])
perf.plot(kind='barh', ax=ax, color=[C_ML, C_R1], width=.75)
ax.set(title='¿En qué se diferencian las dos listas?'); ax.legend(fontsize=8)

# (e) region
ax = fig.add_subplot(gs[1, 2])
rr = pd.DataFrame({'Modelo causal': LISTA.region.value_counts(),
                   'Mayores ventas': regla_ventas.region.value_counts()}).fillna(0)
rr.plot(kind='barh', ax=ax, color=[C_ML, C_R1], width=.75)
ax.set(title='Distribución regional de la lista', xlabel='tiendas'); ax.legend(fontsize=8)
plt.show()
""")

code(r"""
# ----------------------------- 6.4 Por que gana el modelo -----------------------------
print('===== PERFIL DE LAS 1.000 TIENDAS ELEGIDAS =====\n')
pf = pd.DataFrame({
 'nuestra_lista'  : LISTA[['temperatura_media_c','clientes_prom_dia','area_m2','ventas_femsa_cop_mes',
                           'poblacion_500m','nevera_propia_tienda','nevera_postobon','estrato']].mean(),
 'regla_ventas'   : regla_ventas[['temperatura_media_c','clientes_prom_dia','area_m2','ventas_femsa_cop_mes',
                           'poblacion_500m','nevera_propia_tienda','nevera_postobon','estrato']].mean(),
 'todas_elegibles': ELEG[['temperatura_media_c','clientes_prom_dia','area_m2','ventas_femsa_cop_mes',
                           'poblacion_500m','nevera_propia_tienda','nevera_postobon','estrato']].mean()})
print(pf.round(2).to_string())

print('\n===== COMPOSICIÓN DE LA LISTA =====')
print('\nPor región:'); print(LISTA.region.value_counts().to_string())
print('\nPor tipo de negocio:'); print(LISTA.tipo_negocio.value_counts().to_string())
print('\nPor zona:'); print(LISTA.zona.value_counts().to_string())
print('\nTop 10 ciudades:'); print(LISTA.ciudad.value_counts().head(10).to_string())

print('\n===== DÓNDE ESTÁ LA DIFERENCIA CON LA REGLA DE VENTAS =====')
solo_ml = LISTA[~LISTA.id_tienda.isin(regla_ventas.id_tienda)]
solo_rv = regla_ventas[~regla_ventas.id_tienda.isin(LISTA.id_tienda)]
print(f'\nTiendas que solo nuestra lista elige: {len(solo_ml):,}')
print(f'  temperatura media {solo_ml.temperatura_media_c.mean():.1f} °C | '
      f'ventas actuales {cop(solo_ml.ventas_femsa_cop_mes.mean())} | '
      f'ganancia {cop(solo_ml.ganancia_estimada_cop_mes.mean())}')
print(f'Tiendas que solo la regla de ventas elige: {len(solo_rv):,}')
print(f'  temperatura media {solo_rv.temperatura_media_c.mean():.1f} °C | '
      f'ventas actuales {cop(solo_rv.ventas_femsa_cop_mes.mean())} | '
      f'ganancia {cop(solo_rv.ganancia_estimada_cop_mes.mean())}')
print(f'\nLa regla de ventas paga {cop(solo_rv.ventas_femsa_cop_mes.mean()-solo_ml.ventas_femsa_cop_mes.mean())}')
print('más de ventas actuales por tienda, pero obtiene menos ganancia: está comprando tamaño,')
print('no capacidad de respuesta a la nevera.')
cmp_reglas.to_csv(f'{RUTA_SALIDAS}/comparacion_reglas.csv', index=False)
""")

code(r"""
# ----------------------------- 6.5 Sensibilidad de la decision -----------------------------
# Cuanto cambiaria la lista y la ganancia bajo supuestos distintos.
print('===== SENSIBILIDAD DE LA DECISIÓN =====\n')

# (a) linea base por modelo en vez de ventas observadas
tau_mult = np.exp(ELEG.tau_log.values) - 1
alt = {}
alt['Línea base = ventas observadas (principal)'] = ELEG.ventas_femsa_cop_mes.values * tau_mult
alt['Línea base = predicción del modelo']          = ELEG.yhat0_modelo.values * tau_mult
alt['Línea base = media geométrica de ambas']      = np.sqrt(ELEG.ventas_femsa_cop_mes.values*ELEG.yhat0_modelo.values)*tau_mult
filas_s = []
for nm, va in alt.items():
    g = MARGEN*va - COSTO_NEVERA
    top = np.argsort(-g)[:N_NEVERAS]
    ids = set(ELEG.id_tienda.values[top])
    filas_s.append({'supuesto': nm, 'ganancia_total': g[top].sum(),
                    'coincide_con_lista': len(ids & set(LISTA.id_tienda))})
# (b) margenes alternativos
for m_alt in [0.20, 0.30]:
    g = m_alt*ELEG.ventas_adicionales_cop.values - COSTO_NEVERA
    top = np.argsort(-g)[:N_NEVERAS]
    filas_s.append({'supuesto': f'Margen {m_alt:.0%} en vez de 25%', 'ganancia_total': g[top].sum(),
                    'coincide_con_lista': len(set(ELEG.id_tienda.values[top]) & set(LISTA.id_tienda))})
# (c) costo alternativo
for c_alt in [40_000, 90_000]:
    g = MARGEN*ELEG.ventas_adicionales_cop.values - c_alt
    top = np.argsort(-g)[:N_NEVERAS]
    filas_s.append({'supuesto': f'Costo nevera {cop(c_alt)}', 'ganancia_total': g[top].sum(),
                    'coincide_con_lista': len(set(ELEG.id_tienda.values[top]) & set(LISTA.id_tienda))})
# (d) efecto 25% menor (escenario conservador)
g = MARGEN*ELEG.ventas_adicionales_cop.values*0.75 - COSTO_NEVERA
top = np.argsort(-g)[:N_NEVERAS]
filas_s.append({'supuesto': 'Efecto 25 % menor al estimado', 'ganancia_total': g[top].sum(),
                'coincide_con_lista': len(set(ELEG.id_tienda.values[top]) & set(LISTA.id_tienda))})

sens_dec = pd.DataFrame(filas_s)
print(sens_dec.to_string(index=False, formatters={'ganancia_total':'{:,.0f}'.format}))
print('\nLa composición de la lista es muy estable: los supuestos económicos (margen y costo) cambian')
print('la ganancia pero casi no cambian QUÉ tiendas se eligen, porque reescalan a todas por igual.')

# (e) que pasaria si priorizaramos tambien la retencion
valor_ret = EFECTIVIDAD_RETENCION * ELEG.prob_cambio.values * VALOR_EVITAR_CAMBIO - COSTO_RETENCION
ELEG['ganancia_con_retencion'] = ELEG.ganancia_estimada_cop_mes + np.maximum(valor_ret, 0)
lista_ret = ELEG.nlargest(N_NEVERAS, 'ganancia_con_retencion')
print(f'\nEscenario alternativo: si FEMSA valorara también la retención en el mismo ranking,')
print(f'  coincidirían {len(set(lista_ret.id_tienda)&set(LISTA.id_tienda)):,} de las 1.000 tiendas')
print(f'  y {(lista_ret.riesgo_cambio=="Alto").sum():,} serían de riesgo Alto '
      f'(vs {(LISTA.riesgo_cambio=="Alto").sum():,} en nuestra lista).')
print('  No lo usamos para la entrega porque la fórmula de ganancia del caso no incluye la retención,')
print('  pero queda como recomendación operativa: cruzar la lista con la campaña de retención.')
sens_dec.to_csv(f'{RUTA_SALIDAS}/sensibilidad_decision.csv', index=False)
""")

md(r"""
### Lectura del módulo 6

**La recomendación.** Instalar las 1.000 neveras en la lista del modelo causal. La ganancia mensual estimada
es de **COP 251,9 millones** (COP 3.023 millones al año), con un retorno de **4,2x** sobre el costo de las
neveras. Supera a la regla de mayores ventas en **+20,1 %** (COP 209,8 millones) y a la de mayor tráfico en
**+54,7 %** (COP 162,8 millones). La diferencia proviene de un cambio de criterio concreto: **dejar de
comprar tamaño y empezar a comprar capacidad de respuesta**.

**Dónde está exactamente la diferencia.** Las dos listas comparten 638 tiendas; las 362 que las separan
cuentan la historia completa:

| | Solo en nuestra lista | Solo en la regla de ventas |
|---|---|---|
| Temperatura media | **26,6 °C** | 19,5 °C |
| Ventas actuales | COP 1.501.867 | **COP 2.201.314** |
| Ganancia estimada | **COP 175.892** | COP 59.487 |

La regla de ventas escoge tiendas con **COP 700.000 más** de venta mensual y obtiene **tres veces menos
ganancia**. Está pagando por tamaño en ciudades frías, donde una nevera añade poco. Además incluye 36
tiendas con ganancia negativa (la de tráfico, 95); nuestra lista, ninguna.

**Por qué las reglas simples pierden.** Las dos escogen tiendas grandes. El problema es que el tamaño ya
está correlacionado con tener nevera (por eso había sesgo de selección), y entre las *elegibles* las más
grandes son con frecuencia tiendas que ya tienen nevera propia o que están en ciudades frías. Nuestra lista
sacrifica ventas actuales a cambio de un efecto mucho mayor.

**El límite de 1.000 neveras es la restricción activa.** Hay **4.493** tiendas elegibles rentables y solo
1.000 neveras: alcanzan para el 22 % de ellas. No sobra capacidad, así que cada nevera asignada a la tienda
equivocada tiene un costo de oportunidad real. Esto también significa que **ampliar el plan sería
rentable**: la tienda número 1.000 todavía deja COP 119.003 al mes, muy por encima de cero.

**La decisión es robusta.** Cambiar el margen, el costo de la nevera o reducir el efecto estimado en 25 %
mueve la ganancia total pero casi no cambia *qué* tiendas se eligen, porque esos supuestos reescalan a todas
las tiendas por igual. El riesgo real no está en los supuestos económicos sino en el supuesto de
ignorabilidad del módulo 4.
""")
