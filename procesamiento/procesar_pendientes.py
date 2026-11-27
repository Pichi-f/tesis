import json
import sqlite3
import sys
import time
from pathlib import Path
from configurar_logs import obtener_logger

from clasificar import (
    cargar_modelos,
    clasificar_texto
)

from geolocalizar import buscar_ubicacion

# La consola de Windows (cp1252) no puede imprimir emojis de las
# publicaciones; se reemplazan en lugar de abortar el lote.
sys.stdout.reconfigure(errors="replace")


BASE_DIR = Path(__file__).resolve().parent.parent

DB_PATH = (
    BASE_DIR / "data" / "cifra_negra.db"
)

RUTA_CONFIGURACION = (
    BASE_DIR / "config" / "configuracion.json"
)

logger = obtener_logger()


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
    precision_geografica,
    sector
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
            precision_geografica,
            sector
        )
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
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
        precision_geografica,
        sector
    ))


def procesar_reportes():

    configuracion = cargar_configuracion()

    umbral = configuracion[
        "umbral_confianza"
    ]

    tamano_lote = configuracion.get(
        "tamano_lote",
        50
    )


    print(
        f"\nUmbral de confianza: "
        f"{umbral * 100:.2f}%"
    )

    print(
        f"Tamaño de lote: "
        f"{tamano_lote}"
    )


    logger.info(
        "Inicio del procesamiento | "
        "umbral=%.2f | lote=%d",
        umbral,
        tamano_lote
    )


    # ==========================================
    # CARGAR MODELOS
    # ==========================================

    inicio_modelo = time.perf_counter()

    vectorizador, modelo = cargar_modelos()

    tiempo_modelo = (
        time.perf_counter()
        - inicio_modelo
    )


    logger.info(
        "Modelo cargado | tiempo=%.4f s",
        tiempo_modelo
    )


    # ==========================================
    # BASE DE DATOS
    # ==========================================

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


    logger.info(
        "Reportes pendientes=%d",
        len(reportes)
    )


    procesados = 0
    ruido = 0
    errores = 0

    operaciones_lote = 0


    inicio_pipeline = (
        time.perf_counter()
    )


    # ==========================================
    # PROCESAR REPORTES
    # ==========================================

    for reporte in reportes:

        id_reporte = reporte[0]
        texto_crudo = reporte[1]
        referencia_espacial = reporte[2]
        fecha_publicacion = reporte[3]


        print("=" * 65)

        print(
            f"Procesando reporte "
            f"{id_reporte}"
        )

        print(
            f"Texto: {texto_crudo}"
        )


        try:

            # ==================================
            # INICIAR LOTE
            # ==================================

            if operaciones_lote == 0:

                conexion.execute(
                    "BEGIN"
                )


            # El savepoint permite deshacer
            # solamente el reporte actual.
            conexion.execute(
                "SAVEPOINT reporte_actual"
            )


            # ==================================
            # CLASIFICACIÓN
            # ==================================

            categoria, score, texto_procesado = (
                clasificar_texto(
                    texto_crudo,
                    vectorizador,
                    modelo
                )
            )


            print(
                f"Categoría: "
                f"{categoria}"
            )

            print(
                f"Confianza: "
                f"{score * 100:.2f}%"
            )


            logger.info(
                "Reporte=%d | "
                "categoria=%s | "
                "score=%.4f",
                id_reporte,
                categoria,
                score
            )


            # ==================================
            # RUIDO / BAJA CONFIANZA
            # ==================================

            if (
                categoria == "ruido"
                or
                score < umbral
            ):

                actualizar_estado(
                    conexion,
                    id_reporte,
                    "ruido"
                )


                conexion.execute(
                    "RELEASE SAVEPOINT reporte_actual"
                )


                ruido += 1

                operaciones_lote += 1


                logger.info(
                    "Reporte=%d | "
                    "resultado=ruido",
                    id_reporte
                )


                print(
                    "Resultado: "
                    "descartado como ruido."
                )


            else:

                # ==================================
                # GEOLOCALIZACIÓN
                # ==================================

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


                    conexion.execute(
                        "RELEASE SAVEPOINT reporte_actual"
                    )


                    errores += 1

                    operaciones_lote += 1


                    logger.warning(
                        "Reporte=%d | "
                        "resultado="
                        "error_geolocalizacion",
                        id_reporte
                    )


                    print(
                        "Resultado: "
                        "no se pudo obtener "
                        "ubicación."
                    )


                else:

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
                        f"Método: "
                        f"{ubicacion['metodo']}"
                    )

                    print(
                        f"Precisión geográfica: "
                        f"{ubicacion['precision']}"
                    )


                    referencia_geografica = (
                        ubicacion.get(
                            "referencia"
                        )
                    )


                    if not referencia_geografica:

                        referencia_geografica = (
                            referencia_espacial
                            or
                            ubicacion["nombre"]
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
                        ubicacion["precision"],
                        ubicacion.get("sector")
                    )


                    actualizar_estado(
                        conexion,
                        id_reporte,
                        "procesado"
                    )


                    conexion.execute(
                        "RELEASE SAVEPOINT reporte_actual"
                    )


                    procesados += 1

                    operaciones_lote += 1


                    logger.info(
                        "Reporte=%d | "
                        "resultado=procesado | "
                        "metodo_geo=%s | "
                        "precision_geo=%s",
                        id_reporte,
                        ubicacion["metodo"],
                        ubicacion["precision"],
                        ubicacion.get("sector")
                    )


                    print(
                        "Resultado: "
                        "procesado correctamente."
                    )


            # ==================================
            # GUARDAR LOTE
            # ==================================

            if operaciones_lote >= tamano_lote:

                conexion.commit()

                logger.info(
                    "Lote guardado | "
                    "operaciones=%d",
                    operaciones_lote
                )

                operaciones_lote = 0


        except Exception as error:

            try:

                conexion.execute(
                    "ROLLBACK TO SAVEPOINT "
                    "reporte_actual"
                )

                conexion.execute(
                    "RELEASE SAVEPOINT "
                    "reporte_actual"
                )

            except sqlite3.Error:

                pass


            try:

                actualizar_estado(
                    conexion,
                    id_reporte,
                    "error"
                )

                operaciones_lote += 1

            except sqlite3.Error:

                conexion.rollback()

                operaciones_lote = 0


            errores += 1


            logger.exception(
                "Reporte=%d | "
                "resultado=error | "
                "detalle=%s",
                id_reporte,
                error
            )


            print(
                f"ERROR: {error}"
            )


    # ==========================================
    # GUARDAR ÚLTIMO LOTE
    # ==========================================

    if operaciones_lote > 0:

        conexion.commit()

        logger.info(
            "Último lote guardado | "
            "operaciones=%d",
            operaciones_lote
        )


    tiempo_pipeline = (
        time.perf_counter()
        - inicio_pipeline
    )


    conexion.close()


    # ==========================================
    # RESUMEN
    # ==========================================

    print(
        "\n"
        + "=" * 65
    )

    print(
        "RESUMEN DEL PROCESAMIENTO"
    )

    print(
        f"Procesados: "
        f"{procesados}"
    )

    print(
        f"Ruido: "
        f"{ruido}"
    )

    print(
        f"Errores: "
        f"{errores}"
    )

    print(
        f"Tiempo carga modelo: "
        f"{tiempo_modelo:.4f} s"
    )

    print(
        f"Tiempo pipeline: "
        f"{tiempo_pipeline:.4f} s"
    )


    if len(reportes) > 0:

        velocidad = (
            len(reportes)
            / tiempo_pipeline
        )

        print(
            f"Rendimiento: "
            f"{velocidad:.2f} "
            f"reportes/s"
        )


    print(
        "=" * 65
    )


    logger.info(
        "Fin del procesamiento | "
        "procesados=%d | "
        "ruido=%d | "
        "errores=%d | "
        "tiempo=%.4f",
        procesados,
        ruido,
        errores,
        tiempo_pipeline
    )


if __name__ == "__main__":
    procesar_reportes()