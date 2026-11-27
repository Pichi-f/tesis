"""Entrena el clasificador de incidentes y documenta su evaluación.

1. Compara Naive Bayes, Regresión Logística y SVM lineal con validación
   cruzada estratificada de 5 pliegues (RNF-PLN-01).
2. Entrena el modelo definitivo (SVM lineal calibrado sobre TF-IDF de
   n-gramas de caracteres) con todo el dataset.
3. Respalda el modelo anterior y actualiza modelos/metadata_modelo.json.

Uso: python procesamiento/entrenar_modelo.py
"""

import csv
import json
import shutil
import sys
import warnings
from collections import Counter
from datetime import datetime
from pathlib import Path

import joblib
import numpy as np
from sklearn.calibration import CalibratedClassifierCV
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import (
    accuracy_score,
    classification_report,
    confusion_matrix,
    precision_recall_fscore_support,
)
from sklearn.model_selection import StratifiedKFold, cross_val_predict
from sklearn.naive_bayes import MultinomialNB
from sklearn.pipeline import make_pipeline
from sklearn.svm import SVC

from clasificar import preparar_texto

sys.stdout.reconfigure(errors="replace")
warnings.filterwarnings("ignore", category=FutureWarning)

BASE_DIR = Path(__file__).resolve().parent.parent
RUTA_DATASET = BASE_DIR / "data" / "dataset_entrenamiento_v3.csv"
RUTA_MODELOS = BASE_DIR / "modelos"
RUTA_VECTORIZADOR = RUTA_MODELOS / "vectorizador.pkl"
RUTA_MODELO = RUTA_MODELOS / "clasificador.pkl"
RUTA_METADATA = RUTA_MODELOS / "metadata_modelo.json"
RUTA_CONFIG = BASE_DIR / "config" / "configuracion.json"

VERSION = "3.0"
SEMILLA = 42


def cargar_dataset():
    with open(RUTA_DATASET, "r", encoding="utf-8-sig", newline="") as archivo:
        filas = [f for f in csv.DictReader(archivo) if f["texto"].strip()]
    textos = [preparar_texto(f["texto"]) for f in filas]
    categorias = np.array([f["categoria"].strip().lower() for f in filas])
    origenes = np.array([f.get("origen", "") for f in filas])
    return textos, categorias, origenes


def crear_vectorizador():
    # N-gramas de caracteres: toleran faltas de ortografía, abreviaturas
    # y variantes de una misma palabra, habituales en redes sociales.
    return TfidfVectorizer(analyzer="char_wb", ngram_range=(2, 5), sublinear_tf=True)


def crear_svm():
    base = SVC(kernel="linear", class_weight="balanced", random_state=SEMILLA)
    return CalibratedClassifierCV(estimator=base, method="sigmoid", cv=3, ensemble=False)


CANDIDATOS = {
    "Naive Bayes multinomial": lambda: MultinomialNB(alpha=0.3),
    "Regresión logística": lambda: LogisticRegression(
        C=10, class_weight="balanced", max_iter=2000
    ),
    "SVM lineal calibrado": crear_svm,
}
ELEGIDO = "SVM lineal calibrado"


def metricas(reales, predichas):
    precision, recall, f1, _ = precision_recall_fscore_support(
        reales, predichas, average="macro", zero_division=0
    )
    return {
        "accuracy": round(float(accuracy_score(reales, predichas)), 4),
        "precision_macro": round(float(precision), 4),
        "recall_macro": round(float(recall), 4),
        "f1_macro": round(float(f1), 4),
    }


def comparar(textos, categorias, origenes):
    validacion = StratifiedKFold(n_splits=5, shuffle=True, random_state=SEMILLA)
    reales = np.char.startswith(origenes.astype(str), "real")
    resultados = {}

    print("\nVALIDACIÓN CRUZADA ESTRATIFICADA (5 pliegues)")
    print(f"{'Modelo':28s} {'Accuracy':>9s} {'F1 macro':>9s} {'Acc. texto real':>16s}")

    for nombre, fabrica in CANDIDATOS.items():
        modelo = make_pipeline(crear_vectorizador(), fabrica())
        predichas = cross_val_predict(modelo, textos, categorias, cv=validacion)
        resultados[nombre] = metricas(categorias, predichas)
        resultados[nombre]["accuracy_texto_real"] = round(
            float(accuracy_score(categorias[reales], predichas[reales])), 4
        )
        print(
            f"{nombre:28s} {resultados[nombre]['accuracy']:9.4f} "
            f"{resultados[nombre]['f1_macro']:9.4f} "
            f"{resultados[nombre]['accuracy_texto_real']:16.4f}"
        )
        if nombre == ELEGIDO:
            predichas_elegido = predichas

    etiquetas = sorted(set(categorias))
    print(f"\nDETALLE DEL MODELO ELEGIDO: {ELEGIDO}")
    print(classification_report(categorias, predichas_elegido, zero_division=0))
    print("Matriz de confusión (filas = real, columnas = predicho)")
    print(" " * 11 + "".join(f"{e[:9]:>10s}" for e in etiquetas))
    for etiqueta, fila in zip(
        etiquetas, confusion_matrix(categorias, predichas_elegido, labels=etiquetas)
    ):
        print(f"{etiqueta:11s}" + "".join(f"{valor:10d}" for valor in fila))

    return resultados


def respaldar_modelo_anterior():
    destino = RUTA_MODELOS / "backups"
    destino.mkdir(parents=True, exist_ok=True)
    marca = datetime.now().strftime("%Y%m%d_%H%M%S")
    for ruta in (RUTA_VECTORIZADOR, RUTA_MODELO):
        if ruta.exists():
            shutil.copy2(ruta, destino / f"{ruta.stem}_{marca}.pkl")


def entrenar():
    print(f"Dataset: {RUTA_DATASET.name}")
    textos, categorias, origenes = cargar_dataset()
    with open(RUTA_DATASET, "r", encoding="utf-8-sig", newline="") as archivo:
        etiquetadores = [
            f.get("etiquetado_por") or "autor"
            for f in csv.DictReader(archivo) if f["texto"].strip()
        ]
    print(f"Registros: {len(textos)} | por origen: {dict(Counter(map(str, origenes)))}")
    print(f"Por categoría: {dict(Counter(map(str, categorias)))}")

    resultados = comparar(textos, categorias, origenes)

    vectorizador = crear_vectorizador()
    modelo = crear_svm()
    modelo.fit(vectorizador.fit_transform(textos), categorias)

    respaldar_modelo_anterior()
    RUTA_MODELOS.mkdir(parents=True, exist_ok=True)
    joblib.dump(vectorizador, RUTA_VECTORIZADOR)
    joblib.dump(modelo, RUTA_MODELO)

    with open(RUTA_CONFIG, "r", encoding="utf-8") as archivo:
        umbral = json.load(archivo)["umbral_confianza"]

    metadata = {
        "version": VERSION,
        "fecha_entrenamiento": datetime.now().strftime("%Y-%m-%d"),
        "algoritmo": ELEGIDO,
        "calibracion": "sigmoid",
        "representacion": "TF-IDF de n-gramas de caracteres (char_wb)",
        "ngram_range": [2, 5],
        "dataset": RUTA_DATASET.name,
        "cantidad_registros": len(textos),
        "registros_por_origen": dict(Counter(map(str, origenes))),
        "registros_por_etiquetador": dict(Counter(etiquetadores)),
        "categorias": sorted(set(categorias)),
        "validacion": "Stratified 5-fold cross-validation",
        "resultados_cv": resultados,
        "umbral_operativo_actual": umbral,
    }
    with open(RUTA_METADATA, "w", encoding="utf-8") as archivo:
        json.dump(metadata, archivo, ensure_ascii=False, indent=4)

    print(f"\nModelo {VERSION} guardado en {RUTA_MODELOS}")


if __name__ == "__main__":
    entrenar()
