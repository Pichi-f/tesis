"""Construye data/dataset_entrenamiento_v3.csv.

Une el dataset sintético v2 con las publicaciones reales etiquetadas
a mano: las auditorías de X y los lotes data/etiquetado_*.csv. La evaluación externa
(data/evaluacion_x_externa.csv) NO se incluye: queda reservada como
conjunto de prueba que el modelo nunca ve.
"""

import csv
import re
from collections import Counter
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
DATA = BASE_DIR / "data"

RUTA_SINTETICO = DATA / "dataset_entrenamiento_v2.csv"
RUTAS_AUDITORIAS = [
    DATA / "auditoria_lote_ciudadano.csv",
    DATA / "auditoria_balanceo_v3.csv",
    DATA / "auditoria_extorsion_agresion_v3.csv",
]
RUTA_EXTERNA = DATA / "evaluacion_x_externa.csv"
RUTA_SALIDA = DATA / "dataset_entrenamiento_v3.csv"

CATEGORIAS = {"robo", "extorsion", "agresion", "otro", "ruido"}


def clave(texto):
    return re.sub(r"\W+", " ", texto.lower()).strip()


def leer(ruta, delimitador):
    with open(ruta, "r", encoding="utf-8-sig", newline="") as archivo:
        return list(csv.DictReader(archivo, delimiter=delimitador))


def construir():
    reservados = {clave(f["texto_original"]) for f in leer(RUTA_EXTERNA, ";")}
    vistos = set()
    filas = []

    def agregar(texto, categoria, origen, etiquetado_por="autor"):
        texto = " ".join(texto.split())
        categoria = categoria.strip().lower()
        llave = clave(texto)
        if not texto or categoria not in CATEGORIAS:
            return
        if llave in vistos or llave in reservados:
            return
        vistos.add(llave)
        filas.append({
            "texto": texto, "categoria": categoria,
            "origen": origen, "etiquetado_por": etiquetado_por,
        })

    for fila in leer(RUTA_SINTETICO, ","):
        agregar(fila["texto"], fila["categoria"], "sintetico")

    for ruta in RUTAS_AUDITORIAS:
        for fila in leer(ruta, ";"):
            agregar(fila["texto"], fila["categoria_real"], "real_x")

    # Lotes nuevos (exportar_para_etiquetar.py). La columna etiquetado_por
    # distingue las etiquetas del autor de las propuestas por el asistente.
    for ruta in sorted(DATA.glob("etiquetado_*.csv")):
        for fila in leer(ruta, ";"):
            origen = "real_fb" if fila.get("plataforma") == "Facebook" else "real_x"
            agregar(
                fila["texto"], fila["categoria_real"], origen,
                (fila.get("etiquetado_por") or "autor").strip(),
            )

    with open(RUTA_SALIDA, "w", encoding="utf-8", newline="") as archivo:
        escritor = csv.DictWriter(archivo, fieldnames=["texto", "categoria", "origen", "etiquetado_por"])
        escritor.writeheader()
        escritor.writerows(filas)

    print(f"Registros: {len(filas)}")
    print("Por origen:", dict(Counter(f["origen"] for f in filas)))
    print("Por categoría:", dict(Counter(f["categoria"] for f in filas)))
    print("Etiquetado por:", dict(Counter(f["etiquetado_por"] for f in filas)))
    print(f"Archivo: {RUTA_SALIDA}")


if __name__ == "__main__":
    construir()
