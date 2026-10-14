# Guía de trabajo: módulos del simulador biofísico

## 1. Reglas generales

1. **Nunca usar el rendimiento** (`ID_area_rendimiento_...csv`) para nada del simulador: ni para ajustar parámetros, ni para elegir entre opciones. Sería fuga de datos. Las decisiones se justifican con física, literatura y los datos satelitales.
2. **Los parámetros viven en `configs/params.yaml`**, no dentro del código. 
3. **Funciones puras:** `def modulo(df_in, params) -> DataFrame`. No modifican `df_in` (usen `.copy()`), no leen archivos, no imprimen ni guardan. Solo `io.py` lee archivos.
4. **No cambiar nombres de columnas** sin avisar y sin actualizar el contrato. El ID es `ID_POLIGON`; solo el entregable final usa `ID_parcela`.
5. **Temperatura = Open-Meteo.** No usar los rasters CHIRTS: tienen un sesgo cálido de +2.9 °C frente a estaciones.
6. **fPAR = `fapar_final`.** No mezclar `fapar_s2` y `ndvi_planet` como si fueran equivalentes.
7. **Unidades:** temperatura en °C, lluvia y ET en mm/día, radiación en MJ/m²/día, biomasa en kg/ha, agua del suelo en mm.
8. **Ventana de simulación:** 2025-03-15 a 2025-11-30. Antes de la siembra no hay cultivo (GDD = 0, biomasa = 0). Después de la madurez, el cultivo ya no acumula.
9. **Cada parcela es independiente:** haga el cálculo con `groupby("ID_POLIGON")` o un ciclo por parcela. Nunca mezclar filas de parcelas distintas (cuidado con `cumsum`, `shift` y `diff`: siempre dentro del grupo).
10. **Registrar el uso de IA** en `docs/PROMPTS.md` (fecha, herramienta, para qué).
11. **Cada fuente o fórmula nueva se cita** en `docs/FUENTES.md`.

---

## 2. Flujo de trabajo de un módulo

1. Implementar la función en `src/simulador/mX_....py` respetando la firma.
2. Quitar el decorador `@pendiente` de su prueba en `tests/test_modulos.py`, confirmar que pasa y **agregar pruebas con respuesta conocida**.
3. Correr el módulo sobre los datos reales (con `cargar_entrada()`) y revisar: sin vacíos (NaN), rangos razonables, y **graficar 3 parcelas** (una por estado) para ver que la curva tenga sentido. Guardar la figura en `docs/`.
4. Hacer al menos **una prueba de sensibilidad** de su parámetro más incierto (ver cada módulo) y anotar el resultado en `docs/SENSIBILIDAD.md`.
5. Actualizar `docs/FUENTES.md` y `docs/PROMPTS.md`.
6. Commit, push, Pull Request, revisión de otra persona, merge.

**Un módulo está terminado cuando:** las pruebas pasan, corre sobre las 197 parcelas sin NaN, agrega exactamente las columnas del contrato, tiene su sensibilidad documentada y su PR fue aprobado por otra persona.

---

## 3. Módulo 1: clima (A)

Agrega `tmean, ra, par, eto`.

- `tmean = (tmax + tmin) / 2`.
- `par = params["cultivo"]["par_fraccion"] * rs` (0.48 × radiación global).
- **`ra` (radiación extraterrestre, FAO-56 ecuación 21)**, con la latitud en radianes y `J` el día del año:
  - `dr = 1 + 0.033 * cos(2π J / 365)`
  - `δ = 0.409 * sin(2π J / 365 - 1.39)`
  - `ωs = arccos(-tan φ * tan δ)`
  - `Ra = (24·60/π) * 0.0820 * dr * (ωs sin φ sin δ + cos φ cos δ sin ωs)`  [MJ/m²/día]
- **`eto` (Hargreaves-Samani):** `ETo = 0.0023 * (tmean + 17.8) * sqrt(tmax - tmin) * Ra_mm`, donde **`Ra_mm = Ra * 0.408`** (conversión de MJ/m²/día a mm/día).
  - Obs: `tmax >= tmin` y `ETo >= 0`.

**Valores para comprobar Ra** (latitud 19.7°): 21-mar 35.5, 21-jun 39.5, 21-dic 25.8, 15-mar 34.7 y 30-nov 26.4 MJ/m²/día. Ejemplo completo: Tmax 20, Tmin 7, 21-jun → ETo = 4.18 mm/día.

**Sensibilidad de M1:** ETo con y sin el factor de corrección.

---

## 4. Módulo 2: fenología (A)

Agrega `gdd_acum, estadio, kc, fecha_antesis, fecha_madurez`.

**Grados-día:** `gdd_t = max(0, tmean_t - Tbase)` con `Tbase = params["fenologia"]["tbase_c"]`. `gdd_acum` es la suma desde `fecha_siembra` (0 antes de sembrar). Dentro de cada parcela.

**Estadios** (`estadio`, un solo valor por día):
`pre_siembra` → `vegetativo` → `antesis` (ventana de ±`ventana_antesis_dias` días alrededor de `fecha_antesis`, con prioridad sobre los demás) → `llenado` (después de la ventana, hasta `fecha_madurez`) → `madurez`.

### La decisión más importante del proyecto: cómo se fijan `fecha_antesis` y `fecha_madurez`

El prompt maestro propone antesis a **800 °C·d** y madurez a **1450 °C·d** (Tbase 0). **Revisión del 5-oct con fuentes** (detalle en `docs/JUSTIFICACION_PARAMETROS.md`):

- Para variedades mexicanas de Valles Altos, INIFAP describe, por ejemplo para Adabella, floración a los 48-72 días y madurez fisiológica a los 90-132 días después de la siembra. Con una temperatura media de ~14 °C en el ciclo, eso equivale a ~670-1,010 °C·d a floración y ~1,260-1,850 °C·d a madurez (conversión nuestra, aproximada). **Los umbrales del prompt son compatibles en orden de magnitud.**
- Para cultivares de Argentina o cebada de invierno de Serbia, la literatura reporta tiempos más largos (~1,040-1,290 °C·d de siembra a espigamiento; ~1,223 °C·d a hoja bandera). Los umbrales dependen del cultivar y **no conocemos el de estas parcelas**.
- Antes decíamos que no cuadraban con el satélite (mediana de 1,224 °C·d entre la siembra estimada y el pico de NDVI). Esa comparación suponía que el pico de NDVI coincide con la antesis, y es probable que el pico ocurra **semanas después** (el verdor sigue alto en el llenado temprano). La discrepancia no demuestra que los umbrales estén mal.

Por eso `fenologia.modo` queda en **`"umbral_gdd"` como opción principal** y **`"satelite"` como análisis de sensibilidad**. Implementar los dos:

- **`"umbral_gdd"`:** antesis = primer día con `gdd_acum >= 800`; madurez = primer día con `gdd_acum >= 1450` (ambos en params).
- **`"satelite"`:** antesis = `fecha_pico`; madurez = primer día después del pico en que `fapar_final` cae a `madurez_fapar_frac_pico` (0.5) del pico. Ojo: aquí la antesis probablemente queda tarde.

**Advertencia:** en modo umbral, `GDD_antesis` y `GDD_llenado` quedan casi constantes (~800 y ~650), por lo que no aportan información al modelo de ML (las otras 10 variables sí varían). 

**Kc diario (FAO-56)**, basado en fechas (sirve para ambos modos): inicial = `kc_ini` de la siembra hasta `kc_frac_inicial` (30 %) del tiempo siembra → antesis; **desarrollo** = interpolación lineal de `kc_ini` a `kc_mid` hasta la antesis; **mid** = `kc_mid` durante `kc_frac_mid` (50 %) del tiempo antesis → madurez; **tardío** = descenso lineal a `kc_end` hasta la madurez. Antes de sembrar, `kc = kc_ini` (suelo desnudo); después de la madurez, `kc_end`. 

**Pruebas con respuesta conocida:** con `tmean` constante de 10 °C y Tbase 0, `gdd_acum` crece 10 por día; antes de la siembra vale 0; `gdd_acum` nunca decrece.

**Sensibilidad de M2:** `Tbase` = 0 contra 2 °C, y modo satélite contra modo umbral.

**Doble ciclo:** las 31 parcelas con `doble_ciclo = True` usan `fecha_siembra` (hoy escenario A, 25-may en promedio). Para esas parcelas el pico de NDVI que usa el modo satélite es el del ciclo principal. Anoten cómo se comportan.

---

## 5. Módulo 3: balance hídrico (B)

Agrega `sw, ks, eta`. Entradas: `pcp`, `eto`, `kc`, `FC_mm`, `PWP_mm`, `AWC_mm` (0-60 cm, ya con corrección por grava).

- El prompt escribe `SW_t = max(PWP, min(FC, SW_{t-1} + P - ETa))` y calcula KS con `SW_t`, que depende de ETa, que depende de KS: es circular. La solución es usar el SW del día anterior.
- Se corre desde el **15-mar** (calentamiento): antes de la siembra el suelo se humedece o se seca con las lluvias, y llega a la siembra en un estado realista. Antes de sembrar `kc = kc_ini`.

**Pruebas con respuesta conocida:** (1) con lluvia 0 y `eto*kc` constante, `sw` baja hasta `PWP` y `ks` llega a 0; (2) con lluvia muy alta, `sw = FC` y `ks = 1`; (3) **cierre del balance:** `Σpcp - Σeta - Σdrenaje = sw_final - sw_inicial`, con tolerancia 1e-6; (4) `PWP <= sw <= FC` siempre y `0 <= ks <= 1`.

Obs con `AWC` de ~63 mm y `p = 0.55`, solo ~34 mm son fácilmente aprovechables, es decir unos 7 a 8 días sin lluvia en pleno desarrollo. El balance es sensible a periodos secos cortos y al agua inicial. La variación del suelo entre parcelas es muy pequeña (rango de ~3 mm entre cuartiles), así que el KS diferirá entre parcelas sobre todo por el clima y la fecha de siembra.

**Sensibilidad de M3:** `sw_inicial_frac_awc` = 0.3, 0.5 y 0.8; y `AWC_mm` contra `AWC_mm_sin_grava`. Reportar cuánto cambian `ETa_acum` y `KS_prom_llenado`.

---

## 6. Módulo 4: biomasa por LUE (C)

Agrega `dbio` y `bio`. Entradas: `par`, `fapar_final`, `ks`, `estadio`, `fecha_madurez`, `fecha_siembra`.

- `dbio = par * fapar_final * RUE_max * ks * 10`: PAR [MJ/m²/día] × fPAR × RUE [g/MJ] × KS da g/m²/día, y **×10** lo pasa a **kg/ha/día**.
- `bio` = suma acumulada de `dbio`, empezando en la siembra. `dbio` es 0 antes de la siembra y después de la madurez.
- **Orden de magnitud:** con PAR ≈ 11, fPAR ≈ 0.5, RUE 1.2 y KS ≈ 0.9 salen ~60 kg/ha/día; en ~120 días, ~7 t/ha. Si les da 1 t/ha o 40 t/ha, revisen unidades.
- **Sobre `RUE_max = 1.2` (importante):** los experimentos en cebada reportan **2.6-2.9 g/MJ de PAR absorbida** sin limitaciones (Goyne et al., 1993), más del doble. Además 1.2 ≈ 0.48 × 2.5, es decir, parece una RUE respecto a la radiación **global**, no a la PAR (Bonhomme, 2000, advierte justo contra esa confusión). Nuestra fórmula la aplica a la PAR. Como `RUE_max` es una constante que multiplica todo, **no cambia el orden entre parcelas**, y con 1.2 la biomasa sale en un rango razonable (unos 6-8 t/ha). 
- **`hi_penalizado(...)`: dos opciones** (A) lineal: `HI = HI_base * (1 - hi_beta * (1 - KS_llenado))`, sin fuente (`hi_beta` es un supuesto). (B) **recomendada**, de Kemanian et al. (2007): `HI = hi0 + s * fG`, con `fG = (Bio_total - Bio_antesis) / Bio_total` (fracción de la biomasa acumulada después de la antesis); para cebada `hi0` y `s` rondan 0.3. La penalización por estrés aparece sola: el estrés en el llenado reduce la biomasa posterior a la antesis, baja `fG` y baja el HI. Acotado `0 < HI <= 0.6`.

**Sobre doble ciclo (escenario A):** en las 31 parcelas con doble ciclo la vegetación cayó en julio (corte, pastoreo o daño). Con `fapar_final` observado, la biomasa acumulada hasta esa fecha se contaría completa aunque se haya perdido. 

**Pruebas con respuesta conocida:** con `fapar_final = 0`, la biomasa no crece; con `ks = 0`, tampoco; `bio` es monótona no decreciente; duplicar `par` duplica `dbio`.

**Sensibilidad de M4:** `RUE_max` = 1.2 y 2.6, y el HI con las dos opciones (A con `hi_beta` = 0.3, 0.5 y 0.7; B de Kemanian).

---

## 7. Las 12 variables (`variables.py`, C)

Una fila por parcela. **El ciclo** es de `fecha_siembra` a `fecha_madurez`; si la madurez no se alcanza antes del 30-nov, se usa el 30-nov y se marca la parcela.

| Variable | Definición exacta | Unidad |
|---|---|---|
| `GDD_antesis` | `gdd_acum` en `fecha_antesis` | °C·d |
| `GDD_llenado` | `gdd_acum(fecha_madurez) - gdd_acum(fecha_antesis)` | °C·d |
| `DAP_antesis_est` | `(fecha_antesis - fecha_siembra)` en días | días |
| `ETo_acum` | suma de `eto` en el ciclo | mm |
| `ETa_acum` | suma de `eta` en el ciclo | mm |
| `Deficit_Hidrico_Total` | `ETo_acum - ETa_acum` (definición del prompt) | mm |
| `KS_prom_antesis` | promedio de `ks` con `estadio == "antesis"` (±10 días) | 0-1 |
| `KS_prom_llenado` | promedio de `ks` con `estadio == "llenado"` | 0-1 |
| `fPAR_integrado` | suma de `fapar_final` en el ciclo | fPAR·día |
| `Biomasa_Antesis_Sim` | `bio` en `fecha_antesis` | kg/ha |
| `Biomasa_Total_Sim` | `bio` en `fecha_madurez` | kg/ha |
| `HI_penalizado` | `hi_penalizado(KS_prom_llenado)` | 0-0.42 |

**Advertencia sobre el déficit:** como `Kc` es menor que 1 durante buena parte del ciclo, `ETo - ETa` mide sobre todo el efecto de `Kc` y no el estrés. El estrés real es `Σ(eto·kc) - Σeta`. Se mantiene la definición del prompt para `Deficit_Hidrico_Total`, pero agregamos una columna extra, `Deficit_ETc`,** en un archivo aparte para que el equipo de ML decida si la usa.

