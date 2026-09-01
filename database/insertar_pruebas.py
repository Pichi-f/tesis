import sqlite3
from pathlib import Path


BASE_DIR = Path(__file__).resolve().parent.parent
DB_PATH = BASE_DIR / "data" / "cifra_negra.db"


def insertar_datos_prueba():

    conexion = sqlite3.connect(DB_PATH)
    cursor = conexion.cursor()

    publicaciones = [

        (
            "x_001",
            "X",
            "@usuario_prueba1",
            "Mucha cuidado, acaban de asaltar a una persona en la zona 1.",
            "https://x.com/prueba/001",
            "Zona 1",
            "2026-08-10 08:30:00"
        ),

        (
            "x_002",
            "X",
            "@usuario_prueba2",
            "Están cobrando renta a varios negocios en Mixco.",
            "https://x.com/prueba/002",
            "Mixco",
            "2026-08-10 10:15:00"
        ),

        (
            "fb_001",
            "Facebook",
            "Usuario Prueba",
            "Hubo una pelea fuerte cerca del mercado de Villa Nueva.",
            "https://facebook.com/prueba/001",
            "Villa Nueva",
            "2026-08-11 18:45:00"
        ),

        (
            "fb_002",
            "Facebook",
            "Usuario Deportes",
            "Qué buen partido estuvo el de anoche, estuvo increíble.",
            "https://facebook.com/prueba/002",
            None,
            "2026-08-12 20:00:00"
        ),

        (
            "x_003",
            "X",
            "@alertagt",
            "Reportan una balacera cerca del Trébol, tengan cuidado.",
            "https://x.com/prueba/003",
            "El Trébol",
            "2026-08-13 07:20:00"
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
    insertar_datos_prueba()