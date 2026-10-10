# Justificación de parámetros, supuestos y texto para el informe

Revisión del 5 de octubre de 2026. **Todo lo marcado como "verificado" se contrastó contra la fuente durante esta revisión; lo marcado "pendiente" hay que confirmarlo antes de entregar** (no lo citen en el informe hasta hacerlo).

Leyenda: **V** verificado en la fuente · **P** plausible, con una reserva que se explica · **S** supuesto propio del equipo (no tiene fuente; se defiende con análisis de sensibilidad).

---

## 1. Resultado de la verificación

| Parámetro | Valor | Estado | Qué encontramos |
|---|---|---|---|
| `kc_ini`, `kc_mid`, `kc_end` | 0.30, 1.15, 0.25 | **V*** | Son los valores de cebada de FAO-56 (Tabla 12). *Confirmados en fuentes secundarias que reproducen la tabla; verifiquen la Tabla 12 en el documento original.* Un estudio en cebada de primavera en Chequia reportó un Kcb de mitad de temporada menor que el estándar FAO: puede haber sobrestimación local. |
| `p_agotamiento` | 0.55 | **V** | FAO-56, Tabla 22 (capítulo 8): cebada p = 0.55 para ETc ≈ 5 mm/día. FAO ajusta p con `p + 0.04 (5 - ETc)`; con ETc ≈ 4-5 mm/día el efecto es ≈ +0.02 y se ignora. |
| Profundidad de raíz | 0.6 m | **P (subestima)** | FAO-56 da 1.0-1.5 m de profundidad efectiva para cebada. Con 0.6 m el agua disponible (mediana 63 mm) está subestimada; extrapolando linealmente (sin verificar capas más profundas) a 1.0 m serían unos 105 mm. Es la limitación más importante del balance hídrico. |
| `tbase_c` | 0 °C | **V** | Base 0 °C es la que usan los estudios de fenología de cebada revisados (siembra a espigamiento y a hoja bandera). El prompt dice 0-2 °C: hacer sensibilidad con 2. Algunos trabajos usan una base mayor (~8 °C) solo para después del espigamiento. |
| `gdd_antesis_objetivo`, `gdd_madurez_objetivo` | 800, 1450 °C·d | **P** | **Corrección a lo que habíamos dicho.** INIFAP describe para la variedad Adabella (Valles Altos) floración a los 48-72 días y madurez fisiológica a los 90-132 días. Con ~14 °C de media (Open-Meteo) eso es ≈ 670-1,010 y 1,260-1,850 °C·d: **los umbrales son compatibles**. Cultivares de Argentina y cebada de invierno (Serbia) reportan tiempos más largos (≈ 1,040-1,290 °C·d a espigamiento; 1,223 °C·d a hoja bandera). Dependen del cultivar y no lo conocemos. |
| `par_fraccion` | 0.48 | **V** | La literatura reporta PAR/Rs entre ~0.42 y 0.55; muchos modelos usan 0.50. 0.48 está en el rango. |
| `rue_max_g_mj_par` | 1.2 | **P (mal definida)** | Los experimentos en cebada (Goyne y colaboradores, 1993) dan **2.6-2.9 g/MJ de PAR absorbida** sin limitaciones. 1.2 ≈ 0.48 × 2.5: parece una RUE por MJ de radiación **global**, no de PAR. Nuestra fórmula la aplica a PAR. Es una constante de escala: no cambia el orden entre parcelas, y con 1.2 la biomasa sale en ~6-8 t/ha, razonable para temporal. Documentar la base y hacer sensibilidad con 2.6. |
| `hi_base` | 0.42 | **P** | Razonable, algo menor que el HI medido en cebada de Idaho (0.46-0.52). Kemanian et al. (2007) proponen `HI = HI0 + s·fG` (fG = fracción de biomasa posterior a la antesis) y para cebada ambos parámetros rondan 0.3: con fG ≈ 0.4 da 0.42. |
| `hi_beta` | 0.5 | **S** | No tiene fuente. Preferir la opción de Kemanian (`hi_kemanian`). |
| Hargreaves-Samani | 0.0023, 17.8, raíz | **V** | FAO-56, ecuación 52. **Ra y ETo van ambos en mm/día** (1 MJ/m²/día = 0.408 mm/día). FAO recomienda verificarla y calibrarla localmente contra Penman-Monteith. |
| Radiación extraterrestre Ra | ecuación 21 | **V** | Reproducimos al decimal los ejemplos de FAO-56: 32.2 MJ/m²/día (3-sep, 20°S) y 40.6 (Lyon, 15-jul). |
| Saxton y Rawls (2006) | coeficientes | **V** | Los coeficientes de las ecuaciones de punto de marchitez, capacidad de campo, saturación y sus correcciones coinciden con el código del USDA. Validez: materia orgánica ≤ 8 %, arcilla ≤ 60 %. |
| Materia orgánica = 1.724 × C org. | 1.724 | **Pendiente** | Factor estándar (Van Bemmelen); no se verificó en esta revisión. Citar una fuente de métodos de suelos. |
| Umbral del inicio de crecimiento | 20 % de la amplitud | **V** | Umbral relativo estándar para el inicio de temporada con series de NDVI (TIMESAT, Jönsson y Eklundh, 2004); otros trabajos calibran 20-30 %. Detecta el reverdecimiento, **no la siembra**. |
| `gdd_siembra_a_sos` | 200 °C·d | **S (probablemente bajo)** | La emergencia sola toma ~156 °C·d (Alzueta y colaboradores, 2014); falta el tiempo para que el NDVI suba 20 % de su amplitud. Probar 150-350 °C·d. Un valor mayor adelanta la siembra estimada. |
| Nubosidad ≤ 20 %, descarte de picos, mínimo de observaciones | | **S** | Criterios propios. |
| Suavizado Savitzky-Golay (grado 2, ventanas de 15 y 21 días) | | **P** | Método estándar (Savitzky y Golay, 1964; verificar la cita). Las ventanas son elección propia. |
| Calibración NDVI Planet → FAPAR Sentinel-2 | R² 0.97, RMSE 0.036 | **V (propia)** | Regresión lineal robusta con ~8,700 pares parcela-fecha; no usa rendimiento. Sentinel-2 es a su vez un producto derivado. |
| Open-Meteo | | **V** | Licencia CC BY 4.0 con atribución obligatoria. Reanálisis ERA5-Land (0.1°, ~11 km); selecciona la celda por elevación con un modelo de 90 m. |
| Época de siembra de referencia | | **Pendiente** | Fuentes encontradas (INIFAP-CEZAC y prensa) dan ventanas desde la segunda quincena de mayo hasta finales de julio: **no separan el escenario A (14-29 may) del B (9-jul a 8-ago)**. Buscar una fuente INIFAP de Valles Altos. |

### Correcciones a cosas que dijimos antes (léanlas)

1. **Fenología.** Dijimos que los umbrales de 800/1450 °C·d "no cuadraban con el satélite". Esa conclusión suponía que el pico de NDVI coincide con la antesis y es probable que no sea así. Los umbrales son compatibles con variedades mexicanas. El modo principal pasó a `umbral_gdd`.
2. **RUE.** El valor 1.2 del prompt no es una RUE de PAR; ver la tabla.
3. **Época de siembra.** Dijimos que el escenario B quedaba "muy tarde"; las fuentes encontradas permiten siembras hasta finales de julio. Los escenarios siguen sin decidirse.
4. **Profundidad de raíz.** No era solo una simplificación menor: queda por debajo del rango que da FAO.

---

## 2. Texto para el informe

Los apartados del reporte tienen límite de palabras (Metodología 700 en total, incluida la parte de ML). Los bloques están contados; ajusten lo que esté entre `[corchetes]` a lo que decida el equipo.

> **OJO con el límite de palabras.** Los bloques A y B juntos suman unas 505 palabras, y toda la Metodología admite 700 (incluida la parte de ML del otro equipo). Si no cabe, usen esta **versión corta de A + B (≈ 191 palabras)** y dejen el detalle en la tabla del Anexo (máximo 4 páginas en total):
>
> Se integraron clima diario de Open-Meteo (ERA5-Land), suelo de SoilGrids 2.0 (Poggio et al., 2021) y normales del SMN, además de los datos del reto. La precipitación se validó contra CHIRPS (1,015 frente a 961 mm) y la temperatura contra tres estaciones del SMN (sesgo medio de 0.0 °C en Open-Meteo y de +2.9 °C en CHIRTS-ERA5, que se descartó). Las series satelitales se filtraron, interpolaron y suavizaron; el fPAR diario se obtuvo del NDVI de Planet calibrado contra el FAPAR de Sentinel-2 (R² = 0.97). La siembra, no observada, se estimó por parcela con un umbral del 20 % de la amplitud del NDVI (Jönsson y Eklundh, 2004).
>
> El simulador diario tiene cuatro módulos: clima (radiación extraterrestre, PAR y ETo de Hargreaves-Samani; Allen et al., 1998), fenología por tiempo térmico con coeficientes de cultivo de FAO-56, balance hídrico de un depósito con propiedades de Saxton y Rawls (2006) y coeficiente de estrés Ks, y biomasa por eficiencia de uso de la radiación con índice de cosecha penalizado por estrés. Produce 12 variables por parcela. Los parámetros y sus fuentes están en los Anexos. Ningún parámetro se ajustó con el rendimiento.

### Bloque A: Metodología, datos y preparación (≈ 290 palabras)

Además de los datos del Comité Organizador (polígonos, índices de Sentinel-2, Landsat y Planet, y elevación y pendiente del CEM 4.0 del INEGI), se integraron tres fuentes externas: clima diario de Open-Meteo (reanálisis ERA5-Land, 0.1°, licencia CC BY 4.0), suelo de SoilGrids 2.0 (Poggio et al., 2021) obtenido por el servicio WCS de ISRIC, y normales climatológicas del SMN para validar la temperatura. El clima se descargó por parcela para el 15 de marzo al 30 de noviembre de 2025. La precipitación se validó contra CHIRPS (abril-octubre: 1,015 mm frente a 961 mm) y la temperatura contra tres estaciones del SMN: el sesgo medio de la temperatura media fue de 0.0 °C en Open-Meteo y de +2.9 °C en CHIRTS-ERA5, por lo que este último no se usó en el simulador.

Las series satelitales se filtraron por nubosidad (≤ 20 %), se eliminaron picos aislados, se interpolaron a escala diaria y se suavizaron con Savitzky-Golay (Savitzky y Golay, 1964). Como Sentinel-2 carece de observaciones válidas en junio y julio por nubosidad, el fPAR diario se obtuvo del NDVI de Planet mediante una regresión lineal contra el FAPAR de Sentinel-2 en fechas coincidentes (R² = 0.97; RMSE = 0.036), sin usar el rendimiento. Al no existir fechas de siembra, se estimaron por parcela con un umbral relativo del 20 % de la amplitud del NDVI (Jönsson y Eklundh, 2004), retrocediendo 200 °C·d desde el inicio del crecimiento; la mediana resultante fue el 1 de junio. En 31 parcelas (16 %) el NDVI muestra un primer ciclo de vegetación que cae en julio, por lo que se consideraron dos escenarios de siembra. Los parámetros y sus fuentes se presentan en los Anexos.

### Bloque B: Metodología, simulador biofísico (≈ 250 palabras) `[ajustar según las decisiones del equipo]`

El simulador biofísico opera a escala diaria por parcela en cuatro módulos. (1) Clima: radiación extraterrestre con la ecuación 21 de FAO-56, radiación fotosintéticamente activa PAR = 0.48·Rs y evapotranspiración de referencia con Hargreaves-Samani, contrastada con la de Penman-Monteith de Open-Meteo (Allen et al., 1998). (2) Fenología por tiempo térmico (temperatura base de 0 °C) `[con antesis a 800 °C·d y madurez a 1,450 °C·d]` y coeficiente de cultivo por tramos de FAO-56 (Kc = 0.30, 1.15 y 0.25). (3) Balance hídrico de un depósito entre capacidad de campo y punto de marchitez, estimados con las ecuaciones de Saxton y Rawls (2006) a partir de las propiedades de SoilGrids en 0-60 cm; el coeficiente de estrés es Ks = 1 si SW ≥ FC − p·AWC y decrece linealmente por debajo, con p = 0.55 (Allen et al., 1998), y ETa = ETo·Kc·Ks. (4) Biomasa con el modelo de eficiencia de uso de la radiación de Monteith, dBIO = PAR·fPAR·RUE·Ks, e índice de cosecha `[estimado a partir de la fracción de biomasa posterior a la antesis (Kemanian et al., 2007)]`. De este proceso resultan 12 variables por parcela (tiempo térmico, ETo y ETa acumuladas, déficit hídrico, estrés promedio en antesis y llenado, fPAR integrado, biomasa e índice de cosecha) que se integran al conjunto de datos del reto. Ningún parámetro se ajustó con el rendimiento.

### Bloque C: Resultados y discusión, supuestos y limitaciones (≈ 310 palabras)

El simulador usa celdas de reanálisis de ~11 km y suelo de 250 m, mientras que la mediana de las parcelas es de 5.5 ha; por ello el clima y el suelo discriminan poco entre parcelas (el rango intercuartil del agua disponible es de ~3 mm) y la variación espacial proviene sobre todo del satélite, la altitud y la fecha de siembra. La temperatura de Open-Meteo reproduce la media de tres estaciones del SMN (sesgo de 0.0 °C), pero con un rango diario ~3 °C más angosto (Tmax −1.5 °C; Tmin +1.6 °C), lo que podría subestimar la ETo de Hargreaves en torno a 10 % (estimación aproximada); además, las normales son de 30 años y no de 2025, y las estaciones están todas en Tlaxcala. La fecha de siembra no se observó: se estimó con el satélite y un desfase térmico supuesto (200 °C·d), con una incertidumbre de una a dos semanas según el umbral; como la emergencia por sí sola requiere ~156 °C·d (Alzueta et al., 2014), las fechas podrían estar sesgadas hacia tarde. En 31 parcelas el NDVI revela un primer ciclo que cae en julio (corte, pastoreo o daño; no se pudo determinar) y se evaluaron dos escenarios de siembra, separados por una mediana de 62 días. La profundidad de raíz se fijó en 0-60 cm, menor que el intervalo de 1.0-1.5 m que indica FAO-56, por lo que el agua disponible (mediana de 63 mm) está subestimada y el balance es sensible a periodos secos de una semana. Los umbrales térmicos dependen del cultivar, que se desconoce. La eficiencia de uso de la radiación (1.2 g/MJ de PAR) es una constante de escala que modifica la magnitud de la biomasa pero no el orden entre parcelas. Ningún parámetro se calibró con el rendimiento, para evitar fuga de datos.

### Bloque D: Anexo, tabla de parámetros (para pegar en el PDF de Anexos)

| Parámetro | Valor | Fuente |
|---|---|---|
| Coeficientes de cultivo (Kc ini, mid, end) | 0.30; 1.15; 0.25 | Allen et al. (1998), Tabla 12 |
| Fracción de agotamiento p | 0.55 | Allen et al. (1998), Tabla 22 |
| Fracción PAR de la radiación global | 0.48 | Rango publicado 0.42-0.55 |
| Temperatura base | 0 °C | Alzueta et al. (2014); Przulj y Momčilović (2006) |
| Tiempo térmico a antesis / madurez | `800 / 1,450 °C·d` | Supuesto compatible con INIFAP (Adabella, 48-72 y 90-132 días) |
| Eficiencia de uso de la radiación | 1.2 g/MJ de PAR | Supuesto; literatura: 2.6-2.9 g/MJ de PAR absorbida (Goyne et al., 1993) |
| Índice de cosecha | `0.3 + 0.3·fG` | Kemanian et al. (2007) |
| ETo | Hargreaves-Samani (ec. 52) | Allen et al. (1998) |
| Capacidad de campo y marchitez | Saxton y Rawls | Saxton y Rawls (2006) |
| Materia orgánica | 1.724 × C orgánico, tope 8 % | Factor de Van Bemmelen |
| Profundidad de raíz | 0.6 m | Supuesto (FAO-56: 1.0-1.5 m) |
| Agua inicial del suelo | PWP + 0.5·AWC | Supuesto; sensibilidad 0.3-0.8 |
| Umbral de inicio de crecimiento | 20 % de la amplitud del NDVI | Jönsson y Eklundh (2004) |
| Desfase siembra a inicio de crecimiento | 200 °C·d | Supuesto; sensibilidad 150-350 |
| Nubosidad máxima | 20 % | Supuesto |
| Suavizado | Savitzky-Golay, grado 2, 15 y 21 días | Savitzky y Golay (1964) |

---

## 3. Referencias

Separadas por estado de verificación. **Solo las del primer grupo están listas para el informe.**

### Verificadas

- Allen, R. G., Pereira, L. S., Raes, D., & Smith, M. (1998). *Crop evapotranspiration: Guidelines for computing crop water requirements* (FAO Irrigation and Drainage Paper 56). FAO, Roma. (Capítulos 3 y 8 consultados; la Tabla 12 solo en fuentes secundarias.)
- Saxton, K. E., & Rawls, W. J. (2006). Soil water characteristic estimates by texture and organic matter for hydrologic solutions. *Soil Science Society of America Journal, 70*, 1569-1578. (Coeficientes contrastados con el código del USDA.)
- Jönsson, P., & Eklundh, L. (2004). TIMESAT: a program for analyzing time-series of satellite sensor data. *Computers & Geosciences, 30*(8), 833-845. https://doi.org/10.1016/j.cageo.2004.05.006
- Bonhomme, R. (2000). Beware of comparing RUE values calculated from PAR vs solar radiation or absorbed vs intercepted radiation. *Field Crops Research, 68*(3), 247-252.
- Funk, C., Peterson, P., Landsfeld, M., et al. (2015). The climate hazards infrared precipitation with stations: a new environmental record for monitoring extremes. *Scientific Data, 2*, 150066. https://doi.org/10.1038/sdata.2015.66
- Climate Hazards Center (2025). *CHIRTS-ERA5 Data Repository*. Universidad de California, Santa Bárbara. https://doi.org/10.15780/G2F08J
- INEGI (2025). *Continuo de Elevaciones Mexicano 4.0 (CEM 4.0)*, resolución de 15 m.
- Hersbach, H., et al. (2023). *ERA5 hourly data on single levels from 1940 to present*. Copernicus Climate Change Service (C3S) Climate Data Store. https://doi.org/10.24381/cds.adbb2d47
- Open-Meteo (s.f.). *Historical Weather API*. https://open-meteo.com (datos bajo licencia CC BY 4.0, con atribución).
- Servicio Meteorológico Nacional, CONAGUA. *Normales climatológicas*, estaciones Zoquiapan (29034), Tocatlán (29027) y Hueyotlipan (29010). https://smn.conagua.gob.mx

### Pendientes: confirmar autores, título o datos antes de citarlas

- Poggio, L., et al. (2021). SoilGrids 2.0: producing soil information for the globe with quantified spatial uncertainty. *SOIL, 7*, 217-240. https://doi.org/10.5194/soil-7-217-2021 *(confirmar lista de autores)*
- Kemanian, A. R., Stöckle, C. O., Huggins, D. R., & Viega, L. M. (2007). A simple method to estimate harvest index in grain crops. *Field Crops Research, 103*(3), 208-216. *(confirmar DOI y páginas; leer el artículo para confirmar los valores de 0.3)*
- Goyne, P. J., et al. (1993). Radiation interception, radiation use efficiency and growth of barley cultivars. *Australian Journal of Agricultural Research, 44*(6), 1351-1366. https://doi.org/10.1071/AR9931351 *(confirmar autores)*
- Alzueta, I., et al. (2014). Artículo sobre fenología de cebada maltera (archivo `2014alzueta.pdf` del repositorio de la Facultad de Agronomía de la UBA). *(completar autores, título y revista)*
- Przulj, N., & Momčilović, V. (2006). Fenología y rendimiento de la cebada de invierno en condiciones semiáridas. *EMS Annual Meeting Abstracts*, EMS2006-A-00095. *(confirmar título; preferir el artículo en revista)*
- Savitzky, A., & Golay, M. J. E. (1964). Smoothing and differentiation of data by simplified least squares procedures. *Analytical Chemistry, 36*(8), 1627-1639. *(de memoria)*
- Hersbach, H., et al. (2020). The ERA5 global reanalysis. *Quarterly Journal of the Royal Meteorological Society, 146*, 1999-2049. *(de memoria)*
- Muñoz-Sabater, J., et al. (2021). ERA5-Land: a state-of-the-art global reanalysis dataset for land applications. *Earth System Science Data, 13*, 4349-4383. *(de memoria)*
- Zippenfenig, P. (2023). Open-Meteo.com Weather API. Zenodo. https://doi.org/10.5281/zenodo.7970649 *(de memoria; confirmar DOI)*
- Modeling photosynthetically active radiation: a review. *Atmósfera*. https://doi.org/10.20937/ATM.52737 *(completar autores y año)*
- INIFAP. Adabella: variedad de cebada maltera para Valles Altos de la Mesa Central de México. *Agricultura Técnica en México, 34*(4), 2008. *(completar autores y páginas)*
- INIFAP-CEZAC. *Potencial productivo de especies agrícolas en el estado de Zacatecas: cebada maltera de temporal*. https://zacatecas.inifap.gob.mx/PotAgric/CebadaT.pdf *(es de Zacatecas, no de Valles Altos)*
- Una fuente para el factor 1.724 de materia orgánica (método de análisis de suelos).
- Una fuente INIFAP de **época de siembra de cebada de temporal en Valles Altos** (hoy solo hay prensa y un documento de Zacatecas).

## Cambios del 10-oct-2026

| Parámetro | Valor anterior | Valor actual | Estado | Razón |
|---|---|---|---|---|
| `cultivo.rue_max_g_mj_par` | 1.2 | 2.5 | P | Se aplica a la PAR absorbida. La literatura de cebada reporta 2.6-2.9 g/MJ (Goyne et al., 1993). El 1.2 anterior parecía una RUE sobre radiación global. Es una constante de escala: no cambia el orden entre parcelas. |
| `cultivo.hi_base` | 0.42 | 0.45 | S | Valor usado en el módulo 4 del equipo. Sin fuente específica; pendiente de justificar. |
| `lue.hi_opcion` | (no existía) | "C" | S | Fórmula del equipo que penaliza el estrés de antesis y de llenado. La opción B (Kemanian et al., 2007) queda como sensibilidad. |
| `lue.hi_sens_antesis`, `lue.hi_sens_llenado` | (no existían) | 0.5 y 0.3 | S | Sin fuente. |
| `clima.factor_eto` | (no existía) | 1.0 | S | Hargreaves sin corrección. La sensibilidad con 1.09 viene del cociente global 0.917 frente a la ETo de Open-Meteo. |
| `fenologia.gdd_variables_ref` | (no existía) | "pico_ndvi" | S | Evita que GDD_antesis y GDD_llenado queden casi constantes en el modo umbral. |
