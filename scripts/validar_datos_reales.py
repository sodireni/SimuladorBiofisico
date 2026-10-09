"""Fase 1: validación de M1, M2 y M3 con los datos reales. Uso (desde la raíz del repositorio):

    python scripts/validar_datos_reales.py

Imprime un resumen con marcas [OK] / [REVISAR], guarda el mismo texto en docs/resumen_validacion.txt
y la figura de 3 parcelas (una por estado) en docs/fig_m3_parcelas.png. No modifica ningún dato."""
import argparse
import sys
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(RAIZ / "src"))

import numpy as np
import pandas as pd

from simulador.io import cargar_entrada, cargar_params
from simulador.m1_clima import m1_clima, razon_eto_mensual
from simulador.m2_fenologia import ciclos_incompletos, m2_fenologia
from simulador.m3_balance_hidrico import m3_balance_hidrico

LINEAS = []


def p(texto=""):
    print(texto)
    LINEAS.append(str(texto))


def marca(ok):
    return "[OK]     " if ok else "[REVISAR]"


def cuantiles(s, dec=1):
    q = s.quantile([0, 0.1, 0.5, 0.9, 1]).round(dec).tolist()
    return f"min {q[0]} | p10 {q[1]} | mediana {q[2]} | p90 {q[3]} | max {q[4]}"


def titulo(t):
    p("\n" + "=" * 78)
    p(t)
    p("=" * 78)


def paso2_carga(raiz, n_parc, n_dias):
    titulo("PASO 2-3. CARGA Y FORMA DE LOS DATOS")
    ruta_clima = raiz / "data/external/clima_diario_parcelas_2025.csv"
    cols = pd.read_csv(ruta_clima, nrows=0).columns.tolist()
    p(f"Columnas del CSV de clima: {cols}")
    if "fecha" not in cols:
        p(f"{marca(False)} el CSV de clima no tiene la columna 'fecha' (io.py la espera con ese nombre).")
        p("          Renombra la columna en el CSV (p. ej. 'date' -> 'fecha') o cambia io.py, y vuelve a correr.")
        sys.exit(1)
    diario, base = cargar_entrada(str(raiz))

    p(f"{marca(len(base) == n_parc)} parcelas en parcelas_base: {len(base)} (esperadas {n_parc})")
    por_parcela = diario.groupby("ID_POLIGON")["fecha"].agg(["count", "min", "max"])
    p(f"{marca(diario['ID_POLIGON'].nunique() == n_parc)} parcelas en el diario: {diario['ID_POLIGON'].nunique()}")
    p(f"{marca((por_parcela['count'] == n_dias).all())} días por parcela: min {por_parcela['count'].min()}, "
      f"max {por_parcela['count'].max()} (esperados {n_dias})")
    p(f"          rango de fechas: {diario['fecha'].min():%Y-%m-%d} a {diario['fecha'].max():%Y-%m-%d}")
    p(f"          filas totales: {len(diario):,} (esperadas {n_parc * n_dias:,})")
    if (por_parcela["count"] != n_dias).any():
        cortas = por_parcela[por_parcela["count"] != n_dias]
        p(f"          {len(cortas)} parcelas con días distintos; última fecha más común: "
          f"{por_parcela['max'].mode().iloc[0]:%Y-%m-%d} (si es 31-oct, el clima no llega al 30-nov)")

    criticas = ["tmax", "tmin", "pcp", "rs", "eto_om", "fapar_final", "FC_mm", "PWP_mm", "AWC_mm",
                "fecha_siembra", "fecha_pico"]
    nulos = diario[criticas].isna().sum()
    p(f"{marca(nulos.sum() == 0)} vacíos en columnas críticas: {int(nulos.sum())}")
    if nulos.sum():
        p(nulos[nulos > 0].to_string())
    return diario, base


def paso4_m1(diario, params):
    titulo("PASO 4. M1: CLIMA Y ETo")
    d = m1_clima(diario, params)
    p(f"{marca(d['eto'].between(0, 10).all())} eto (mm/día): {cuantiles(d['eto'], 2)}")
    p(f"          tmean (°C): {cuantiles(d['tmean'])}")
    p(f"          ra (MJ/m2/día): {cuantiles(d['ra'])}   par: {cuantiles(d['par'])}")
    r = razon_eto_mensual(d)
    p("\nCociente mensual ETo(Hargreaves) / ETo(Open-Meteo, Penman-Monteith):")
    p(r.round(3).to_string())
    total = d["eto"].sum() / d["eto_om"].sum()
    p(f"\nCociente global: {total:.3f}  -> {'cerca de 1: Hargreaves no está sesgada' if abs(total - 1) < 0.05 else 'se aleja de 1: hay que decidir clima.factor_eto (decisión abierta 3)'}")
    p(f"          si el cociente es ~0.90 se confirma la subestimación de ~10 % esperada; "
      f"factor sugerido = {1 / total:.2f} (SOLO una referencia: la decide el equipo)")
    return d


def paso5_m2(d_m1, params):
    titulo("PASO 5. M2: FENOLOGÍA (dos modos)")
    resultados = {}
    for modo in ["umbral_gdd", "satelite"]:
        pm = {**params, "fenologia": {**params["fenologia"], "modo": modo}}
        d = m2_fenologia(d_m1, pm)
        resultados[modo] = d
        u = d.drop_duplicates("ID_POLIGON").copy()
        inc = ciclos_incompletos(d)
        p(f"\n--- modo '{modo}' ---")
        p(f"{marca(not inc['madurez_incompleta'].any())} parcelas SIN madurez antes del 30-nov: "
          f"{int(inc['madurez_incompleta'].sum())} de {len(inc)}; sin antesis: {int(inc['antesis_incompleta'].sum())}")
        u["dias_sie_ant"] = (u["fecha_antesis"] - u["fecha_siembra"]).dt.days
        u["dias_sie_mad"] = (u["fecha_madurez"] - u["fecha_siembra"]).dt.days
        u["dif_antesis_vs_pico"] = (u["fecha_antesis"] - u["fecha_pico"]).dt.days
        p(f"          días siembra -> antesis : {cuantiles(u['dias_sie_ant'], 0)}")
        p(f"          días siembra -> madurez : {cuantiles(u['dias_sie_mad'], 0)}")
        p(f"          antesis menos pico de NDVI (días): {cuantiles(u['dif_antesis_vs_pico'], 0)}")
        p(f"          fecha_antesis mediana: {u['fecha_antesis'].median():%Y-%m-%d}; "
          f"fecha_madurez mediana: {u['fecha_madurez'].median():%Y-%m-%d}")
    # GDD entre siembra y pico de NDVI: el chequeo fisiológico del contrato (mediana ~1,224 °C·d con Tbase 0)
    d = resultados["umbral_gdd"]
    en_pico = d[d["fecha"] == d["fecha_pico"]].drop_duplicates("ID_POLIGON")
    p(f"\nGDD acumulados siembra -> pico de NDVI (Tbase {params['fenologia']['tbase_c']}): {cuantiles(en_pico['gdd_acum'], 0)}")
    p("          referencia del contrato: mediana ~1,224 °C·d con Tbase 0; los umbrales del prompt son 800 y 1,450.")
    return resultados


def paso6_m3(d_m2, params, raiz):
    titulo("PASO 6. M3: BALANCE HÍDRICO")
    d = m3_balance_hidrico(d_m2, params)
    nan = int(d[["sw", "ks", "eta"]].isna().sum().sum())
    p(f"{marca(nan == 0)} vacíos en sw/ks/eta: {nan}")
    p(f"{marca(d['ks'].between(0, 1).all())} ks entre 0 y 1")
    p(f"{marca(((d['sw'] >= d['PWP_mm'] - 1e-9) & (d['sw'] <= d['FC_mm'] + 1e-9)).all())} sw entre PWP y FC")
    p(f"{marca((d['eta'] <= d['eto'] * d['kc'] + 1e-9).all())} eta <= eto*kc")

    ciclo = d[d["estadio"].isin(["vegetativo", "antesis", "llenado"])]
    por = ciclo.groupby("ID_POLIGON").agg(ks_min=("ks", "min"), ks_medio=("ks", "mean"),
                                         dias_estres=("ks", lambda s: int((s < 1).sum())),
                                         eta=("eta", "sum"), eto=("eto", "sum"),
                                         etc=("kc", lambda s: 0.0))
    por["etc"] = (ciclo["eto"] * ciclo["kc"]).groupby(ciclo["ID_POLIGON"]).sum()
    por["eta_sobre_etc"] = por["eta"] / por["etc"]
    p("\nDurante el ciclo (siembra -> madurez), por parcela:")
    p(f"          ks mínimo        : {cuantiles(por['ks_min'], 2)}")
    p(f"          ks medio         : {cuantiles(por['ks_medio'], 2)}")
    p(f"          días con ks < 1  : {cuantiles(por['dias_estres'], 0)}")
    p(f"          ETo del ciclo mm : {cuantiles(por['eto'], 0)}")
    p(f"          ETa del ciclo mm : {cuantiles(por['eta'], 0)}")
    p(f"          ETa / ETc        : {cuantiles(por['eta_sobre_etc'], 2)}")
    todos_1 = (por["ks_min"] > 0.999).mean()
    p(f"{marca(0.0 < todos_1 < 1.0)} parcelas que NUNCA tienen estrés (ks mínimo = 1): {todos_1:.0%}  "
      f"(si es ~100 % o ~0 %, el modelo no discrimina entre parcelas: revisar)")
    p(f"          desviación estándar de ETa entre parcelas: {por['eta'].std():.1f} mm "
      f"(clima y suelo varían poco entre parcelas; esperable que sea pequeña)")

    try:
        import matplotlib
        matplotlib.use("Agg")
        import matplotlib.pyplot as plt
        elegidas = d.drop_duplicates("ID_POLIGON").groupby("Estado").head(1)["ID_POLIGON"].tolist()[:3]
        fig, ejes = plt.subplots(len(elegidas), 1, figsize=(11, 3.6 * len(elegidas)), sharex=True)
        ejes = np.atleast_1d(ejes)
        for ax, pid in zip(ejes, elegidas):
            g = d[d["ID_POLIGON"] == pid]
            ax.bar(g["fecha"], g["pcp"], color="#9ecae1", width=1.0, label="lluvia (mm/día)")
            ax.set_ylabel("mm/día")
            ax2 = ax.twinx()
            ax2.plot(g["fecha"], g["sw"], color="#08519c", label="sw (mm)")
            ax2.axhline(g["FC_mm"].iloc[0], color="gray", ls="--", lw=0.8)
            ax2.axhline(g["PWP_mm"].iloc[0], color="gray", ls=":", lw=0.8)
            ax2.plot(g["fecha"], g["ks"] * g["AWC_mm"].iloc[0] + g["PWP_mm"].iloc[0], color="#d94801", lw=1,
                     label="ks (escalado entre PWP y FC)")
            ax2.set_ylabel("sw (mm) / ks escalado")
            for etq, color in (("fecha_siembra", "green"), ("fecha_antesis", "purple"), ("fecha_madurez", "brown")):
                ax.axvline(g[etq].iloc[0], color=color, lw=1)
            ax.set_title(f"{pid} ({g['Estado'].iloc[0]})  |  líneas verticales: siembra, antesis, madurez")
            ax2.legend(loc="upper left", fontsize=7)
        ruta = raiz / "docs/fig_m3_parcelas.png"
        fig.tight_layout()
        fig.savefig(ruta, dpi=130)
        p(f"\n[OK]      figura guardada en {ruta.relative_to(raiz)} (parcelas: {', '.join(elegidas)})")
    except ImportError:
        p("\n[REVISAR] matplotlib no está instalado: pip install matplotlib, y vuelve a correr para obtener la figura")
    return d


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--parcelas", type=int, default=197)
    ap.add_argument("--dias", type=int, default=261)
    a = ap.parse_args()
    params = cargar_params(str(RAIZ))
    diario, base = paso2_carga(RAIZ, a.parcelas, a.dias)
    d1 = paso4_m1(diario, params)
    d2 = paso5_m2(d1, params)["umbral_gdd"]
    paso6_m3(d2, params, RAIZ)
    (RAIZ / "docs").mkdir(exist_ok=True)
    (RAIZ / "docs/resumen_validacion.txt").write_text("\n".join(LINEAS), encoding="utf-8")
    print("\nResumen guardado en docs/resumen_validacion.txt (pégamelo completo para revisarlo).")
