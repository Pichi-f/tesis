import json
import re
from functools import lru_cache
from pathlib import Path

import spacy

from anonimizar import anonimizar_texto


# cargar modelo de español
nlp = spacy.load("es_core_news_sm")

RUTA_DICCIONARIO = Path(__file__).resolve().parent.parent / "config" / "chapinismos.json"


@lru_cache(maxsize=1)
def cargar_ofuscacion():
    """Sustituciones de la sección 'ofuscacion' de config/chapinismos.json."""
    with open(RUTA_DICCIONARIO, "r", encoding="utf-8") as archivo:
        datos = json.load(archivo)
    return datos.get("ofuscacion", {}) if isinstance(datos.get("expresiones"), dict) else {}


def desofuscar(texto):
    """Revierte letras sustituidas por números o símbolos (4s3s1n4d0 -> asesinado).

    Solo se toca una palabra si un carácter sustituible está entre dos letras
    (b@l@cera, jov3n) o si abre una palabra de cinco o más caracteres
    (4rmados). Así no se alteran ordinales (4ta, 3era), montos (q50) ni zonas.
    """
    sustituciones = cargar_ofuscacion()
    if not sustituciones:
        return texto
    simbolos = re.escape("".join(sustituciones))
    entre_letras = re.compile(rf"[a-záéíóúñ][{simbolos}][a-záéíóúñ]")
    al_inicio = re.compile(rf"^[{simbolos}][a-záéíóúñ{simbolos}]{{4,}}$")

    def reparar(coincidencia):
        palabra = coincidencia.group()
        nucleo = palabra.rstrip("!.,;:?")
        if entre_letras.search(nucleo) or al_inicio.match(nucleo):
            nucleo = "".join(sustituciones.get(c, c) for c in nucleo)
        return nucleo + palabra[len(palabra.rstrip("!.,;:?")):]

    return re.sub(r"\S+", reparar, texto)


def preprocesar_texto(texto):

    if not texto:
        return ""

    # 1. anonimizar antes de cualquier procesamiento
    texto = anonimizar_texto(texto)

    # 2. convertir a minúsculas y revertir la ofuscación (b@l@cera -> balacera)
    texto = desofuscar(texto.lower())

    # 3. eliminar marcadores que ya no necesitamos
    texto = texto.replace("[url]", " ")
    texto = texto.replace("[usuario]", " ")
    texto = texto.replace("[email]", " ")
    texto = texto.replace("[telefono]", " ")
    texto = texto.replace("[persona]", " ")

    # 4. eliminar caracteres especiales y números aislados
    # los números de zona se conservarán posteriormente
    texto = re.sub(
        r"[^a-záéíóúñü0-9\s]",
        " ",
        texto
    )

    # 5. eliminar espacios duplicados
    texto = re.sub(
        r"\s+",
        " ",
        texto
    ).strip()

    # 6. procesamiento lingüístico con spaCy
    documento = nlp(texto)

    tokens_limpios = []

    for token in documento:

        # ignorar espacios
        if token.is_space:
            continue

        # ignorar signos de puntuación
        if token.is_punct:
            continue

        # eliminar stopwords
        if token.is_stop:
            continue

        # obtener lema
        lema = token.lemma_.strip().lower()

        if not lema:
            continue

        tokens_limpios.append(lema)

    # 7. reconstruir el texto
    texto_procesado = " ".join(tokens_limpios)

    return texto_procesado


if __name__ == "__main__":

    texto_prueba = (
        "Juan Pérez fue asaltado en la zona 1. "
        "Los delincuentes estaban robando teléfonos "
        "y huyeron rápidamente!!! 😨"
    )

    resultado = preprocesar_texto(texto_prueba)

    print("\nTEXTO ORIGINAL:")
    print(texto_prueba)

    print("\nTEXTO PROCESADO:")
    print(resultado)