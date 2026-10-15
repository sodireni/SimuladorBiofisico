# SimuladorBiofisico

Simulador biofísico diario de cebada por parcela, del equipo de UDLAP para el Reto AgroCebada FIRA 2026. Para cada una de las 197 parcelas calcula 12 variables biofísicas (más tres columnas extra de control) que se entregan al equipo de aprendizaje automático (ML) como variables explicativas.

El simulador **nunca usa el rendimiento**: solo clima, satélite y suelo.

## Qué calcula

Cuatro módulos encadenados, día por día, del 15-mar al 30-nov de 2025 (261 días):

| Módulo | Archivo | Qué hace |
| --- | --- | --- |
| M1 clima | `src/simulador/m1_clima.py` | Radiación extraterrestre, ETo (Hargreaves-Samani) y PAR |
| M2 fenología | `src/simulador/m2_fenologia.py` | Grados-día, fechas de antesis y madurez, estadios y Kc |
| M3 balance hídrico | `src/simulador/m3_balance_hidrico.py` | Depósito de suelo, ETa y coeficiente de estrés KS |
| M4 biomasa | `src/simulador/m4_lue.py` | Biomasa por eficiencia de uso de la luz (RUE) e índice de cosecha |

`src/simulador/variables.py` resume las series diarias en las 12 variables por parcela, y `src/simulador/pipeline.py` encadena todo.

## Requisitos

Python 3.10 o superior con `pandas`, `numpy`, `pyyaml`, `matplotlib` y `pytest`:

```
pip install pandas numpy pyyaml matplotlib pytest
```

## Datos de entrada

Los archivos van en estas rutas (el formato está en `docs/CONTRATO_DE_DATOS.md`):

- `data/external/clima_diario_parcelas_2025.csv`
- `data/processed/series_satelite_diarias_2025.csv`
- `data/processed/parcelas_base.csv`

## Cómo correrlo

Desde la raíz del proyecto:

```
python -m pytest                          # pruebas de todos los módulos
python src/simulador/pipeline.py          # corrida completa
python scripts/sensibilidad.py            # análisis de sensibilidad (escribe docs/SENSIBILIDAD.md)
```

El pipeline escribe en `data/processed/`:

| Archivo | Contenido |
| --- | --- |
| `biofisicas_197_parcelas.csv` | **Entregable a ML**: `ID_parcela` y las 12 variables |
| `biofisicas_extras_197_parcelas.csv` | Columnas de control: `Deficit_ETc`, `ciclo_incompleto`, `caida_fpar_no_alcanzada` |
| `simulacion_diaria.csv` | Serie diaria por parcela (no se sube a git) |

## Parámetros

Todos los parámetros viven en `configs/params.yaml`; ningún módulo tiene valores escritos en el código. Cada uno indica su estado: **V** verificado contra la fuente, **P** plausible con reserva, **S** supuesto propio del equipo. El respaldo de cada valor está en `docs/JUSTIFICACION_PARAMETROS.md`.

Si cambias un parámetro, vuelve a correr `python -m pytest` y `python src/simulador/pipeline.py`, y reenvía los CSV a ML.

## Estructura

```
configs/params.yaml        parámetros (única fuente de verdad)
src/simulador/             módulos M1 a M4, variables, pipeline y carga de datos
scripts/                   sensibilidad y validaciones
tests/                     pruebas con datos sintéticos
docs/                      contrato de datos, fuentes, parámetros, sensibilidad
data/external/             clima descargado
data/processed/            datos procesados y resultados
legacy/                    versiones anteriores, solo de consulta
```

## Documentación

- `docs/CONTRATO_DE_DATOS.md`: columnas de entrada y salida de cada módulo.
- `docs/FUENTES.md`: fuentes, supuestos y limitaciones.
- `docs/JUSTIFICACION_PARAMETROS.md`: valor, estado y fuente de cada parámetro.
- `docs/SENSIBILIDAD.md`: efecto de cada supuesto sobre las variables.
- `docs/PROMPTS.md`: registro del uso de IA en el desarrollo.

## Reglas del equipo

- Cada módulo es una función pura `modulo(df, params)`.
- La parcela se identifica con `ID_POLIGON` dentro del simulador; `ID_parcela` aparece solo en la exportación final.
- Cambios por rama y pull request con revisión cruzada.

## Limitaciones principales

Las fechas de siembra son estimadas con NDVI, no observadas, y la fecha de siembra es el supuesto que más mueve los resultados. `Biomasa_Total_Sim` sirve para ordenar parcelas, no como valor absoluto, porque la RUE no está calibrada. `HI_penalizado` vale 0.45 en 149 de 197 parcelas, así que aporta poca variación. El detalle está en `docs/FUENTES.md` y `docs/SENSIBILIDAD.md`.
