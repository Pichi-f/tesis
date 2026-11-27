"""Traduce chapinismos y jerga urbana a su equivalente formal (RF-PLN-03).

El diccionario vive en config/chapinismos.json (RNF-PLN-03), sección
"expresiones". Se aplica sobre el texto ya preprocesado (lematizado y sin
stopwords), por eso las expresiones del diccionario se preprocesan igual al
cargarlas: "cacos" y "caco" coinciden, y "meter bala" coincide con
"le metieron bala". Las frases de varias palabras se reemplazan antes que
las palabras sueltas.
"""

import json
from functools import lru_cache
from pathlib import Path

from preprocesar import preprocesar_texto


BASE_DIR = Path(__file__).resolve().parent.parent
RUTA_DICCIONARIO = BASE_DIR / "config" / "chapinismos.json"


def cargar_diccionario():
    with open(RUTA_DICCIONARIO, "r", encoding="utf-8") as archivo:
        datos = json.load(archivo)
    # Formato anterior: un objeto plano {"caco": "ladron", ...}
    return datos.get("expresiones", datos) if isinstance(datos.get("expresiones"), dict) else datos


@lru_cache(maxsize=1)
def diccionario_preparado():
    """[(tokens de la expresión, tokens del equivalente)], de la más larga a la más corta.

    Una palabra suelta se compara tal como está escrita (spaCy la lematiza
    distinto fuera de contexto: "mara" quedaría como "mar"). Las frases sí se
    preprocesan, para descartar artículos y conjugar como en el texto.
    """
    entradas = {}
    for expresion, equivalente in cargar_diccionario().items():
        if expresion.startswith("_"):
            continue
        expresion = expresion.lower().strip()
        if " " in expresion:
            clave = tuple(preprocesar_texto(expresion).split())
        else:
            clave = (expresion,)
        if clave:
            entradas[clave] = preprocesar_texto(equivalente).split() or [equivalente]
    return sorted(entradas.items(), key=lambda entrada: -len(entrada[0]))


def coincide(palabras, expresion):
    """Las palabras sueltas admiten el plural (cacos, clicas, mareros)."""
    if len(expresion) == 1:
        clave = expresion[0]
        return bool(palabras) and palabras[0] in (clave, clave + "s", clave + "es")
    return tuple(palabras) == expresion


def normalizar_chapinismos(texto):
    if not texto:
        return ""

    palabras = texto.split()
    resultado = []
    posicion = 0

    while posicion < len(palabras):
        for expresion, equivalente in diccionario_preparado():
            fin = posicion + len(expresion)
            if coincide(palabras[posicion:fin], expresion):
                resultado.extend(equivalente)
                posicion = fin
                break
        else:
            resultado.append(palabras[posicion])
            posicion += 1

    return " ".join(resultado)


if __name__ == "__main__":

    pruebas = [
        "Mucha, unos cacos estaban cobrando la renta y uno llevaba un cuete en la zona 1.",
        "Le metieron bala a un patojo en la colonia, quedó encostalado.",
        "B@L@CERA en zona 18: 4S3S1N4N a JOV3N, captur4s en la 4ta avenida.",
    ]

    for texto_prueba in pruebas:
        texto_procesado = preprocesar_texto(texto_prueba)
        print("\nTEXTO ORIGINAL:            ", texto_prueba)
        print("DESPUÉS DEL PREPROCESAMIENTO:", texto_procesado)
        print("DESPUÉS DE CHAPINISMOS:      ", normalizar_chapinismos(texto_procesado))
