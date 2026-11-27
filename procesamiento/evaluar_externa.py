"""Evalúa el modelo vigente con publicaciones reales que nunca vio.

Usa data/evaluacion_x_externa.csv (publicaciones de X etiquetadas a
mano, excluidas del entrenamiento) y aplica el mismo criterio que el
pipeline: la categoría predicha se descarta como ruido si su score
queda por debajo del umbral de confianza.

Uso: python procesamiento/evaluar_externa.py
"""

import csv
import json
import sys
from pathlib import Path

from sklearn.metrics import accuracy_score, classification_report, confusion_matrix

from clasificar import cargar_modelos, clasificar_texto
from geolocalizar import buscar_ubicacion

sys.stdout.reconfigure(errors="replace")

BASE_DIR = Path(__file__).resolve().parent.parent
RUTA = BASE_DIR / "data" / "evaluacion_x_externa.csv"
RUTA_CONFIG = BASE_DIR / "config" / "configuracion.json"


def evaluar():
    with open(RUTA_CONFIG, "r", encoding="utf-8") as archivo:
        umbral = json.load(archivo)["umbral_confianza"]
    with open(RUTA, "r", encoding="utf-8-sig", newline="") as archivo:
        filas = list(csv.DictReader(archivo, delimiter=";"))

    vectorizador, modelo = cargar_modelos()
    reales, predichas, area_real, area_predicha = [], [], [], []

    for fila in filas:
        categoria, score, _ = clasificar_texto(fila["texto_original"], vectorizador, modelo)
        if score < umbral:
            categoria = "ruido"
        reales.append(fila["categoria_real"])
        predichas.append(categoria)

        area_real.append(fila["area_real"] == "dentro")
        area_predicha.append(buscar_ubicacion(fila["texto_original"]) is not None)

    etiquetas = sorted(set(reales) | set(predichas))
    print(f"Publicaciones evaluadas: {len(filas)} | umbral: {umbral}")
    print(f"\nCLASIFICACIÓN | accuracy = {accuracy_score(reales, predichas):.4f}")
    print(classification_report(reales, predichas, zero_division=0))
    print("Matriz de confusión (filas = real, columnas = predicho)")
    print(" " * 11 + "".join(f"{e[:9]:>10s}" for e in etiquetas))
    for etiqueta, fila in zip(etiquetas, confusion_matrix(reales, predichas, labels=etiquetas)):
        print(f"{etiqueta:11s}" + "".join(f"{valor:10d}" for valor in fila))

    es_incidente_real = [r != "ruido" for r in reales]
    es_incidente_pred = [p != "ruido" for p in predichas]
    print(
        "\nFILTRO DE RUIDO (incidente vs. ruido) | accuracy = "
        f"{accuracy_score(es_incidente_real, es_incidente_pred):.4f}"
    )

    aciertos = sum(r == p for r, p in zip(area_real, area_predicha))
    print(
        f"\nUBICACIÓN (dentro del área y localizable) | accuracy = "
        f"{aciertos / len(filas):.4f} | "
        f"reales dentro: {sum(area_real)} | ubicadas por el sistema: {sum(area_predicha)}"
    )


if __name__ == "__main__":
    evaluar()
