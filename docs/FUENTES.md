# Fuentes de datos y referencias

## Datos del Comité Organizador (Reto AgroCebada FIRA 2026)
| Dato | Fuente | Uso en el simulador |
|---|---|---|
| Parcelas (shapefile) | Comité Organizador | Centroides (lat/lon) |
| Elevación y pendiente | INEGI, Continuo de Elevaciones Mexicano 4.0 | Variables topográficas |
| Precipitación mensual | CHIRPS (Funk et al., 2015) | Control de calidad de la lluvia diaria |
| Tmin y Tmax mensuales | CHIRTS-ERA5 (Climate Hazards Center, 2025) | Control de calidad de temperatura |
| Índices satelitales | Sentinel-2, Landsat y Planet (dataset Básico y PRO) | fPAR y series de vegetación |

## Datos externos
| Dato | Fuente | Periodo | Archivo generado |
|---|---|---|---|
| Clima diario (Tmax, Tmin, precipitación, radiación solar, ET0) | Open-Meteo Historical Weather API (reanálisis ERA5 / ERA5-Land) | 15-mar-2025 a 31-oct-2025 | `data/external/clima_diario_*_2025.csv` |

Script: `src/ingest/descargar_clima_diario_2025.py`

## Referencias
- Zippenfenig, P. (2023). Open-Meteo.com Weather API. Zenodo. https://doi.org/10.5281/zenodo.7970649 (licencia CC BY 4.0)
- Hersbach, H. et al. (2020). The ERA5 global reanalysis. Quarterly Journal of the Royal Meteorological Society, 146, 1999-2049.
- Muñoz-Sabater, J. et al. (2021). ERA5-Land: a state-of-the-art global reanalysis dataset for land applications. Earth System Science Data, 13, 4349-4383.
- Funk, C. et al. (2015). The climate hazards infrared precipitation with stations. Scientific Data, 2, 150066.
- Allen, R. G. et al. (1998). Crop evapotranspiration (FAO Irrigation and Drainage Paper 56). FAO.
- Hargreaves, G. H. y Samani, Z. A. (1985). Reference crop evapotranspiration from temperature. Applied Engineering in Agriculture, 1(2), 96-99.

## Supuestos y limitaciones (ir completando)
- El clima viene de un reanálisis de ~0.1°, por lo que varias parcelas comparten la misma serie.
- No se conoce la fecha de siembra; se define una regla (pendiente).
- Control de calidad de la lluvia: la suma diaria de Open-Meteo (abril-octubre 2025) se comparó con el CHIRPS mensual del reto en el centroide de cada parcela. Total medio: 1,015 mm (Open-Meteo) vs 961 mm (CHIRPS), +6 %. Razón mensual entre 0.84 y 1.24, sin sesgo sistemático. La variación espacial entre parcelas es pequeña en ambas fuentes por su resolución (5-10 km).
- Topografía: elevación y pendiente del CEM 4.0 de INEGI (120 m), media dentro del polígono de cada parcela (`src/ingest/extraer_topografia.py`). La pendiente se entrega en grados y se convierte a % con tan(grados)×100. Elevación media 2,667 m (2,497-2,905), pendiente media 2.9°.
- Satélite: FAPAR de Sentinel-2 (Dataset Básico) y NDVI de Planet (Dataset PRO), usados por separado, sin mezclar sensores. Filtros: nubosidad ≤ 20 %, valores vacíos descartados, picos aislados removidos (mediana móvil de 5 observaciones, umbral 0.25). Interpolación lineal diaria y suavizado Savitzky-Golay (grado 2; ventanas de 21 días para Sentinel-2 y 15 para Planet). Script: `src/ingest/limpiar_satelite.py`.
- Hallazgo: la vegetación de la cebada empieza a crecer entre junio y agosto según la parcela (cultivo de temporal), por lo que la fecha de siembra se estima por parcela y no se fija en abril. Sentinel-2 tiene un hueco de unos 25 días en junio por nubosidad.
- Hueco en Sentinel-2: del 16 al 29 de junio y del 7 al 13 de julio de 2025 no hay observaciones válidas de ninguna parcela (nubosidad). Por eso el fPAR diario se obtiene del NDVI de Planet, convertido a FAPAR con un ajuste lineal contra Sentinel-2 en las fechas coincidentes (`src/ingest/calibrar_fpar.py`).
- fPAR diario: se obtiene del NDVI de Planet convertido a FAPAR con un ajuste lineal contra el FAPAR de Sentinel-2 en las fechas coincidentes (7,207 pares parcela-fecha): FAPAR = 1.04·NDVI − 0.14, R² = 0.974, RMSE = 0.035; se descartó el 3.6 % de los pares con un criterio robusto (residuo > 3 MAD). No se usó el rendimiento. Script: `src/ingest/calibrar_fpar.py`. La serie resultante (`fapar_final`) se acota a [0, 0.95]. Limitación: el ajuste es lineal, y Sentinel-2 es a su vez un producto derivado, no una medición directa de campo.
- Ventana de análisis: 15-mar a 30-nov de 2025 (clima y satélite). Se amplió desde el 31-oct porque varias parcelas seguían verdes a finales de octubre (senescencia y cosecha en noviembre). El control de calidad de lluvia contra CHIRPS solo cubre abril-octubre.