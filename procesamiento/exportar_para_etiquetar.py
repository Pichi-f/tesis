"""Exporta a CSV los reportes de la base que aún no tienen etiqueta manual.

Uso: python procesamiento/exportar_para_etiquetar.py

Genera data/etiquetado_AAAAMMDD_HHMM.csv (separado por punto y coma, se abre
en Excel). El autor llena dos columnas por fila:

- categoria_real: robo | extorsion | agresion | otro | ruido
- area_real:      dentro | fuera | no_determinada

Un reporte ya está etiquetado si su id aparece en cualquier
auditoria_*.csv, etiquetado_*.csv o en la evaluación externa.
crear_dataset_v3.py incorpora después los etiquetado_*.csv al
entrenamiento.
"""

import csv
import sqlite3
import sys
from datetime import datetime
from pathlib import Path

from clasificar import cargar_modelos, clasificar_texto

sys.stdout.reconfigure(errors="replace")

BASE_DIR = Path(__file__).resolve().parent.parent
DATA = BASE_DIR / "data"
DB_PATH = DATA / "cifra_negra.db"

COLUMNAS = [
    "id_reporte",
    "plataforma",
    "id_publicacion",
    "fecha",
    "texto",
    "url",
    "sugerencia_modelo",
    "categoria_real",
    "area_real",
    "observacion",
]


def ids_etiquetados():
    archivos = (
        list(DATA.glob("auditoria_*.csv"))
        + list(DATA.glob("etiquetado_*.csv"))
        + [DATA / "evaluacion_x_externa.csv"]
    )
    ids = set()
    for ruta in archivos:
        with open(ruta, "r", encoding="utf-8-sig", newline="") as archivo:
            for fila in csv.DictReader(archivo, delimiter=";"):
                ids.add(fila.get("id_publicacion") or fila.get("id_x"))
    return ids


def exportar():
    etiquetados = ids_etiquetados()
    conexion = sqlite3.connect(DB_PATH)
    reportes = [
        fila
        for fila in conexion.execute(
            """
            SELECT id_reporte, plataforma, id_publicacion_plataforma,
                   fecha_publicacion, texto_crudo, url_publicacion
            FROM reporte_crudo
            ORDER BY id_reporte
            """
        )
        if fila[2] not in etiquetados
    ]
    conexion.close()

    if not reportes:
        print("No hay reportes nuevos por etiquetar.")
        return

    vectorizador, modelo = cargar_modelos()
    salida = DATA / f"etiquetado_{datetime.now():%Y%m%d_%H%M}.csv"

    with open(salida, "w", encoding="utf-8-sig", newline="") as archivo:
        escritor = csv.DictWriter(archivo, fieldnames=COLUMNAS, delimiter=";")
        escritor.writeheader()
        for id_reporte, plataforma, id_pub, fecha, texto, url in reportes:
            categoria, score, _ = clasificar_texto(texto, vectorizador, modelo)
            escritor.writerow(
                {
                    "id_reporte": id_reporte,
                    "plataforma": plataforma,
                    "id_publicacion": id_pub,
                    "fecha": fecha,
                    "texto": " ".join(texto.split()),
                    "url": url,
                    "sugerencia_modelo": f"{categoria} ({score:.0%})",
                    "categoria_real": "",
                    "area_real": "",
                    "observacion": "",
                }
            )

    print(f"Reportes por etiquetar: {len(reportes)}")
    print(f"Archivo: {salida}")


if __name__ == "__main__":
    exportar()
