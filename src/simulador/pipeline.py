"""Encadena M1 -> M2 -> M3 -> M4 y calcula las 12 variables. Uso: python src/simulador/pipeline.py"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))   # permite correrlo como script

from simulador.io import cargar_entrada, cargar_params
from simulador.m1_clima import m1_clima
from simulador.m2_fenologia import m2_fenologia
from simulador.m3_balance_hidrico import m3_balance_hidrico
from simulador.m4_lue import m4_lue
from simulador.variables import calcular_variables, exportar_entregable


def correr(raiz="."):
    params = cargar_params(raiz)
    diario, base = cargar_entrada(raiz)
    df = m4_lue(m3_balance_hidrico(m2_fenologia(m1_clima(diario, params), params), params), params)
    variables = calcular_variables(df, base, params)
    return df, variables


if __name__ == "__main__":
    df, variables = correr()
    Path("data/processed").mkdir(parents=True, exist_ok=True)
    df.to_csv("data/processed/simulacion_diaria.csv", index=False)
    exportar_entregable(variables, "data/processed/biofisicas_197_parcelas.csv")
    print("Listo:", variables.shape)
