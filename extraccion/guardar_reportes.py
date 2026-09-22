import sqlite3
from pathlib import Path


BASE_DIR = Path(__file__).resolve().parent.parent

DB_PATH = (
    BASE_DIR / "data" / "cifra_negra.db"
)


def guardar_publicaciones(
    publicaciones
):

    conexion = sqlite3.connect(
        DB_PATH
    )

    cursor = conexion.cursor()

    insertados = 0
    duplicados = 0
    invalidos = 0


    for publicacion in publicaciones:

        id_publicacion = publicacion.get(
            "id_publicacion_plataforma"
        )

        texto = publicacion.get(
            "texto"
        )

        fecha = publicacion.get(
            "fecha"
        )


        if (
            not id_publicacion
            or not texto
            or not fecha
        ):

            invalidos += 1
            continue


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

                id_publicacion,

                publicacion[
                    "plataforma"
                ],

                publicacion.get(
                    "usuario_publico"
                ),

                texto,

                publicacion.get(
                    "url"
                ),

                None,

                fecha
            ))


            insertados += 1


        except sqlite3.IntegrityError:

            duplicados += 1


    conexion.commit()

    conexion.close()


    return {
        "insertados": insertados,
        "duplicados": duplicados,
        "invalidos": invalidos
    }