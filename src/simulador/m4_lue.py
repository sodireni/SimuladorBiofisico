"""Módulo 4: biomasa por eficiencia de uso de la luz (Monteith). Ver docs/GUIA_DE_MODULOS.md."""
import pandas as pd


def m4_lue(df_in: pd.DataFrame, params: dict) -> pd.DataFrame:
    """Requiere: par (M1), fapar_final, ks (M3), estadio y fecha_madurez (M2), fecha_siembra.
    Agrega: dbio [kg/ha/día] y bio [kg/ha, acumulada desde la siembra hasta la madurez].
    - dbio = par * fapar_final * RUE_max * ks * 10   (g/m2 -> kg/ha)"""
    raise NotImplementedError("M4 pendiente")


def hi_penalizado(bio_antesis, bio_total, ks_prom_llenado, params: dict):
    """Índice de cosecha penalizado por el estrés del llenado. Dos opciones (ver docs/GUIA_DE_MODULOS.md):
    (A) HI_base * (1 - hi_beta * (1 - ks_prom_llenado))
    (B) Kemanian et al. (2007): hi0 + s * fG, con fG = (bio_total - bio_antesis) / bio_total
    Debe quedar acotado (0 < HI <= 0.6) y NUNCA ajustarse con el rendimiento."""
    raise NotImplementedError("M4 pendiente")
