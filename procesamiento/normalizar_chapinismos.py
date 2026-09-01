import json
from pathlib import Path

from preprocesar import preprocesar_texto


BASE_DIR = Path(__file__).resolve().parent.parent
RUTA_DICCIONARIO = BASE_DIR / "config" / "chapinismos.json"


def cargar_diccionario():

    with open(
        RUTA_DICCIONARIO,
        "r",
        encoding="utf-8"
    ) as archivo:

        return json.load(archivo)


def normalizar_chapinismos(texto):

    if not texto:
        return ""

    diccionario = cargar_diccionario()

    palabras = texto.split()

    palabras_normalizadas = []

    for palabra in palabras:

        if palabra in diccionario:
            palabras_normalizadas.append(
                diccionario[palabra]
            )
        else:
            palabras_normalizadas.append(
                palabra
            )

    return " ".join(palabras_normalizadas)


if __name__ == "__main__":

    texto_prueba = (
        "Mucha, unos cacos estaban cobrando renta "
        "y uno llevaba un cuete en la zona 1."
    )

    texto_procesado = preprocesar_texto(
        texto_prueba
    )

    resultado = normalizar_chapinismos(
        texto_procesado
    )

    print("\nTEXTO ORIGINAL:")
    print(texto_prueba)

    print("\nDESPUÉS DEL PREPROCESAMIENTO:")
    print(texto_procesado)

    print("\nDESPUÉS DE NORMALIZAR CHAPINISMOS:")
    print(resultado)