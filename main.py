import sqlite3
from pathlib import Path

import numpy as np

import folium

import json

from pyproj import Transformer
from sklearn.neighbors import KernelDensity

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

CONFIG_PATH = (
    BASE_DIR / "config" / "configuracion.json"
)


app = Flask(__name__)

# WGS84:
# latitud / longitud utilizadas por GPS y Folium
#
# UTM zona 15N:
# coordenadas métricas apropiadas para Guatemala

wgs84_a_utm = Transformer.from_crs(
    "EPSG:4326",
    "EPSG:32615",
    always_xy=True
)

utm_a_wgs84 = Transformer.from_crs(
    "EPSG:32615",
    "EPSG:4326",
    always_xy=True
)


def cargar_configuracion():

    with open(
        CONFIG_PATH,
        "r",
        encoding="utf-8"
    ) as archivo:

        return json.load(archivo)


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
            precision_geografica,
            sector
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

    # Con un único punto no existe una
    # distribución espacial útil.
    if len(indicios) < 2:
        return []


    configuracion = cargar_configuracion()

    bandwidth = configuracion.get(
        "bandwidth_kde_metros",
        1500
    )

    resolucion = configuracion.get(
        "resolucion_kde",
        45
    )


    # ==========================================
    # CONVERTIR LAT/LON A COORDENADAS EN METROS
    # ==========================================

    coordenadas_metros = []


    for indicio in indicios:

        longitud = indicio[
            "longitud"
        ]

        latitud = indicio[
            "latitud"
        ]


        x, y = wgs84_a_utm.transform(
            longitud,
            latitud
        )


        coordenadas_metros.append(
            [
                x,
                y
            ]
        )


    coordenadas_metros = np.array(
        coordenadas_metros
    )


    valores_x = coordenadas_metros[
        :,
        0
    ]

    valores_y = coordenadas_metros[
        :,
        1
    ]


    # ==========================================
    # ENTRENAR KDE
    # ==========================================

    kde = KernelDensity(
        kernel="gaussian",
        bandwidth=bandwidth
    )


    kde.fit(
        coordenadas_metros
    )


    # ==========================================
    # CREAR CUADRÍCULA
    # ==========================================

    # Evaluamos hasta 3 bandwidth alrededor
    # de los incidentes extremos.

    margen = bandwidth * 3


    min_x = valores_x.min() - margen
    max_x = valores_x.max() + margen

    min_y = valores_y.min() - margen
    max_y = valores_y.max() + margen


    grid_x = np.linspace(
        min_x,
        max_x,
        resolucion
    )

    grid_y = np.linspace(
        min_y,
        max_y,
        resolucion
    )


    malla_x, malla_y = np.meshgrid(
        grid_x,
        grid_y
    )


    puntos_malla = np.column_stack(
        [
            malla_x.ravel(),
            malla_y.ravel()
        ]
    )


    # ==========================================
    # CALCULAR DENSIDADES
    # ==========================================

    log_densidades = kde.score_samples(
        puntos_malla
    )


    densidades = np.exp(
        log_densidades
    )


    densidad_maxima = densidades.max()


    if densidad_maxima <= 0:

        return []


    densidades_normalizadas = (
        densidades
        / densidad_maxima
    )


    # ==========================================
    # REGRESAR A LATITUD / LONGITUD
    # ==========================================

    resultado = []


    for punto, densidad in zip(
        puntos_malla,
        densidades_normalizadas
    ):

        # Omitimos densidades prácticamente
        # irrelevantes para no pintar
        # todo el mapa.

        if densidad < 0.05:
            continue


        x = punto[0]
        y = punto[1]


        longitud, latitud = (
            utm_a_wgs84.transform(
                x,
                y
            )
        )


        resultado.append(
            [
                latitud,
                longitud,
                float(densidad)
            ]
        )


    return resultado
    

NOMBRES_CATEGORIA = {
    "robo": "Robo",
    "extorsion": "Extorsión",
    "agresion": "Agresión",
    "otro": "Otro"
}


def agregar_resumen_por_zona(mapa, indicios):
    """RF-VIS-04: un marcador por zona o municipio con estadísticas resumidas.

    Se ubica en el centro de los indicios de ese sector y su ventana
    emergente muestra solo conteos y fechas, nunca el texto de los
    reportes, para mantener la anonimización.
    """
    sectores = {}

    for indicio in indicios:

        sector = indicio["sector"]

        if not sector or sector == "Sin determinar":
            continue

        sectores.setdefault(sector, []).append(indicio)

    if not sectores:
        return

    capa = folium.FeatureGroup(
        name="Resumen por zona",
        show=True
    )

    total_general = len(indicios)

    for sector, grupo in sectores.items():

        latitud = float(np.mean([i["latitud"] for i in grupo]))
        longitud = float(np.mean([i["longitud"] for i in grupo]))

        conteos = {clave: 0 for clave in NOMBRES_CATEGORIA}
        for indicio in grupo:
            if indicio["categoria_delito"] in conteos:
                conteos[indicio["categoria_delito"]] += 1

        predominante = max(conteos, key=conteos.get)
        fechas = sorted(str(i["fecha_publicacion"])[:10] for i in grupo)

        filas = "".join(
            f"<tr><td>{NOMBRES_CATEGORIA[clave]}</td>"
            f"<td style='text-align:right;'><b>{cantidad}</b></td></tr>"
            for clave, cantidad in conteos.items()
            if cantidad
        )

        popup = (
            f"<div style='width: 230px; font-family: Arial, sans-serif;'>"
            f"<h4 style='margin: 0 0 8px 0;'>{sector}</h4>"
            f"<b>{len(grupo)}</b> indicios "
            f"({len(grupo) / total_general:.0%} de los mostrados)"
            f"<table style='width: 100%; margin: 8px 0; font-size: 13px;'>"
            f"{filas}</table>"
            f"<b>Predominante:</b> {NOMBRES_CATEGORIA[predominante]}<br>"
            f"<b>Periodo:</b> {fechas[0]} a {fechas[-1]}"
            f"</div>"
        )

        tamano = 22 + min(len(grupo), 30)

        folium.Marker(
            location=[latitud, longitud],
            tooltip=f"{sector}: {len(grupo)}",
            popup=folium.Popup(popup, max_width=260),
            icon=folium.DivIcon(
                icon_size=(tamano, tamano),
                icon_anchor=(tamano // 2, tamano // 2),
                html=(
                    f"<div style='width: {tamano}px; height: {tamano}px; "
                    f"line-height: {tamano}px; border-radius: 50%; "
                    f"background: rgba(33, 37, 41, 0.85); color: white; "
                    f"border: 2px solid white; text-align: center; "
                    f"font: bold 12px Arial, sans-serif;'>{len(grupo)}</div>"
                )
            )
        ).add_to(capa)

    capa.add_to(mapa)


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

    agregar_resumen_por_zona(
        mapa,
        indicios
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
        "otro": 0,

        "precision_alta": 0,
        "precision_media": 0,
        "precision_baja": 0
    }


    for indicio in indicios:

        categoria = indicio[
            "categoria_delito"
        ]

        precision = indicio[
            "precision_geografica"
        ]


        if categoria in resumen:

            resumen[categoria] += 1


        clave_precision = (
            f"precision_{precision}"
        )


        if clave_precision in resumen:

            resumen[
                clave_precision
            ] += 1


    # RF-VIS-04: incidentes por zona o municipio, de mayor a menor.
    por_sector = {}

    for indicio in indicios:

        sector = indicio["sector"] or "Sin determinar"

        fila = por_sector.setdefault(
            sector,
            {
                "sector": sector,
                "total": 0,
                "robo": 0,
                "extorsion": 0,
                "agresion": 0,
                "otro": 0
            }
        )

        fila["total"] += 1

        if indicio["categoria_delito"] in fila:
            fila[indicio["categoria_delito"]] += 1

    resumen["por_sector"] = sorted(
        por_sector.values(),
        key=lambda fila: (-fila["total"], fila["sector"])
    )

    return jsonify(
        resumen
    )


if __name__ == "__main__":

    app.run(
        debug=True
    )