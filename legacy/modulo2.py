# modulos/modulo2.py
# -*- coding: utf-8 -*-
"""
MÓDULO 2: FENOLOGÍA Y GDD - Reto AgroCebada FIRA 2026
Simula la fenología diaria por parcela combinando fechas satelitales (NDVI)
y tiempo térmico (Grados Día de Desarrollo).

Entradas : data/processed/clima_m1_procesado.csv
           data/processed/parcelas_base.csv
Salida   : data/processed/fenologia_m2_procesado.csv
"""

from pathlib import Path

import numpy as np
import pandas as pd

# ----------------------------------------------------------------------------
# CONSTANTES
# ----------------------------------------------------------------------------
N_PARCELAS_ESPERADAS = 197
TBASE = 2.0
GDD_MADUREZ_TARGET = 1450.0

KC_INI_VEG, KC_FIN_VEG = 0.30, 1.15      # vegetativo_antesis: 0.30 -> 1.15
KC_INI_LLE, KC_FIN_LLE = 1.15, 0.25      # llenado_grano:      1.15 -> 0.25
KC_MADURO = 0.25
KC_PRE = 0.0

COLS_CLIMA = ["ID_POLIGON", "fecha", "tmean", "tmax", "tmin", "eto", "par", "pcp"]

ROOT = Path(__file__).resolve().parent.parent
PATH_CLIMA = ROOT / "data" / "processed" / "clima_m1_procesado.csv"
PATH_PARCELAS = ROOT / "data" / "processed" / "parcelas_base.csv"
PATH_SALIDA = ROOT / "data" / "processed" / "fenologia_m2_procesado.csv"


# ----------------------------------------------------------------------------
# FUNCIÓN PURA DEL MÓDULO 2
# ----------------------------------------------------------------------------
def modulo_2(
    df_clima_parcela: pd.DataFrame,
    fecha_sos: str,
    fecha_pico: str,
    tbase: float = TBASE,
    gdd_madurez_target: float = GDD_MADUREZ_TARGET,
) -> pd.DataFrame:
    """
    Simula la fenología diaria de UNA parcela.

    Parámetros
    ----------
    df_clima_parcela : DataFrame diario de una sola parcela (col. 'fecha', 'tmean', ...).
    fecha_sos        : fecha de emergencia / inicio de crecimiento (NDVI).
    fecha_pico       : fecha de antesis / pico de NDVI.
    tbase            : temperatura base (°C).
    gdd_madurez_target : GDD acumulados desde fecha_sos que definen madurez fisiológica.

    Devuelve
    --------
    DataFrame diario con: gdd_diario, gdd_acum, estadio, kc, GDD_antesis, GDD_llenado.
    (GDD_antesis y GDD_llenado son constantes por parcela, repetidas en cada fila.)
    """
    df = df_clima_parcela.copy()
    df["fecha"] = pd.to_datetime(df["fecha"])
    df = df.sort_values("fecha").drop_duplicates(subset="fecha").reset_index(drop=True)

    sos = pd.Timestamp(fecha_sos)
    pico = pd.Timestamp(fecha_pico)

    # Tmean: si falta, se reconstruye con (tmax + tmin) / 2; huecos restantes se
    # interpolan en el tiempo (la simulación no puede tener NaN).
    tmean = df["tmean"].astype(float)
    tmean = tmean.fillna((df["tmax"].astype(float) + df["tmin"].astype(float)) / 2.0)
    tmean = tmean.interpolate(limit_direction="both")

    # 1) GDD diario
    df["gdd_diario"] = np.maximum(0.0, tmean - tbase)

    # 2) GDD acumulado desde fecha_sos (días previos = 0)
    desde_sos = df["fecha"] >= sos
    df["gdd_acum"] = (df["gdd_diario"].where(desde_sos, 0.0)).cumsum()

    # 3) Variables clave FIRA
    mask_antesis = (df["fecha"] >= sos) & (df["fecha"] <= pico)
    gdd_antesis = float(df.loc[mask_antesis, "gdd_diario"].sum())

    # Llenado: desde el día posterior a fecha_pico hasta madurez (tope = target)
    # o hasta el fin de la ventana si no se alcanza.
    if df["fecha"].iloc[-1] > pico:
        gdd_fin = float(df["gdd_acum"].iloc[-1])
        gdd_llenado = max(0.0, min(gdd_fin, gdd_madurez_target) - gdd_antesis)
    else:
        gdd_llenado = 0.0

    # 4) Estadio fenológico
    fecha = df["fecha"]
    acum = df["gdd_acum"]
    cond = [
        fecha < sos,
        (fecha >= sos) & (fecha <= pico),
        (fecha > pico) & (acum <= gdd_madurez_target),
    ]
    df["estadio"] = np.select(
        cond, ["pre_emergencia", "vegetativo_antesis", "llenado_grano"], default="maduro"
    )

    # 5) Kc (interpolación lineal en tiempo térmico)
    # Vegetativo: fracción = gdd_acum / GDD_antesis (si es 0, se usa fracción en días)
    if gdd_antesis > 0:
        frac_veg = (acum / gdd_antesis).clip(0.0, 1.0)
    else:
        dias_veg = max((pico - sos).days, 1)
        frac_veg = (((fecha - sos).dt.days) / dias_veg).clip(0.0, 1.0)

    # Llenado: fracción = (gdd_acum - GDD_antesis) / (target - GDD_antesis)
    rango_lle = gdd_madurez_target - gdd_antesis
    if rango_lle > 0:
        frac_lle = ((acum - gdd_antesis) / rango_lle).clip(0.0, 1.0)
    else:
        frac_lle = pd.Series(1.0, index=df.index)

    kc_veg = KC_INI_VEG + (KC_FIN_VEG - KC_INI_VEG) * frac_veg
    kc_lle = KC_INI_LLE + (KC_FIN_LLE - KC_INI_LLE) * frac_lle

    df["kc"] = np.select(
        [df["estadio"] == "pre_emergencia",
         df["estadio"] == "vegetativo_antesis",
         df["estadio"] == "llenado_grano"],
        [KC_PRE, kc_veg, kc_lle],
        default=KC_MADURO,
    ).astype(float)

    df["GDD_antesis"] = gdd_antesis
    df["GDD_llenado"] = gdd_llenado
    return df


# ----------------------------------------------------------------------------
# UTILIDADES DE EJECUCIÓN
# ----------------------------------------------------------------------------
def _preparar_fechas_parcelas(df_parc: pd.DataFrame, ids_clima) -> pd.DataFrame:
    """
    Devuelve una tabla ID_POLIGON / fecha_sos / fecha_pico completa.
    Faltantes (o parcelas ausentes en parcelas_base) -> mediana de fechas válidas.
    Si fecha_pico < fecha_sos, se considera inválida y se reemplaza igual.
    """
    df = df_parc[["ID_POLIGON", "fecha_sos", "fecha_pico"]].copy()
    df["fecha_sos"] = pd.to_datetime(df["fecha_sos"], errors="coerce")
    df["fecha_pico"] = pd.to_datetime(df["fecha_pico"], errors="coerce")
    df = df.drop_duplicates(subset="ID_POLIGON")

    # Asegura que todas las parcelas del clima estén presentes
    df = (pd.DataFrame({"ID_POLIGON": pd.Series(list(ids_clima))})
          .merge(df, on="ID_POLIGON", how="left"))

    # Fechas inconsistentes (pico antes de sos) -> se tratan como faltantes
    incons = df["fecha_pico"] < df["fecha_sos"]
    df.loc[incons, ["fecha_sos", "fecha_pico"]] = pd.NaT

    med_sos = df["fecha_sos"].dropna().median()
    med_pico = df["fecha_pico"].dropna().median()
    if pd.isna(med_sos) or pd.isna(med_pico):
        raise ValueError("No hay fechas SOS/pico válidas para calcular la mediana.")

    n_sos, n_pico = int(df["fecha_sos"].isna().sum()), int(df["fecha_pico"].isna().sum())
    if n_sos or n_pico:
        print(f"[AVISO] Imputando con mediana -> fecha_sos: {n_sos} parcelas "
              f"({med_sos.date()}), fecha_pico: {n_pico} parcelas ({med_pico.date()}).")

    df["fecha_sos"] = df["fecha_sos"].fillna(med_sos)
    df["fecha_pico"] = df["fecha_pico"].fillna(med_pico)

    # Garantiza orden lógico tras imputación parcial
    malo = df["fecha_pico"] < df["fecha_sos"]
    df.loc[malo, "fecha_pico"] = df.loc[malo, "fecha_sos"]
    return df


def _validar(df_out: pd.DataFrame) -> None:
    print("\n" + "=" * 70)
    print("VALIDACIÓN AUTOMÁTICA - MÓDULO 2")
    print("=" * 70)

    n_parc = df_out["ID_POLIGON"].nunique()
    estado = "OK" if n_parc == N_PARCELAS_ESPERADAS else "REVISAR"
    print(f"Cobertura de parcelas : {n_parc}/{N_PARCELAS_ESPERADAS}  [{estado}]")
    print(f"Filas diarias totales : {len(df_out):,}")

    n_nan = int(df_out.isna().sum().sum())
    print(f"Valores nulos (NaN)   : {n_nan}  [{'OK' if n_nan == 0 else 'REVISAR'}]")
    if n_nan:
        print(df_out.isna().sum()[lambda s: s > 0].to_string())

    por_parcela = df_out.drop_duplicates(subset="ID_POLIGON")
    print("\nResumen por parcela (promedio / mín / máx):")
    for col in ["GDD_antesis", "GDD_llenado"]:
        s = por_parcela[col]
        print(f"  {col:<12}: {s.mean():9.1f} / {s.min():9.1f} / {s.max():9.1f}")

    print("\nDistribución de estadios (% de días):")
    print((df_out["estadio"].value_counts(normalize=True) * 100).round(1).to_string())
    print(f"\nKc rango: {df_out['kc'].min():.2f} - {df_out['kc'].max():.2f}")
    print("=" * 70 + "\n")


# ----------------------------------------------------------------------------
# MAIN
# ----------------------------------------------------------------------------
if __name__ == "__main__":
    # 1) Carga
    clima = pd.read_csv(PATH_CLIMA, usecols=COLS_CLIMA, parse_dates=["fecha"])
    parcelas = pd.read_csv(PATH_PARCELAS)
    print(f"Clima cargado    : {clima.shape} | parcelas: {clima['ID_POLIGON'].nunique()}")
    print(f"Parcelas base    : {parcelas.shape}")

    # 2) Fechas por parcela (con imputación por mediana)
    ids_clima = clima["ID_POLIGON"].unique()
    fechas = _preparar_fechas_parcelas(parcelas, ids_clima).set_index("ID_POLIGON")

    # 3) Procesamiento por parcela
    resultados = []
    for id_pol, g in clima.groupby("ID_POLIGON", sort=True):
        sos = fechas.at[id_pol, "fecha_sos"]
        pico = fechas.at[id_pol, "fecha_pico"]
        resultados.append(
            modulo_2(
                g,
                fecha_sos=sos.strftime("%Y-%m-%d"),
                fecha_pico=pico.strftime("%Y-%m-%d"),
                tbase=TBASE,
                gdd_madurez_target=GDD_MADUREZ_TARGET,
            )
        )
    df_out = pd.concat(resultados, ignore_index=True)

    # 4) Validación
    _validar(df_out)

    # 5) Guardado
    PATH_SALIDA.parent.mkdir(parents=True, exist_ok=True)
    df_out["fecha"] = df_out["fecha"].dt.strftime("%Y-%m-%d")
    df_out.to_csv(PATH_SALIDA, index=False)
    print(f"Salida guardada en: {PATH_SALIDA}")