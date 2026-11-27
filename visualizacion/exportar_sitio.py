"""Genera la versión estática del visor para publicarla en GitHub Pages.

Uso: python visualizacion/exportar_sitio.py

Escribe en sitio/:
- index.html: los estilos y el panel de templates/index.html con un mapa
  Leaflet que filtra, resume por zona y calcula el KDE en el navegador.
- indicios.json: los indicios de la base, solo con lo que el mapa necesita
  (categoría, confianza, coordenadas, fecha, lugar y precisión). No incluye
  ningún texto de las publicaciones ni datos de sus autores (RNF-PLN-04).

Después de generar, se suben a GitHub los cambios de sitio/ y el flujo
.github/workflows/pages.yml lo publica.
"""

import json
import re
import shutil
import sqlite3
from datetime import datetime
from pathlib import Path

import folium

BASE_DIR = Path(__file__).resolve().parent.parent
DB_PATH = BASE_DIR / "data" / "cifra_negra.db"
CONFIG_PATH = BASE_DIR / "config" / "configuracion.json"
PLANTILLA_FLASK = BASE_DIR / "templates" / "index.html"
PLANTILLA_SITIO = Path(__file__).resolve().parent / "plantilla_sitio.html"
SALIDA = BASE_DIR / "sitio"


def leer_indicios():
    conexion = sqlite3.connect(DB_PATH)
    conexion.row_factory = sqlite3.Row
    filas = conexion.execute(
        """
        SELECT categoria_delito, score_clasificacion, latitud, longitud,
               fecha_publicacion, referencia_geografica,
               metodo_geolocalizacion, precision_geografica, sector
        FROM indicio_procesado
        ORDER BY fecha_publicacion
        """
    ).fetchall()
    conexion.close()

    return [
        {
            "categoria": fila["categoria_delito"],
            "score": round(fila["score_clasificacion"], 4),
            "latitud": round(fila["latitud"], 6),
            "longitud": round(fila["longitud"], 6),
            "fecha": str(fila["fecha_publicacion"]).replace("T", " ").replace(".000Z", ""),
            "dia": str(fila["fecha_publicacion"])[:10],
            "referencia": fila["referencia_geografica"],
            "metodo": fila["metodo_geolocalizacion"],
            "precision": fila["precision_geografica"],
            "sector": fila["sector"],
        }
        for fila in filas
    ]


def generar_html():
    """Reutiliza los estilos y el panel de la interfaz Flask."""
    flask = PLANTILLA_FLASK.read_text(encoding="utf-8")
    estilos = re.search(r"<style>.*?</style>", flask, re.S).group()
    panel = re.search(r'<aside class="panel">.*?</aside>', flask, re.S).group()
    panel = panel.replace("{{ total_indicios }}", "0")

    plantilla = PLANTILLA_SITIO.read_text(encoding="utf-8")
    return plantilla.replace("{{ESTILOS}}", estilos).replace("{{PANEL}}", panel)


def exportar():
    with open(CONFIG_PATH, "r", encoding="utf-8") as archivo:
        configuracion = json.load(archivo)

    indicios = leer_indicios()
    datos = {
        "generado": datetime.now().strftime("%d/%m/%Y"),
        "kde": {
            "bandwidth_metros": configuracion.get("bandwidth_kde_metros", 1500),
            "resolucion": configuracion.get("resolucion_kde", 45),
        },
        "indicios": indicios,
    }

    SALIDA.mkdir(exist_ok=True)
    (SALIDA / "indicios.json").write_text(
        json.dumps(datos, ensure_ascii=False, indent=1), encoding="utf-8"
    )
    (SALIDA / "index.html").write_text(generar_html(), encoding="utf-8")
    # La misma versión de leaflet.heat que usa Folium en main.py, para que
    # el mapa de calor se vea igual en los dos visores.
    shutil.copy(
        Path(folium.__file__).parent / "templates" / "leaflet_heat.min.js",
        SALIDA / "leaflet_heat.min.js",
    )
    # GitHub Pages no debe procesar el sitio con Jekyll.
    (SALIDA / ".nojekyll").write_text("", encoding="utf-8")

    print(f"Indicios exportados: {len(indicios)}")
    print(f"Sitio: {SALIDA}")


if __name__ == "__main__":
    exportar()
