# Contrato de datos del simulador biofísico

Todo lo que se lee o se produce, con nombres y unidades acordados. **Avisar si se cambia un nombre.**

Reglas generales
- El identificador de parcela es `ID_POLIGON` en todos los archivos intermedios. Solo el entregable final lo renombra a `ID_parcela`.
- Ventana de simulación: **2025-03-15 a 2025-11-30** (261 días). Fechas en formato `YYYY-MM-DD`.
- Los parámetros (Tbase, Kc, p, RUE, HI, umbrales) se leen de `configs/params.yaml`, nunca se escriben dentro del código.
- **No se usa el rendimiento** en ningún cálculo del simulador. Evita fuga de datos.
- Los archivos de `data/` ya incluyen lo necesario; los scripts que los generan están en `src/ingest/`.

## 1. Entrada estática: `data/processed/parcelas_base.csv` (197 filas, una por parcela)

| Columna | Unidad | Descripción |
|---|---|---|
| `ID_POLIGON` | | AGC_001 ... AGC_197 |
| `CONJUNTO` | | ENTRENAMIENTO (138) o PREDICCION (59) |
| `Estado`, `Municipio` | | del shapefile |
| `area_ha` | ha | del shapefile |
| `lat`, `lon` | grados | centroide (EPSG:4326) |
| `elev_m` | m | elevación, INEGI CEM 4.0 (media en el polígono) |
| `pendiente_deg`, `pendiente_pct` | ° y % | pendiente, INEGI CEM 4.0 |
| `fecha_siembra` | fecha | **la que usan los módulos**: sale del escenario de `params.yaml` |
| `fecha_siembra_A`, `fecha_siembra_B` | fecha | escenarios de las 31 parcelas de doble ciclo (en el resto A = B) |
| `doble_ciclo` | bool | hubo un primer ciclo de vegetación que cayó en julio |
| `flag_siembra` | | `ok` o `doble_ciclo` |
| `fecha_sos`, `fecha_pico`, `ndvi_pico` | fecha, fecha, - | inicio de crecimiento y pico del NDVI de Planet |
| `arcilla_pct`, `arena_pct`, `limo_pct` | % | SoilGrids, promedio ponderado 0-60 cm |
| `om_pct` | % | materia orgánica (carbono orgánico x 1.724, tope 8 %) |
| `bdod_g_cm3` | g/cm3 | densidad aparente |
| `cfvo_pct` | % | fragmentos gruesos |
| `FC_vol`, `PWP_vol` | m3/m3 | capacidad de campo y punto de marchitez (Saxton y Rawls 2006) |
| `FC_mm`, `PWP_mm`, `AWC_mm` | mm en 0-60 cm | con corrección por grava; AWC = FC - PWP |
| `AWC_mm_sin_grava` | mm | para sensibilidad |

## 2. Clima diario: `data/external/clima_diario_parcelas_2025.csv` (una fila por parcela y día)

| Columna original | Nombre sugerido en los módulos | Unidad |
|---|---|---|
| `temperature_2m_max` | `tmax` | °C |
| `temperature_2m_min` | `tmin` | °C |
| `precipitation_sum` | `pcp` | mm/día |
| `shortwave_radiation_sum` | `rs` | MJ/m2/día |
| `et0_fao_evapotranspiration` | `eto_om` | mm/día (solo para comparar con tu ETo) |
| `elevacion_modelo_m` | | m |

Fuente: Open-Meteo (ERA5/ERA5-Land). **No usar los rasters CHIRTS como temperatura**: tienen un sesgo cálido de +2.9 °C frente a estaciones (ver `docs/FUENTES.md`).

## 3. Satélite diario: `data/processed/series_satelite_diarias_2025.csv`

| Columna | Descripción |
|---|---|
| `fapar_final` | **fPAR diario que usa el Módulo 4** (NDVI de Planet convertido a FAPAR, calibrado con Sentinel-2) |
| `fapar_s2` | FAPAR de Sentinel-2 suavizado (referencia; tiene un hueco en junio-julio) |
| `ndvi_planet` | NDVI de Planet suavizado |

## 4. Qué devuelve cada módulo

Cada módulo es una función pura: `def modulo_X(df_in: pd.DataFrame, params: dict) -> pd.DataFrame`, con un DataFrame diario (una fila por parcela y día) al que **agrega** columnas.

| Módulo | Agrega | Notas |
|---|---|---|
| M1 clima | `tmean, ra, par, eto` | `par = 0.48 * rs`; `ra` por la ecuación 21 de FAO-56; ojo con las unidades de Hargreaves (Ra en MJ/m2/día x 0.408) |
| M2 fenología | `gdd_acum, estadio, kc` | GDD desde `fecha_siembra` con `tbase_c` |
| M3 balance hídrico | `sw, ks, eta` | `ks` se calcula con `sw` del día anterior (evita la circularidad) |
| M4 LUE | `bio, hi` | usa `fapar_final` |

## 5. Entregable final: `biofisicas_197_parcelas.csv`

Una fila por parcela con `ID_parcela` y las 12 variables del prompt maestro. `Deficit_Hidrico_Total = ETo_acum - ETa_acum` (no confundir con el balance lluvia - ETo del notebook antiguo).

## 6. Decisiones abiertas (no bloquean el trabajo)

1. **Escenario de siembra** A o B para las 31 parcelas de doble ciclo (hoy A). Pendiente de decisión del equipo o respuesta de FIRA.
2. **Fenología:** los umbrales del prompt (antesis 800, madurez 1450 °C·d) no cuadran con lo que muestra el satélite (mediana de 1,224 °C·d entre la siembra estimada y el pico de NDVI). Falta decidir Tbase y cómo definir las etapas.
3. **ETo:** el rango térmico diario de Open-Meteo es ~3 °C más angosto que el de las estaciones; Hargreaves podría salir ~10 % bajo. Compararlo con `eto_om` y decidir si se corrige.
