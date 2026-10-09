"""Corre M1 -> M2 -> M3 con los datos reales y guarda el resultado diario para trabajar el módulo 4.
Uso (desde la raíz del repositorio):

    python scripts/exportar_m1_m3.py

Salida: data/processed/simulacion_m1_m3.csv (una fila por parcela y día; ~51,417 filas).
Si existe el CSV del módulo 1 antiguo (data/processed/clima_m1_procesado.csv), compara su ETo con la nueva."""
import sys
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(RAIZ / "src"))

import numpy as np
import pandas as pd

from simulador.io import cargar_entrada, cargar_params
from simulador.m1_clima import m1_clima
from simulador.m2_fenologia import m2_fenologia
from simulador.m3_balance_hidrico import m3_balance_hidrico

params = cargar_params(str(RAIZ))
diario, _ = cargar_entrada(str(RAIZ))
df = m3_balance_hidrico(m2_fenologia(m1_clima(diario, params), params), params)

salida = RAIZ / "data/processed/simulacion_m1_m3.csv"
df.to_csv(salida, index=False, date_format="%Y-%m-%d")
print(f"Guardado: {salida.relative_to(RAIZ)}  |  {df.shape[0]:,} filas x {df.shape[1]} columnas")
print(f"Modo de fenología: {params['fenologia']['modo']}  |  Tbase: {params['fenologia']['tbase_c']} °C")
print("Columnas nuevas de M1-M3:", [c for c in ["tmean", "ra", "par", "eto", "gdd_acum", "estadio", "kc",
                                                "fecha_antesis", "fecha_madurez", "sw", "ks", "eta"] if c in df.columns])

viejo = RAIZ / "data/processed/clima_m1_procesado.csv"
if viejo.exists():
    v = pd.read_csv(viejo, usecols=["ID_POLIGON", "fecha", "tmean", "ra", "par", "eto"], parse_dates=["fecha"])
    c = df[["ID_POLIGON", "fecha", "tmean", "ra", "par", "eto"]].merge(v, on=["ID_POLIGON", "fecha"], suffixes=("", "_viejo"))
    print(f"\nComparación con el M1 antiguo ({len(c):,} filas en común):")
    for col in ["tmean", "ra", "par", "eto"]:
        dif = (c[col] - c[f"{col}_viejo"]).abs().max()
        print(f"  {col:<6} diferencia máxima: {dif:.2e}  {'[OK]' if dif < 1e-6 else '[REVISAR]'}")
