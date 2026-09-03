import json
import re
import unicodedata
from pathlib import Path

from geopy.geocoders import Nominatim
from geopy.extra.rate_limiter import RateLimiter


BASE_DIR = Path(__file__).resolve().parent.parent

RUTA_UBICACIONES = (
    BASE_DIR / "config" / "ubicaciones.json"
)


# =========================================================
# GEOCODIFICADOR
# =========================================================

geolocalizador = Nominatim(
    user_agent="tesis_cifra_negra_usac_2026"
)

geocodificar = RateLimiter(
    geolocalizador.geocode,
    min_delay_seconds=1,
    max_retries=2,
    error_wait_seconds=2,
    swallow_exceptions=True
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


# =========================================================
# COORDENADAS EXPLÍCITAS
# =========================================================

def extraer_coordenadas(texto):

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


# =========================================================
# EXTRAER REFERENCIAS DEL TEXTO
# =========================================================

def extraer_referencia_textual(texto):

    if not texto:
        return None

    # -----------------------------------------
    # Buscar zonas
    # -----------------------------------------

    zona = re.search(
        r"\bzona\s+\d{1,2}\b",
        texto,
        re.IGNORECASE
    )

    if zona:
        return zona.group(0)


    # -----------------------------------------
    # Buscar calles, colonias, avenidas, etc.
    # -----------------------------------------

    patron = (
        r"\b"
        r"(?:"
        r"calzada|"
        r"avenida|"
        r"colonia|"
        r"bulevar|"
        r"boulevard|"
        r"carretera|"
        r"calle"
        r")"
        r"\s+"
        r"[A-Za-zÁÉÍÓÚÑáéíóúñ0-9]+"
        r"(?:\s+[A-Za-zÁÉÍÓÚÑáéíóúñ0-9]+){0,3}"
    )

    coincidencia = re.search(
        patron,
        texto,
        re.IGNORECASE
    )

    if not coincidencia:
        return None

    candidato = coincidencia.group(0)

    # palabras que indican que la ubicación
    # probablemente ya terminó
    palabras_corte = {
        "cerca",
        "donde",
        "cuando",
        "reportan",
        "reportaron",
        "ocurrio",
        "ocurrió",
        "hubo",
        "tengan",
        "zona"
    }

    palabras = candidato.split()

    resultado = []

    for palabra in palabras:

        if (
            resultado
            and normalizar_texto(palabra)
            in palabras_corte
        ):
            break

        resultado.append(
            palabra
        )

    if len(resultado) < 2:
        return None

    return " ".join(resultado)


# =========================================================
# VALIDAR ÁREA METROPOLITANA
# =========================================================

def dentro_area_metropolitana(
    latitud,
    longitud
):

    return (
        14.40 <= latitud <= 14.80
        and
        -90.80 <= longitud <= -90.30
    )


# =========================================================
# GEOCODIFICACIÓN EXTERNA
# =========================================================

def geocodificar_referencia(
    referencia
):

    if not referencia:
        return None

    consulta = (
        f"{referencia}, Guatemala, Guatemala"
    )

    try:

        ubicacion = geocodificar(
            consulta,
            exactly_one=True,
            country_codes="gt",
            language="es",
            timeout=10,
            viewbox=[
                (14.80, -90.80),
                (14.40, -90.30)
            ],
            bounded=True
        )

    except Exception as error:

        print(
            f"Error de geocodificación: "
            f"{error}"
        )

        return None


    if not ubicacion:
        return None


    latitud = float(
        ubicacion.latitude
    )

    longitud = float(
        ubicacion.longitude
    )


    if not dentro_area_metropolitana(
        latitud,
        longitud
    ):
        return None


    return {
        "nombre": ubicacion.address,
        "latitud": latitud,
        "longitud": longitud,
        "metodo": "geocodificacion_nominatim",
        "referencia": referencia
    }


# =========================================================
# FUNCIÓN PRINCIPAL
# =========================================================

def buscar_ubicacion(
    texto,
    referencia_espacial=None
):

    # =====================================================
    # 1. COORDENADAS EXPLÍCITAS
    # =====================================================

    coordenadas = extraer_coordenadas(
        texto
    )

    if coordenadas:
        return coordenadas


    # =====================================================
    # 2. CATÁLOGO LOCAL
    # =====================================================

    ubicaciones = cargar_ubicaciones()

    contenido = ""

    if referencia_espacial:
        contenido += (
            referencia_espacial
            + " "
        )

    if texto:
        contenido += texto

    contenido_normalizado = normalizar_texto(
        contenido
    )


    claves = sorted(
        ubicaciones.keys(),
        key=len,
        reverse=True
    )


    for clave in claves:

        clave_normalizada = normalizar_texto(
            clave
        )

        if clave_normalizada in contenido_normalizado:

            datos = ubicaciones[
                clave
            ]

            return {
                "nombre": datos["nombre"],
                "latitud": datos["latitud"],
                "longitud": datos["longitud"],
                "metodo": "catalogo_local"
            }


    # =====================================================
    # 3. OBTENER REFERENCIA PARA GEOCODIFICACIÓN
    # =====================================================

    if referencia_espacial:

        referencia = referencia_espacial

    else:

        referencia = extraer_referencia_textual(
            texto
        )


    if not referencia:
        return None


    # =====================================================
    # 4. GEOCODIFICACIÓN AUTOMÁTICA
    # =====================================================

    return geocodificar_referencia(
        referencia
    )


# =========================================================
# PRUEBA
# =========================================================

if __name__ == "__main__":

    texto_prueba = (
        "Vecinos reportan un asalto "
        "en la colonia El Milagro."
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