import sqlite3
from pathlib import Path

import folium

from flask import (
    Flask,
    render_template,
    request
)

from folium.plugins import HeatMap


BASE_DIR = Path(__file__).resolve().parent

DB_PATH = (
    BASE_DIR / "data" / "cifra_negra.db"
)


app = Flask(__name__)


def obtener_indicios(
    categorias=None,
    fecha_desde=None,
    fecha_hasta=None
):

    conexion = sqlite3.connect(DB_PATH)

    conexion.row_factory = sqlite3.Row

    cursor = conexion.cursor()

    consulta = """
        SELECT
            id_indicio,
            texto_procesado,
            categoria_delito,
            score_clasificacion,
            latitud,
            longitud,
            fecha_publicacion
        FROM indicio_procesado
        WHERE 1 = 1
    """

    parametros = []

    # ==========================================
    # FILTRO POR CATEGORÍA
    # ==========================================

    if categorias:

        marcadores = ",".join(
            "?"
            for _ in categorias
        )

        consulta += (
            f" AND categoria_delito "
            f"IN ({marcadores})"
        )

        parametros.extend(
            categorias
        )

    # ==========================================
    # FILTRO FECHA DESDE
    # ==========================================

    if fecha_desde:

        consulta += """
            AND date(fecha_publicacion) >= date(?)
        """

        parametros.append(
            fecha_desde
        )

    # ==========================================
    # FILTRO FECHA HASTA
    # ==========================================

    if fecha_hasta:

        consulta += """
            AND date(fecha_publicacion) <= date(?)
        """

        parametros.append(
            fecha_hasta
        )

    consulta += """
        ORDER BY fecha_publicacion
    """

    cursor.execute(
        consulta,
        parametros
    )

    indicios = cursor.fetchall()

    conexion.close()

    return indicios


def generar_mapa(indicios):

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

        latitud = indicio[
            "latitud"
        ]

        longitud = indicio[
            "longitud"
        ]

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

    if puntos_calor:

        HeatMap(
            puntos_calor,
            radius=30,
            blur=20,
            min_opacity=0.4
        ).add_to(mapa)

    return mapa.get_root().render()


@app.route("/")
def inicio():

    indicios = obtener_indicios()

    return render_template(
        "index.html",
        total_indicios=len(indicios)
    )


@app.route("/mapa")
def mapa():

    categorias = request.args.getlist(
        "categoria"
    )

    fecha_desde = request.args.get(
        "desde"
    )

    fecha_hasta = request.args.get(
        "hasta"
    )

    indicios = obtener_indicios(
        categorias=categorias,
        fecha_desde=fecha_desde,
        fecha_hasta=fecha_hasta
    )

    return generar_mapa(
        indicios
    )


if __name__ == "__main__":

    app.run(
        debug=True
    )