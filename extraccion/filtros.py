"""Filtros previos al almacenamiento: fuente, idioma y palabras clave."""

import json
import unicodedata

from langdetect import DetectorFactory, LangDetectException, detect_langs

from navegador import BASE_DIR

DetectorFactory.seed = 42

RUTA_EXCLUIDAS = BASE_DIR / "config" / "fuentes_excluidas.json"


def normalizar(texto):
    texto = unicodedata.normalize("NFD", (texto or "").lower())
    return "".join(c for c in texto if unicodedata.category(c) != "Mn").strip()


def cargar_fuentes_excluidas():
    """Medios, instituciones y cuentas que no son reportes ciudadanos."""
    with open(RUTA_EXCLUIDAS, "r", encoding="utf-8") as archivo:
        datos = json.load(archivo)
    return {normalizar(nombre) for lista in datos.values() for nombre in lista}


def evaluar_idioma(texto, confianza_minima=0.70):
    try:
        principal = detect_langs(texto or "")[0]
    except (LangDetectException, IndexError):
        return "indeterminado"
    if principal.prob < confianza_minima:
        return "indeterminado"
    return "espanol" if principal.lang == "es" else "otro_idioma"


def contiene_palabra_clave(texto, palabras_clave):
    texto = normalizar(texto)
    return any(normalizar(palabra) in texto for palabra in palabras_clave)


def filtrar(publicaciones, excluidas, palabras_clave=None):
    """Devuelve (válidas, conteo de descartes por motivo)."""
    validas = []
    descartes = {"fuente": 0, "idioma": 0, "sin_palabra_clave": 0}

    for publicacion in publicaciones:
        if normalizar(publicacion.get("usuario_publico")) in excluidas:
            descartes["fuente"] += 1
        elif evaluar_idioma(publicacion["texto"]) != "espanol":
            descartes["idioma"] += 1
        elif palabras_clave and not contiene_palabra_clave(
            publicacion["texto"], palabras_clave
        ):
            descartes["sin_palabra_clave"] += 1
        else:
            validas.append(publicacion)

    return validas, descartes
