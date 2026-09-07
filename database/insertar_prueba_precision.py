import sqlite3
from pathlib import Path


BASE_DIR = Path(__file__).resolve().parent.parent
DB_PATH = BASE_DIR / "data" / "cifra_negra.db"


def insertar_prueba():

    conexion = sqlite3.connect(DB_PATH)

    cursor = conexion.cursor()

    try:

        cursor.execute("""
            INSERT INTO reporte_crudo (
                id_publicacion_plataforma,
                plataforma,
                usuario_publico,
                texto_crudo,
                url_publicacion,
                referencia_espacial,
                fecha_publicacion
            )
            VALUES (?, ?, ?, ?, ?, ?, ?)
        """, (
            "x_006",
            "X",
            "@reporte_prueba",
            (
                "Me asaltaron en la Calzada Roosevelt zona 7. "
                "Me quitaron el teléfono."
            ),
            "https://x.com/prueba/006",
            None,
            "2026-08-16 14:30:00"
        ))

        conexion.commit()

        print(
            "Reporte de prueba insertado correctamente."
        )

    except sqlite3.IntegrityError:

        print(
            "El reporte de prueba ya existe."
        )

    finally:

        conexion.close()


if __name__ == "__main__":
    insertar_prueba()