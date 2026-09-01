import json
import re
import unicodedata
from pathlib import Path


BASE_DIR = Path(__file__).resolve().parent.parent

RUTA_UBICACIONES = (
    BASE_DIR / "config" / "ubicaciones.json"
)


def cargar_ubicaciones():

    with open(
        RUTA_UBICACIONES,
        "r",
        encoding="utf-8"
    ) as archivo:

        return json.load(archivo)


def normalizar_texto(texto):

    if not texto:
        return ""

    texto = texto.lower()

    # quitar tildes
    texto = unicodedata.normalize(
        "NFD",
        texto
    )

    texto = "".join(
        caracter
        for caracter in texto
        if unicodedata.category(caracter) != "Mn"
    )

    return texto


def extraer_coordenadas(texto):

    """
    Busca coordenadas explícitas dentro del texto.

    Ejemplo:
    14.6416, -90.5133
    """

    if not texto:
        return None

    patron = (
        r"(-?\d{1,2}(?:\.\d+)?)"
        r"\s*[,;]\s*"
        r"(-?\d{1,3}(?:\.\d+)?)"
    )

    coincidencia = re.search(
        patron,
        texto
    )

    if not coincidencia:
        return None

    latitud = float(
        coincidencia.group(1)
    )

    longitud = float(
        coincidencia.group(2)
    )

    # validar coordenadas
    if not (-90 <= latitud <= 90):
        return None

    if not (-180 <= longitud <= 180):
        return None

    return {
        "nombre": "Coordenadas explícitas",
        "latitud": latitud,
        "longitud": longitud,
        "metodo": "coordenadas_explicitas"
    }


def buscar_ubicacion(
    texto,
    referencia_espacial=None
):

    # =====================================================
    # 1. BUSCAR COORDENADAS EXPLÍCITAS
    # =====================================================

    coordenadas = extraer_coordenadas(
        texto
    )

    if coordenadas:
        return coordenadas

    # =====================================================
    # 2. CARGAR CATÁLOGO LOCAL
    # =====================================================

    ubicaciones = cargar_ubicaciones()

    # primero usamos referencia_espacial porque
    # es más específica que todo el texto
    contenido = ""

    if referencia_espacial:
        contenido += referencia_espacial + " "

    if texto:
        contenido += texto

    contenido = normalizar_texto(
        contenido
    )

    # =====================================================
    # 3. BUSCAR UBICACIONES CONOCIDAS
    # =====================================================

    # ordenar desde nombres más largos
    # para encontrar primero referencias específicas
    claves = sorted(
        ubicaciones.keys(),
        key=len,
        reverse=True
    )

    for clave in claves:

        clave_normalizada = normalizar_texto(
            clave
        )

        if clave_normalizada in contenido:

            datos = ubicaciones[clave]

            return {
                "nombre": datos["nombre"],
                "latitud": datos["latitud"],
                "longitud": datos["longitud"],
                "metodo": "catalogo_local"
            }

    return None


if __name__ == "__main__":

    texto_prueba = (
        "Reportan un incidente en "
        "14.6205, -90.5312"
    )

    resultado = buscar_ubicacion(
        texto_prueba
    )

    print("\nTEXTO:")
    print(texto_prueba)

    print("\nRESULTADO:")

    if resultado:

        print(
            f"Ubicación: "
            f"{resultado['nombre']}"
        )

        print(
            f"Latitud: "
            f"{resultado['latitud']}"
        )

        print(
            f"Longitud: "
            f"{resultado['longitud']}"
        )

        print(
            f"Método: "
            f"{resultado['metodo']}"
        )

    else:

        print(
            "No se encontró ubicación."
        )