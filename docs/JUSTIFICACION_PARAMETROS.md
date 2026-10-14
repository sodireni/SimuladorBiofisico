# Justificación de parámetros, supuestos y texto para el informe

Leyenda: **V** verificado en la fuente · **P** plausible, con una reserva que se explica · **S** supuesto propio del equipo (no tiene fuente; se defiende con análisis de sensibilidad).

---

## 1. Resultado de la verificación

| Parámetro | Valor | Estado | Qué encontramos |
|---|---|---|---|
| `kc_ini`, `kc_mid`, `kc_end` | 0.30, 1.15, 0.25 | **V*** | Son los valores de cebada de FAO-56 (Tabla 12). *Confirmados en fuentes secundarias que reproducen la tabla* Un estudio en cebada de primavera en Chequia reportó un Kcb de mitad de temporada menor que el estándar FAO: puede haber sobrestimación local. |
| `p_agotamiento` | 0.55 | **V** | FAO-56, Tabla 22 (capítulo 8): cebada p = 0.55 para ETc ≈ 5 mm/día. FAO ajusta p con `p + 0.04 (5 - ETc)`; con ETc ≈ 4-5 mm/día el efecto es ≈ +0.02 y se ignora. |
| Profundidad de raíz | 0.6 m | **P (subestima)** | FAO-56 da 1.0-1.5 m de profundidad efectiva para cebada. Con 0.6 m el agua disponible (mediana 63 mm) está subestimada; extrapolando linealmente (sin verificar capas más profundas) a 1.0 m serían unos 105 mm. Es la limitación más importante del balance hídrico. |
| `tbase_c` | 0 °C | **V** | Base 0 °C es la que usan los estudios de fenología de cebada revisados (siembra a espigamiento y a hoja bandera). El prompt dice 0-2 °C: hacer sensibilidad con 2. Algunos trabajos usan una base mayor (~8 °C) solo para después del espigamiento. |
| `gdd_antesis_objetivo`, `gdd_madurez_objetivo` | 800, 1450 °C·d | **P** | INIFAP describe para la variedad Adabella (Valles Altos) floración a los 48-72 días y madurez fisiológica a los 90-132 días. Con ~14 °C de media (Open-Meteo) eso es ≈ 670-1,010 y 1,260-1,850 °C·d: **los umbrales son compatibles**. Cultivares de Argentina y cebada de invierno (Serbia) reportan tiempos más largos (≈ 1,040-1,290 °C·d a espigamiento; 1,223 °C·d a hoja bandera). Dependen del cultivar y no lo conocemos. |
| `par_fraccion` | 0.48 | **V** | La literatura reporta PAR/Rs entre ~0.42 y 0.55; muchos modelos usan 0.50. 0.48 está en el rango. |
| `rue_max_g_mj_par` | 1.2 | **P (mal definida)** | Los experimentos en cebada (Goyne y colaboradores, 1993) dan **2.6-2.9 g/MJ de PAR absorbida** sin limitaciones. 1.2 ≈ 0.48 × 2.5: parece una RUE por MJ de radiación **global**, no de PAR. Nuestra fórmula la aplica a PAR. Es una constante de escala: no cambia el orden entre parcelas, y con 1.2 la biomasa sale en ~6-8 t/ha, razonable para temporal. |
| `hi_base` | 0.42 | **P** | Razonable, algo menor que el HI medido en cebada de Idaho (0.46-0.52). Kemanian et al. (2007) proponen `HI = HI0 + s·fG` (fG = fracción de biomasa posterior a la antesis) y para cebada ambos parámetros rondan 0.3: con fG ≈ 0.4 da 0.42. |
| `hi_beta` | 0.5 | **S** | No tiene fuente. Preferir la opción de Kemanian (`hi_kemanian`). |
| Hargreaves-Samani | 0.0023, 17.8, raíz | **V** | FAO-56, ecuación 52. **Ra y ETo van ambos en mm/día** (1 MJ/m²/día = 0.408 mm/día). FAO recomienda verificarla y calibrarla localmente contra Penman-Monteith. |
| Radiación extraterrestre Ra | ecuación 21 | **V** | Reproducimos al decimal los ejemplos de FAO-56: 32.2 MJ/m²/día (3-sep, 20°S) y 40.6 (Lyon, 15-jul). |
| Saxton y Rawls (2006) | coeficientes | **V** | Los coeficientes de las ecuaciones de punto de marchitez, capacidad de campo, saturación y sus correcciones coinciden con el código del USDA. Validez: materia orgánica ≤ 8 %, arcilla ≤ 60 %. |
| Materia orgánica = 1.724 × C org. | 1.724 | **Pendiente** | Factor estándar (Van Bemmelen); no se verificó en esta revisión.  |
| Umbral del inicio de crecimiento | 20 % de la amplitud | **V** | Umbral relativo estándar para el inicio de temporada con series de NDVI (TIMESAT, Jönsson y Eklundh, 2004); otros trabajos calibran 20-30 %. Detecta el reverdecimiento, **no la siembra**. |
| `gdd_siembra_a_sos` | 200 °C·d | **S (probablemente bajo)** | La emergencia sola toma ~156 °C·d (Alzueta y colaboradores, 2014); falta el tiempo para que el NDVI suba 20 % de su amplitud. Probar 150-350 °C·d. Un valor mayor adelanta la siembra estimada. |
| Nubosidad ≤ 20 %, descarte de picos, mínimo de observaciones | | **S** | Criterios propios. |
| Suavizado Savitzky-Golay (grado 2, ventanas de 15 y 21 días) | | **P** | Método estándar (Savitzky y Golay, 1964). Las ventanas son elección propia. |
| Calibración NDVI Planet → FAPAR Sentinel-2 | R² 0.97, RMSE 0.036 | **V (propia)** | Regresión lineal robusta con ~8,700 pares parcela-fecha; no usa rendimiento. Sentinel-2 es a su vez un producto derivado. |
| Open-Meteo | | **V** | Licencia CC BY 4.0 con atribución obligatoria. Reanálisis ERA5-Land (0.1°, ~11 km); selecciona la celda por elevación con un modelo de 90 m. |
| Época de siembra de referencia | | **Pendiente** | Fuentes encontradas (INIFAP-CEZAC y prensa) dan ventanas desde la segunda quincena de mayo hasta finales de julio: **no separan el escenario A (14-29 may) del B (9-jul a 8-ago)**. Buscar una fuente INIFAP de Valles Altos. |


## Cambios del 10-oct-2026

| Parámetro | Valor anterior | Valor actual | Estado | Razón |
|---|---|---|---|---|
| `cultivo.rue_max_g_mj_par` | 1.2 | 2.5 | P | Se aplica a la PAR absorbida. La literatura de cebada reporta 2.6-2.9 g/MJ (Goyne et al., 1993). El 1.2 anterior parecía una RUE sobre radiación global. Es una constante de escala: no cambia el orden entre parcelas. |
| `cultivo.hi_base` | 0.42 | 0.45 | S | Valor usado en el módulo 4 del equipo. Sin fuente específica; pendiente de justificar. |
| `lue.hi_opcion` | (no existía) | "C" | S | Fórmula del equipo que penaliza el estrés de antesis y de llenado. La opción B (Kemanian et al., 2007) queda como sensibilidad. |
| `lue.hi_sens_antesis`, `lue.hi_sens_llenado` | (no existían) | 0.5 y 0.3 | S | Sin fuente. |
| `clima.factor_eto` | (no existía) | 1.0 | S | Hargreaves sin corrección. La sensibilidad con 1.09 viene del cociente global 0.917 frente a la ETo de Open-Meteo. |
| `fenologia.gdd_variables_ref` | (no existía) | "pico_ndvi" | S | Evita que GDD_antesis y GDD_llenado queden casi constantes en el modo umbral. GDD_llenado llega hasta la caída del fPAR a la mitad del pico; llegar hasta la madurez por umbral dejaba GDD_llenado en 0 en 61 de 197 parcelas. |