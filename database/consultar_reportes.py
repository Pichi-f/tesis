import sqlite3
from pathlib import Path


BASE_DIR = Path(__file__).resolve().parent.parent
DB_PATH = BASE_DIR / "data" / "cifra_negra.db"


def consultar_reportes():

    conexion = sqlite3.connect(DB_PATH)

    # Permite acceder a las columnas por su nombre
    conexion.row_factory = sqlite3.Row

    cursor = conexion.cursor()

    cursor.execute("""
        SELECT
            id_reporte,
            id_publicacion_plataforma,
            plataforma,
            usuario_publico,
            texto_crudo,
            referencia_espacial,
            fecha_publicacion,
            fecha_extraccion,
            estado_procesamiento
        FROM reporte_crudo
        ORDER BY id_reporte
    """)

    reportes = cursor.fetchall()

    print(f"\nTotal de reportes: {len(reportes)}\n")

    for reporte in reportes:

        print("=" * 70)

        print(f"ID interno: {reporte['id_reporte']}")
        print(
            f"ID plataforma: "
            f"{reporte['id_publicacion_plataforma']}"
        )
        print(f"Plataforma: {reporte['plataforma']}")
        print(f"Usuario: {reporte['usuario_publico']}")
        print(f"Texto: {reporte['texto_crudo']}")
        print(
            f"Referencia espacial: "
            f"{reporte['referencia_espacial']}"
        )
        print(
            f"Fecha publicación: "
            f"{reporte['fecha_publicacion']}"
        )
        print(
            f"Fecha extracción: "
            f"{reporte['fecha_extraccion']}"
        )
        print(
            f"Estado: "
            f"{reporte['estado_procesamiento']}"
        )

    print("=" * 70)

    conexion.close()


if __name__ == "__main__":
    consultar_reportes()