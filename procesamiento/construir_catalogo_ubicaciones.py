"""Construye config/ubicaciones.json con Nominatim (OpenStreetMap).

Se ejecuta una sola vez (o al agregar lugares). Geocodifica las zonas
de los cuatro municipios del área de estudio y una lista de colonias y
puntos de referencia frecuentes en los reportes. Solo se aceptan
resultados dentro del recuadro del Área Metropolitana.

Las entradas que ya existen en el archivo se conservan, de modo que
las correcciones hechas a mano no se pierden.
"""

import json
import time
from pathlib import Path

from geopy.geocoders import Nominatim

BASE_DIR = Path(__file__).resolve().parent.parent
RUTA = BASE_DIR / "config" / "ubicaciones.json"

RECUADRO = [(14.80, -90.80), (14.40, -90.30)]

ZONAS = {
    "ciudad de guatemala": (list(range(1, 20)) + [21, 24, 25], "Ciudad de Guatemala"),
    "mixco": (range(1, 12), "Mixco"),
    "villa nueva": (range(1, 13), "Villa Nueva"),
    "san miguel petapa": (range(1, 11), "San Miguel Petapa"),
}

# clave en el texto -> (consulta para Nominatim, municipio)
LUGARES = {
    "calzada roosevelt": ("Calzada Roosevelt, Ciudad de Guatemala", "ciudad de guatemala"),
    "calzada san juan": ("Calzada San Juan, Ciudad de Guatemala", "ciudad de guatemala"),
    "calzada aguilar batres": ("Calzada Aguilar Batres, Ciudad de Guatemala", "ciudad de guatemala"),
    "aguilar batres": ("Calzada Aguilar Batres, Ciudad de Guatemala", "ciudad de guatemala"),
    "calzada atanasio tzul": ("Calzada Atanasio Tzul, Ciudad de Guatemala", "ciudad de guatemala"),
    "atanasio": ("Calzada Atanasio Tzul, Ciudad de Guatemala", "ciudad de guatemala"),
    "avenida petapa": ("Avenida Petapa, Ciudad de Guatemala", "ciudad de guatemala"),
    "avenida bolivar": ("Avenida Bolívar, Ciudad de Guatemala", "ciudad de guatemala"),
    "avenida reforma": ("Avenida La Reforma, Ciudad de Guatemala", "ciudad de guatemala"),
    "avenida las americas": ("Avenida Las Américas, Ciudad de Guatemala", "ciudad de guatemala"),
    "avenida hincapie": ("Avenida Hincapié, Ciudad de Guatemala", "ciudad de guatemala"),
    "calle marti": ("Calle Martí, Ciudad de Guatemala", "ciudad de guatemala"),
    "anillo periferico": ("Anillo Periférico, Ciudad de Guatemala", "ciudad de guatemala"),
    "periferico": ("Anillo Periférico, Ciudad de Guatemala", "ciudad de guatemala"),
    "sexta avenida": ("6a Avenida, Zona 1, Ciudad de Guatemala", "ciudad de guatemala"),
    "parque central": ("Plaza de la Constitución, Ciudad de Guatemala", "ciudad de guatemala"),
    "centro historico": ("Centro Histórico, Ciudad de Guatemala", "ciudad de guatemala"),
    "la terminal": ("Mercado La Terminal, Ciudad de Guatemala", "ciudad de guatemala"),
    "el guarda": ("Mercado El Guarda, Ciudad de Guatemala", "ciudad de guatemala"),
    "la bethania": ("Colonia Bethania, Ciudad de Guatemala", "ciudad de guatemala"),
    "el limon": ("Colonia El Limón, Zona 18, Ciudad de Guatemala", "ciudad de guatemala"),
    "la florida": ("La Florida, Zona 19, Ciudad de Guatemala", "ciudad de guatemala"),
    "el gallito": ("Colonia El Gallito, Ciudad de Guatemala", "ciudad de guatemala"),
    "la reformita": ("La Reformita, Ciudad de Guatemala", "ciudad de guatemala"),
    "la parroquia": ("La Parroquia, Ciudad de Guatemala", "ciudad de guatemala"),
    "usac": ("Universidad de San Carlos de Guatemala, Zona 12", "ciudad de guatemala"),
    "paraiso 2": ("Colonia Paraíso II, Zona 18, Ciudad de Guatemala", "ciudad de guatemala"),
    "san rafael": ("San Rafael, Zona 18, Ciudad de Guatemala", "ciudad de guatemala"),
    "ciudad san cristobal": ("Ciudad San Cristóbal, Mixco", "mixco"),
    "el milagro": ("Colonia El Milagro, Mixco", "mixco"),
    "la brigada": ("La Brigada, Mixco", "mixco"),
    "primero de julio": ("Colonia Primero de Julio, Mixco", "mixco"),
    "lo de bran": ("Lo de Bran, Mixco", "mixco"),
    "lo de coy": ("Lo de Coy, Mixco", "mixco"),
    "montserrat": ("Montserrat, Mixco", "mixco"),
    "el naranjo": ("Bulevar El Naranjo, Mixco", "mixco"),
    "barcena": ("Bárcena, Villa Nueva", "villa nueva"),
    "barcenas": ("Bárcena, Villa Nueva", "villa nueva"),
    "el frutal": ("El Frutal, Villa Nueva", "villa nueva"),
    "villalobos": ("Villalobos, Villa Nueva", "villa nueva"),
    "mezquital": ("El Mezquital, Villa Nueva", "villa nueva"),
    "ciudad del sol": ("Ciudad del Sol, Villa Nueva", "villa nueva"),
    "linda vista": ("Linda Vista, Villa Nueva", "villa nueva"),
    "santa isabel": ("Santa Isabel II, Villa Nueva", "villa nueva"),
    "ciudad peronia": ("Ciudad Peronia, Villa Nueva", "villa nueva"),
    "peronia": ("Ciudad Peronia, Villa Nueva", "villa nueva"),
    "villa hermosa": ("Villa Hermosa, San Miguel Petapa", "san miguel petapa"),
    "prados de villa hermosa": ("Prados de Villa Hermosa, San Miguel Petapa", "san miguel petapa"),
}


def geocodificar(geolocalizador, consulta):
    time.sleep(1.1)
    resultado = geolocalizador.geocode(
        f"{consulta}, Guatemala",
        exactly_one=True,
        country_codes="gt",
        language="es",
        timeout=15,
        viewbox=RECUADRO,
        bounded=True,
    )
    if not resultado:
        return None
    return round(resultado.latitude, 6), round(resultado.longitude, 6), resultado.address


def construir():
    catalogo = json.loads(RUTA.read_text(encoding="utf-8")) if RUTA.exists() else {}
    geolocalizador = Nominatim(user_agent="modelo-geoespacial-academico")
    faltantes = []

    def agregar(clave, consulta, nombre, tipo, municipio):
        if clave in catalogo:
            catalogo[clave].setdefault("tipo", tipo)
            catalogo[clave].setdefault("municipio", municipio)
            return
        resultado = geocodificar(geolocalizador, consulta)
        if not resultado:
            faltantes.append(clave)
            return
        latitud, longitud, direccion = resultado
        catalogo[clave] = {
            "nombre": nombre or direccion.split(",")[0],
            "latitud": latitud,
            "longitud": longitud,
            "tipo": tipo,
            "municipio": municipio,
        }
        print(f"{clave:28s} {latitud:9.5f} {longitud:10.5f}  {direccion[:70]}")

    for municipio, (zonas, nombre_municipio) in ZONAS.items():
        agregar(municipio, nombre_municipio, nombre_municipio, "municipio", municipio)
        for zona in zonas:
            clave = f"zona {zona}" if municipio == "ciudad de guatemala" else f"zona {zona} {municipio}"
            agregar(
                clave,
                f"Zona {zona}, {nombre_municipio}",
                f"Zona {zona}, {nombre_municipio}",
                "zona",
                municipio,
            )

    for clave, (consulta, municipio) in LUGARES.items():
        agregar(clave, consulta, None, "lugar", municipio)

    RUTA.write_text(json.dumps(catalogo, ensure_ascii=False, indent=4), encoding="utf-8")
    print(f"\nEntradas en el catálogo: {len(catalogo)}")
    print(f"Sin resultado ({len(faltantes)}): {faltantes}")


if __name__ == "__main__":
    construir()
