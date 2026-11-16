# Proyecto final de Machine Learning — Plan de neveras FEMSA

¿En cuáles **1.000 tiendas** debe FEMSA instalar sus 1.000 neveras nuevas, y cuánto ganaría cada mes?

Este repositorio contiene el programa completo: un cuaderno que corre de principio a fin desde la base
original y produce la lista de tiendas, la estimación de ganancia y todos los insumos del tablero.

---

## Resultado

| | |
|---|---|
| **Tiendas elegidas** | 1.000 de 12.700 elegibles |
| **Ganancia mensual estimada** | **COP 251,9 millones** (COP 3.023 millones al año) |
| **Retorno sobre el costo de las neveras** | 4,2x |
| **Método del efecto** | DR-learner (doblemente robusto) con cross-fitting |
| **Efecto causal de la nevera** | **+27,1 %** sobre las ventas (IC 95 %: +25,8 % a +28,4 %) |
| **Ventaja sobre la mejor regla simple** | **+20,1 %** de ganancia (COP +42,1 millones/mes) |

El núcleo del proyecto está en una sola comparación: la diferencia simple de promedios entre tiendas con y
sin nevera es de **COP 748.000** al mes, pero el efecto causal es de **COP 273.000**. La diferencia simple
sobreestima el efecto en **174 %**, y el 63 % de ella no es efecto de la nevera: es que FEMSA puso sus
neveras en las mejores tiendas.

Esto cambia la decisión por completo. Con la diferencia simple, cada tienda elegible parecería rendir
COP 127.000 al mes y las 12.700 serían rentables. Con el efecto causal, la ganancia promedio de una
elegible es de **COP 8.300** y solo **4.493** se pagan la nevera.

---

## Cómo correrlo

### Opción A — Google Colab (recomendada)

1. Abrir [Google Colab](https://colab.research.google.com) → **Archivo → Subir cuaderno** →
   `notebooks/proyecto_final_neveras.ipynb`.
2. En el **módulo 0**, cambiar `GRUPO = 'X'` por el número del grupo.
3. **Entorno de ejecución → Ejecutar todo**.
4. Cuando lo pida, subir `base_refrescos_nevera.csv` (o descomentar el bloque de Google Drive
   en la celda de carga).

Tiempo total: **8–12 minutos** en una instancia estándar de Colab (sin GPU).

### Opción B — Local

```bash
pip install -r requirements.txt
jupyter notebook notebooks/proyecto_final_neveras.ipynb
```

El cuaderno busca la base en `datos/base_refrescos_nevera.csv`, en el directorio actual o en Drive.

---

## Estructura

```
├── notebooks/
│   └── proyecto_final_neveras.ipynb   Programa completo (módulos 0 a 7)
├── datos/
│   ├── base_refrescos_nevera.csv      Base original: 38.000 tiendas x 109 columnas
│   └── diccionario_base_tiendas.xlsx  Diccionario de variables
├── salidas/                           Se genera al correr el cuaderno
│   ├── lista_grupoX.csv               ENTREGABLE: 1.000 tiendas
│   ├── tablero_tiendas.csv            Insumo principal del tablero
│   ├── tablero_kpis.csv               Indicadores de resumen
│   └── ...                            Métricas, importancias, validaciones
├── tablero/                           Aplicación web de Google Apps Script
│   ├── codigo.gs                      Servidor: lee la hoja y sirve el tablero
│   └── tablero.html                   Interfaz del tablero
├── nb_parts/                          Fuente del cuaderno, por módulo
├── build_notebook.py                  Regenera el .ipynb desde nb_parts/
├── requirements.txt
└── README.md
```

> `nb_parts/` y `build_notebook.py` son solo la herramienta con la que se arma el cuaderno, para poder
> editar cada módulo por separado sin tocar el JSON del `.ipynb`. Correr `python build_notebook.py`
> reconstruye `notebooks/proyecto_final_neveras.ipynb`. **No es necesario** para usar el proyecto.

---

## El tablero

La carpeta `tablero/` es una **aplicación web de Google Apps Script**: se pegan los dos
archivos en el editor de Apps Script de la hoja, se publica, y la URL que devuelve **es
el tablero**.

1. En Google Sheets: **Archivo → Importar → Subir →** `salidas/tablero_tiendas.csv`,
   insertando una hoja nueva llamada `tablero_tiendas`.
2. **Extensiones → Apps Script**. Crear `codigo.gs` y `tablero.html` con esos nombres
   exactos y pegar el contenido de cada uno.
3. **Implementar → Nueva implementación → Aplicación web →** *Ejecutar como: Yo*,
   *Acceso: Cualquier usuario con el enlace* → **Implementar**.

Las instrucciones completas están en la cabecera de `tablero/codigo.gs`.

El tablero cubre lo que pide el enunciado: filtros por región, ciudad y tipo de negocio,
mapa de las 1.000 tiendas, ganancia estimada, comparación con las dos reglas simples,
riesgo de cambio, importancia de variables y consulta por `id_tienda`.

La fuente de datos es **`salidas/tablero_tiendas.csv`** (12.700 elegibles × 36 columnas),
no `salidas/lista_grupoDaniJohelRebe.csv`, que es el entregable de 3 columnas que se sube
al profesor.

---

## Los seis módulos

| Módulo | Qué hace | Hallazgo principal |
|---|---|---|
| **1. Análisis exploratorio** | Describe tiendas, ventas y neveras | Las ventas son log-normales; las tiendas con nevera tenían **+29 % de tráfico** antes de recibirla |
| **2. Preparación de datos** | Define variables y controla la fuga | Verifica numéricamente que 50 columnas *contienen* la respuesta; define tres conjuntos de variables |
| **3. Modelo de ventas** | 4 algoritmos con validación cruzada | Gradient Boosting R² = 0,706 en test vs 0,661 del base lineal |
| **4. Efecto de la nevera** | 5 estimadores causales + validación GATE | Efecto **+27,1 %**, muy heterogéneo: de +4 % a +62 % según la tienda |
| **5. Riesgo de cambio** | 3 modelos, desbalance, umbral por costos | ROC-AUC 0,82 y PR-AUC 0,40; el umbral económico es **0,25**, no 0,5 |
| **6. Decisión** | Las 1.000 tiendas y la ganancia | COP 251,9 MM/mes: **+20,1 %** sobre la mejor regla simple |

### El hallazgo que resume el proyecto

Nuestra lista y la regla de "mayores ventas" comparten 638 tiendas. Las 362 que las separan:

| | Solo en nuestra lista | Solo en la regla de ventas |
|---|---|---|
| Temperatura media | **26,6 °C** | 19,5 °C |
| Ventas actuales | COP 1.501.867 | **COP 2.201.314** |
| Ganancia estimada | **COP 175.892** | COP 59.487 |

La regla de ventas escoge tiendas con COP 700.000 más de venta mensual y obtiene **tres veces menos
ganancia**: está pagando por tamaño en ciudades frías, donde una nevera añade poco.

---

## Decisiones de modelación que vale la pena conocer

**1. Todo en logaritmo.** `log(ventas)` es casi perfectamente simétrico (asimetría −0,03 frente a 4,4 en
niveles). El efecto de la nevera se comporta como un **porcentaje**, no como un monto fijo: por eso el
mismo efecto del 27 % vale COP 90.000 en una tienda pequeña y COP 900.000 en una grande.

**2. El tratamiento se define con precisión.** El grupo "con nevera" de la base mezcla configuraciones:
1 o 2 neveras, 1/2/4 puertas, de 0 a 15 años, y unas 3.800 tiendas con la nevera **averiada**. Como FEMSA
instalará *una nevera nueva y operativa*, el análisis compara contra tiendas con exactamente esa
configuración. La sensibilidad muestra que usar todas las tratadas infla el efecto.

**3. Control de fuga en tres niveles.** No solo se excluyen las columnas que suman a la respuesta
(verificado con `np.allclose`), sino también los resultados **simultáneos** (ventas de Postobón del mismo
mes: están afectadas por el tratamiento, condicionar sobre ellas sesga el efecto) y las variables que
**describen la nevera FEMSA** (son funciones determinísticas del tratamiento).

**4. Línea base observada.** Para una tienda elegible —que hoy no tiene nevera— sus ventas observadas
**son** su contrafactual sin nevera. No hay que predecirlas. Esto elimina el error de la línea base y deja
solo la incertidumbre del multiplicador.

**5. El modelo causal se valida ordenando, no prediciendo.** El efecto individual no es observable, así que
no hay R² posible. Lo que sí se puede validar es el **orden**: agrupamos las tiendas por decil de efecto
predicho y estimamos el efecto real de cada decil con el estimador doble-robusto, que no usa el modelo de
efectos. Las dos series se correlacionan **0,994** y el decil superior tiene un efecto 12 veces mayor que el
inferior (+0,483 contra +0,041 en log). Además, el balance de covariables pasa de un |SMD| máximo de 0,45 a
0,03 tras el ajuste, y el *propensity score* se mantiene entre 0,07 y 0,88 — sin problemas de positividad.

**6. El umbral de riesgo sale de los costos, no de 0,5.** Conviene actuar cuando
`0,40 × p × 500.000 > 50.000`, es decir `p > 0,25`. En los datos, ese umbral teórico rinde COP 123,2
millones contra COP 125,0 millones del óptimo empírico (0,24): una diferencia del 1,5 %. El umbral que sale
de los costos es, en la práctica, el óptimo.

---

## Reproducibilidad

- Semilla fija `SEED = 42` en todos los modelos, particiones y validaciones cruzadas.
- Los mapas de categorías se fijan explícitamente (`MAPAS_CAT`), así que la codificación no depende del
  orden de las filas.
- Correr *Ejecutar todo* dos veces produce los mismos 1.000 `id_tienda` y las mismas cifras.
- El cuaderno valida la base al cargarla (38.000 filas, 109 columnas, 0 faltantes, 0 duplicados) y valida
  el entregable antes de escribirlo (exactamente 1.000 filas, sin repetidos, todas elegibles).

## Limitaciones

- **Ignorabilidad no verificable.** Si FEMSA usó un criterio que no está en la base al decidir dónde poner
  sus neveras, el efecto estimado seguiría sesgado. El balance de covariables post-ajuste no descarta esto.
- **Un solo mes.** Sin una línea de base previa no se puede usar diferencias-en-diferencias, que sería el
  método preferible.
- **SUTVA.** Instalar 1.000 neveras puede mover a la competencia o canibalizar tiendas vecinas.
- Los datos son **simulados con fines académicos**: no provienen de FEMSA, Postobón ni de tiendas reales.

## Declaración de uso de IA

Este proyecto se desarrolló con apoyo de un asistente de IA (Claude) en: exploración inicial de la base,
redacción del código del cuaderno, elección y discusión de los estimadores causales, y redacción de los
textos explicativos.

Las decisiones de modelación —definición del tratamiento, variables excluidas por fuga, estimador final y
criterio de selección de las 1.000 tiendas— fueron revisadas, verificadas y asumidas por el grupo. Todos
los integrantes pueden explicar y modificar cualquier celda del cuaderno.
