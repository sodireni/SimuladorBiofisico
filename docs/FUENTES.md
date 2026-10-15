# Fuentes de datos y referencias

## Datos del Comité Organizador (Reto AgroCebada FIRA 2026)
|         Dato          |       Fuente                                      |  Uso en el simulador |
|-----------------------|---------------------------------------------------|----------------------|
| Parcelas (shapefile)  | Comité Organizador                                | Centroides (lat/lon) |
| Elevación y pendiente | INEGI, Continuo de Elevaciones Mexicano 4.0       | Variables topográficas |
| Precipitación mensual | CHIRPS (Funk et al., 2015)                        | Control de calidad de la lluvia diaria |
| Tmin y Tmax mensuales | CHIRTS-ERA5 (Climate Hazards Center, 2025)        | Control de calidad de temperatura |
| Índices satelitales | Sentinel-2, Landsat y Planet (dataset Básico y PRO) | fPAR y series de vegetación |

## Datos externos
| Dato | Fuente | Periodo | Archivo generado |
|---|---|---|---|
| Clima diario (Tmax, Tmin, precipitación, radiación solar, ET0) | Open-Meteo Historical Weather API (reanálisis ERA5 / ERA5-Land) | 15-mar-2025 a 30-nov-2025 | `data/external/clima_diario_*_2025.csv` |

Script: `src/ingest/descargar_clima_diario_2025.py`
| Suelo: arcilla, arena, limo, densidad aparente, carbono orgánico y fragmentos gruesos, 4 capas hasta 60 cm | SoilGrids 2.0 (ISRIC, CC BY 4.0), vía WCS en maps.isric.org (la API REST estaba pausada) | consultado en octubre de 2026 | `data/external/soilgrids/*.tif` |

## Referencias
- Zippenfenig, P. (2023). Open-Meteo.com Weather API. Zenodo. https://doi.org/10.5281/zenodo.7970649 (licencia CC BY 4.0)
- Hersbach, H. et al. (2020). The ERA5 global reanalysis. Quarterly Journal of the Royal Meteorological Society, 146, 1999-2049.
- Muñoz-Sabater, J. et al. (2021). ERA5-Land: a state-of-the-art global reanalysis dataset for land applications. Earth System Science Data, 13, 4349-4383.
- Funk, C. et al. (2015). The climate hazards infrared precipitation with stations. Scientific Data, 2, 150066.
- Allen, R. G. et al. (1998). Crop evapotranspiration (FAO Irrigation and Drainage Paper 56). FAO.
- Hargreaves, G. H. y Samani, Z. A. (1985). Reference crop evapotranspiration from temperature. Applied Engineering in Agriculture, 1(2), 96-99.
- Poggio, L. et al. (2021). SoilGrids 2.0: producing soil information for the globe with quantified spatial uncertainty. SOIL, 7, 217-240. https://doi.org/10.5194/soil-7-217-2021
- Saxton, K. E. y Rawls, W. J. (2006). Soil water characteristic estimates by texture and organic matter for hydrologic solutions. Soil Science Society of America Journal, 70, 1569-1578.
- Servicio Meteorológico Nacional (SMN-CONAGUA). Normales climatológicas, estaciones Zoquiapan (29034), Tocatlán (29027) y Hueyotlipan (29010), Tlaxcala. https://smn.conagua.gob.mx
- Monteith, J. L. (1977). *Climate and the efficiency of crop production in Britain*. Philosophical Transactions of the Royal Society B, 281(980), 277–294. https://doi.org/10.1098/rstb.1977.0140  
  Base conceptual del modelo de eficiencia de uso de la radiación: la biomasa se relaciona con la radiación interceptada y la eficiencia de conversión.
- Goyne, P. J., Milroy, S. P., Lilley, J. M., & Hare, J. M. (1993). *Radiation interception, radiation use efficiency and growth of barley cultivars*. Australian Journal of Agricultural Research, 44(6), 1351–1366. https://doi.org/10.1071/AR9931351  
  Referencia de RUE para cebada basada en PAR absorbida; reporta aproximadamente 2.60–2.90 g de biomasa por MJ de PAR absorbida bajo condiciones no limitantes.
- Kemanian, A. R., Stöckle, C. O., Huggins, D. R., & Viega, L. M. (2007). *A simple method to estimate harvest index in grain crops*. Field Crops Research, 103(3), 208–216. https://doi.org/10.1016/j.fcr.2007.06.007  
  Fundamenta la opción B del índice de cosecha: HI = HI0 + s·fG, donde fG es la fracción de biomasa acumulada después de antesis. Para cebada, HI0 y s se encuentran aproximadamente alrededor de 0.3.

## Supuestos y limitaciones

Esta sección empieza con un resumen de los supuestos que más pesan en los resultados y el estado de su análisis de sensibilidad. Después sigue el detalle por tema: alcance y respuestas de FIRA, datos de entrada, fecha de siembra, módulos, variables derivadas y resultados que conviene explicar. Las cifras de resultados vienen de la corrida con las 197 parcelas.

### Resumen de supuestos clave

| # | Supuesto | Valor usado | Sensibilidad |
|---|---|---|---|
| 1 | Fecha de siembra | Estimada con NDVI de Planet; mediana 1-jun (p10 19-may, p90 22-jul) | Umbral de NDVI de 10 % y 30 %: hecha (−7 y +6 días). Siembra fija al 5-may: Umbral de NDVI de 10 % y 30 %: −7 y +6 días. Siembra fija al 5-may: biomasa −34 % (ρ 0.64), GDD_antesis +31 %. Influyente. |
| 2 | Doble ciclo (31 parcelas) | Escenario A (siembra del primer ciclo, mediana 25-may) | Escenario A contra B (mediana 26-jul): Escenario B: cambia el orden en las 31 parcelas (ρ de GDD_antesis 0.49) y deja 6 ciclos sin madurez. Influyente. |
| 3 | Temperatura | Open-Meteo; CHIRTS no se usa | No aplica |
| 4 | ETo | Hargreaves-Samani sin corrección (factor 1.0) | Factor 1.09: Factor 1.09: ETa +8.8 %, biomasa −0.1 %. Solo escala. |
| 5 | Fenología | Antesis a 800 °C·d y madurez a 1,450 °C·d, Tbase 0 °C | Tbase 2 °C y modo satelital: Tbase 2 °C: solo escala (biomasa +21 %, ρ 0.98). Modo satelital: orden muy distinto (ρ 0.25 a 0.32). Influyente. |
| 6 | GDD_antesis y GDD_llenado | Calculados con el pico de NDVI y la caída del fPAR | Definición de la guía (con la antesis por umbral): Antesis por umbral: ρ −0.11. Versión descartada: 61 parcelas con GDD_llenado = 0. |
| 7 | Balance hídrico | Un depósito de 0-60 cm, p = 0.55, agua inicial = PWP + 0.5·AWC | Agua inicial 0.3, 0.5 y 0.8, y AWC con y sin grava: Sin efecto: agua inicial y grava cambian ETa 0.0 % (ρ ≥ 0.98). |
| 8 | Eficiencia de uso de la luz (RUE) | 2.5 g/MJ de PAR absorbida | RUE 1.2 y 2.6: RUE 1.2: biomasa −52 % con ρ 1.00; RUE 2.6: +4 %. Solo escala. |
| 9 | Índice de cosecha (HI) | HI base 0.45 con penalización por estrés (sensibilidades 0.5 y 0.3) | Alternativa de Kemanian et al. (2007): Kemanian: ρ 0.19 contra la opción base. Influyente. |
| 10 | Procesos omitidos | Sin escurrimiento, riego ni ascenso capilar | No aplica (limitación) |

### 1. Alcance y respuestas de FIRA

- **Ventana de análisis.** 15-mar a 30-nov de 2025 (clima y satélite). Se amplió desde el 31-oct porque varias parcelas seguían verdes a finales de octubre (senescencia y cosecha en noviembre). El control de calidad de lluvia contra CHIRPS solo cubre abril-octubre.
- **Respuestas de FIRA** (segunda sesión de preguntas, 9-oct-2026):
  - La cebada de las parcelas se cultivó bajo condiciones de temporal, lo cual es consistente con un balance hídrico sin riego.
  - El rendimiento corresponde a grano en t/ha, reportado en su mayoría por la empresa comercializadora y en menor proporción por el productor.
  - Las variedades fueron principalmente Josefa (seis hileras, predominante) y Voyager (dos hileras), sin identificación por parcela.
  - No se cuenta con fecha exacta de siembra, dosis de siembra, historial de cultivos ni registro de siniestros por parcela.
  - Como referencia de siembra se mencionó el inicio en los primeros días de mayo, con variación según el clima y las prácticas locales.
- **Tamaño de las parcelas frente a los datos.** El área va de 0.4 a 64 ha (mediana 5.5 ha). Un píxel de SoilGrids equivale a 6.25 ha y uno de topografía a 1.4 ha, por lo que cerca de la mitad de las parcelas es más chica que un píxel de suelo y su valor representa también terreno vecino. El clima (Open-Meteo, ~0.1°) y el suelo varían poco entre parcelas por la misma razón.
- **Tabla base** (`data/processed/parcelas_base.csv`). Una fila por parcela con ubicación, topografía, siembra y suelo, verificada automáticamente (197 parcelas sin repetidos, división 138/59, siembras dentro de la ventana y antes del pico de NDVI). No incluye rendimiento. El escenario de siembra de las 31 parcelas de doble ciclo se elige en `configs/params.yaml` y hoy está en A, de forma provisional.

### 2. Datos de entrada

#### Clima

- **Resolución.** El clima viene de un reanálisis de ~0.1°, por lo que varias parcelas comparten la misma serie.
- **Control de calidad de la lluvia.** La suma diaria de Open-Meteo (abril-octubre 2025) se comparó con el CHIRPS mensual del reto en el centroide de cada parcela. Total medio: 1,015 mm (Open-Meteo) frente a 961 mm (CHIRPS), +6 %. Razón mensual entre 0.84 y 1.24, sin sesgo sistemático. La variación espacial entre parcelas es pequeña en ambas fuentes por su resolución (5-10 km).
- **Control de calidad de la temperatura.** Open-Meteo se comparó con CHIRTS-ERA5 (rasters mensuales del reto) en el centroide de cada parcela, con 3 estaciones del SMN y con el gradiente de altitud (`src/ingest/qc_temperatura_vs_chirts.py`, `qc_gradiente_altitud.py`, `qc_estaciones_smn.py`).
  - Frente a CHIRTS, Open-Meteo es 3.8 °C más fría en Tmax y 4.3 °C en Tmin (abril-noviembre 2025).
  - Gradiente con la altitud entre parcelas (°C/km): Open-Meteo, Tmax −9.0 y Tmin −5.8; CHIRTS, Tmax −1.2 y Tmin +1.4 (no resuelve la altitud de las parcelas).
  - Contra las normales del SMN en el punto de las estaciones Zoquiapan (29034), Tocatlán (29027) y Hueyotlipan (29010), con la altitud de cada estación, el sesgo medio abril-noviembre es: Open-Meteo, Tmax −1.5, Tmin +1.6 y Tmean 0.0 °C (+4 °C·d); CHIRTS, Tmax +1.1, Tmin +4.7 y Tmean +2.9 °C (+707 °C·d).
  - **Decisión:** la temperatura del simulador proviene de Open-Meteo y CHIRTS no se usa.
- **Limitaciones de la temperatura.**
  - El rango térmico diario de Open-Meteo es ~3 °C más angosto que el de las estaciones, lo que podría subestimar la ETo de Hargreaves (~10 %, estimación aproximada).
  - Las normales del SMN son promedios de 30 años (Hueyotlipan, 1971-2000) y no el año 2025, por lo que parte de la diferencia puede ser variabilidad real (junio de 2025 fue muy lluvioso).
  - Las 3 estaciones están en Tlaxcala y no cubren las parcelas de Puebla e Hidalgo.
  - Los rasters de CHIRTS-ERA5 del reto tienen un sesgo cálido (Tmean +2.9 °C frente a estaciones) y su uso como variable debe considerarlo.

#### Topografía

- **Fuente y método.** Elevación y pendiente del CEM 4.0 de INEGI (120 m), media dentro del polígono de cada parcela (`src/ingest/extraer_topografia.py`). La pendiente se entrega en grados y se convierte a % con tan(grados)×100. Elevación media 2,667 m (2,497-2,905), pendiente media 2.9°.

#### Satélite y fPAR

- **Sensores y filtros.** FAPAR de Sentinel-2 (Dataset Básico) y NDVI de Planet (Dataset PRO), usados por separado, sin mezclar sensores. Filtros: nubosidad ≤ 20 %, valores vacíos descartados, picos aislados removidos (mediana móvil de 5 observaciones, umbral 0.25). Interpolación lineal diaria y suavizado Savitzky-Golay (grado 2; ventanas de 21 días para Sentinel-2 y 15 para Planet). Script: `src/ingest/limpiar_satelite.py`.
- **Hueco en Sentinel-2.** Del 16 al 29 de junio y del 7 al 13 de julio de 2025 no hay observaciones válidas de ninguna parcela (nubosidad). Por eso el fPAR diario se obtiene del NDVI de Planet.
- **fPAR diario.** NDVI de Planet convertido a FAPAR con un ajuste lineal contra el FAPAR de Sentinel-2 en las fechas coincidentes (7,207 pares parcela-fecha): FAPAR = 1.04·NDVI − 0.14, R² = 0.974, RMSE = 0.035. Se descartó el 3.6 % de los pares con un criterio robusto (residuo > 3 MAD). No se usó el rendimiento. Script: `src/ingest/calibrar_fpar.py`. La serie resultante (`fapar_final`) se acota a [0, 0.95].
  - **Limitación:** el ajuste es lineal, y Sentinel-2 es a su vez un producto derivado, no una medición directa de campo.

#### Suelo

- **Extracción.** Media de cada capa de SoilGrids dentro del polígono de la parcela (`src/ingest/extraer_suelo.py`). Los píxeles con arcilla, arena, limo o densidad igual a 0 (2.1 % del área descargada) se trataron como sin dato. Las 197 parcelas tienen las 4 capas. Textura media: franco arcilloso (arcilla 29 %, arena 44 %, limo 28 %).
- **Agua disponible.** Capacidad de campo y punto de marchitez por capa con Saxton y Rawls (2006), materia orgánica = carbono orgánico × 1.724 acotada a 8 %, y corrección por fragmentos gruesos (mediana 18 %). Agua disponible en 0-60 cm: mediana 62.7 mm (rango 58-68); sin la corrección por grava, 76.8 mm. La variación entre parcelas es muy pequeña (rango intercuartil de ~3 mm).
- **Limitaciones del suelo.**
  - SoilGrids es una predicción a 250 m y no una medición de la parcela.
  - Las ecuaciones de Saxton y Rawls provienen de suelos de Estados Unidos, y la saturación estimada (0.46) difiere de la porosidad por densidad aparente (0.53; correlación entre parcelas 0.53).
  - La profundidad de raíz se fijó en 60 cm (0-60 cm), por debajo de lo que puede alcanzar la cebada. Con ~34 mm de agua fácilmente aprovechable, el balance es sensible a periodos secos de 7 a 8 días.

### 3. Fecha de siembra y doble ciclo

- **Hallazgo.** La vegetación de la cebada empieza a crecer entre junio y agosto según la parcela (cultivo de temporal), por lo que la fecha de siembra se estima por parcela y no se fija en abril.
- **Estimación de la siembra (supuesto).** No hay registros, así que se estimó por parcela con el NDVI de Planet (`src/ingest/estimar_siembra.py`). Se toma el inicio de crecimiento sostenido (20 % de la amplitud del NDVI, contando hacia atrás desde el pico) y se retroceden 200 °C·d (Tbase 0 °C) hasta la siembra.
  - Resultado: mediana 1-jun (p10 19-may, p90 22-jul).
  - Sensibilidad realizada: con umbral de 10 % el inicio se adelanta 7 días (mediana), con 30 % se atrasa 6.
  - No se validó con fechas reales.
  - La emergencia por sí sola requiere ~156 °C·d (Alzueta et al., 2014), por lo que los 200 °C·d podrían quedar cortos y las fechas estimadas, sesgadas hacia tarde.
- **Frente a la referencia de FIRA.** La fecha estimada (mediana 1-jun, p10 19-may) es posterior a la referencia de principios de mayo. La referencia no es una fecha por parcela y puede variar, por lo que no se usa para corregir la estimación base; se incluye una sensibilidad con siembra fija al 5-may.
- **Verificación fisiológica.** En las parcelas de ciclo simple, la mediana de grados-día entre la siembra estimada y el pico de NDVI es 1,224 °C·d (Tbase 0 °C), mayor que el umbral de antesis del prompt (800 °C·d). Esto no demuestra que el umbral esté mal: el pico de NDVI suele ocurrir semanas después de la antesis, porque el verdor sigue alto en el llenado temprano.
- **Doble ciclo.** 31 de 197 parcelas (16 %) muestran un primer ciclo de NDVI (pico previo mediano 0.60) que cae a ~0.32 entre el 10-jul y el 5-ago, antes del ciclo principal. Causas posibles: corte de forraje o pastoreo (doble propósito), daño o resiembra; no se pudo determinar.
  - Escenario A (adoptado de forma provisional, parámetro `siembra.escenario_doble_ciclo`): siembra del primer ciclo, mediana 25-may en estas 31 parcelas.
  - Escenario B: siembra del ciclo principal, mediana 26-jul.
  - El conteo depende de la prominencia mínima del pico previo (37 con 0.12, 31 con 0.20, 11 con 0.30). El detector omite dobles ciclos cuyo segundo ciclo inicia antes de que el primero caiga del todo.
- **Doble propósito sin respuesta.** Se preguntó a FIRA si cortar o pastorear en julio es práctica común y no se obtuvo respuesta. La referencia de siembra de principios de mayo queda más cerca del escenario A (mediana 25-may) que del B (mediana 26-jul), pero no demuestra cuál es el correcto.

### 4. Módulos del simulador

#### Módulo 1: clima

- **Cálculo.** Ra con la ecuación 21 de FAO-56 y ETo con Hargreaves-Samani (ecuación 52), con Ra convertida a mm/día (× 0.408). PAR = 0.48·Rs. El código reproduce los valores de referencia de Ra (p. ej. 32.2 MJ/m²/día el 3-sep a 20 °S) y un ejemplo de ETo (Tmax 20 °C, Tmin 7 °C, 21-jun, lat 19.7° → 4.18 mm/día). Los vacíos no se rellenan dentro del módulo: si los hay, la función falla.
- **Validación.** El cociente global ETo (Hargreaves) / ETo (Open-Meteo, Penman-Monteith) es 0.917 en las 197 parcelas, con variación mensual de 0.82 (nov) a 1.06 (jun). En los meses del ciclo (jun-oct) va de 0.88 a 1.06, por lo que un factor único corregiría de más en junio.
- **Decisión.** Hargreaves sin corrección (factor 1.0) como caso base y un factor de 1.09 (aprox. 1 / 0.917) como análisis de sensibilidad, declarado en `params.yaml` (`clima.factor_eto`). La corrección no se calibró con rendimiento.

#### Módulo 2: fenología

- **Grados-día.** max(0, Tmedia − Tbase), acumulados desde la fecha de siembra estimada (el día de siembra cuenta). Tbase 0 °C, con sensibilidad a 2 °C.
- **Modos.**
  - Principal: antesis y madurez al alcanzar 800 y 1,450 °C·d.
  - Sensibilidad: antesis en el pico de NDVI y madurez cuando el fPAR cae a la mitad del pico.
  - Si la meta no se alcanza antes del 30-nov, se usa el último día de la ventana y la parcela se marca. En el modo principal ninguna parcela queda sin madurez antes del 30-nov; en el modo satelital, 6 de 197 no la alcanzan.
- **Kc diario.** Sigue los tramos de FAO-56 (inicial, desarrollo, mitad, tardío; Kc 0.30, 1.15 y 0.25) y se define por fechas, con fracciones de tiempo propias de 30 % y 50 % (supuestos del equipo, en `params.yaml`).
- **Limitación.** Los umbrales térmicos dependen del cultivar, que se desconoce parcela por parcela (Josefa predominante, según FIRA). Los de 800 y 1,450 °C·d son compatibles en orden de magnitud con variedades mexicanas de Valles Altos (INIFAP; ver `docs/JUSTIFICACION_PARAMETROS.md`).

#### Módulo 3: balance hídrico

- **Modelo.** Depósito único de 0-60 cm entre punto de marchitez (PWP) y capacidad de campo (FC). El coeficiente de estrés es Ks = 1 si SW ≥ FC − p·AWC y decrece linealmente por debajo (Allen et al., 1998, cap. 8), con p = 0.55 (Tabla 22).
  - Para evitar la circularidad (Ks depende de SW, que depende de ETa), Ks del día t se calcula con el SW del día t−1.
  - ETa = ETo·Kc·Ks y nunca excede el agua disponible sobre PWP. El exceso sobre FC se pierde como drenaje.
- **Condiciones iniciales (supuesto propio).** El balance arranca el 15-mar con SW = PWP + 0.5·AWC. Antes de la siembra se usa Kc = Kc inicial (suelo desnudo).
- **Limitaciones.**
  - Sin escurrimiento (pendientes de 0.5 a 16 %), sin riego, sin ascenso capilar y sin diferenciar evaporación del suelo y transpiración.
  - La raíz de 60 cm está por debajo del intervalo de 1.0-1.5 m de FAO-56, así que el agua disponible está subestimada y el balance es sensible a periodos secos cortos.
  - Como el suelo varía poco entre parcelas, las diferencias de Ks vienen sobre todo del clima y de la fecha de siembra.

#### Módulo 4: biomasa e índice de cosecha

- **Biomasa.** dBIO = PAR × fPAR × RUE × Ks × 10 (kg/ha/día), acumulada de la siembra a la madurez, con fPAR = `fapar_final` acotado a 1.
- **RUE.** 2.5 g/MJ de PAR absorbida (la literatura de cebada reporta 2.6-2.9; Goyne et al., 1993). Es una constante de escala: no cambia el orden entre parcelas, pero la biomasa absoluta no debe leerse como biomasa medida.
- **Índice de cosecha.** HI = 0.45 × (1 − 0.5 × (1 − KS_antesis) − 0.3 × (1 − KS_llenado)), acotado entre 0 y 0.45.
  - Los valores 0.45, 0.5 y 0.3 son supuestos del equipo.
  - La alternativa con respaldo bibliográfico es Kemanian et al. (2007), que se corre como sensibilidad.

### 5. Variables derivadas

- **GDD_antesis y GDD_llenado.** Con la antesis del modo umbral serían casi constantes (~800 y ~650 °C·d). Por decisión del equipo se calculan con el pico de NDVI: GDD_antesis = grados-día de la siembra al pico, y GDD_llenado = grados-día del pico al día en que el fPAR cae a la mitad del valor del pico.
  - Una primera versión (del pico a la madurez por umbral) dio GDD_llenado = 0 en 61 de 197 parcelas, porque el pico cae después de los 1,450 °C·d, y se descartó.
  - Resultado con la definición adoptada: GDD_antesis de 589 a 2,161 (mediana 1,274) y GDD_llenado de 123 a 1,835 (mediana 802).
  - En 5 parcelas el fPAR no cae a la mitad del pico antes del 30-nov; GDD_llenado queda truncado al último día de la ventana y están marcadas en `biofisicas_extras_197_parcelas.csv` (`caida_fpar_no_alcanzada`).
  - GDD_llenado mide la duración de la senescencia según el satélite, no el llenado fisiológico estricto.
  - La definición de la guía y la anterior siguen disponibles en `params.yaml` (`fenologia.gdd_variables_ref`) para sensibilidad.
- **Dos definiciones de antesis.** DAP_antesis_est, KS_prom_antesis y Biomasa_Antesis_Sim usan la antesis del modo de fenología activo, por lo que no coinciden con el pico de NDVI usado en GDD_antesis. Con el modo principal, la antesis por umbral ocurre en promedio 35 días antes del pico (mediana de la diferencia).
- **Déficit hídrico.** Deficit_Hidrico_Total = ETo_acum − ETa_acum (definición del prompt) mide sobre todo el efecto de Kc. El estrés real es la suma de ETo × Kc menos la suma de ETa, que se entrega aparte como Deficit_ETc.

### 6. Resultados que conviene explicar

- **Estrés hídrico simulado bajo.** El 49 % de las parcelas no tiene ningún día con Ks < 1 durante el ciclo (mediana de 1 día con Ks < 1), y el año fue muy lluvioso. Con tan poca variación, KS_prom_antesis y KS_prom_llenado aportan poca información al modelo.
- **HI casi constante.** 149 de 197 parcelas tienen HI = 0.45 (sin penalización), por lo que esta variable aporta poca variación.
- **Biomasa alta.** La mediana es 11.4 t/ha, 78 de 197 parcelas pasan de 12 t/ha y el máximo es 17.1 t/ha, por encima del rango de 3-12 t/ha que se esperaba a priori. Viene de la RUE de 2.5 y, al ser una constante de escala, no afecta el orden entre parcelas. La correlación de Spearman entre fPAR_integrado y Biomasa_Total_Sim es 0.98.
- **ETo del ciclo.** ETo_acum va de 361 a 411 mm (mediana 382 mm), por debajo del rango de 400-800 mm que se esperaba a priori; es consistente con un ciclo corto (mediana de 104 días de la siembra a la madurez por umbral).
- **Días a la antesis.** DAP_antesis_est va de 48 a 66 días (mediana 56), por debajo del rango de 60-120 días que se esperaba a priori, pero dentro de la floración a 48-72 días que reporta INIFAP para variedades de Valles Altos.
