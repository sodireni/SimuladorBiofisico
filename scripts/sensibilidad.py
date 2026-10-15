"""Análisis de sensibilidad del simulador biofísico. Uso (desde la raíz del repositorio):

    python scripts/sensibilidad.py

Corre el caso base y 15 escenarios, cada uno cambiando UN solo supuesto. Para cada escenario compara las
12 variables (más Deficit_ETc) contra el caso base y escribe:
    docs/SENSIBILIDAD.md                                          tablas listas para revisar
    data/processed/sensibilidad_resumen.csv                       una fila por escenario y variable
    data/processed/simulacion_sensibilidad_por_parcela.csv        valores por parcela y escenario (no se sube a git)

No usa el rendimiento. No modifica configs/params.yaml ni ningún dato de entrada.
"""
import copy
import sys
import time
from datetime import date
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(RAIZ / "src"))

import numpy as np
import pandas as pd

from simulador.io import cargar_entrada, cargar_params
from simulador.m1_clima import m1_clima
from simulador.m2_fenologia import m2_fenologia
from simulador.m3_balance_hidrico import m3_balance_hidrico
from simulador.m4_lue import m4_lue
from simulador.variables import VARIABLES_12, calcular_variables

VARS = VARIABLES_12 + ["Deficit_ETc"]
CLAVE = ["ETa_acum", "KS_prom_llenado", "Biomasa_Total_Sim", "HI_penalizado",
         "GDD_antesis", "GDD_llenado", "DAP_antesis_est"]
UMBRAL_MAGNITUD_PCT = 10.0     # criterio de lectura: cambio mediano por parcela >= 10 %
UMBRAL_RHO = 0.90              # criterio de lectura: correlación de Spearman con el caso base < 0.90


# ----------------------------------------------------------------------------
# Escenarios
# ----------------------------------------------------------------------------
def _siembra_fija(d):
    d = d.copy()
    d["fecha_siembra"] = pd.Timestamp("2025-05-05")
    return d


def _doble_ciclo_b(d):
    d = d.copy()
    m = d["doble_ciclo"].astype(bool)
    d.loc[m, "fecha_siembra"] = d.loc[m, "fecha_siembra_B"]
    return d


def _awc_sin_grava(d):
    """Agua disponible sin la corrección por fragmentos gruesos: conserva PWP y sube FC para que AWC = AWC_mm_sin_grava."""
    d = d.copy()
    d["AWC_mm"] = d["AWC_mm_sin_grava"]
    d["FC_mm"] = d["PWP_mm"] + d["AWC_mm_sin_grava"]
    return d


ESCENARIOS = [
    dict(id="eto_1.09", grupo="M1 clima", etiqueta="ETo con factor 1.09 (base 1.0)",
         params={"clima.factor_eto": 1.09}),
    dict(id="tbase_2", grupo="M2 fenología", etiqueta="Tbase 2 °C (base 0 °C)",
         params={"fenologia.tbase_c": 2.0}),
    dict(id="modo_satelite", grupo="M2 fenología",
         etiqueta="Modo satelital (antesis = pico de NDVI; madurez = fPAR a la mitad del pico)",
         params={"fenologia.modo": "satelite"}),
    dict(id="siembra_5may", grupo="Siembra", etiqueta="Siembra fija el 5-may en las 197 parcelas",
         diario=_siembra_fija),
    dict(id="doble_B", grupo="Siembra", etiqueta="Doble ciclo: escenario B (siembra del ciclo principal)",
         diario=_doble_ciclo_b),
    dict(id="sw0_0.3", grupo="M3 balance hídrico", etiqueta="Agua inicial 0.3·AWC (base 0.5)",
         params={"suelo.sw_inicial_frac_awc": 0.3}),
    dict(id="sw0_0.8", grupo="M3 balance hídrico", etiqueta="Agua inicial 0.8·AWC (base 0.5)",
         params={"suelo.sw_inicial_frac_awc": 0.8}),
    dict(id="awc_sin_grava", grupo="M3 balance hídrico", etiqueta="AWC sin corrección por grava",
         diario=_awc_sin_grava),
    dict(id="rue_1.2", grupo="M4 biomasa", etiqueta="RUE 1.2 g/MJ (base 2.5)",
         params={"cultivo.rue_max_g_mj_par": 1.2}),
    dict(id="rue_2.6", grupo="M4 biomasa", etiqueta="RUE 2.6 g/MJ (base 2.5)",
         params={"cultivo.rue_max_g_mj_par": 2.6}),
    dict(id="hi_A_0.3", grupo="M4 índice de cosecha", etiqueta="HI opción A (lineal), hi_beta 0.3",
         params={"lue.hi_opcion": "A", "lue.hi_beta": 0.3}),
    dict(id="hi_A_0.5", grupo="M4 índice de cosecha", etiqueta="HI opción A (lineal), hi_beta 0.5",
         params={"lue.hi_opcion": "A", "lue.hi_beta": 0.5}),
    dict(id="hi_A_0.7", grupo="M4 índice de cosecha", etiqueta="HI opción A (lineal), hi_beta 0.7",
         params={"lue.hi_opcion": "A", "lue.hi_beta": 0.7}),
    dict(id="hi_B", grupo="M4 índice de cosecha", etiqueta="HI opción B (Kemanian et al., 2007)",
         params={"lue.hi_opcion": "B"}),
    dict(id="gdd_ref_antesis", grupo="Variables GDD",
         etiqueta="GDD con la antesis por umbral (definición de la guía)",
         params={"fenologia.gdd_variables_ref": "antesis"}),
    dict(id="gdd_ref_madurez_modelo", grupo="Variables GDD",
         etiqueta="GDD_llenado del pico a la madurez del modo activo (versión descartada)",
         params={"fenologia.gdd_variables_ref": "pico_ndvi_hasta_madurez_modelo"}),
]
ORDEN_GRUPOS = ["M1 clima", "M2 fenología", "Siembra", "M3 balance hídrico", "M4 biomasa",
                "M4 índice de cosecha", "Variables GDD"]


def _con_params(params, cambios):
    p = copy.deepcopy(params)
    for ruta, valor in (cambios or {}).items():
        seccion, clave = ruta.split(".")
        p.setdefault(seccion, {})[clave] = valor
    return p


def correr(diario, params):
    """M1 -> M2 -> M3 -> M4 -> 12 variables. Devuelve un DataFrame indexado por ID_POLIGON."""
    df = m4_lue(m3_balance_hidrico(m2_fenologia(m1_clima(diario, params), params), params), params)
    return calcular_variables(df, None, params).set_index("ID_POLIGON")


# ----------------------------------------------------------------------------
# Comparación contra el caso base
# ----------------------------------------------------------------------------
def comparar(base, esc):
    filas = []
    for v in VARS:
        b, e = base[v].astype(float), esc[v].astype(float)
        ok = b.notna() & e.notna()
        d = (e - b)[ok]
        rel = (d / b[ok].abs()).replace([np.inf, -np.inf], np.nan).dropna()
        hay_rho = ok.sum() > 2 and b[ok].nunique() > 1 and e[ok].nunique() > 1
        filas.append(dict(
            variable=v,
            mediana_base=b.median(), mediana_esc=e.median(),
            cambio_mediano_abs=d.median() if len(d) else np.nan,
            cambio_mediano_pct=100 * rel.median() if len(rel) else np.nan,
            rho=b[ok].corr(e[ok], method="spearman") if hay_rho else np.nan,
            sin_cambio=bool(len(d) and (d.abs() < 1e-9).all()),
            n_sin_valor=int((~ok).sum()),
        ))
    return pd.DataFrame(filas).set_index("variable")


def conteos(res):
    return dict(
        ciclo_incompleto=int(res["ciclo_incompleto"].sum()),
        caida_no_alcanzada=int(res["caida_fpar_no_alcanzada"].sum()),
        gdd_llenado_cero=int((res["GDD_llenado"] == 0).sum()),
    )


def celda(fila):
    if fila["sin_cambio"]:
        return "sin cambio"
    rho = "n/d" if np.isnan(fila["rho"]) else f"{fila['rho']:.2f}"
    pct = "n/d" if np.isnan(fila["cambio_mediano_pct"]) else f"{fila['cambio_mediano_pct']:+.1f} %"
    return f"{pct} (ρ {rho})"


def marcas(fila):
    """Qué cambia en una variable: magnitud, orden entre parcelas, o ambos."""
    if fila["sin_cambio"]:
        return None
    mag = (not np.isnan(fila["cambio_mediano_pct"])) and abs(fila["cambio_mediano_pct"]) >= UMBRAL_MAGNITUD_PCT
    orden = (not np.isnan(fila["rho"])) and fila["rho"] < UMBRAL_RHO
    if mag and orden:
        return "cambia la magnitud y el orden entre parcelas"
    if mag:
        return "cambia la magnitud"
    if orden:
        return "cambia el orden entre parcelas"
    return None


# ----------------------------------------------------------------------------
# Ejecución
# ----------------------------------------------------------------------------
def verificar_base(params):
    esperado = {
        ("fenologia", "tbase_c"): 0.0, ("fenologia", "modo"): "umbral_gdd",
        ("fenologia", "gdd_variables_ref"): "pico_ndvi", ("clima", "factor_eto"): 1.0,
        ("suelo", "sw_inicial_frac_awc"): 0.5, ("cultivo", "rue_max_g_mj_par"): 2.5,
        ("lue", "hi_opcion"): "C",
    }
    avisos = []
    for (sec, clave), valor in esperado.items():
        real = params.get(sec, {}).get(clave)
        if real != valor:
            avisos.append(f"{sec}.{clave} = {real!r} (el caso base documentado usa {valor!r})")
    return avisos


def main():
    t0 = time.time()
    params = cargar_params(str(RAIZ))
    diario, _ = cargar_entrada(str(RAIZ))
    n_parc = diario["ID_POLIGON"].nunique()
    print(f"Datos cargados: {n_parc} parcelas, {len(diario):,} filas")
    for a in verificar_base(params):
        print(f"[AVISO] {a}")

    base = correr(diario, params)
    print(f"Caso base listo ({time.time() - t0:.0f} s)")
    resultados, filas_csv, por_parcela, cnt = {}, [], [base.assign(escenario="base")], {"base": conteos(base)}
    afectadas = {}

    for esc in ESCENARIOS:
        d_esc = esc["diario"](diario) if "diario" in esc else diario
        if "diario" in esc:
            afectadas[esc["id"]] = int((d_esc["fecha_siembra"] != diario["fecha_siembra"]).groupby(
                diario["ID_POLIGON"]).any().sum()) if "siembra" in esc["id"] or "doble" in esc["id"] else None
        res = correr(d_esc, _con_params(params, esc.get("params")))
        comp = comparar(base, res)
        resultados[esc["id"]] = comp
        cnt[esc["id"]] = conteos(res)
        por_parcela.append(res.assign(escenario=esc["id"]))
        for v, r in comp.iterrows():
            filas_csv.append(dict(escenario=esc["id"], grupo=esc["grupo"], etiqueta=esc["etiqueta"], variable=v,
                                  mediana_base=r["mediana_base"], mediana_esc=r["mediana_esc"],
                                  cambio_mediano_abs=r["cambio_mediano_abs"], cambio_mediano_pct=r["cambio_mediano_pct"],
                                  rho_spearman=r["rho"], n_sin_valor=r["n_sin_valor"]))
        print(f"  [{esc['id']:<24}] listo ({time.time() - t0:.0f} s)")

    # --- archivos de datos ---
    proc = RAIZ / "data/processed"
    proc.mkdir(parents=True, exist_ok=True)
    pd.DataFrame(filas_csv).to_csv(proc / "sensibilidad_resumen.csv", index=False, float_format="%.6g")
    pd.concat(por_parcela).reset_index().to_csv(proc / "simulacion_sensibilidad_por_parcela.csv",
                                                index=False, float_format="%.6g")

    # --- markdown ---
    L = []
    L.append("# Análisis de sensibilidad\n")
    L.append(f"Generado el {date.today():%Y-%m-%d} con `scripts/sensibilidad.py` sobre {n_parc} parcelas. "
             "Cada escenario cambia un solo supuesto y deja los demás en el caso base. No se usó el rendimiento.\n")
    L.append("## Cómo leer las tablas\n")
    L.append("- Cada celda muestra el **cambio mediano por parcela** respecto al caso base, en %, y entre paréntesis la "
             "**correlación de Spearman (ρ)** entre los valores del escenario y los del caso base.")
    L.append("- ρ cercano a 1 significa que el **orden entre parcelas casi no cambia**, que es lo que le importa a un modelo "
             "de aprendizaje; un cambio grande de magnitud con ρ cercano a 1 solo cambia la escala.")
    L.append(f"- \"sin cambio\" significa que la variable no se movió en ninguna parcela. \"n/d\" significa que la variable "
             "quedó constante y ρ no se puede calcular.")
    L.append(f"- Criterio de lectura (arbitrario, solo para señalar casos): magnitud ≥ {UMBRAL_MAGNITUD_PCT:.0f} % o "
             f"ρ < {UMBRAL_RHO:.2f}.\n")

    L.append("## Caso base\n")
    L.append("| Variable | Mínimo | Mediana | Máximo |")
    L.append("| --- | --- | --- | --- |")
    for v in VARS:
        s = base[v].astype(float)
        L.append(f"| {v} | {s.min():,.2f} | {s.median():,.2f} | {s.max():,.2f} |")
    cb = cnt["base"]
    L.append(f"\nCiclos sin madurez antes del 30-nov: {cb['ciclo_incompleto']}. Parcelas donde el fPAR no cae a la mitad "
             f"del pico: {cb['caida_no_alcanzada']}. Parcelas con GDD_llenado = 0: {cb['gdd_llenado_cero']}.\n")

    L.append("## Resultados por escenario\n")
    for g in ORDEN_GRUPOS:
        escs = [e for e in ESCENARIOS if e["grupo"] == g]
        if not escs:
            continue
        L.append(f"### {g}\n")
        L.append("| Escenario | " + " | ".join(CLAVE) + " | Ciclos incompletos | GDD_llenado = 0 |")
        L.append("| --- | " + " | ".join(["---"] * len(CLAVE)) + " | --- | --- |")
        for e in escs:
            comp = resultados[e["id"]]
            c = cnt[e["id"]]
            nota = ""
            if afectadas.get(e["id"]) is not None:
                nota = f" ({afectadas[e['id']]} parcelas cambian de fecha)"
            L.append(f"| {e['etiqueta']}{nota} | " + " | ".join(celda(comp.loc[v]) for v in CLAVE)
                     + f" | {c['ciclo_incompleto']} | {c['gdd_llenado_cero']} |")
        L.append("")

    L.append("## Lectura automática\n")
    L.append("Solo se listan los escenarios y variables que superan el criterio de lectura. "
             "Las conclusiones para el reporte las redacta el equipo.\n")
    hubo = False
    for e in ESCENARIOS:
        comp = resultados[e["id"]]
        notas = [(v, marcas(comp.loc[v])) for v in CLAVE if marcas(comp.loc[v])]
        if notas:
            hubo = True
            L.append(f"- **{e['etiqueta']}**: " + "; ".join(f"{v} {m}" for v, m in notas) + ".")
    if not hubo:
        L.append("- Ningún escenario supera el criterio de lectura en las variables clave.")
    L.append("")

    L.append("## Parámetros del caso base\n")
    L.append("| Parámetro | Valor |")
    L.append("| --- | --- |")
    for sec, clave in [("fenologia", "tbase_c"), ("fenologia", "modo"), ("fenologia", "gdd_variables_ref"),
                       ("clima", "factor_eto"), ("suelo", "sw_inicial_frac_awc"), ("cultivo", "p_agotamiento"),
                       ("cultivo", "rue_max_g_mj_par"), ("cultivo", "hi_base"), ("lue", "hi_opcion"),
                       ("lue", "hi_sens_antesis"), ("lue", "hi_sens_llenado")]:
        L.append(f"| {sec}.{clave} | {params.get(sec, {}).get(clave)} |")
    L.append("\nDetalle de todas las variables y escenarios: `data/processed/sensibilidad_resumen.csv`.")
    (RAIZ / "docs").mkdir(exist_ok=True)
    (RAIZ / "docs/SENSIBILIDAD.md").write_text("\n".join(L) + "\n", encoding="utf-8")

    print("\nListo.")
    print("  docs/SENSIBILIDAD.md")
    print("  data/processed/sensibilidad_resumen.csv")
    print("  data/processed/simulacion_sensibilidad_por_parcela.csv (no subir a git)")
    print(f"Tiempo total: {time.time() - t0:.0f} s")


if __name__ == "__main__":
    main()
