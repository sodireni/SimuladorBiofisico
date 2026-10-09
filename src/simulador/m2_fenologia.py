"""Módulo 2: fenología por tiempo térmico. Ver docs/GUIA_DE_MODULOS.md (sección 6)."""
import numpy as np
import pandas as pd

ESTADIOS = ["pre_siembra", "vegetativo", "antesis", "llenado", "madurez"]
COLS_REQUERIDAS = ["ID_POLIGON", "fecha", "tmean", "fecha_siembra"]
COLS_MODO_SATELITE = ["fecha_pico", "fapar_final"]


def _primer_indice(condicion: np.ndarray) -> int:
    """Índice del primer True; si nunca ocurre, el último día de la serie."""
    return int(np.argmax(condicion)) if condicion.any() else len(condicion) - 1


def _fechas_umbral_gdd(gdd_acum, fen):
    """Modo 'umbral_gdd': antesis y madurez al alcanzar los GDD objetivo (índices dentro de la serie)."""
    i_ant = _primer_indice(gdd_acum >= float(fen["gdd_antesis_objetivo"]))
    i_mad = _primer_indice(gdd_acum >= float(fen["gdd_madurez_objetivo"]))
    return i_ant, i_mad


def _fechas_satelite(fechas, fapar, fecha_pico, fecha_siembra, fen):
    """Modo 'satelite': antesis = fecha_pico; madurez = primer día tras el pico con
    fapar_final <= madurez_fapar_frac_pico * (fapar en el pico)."""
    n = len(fechas)
    i_ant = int(np.clip(np.searchsorted(fechas, np.datetime64(fecha_pico)), 0, n - 1))
    pico = float(fapar[i_ant])
    despues = (np.arange(n) > i_ant) & (fapar <= float(fen["madurez_fapar_frac_pico"]) * pico)
    i_mad = _primer_indice(despues) if despues.any() else n - 1
    return i_ant, i_mad


def _kc_diario(dias, d_sie, d_ant, d_mad, cultivo, fen):
    """Kc por tramos (FAO-56) en días desde el inicio de la serie:
    inicial (kc_ini) -> desarrollo (lineal a kc_mid en la antesis) -> mid (kc_mid) -> tardío (lineal a kc_end
    en la madurez). Antes de sembrar: kc_ini (suelo desnudo). Después de la madurez: kc_end."""
    kc_ini, kc_mid, kc_end = (float(cultivo[k]) for k in ("kc_ini", "kc_mid", "kc_end"))
    fin_ini = d_sie + float(fen["kc_frac_inicial"]) * (d_ant - d_sie)
    fin_mid = d_ant + float(fen["kc_frac_mid"]) * (d_mad - d_ant)
    xp = np.array([d_sie, fin_ini, d_ant, fin_mid, d_mad], dtype=float)
    xp = np.maximum.accumulate(xp) + 1e-6 * np.arange(5)      # estrictamente creciente
    fp = np.array([kc_ini, kc_ini, kc_mid, kc_mid, kc_end])
    return np.interp(dias, xp, fp)                             # fuera de rango: kc_ini / kc_end


def m2_fenologia(df_in: pd.DataFrame, params: dict) -> pd.DataFrame:
    """Requiere: tmean (M1), fecha_siembra, y para el modo 'satelite' fecha_pico, fapar_final.
    Agrega: gdd_acum, estadio (uno de ESTADIOS), kc, fecha_antesis, fecha_madurez.
    - gdd_acum: grados-día acumulados desde fecha_siembra (0 antes de sembrar), Tbase de params.
      El día de siembra ya cuenta.
    - fecha_antesis / fecha_madurez según params['fenologia']['modo']:
        'umbral_gdd': primer día con gdd_acum >= gdd_antesis_objetivo / gdd_madurez_objetivo.
        'satelite'  : antesis = fecha_pico; madurez = primer día tras el pico con fapar_final
                      <= madurez_fapar_frac_pico * fapar del pico.
      Si la meta no se alcanza dentro de la ventana, se usa el último día de la serie de esa parcela
      (ver ciclos_incompletos()).
    - estadio: pre_siembra (antes de sembrar) -> vegetativo -> antesis (+-ventana_antesis_dias alrededor de
      fecha_antesis, con prioridad sobre vegetativo y llenado) -> llenado (hasta fecha_madurez, inclusive)
      -> madurez (después de fecha_madurez).
    - kc: curva por tramos de FAO-56 (ini, desarrollo, mid, tardío) con Kc de params.
    - fecha_antesis, fecha_madurez: constantes por parcela, repetidas en cada fila.
    No modifica df_in; conserva el orden y el índice de sus filas."""
    faltan = [c for c in COLS_REQUERIDAS if c not in df_in.columns]
    if faltan:
        raise KeyError(f"M2 requiere las columnas {faltan}")
    fen, cultivo = params["fenologia"], params["cultivo"]
    modo = fen.get("modo", "umbral_gdd")
    if modo not in ("umbral_gdd", "satelite"):
        raise ValueError(f"fenologia.modo debe ser 'umbral_gdd' o 'satelite', se recibió {modo!r}")
    if modo == "satelite":
        faltan = [c for c in COLS_MODO_SATELITE if c not in df_in.columns]
        if faltan:
            raise KeyError(f"M2 en modo 'satelite' requiere las columnas {faltan}")
    for c in ["tmean", "fecha_siembra"]:
        if df_in[c].isna().any():
            raise ValueError(f"M2: la columna '{c}' tiene valores vacíos")
    if df_in.duplicated(["ID_POLIGON", "fecha"]).any():
        raise ValueError("M2: hay filas repetidas para una misma parcela y fecha")

    tbase = float(fen["tbase_c"])
    ventana = int(fen["ventana_antesis_dias"])

    df = df_in.copy()
    fecha_all = pd.to_datetime(df["fecha"]).to_numpy("datetime64[ns]")
    pos = np.lexsort((fecha_all, df["ID_POLIGON"].to_numpy()))
    n = len(df)
    gdd_acum = np.full(n, np.nan)
    kc = np.full(n, np.nan)
    estadio = np.empty(n, dtype=object)
    f_ant = np.full(n, np.datetime64("NaT"), dtype="datetime64[ns]")
    f_mad = np.full(n, np.datetime64("NaT"), dtype="datetime64[ns]")

    trabajo = df.iloc[pos].assign(_pos=pos)
    for _, g in trabajo.groupby("ID_POLIGON", sort=False):
        idp = g["_pos"].to_numpy()
        fechas = pd.to_datetime(g["fecha"]).to_numpy("datetime64[ns]")
        siembra = pd.to_datetime(g["fecha_siembra"]).iloc[0].to_datetime64()
        despues_siembra = fechas >= siembra

        gdd = np.where(despues_siembra, np.maximum(0.0, g["tmean"].to_numpy(float) - tbase), 0.0)
        acum = np.cumsum(gdd)

        if modo == "umbral_gdd":
            i_ant, i_mad = _fechas_umbral_gdd(acum, fen)
        else:
            i_ant, i_mad = _fechas_satelite(
                fechas, g["fapar_final"].to_numpy(float),
                pd.to_datetime(g["fecha_pico"]).iloc[0], siembra, fen)
        i_mad = max(i_mad, i_ant)
        fecha_ant, fecha_mad = fechas[i_ant], fechas[i_mad]

        # --- estadios (la ventana de antesis tiene prioridad) ---
        dias_ant = (fechas - fecha_ant) / np.timedelta64(1, "D")
        est = np.select(
            [~despues_siembra,
             np.abs(dias_ant) <= ventana,
             fechas < fecha_ant,
             fechas <= fecha_mad],
            ["pre_siembra", "antesis", "vegetativo", "llenado"], default="madurez")

        # --- kc, en días desde el primer día de la serie ---
        dias = (fechas - fechas[0]) / np.timedelta64(1, "D")
        d = lambda f: float((f - fechas[0]) / np.timedelta64(1, "D"))
        kc_g = _kc_diario(dias, d(max(siembra, fechas[0])), d(fecha_ant), d(fecha_mad), cultivo, fen)

        gdd_acum[idp], kc[idp], estadio[idp] = acum, kc_g, est
        f_ant[idp], f_mad[idp] = fecha_ant, fecha_mad

    df["gdd_acum"], df["estadio"], df["kc"] = gdd_acum, estadio, kc
    df["fecha_antesis"], df["fecha_madurez"] = f_ant, f_mad
    return df


def ciclos_incompletos(df_m2: pd.DataFrame) -> pd.DataFrame:
    """Parcelas cuya antesis o madurez cae en el último día de la serie (la meta no se alcanzó dentro de
    la ventana, o coincidió justo con el último día). La guía pide marcarlas y reportar cuántas son.
    Devuelve ID_POLIGON, fecha_antesis, fecha_madurez, antesis_incompleta, madurez_incompleta."""
    ultimo = df_m2.groupby("ID_POLIGON")["fecha"].max().rename("ultimo_dia")
    por_parcela = (df_m2.drop_duplicates("ID_POLIGON")[["ID_POLIGON", "fecha_antesis", "fecha_madurez"]]
                   .merge(ultimo, on="ID_POLIGON"))
    por_parcela["antesis_incompleta"] = por_parcela["fecha_antesis"] >= por_parcela["ultimo_dia"]
    por_parcela["madurez_incompleta"] = por_parcela["fecha_madurez"] >= por_parcela["ultimo_dia"]
    return por_parcela.drop(columns="ultimo_dia")
