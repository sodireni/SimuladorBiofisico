# Contrato de datos del simulador biofísico

Todo lo que se lee o se produce, con nombres y unidades acordados. **Si cambian un nombre, avisen al equipo y actualicen este archivo.**

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
| M2 fenología | `gdd_acum, estadio, kc, fecha_antesis, fecha_madurez` | `estadio` es uno de `pre_siembra, vegetativo, antesis, llenado, madurez`; la ventana de antesis tiene prioridad; las dos fechas son constantes por parcela |
| M3 balance hídrico | `sw, ks, eta` | `ks` se calcula con `sw` del día anterior (evita la circularidad) |
| M4 LUE | `dbio, bio` | `dbio` en kg/ha/día y `bio` acumulada desde la siembra hasta la madurez; usa `fapar_final`. `hi_penalizado()` es una función aparte |

Código: paquete `src/simulador/` (carga en `io.py`, módulos `m1_clima.py` ... `m4_lue.py`, cálculo de las 12 variables en `variables.py`, encadenado en `pipeline.py`). Guía de cada módulo: `docs/GUIA_DE_MODULOS.md`.

## 5. Entregable final: `biofisicas_197_parcelas.csv`

Una fila por parcela con `ID_parcela` y las 12 variables del prompt maestro. `Deficit_Hidrico_Total = ETo_acum - ETa_acum` (no confundir con el balance lluvia - ETo del notebook antiguo).
Aparte se guarda `biofisicas_extras_197_parcelas.csv` con `ID_parcela`, `Deficit_ETc` (suma de ETo x Kc menos suma de ETa) y `ciclo_incompleto` (la madurez no se alcanzó antes del 30-nov), para que el equipo de ML decida si los usa.

## 6. Decisiones abiertas (no bloquean el trabajo)

Tomadas el 10-oct-2026:
1. **ETo:** Hargreaves sin corrección (`clima.factor_eto: 1.0`) como caso base y factor 1.09 como sensibilidad.
2. **Fenología:** `umbral_gdd` como modo principal y `satelite` como sensibilidad. Tbase 0 °C, con sensibilidad a 2 °C.
3. **GDD_antesis y GDD_llenado:** se calculan con el pico de NDVI (`fenologia.gdd_variables_ref: "pico_ndvi"`) para que varíen entre parcelas: `GDD_antesis` va de la siembra al pico y `GDD_llenado` del pico al día en que el fPAR cae a la mitad del pico. La versión que llegaba hasta la madurez por umbral se descartó porque dio 0 en 61 de 197 parcelas.
4. **Escenario de siembra:** se mantiene A para las 31 parcelas de doble ciclo. FIRA respondió el 9-oct que no hay fechas reales de siembra (referencia: primeros días de mayo) y no respondió sobre el doble propósito.

Abiertas:
1. **Índice de cosecha:** opción C (la del M4 del equipo, sin fuente) contra opción B (Kemanian et al., 2007, recomendada).
2. **Siembra:** la estimación con NDVI es posterior a la referencia de FIRA; se evalúa con una sensibilidad (siembra fija al 5-may).
