"""Módulo 3: balance hídrico de un solo depósito. Ver docs/GUIA_DE_MODULOS.md (sección 7)."""
import numpy as np
import pandas as pd

COLS_REQUERIDAS = ["ID_POLIGON", "fecha", "pcp", "eto", "kc", "FC_mm", "PWP_mm", "AWC_mm"]


def _balance_parcela(pcp, eto, kc, fc, pwp, awc, p, frac_inicial):
    """Balance diario de UNA parcela (arreglos ordenados por fecha). Devuelve (sw, ks, eta).

    Estado inicial (15-mar): sw = PWP + frac_inicial * AWC.
    Cada día t, con sw_prev = sw del día t-1:
        umbral = FC - p * AWC
        ks  = 1                                   si sw_prev >= umbral
              (sw_prev - PWP) / ((1 - p) * AWC)   si no (continuo en el umbral)
        eta = min(eto * kc * ks, sw_prev + pcp - PWP)   # nunca se extrae más de lo disponible
        sw  = min(FC, sw_prev + pcp - eta)              # el exceso sobre FC se pierde (drenaje)
    """
    n = len(pcp)
    sw = np.empty(n)
    ks = np.empty(n)
    eta = np.empty(n)

    umbral = fc - p * awc
    denom = (1.0 - p) * awc
    sw_prev = pwp + frac_inicial * awc

    for t in range(n):
        if sw_prev >= umbral:
            ks_t = 1.0
        else:
            ks_t = (sw_prev - pwp) / denom
        ks_t = min(1.0, max(0.0, ks_t))

        demanda = eto[t] * kc[t] * ks_t
        disponible = max(0.0, sw_prev + pcp[t] - pwp)
        eta_t = min(demanda, disponible)

        sw_t = min(fc, sw_prev + pcp[t] - eta_t)

        ks[t], eta[t], sw[t] = ks_t, eta_t, sw_t
        sw_prev = sw_t

    return sw, ks, eta


def m3_balance_hidrico(df_in: pd.DataFrame, params: dict) -> pd.DataFrame:
    """Requiere: pcp, eto, kc, FC_mm, PWP_mm, AWC_mm (más ID_POLIGON y fecha).
    Agrega: sw [mm], ks [0-1], eta [mm/día].
    - KS del día t se calcula con SW del día t-1 (evita la circularidad).
    - SW_t = max(PWP, min(FC, SW_{t-1} + pcp_t - eta_t)); el exceso sobre FC se pierde (drenaje).
    - eta = eto * kc * ks, limitada al agua que realmente hay sobre PWP.

    Parámetros (configs/params.yaml): cultivo.p_agotamiento, suelo.sw_inicial_frac_awc.
    Supuestos: sin escurrimiento, sin riego, sin ascenso capilar, raíz de 0-60 cm.
    No modifica df_in; conserva el orden y el índice de sus filas."""
    faltan = [c for c in COLS_REQUERIDAS if c not in df_in.columns]
    if faltan:
        raise KeyError(f"M3 requiere las columnas {faltan}")
    for c in ["pcp", "eto", "kc", "FC_mm", "PWP_mm", "AWC_mm"]:
        if df_in[c].isna().any():
            raise ValueError(f"M3: la columna '{c}' tiene valores vacíos; el balance no puede continuar")
    if df_in.duplicated(["ID_POLIGON", "fecha"]).any():
        raise ValueError("M3: hay filas repetidas para una misma parcela y fecha")

    p = float(params["cultivo"]["p_agotamiento"])
    frac0 = float(params["suelo"]["sw_inicial_frac_awc"])
    if not 0.0 <= p < 1.0:
        raise ValueError(f"p_agotamiento debe estar en [0, 1), se recibió {p}")
    if not 0.0 <= frac0 <= 1.0:
        raise ValueError(f"sw_inicial_frac_awc debe estar en [0, 1], se recibió {frac0}")

    df = df_in.copy()
    # posiciones (no etiquetas) para que funcione aunque el índice esté repetido o desordenado
    pos = np.lexsort((df["fecha"].to_numpy(), df["ID_POLIGON"].to_numpy()))
    trabajo = df.iloc[pos]
    sw = np.full(len(df), np.nan)
    ks = np.full(len(df), np.nan)
    eta = np.full(len(df), np.nan)

    for _, g in trabajo.assign(_pos=pos).groupby("ID_POLIGON", sort=False):
        idp = g["_pos"].to_numpy()
        suelo = g[["FC_mm", "PWP_mm", "AWC_mm"]]
        if (suelo.nunique() > 1).any():
            raise ValueError(f"M3: el suelo cambia dentro de la parcela {g['ID_POLIGON'].iloc[0]}")
        fc, pwp, awc = (float(suelo[c].iloc[0]) for c in ["FC_mm", "PWP_mm", "AWC_mm"])
        if awc <= 0 or fc <= pwp:
            raise ValueError(f"M3: suelo inválido en {g['ID_POLIGON'].iloc[0]} (FC={fc}, PWP={pwp}, AWC={awc})")

        s, k, e = _balance_parcela(
            g["pcp"].to_numpy(float), g["eto"].to_numpy(float), g["kc"].to_numpy(float),
            fc, pwp, awc, p, frac0)
        sw[idp], ks[idp], eta[idp] = s, k, e

    df["sw"], df["ks"], df["eta"] = sw, ks, eta
    return df
