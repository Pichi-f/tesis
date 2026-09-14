import sqlite3
from pathlib import Path

import numpy as np

import folium

from scipy.stats import gaussian_kde

from flask import (
    Flask,
    render_template,
    request,
    jsonify
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
            fecha_publicacion,
            referencia_geografica,
            metodo_geolocalizacion,
            precision_geografica
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


def formatear_precision(precision):

    valores = {
        "alta": "Alta",
        "media": "Media",
        "baja": "Baja"
    }

    return valores.get(
        precision,
        "No determinada"
    )


def formatear_metodo(metodo):

    valores = {
        "coordenadas_explicitas":
            "Coordenadas explícitas",

        "catalogo_local":
            "Catálogo local",

        "geocodificacion_nominatim":
            "Geocodificación externa",

        "cache_geocodificacion":
            "Caché de geocodificación"
    }

    return valores.get(
        metodo,
        "No determinado"
    )
    
    
def generar_densidad_kde(indicios):
    
    if len(indicios) < 3:
        return []


    latitudes = np.array([
        indicio["latitud"]
        for indicio in indicios
    ])

    longitudes = np.array([
        indicio["longitud"]
        for indicio in indicios
    ])


    # ==========================================
    # CALCULAR KDE
    # ==========================================

    coordenadas = np.vstack([
        longitudes,
        latitudes
    ])


    try:

        kde = gaussian_kde(
            coordenadas
        )

    except np.linalg.LinAlgError:

        return []


    # ==========================================
    # CREAR ÁREA DE EVALUACIÓN
    # ==========================================

    margen_lat = 0.02
    margen_lon = 0.02


    min_lat = latitudes.min() - margen_lat
    max_lat = latitudes.max() + margen_lat

    min_lon = longitudes.min() - margen_lon
    max_lon = longitudes.max() + margen_lon


    cantidad_celdas = 35


    valores_lat = np.linspace(
        min_lat,
        max_lat,
        cantidad_celdas
    )

    valores_lon = np.linspace(
        min_lon,
        max_lon,
        cantidad_celdas
    )


    puntos_kde = []


    # ==========================================
    # EVALUAR DENSIDAD
    # ==========================================

    for latitud in valores_lat:

        for longitud in valores_lon:

            puntos_kde.append(
                [
                    longitud,
                    latitud
                ]
            )


    puntos_kde_array = np.array(
        puntos_kde
    ).T


    densidades = kde(
        puntos_kde_array
    )


    # ==========================================
    # NORMALIZAR DENSIDAD
    # ==========================================

    densidad_maxima = densidades.max()


    if densidad_maxima <= 0:

        return []


    densidades_normalizadas = (
        densidades
        / densidad_maxima
    )


    resultado = []


    for punto, densidad in zip(
        puntos_kde,
        densidades_normalizadas
    ):

        # Eliminamos valores demasiado bajos
        # para evitar pintar todo el mapa.

        if densidad < 0.05:

            continue


        resultado.append(
            [
                punto[1],
                punto[0],
                float(densidad)
            ]
        )


    return resultado
    

def generar_mapa(indicios):

    # ==========================================
    # CENTRO Y ZOOM INICIAL
    # ==========================================

    if len(indicios) == 1:

        centro = [
            indicios[0]["latitud"],
            indicios[0]["longitud"]
        ]

        zoom = 14

    else:

        centro = [
            14.61,
            -90.55
        ]

        zoom = 11


    mapa = folium.Map(
        location=centro,
        zoom_start=zoom,
        control_scale=True
    )
    
    

    puntos_calor = []
    
    capa_incidentes = folium.FeatureGroup(
        name="Incidentes",
        show=True
    )


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
        
        referencia = indicio[
            "referencia_geografica"
        ]

        metodo = indicio[
            "metodo_geolocalizacion"
        ]

        precision = indicio[
            "precision_geografica"
        ]


        precision_texto = formatear_precision(
            precision
        )

        metodo_texto = formatear_metodo(
            metodo
        )

        descripcion_precision = {
            "alta": "Ubicación obtenida mediante coordenadas explícitas.",
            "media": "Ubicación aproximada basada en una referencia relativamente acotada.",
            "baja": "Ubicación representativa de una referencia geográfica amplia."
        }.get(
            precision,
            "Precisión no determinada."
        )

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

            popup=folium.Popup(
                html=(
                    f"<div style='width: 260px;'>"

                    f"<h4 style='margin-bottom: 10px;'>"
                    f"Detalle del indicio"
                    f"</h4>"

                    f"<b>Categoría:</b> "
                    f"{categoria.capitalize()}"
                    f"<br><br>"

                    f"<b>Confianza:</b> "
                    f"{score * 100:.2f}%"
                    f"<br><br>"

                    f"<b>Referencia geográfica:</b><br>"
                    f"{referencia or 'No disponible'}"
                    f"<br><br>"

                    f"<b>Precisión geográfica:</b> "
                    f"{precision_texto}"
                    f"<br><br>"
                    
                    f"<span style='font-size: 11px; color: #666;'>"
                    f"{descripcion_precision}"
                    f"</span>"
                    f"<br><br>"

                    f"<b>Método de ubicación:</b><br>"
                    f"{metodo_texto}"
                    f"<br><br>"

                    f"<b>Fecha:</b><br>"
                    f"{fecha}"

                    f"</div>"
                ),

                max_width=300
            )

        ).add_to(capa_incidentes)
        
    capa_incidentes.add_to(
        mapa
    )


    # ==========================================
    # CAPA KDE
    # ==========================================

    puntos_kde = generar_densidad_kde(
        indicios
    )


    if puntos_kde:

        capa_kde = folium.FeatureGroup(
            name="Densidad KDE",
            show=True
        )


        HeatMap(
            puntos_kde,

            radius=25,

            blur=20,

            min_opacity=0.2,

            max_zoom=13

        ).add_to(
            capa_kde
        )


        capa_kde.add_to(
            mapa
        )


    # ==========================================
    # CONTROL DE CAPAS
    # ==========================================

    folium.LayerControl(
        collapsed=False
    ).add_to(
        mapa
    )


    # ==========================================
    # AJUSTAR VISTA
    # ==========================================

    if len(puntos_calor) > 1:

        mapa.fit_bounds(
            puntos_calor,
            padding=(
                40,
                40
            )
        )
        
    if not indicios:

        folium.Marker(
            location=[
                14.61,
                -90.55
            ],

            icon=folium.DivIcon(
                html="""
                    <div style="
                        width: 260px;
                        padding: 12px;
                        background: white;
                        border: 1px solid #cccccc;
                        border-radius: 6px;
                        font-size: 14px;
                        text-align: center;
                    ">
                        No se encontraron incidentes
                        con los filtros seleccionados.
                    </div>
                """
            )
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


@app.route("/estadisticas")
def estadisticas():

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

    resumen = {
        "total": len(indicios),
        "robo": 0,
        "extorsion": 0,
        "agresion": 0,
        "otro": 0
    }

    for indicio in indicios:

        categoria = indicio[
            "categoria_delito"
        ]

        if categoria in resumen:

            resumen[categoria] += 1

    return jsonify(resumen)


if __name__ == "__main__":

    app.run(
        debug=True
    )