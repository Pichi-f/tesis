import json
import sqlite3
import time

from collections import Counter
from pathlib import Path

from clasificar import (
    cargar_modelos,
    clasificar_texto
)

from geolocalizar import buscar_ubicacion


BASE_DIR = Path(__file__).resolve().parent.parent

DB_PRUEBA = (
    BASE_DIR
    / "data"
    / "prueba_pipeline_500.db"
)

CONFIG_PATH = (
    BASE_DIR
    / "config"
    / "configuracion.json"
)


def cargar_umbral():

    with open(
        CONFIG_PATH,
        "r",
        encoding="utf-8"
    ) as archivo:

        configuracion = json.load(
            archivo
        )

    return configuracion[
        "umbral_confianza"
    ]


def crear_base_prueba():

    # Eliminar una prueba anterior
    if DB_PRUEBA.exists():
        DB_PRUEBA.unlink()

    conexion = sqlite3.connect(
        DB_PRUEBA
    )

    conexion.execute(
        "PRAGMA foreign_keys = ON"
    )

    cursor = conexion.cursor()


    cursor.execute("""
        CREATE TABLE reporte_crudo (

            id_reporte
                INTEGER
                PRIMARY KEY
                AUTOINCREMENT,

            id_publicacion_plataforma
                TEXT
                NOT NULL,

            plataforma
                TEXT
                NOT NULL,

            usuario_publico
                TEXT,

            texto_crudo
                TEXT
                NOT NULL,

            url_publicacion
                TEXT,

            referencia_espacial
                TEXT,

            fecha_publicacion
                DATETIME
                NOT NULL,

            estado_procesamiento
                TEXT
                NOT NULL
                DEFAULT 'pendiente'
        )
    """)


    cursor.execute("""
        CREATE TABLE indicio_procesado (

            id_indicio
                INTEGER
                PRIMARY KEY
                AUTOINCREMENT,

            id_reporte
                INTEGER
                NOT NULL
                UNIQUE,

            texto_procesado
                TEXT
                NOT NULL,

            categoria_delito
                TEXT
                NOT NULL,

            score_clasificacion
                REAL
                NOT NULL,

            latitud
                REAL
                NOT NULL,

            longitud
                REAL
                NOT NULL,

            fecha_publicacion
                DATETIME
                NOT NULL,

            referencia_geografica
                TEXT,

            metodo_geolocalizacion
                TEXT,

            precision_geografica
                TEXT,

            FOREIGN KEY(id_reporte)
                REFERENCES reporte_crudo(id_reporte)
        )
    """)


    conexion.commit()

    return conexion


def generar_publicaciones(
    cantidad=500
):

    ejemplos = [

        (
            "Me quitaron el celular "
            "cuando caminaba por zona 1.",
            "Zona 1"
        ),

        (
            "Dos hombres asaltaron a "
            "una persona en Mixco.",
            "Mixco"
        ),

        (
            "Reportan un asalto cerca "
            "del mercado de Villa Nueva.",
            "Villa Nueva"
        ),

        (
            "Un caco le robó el teléfono "
            "a una persona en zona 1.",
            "Zona 1"
        ),


        (
            "Están cobrando renta a "
            "comerciantes en Mixco.",
            "Mixco"
        ),

        (
            "Amenazaron a varios negocios "
            "para exigirles dinero en zona 1.",
            "Zona 1"
        ),

        (
            "Reportan cobro de extorsión "
            "en Villa Nueva.",
            "Villa Nueva"
        ),

        (
            "Comerciantes denuncian renta "
            "en Mixco.",
            "Mixco"
        ),


        (
            "Golpearon a un joven "
            "en Villa Nueva.",
            "Villa Nueva"
        ),

        (
            "Reportan una pelea fuerte "
            "en zona 1.",
            "Zona 1"
        ),

        (
            "Una persona fue agredida "
            "cerca del Trébol.",
            "El Trébol"
        ),

        (
            "Reportan una balacera "
            "cerca del Trébol.",
            "El Trébol"
        ),


        (
            "Reportan un vehículo "
            "sospechoso en Mixco.",
            "Mixco"
        ),

        (
            "Vecinos observaron actividad "
            "extraña en Villa Nueva.",
            "Villa Nueva"
        ),

        (
            "Hay movimiento sospechoso "
            "en zona 1.",
            "Zona 1"
        ),

        (
            "Reportan una situación "
            "inusual cerca del Trébol.",
            "El Trébol"
        ),


        (
            "Qué buen partido estuvo "
            "el de anoche.",
            None
        ),

        (
            "Hoy estuvo muy bonito "
            "el clima.",
            None
        ),

        (
            "Vamos a comer con la "
            "familia este domingo.",
            None
        ),

        (
            "Feliz cumpleaños para "
            "todos mis amigos.",
            None
        )
    ]


    publicaciones = []


    for indice in range(
        cantidad
    ):

        texto, referencia = ejemplos[
            indice % len(ejemplos)
        ]


        publicaciones.append(
            (
                f"benchmark_{indice + 1:04d}",
                "X",
                None,
                texto,
                None,
                referencia,
                "2026-08-20 10:00:00"
            )
        )


    return publicaciones


def insertar_publicaciones(
    conexion,
    publicaciones
):

    cursor = conexion.cursor()

    cursor.executemany("""
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
    """, publicaciones)

    conexion.commit()


def ejecutar_pipeline(
    conexion,
    vectorizador,
    modelo,
    umbral
):
    
    tamano_lote = 50
    operaciones_lote = 0

    conexion.row_factory = (
        sqlite3.Row
    )

    cursor = conexion.cursor()


    cursor.execute("""
        SELECT
            id_reporte,
            texto_crudo,
            referencia_espacial,
            fecha_publicacion

        FROM reporte_crudo

        WHERE
            estado_procesamiento = 'pendiente'

        ORDER BY id_reporte
    """)


    reportes = cursor.fetchall()


    procesados = 0
    ruido = 0
    errores = 0

    categorias = Counter()
    metodos_geo = Counter()


    inicio = time.perf_counter()


    for reporte in reportes:

        id_reporte = reporte[
            "id_reporte"
        ]

        texto = reporte[
            "texto_crudo"
        ]

        referencia = reporte[
            "referencia_espacial"
        ]

        fecha = reporte[
            "fecha_publicacion"
        ]


        try:

            categoria, score, texto_procesado = (
                clasificar_texto(
                    texto,
                    vectorizador,
                    modelo
                )
            )


            categorias[
                categoria
            ] += 1


            if (
                categoria == "ruido"
                or
                score < umbral
            ):

                cursor.execute("""
                    UPDATE reporte_crudo
                    SET estado_procesamiento = 'ruido'
                    WHERE id_reporte = ?
                """, (
                    id_reporte,
                ))

                ruido += 1

                continue


            ubicacion = buscar_ubicacion(
                texto,
                referencia
            )


            if not ubicacion:

                cursor.execute("""
                    UPDATE reporte_crudo
                    SET estado_procesamiento = 'error'
                    WHERE id_reporte = ?
                """, (
                    id_reporte,
                ))

                errores += 1

                continue


            referencia_geo = (
                ubicacion.get(
                    "referencia"
                )
                or referencia
                or ubicacion["nombre"]
            )


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
                VALUES (
                    ?, ?, ?, ?, ?, ?,
                    ?, ?, ?, ?
                )
            """, (

                id_reporte,

                texto_procesado,

                categoria,

                score,

                ubicacion[
                    "latitud"
                ],

                ubicacion[
                    "longitud"
                ],

                fecha,

                referencia_geo,

                ubicacion[
                    "metodo"
                ],

                ubicacion[
                    "precision"
                ]
            ))


            cursor.execute("""
                UPDATE reporte_crudo
                SET estado_procesamiento = 'procesado'
                WHERE id_reporte = ?
            """, (
                id_reporte,
            ))


            metodos_geo[
                ubicacion["metodo"]
            ] += 1


            procesados += 1
            
            operaciones_lote += 1

            if operaciones_lote >= tamano_lote:

                conexion.commit()

                operaciones_lote = 0


        except Exception as error:

            conexion.rollback()

            errores += 1

            print(
                f"Error en reporte "
                f"{id_reporte}: {error}"
            )

    if operaciones_lote > 0:
        conexion.commit()
    
    fin = time.perf_counter()


    return {
        "tiempo": fin - inicio,
        "total": len(reportes),
        "procesados": procesados,
        "ruido": ruido,
        "errores": errores,
        "categorias": categorias,
        "metodos_geo": metodos_geo
    }


def ejecutar_prueba():

    print(
        "\n"
        + "=" * 70
    )

    print(
        "PRUEBA DE RENDIMIENTO "
        "DEL PIPELINE COMPLETO"
    )

    print(
        "=" * 70
    )


    umbral = cargar_umbral()


    print(
        f"Umbral: "
        f"{umbral * 100:.2f}%"
    )


    # ==========================================
    # BASE DE DATOS TEMPORAL
    # ==========================================

    conexion = crear_base_prueba()

    publicaciones = (
        generar_publicaciones(
            500
        )
    )


    inicio_insercion = (
        time.perf_counter()
    )


    insertar_publicaciones(
        conexion,
        publicaciones
    )


    fin_insercion = (
        time.perf_counter()
    )


    tiempo_insercion = (
        fin_insercion
        - inicio_insercion
    )


    print(
        f"Publicaciones insertadas: "
        f"{len(publicaciones)}"
    )

    print(
        f"Tiempo de inserción: "
        f"{tiempo_insercion:.4f} s"
    )


    # ==========================================
    # MODELO
    # ==========================================

    inicio_modelo = (
        time.perf_counter()
    )


    vectorizador, modelo = (
        cargar_modelos()
    )


    fin_modelo = (
        time.perf_counter()
    )


    tiempo_modelo = (
        fin_modelo
        - inicio_modelo
    )


    print(
        f"Tiempo carga modelo: "
        f"{tiempo_modelo:.4f} s"
    )


    # ==========================================
    # PIPELINE
    # ==========================================

    resultado = ejecutar_pipeline(
        conexion,
        vectorizador,
        modelo,
        umbral
    )


    conexion.close()


    tiempo_pipeline = resultado[
        "tiempo"
    ]


    rendimiento = (
        resultado["total"]
        / tiempo_pipeline
    )


    tiempo_total = (
        tiempo_insercion
        + tiempo_modelo
        + tiempo_pipeline
    )


    print(
        "\n"
        + "=" * 70
    )

    print(
        "RESULTADOS"
    )

    print(
        "=" * 70
    )


    print(
        f"Reportes evaluados: "
        f"{resultado['total']}"
    )

    print(
        f"Procesados: "
        f"{resultado['procesados']}"
    )

    print(
        f"Ruido/descartados: "
        f"{resultado['ruido']}"
    )

    print(
        f"Errores: "
        f"{resultado['errores']}"
    )


    print(
        f"\nTiempo pipeline: "
        f"{tiempo_pipeline:.4f} s"
    )

    print(
        f"Rendimiento pipeline: "
        f"{rendimiento:.2f} "
        f"reportes/s"
    )

    print(
        f"Tiempo total medido: "
        f"{tiempo_total:.4f} s"
    )


    print(
        "\nClasificaciones:"
    )


    for categoria, cantidad in (
        resultado[
            "categorias"
        ].items()
    ):

        print(
            f"  {categoria}: "
            f"{cantidad}"
        )


    print(
        "\nMétodos de geolocalización:"
    )


    for metodo, cantidad in (
        resultado[
            "metodos_geo"
        ].items()
    ):

        print(
            f"  {metodo}: "
            f"{cantidad}"
        )


    print(
        "\n"
        + "=" * 70
    )


    if (
        tiempo_pipeline
        <= 120
        and
        resultado["errores"] == 0
    ):

        print(
            "RESULTADO: CUMPLE"
        )

        print(
            "El pipeline procesó "
            "500 publicaciones en "
            "menos de 120 segundos."
        )

    else:

        print(
            "RESULTADO: REVISAR"
        )


    print(
        "=" * 70
    )


    print(
        f"\nBase temporal:"
    )

    print(
        DB_PRUEBA
    )


if __name__ == "__main__":
    ejecutar_prueba()