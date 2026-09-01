import sqlite3
from pathlib import Path


BASE_DIR = Path(__file__).resolve().parent.parent

DB_PATH = (
    BASE_DIR / "data" / "cifra_negra.db"
)


def consultar_indicios():

    conexion = sqlite3.connect(
        DB_PATH
    )

    conexion.row_factory = sqlite3.Row

    cursor = conexion.cursor()

    cursor.execute("""
        SELECT
            id_indicio,
            id_reporte,
            texto_procesado,
            categoria_delito,
            score_clasificacion,
            latitud,
            longitud,
            fecha_publicacion
        FROM indicio_procesado
        ORDER BY id_indicio
    """)

    indicios = cursor.fetchall()

    print(
        f"\nTotal de indicios: "
        f"{len(indicios)}\n"
    )

    for indicio in indicios:

        print("=" * 70)

        print(
            f"ID indicio: "
            f"{indicio['id_indicio']}"
        )

        print(
            f"ID reporte: "
            f"{indicio['id_reporte']}"
        )

        print(
            f"Texto procesado: "
            f"{indicio['texto_procesado']}"
        )

        print(
            f"Categoría: "
            f"{indicio['categoria_delito']}"
        )

        print(
            f"Score: "
            f"{indicio['score_clasificacion']:.4f}"
        )

        print(
            f"Latitud: "
            f"{indicio['latitud']}"
        )

        print(
            f"Longitud: "
            f"{indicio['longitud']}"
        )

        print(
            f"Fecha: "
            f"{indicio['fecha_publicacion']}"
        )

    print("=" * 70)

    conexion.close()


if __name__ == "__main__":
    consultar_indicios()