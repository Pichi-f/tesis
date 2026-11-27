"""Geolocalización de reportes dentro del Área Metropolitana de Guatemala.

buscar_ubicacion(texto) devuelve la mejor ubicación disponible o None.
Orden de búsqueda, de lo más específico a lo más general:

1. Coordenadas explícitas en el texto.
2. Calle, avenida o colonia mencionada -> caché / Nominatim.
3. Lugar conocido del catálogo local (config/ubicaciones.json).
4. Zona del municipio mencionado (catálogo local).
5. Municipio del área de estudio (precisión baja).

Si el texto menciona un lugar fuera del área de estudio
(config/area_estudio.json) no se asigna ubicación.
"""

import json
import re
import unicodedata
from functools import lru_cache
from pathlib import Path

from geopy.extra.rate_limiter import RateLimiter
from geopy.geocoders import Nominatim

BASE_DIR = Path(__file__).resolve().parent.parent
RUTA_UBICACIONES = BASE_DIR / "config" / "ubicaciones.json"
RUTA_AREA = BASE_DIR / "config" / "area_estudio.json"
RUTA_CACHE = BASE_DIR / "data" / "cache_geocodificacion.json"

# Recuadro del Área Metropolitana: (lat mín, lat máx, lon mín, lon máx)
LAT_MIN, LAT_MAX, LON_MIN, LON_MAX = 14.40, 14.80, -90.80, -90.30

MUNICIPIO_POR_DEFECTO = "ciudad de guatemala"
NOMBRES_MUNICIPIO = {
    "ciudad de guatemala": "Ciudad de Guatemala",
    "mixco": "Mixco",
    "villa nueva": "Villa Nueva",
    "san miguel petapa": "San Miguel Petapa",
}

VIAS = ("calzada", "avenida", "carretera", "bulevar", "boulevard", "calle", "periferico")

geolocalizador = Nominatim(user_agent="tesis_cifra_negra_usac_2026")
geocodificar = RateLimiter(
    geolocalizador.geocode,
    min_delay_seconds=1,
    max_retries=2,
    error_wait_seconds=2,
    swallow_exceptions=True,
)


def normalizar_texto(texto):
    texto = unicodedata.normalize("NFD", (texto or "").lower())
    texto = "".join(c for c in texto if unicodedata.category(c) != "Mn")
    return re.sub(r"\s+", " ", texto).strip()


def contiene(frase, contenido):
    """Coincidencia por palabra completa: 'zona 1' no coincide con 'zona 18'."""
    return re.search(rf"(?<!\w){re.escape(frase)}(?!\w)", contenido) is not None


@lru_cache(maxsize=1)
def cargar_ubicaciones():
    with open(RUTA_UBICACIONES, "r", encoding="utf-8") as archivo:
        return {normalizar_texto(k): v for k, v in json.load(archivo).items()}


@lru_cache(maxsize=1)
def cargar_area():
    with open(RUTA_AREA, "r", encoding="utf-8") as archivo:
        return json.load(archivo)


def cargar_cache():
    if not RUTA_CACHE.exists():
        return {}
    try:
        with open(RUTA_CACHE, "r", encoding="utf-8") as archivo:
            return json.load(archivo)
    except json.JSONDecodeError:
        return {}


def guardar_cache(cache):
    with open(RUTA_CACHE, "w", encoding="utf-8") as archivo:
        json.dump(cache, archivo, ensure_ascii=False, indent=4)


def dentro_area_metropolitana(latitud, longitud):
    return LAT_MIN <= latitud <= LAT_MAX and LON_MIN <= longitud <= LON_MAX


# =========================================================
# ANÁLISIS DEL TEXTO
# =========================================================

def lugar_fuera_del_area(contenido):
    """Devuelve el lugar ajeno al área de estudio que menciona el texto."""
    area = cargar_area()
    for lugar in area["departamentos_fuera_area"] + area.get("lugares_fuera_area", []):
        if contiene(normalizar_texto(lugar), contenido):
            return lugar
    return None


def detectar_municipio(contenido):
    """Municipio mencionado de forma explícita, o None."""
    if contiene("mixco", contenido):
        return "mixco"
    if contiene("villa nueva", contenido):
        return "villa nueva"
    # "Avenida Petapa" está en la Ciudad de Guatemala, no en San Miguel Petapa.
    if re.search(r"(?<!avenida )(?<!av )(?<!av\. )(?<!\w)petapa(?!\w)", contenido):
        return "san miguel petapa"
    if re.search(r"ciudad de guatemala|ciudad capital|la capital|guatemala city", contenido):
        return "ciudad de guatemala"
    return None


def extraer_zona(contenido):
    coincidencia = re.search(r"(?<!\w)z(?:ona)?\.?\s?(\d{1,2})(?!\w)", contenido)
    return int(coincidencia.group(1)) if coincidencia else None


def extraer_coordenadas(texto):
    """Solo acepta pares decimales que caen dentro del área de estudio."""
    for coincidencia in re.finditer(
        r"(-?\d{1,2}\.\d{3,})\s*[,;]\s*(-?\d{1,3}\.\d{3,})", texto or ""
    ):
        latitud, longitud = float(coincidencia.group(1)), float(coincidencia.group(2))
        if dentro_area_metropolitana(latitud, longitud):
            return {
                "nombre": "Coordenadas explícitas",
                "latitud": latitud,
                "longitud": longitud,
                "metodo": "coordenadas_explicitas",
                "precision": "alta",
            }
    return None


PALABRA = r"[a-z0-9ñªº]+"
PALABRAS_CORTE = {
    "zona", "z", "cerca", "donde", "cuando", "reportan", "reportaron", "ocurrio",
    "hubo", "tengan", "de", "del", "en", "y", "a", "que", "por", "para", "con",
    "me", "nos", "le", "se", "frente", "anda", "andan", "hoy", "ayer", "ciudad",
}
PATRONES_VIA = [
    rf"(?<!\w)\d{{1,2}}a?\.? (?:calle|avenida|av)(?: [a-d](?!\w))?(?: y \d{{1,2}}a?\.? (?:calle|avenida|av))?",
    rf"(?<!\w)colonia {PALABRA}(?: {PALABRA}){{0,3}}",
    rf"(?<!\w)(?:calzada|avenida|bulevar|boulevard|carretera|calle) {PALABRA}(?: {PALABRA}){{0,3}}",
]


def extraer_via(contenido):
    """Calle, avenida o colonia mencionada en el texto normalizado."""
    for patron in PATRONES_VIA:
        coincidencia = re.search(patron, contenido)
        if not coincidencia:
            continue
        palabras = coincidencia.group(0).split()
        if palabras[0][0].isdigit():
            return " ".join(palabras)

        # Se corta el nombre al llegar a una palabra que ya no le pertenece.
        resultado = palabras[:2]
        for palabra in palabras[2:]:
            if palabra in PALABRAS_CORTE:
                break
            resultado.append(palabra)
        if resultado[1] not in PALABRAS_CORTE:
            return " ".join(resultado)
    return None


def buscar_lugar_catalogo(contenido):
    ubicaciones = cargar_ubicaciones()
    lugares = [k for k, v in ubicaciones.items() if v.get("tipo", "lugar") == "lugar"]
    for clave in sorted(lugares, key=len, reverse=True):
        if contiene(clave, contenido):
            return clave, ubicaciones[clave]
    return None, None


# =========================================================
# GEOCODIFICACIÓN EXTERNA (con caché)
# =========================================================

def geocodificar_referencia(referencia, municipio=MUNICIPIO_POR_DEFECTO):
    if not referencia:
        return None

    cache = cargar_cache()
    clave_cache = f"{normalizar_texto(referencia)} | {municipio}"

    if clave_cache in cache:
        datos = cache[clave_cache]
        if datos is None:
            return None
        return {**datos, "metodo": "cache_geocodificacion", "referencia": referencia}

    ubicacion = geocodificar(
        f"{referencia}, {NOMBRES_MUNICIPIO[municipio]}, Guatemala",
        exactly_one=True,
        country_codes="gt",
        language="es",
        timeout=10,
        viewbox=[(LAT_MAX, LON_MIN), (LAT_MIN, LON_MAX)],
        bounded=True,
    )

    datos = None
    if ubicacion and dentro_area_metropolitana(ubicacion.latitude, ubicacion.longitude):
        datos = {
            "nombre": ubicacion.address,
            "latitud": float(ubicacion.latitude),
            "longitud": float(ubicacion.longitude),
            "precision": "media",
        }

    # También se guarda el "no encontrado" para no repetir la consulta.
    cache[clave_cache] = datos
    guardar_cache(cache)

    if datos is None:
        return None
    return {**datos, "metodo": "geocodificacion_nominatim", "referencia": referencia}


# =========================================================
# FUNCIÓN PRINCIPAL
# =========================================================

def desde_catalogo(clave, datos, precision):
    return {
        "nombre": datos["nombre"],
        "latitud": datos["latitud"],
        "longitud": datos["longitud"],
        "metodo": "catalogo_local",
        "precision": precision,
        "referencia": clave,
        "municipio": datos.get("municipio"),
    }


def sector_de(resultado, contenido):
    """Zona y municipio del indicio para las estadísticas (RF-VIS-04).

    "Zona 18, Ciudad de Guatemala", "Mixco (sin zona)" o "Sin determinar"
    cuando la ubicación vino de coordenadas sin municipio mencionado.
    """
    municipio = resultado.get("municipio") or detectar_municipio(contenido)
    if not municipio:
        if resultado.get("metodo") == "coordenadas_explicitas":
            return "Sin determinar"
        municipio = MUNICIPIO_POR_DEFECTO
    nombre = NOMBRES_MUNICIPIO.get(municipio, municipio.title())
    zona = extraer_zona(contenido)
    clave = f"zona {zona}" if municipio == "ciudad de guatemala" else f"zona {zona} {municipio}"
    if zona is not None and clave in cargar_ubicaciones():
        return f"Zona {zona}, {nombre}"
    return f"{nombre} (sin zona)"


def buscar_ubicacion(texto, referencia_espacial=None, usar_red=True):
    resultado = ubicar(texto, referencia_espacial, usar_red)
    if resultado:
        crudo = " ".join(parte for parte in (referencia_espacial, texto) if parte)
        resultado["sector"] = sector_de(resultado, normalizar_texto(crudo))
    return resultado


def ubicar(texto, referencia_espacial=None, usar_red=True):
    crudo = " ".join(parte for parte in (referencia_espacial, texto) if parte)

    coordenadas = extraer_coordenadas(crudo)
    if coordenadas:
        return coordenadas

    contenido = normalizar_texto(crudo)

    if lugar_fuera_del_area(contenido):
        return None

    ubicaciones = cargar_ubicaciones()
    municipio = detectar_municipio(contenido)
    municipio_busqueda = municipio or MUNICIPIO_POR_DEFECTO
    zona = extraer_zona(contenido)
    clave_zona = None
    if zona is not None:
        clave_zona = (
            f"zona {zona}"
            if municipio_busqueda == "ciudad de guatemala"
            else f"zona {zona} {municipio_busqueda}"
        )
        if clave_zona not in ubicaciones:
            clave_zona = None

    # Una vía o colonia solo se consulta si hay contexto local que la ancle.
    via = extraer_via(contenido)
    if via and usar_red and (clave_zona or municipio):
        referencia = f"{via}, zona {zona}" if clave_zona else via
        resultado = geocodificar_referencia(referencia, municipio_busqueda)
        if resultado:
            return resultado

    clave_lugar, lugar = buscar_lugar_catalogo(contenido)
    if lugar:
        precision = "baja" if clave_lugar.split()[0] in VIAS or "avenida" in clave_lugar else "media"
        return desde_catalogo(clave_lugar, lugar, precision)

    if clave_zona:
        return desde_catalogo(clave_zona, ubicaciones[clave_zona], "media")

    if municipio and municipio != "ciudad de guatemala":
        return desde_catalogo(municipio, ubicaciones[municipio], "baja")

    return None


if __name__ == "__main__":
    pruebas = [
        "Un intento de asalto se registró sobre la 11 calle y calzada Roosevelt, zona 7.",
        "Ataque armado en el redondel de la colonia El Limón, zona 18, dejó un herido.",
        "Balacera abajo de la iglesia en zona 3 de Santiago Sacatepéquez.",
        "Me asaltaron en la zona 6 de Mixco saliendo del trabajo.",
        "Me robaron el celular en la Avenida Petapa.",
        "Asaltaron una vivienda en la Villa Nueva Galilea de Curicó.",
        "En Guatemala nos asaltaron hace años.",
    ]
    for prueba in pruebas:
        resultado = buscar_ubicacion(prueba)
        print(f"\n{prueba}")
        if resultado:
            print(
                f"  -> {resultado['nombre'][:60]} | {resultado['metodo']} | "
                f"{resultado['precision']} | {resultado['latitud']:.4f}, {resultado['longitud']:.4f}"
                f" | {resultado['sector']}"
            )
        else:
            print("  -> sin ubicación")
