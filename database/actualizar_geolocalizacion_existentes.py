import sqlite3
import sys
from pathlib import Path


BASE_DIR = Path(__file__).resolve().parent.parent
DB_PATH = BASE_DIR / "data" / "cifra_negra.db"

# Permite importar módulos desde procesamiento/
sys.path.insert(
    0,
    str(BASE_DIR)
)

from procesamiento.geolocalizar import buscar_ubicacion


def actualizar_geolocalizacion():

    conexion = sqlite3.connect(DB_PATH)

    conexion.row_factory = sqlite3.Row

    cursor = conexion.cursor()

    # Solamente buscamos indicios que todavía
    # no tengan la nueva información geográfica.
    cursor.execute("""
        SELECT
            i.id_indicio,
            i.id_reporte,
            i.latitud AS latitud_anterior,
            i.longitud AS longitud_anterior,
            r.texto_crudo,
            r.referencia_espacial
        FROM indicio_procesado i
        INNER JOIN reporte_crudo r
            ON i.id_reporte = r.id_reporte
        WHERE
            i.referencia_geografica IS NULL
            OR i.metodo_geolocalizacion IS NULL
            OR i.precision_geografica IS NULL
        ORDER BY i.id_indicio
    """)

    indicios = cursor.fetchall()

    print(
        f"\nIndicios pendientes de actualizar: "
        f"{len(indicios)}\n"
    )

    actualizados = 0
    errores = 0


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
            f"Texto: "
            f"{indicio['texto_crudo']}"
        )


        ubicacion = buscar_ubicacion(
            indicio["texto_crudo"],
            indicio["referencia_espacial"]
        )


        if not ubicacion:

            print(
                "ERROR: No se pudo determinar "
                "la ubicación."
            )

            errores += 1

            continue


        referencia_geografica = ubicacion.get(
            "referencia"
        )

        if not referencia_geografica:

            referencia_geografica = (
                indicio["referencia_espacial"]
                or ubicacion["nombre"]
            )


        print(
            f"Coordenadas anteriores: "
            f"{indicio['latitud_anterior']}, "
            f"{indicio['longitud_anterior']}"
        )

        print(
            f"Coordenadas actuales: "
            f"{ubicacion['latitud']}, "
            f"{ubicacion['longitud']}"
        )

        print(
            f"Referencia: "
            f"{referencia_geografica}"
        )

        print(
            f"Método: "
            f"{ubicacion['metodo']}"
        )

        print(
            f"Precisión: "
            f"{ubicacion['precision']}"
        )


        cursor.execute("""
            UPDATE indicio_procesado
            SET
                latitud = ?,
                longitud = ?,
                referencia_geografica = ?,
                metodo_geolocalizacion = ?,
                precision_geografica = ?
            WHERE id_indicio = ?
        """, (
            ubicacion["latitud"],
            ubicacion["longitud"],
            referencia_geografica,
            ubicacion["metodo"],
            ubicacion["precision"],
            indicio["id_indicio"]
        ))

        conexion.commit()

        actualizados += 1

        print(
            "Resultado: actualizado correctamente."
        )


    conexion.close()


    print("\n" + "=" * 70)

    print(
        "RESUMEN DE ACTUALIZACIÓN"
    )

    print(
        f"Actualizados: {actualizados}"
    )

    print(
        f"Errores: {errores}"
    )

    print("=" * 70)


if __name__ == "__main__":

    actualizar_geolocalizacion()