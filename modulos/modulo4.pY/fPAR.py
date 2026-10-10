"""Visualización interactiva de la serie temporal de fPAR.

El archivo puede ejecutarse desde cualquier carpeta: localiza por sí mismo
``data/processed/Datos para fpar.csv`` y abre la gráfica en una ventana.
"""

import csv
from datetime import datetime
from pathlib import Path
import tkinter as tk


RAIZ_PROYECTO = Path(__file__).resolve().parents[2]
RUTA_CSV = RAIZ_PROYECTO / "data" / "processed" / "Datos para fpar.csv"


def leer_fpar(ruta_csv: Path = RUTA_CSV) -> tuple[list[datetime], list[float]]:
    """Carga las fechas y la serie fPAR, interpolando huecos internos."""
    if not ruta_csv.is_file():
        raise FileNotFoundError(f"No se encontró el archivo de fPAR: {ruta_csv}")

    fechas: list[datetime] = []
    valores: list[float | None] = []
    with ruta_csv.open("r", encoding="utf-8-sig", newline="") as archivo:
        lector = csv.DictReader(archivo)
        requeridas = {"fecha_captura", "fapar_promedio"}
        if lector.fieldnames is None or not requeridas.issubset(lector.fieldnames):
            disponibles = [] if lector.fieldnames is None else lector.fieldnames
            raise ValueError(
                "El CSV debe incluir fecha_captura y fapar_promedio. "
                f"Columnas encontradas: {disponibles}"
            )

        for fila, registro in enumerate(lector, start=2):
            try:
                fecha = datetime.strptime(registro["fecha_captura"].strip(), "%d/%m/%Y")
            except (AttributeError, ValueError) as error:
                raise ValueError(f"Fecha inválida en la fila {fila}.") from error

            texto_valor = (registro["fapar_promedio"] or "").strip()
            try:
                valor = None if texto_valor == "" else float(texto_valor)
            except ValueError as error:
                raise ValueError(f"fPAR inválido en la fila {fila}: {texto_valor!r}") from error
            fechas.append(fecha)
            valores.append(valor)

    if not fechas:
        raise ValueError("El CSV de fPAR no tiene datos.")
    orden = sorted(zip(fechas, valores), key=lambda par: par[0])
    fechas, valores = map(list, zip(*orden))
    return fechas, interpolar_huecos(valores)


def interpolar_huecos(valores: list[float | None]) -> list[float]:
    """Replica la interpolación lineal; los huecos de los extremos se vuelven 0."""
    resultado = valores[:]
    indices_validos = [indice for indice, valor in enumerate(resultado) if valor is not None]
    if not indices_validos:
        return [0.0] * len(resultado)

    primero, ultimo = indices_validos[0], indices_validos[-1]
    for indice in range(0, primero):
        resultado[indice] = 0.0
    for indice in range(ultimo + 1, len(resultado)):
        resultado[indice] = 0.0

    izquierda = primero
    for derecha in indices_validos[1:]:
        inicio, fin = resultado[izquierda], resultado[derecha]
        for indice in range(izquierda + 1, derecha):
            proporcion = (indice - izquierda) / (derecha - izquierda)
            resultado[indice] = float(inicio) + proporcion * (float(fin) - float(inicio))
        izquierda = derecha

    return [max(0.0, min(1.0, float(valor))) for valor in resultado]


def mostrar_grafica(fechas: list[datetime], valores: list[float]) -> None:
    """Abre una ventana con la evolución temporal de fPAR."""
    ancho, alto = 1100, 620
    margen_izq, margen_der, margen_sup, margen_inf = 85, 35, 60, 105
    area_ancho = ancho - margen_izq - margen_der
    area_alto = alto - margen_sup - margen_inf

    ventana = tk.Tk()
    ventana.title("Evolución Temporal del fPAR Promedio - Reto FIRA")
    lienzo = tk.Canvas(ventana, width=ancho, height=alto, bg="white", highlightthickness=0)
    lienzo.pack()

    # Ejes y cuadrícula vertical de fPAR (0--1).
    lienzo.create_line(margen_izq, margen_sup, margen_izq, alto - margen_inf, width=2)
    lienzo.create_line(margen_izq, alto - margen_inf, ancho - margen_der, alto - margen_inf, width=2)
    for marca in range(6):
        valor = marca / 5
        y = alto - margen_inf - valor * area_alto
        lienzo.create_line(margen_izq, y, ancho - margen_der, y, fill="#d9d9d9", dash=(3, 3))
        lienzo.create_text(margen_izq - 14, y, text=f"{valor:.1f}", font=("Arial", 9))

    total = max(len(valores) - 1, 1)
    puntos = []
    for indice, valor in enumerate(valores):
        x = margen_izq + indice / total * area_ancho
        y = alto - margen_inf - valor * area_alto
        puntos.extend((x, y))
    lienzo.create_line(*puntos, fill="#27ae60", width=2, smooth=True)
    for indice in range(0, len(valores), max(1, len(valores) // 100)):
        x, y = puntos[2 * indice], puntos[2 * indice + 1]
        lienzo.create_oval(x - 1.5, y - 1.5, x + 1.5, y + 1.5, fill="#27ae60", outline="")

    # Etiquetas temporales repartidas en el eje X.
    for indice in range(6):
        posicion = round(indice * total / 5)
        x = margen_izq + posicion / total * area_ancho
        lienzo.create_line(x, alto - margen_inf, x, alto - margen_inf + 5)
        etiqueta = fechas[posicion].strftime("%d/%m/%Y")
        lienzo.create_text(x, alto - margen_inf + 42, text=etiqueta, angle=35, font=("Arial", 9))

    lienzo.create_text(ancho / 2, 24, text="Evolución Temporal del fPAR Promedio - Reto FIRA", font=("Arial", 14, "bold"))
    lienzo.create_text(ancho / 2, alto - 22, text="Fecha de captura", font=("Arial", 10))
    lienzo.create_text(22, alto / 2, text="fPAR promedio", angle=90, font=("Arial", 10))
    ventana.mainloop()


def main() -> None:
    fechas, valores = leer_fpar()
    print(f"Archivo cargado con éxito: {RUTA_CSV}")
    print(f"Registros graficados: {len(valores)}")
    mostrar_grafica(fechas, valores)


if __name__ == "__main__":
    main()
