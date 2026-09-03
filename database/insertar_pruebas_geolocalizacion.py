import sqlite3
from pathlib import Path


BASE_DIR = Path(__file__).resolve().parent.parent

DB_PATH = (
    BASE_DIR / "data" / "cifra_negra.db"
)


def insertar_pruebas():

    conexion = sqlite3.connect(DB_PATH)

    cursor = conexion.cursor()

    publicaciones = [

        (
            "x_004",
            "X",
            "@alerta_gt",
            (
                "Reportan un asalto en la Calzada Roosevelt. "
                "Le quitaron el celular a una persona."
            ),
            "https://x.com/prueba/004",
            None,
            "2026-08-14 08:30:00"
        ),

        (
            "fb_003",
            "Facebook",
            "Usuario Prueba",
            (
                "Golpearon a un joven cerca de la "
                "Avenida Petapa."
            ),
            "https://facebook.com/prueba/003",
            None,
            "2026-08-14 12:15:00"
        ),

        (
            "x_005",
            "X",
            "@vecinos_mixco",
            (
                "Están cobrando renta a comerciantes "
                "en la colonia El Milagro."
            ),
            "https://x.com/prueba/005",
            None,
            "2026-08-15 18:40:00"
        )
    ]


    for publicacion in publicaciones:

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
            """, publicacion)

            print(
                f"Insertada correctamente: "
                f"{publicacion[0]}"
            )

        except sqlite3.IntegrityError:

            print(
                f"Publicación duplicada ignorada: "
                f"{publicacion[0]}"
            )


    conexion.commit()
    conexion.close()


if __name__ == "__main__":
    insertar_pruebas()