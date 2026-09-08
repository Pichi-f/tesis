import json
import re
import unicodedata
from pathlib import Path
from functools import lru_cache

from geopy.geocoders import Nominatim
from geopy.extra.rate_limiter import RateLimiter


BASE_DIR = Path(__file__).resolve().parent.parent

RUTA_UBICACIONES = (
    BASE_DIR / "config" / "ubicaciones.json"
)

RUTA_CACHE = (
    BASE_DIR / "data" / "cache_geocodificacion.json"
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


@lru_cache(maxsize=1)
def cargar_ubicaciones():

    with open(
        RUTA_UBICACIONES,
        "r",
        encoding="utf-8"
    ) as archivo:

        return json.load(archivo)
    
    
def cargar_cache():

    if not RUTA_CACHE.exists():
        return {}

    try:

        with open(
            RUTA_CACHE,
            "r",
            encoding="utf-8"
        ) as archivo:

            return json.load(archivo)

    except (
        json.JSONDecodeError,
        OSError
    ):

        return {}


def guardar_cache(cache):

    with open(
        RUTA_CACHE,
        "w",
        encoding="utf-8"
    ) as archivo:

        json.dump(
            cache,
            archivo,
            ensure_ascii=False,
            indent=4
        )


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


def determinar_precision(
    referencia,
    metodo
):

    # Coordenadas directas:
    # máxima precisión disponible
    if metodo == "coordenadas_explicitas":
        return "alta"

    if not referencia:
        return "baja"

    referencia_normalizada = normalizar_texto(
        referencia
    )

    # Colonias, zonas y municipios
    # son referencias relativamente acotadas
    if "colonia" in referencia_normalizada:
        return "media"

    if re.search(
        r"\bzona\s+\d{1,2}\b",
        referencia_normalizada
    ):
        return "media"

    municipios = [
        "mixco",
        "villa nueva",
        "san miguel petapa",
        "guatemala",
        "santa catarina pinula",
        "villa canales"
    ]

    for municipio in municipios:

        if municipio in referencia_normalizada:
            return "media"

    # Vías extensas:
    # una coordenada representa solamente
    # un punto aproximado de la vía
    vias = [
        "calzada",
        "avenida",
        "carretera",
        "bulevar",
        "boulevard",
        "calle"
    ]

    for via in vias:

        if via in referencia_normalizada:
            return "baja"

    return "baja"


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
        "metodo": "coordenadas_explicitas",
        "precision": "alta"
    }


# =========================================================
# EXTRAER REFERENCIAS DEL TEXTO
# =========================================================

def extraer_referencia_textual(texto):

    if not texto:
        return None

    # ==========================================
    # BUSCAR ZONA
    # ==========================================

    coincidencia_zona = re.search(
        r"\bzona\s+\d{1,2}\b",
        texto,
        re.IGNORECASE
    )

    zona = None

    if coincidencia_zona:
        zona = coincidencia_zona.group(0)


    # ==========================================
    # BUSCAR VÍA O COLONIA
    # ==========================================

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

    referencia = None

    if coincidencia:

        candidato = coincidencia.group(0)

        palabras_corte = {
            "cerca",
            "donde",
            "cuando",
            "reportan",
            "reportaron",
            "ocurrio",
            "ocurrió",
            "hubo",
            "tengan"
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

        if len(resultado) >= 2:
            referencia = " ".join(resultado)


    # ==========================================
    # COMBINAR REFERENCIA + ZONA
    # ==========================================

    if referencia and zona:

        if normalizar_texto(zona) not in normalizar_texto(
            referencia
        ):

            return (
                f"{referencia}, {zona}"
            )


    if referencia:
        return referencia


    if zona:
        return zona


    return None


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


    # ==========================================
    # 1. REVISAR CACHÉ
    # ==========================================

    cache = cargar_cache()

    clave_cache = normalizar_texto(
        referencia
    ).strip()


    if clave_cache in cache:

        datos = cache[
            clave_cache
        ]

        precision = datos.get(
            "precision"
        )

        if not precision:

            precision = determinar_precision(
                referencia,
                "cache_geocodificacion"
            )

        return {
            "nombre": datos["nombre"],
            "latitud": datos["latitud"],
            "longitud": datos["longitud"],
            "metodo": "cache_geocodificacion",
            "referencia": referencia,
            "precision": precision
        }


    # ==========================================
    # 2. CONSULTAR NOMINATIM
    # ==========================================

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


    # ==========================================
    # CALCULAR NIVEL DE PRECISIÓN
    # ==========================================

    precision = determinar_precision(
        referencia,
        "geocodificacion_nominatim"
    )


    # ==========================================
    # 3. GUARDAR RESULTADO EN CACHÉ
    # ==========================================

    cache[clave_cache] = {

        "nombre": ubicacion.address,

        "latitud": latitud,

        "longitud": longitud,

        "precision": precision
    }


    guardar_cache(
        cache
    )


    return {

        "nombre": ubicacion.address,

        "latitud": latitud,

        "longitud": longitud,

        "metodo": "geocodificacion_nominatim",

        "referencia": referencia,

        "precision": precision
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
                "metodo": "catalogo_local",
                "precision": determinar_precision(
                    clave,
                    "catalogo_local"
                )
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
        "Reportan un asalto en la "
        "Calzada Roosevelt zona 7."
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
        
        print(
            f"Precisión: "
            f"{resultado['precision']}"
        )

    else:

        print(
            "No se encontró ubicación."
        )