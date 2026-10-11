"""Módulo 4: biomasa por eficiencia de uso de la luz (Monteith). Ver docs/GUIA_DE_MODULOS.md (sección 8)."""
import numpy as np
import pandas as pd

COLS_REQUERIDAS = ["ID_POLIGON", "fecha", "par", "fapar_final", "ks", "fecha_siembra", "fecha_madurez"]


def m4_lue(df_in: pd.DataFrame, params: dict) -> pd.DataFrame:
    """Requiere: par (M1), fapar_final, ks (M3), fecha_siembra y fecha_madurez (M2).
    Agrega: dbio [kg/ha/día] y bio [kg/ha, acumulada desde la siembra hasta la madurez].
    - dbio = par * min(fapar_final, 1) * RUE_max * ks * 10   (g/m2 -> kg/ha)
    - dbio es 0 antes de la siembra y después de la madurez (la siembra y la madurez cuentan).
    - bio = suma acumulada de dbio dentro de cada parcela; queda constante después de la madurez.
    RUE_max = params['cultivo']['rue_max_g_mj_par'] en g por MJ de PAR absorbida.
    No modifica df_in; conserva el orden y el índice de sus filas."""
    faltan = [c for c in COLS_REQUERIDAS if c not in df_in.columns]
    if faltan:
        raise KeyError(f"M4 requiere las columnas {faltan}")
    for c in ["par", "fapar_final", "ks", "fecha_siembra", "fecha_madurez"]:
        if df_in[c].isna().any():
            raise ValueError(f"M4: la columna '{c}' tiene valores vacíos")
    if (df_in["par"] < 0).any() or (df_in["fapar_final"] < 0).any() or not df_in["ks"].between(0, 1).all():
        raise ValueError("M4: se requiere par >= 0, fapar_final >= 0 y 0 <= ks <= 1")
    if df_in.duplicated(["ID_POLIGON", "fecha"]).any():
        raise ValueError("M4: hay filas repetidas para una misma parcela y fecha")

    rue = float(params["cultivo"]["rue_max_g_mj_par"])
    df = df_in.copy()
    fecha = pd.to_datetime(df["fecha"])
    en_ciclo = (fecha >= pd.to_datetime(df["fecha_siembra"])) & (fecha <= pd.to_datetime(df["fecha_madurez"]))
    fpar = df["fapar_final"].astype(float).clip(upper=1.0)
    dbio = np.where(en_ciclo, df["par"].astype(float) * fpar * rue * df["ks"].astype(float) * 10.0, 0.0)

    pos = np.lexsort((fecha.to_numpy(), df["ID_POLIGON"].to_numpy()))
    ordenado = pd.DataFrame({"id": df["ID_POLIGON"].to_numpy()[pos], "dbio": dbio[pos]})
    bio = np.empty(len(df))
    bio[pos] = ordenado.groupby("id", sort=False)["dbio"].cumsum().to_numpy()   # cumsum SIEMPRE dentro de la parcela

    df["dbio"], df["bio"] = dbio, bio
    return df


def hi_penalizado(bio_antesis, bio_total, ks_prom_llenado, params: dict, ks_prom_antesis=None):
    """Índice de cosecha penalizado por el estrés hídrico. Opción en params['lue']['hi_opcion']:
    (A) HI_base * (1 - hi_beta * (1 - ks_prom_llenado))
    (B) Kemanian et al. (2007): hi0 + s * fG, con fG = (bio_total - bio_antesis) / bio_total
    (C) M4 de la compañera: HI_base * (1 - sens_antesis*(1 - ks_prom_antesis) - sens_llenado*(1 - ks_prom_llenado))
    Acepta escalares o arreglos. Acotado a [0, HI_base] en A y C, y a [0, 0.6] en B.
    NUNCA se ajusta con el rendimiento."""
    lue = params["lue"]
    opcion = str(lue.get("hi_opcion", "B")).upper()
    hi_base = float(params["cultivo"]["hi_base"])
    ks_lle = np.asarray(ks_prom_llenado, dtype=float)

    if opcion == "A":
        hi = hi_base * (1.0 - float(lue["hi_beta"]) * (1.0 - ks_lle))
        tope = hi_base
    elif opcion == "B":
        bt = np.asarray(bio_total, dtype=float)
        fg = np.where(bt > 0, (bt - np.asarray(bio_antesis, dtype=float)) / np.where(bt > 0, bt, 1.0), 0.0)
        hi = float(lue["hi_kemanian"]["hi0"]) + float(lue["hi_kemanian"]["s"]) * fg
        tope = 0.6
    elif opcion == "C":
        if ks_prom_antesis is None:
            raise ValueError("La opción C de HI requiere ks_prom_antesis")
        ks_ant = np.asarray(ks_prom_antesis, dtype=float)
        hi = hi_base * (1.0 - float(lue["hi_sens_antesis"]) * (1.0 - ks_ant)
                        - float(lue["hi_sens_llenado"]) * (1.0 - ks_lle))
        tope = hi_base
    else:
        raise ValueError(f"lue.hi_opcion debe ser 'A', 'B' o 'C', se recibió {opcion!r}")
    return np.clip(hi, 0.0, tope)
