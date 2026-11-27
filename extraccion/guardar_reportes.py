"""Almacena las publicaciones extraídas en la tabla reporte_crudo.

RF-PLN-01 / RNF-PLN-04: la anonimización ocurre aquí, antes de guardar, y es
irrevocable: no se conserva el nombre del autor, el texto se guarda con
nombres, teléfonos, correos, menciones y enlaces reemplazados, y la URL se
reduce a una forma que no expone el perfil.
"""

import re
import sqlite3
import sys

from navegador import BASE_DIR

sys.path.insert(0, str(BASE_DIR / "procesamiento"))
from anonimizar import anonimizar_texto  # noqa: E402

DB_PATH = BASE_DIR / "data" / "cifra_negra.db"


def huella(texto):
    """Texto reducido a letras y números para detectar copias del mismo reporte."""
    texto = re.sub(r"https?://\S+", " ", texto.lower())
    return re.sub(r"\W+", " ", texto).strip()


def anonimizar_url(url, plataforma, id_publicacion):
    """Enlace a la publicación sin el usuario ni el id del perfil."""
    if plataforma == "X":
        return f"https://x.com/i/status/{id_publicacion}"
    url = url or ""
    if re.search(r"facebook\.com/(reel|videos|groups/\d+/(posts|permalink))/", url):
        return url.split("?")[0]
    return f"https://www.facebook.com/{id_publicacion}"


def guardar_publicaciones(publicaciones):
    """Inserta las publicaciones nuevas (RF-EXT-05: control de duplicados).

    Se descarta una publicación si ya existe su identificador en la
    plataforma o si otro reporte almacenado tiene exactamente el mismo
    texto (copias y republicaciones), para no sobreponderar un incidente.
    """
    conexion = sqlite3.connect(DB_PATH)
    huellas = {
        huella(texto)
        for (texto,) in conexion.execute("SELECT texto_crudo FROM reporte_crudo")
    }
    resultado = {"insertados": 0, "duplicados": 0, "invalidos": 0}

    for publicacion in publicaciones:
        id_publicacion = publicacion.get("id_publicacion_plataforma")
        texto = anonimizar_texto(publicacion.get("texto") or "")
        fecha = publicacion.get("fecha")

        if not id_publicacion or not texto or not fecha:
            resultado["invalidos"] += 1
            continue

        if huella(texto) in huellas:
            resultado["duplicados"] += 1
            continue

        try:
            conexion.execute(
                """
                INSERT INTO reporte_crudo (
                    id_publicacion_plataforma, plataforma, usuario_publico,
                    texto_crudo, url_publicacion, referencia_espacial,
                    fecha_publicacion
                )
                VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    id_publicacion,
                    publicacion["plataforma"],
                    None,
                    texto,
                    anonimizar_url(publicacion.get("url"), publicacion["plataforma"], id_publicacion),
                    None,
                    fecha,
                ),
            )
            huellas.add(huella(texto))
            resultado["insertados"] += 1
        except sqlite3.IntegrityError:
            resultado["duplicados"] += 1

    conexion.commit()
    conexion.close()
    return resultado
