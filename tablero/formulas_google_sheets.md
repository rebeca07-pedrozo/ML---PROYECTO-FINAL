# Fórmulas para Google Sheets (alternativa sin Apps Script)

Si prefieren no usar Apps Script, estas fórmulas arman las mismas tablas de resumen.
Péguenlas en una hoja nueva llamada **Resumen**, con los datos importados en una
pestaña llamada **`tablero_tiendas`**.

> Si al pegar una fórmula Sheets reclama por los `;`, cámbienlos por `,`.
> Depende de la configuración regional del archivo.

---

## 1. Indicadores principales

| Celda | Fórmula | Qué da |
|---|---|---|
| Ganancia mensual total | `=SUMIF(tablero_tiendas!AE:AE;"Sí";tablero_tiendas!AC:AC)` | COP/mes |
| Tiendas seleccionadas | `=COUNTIF(tablero_tiendas!AE:AE;"Sí")` | 1.000 |
| Tiendas elegibles | `=COUNTA(tablero_tiendas!A2:A)` | 12.700 |
| Ganancia promedio | `=AVERAGEIF(tablero_tiendas!AE:AE;"Sí";tablero_tiendas!AC:AC)` | COP/mes |
| Efecto promedio | `=AVERAGEIF(tablero_tiendas!AE:AE;"Sí";tablero_tiendas!AA:AA)` | % |
| Riesgo alto | `=COUNTIFS(tablero_tiendas!AE:AE;"Sí";tablero_tiendas!AG:AG;"Alto")` | tiendas |
| Tiendas rentables | `=COUNTIF(tablero_tiendas!AC:AC;">0")` | de las 12.700 |

> **Verifiquen las letras de columna.** Dependen del orden en que quedó el CSV.
> Para no adivinar, usen la versión robusta con `INDEX/MATCH` que está abajo.

### Versión robusta (no depende de la letra de la columna)

```
=SUMIF(
   INDEX(tablero_tiendas!$A:$AJ;0;MATCH("seleccionada";tablero_tiendas!$A$1:$AJ$1;0));
   "Sí";
   INDEX(tablero_tiendas!$A:$AJ;0;MATCH("ganancia_estimada_cop_mes";tablero_tiendas!$A$1:$AJ$1;0))
 )
```

Cambiando el nombre entre comillas sirve para cualquier columna.

---

## 2. Resumen por región (con QUERY)

```
=QUERY(tablero_tiendas!A:AJ;
  "select B, count(A), sum(AC), avg(AA)
   where AE = 'Sí'
   group by B
   order by sum(AC) desc
   label B 'Región', count(A) 'Tiendas', sum(AC) 'Ganancia total', avg(AA) 'Efecto %'";1)
```

Cambien `B` por la columna de la dimensión que quieran:

| Dimensión | Columna |
|---|---|
| region | B |
| ciudad | D |
| tipo_negocio | F |
| zona | E |

---

## 3. Las 20 mejores tiendas

```
=QUERY(tablero_tiendas!A:AJ;
  "select A, D, F, AA, AC, AG
   where AE = 'Sí'
   order by AC desc
   limit 20
   label A 'Tienda', D 'Ciudad', F 'Tipo', AA 'Efecto %', AC 'Ganancia', AG 'Riesgo'";1)
```

---

## 4. Consulta por id_tienda

En `B1` escriban el id (ej. `T02355`). En `A3`:

```
=IFERROR(
   TRANSPOSE(tablero_tiendas!A1:AJ1);
   "")
```

En `B3`:

```
=IFERROR(
   TRANSPOSE(FILTER(tablero_tiendas!A2:AJ; EXACT(UPPER(tablero_tiendas!A2:A); UPPER($B$1))));
   "No existe esa tienda entre las elegibles")
```

Queda la ficha completa de la tienda en vertical.

---

## 5. Efecto por banda de temperatura

En una columna auxiliar de la hoja de datos (digamos `AK2`, y la arrastran):

```
=IF(J2<16;"< 16 °C";IF(J2<20;"16-20 °C";IF(J2<24;"20-24 °C";IF(J2<28;"24-28 °C";"> 28 °C"))))
```

(`J` es `temperatura_media_c`; verifiquen la letra.)

Luego:

```
=QUERY(tablero_tiendas!A:AK;
  "select AK, avg(AA), count(A)
   group by AK
   label AK 'Banda', avg(AA) 'Efecto promedio %', count(A) 'Tiendas'";1)
```

Sin filtrar por `seleccionada`: el patrón se ve mejor sobre las 12.700 elegibles.

---

## 6. Formatos

Seleccionen las columnas de dinero y pongan **Formato → Número → Moneda personalizada**:

```
$ #,##0
```

Para porcentajes que ya vienen en escala 0-100 (como `efecto_pct_ventas`),
usen formato de número con un decimal y el sufijo manual, **no** formato de porcentaje
(este multiplicaría por 100 otra vez).
