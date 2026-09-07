import json
import sqlite3
from pathlib import Path

from clasificar import (
    cargar_modelos,
    clasificar_texto
)

from geolocalizar import buscar_ubicacion


BASE_DIR = Path(__file__).resolve().parent.parent

DB_PATH = (
    BASE_DIR / "data" / "cifra_negra.db"
)

RUTA_CONFIGURACION = (
    BASE_DIR / "config" / "configuracion.json"
)


def cargar_configuracion():

    with open(
        RUTA_CONFIGURACION,
        "r",
        encoding="utf-8"
    ) as archivo:

        return json.load(archivo)


def obtener_reportes_pendientes(conexion):

    cursor = conexion.cursor()

    cursor.execute("""
        SELECT
            id_reporte,
            texto_crudo,
            referencia_espacial,
            fecha_publicacion
        FROM reporte_crudo
        WHERE estado_procesamiento = 'pendiente'
        ORDER BY id_reporte
    """)

    return cursor.fetchall()


def actualizar_estado(
    conexion,
    id_reporte,
    estado
):

    cursor = conexion.cursor()

    cursor.execute("""
        UPDATE reporte_crudo
        SET estado_procesamiento = ?
        WHERE id_reporte = ?
    """, (
        estado,
        id_reporte
    ))


def insertar_indicio(
    conexion,
    id_reporte,
    texto_procesado,
    categoria,
    score,
    latitud,
    longitud,
    fecha_publicacion,
    referencia_geografica,
    metodo_geolocalizacion,
    precision_geografica
):

    cursor = conexion.cursor()

    cursor.execute("""
        INSERT INTO indicio_procesado (
            id_reporte,
            texto_procesado,
            categoria_delito,
            score_clasificacion,
            latitud,
            longitud,
            fecha_publicacion,
            referencia_geografica,
            metodo_geolocalizacion,
            precision_geografica
        )
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (
        id_reporte,
        texto_procesado,
        categoria,
        score,
        latitud,
        longitud,
        fecha_publicacion,
        referencia_geografica,
        metodo_geolocalizacion,
        precision_geografica
    ))


def procesar_reportes():

    configuracion = cargar_configuracion()

    umbral = configuracion[
        "umbral_confianza"
    ]

    print(
        f"\nUmbral de confianza: "
        f"{umbral * 100:.2f}%"
    )

    # cargar modelo previamente entrenado
    vectorizador, modelo = cargar_modelos()

    conexion = sqlite3.connect(
        DB_PATH
    )

    conexion.execute(
        "PRAGMA foreign_keys = ON"
    )

    reportes = obtener_reportes_pendientes(
        conexion
    )

    print(
        f"Reportes pendientes: "
        f"{len(reportes)}\n"
    )

    procesados = 0
    ruido = 0
    errores = 0

    for reporte in reportes:

        (
            id_reporte,
            texto_crudo,
            referencia_espacial,
            fecha_publicacion
        ) = reporte

        print("=" * 65)

        print(
            f"Procesando reporte "
            f"{id_reporte}"
        )

        print(
            f"Texto: {texto_crudo}"
        )

        try:

            # =================================================
            # 1. CLASIFICACIÓN
            # =================================================

            (
                categoria,
                score,
                texto_procesado
            ) = clasificar_texto(
                texto_crudo,
                vectorizador,
                modelo
            )

            print(
                f"Categoría: {categoria}"
            )

            print(
                f"Confianza: "
                f"{score * 100:.2f}%"
            )

            # =================================================
            # 2. FILTRAR RUIDO
            # =================================================

            if (
                categoria == "ruido"
                or score < umbral
            ):

                actualizar_estado(
                    conexion,
                    id_reporte,
                    "ruido"
                )

                conexion.commit()

                ruido += 1

                print(
                    "Resultado: descartado "
                    "como ruido."
                )

                continue

            # =================================================
            # 3. GEOLOCALIZACIÓN
            # =================================================

            ubicacion = buscar_ubicacion(
                texto_crudo,
                referencia_espacial
            )

            if not ubicacion:

                actualizar_estado(
                    conexion,
                    id_reporte,
                    "error"
                )

                conexion.commit()

                errores += 1

                print(
                    "Resultado: no se pudo "
                    "obtener ubicación."
                )

                continue

            print(
                f"Ubicación: "
                f"{ubicacion['nombre']}"
            )

            print(
                f"Latitud: "
                f"{ubicacion['latitud']}"
            )

            print(
                f"Longitud: "
                f"{ubicacion['longitud']}"
            )
            
            print(
                f"Método: {ubicacion['metodo']}"
            )

            print(
                f"Precisión geográfica: "
                f"{ubicacion['precision']}"
            )

            # =================================================
            # 4. INSERTAR INDICIO PROCESADO
            # =================================================

            referencia_geografica = ubicacion.get(
                "referencia"
            )

            if not referencia_geografica:

                referencia_geografica = (
                    referencia_espacial
                    or ubicacion["nombre"]
                )


            insertar_indicio(
                conexion,
                id_reporte,
                texto_procesado,
                categoria,
                score,
                ubicacion["latitud"],
                ubicacion["longitud"],
                fecha_publicacion,
                referencia_geografica,
                ubicacion["metodo"],
                ubicacion["precision"]
            )

            # =================================================
            # 5. MARCAR REPORTE COMO PROCESADO
            # =================================================

            actualizar_estado(
                conexion,
                id_reporte,
                "procesado"
            )

            conexion.commit()

            procesados += 1

            print(
                "Resultado: procesado "
                "correctamente."
            )

        except Exception as error:

            conexion.rollback()

            actualizar_estado(
                conexion,
                id_reporte,
                "error"
            )

            conexion.commit()

            errores += 1

            print(
                f"ERROR: {error}"
            )

    conexion.close()

    print("\n" + "=" * 65)

    print("RESUMEN DEL PROCESAMIENTO")

    print(
        f"Procesados: {procesados}"
    )

    print(
        f"Ruido: {ruido}"
    )

    print(
        f"Errores: {errores}"
    )

    print("=" * 65)


if __name__ == "__main__":
    procesar_reportes()