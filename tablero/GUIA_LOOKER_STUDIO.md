# Guía: construir el tablero en Looker Studio (antes Data Studio)

Esta guía replica, elemento por elemento, el mockup `mockup_tablero.html`.
Ábrelo al lado mientras construyes: lo que ves ahí es lo que debe quedar.

**Fuente de datos única: `salidas/tablero_tiendas.csv`** (12.700 filas × 36 columnas).

---

## Paso 0 — Subir los datos a Google Sheets

1. Crea una hoja nueva en [sheets.google.com](https://sheets.google.com).
2. **Archivo → Importar → Subir →** `tablero_tiendas.csv`.
3. En *Tipo de importación* elige **Insertar nueva hoja**. En *Separador*, **Coma**.
4. Renombra la pestaña como **`tablero_tiendas`**.

> ⚠️ **Si los decimales se dañan** (ves `4.2` convertido en `42`, o `28.0` en `280`):
> **Archivo → Configuración → Configuración regional → Estados Unidos**, y vuelve a importar.
> Esto pasa porque en configuración de Colombia el punto es separador de miles.

Opcional: pega `apps_script_tablero.gs` en **Extensiones → Apps Script** y ejecuta
`construirTablero` para generar hojas de resumen y gráficos nativos de Sheets.
No es necesario para Looker, pero sirve para revisar que los datos quedaron bien.

---

## Paso 1 — Conectar Looker Studio

1. Entra a [lookerstudio.google.com](https://lookerstudio.google.com) → **Crear → Informe**.
2. **Google Sheets** → elige tu archivo → hoja `tablero_tiendas` → **Añadir**.
3. Verifica los tipos de campo en el panel derecho. **Esto es lo que más falla:**

| Campo | Tipo que debe tener |
|---|---|
| `lat_long` | **Geo → Latitud, Longitud** ← no lo detecta solo, cámbialo a mano |
| `ganancia_estimada_cop_mes` | Número → Moneda → COP |
| `ventas_adicionales_cop_mes`, `ventas_femsa_cop_mes` | Número → Moneda → COP |
| `efecto_pct_ventas` | Número (no porcentaje: ya viene en 0-114) |
| `prob_cambio` | Número |
| `ranking`, `clientes_prom_dia` | Número |
| `region`, `ciudad`, `tipo_negocio`, `zona`, `riesgo_cambio`, `seleccionada` | Texto |

4. En **Agregación**, pon `ganancia_estimada_cop_mes` en **Suma** y
   `efecto_pct_ventas` en **Media**. Si no, Looker suma los porcentajes y da cifras absurdas.

---

## Paso 2 — El filtro que define todo

Casi todo el tablero habla de **las 1.000 tiendas elegidas**, no de las 12.700.

Crea un **filtro a nivel de informe**: `seleccionada` **igual a** `Sí`
(*Recurso → Administrar filtros → Añadir filtro*).

Luego aplícalo a cada gráfico salvo los dos que comparan contra todas las elegibles
(el de temperatura y la tarjeta de "tiendas elegibles").

---

## Paso 3 — Los controles de filtro

Barra superior, de izquierda a derecha. **Añadir un control → Lista desplegable**:

| Control | Campo | Nota |
|---|---|---|
| Región | `region` | 7 valores |
| Ciudad | `ciudad` | 28 valores |
| Tipo de negocio | `tipo_negocio` | 6 valores |
| Riesgo de cambio | `riesgo_cambio` | Alto / Bajo |
| Consulta por id_tienda | `id_tienda` | usa **Control de entrada de texto**, no desplegable |

El enunciado pide explícitamente filtros por región, ciudad y tipo de negocio, y
consulta por `id_tienda`: los cinco son obligatorios.

---

## Paso 4 — Las tarjetas de KPI

**Añadir un gráfico → Tarjeta de puntuación** (una por cada uno):

| Tarjeta | Métrica | Agregación | Formato |
|---|---|---|---|
| Ganancia mensual | `ganancia_estimada_cop_mes` | Suma | Moneda COP, compacto |
| Tiendas | `id_tienda` | Recuento único | Número |
| Efecto en la selección | `efecto_pct_ventas` | Media | Número, 1 decimal, sufijo " %" |
| Ganancia por tienda | `ganancia_estimada_cop_mes` | Media | Moneda COP |
| Riesgo alto | `id_tienda` | Recuento único | + filtro `riesgo_cambio = Alto` |

---

## Paso 5 — Los gráficos

### 5.1 Mapa de las tiendas (el que más luce)

**Añadir un gráfico → Gráfico de mapa de burbujas**

- Ubicación: **`lat_long`** (debe estar como tipo Geo, ver paso 1)
- Métrica de tamaño: `ganancia_estimada_cop_mes` (Suma)
- Métrica de color: `ganancia_estimada_cop_mes`
- Filtro: `seleccionada = Sí`

Si el mapa sale vacío, el 99 % de las veces es que `lat_long` quedó como texto.

### 5.2 Nuestra lista vs las reglas simples

Este **no sale de `tablero_tiendas.csv`**: usa `salidas/comparacion_reglas.csv`
como segunda fuente de datos (impórtalo como otra hoja).

- Gráfico de **barras en columna**
- Dimensión: `estrategia` · Métrica: `ganancia_total_mes`
- Ordena de mayor a menor. Destaca la primera barra en azul y las demás en gris.

Es el gráfico que sustenta la recomendación: no lo dejes por fuera.

### 5.3 Ganancia por región · 5.4 Ganancia por tipo de negocio

- Gráfico de **barras horizontales**
- Dimensión: `region` (o `tipo_negocio`) · Métrica: `ganancia_estimada_cop_mes` (Suma)
- Orden: descendente por la métrica

### 5.5 Riesgo de cambio

- Gráfico **circular** (de anillo)
- Dimensión: `riesgo_cambio` · Métrica: `id_tienda` (Recuento único)
- Colores: Bajo `#0ca30c`, Alto `#d03b3b`

### 5.6 El efecto crece con el calor

Necesita agrupar la temperatura en bandas. Crea un **campo calculado**
(*Añadir un campo* en el panel de datos):

```
CASE
  WHEN temperatura_media_c < 16 THEN "< 16 °C"
  WHEN temperatura_media_c < 20 THEN "16-20 °C"
  WHEN temperatura_media_c < 24 THEN "20-24 °C"
  WHEN temperatura_media_c < 28 THEN "24-28 °C"
  ELSE "> 28 °C"
END
```

Llámalo `banda_temperatura`.

- Gráfico de **barras en columna**
- Dimensión: `banda_temperatura` · Métrica: `efecto_pct_ventas` (**Media**)
- **Sin** el filtro `seleccionada = Sí`: el patrón se ve sobre las 12.700 elegibles
- Ordena la dimensión manualmente de frío a caliente

### 5.7 Importancia de variables

Segunda fuente: `salidas/importancia_heterogeneidad.csv`.

- Barras horizontales · Dimensión `variable` · Métrica `importancia`
- Limita a las 8-10 primeras

---

## Paso 6 — La tabla de detalle

**Añadir un gráfico → Tabla**

Columnas sugeridas: `ranking`, `id_tienda`, `ciudad`, `tipo_negocio`,
`temperatura_media_c`, `clientes_prom_dia`, `ventas_femsa_cop_mes`,
`efecto_pct_ventas`, `ganancia_estimada_cop_mes`, `riesgo_cambio`.

- Ordena por `ganancia_estimada_cop_mes` descendente
- Activa **Paginación**
- En *Estilo*, activa **Barras de datos** en la columna de ganancia

---

## Paso 7 — Repasar contra la rúbrica

El enunciado pide que el tablero tenga:

- [ ] Filtros por **región, ciudad y tipo de negocio** → paso 3
- [ ] **Mapa** de las 1.000 tiendas → paso 5.1
- [ ] **Ganancia estimada** → paso 4 y 5.3/5.4
- [ ] **Comparación con reglas simples** → paso 5.2
- [ ] **Riesgo de cambio** → paso 5.5
- [ ] **Importancia de variables** → paso 5.7
- [ ] **Consulta por id_tienda** → paso 3

Los siete están en el mockup. Si alguno falta, se pierden puntos del criterio
*Tablero* (10 puntos).

---

## Problemas frecuentes

| Síntoma | Causa | Solución |
|---|---|---|
| El mapa sale vacío | `lat_long` quedó como texto | Cámbialo a Geo → Latitud, Longitud |
| Los porcentajes dan miles | `efecto_pct_ventas` está en Suma | Cámbialo a Media |
| Las cifras son 12,7 veces más grandes | Falta el filtro `seleccionada = Sí` | Aplícalo (paso 2) |
| `28.0` aparece como `280` | Configuración regional de la hoja | Archivo → Configuración → Estados Unidos |
| Looker no ve cambios de la hoja | Caché | En la fuente de datos, **Actualizar campos** |

---

## Durante la sustentación

El enunciado dice: *"el programa o el tablero deben funcionar durante la sustentación"*.

Lleva `mockup_tablero.html` descargado en el computador. **Abre sin internet**
(Chart.js va incrustado en el archivo). Si la wifi del salón falla o Looker no carga,
ese archivo salva la demostración.
