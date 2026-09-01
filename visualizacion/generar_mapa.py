import sqlite3
from pathlib import Path

import folium
from folium.plugins import HeatMap


BASE_DIR = Path(__file__).resolve().parent.parent

DB_PATH = (
    BASE_DIR / "data" / "cifra_negra.db"
)

MAPA_PATH = (
    BASE_DIR / "visualizacion" / "mapa_inicial.html"
)


def obtener_indicios():

    conexion = sqlite3.connect(DB_PATH)

    conexion.row_factory = sqlite3.Row

    cursor = conexion.cursor()

    cursor.execute("""
        SELECT
            id_indicio,
            categoria_delito,
            score_clasificacion,
            latitud,
            longitud,
            fecha_publicacion
        FROM indicio_procesado
        ORDER BY fecha_publicacion
    """)

    indicios = cursor.fetchall()

    conexion.close()

    return indicios


def generar_mapa():

    indicios = obtener_indicios()

    print(
        f"\nIndicios encontrados: "
        f"{len(indicios)}"
    )

    if not indicios:

        print(
            "No existen indicios para mostrar."
        )

        return

    # Centro aproximado del Área Metropolitana
    mapa = folium.Map(
        location=[
            14.61,
            -90.55
        ],
        zoom_start=11,
        control_scale=True
    )

    puntos_calor = []

    for indicio in indicios:

        latitud = indicio["latitud"]
        longitud = indicio["longitud"]

        categoria = indicio[
            "categoria_delito"
        ]

        score = indicio[
            "score_clasificacion"
        ]

        fecha = indicio[
            "fecha_publicacion"
        ]

        puntos_calor.append(
            [
                latitud,
                longitud
            ]
        )

        # Marcador temporal para comprobar
        # que las coordenadas son correctas
        folium.CircleMarker(
            location=[
                latitud,
                longitud
            ],
            radius=6,
            fill=True,
            fill_opacity=0.8,
            popup=(
                f"<b>Categoría:</b> "
                f"{categoria}<br>"
                f"<b>Confianza:</b> "
                f"{score * 100:.2f}%<br>"
                f"<b>Fecha:</b> "
                f"{fecha}"
            )
        ).add_to(mapa)

    # Mapa de calor
    HeatMap(
        puntos_calor,
        radius=30,
        blur=20,
        min_opacity=0.4
    ).add_to(mapa)

    mapa.save(MAPA_PATH)

    print(
        "Mapa generado correctamente."
    )

    print(
        f"Ubicación: {MAPA_PATH}"
    )


if __name__ == "__main__":
    generar_mapa()