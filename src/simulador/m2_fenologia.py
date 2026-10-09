"""Módulo 2: fenología por tiempo térmico. Ver docs/GUIA_DE_MODULOS.md (sección M2)."""
import pandas as pd

ESTADIOS = ["pre_siembra", "vegetativo", "antesis", "llenado", "madurez"]


def m2_fenologia(df_in: pd.DataFrame, params: dict) -> pd.DataFrame:
    """Requiere: tmean (M1), fecha_siembra, y para el modo 'satelite' fecha_pico, fapar_final.
    Agrega: gdd_acum, estadio (uno de ESTADIOS), kc, fecha_antesis, fecha_madurez.
    - gdd_acum: grados-día acumulados desde fecha_siembra (0 antes de sembrar), Tbase de params.
    - estadio: la ventana de antesis (+-ventana_antesis_dias) tiene prioridad sobre
      vegetativo y llenado.
    - kc: curva por tramos de FAO-56 (ini, desarrollo, mid, tardío) con Kc de params.
    - fecha_antesis, fecha_madurez: constantes por parcela, repetidas en cada fila."""
    raise NotImplementedError("M2 pendiente")
