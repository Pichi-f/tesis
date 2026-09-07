import sqlite3
from pathlib import Path


BASE_DIR = Path(__file__).resolve().parent.parent

DB_PATH = (
    BASE_DIR / "data" / "cifra_negra.db"
)


def obtener_columnas(cursor):

    cursor.execute(
        "PRAGMA table_info(indicio_procesado)"
    )

    return {
        fila[1]
        for fila in cursor.fetchall()
    }


def migrar():

    conexion = sqlite3.connect(DB_PATH)

    cursor = conexion.cursor()

    columnas = obtener_columnas(
        cursor
    )

    # ==========================================
    # REFERENCIA GEOGRÁFICA
    # ==========================================

    if "referencia_geografica" not in columnas:

        cursor.execute("""
            ALTER TABLE indicio_procesado
            ADD COLUMN referencia_geografica TEXT
        """)

        print(
            "Columna referencia_geografica agregada."
        )

    else:

        print(
            "referencia_geografica ya existe."
        )


    # ==========================================
    # MÉTODO DE GEOLOCALIZACIÓN
    # ==========================================

    if "metodo_geolocalizacion" not in columnas:

        cursor.execute("""
            ALTER TABLE indicio_procesado
            ADD COLUMN metodo_geolocalizacion TEXT
        """)

        print(
            "Columna metodo_geolocalizacion agregada."
        )

    else:

        print(
            "metodo_geolocalizacion ya existe."
        )


    # ==========================================
    # PRECISIÓN GEOGRÁFICA
    # ==========================================

    if "precision_geografica" not in columnas:

        cursor.execute("""
            ALTER TABLE indicio_procesado
            ADD COLUMN precision_geografica TEXT
            CHECK (
                precision_geografica IN (
                    'alta',
                    'media',
                    'baja'
                )
                OR precision_geografica IS NULL
            )
        """)

        print(
            "Columna precision_geografica agregada."
        )

    else:

        print(
            "precision_geografica ya existe."
        )


    conexion.commit()

    conexion.close()

    print(
        "\nMigración terminada correctamente."
    )


if __name__ == "__main__":
    migrar()