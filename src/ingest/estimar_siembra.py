"""
Estima la fecha de siembra de cada parcela a partir del NDVI diario de Planet.

NO hay fechas reales de siembra, así que se infiere (SUPUESTO del equipo, documentarlo):
  0. Doble ciclo: si antes del pico principal hay otro pico que luego cae hasta la mitad hacia la
     base (corte, chapeo, barbecho o resiembra), la parcela se marca "doble_ciclo". La fecha
     principal es la del ciclo del pico más alto (escenario B: es el que probablemente se
     cosechó); la del primer ciclo se guarda aparte (escenario A) para medir su efecto.
  1. Pico del ciclo: fecha del NDVI suavizado máximo. Base: NDVI mínimo antes del pico.
  2. Inicio de crecimiento (SOS): se camina hacia atrás desde el pico hasta el último día con
     NDVI <= base + pct_amplitud * (pico - base). Así un pico previo (p. ej. maleza) que vuelve
     a bajar antes del crecimiento real no se confunde con el arranque del cultivo.
  3. Siembra: desde el SOS se retrocede acumulando grados-día (Tbase de params.yaml) hasta
     sumar gdd_siembra_a_sos (cubre emergencia y cierre del dosel).
Autoverificación sin usar rendimiento: los GDD entre siembra y pico deberían ser del orden de la
antesis de cebada (~800-1000 °C·d). Además se repite con umbrales de 10 % y 30 % para medir cuánto
se mueve la fecha (análisis de sensibilidad).

Requiere haber corrido antes descargar_clima_diario_2025.py, limpiar_satelite.py y calibrar_fpar.py.

Uso (desde la carpeta principal del proyecto):
    python src/ingest/estimar_siembra.py

Salidas:
    data/processed/siembra_estimada.csv
    docs/fig_siembra_qc.png
"""
import os

import numpy as np
import pandas as pd
import yaml
from scipy.signal import find_peaks

SERIES = "data/processed/series_satelite_diarias_2025.csv"
CLIMA = "data/external/clima_diario_parcelas_2025.csv"
SHP = "data/raw/Parcelas_Reto_AGC_CONJUNTO.shp"
PARAMS = "configs/params.yaml"
SALIDA = "data/processed/siembra_estimada.csv"
FIGURA = "docs/fig_siembra_qc.png"
UN_DIA = pd.Timedelta(days=1)


def sos_desde_pico(s, pico, pct, desde=None, base=None):
    """s: NDVI diario (Series con índice de fechas). 'desde' y 'base' permiten acotar el análisis
    al ciclo que empieza en un valle. Devuelve (fecha_sos, base, amplitud, en_borde)."""
    antes = s[desde:pico] if desde is not None else s[:pico]
    base = antes.min() if base is None else base
    amp = s[pico] - base
    debajo = antes[antes <= base + pct * amp]
    if debajo.empty:
        return antes.index[0], base, amp, True
    return debajo.index[-1] + UN_DIA, base, amp, False


def detectar_doble_ciclo(s, pico, S):
    """Busca un pico previo (el más cercano al principal) que sobresalga y cuyo valle caiga
    al menos 'caida_valle_fraccion' hacia la base. Devuelve (fecha_p1, p1, fecha_valle, valle) o None."""
    antes = s[:pico]
    idx, _ = find_peaks(antes.values, prominence=S["prominencia_pico_previo"])
    base = antes.min()
    for i in idx[::-1]:
        f1, p1 = antes.index[i], antes.iloc[i]
        tramo = s[f1:pico]
        valle, f_valle = tramo.min(), tramo.idxmin()
        if f_valle > f1 and valle <= base + S["caida_valle_fraccion"] * (p1 - base):
            return f1, p1, f_valle, valle
    return None


def siembra_desde_sos(gdd, sos, objetivo):
    """Retrocede desde el SOS acumulando GDD hasta 'objetivo'. Devuelve (fecha, alcanzado)."""
    previo = gdd[: sos - UN_DIA].iloc[::-1].cumsum()
    ok = previo[previo >= objetivo]
    if ok.empty:
        return gdd.index[0], False
    return ok.index[0], True


def main():
    P = yaml.safe_load(open(PARAMS))
    tbase = P["fenologia"]["tbase_c"]
    S = P["siembra"]

    ser = pd.read_csv(SERIES, parse_dates=["fecha"])
    cli = pd.read_csv(CLIMA, parse_dates=["fecha"])
    cli["gdd"] = np.maximum(0, (cli["temperature_2m_max"] + cli["temperature_2m_min"]) / 2 - tbase)

    filas = []
    for pid, g in ser.groupby("ID_POLIGON"):
        s = g.set_index("fecha")["ndvi_planet"].dropna()
        gdd = cli[cli["ID_POLIGON"] == pid].set_index("fecha")["gdd"]
        fila = {"ID_POLIGON": pid}
        flags = []
        if len(s) < 30:
            fila["flag_calidad"] = "sin_serie"
            filas.append(fila)
            continue
        pico = s.idxmax()
        dbl = detectar_doble_ciclo(s, pico, S)
        kw = {"desde": dbl[2], "base": dbl[3]} if dbl else {}
        sos, base, amp, borde_sos = sos_desde_pico(s, pico, S["pct_amplitud"], **kw)
        siembra, ok_gdd = siembra_desde_sos(gdd, sos, S["gdd_siembra_a_sos"])
        if dbl:
            flags.append("doble_ciclo")
            sos_a = sos_desde_pico(s, dbl[0], S["pct_amplitud"])[0]
            siembra_a = siembra_desde_sos(gdd, sos_a, S["gdd_siembra_a_sos"])[0]
            fila.update({"fecha_pico_previo": dbl[0].date(), "ndvi_pico_previo": round(dbl[1], 3),
                         "fecha_valle": dbl[2].date(), "ndvi_valle": round(dbl[3], 3),
                         "fecha_siembra_A": siembra_a.date()})

        if s[pico] < S["ndvi_pico_minimo"]:
            flags.append("pico_bajo")
        if amp < S["amplitud_minima"]:
            flags.append("amplitud_baja")
        if borde_sos:
            flags.append("sos_en_borde")
        if not ok_gdd:
            flags.append("siembra_en_borde")
        if pico == s.index[-1]:
            flags.append("pico_al_final")

        fila.update({
            "doble_ciclo": bool(dbl),
            "fecha_pico": pico.date(), "ndvi_pico": round(s[pico], 3),
            "ndvi_base": round(base, 3), "amplitud": round(amp, 3),
            "fecha_sos": sos.date(), "fecha_siembra": siembra.date(),
            "gdd_sos_pico": round(gdd[sos:pico].sum(), 0),
            "gdd_siembra_pico": round(gdd[siembra:pico].sum(), 0),
            "dias_siembra_pico": (pico - siembra).days,
            "flag_calidad": ";".join(flags) if flags else "ok",
        })
        for pr in (0.12, 0.30):       # sensibilidad del criterio de doble ciclo
            fila[f"doble_prom_{int(pr * 100)}"] = bool(detectar_doble_ciclo(
                s, pico, {**S, "prominencia_pico_previo": pr}))
        for pct in (0.10, 0.30):      # sensibilidad
            fila[f"fecha_sos_{int(pct * 100)}"] = sos_desde_pico(s, pico, pct, **kw)[0].date()
        filas.append(fila)

    df = pd.DataFrame(filas)

    try:                               # Estado y municipio (útiles para agrupar y validar)
        import geopandas as gpd
        meta = gpd.read_file(SHP)[["ID_POLIGON", "Estado", "Municipio"]]
        df = df.merge(meta, on="ID_POLIGON", how="left")
    except Exception as e:
        print("Aviso: no se pudo leer Estado/Municipio del shapefile:", e)

    os.makedirs(os.path.dirname(SALIDA), exist_ok=True)
    df.to_csv(SALIDA, index=False)

    # ---------------- Diagnóstico ----------------
    def fechas_q_df(datos, col, qs=(0, .1, .5, .9, 1)):
        d = pd.to_datetime(datos[col]).dt.dayofyear.dropna()
        return [(pd.Timestamp("2025-01-01") + pd.Timedelta(days=int(d.quantile(q)) - 1)).strftime("%d-%b")
                for q in qs]

    def fechas_q(col, qs=(0, .1, .5, .9, 1)):
        d = pd.to_datetime(df[col]).dt.dayofyear.dropna()
        return [(pd.Timestamp("2025-01-01") + pd.Timedelta(days=int(d.quantile(q)) - 1)).strftime("%d-%b")
                for q in qs]

    n_dbl = int(df["doble_ciclo"].sum())
    simple = df[~df["doble_ciclo"].fillna(False)]
    print(f"Parcelas: {len(df)}")
    print("Calidad:", df["flag_calidad"].value_counts().to_dict())
    print(f"Parcelas con DOBLE CICLO: {n_dbl} ({100 * n_dbl / len(df):.0f} %)")
    if n_dbl:
        d = df[df["doble_ciclo"] == True]
        print("  Fecha del valle (mín, mediana, máx):", fechas_q_df(d, "fecha_valle", (0, .5, 1)))
        print(f"  NDVI del pico previo (mediana): {d['ndvi_pico_previo'].median():.2f} | "
              f"del valle: {d['ndvi_valle'].median():.2f} | del pico principal: {d['ndvi_pico'].median():.2f}")
        print("  Siembra escenario A, primer ciclo (mín, p10, mediana, p90, máx):",
              fechas_q_df(d, "fecha_siembra_A"))
        print("  Siembra escenario B, ciclo principal (mín, p10, mediana, p90, máx):",
              fechas_q_df(d, "fecha_siembra"))
    print("  Sensibilidad del conteo según la prominencia mínima del pico previo: "
          f"0.12 -> {int(df['doble_prom_12'].sum())} | {S['prominencia_pico_previo']:.2f} (actual) -> {n_dbl} "
          f"| 0.30 -> {int(df['doble_prom_30'].sum())} parcelas")
    print("\nSiembra estimada, TODAS las parcelas (mín, p10, mediana, p90, máx):", fechas_q("fecha_siembra"))
    print("Inicio de crecimiento SOS (mín, p10, mediana, p90, máx):", fechas_q("fecha_sos"))
    print("Pico de NDVI (mín, p10, mediana, p90, máx):", fechas_q("fecha_pico"))
    print(f"\n--- Verificación fisiológica, solo ciclo simple ({len(simple)} parcelas) ---")
    print("GDD siembra->pico (mín, p10, mediana, p90, máx):",
          simple["gdd_siembra_pico"].quantile([0, .1, .5, .9, 1]).round(0).astype(int).tolist())
    gdd_sos = simple["gdd_sos_pico"].median()
    objetivo = P["fenologia"]["gdd_antesis_objetivo"]
    print(f"GDD entre el inicio de crecimiento (SOS) y el pico: mediana {gdd_sos:.0f}. "
          f"Si el pico coincidiera con la antesis ({objetivo} °C·d desde la siembra), el desfase "
          f"siembra->SOS que lo haría cuadrar sería ~{objetivo - gdd_sos:.0f} °C·d (ahora: "
          f"{S['gdd_siembra_a_sos']}). Un valor negativo significa que esa hipótesis NO se sostiene.")
    print("Días siembra->pico (mín, p10, mediana, p90, máx):",
          simple["dias_siembra_pico"].quantile([0, .1, .5, .9, 1]).round(0).astype(int).tolist())

    base20 = pd.to_datetime(df["fecha_sos"])
    for pct in (10, 30):
        dif = (pd.to_datetime(df[f"fecha_sos_{pct}"]) - base20).dt.days
        print(f"Sensibilidad umbral {pct} % vs 20 % (días de diferencia en el SOS): "
              f"mediana {dif.median():+.0f}, p10 {dif.quantile(.1):+.0f}, p90 {dif.quantile(.9):+.0f}")

    if "Estado" in df.columns:
        df["_doy"] = pd.to_datetime(df["fecha_siembra"]).dt.dayofyear
        r = df.groupby("Estado").agg(parcelas=("ID_POLIGON", "size"), siembra_mediana_doy=("_doy", "median"))
        r["siembra_mediana"] = [(pd.Timestamp("2025-01-01") + pd.Timedelta(days=int(d) - 1)).strftime("%d-%b")
                                for d in r["siembra_mediana_doy"]]
        print("\nSiembra mediana por estado:\n", r[["parcelas", "siembra_mediana"]].to_string())

    try:
        import matplotlib
        matplotlib.use("Agg")
        import matplotlib.pyplot as plt
        con = df[df["flag_calidad"] != "sin_serie"]
        rng = np.random.default_rng(2)
        dob = con[con["doble_ciclo"] == True]["ID_POLIGON"].to_numpy()
        res = con[con["doble_ciclo"] != True]["ID_POLIGON"].to_numpy()
        n_d = min(5, len(dob))
        elegidas = list(rng.choice(dob, n_d, replace=False)) if n_d else []
        elegidas += list(rng.choice(res, min(12 - n_d, len(res)), replace=False))
        fig, ejes = plt.subplots(3, 4, figsize=(16, 9), sharey=True)
        for ax, pid in zip(ejes.ravel(), elegidas):
            s = ser[ser["ID_POLIGON"] == pid].set_index("fecha")["ndvi_planet"]
            f = con[con["ID_POLIGON"] == pid].iloc[0]
            ax.plot(s.index, s.values, color="tab:blue")
            ax.axvline(pd.Timestamp(f["fecha_sos"]), color="green", ls="-", label="inicio crecimiento")
            ax.axvline(pd.Timestamp(f["fecha_siembra"]), color="orange", ls="--", label="siembra est.")
            ax.axvline(pd.Timestamp(f["fecha_pico"]), color="red", ls=":", label="pico")
            if f.get("doble_ciclo") == True:
                ax.axvline(pd.Timestamp(f["fecha_siembra_A"]), color="gray", ls="--", label="siembra A (1.er ciclo)")
            ax.set_title(f"{pid}  ({f['flag_calidad']})", fontsize=9)
            ax.tick_params(axis="x", rotation=45)
        ejes[0, 0].legend(fontsize=7)
        fig.suptitle("NDVI de Planet y fechas estimadas")
        fig.tight_layout()
        os.makedirs(os.path.dirname(FIGURA), exist_ok=True)
        fig.savefig(FIGURA, dpi=100)
        print("\nFigura:", FIGURA)
    except ImportError:
        pass
    print("Guardado:", SALIDA)


if __name__ == "__main__":
    main()
