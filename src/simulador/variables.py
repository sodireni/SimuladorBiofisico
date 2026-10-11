"""Las 12 variables biofísicas por parcela y el entregable final. Definiciones: docs/GUIA_DE_MODULOS.md (sección 9)."""
import numpy as np
import pandas as pd

from simulador.m2_fenologia import ciclos_incompletos
from simulador.m4_lue import hi_penalizado

VARIABLES_12 = [
    "GDD_antesis", "GDD_llenado", "DAP_antesis_est", "ETo_acum", "ETa_acum",
    "Deficit_Hidrico_Total", "KS_prom_antesis", "KS_prom_llenado", "fPAR_integrado",
    "Biomasa_Antesis_Sim", "Biomasa_Total_Sim", "HI_penalizado",
]
EXTRAS = ["Deficit_ETc", "ciclo_incompleto", "caida_fpar_no_alcanzada"]
COLS_REQUERIDAS = ["ID_POLIGON", "fecha", "fecha_siembra", "fecha_antesis", "fecha_madurez", "fecha_pico",
                   "gdd_acum", "estadio", "eto", "kc", "eta", "ks", "fapar_final", "bio"]


def _valor_en_fecha(g: pd.DataFrame, columna: str, fecha: pd.Timestamp) -> float:
    fila = g.loc[g["fecha"] == fecha, columna]
    if fila.empty:
        raise ValueError(f"La serie de {g['ID_POLIGON'].iloc[0]} no incluye el día {fecha:%Y-%m-%d} "
                         f"(necesario para '{columna}')")
    return float(fila.iloc[0])


def _gdd_hasta_caida_fpar(g: pd.DataFrame, fecha_pico: pd.Timestamp, frac: float):
    """Primer día después del pico con fapar_final <= frac * (fapar en el pico). Devuelve (gdd_acum ese día, alcanzado).
    Si la caída nunca ocurre dentro de la ventana, usa el último día de la serie y alcanzado = False."""
    g = g.sort_values("fecha")
    fechas = g["fecha"].to_numpy("datetime64[ns]")
    fapar = g["fapar_final"].to_numpy(float)
    i_pico = int(np.clip(np.searchsorted(fechas, np.datetime64(fecha_pico)), 0, len(g) - 1))
    despues = (np.arange(len(g)) > i_pico) & (fapar <= frac * fapar[i_pico])
    alcanzado = bool(despues.any())
    i_fin = int(np.argmax(despues)) if alcanzado else len(g) - 1
    return float(g["gdd_acum"].to_numpy(float)[i_fin]), alcanzado


def calcular_variables(df_diario: pd.DataFrame, base: pd.DataFrame, params: dict) -> pd.DataFrame:
    """Una fila por parcela: ID_POLIGON + VARIABLES_12 + EXTRAS. Requiere las columnas de M1 a M4.
    El ciclo es de fecha_siembra a fecha_madurez, ambos días incluidos.
    GDD_antesis y GDD_llenado dependen de params['fenologia']['gdd_variables_ref']:
      'pico_ndvi' (decisión del equipo): GDD_antesis = gdd_acum(fecha_pico); GDD_llenado = gdd_acum(día en que el fPAR cae a
                  madurez_fapar_frac_pico del valor del pico) - gdd_acum(fecha_pico). Siempre >= 0.
      'pico_ndvi_hasta_madurez_modelo': GDD_antesis igual; GDD_llenado = gdd_acum(fecha_madurez) - gdd_acum(fecha_pico), con 0 si el
                  pico cae después de la madurez (en las parcelas reales eso pasó en 61 de 197).
      'antesis'   (definición de la guía): gdd_acum(fecha_antesis) y gdd_acum(fecha_madurez) - gdd_acum(fecha_antesis); casi constantes en modo umbral.
    Extras: Deficit_ETc = suma(eto*kc) - suma(eta) (estrés real, ver guía), ciclo_incompleto (la madurez no se alcanzó
    antes del fin de la ventana) y caida_fpar_no_alcanzada (el fPAR no cae a la fracción indicada antes del fin de la ventana;
    solo aplica a 'pico_ndvi'; en ese caso GDD_llenado llega al último día de la serie)."""
    faltan = [c for c in COLS_REQUERIDAS if c not in df_diario.columns]
    if faltan:
        raise KeyError(f"calcular_variables requiere las columnas {faltan}")
    ref = params["fenologia"].get("gdd_variables_ref", "pico_ndvi")
    if ref not in ("pico_ndvi", "pico_ndvi_hasta_madurez_modelo", "antesis"):
        raise ValueError("fenologia.gdd_variables_ref debe ser 'pico_ndvi', 'pico_ndvi_hasta_madurez_modelo' o 'antesis', "
                         f"se recibió {ref!r}")
    col_ref = ("fecha_antesis" if ref == "antesis" else "fecha_pico")
    frac_fpar = float(params["fenologia"]["madurez_fapar_frac_pico"])

    d = df_diario.copy()
    d["fecha"] = pd.to_datetime(d["fecha"])
    incompletos = ciclos_incompletos(d).set_index("ID_POLIGON")["madurez_incompleta"]

    filas = []
    for id_poligon, g in d.groupby("ID_POLIGON", sort=True):
        siembra, antesis, madurez = (pd.Timestamp(g[c].iloc[0]) for c in ("fecha_siembra", "fecha_antesis", "fecha_madurez"))
        fecha_ref = pd.Timestamp(g[col_ref].iloc[0])
        ciclo = g[(g["fecha"] >= siembra) & (g["fecha"] <= madurez)]

        gdd_ref = _valor_en_fecha(g, "gdd_acum", fecha_ref)
        if ref == "pico_ndvi":
            gdd_fin_llenado, caida_ok = _gdd_hasta_caida_fpar(g, fecha_ref, frac_fpar)
        else:
            gdd_fin_llenado, caida_ok = _valor_en_fecha(g, "gdd_acum", madurez), True
        eto_acum, eta_acum = float(ciclo["eto"].sum()), float(ciclo["eta"].sum())
        etc_acum = float((ciclo["eto"] * ciclo["kc"]).sum())
        ks_ant = g.loc[g["estadio"] == "antesis", "ks"]
        ks_lle = g.loc[g["estadio"] == "llenado", "ks"]
        ks_ant = float(ks_ant.mean()) if len(ks_ant) else np.nan
        ks_lle = float(ks_lle.mean()) if len(ks_lle) else np.nan
        bio_ant = _valor_en_fecha(g, "bio", antesis)
        bio_tot = _valor_en_fecha(g, "bio", madurez)

        filas.append({
            "ID_POLIGON": id_poligon,
            "GDD_antesis": gdd_ref,
            "GDD_llenado": max(0.0, gdd_fin_llenado - gdd_ref),
            "DAP_antesis_est": float((antesis - siembra).days),
            "ETo_acum": eto_acum,
            "ETa_acum": eta_acum,
            "Deficit_Hidrico_Total": eto_acum - eta_acum,
            "KS_prom_antesis": ks_ant,
            "KS_prom_llenado": ks_lle,
            "fPAR_integrado": float(ciclo["fapar_final"].clip(0.0, 1.0).sum()),
            "Biomasa_Antesis_Sim": bio_ant,
            "Biomasa_Total_Sim": bio_tot,
            "HI_penalizado": float(hi_penalizado(bio_ant, bio_tot, ks_lle, params, ks_prom_antesis=ks_ant)),
            "Deficit_ETc": etc_acum - eta_acum,
            "ciclo_incompleto": bool(incompletos.loc[id_poligon]),
            "caida_fpar_no_alcanzada": not caida_ok,
        })
    return pd.DataFrame(filas, columns=["ID_POLIGON", *VARIABLES_12, *EXTRAS])


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


def exportar_extras(variables: pd.DataFrame, ruta: str) -> pd.DataFrame:
    """Guarda aparte las columnas extra (Deficit_ETc y la marca de ciclo incompleto) para el equipo de ML."""
    faltan = [c for c in ["ID_POLIGON", *EXTRAS] if c not in variables.columns]
    if faltan:
        raise ValueError(f"Faltan columnas: {faltan}")
    salida = variables[["ID_POLIGON", *EXTRAS]].rename(columns={"ID_POLIGON": "ID_parcela"})
    salida.to_csv(ruta, index=False)
    return salida
