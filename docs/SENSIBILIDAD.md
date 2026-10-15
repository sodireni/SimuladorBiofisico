# Análisis de sensibilidad

Generado el 2026-10-15 con `scripts/sensibilidad.py` sobre 197 parcelas. Cada escenario cambia un solo supuesto y deja los demás en el caso base. No se usó el rendimiento.

## Cómo leer las tablas

- Cada celda muestra el **cambio mediano por parcela** respecto al caso base, en %, y entre paréntesis la **correlación de Spearman (ρ)** entre los valores del escenario y los del caso base.
- ρ cercano a 1 significa que el **orden entre parcelas casi no cambia**, que es lo que le importa a un modelo de aprendizaje; un cambio grande de magnitud con ρ cercano a 1 solo cambia la escala.
- "sin cambio" significa que la variable no se movió en ninguna parcela. "n/d" significa que la variable quedó constante y ρ no se puede calcular.
- Criterio de lectura (arbitrario, solo para señalar casos): magnitud ≥ 10 % o ρ < 0.90.

## Caso base

| Variable | Mínimo | Mediana | Máximo |
| --- | --- | --- | --- |
| GDD_antesis | 588.90 | 1,273.65 | 2,160.90 |
| GDD_llenado | 122.60 | 801.80 | 1,834.85 |
| DAP_antesis_est | 48.00 | 56.00 | 66.00 |
| ETo_acum | 361.18 | 382.07 | 411.14 |
| ETa_acum | 235.16 | 281.44 | 301.08 |
| Deficit_Hidrico_Total | 91.79 | 101.33 | 150.91 |
| KS_prom_antesis | 0.92 | 1.00 | 1.00 |
| KS_prom_llenado | 0.64 | 1.00 | 1.00 |
| fPAR_integrado | 21.91 | 42.75 | 63.47 |
| Biomasa_Antesis_Sim | 1,943.93 | 4,444.24 | 8,051.62 |
| Biomasa_Total_Sim | 5,858.49 | 11,352.06 | 17,092.30 |
| HI_penalizado | 0.39 | 0.45 | 0.45 |
| Deficit_ETc | 0.00 | 0.29 | 52.59 |

Ciclos sin madurez antes del 30-nov: 0. Parcelas donde el fPAR no cae a la mitad del pico: 5. Parcelas con GDD_llenado = 0: 0.

## Resultados por escenario

### M1 clima

| Escenario | ETa_acum | KS_prom_llenado | Biomasa_Total_Sim | HI_penalizado | GDD_antesis | GDD_llenado | DAP_antesis_est | Ciclos incompletos | GDD_llenado = 0 |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| ETo con factor 1.09 (base 1.0) | +8.8 % (ρ 0.98) | +0.0 % (ρ 0.89) | -0.1 % (ρ 0.99) | +0.0 % (ρ 0.89) | sin cambio | sin cambio | sin cambio | 0 | 0 |

### M2 fenología

| Escenario | ETa_acum | KS_prom_llenado | Biomasa_Total_Sim | HI_penalizado | GDD_antesis | GDD_llenado | DAP_antesis_est | Ciclos incompletos | GDD_llenado = 0 |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| Tbase 2 °C (base 0 °C) | +15.1 % (ρ 0.95) | +0.0 % (ρ 0.91) | +21.1 % (ρ 0.98) | +0.0 % (ρ 0.91) | -14.3 % (ρ 1.00) | -15.3 % (ρ 1.00) | +18.2 % (ρ 0.99) | 1 | 0 |
| Modo satelital (antesis = pico de NDVI; madurez = fPAR a la mitad del pico) | +35.8 % (ρ 0.25) | +0.0 % (ρ 0.35) | +51.6 % (ρ 0.32) | +0.0 % (ρ 0.42) | sin cambio | sin cambio | +61.4 % (ρ -0.12) | 6 | 0 |

### Siembra

| Escenario | ETa_acum | KS_prom_llenado | Biomasa_Total_Sim | HI_penalizado | GDD_antesis | GDD_llenado | DAP_antesis_est | Ciclos incompletos | GDD_llenado = 0 |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| Siembra fija el 5-may en las 197 parcelas (197 parcelas cambian de fecha) | -2.8 % (ρ 0.83) | +0.0 % (ρ 0.64) | -34.0 % (ρ 0.64) | +0.0 % (ρ 0.64) | +31.1 % (ρ 0.86) | sin cambio | -9.6 % (ρ 0.79) | 0 | 0 |
| Doble ciclo: escenario B (siembra del ciclo principal) (31 parcelas cambian de fecha) | +0.0 % (ρ 0.72) | +0.0 % (ρ 0.78) | +0.0 % (ρ 0.70) | +0.0 % (ρ 0.78) | +0.0 % (ρ 0.49) | sin cambio | +0.0 % (ρ 0.91) | 6 | 0 |

### M3 balance hídrico

| Escenario | ETa_acum | KS_prom_llenado | Biomasa_Total_Sim | HI_penalizado | GDD_antesis | GDD_llenado | DAP_antesis_est | Ciclos incompletos | GDD_llenado = 0 |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| Agua inicial 0.3·AWC (base 0.5) | +0.0 % (ρ 1.00) | sin cambio | +0.0 % (ρ 1.00) | sin cambio | sin cambio | sin cambio | sin cambio | 0 | 0 |
| Agua inicial 0.8·AWC (base 0.5) | +0.0 % (ρ 1.00) | sin cambio | +0.0 % (ρ 1.00) | sin cambio | sin cambio | sin cambio | sin cambio | 0 | 0 |
| AWC sin corrección por grava | +0.0 % (ρ 0.98) | +0.0 % (ρ 1.00) | +0.0 % (ρ 1.00) | +0.0 % (ρ 1.00) | sin cambio | sin cambio | sin cambio | 0 | 0 |

### M4 biomasa

| Escenario | ETa_acum | KS_prom_llenado | Biomasa_Total_Sim | HI_penalizado | GDD_antesis | GDD_llenado | DAP_antesis_est | Ciclos incompletos | GDD_llenado = 0 |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| RUE 1.2 g/MJ (base 2.5) | sin cambio | sin cambio | -52.0 % (ρ 1.00) | sin cambio | sin cambio | sin cambio | sin cambio | 0 | 0 |
| RUE 2.6 g/MJ (base 2.5) | sin cambio | sin cambio | +4.0 % (ρ 1.00) | sin cambio | sin cambio | sin cambio | sin cambio | 0 | 0 |

### M4 índice de cosecha

| Escenario | ETa_acum | KS_prom_llenado | Biomasa_Total_Sim | HI_penalizado | GDD_antesis | GDD_llenado | DAP_antesis_est | Ciclos incompletos | GDD_llenado = 0 |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| HI opción A (lineal), hi_beta 0.3 | sin cambio | sin cambio | sin cambio | +0.0 % (ρ 1.00) | sin cambio | sin cambio | sin cambio | 0 | 0 |
| HI opción A (lineal), hi_beta 0.5 | sin cambio | sin cambio | sin cambio | +0.0 % (ρ 1.00) | sin cambio | sin cambio | sin cambio | 0 | 0 |
| HI opción A (lineal), hi_beta 0.7 | sin cambio | sin cambio | sin cambio | +0.0 % (ρ 1.00) | sin cambio | sin cambio | sin cambio | 0 | 0 |
| HI opción B (Kemanian et al., 2007) | sin cambio | sin cambio | sin cambio | +7.7 % (ρ 0.19) | sin cambio | sin cambio | sin cambio | 0 | 0 |

### Variables GDD

| Escenario | ETa_acum | KS_prom_llenado | Biomasa_Total_Sim | HI_penalizado | GDD_antesis | GDD_llenado | DAP_antesis_est | Ciclos incompletos | GDD_llenado = 0 |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| GDD con la antesis por umbral (definición de la guía) | sin cambio | sin cambio | sin cambio | sin cambio | -36.8 % (ρ -0.11) | -18.5 % (ρ -0.14) | sin cambio | 0 | 0 |
| GDD_llenado del pico a la madurez del modo activo (versión descartada) | sin cambio | sin cambio | sin cambio | sin cambio | sin cambio | -78.3 % (ρ 0.39) | sin cambio | 0 | 61 |

## Lectura automática

Solo se listan los escenarios y variables que superan el criterio de lectura. Las conclusiones para el reporte las redacta el equipo.

- **ETo con factor 1.09 (base 1.0)**: KS_prom_llenado cambia el orden entre parcelas; HI_penalizado cambia el orden entre parcelas.
- **Tbase 2 °C (base 0 °C)**: ETa_acum cambia la magnitud; Biomasa_Total_Sim cambia la magnitud; GDD_antesis cambia la magnitud; GDD_llenado cambia la magnitud; DAP_antesis_est cambia la magnitud.
- **Modo satelital (antesis = pico de NDVI; madurez = fPAR a la mitad del pico)**: ETa_acum cambia la magnitud y el orden entre parcelas; KS_prom_llenado cambia el orden entre parcelas; Biomasa_Total_Sim cambia la magnitud y el orden entre parcelas; HI_penalizado cambia el orden entre parcelas; DAP_antesis_est cambia la magnitud y el orden entre parcelas.
- **Siembra fija el 5-may en las 197 parcelas**: ETa_acum cambia el orden entre parcelas; KS_prom_llenado cambia el orden entre parcelas; Biomasa_Total_Sim cambia la magnitud y el orden entre parcelas; HI_penalizado cambia el orden entre parcelas; GDD_antesis cambia la magnitud y el orden entre parcelas; DAP_antesis_est cambia el orden entre parcelas.
- **Doble ciclo: escenario B (siembra del ciclo principal)**: ETa_acum cambia el orden entre parcelas; KS_prom_llenado cambia el orden entre parcelas; Biomasa_Total_Sim cambia el orden entre parcelas; HI_penalizado cambia el orden entre parcelas; GDD_antesis cambia el orden entre parcelas.
- **RUE 1.2 g/MJ (base 2.5)**: Biomasa_Total_Sim cambia la magnitud.
- **HI opción B (Kemanian et al., 2007)**: HI_penalizado cambia el orden entre parcelas.
- **GDD con la antesis por umbral (definición de la guía)**: GDD_antesis cambia la magnitud y el orden entre parcelas; GDD_llenado cambia la magnitud y el orden entre parcelas.
- **GDD_llenado del pico a la madurez del modo activo (versión descartada)**: GDD_llenado cambia la magnitud y el orden entre parcelas.

## Parámetros del caso base

| Parámetro | Valor |
| --- | --- |
| fenologia.tbase_c | 0.0 |
| fenologia.modo | umbral_gdd |
| fenologia.gdd_variables_ref | pico_ndvi |
| clima.factor_eto | 1.0 |
| suelo.sw_inicial_frac_awc | 0.5 |
| cultivo.p_agotamiento | 0.55 |
| cultivo.rue_max_g_mj_par | 2.5 |
| cultivo.hi_base | 0.45 |
| lue.hi_opcion | C |
| lue.hi_sens_antesis | 0.5 |
| lue.hi_sens_llenado | 0.3 |

Detalle de todas las variables y escenarios: `data/processed/sensibilidad_resumen.csv`.

## Conclusiones

Se probaron 15 escenarios, uno a la vez, sobre las 197 parcelas. Ninguno se evaluó con rendimiento. Los resultados no llevaron a cambiar ningún parámetro del caso base.

**Supuestos que cambian el orden entre parcelas.**
- Fecha de siembra: con siembra fija el 5-may, la biomasa cambia -34 % (ρ 0.64) y GDD_antesis +31 % (ρ 0.86). Es el supuesto más influyente, y no se conocen fechas reales de siembra.
- Doble ciclo: el escenario B altera el orden en las 31 parcelas afectadas (ρ de GDD_antesis 0.49) y deja 6 ciclos sin madurez antes del 30-nov.
- Modo de fenología: el modo satelital produce una fenología muy distinta (ρ de ETa_acum 0.25, de biomasa 0.32, de DAP_antesis_est -0.12).
- Índice de cosecha: la opción de Kemanian et al. (2007) casi no se relaciona con la opción base (ρ 0.19). En el caso base HI_penalizado vale 0.45 en 149 de 197 parcelas, por lo que aporta poca variación.
- Definición de GDD_antesis: con la antesis por umbral (definición de la guía) el orden cambia por completo (ρ -0.11).

**Supuestos que solo cambian la magnitud (ρ ≥ 0.95).** RUE (1.2 g/MJ: biomasa -52 %, ρ 1.00), Tbase 2 °C (biomasa +21 %, ETa +15 %; refleja que los umbrales de 800 y 1,450 °C·d no se recalibraron) y factor de ETo 1.09 (ETa +8.8 %, biomasa -0.1 %).

**Supuestos sin efecto apreciable.** Agua inicial (0.3 y 0.8 de AWC), AWC con o sin grava, y hi_beta de la opción A.

**Implicaciones.** Biomasa_Total_Sim es útil para ordenar parcelas, no como valor absoluto. Las variables de fenología (GDD, DAP) dependen de la fecha de siembra estimada. HI_penalizado tiene poca variación.
