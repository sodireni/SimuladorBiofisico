"""Las 12 variables biofísicas por parcela y el entregable final."""
import pandas as pd

VARIABLES_12 = [
    "GDD_antesis", "GDD_llenado", "DAP_antesis_est", "ETo_acum", "ETa_acum",
    "Deficit_Hidrico_Total", "KS_prom_antesis", "KS_prom_llenado", "fPAR_integrado",
    "Biomasa_Antesis_Sim", "Biomasa_Total_Sim", "HI_penalizado",
]


def calcular_variables(df_diario: pd.DataFrame, base: pd.DataFrame, params: dict) -> pd.DataFrame:
    """Una fila por parcela: ID_POLIGON + VARIABLES_12. Definiciones en docs/GUIA_DE_MODULOS.md."""
    raise NotImplementedError("Variables pendientes")


def exportar_entregable(variables: pd.DataFrame, ruta: str) -> pd.DataFrame:
    """Verifica y guarda biofisicas_197_parcelas.csv con ID_parcela y las 12 variables."""
    faltan = [c for c in ["ID_POLIGON", *VARIABLES_12] if c not in variables.columns]
    if faltan:
        raise ValueError(f"Faltan columnas: {faltan}")
    if variables["ID_POLIGON"].duplicated().any():
        raise ValueError("Hay parcelas repetidas")
    if variables[VARIABLES_12].isna().any().any():
        raise ValueError("Hay valores vacíos en las 12 variables")
    salida = variables[["ID_POLIGON", *VARIABLES_12]].rename(columns={"ID_POLIGON": "ID_parcela"})
    salida.to_csv(ruta, index=False)
    return salida
