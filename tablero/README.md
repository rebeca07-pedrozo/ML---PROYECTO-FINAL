# Carpeta `tablero/`

Insumos para que el equipo construya el tablero en Looker Studio (Data Studio).

| Archivo | Qué es | Para quién |
|---|---|---|
| **`mockup_tablero.html`** | Tablero funcional con los datos reales. **Ábrelo con doble clic.** Es la referencia visual de lo que hay que construir. | Todo el equipo |
| **`GUIA_LOOKER_STUDIO.md`** | Instrucciones paso a paso para replicar el mockup en Looker Studio. | Quien arme el tablero |
| **`apps_script_tablero.gs`** | Código para pegar en Google Sheets (*Extensiones → Apps Script*). Crea hojas de resumen y gráficos nativos. | Quien monte la hoja |
| **`formulas_google_sheets.md`** | Las mismas tablas con fórmulas (`QUERY`, `SUMIF`), sin programar. | Alternativa al anterior |

---

## El dato de entrada

Todo sale de **`../salidas/tablero_tiendas.csv`**: 12.700 tiendas elegibles × 36 columnas.
La columna `seleccionada` marca cuáles son las 1.000 elegidas.

**No confundir con `../salidas/lista_grupoDaniJohelRebe.csv`**, que tiene solo 3 columnas:
ese es el entregable que se sube al profesor, no sirve para el tablero.

---

## Empezar en 3 pasos

1. Abre `mockup_tablero.html` en el navegador para ver a dónde vamos.
2. Sigue `GUIA_LOOKER_STUDIO.md` desde el paso 0.
3. Si algo no cuadra, revisa la tabla de *Problemas frecuentes* al final de la guía.

---

## Sobre el mockup

- **Funciona sin internet.** Chart.js va incrustado en el archivo (451 KB), así que
  abre aunque no haya conexión. Útil el día de la sustentación.
- **Datos reales**, no de ejemplo: las 1.000 tiendas seleccionadas, generadas por
  `notebooks/proyecto_final_neveras.ipynb`.
- **Es interactivo**: los filtros, el buscador por `id_tienda` y el orden de la tabla
  funcionan. Sirve para ensayar la demostración en vivo.
- Tiene modo claro y oscuro (botón *Tema* arriba a la derecha).

### Qué NO es

No es el entregable del tablero. El enunciado pide **Streamlit, Dash o Power BI**
(o Looker Studio). Este archivo es el plano, no la obra.

---

## Regenerarlo

El mockup se arma desde las salidas del cuaderno. Si cambian los datos, hay que
volver a correr `notebooks/proyecto_final_neveras.ipynb` y regenerar los CSV de
`salidas/`. El HTML trae los datos embebidos, así que no se actualiza solo.
