"""Extractor de publicaciones públicas de Facebook.

Dos modos:
- buscar_publicaciones: búsqueda de publicaciones públicas por palabras
  clave. Facebook solo la permite con sesión iniciada
  (python extraccion/iniciar_sesion.py facebook).
- extraer_de_fuente: recorre una página o grupo PÚBLICO indicado por URL.

Nunca se accede a grupos cerrados ni a perfiles privados.

Facebook oculta el enlace permanente y la fecha de cada publicación
hasta que el cursor pasa sobre la hora visible; el extractor simula ese
paso y lee el enlace y la fecha completa del cuadro emergente.
"""

import re
import time
from datetime import datetime, timedelta
from urllib.parse import parse_qs, quote, urlparse

from selenium.webdriver.common.action_chains import ActionChains
from selenium.webdriver.common.by import By

from navegador import desplazar

PLATAFORMA = "Facebook"

MESES = {
    "enero": 1, "febrero": 2, "marzo": 3, "abril": 4, "mayo": 5, "junio": 6,
    "julio": 7, "agosto": 8, "septiembre": 9, "setiembre": 9, "octubre": 10,
    "noviembre": 11, "diciembre": 12,
    "ene": 1, "feb": 2, "mar": 3, "abr": 4, "may": 5, "jun": 6, "jul": 7,
    "ago": 8, "sep": 9, "sept": 9, "oct": 10, "nov": 11, "dic": 12,
    "january": 1, "february": 2, "march": 3, "april": 4, "june": 6,
    "july": 7, "august": 8, "september": 9, "october": 10, "november": 11,
    "december": 12,
}

# "25 de noviembre de 2026 a las 19:58"
PATRON_FECHA_ES = re.compile(
    r"(\d{1,2}) de ([a-záéíóú]+)\.?(?: de (\d{4}))?(?: a las? (\d{1,2}):(\d{2}))?",
    re.IGNORECASE,
)
# "November 25, 2026 at 7:58 PM"
PATRON_FECHA_EN = re.compile(
    r"([a-z]+) (\d{1,2}),? (\d{4})(?: at (\d{1,2}):(\d{2})\s*(am|pm)?)?",
    re.IGNORECASE,
)
PATRON_RELATIVA = re.compile(r"^(\d+)\s*(min|h|d|sem|w)\b", re.IGNORECASE)

SELECTOR_TEXTO = (
    '[data-ad-rendering-role="story_message"], '
    '[data-ad-comet-preview="message"], '
    '[data-ad-preview="message"]'
)
SELECTOR_AUTOR = '[data-ad-rendering-role="profile_name"]'
SELECTOR_ENLACE = (
    'a[href*="#?"], a[href*="story_fbid"], a[href*="/posts/"], '
    'a[href*="/permalink/"], a[href*="/videos/"], a[href*="/reel/"]'
)
TEXTOS_VER_MAS = ("ver más", "see more")


class SesionRequerida(Exception):
    """La plataforma pide iniciar sesión; no se intenta evadirlo."""


def construir_url_busqueda(consulta):
    # El filtro pide "publicaciones recientes".
    return (
        f"https://www.facebook.com/search/posts?q={quote(consulta)}"
        "&filters=eyJyZWNlbnRfcG9zdHM6MCI6IntcIm5hbWVcIjpcInJlY2VudF9wb3N0c1wiLFwiYXJnc1wiOlwiXCJ9In0%3D"
    )


def pide_sesion(driver):
    url = driver.current_url.lower()
    if "/login" in url or "checkpoint" in url:
        return True
    formulario = driver.find_elements(By.CSS_SELECTOR, 'form[action*="/login"] input[name="pass"]')
    return bool(formulario) and not driver.find_elements(By.CSS_SELECTOR, '[role="feed"], [role="article"]')


# =========================================================
# FECHAS
# =========================================================

def _hora_24(hora, minuto, sufijo):
    hora, minuto = int(hora or 0), int(minuto or 0)
    if sufijo:
        sufijo = sufijo.lower()
        if sufijo == "pm" and hora < 12:
            hora += 12
        if sufijo == "am" and hora == 12:
            hora = 0
    return hora, minuto


def interpretar_fecha(texto, ahora=None):
    """Convierte una fecha visible de Facebook (español o inglés) a ISO 8601.

    Devuelve None si no reconoce ninguna fecha en el texto.
    """
    ahora = ahora or datetime.now()

    for linea in (texto or "").replace(" ", " ").splitlines():
        linea = linea.strip().lower()

        relativa = PATRON_RELATIVA.match(linea)
        if relativa:
            cantidad, unidad = int(relativa.group(1)), relativa.group(2).lower()
            delta = {
                "min": timedelta(minutes=cantidad),
                "h": timedelta(hours=cantidad),
                "d": timedelta(days=cantidad),
                "sem": timedelta(weeks=cantidad),
                "w": timedelta(weeks=cantidad),
            }[unidad]
            return (ahora - delta).strftime("%Y-%m-%dT%H:%M:%S")

        candidatos = []
        coincidencia = PATRON_FECHA_EN.search(linea)
        if coincidencia and coincidencia.group(1) in MESES:
            mes, dia, anio = MESES[coincidencia.group(1)], coincidencia.group(2), coincidencia.group(3)
            hora, minuto = _hora_24(*coincidencia.group(4, 5, 6))
            candidatos.append((int(anio), mes, int(dia), hora, minuto, True))

        coincidencia = PATRON_FECHA_ES.search(linea)
        if coincidencia and coincidencia.group(2).rstrip(".") in MESES:
            anio_explicito = coincidencia.group(3) is not None
            hora, minuto = _hora_24(coincidencia.group(4), coincidencia.group(5), None)
            candidatos.append((
                int(coincidencia.group(3) or ahora.year),
                MESES[coincidencia.group(2).rstrip(".")],
                int(coincidencia.group(1)),
                hora,
                minuto,
                anio_explicito,
            ))

        for anio, mes, dia, hora, minuto, anio_explicito in candidatos:
            try:
                fecha = datetime(anio, mes, dia, hora, minuto)
            except ValueError:
                continue
            if not anio_explicito and fecha > ahora:
                fecha = fecha.replace(year=anio - 1)
            return fecha.strftime("%Y-%m-%dT%H:%M:%S")

    return None


# =========================================================
# PUBLICACIONES
# =========================================================

def identificar_publicacion(href):
    """Obtiene (id, url limpia) a partir del enlace permanente."""
    partes = urlparse(href or "")
    parametros = parse_qs(partes.query)

    if "story_fbid" in parametros:
        id_publicacion = parametros["story_fbid"][0]
        autor = parametros.get("id", [""])[0]
        url = f"https://www.facebook.com/permalink.php?story_fbid={id_publicacion}&id={autor}"
        return id_publicacion, url

    coincidencia = re.search(r"/(?:posts|permalink|videos|reel)/([\w.-]+)", partes.path)
    if coincidencia:
        return coincidencia.group(1), f"https://www.facebook.com{partes.path}"

    return None, None


def revelar_enlace(driver, publicacion):
    """Pasa el cursor sobre la hora para obtener enlace permanente y fecha."""
    for enlace in publicacion.find_elements(By.CSS_SELECTOR, SELECTOR_ENLACE):
        id_publicacion, url = identificar_publicacion(enlace.get_attribute("href"))
        tooltip = ""
        if not id_publicacion:
            try:
                driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", enlace)
                time.sleep(0.4)
                ActionChains(driver).move_to_element(enlace).perform()
                time.sleep(1.2)
            except Exception:
                continue
            id_publicacion, url = identificar_publicacion(enlace.get_attribute("href"))
            tooltip = " ".join(
                t.text for t in driver.find_elements(By.CSS_SELECTOR, '[role="tooltip"]')
            )
        if id_publicacion:
            return id_publicacion, url, interpretar_fecha(tooltip)
    return None, None, None


def expandir_texto(driver, publicacion):
    for boton in publicacion.find_elements(By.CSS_SELECTOR, 'div[role="button"]'):
        if boton.text.strip().lower() in TEXTOS_VER_MAS:
            try:
                driver.execute_script("arguments[0].click();", boton)
                time.sleep(0.8)
            except Exception:
                pass
            return


def extraer_publicacion(driver, publicacion):
    bloques = publicacion.find_elements(By.CSS_SELECTOR, SELECTOR_TEXTO)
    if not bloques:
        # Publicaciones solo con imagen o video: fuera del alcance.
        return None

    expandir_texto(driver, publicacion)
    bloques = publicacion.find_elements(By.CSS_SELECTOR, SELECTOR_TEXTO) or bloques
    texto = re.sub(r"…?\s*(see more|ver más)$", "", bloques[0].text.strip(), flags=re.IGNORECASE)
    if not texto:
        return None

    id_publicacion, url, fecha = revelar_enlace(driver, publicacion)
    if not id_publicacion:
        return None

    autores = publicacion.find_elements(By.CSS_SELECTOR, SELECTOR_AUTOR)
    usuario = autores[0].text.strip().splitlines()[0] if autores and autores[0].text.strip() else None

    if not fecha:
        fecha = interpretar_fecha(publicacion.text.split(texto[:40])[0])
    if not fecha:
        # Sin fecha visible se usa el momento de la extracción.
        fecha = datetime.now().strftime("%Y-%m-%dT%H:%M:%S")

    return {
        "id_publicacion_plataforma": id_publicacion,
        "plataforma": PLATAFORMA,
        "usuario_publico": usuario,
        "texto": texto,
        "fecha": fecha,
        "url": url,
    }


# Sube desde cada texto de publicación hasta el contenedor más amplio
# que solo incluye esa publicación (las páginas no usan role="feed").
JS_CONTENEDORES = """
const selector = arguments[0];
// Un mismo texto puede tener dos marcas anidadas; solo cuenta la exterior.
const exteriores = [...document.querySelectorAll(selector)]
    .filter(e => !e.parentElement || !e.parentElement.closest(selector));
const cuantos = n => exteriores.filter(e => n.contains(e)).length;
const vistos = new Set();
const resultado = [];
for (const mensaje of exteriores) {
    let nodo = mensaje;
    while (nodo.parentElement && cuantos(nodo.parentElement) === 1
           && nodo.parentElement.tagName !== 'BODY') {
        nodo = nodo.parentElement;
    }
    if (!vistos.has(nodo)) { vistos.add(nodo); resultado.push(nodo); }
}
return resultado;
"""


def contenedores(driver):
    """Publicaciones visibles en grupos, búsquedas y páginas."""
    hijos = driver.find_elements(By.CSS_SELECTOR, '[role="feed"] > div')
    if hijos:
        return hijos
    return driver.execute_script(JS_CONTENEDORES, SELECTOR_TEXTO)


def recorrer_publicaciones(driver, limite, pausa_scroll=6):
    publicaciones = {}
    revisados = 0
    vueltas_sin_nuevas = 0

    while len(publicaciones) < limite and vueltas_sin_nuevas < 3:
        antes = len(publicaciones)
        visibles = contenedores(driver)

        for contenedor in visibles[revisados:]:
            revisados += 1
            try:
                publicacion = extraer_publicacion(driver, contenedor)
            except Exception:
                continue
            if publicacion:
                publicaciones.setdefault(publicacion["id_publicacion_plataforma"], publicacion)
            if len(publicaciones) >= limite:
                break

        vueltas_sin_nuevas = vueltas_sin_nuevas + 1 if len(publicaciones) == antes else 0

        if len(publicaciones) < limite:
            desplazar(driver)
            time.sleep(pausa_scroll)
            # Facebook descarta del DOM publicaciones ya vistas; se recuenta.
            revisados = min(revisados, len(contenedores(driver)))

    return list(publicaciones.values())


def buscar_publicaciones(driver, consulta, limite=15):
    driver.get(construir_url_busqueda(consulta))
    time.sleep(7)

    cuerpo = driver.find_element(By.TAG_NAME, "body").text[:40].lower()
    if pide_sesion(driver) or "not found" in cuerpo:
        raise SesionRequerida("Facebook pide iniciar sesión para buscar publicaciones")

    return recorrer_publicaciones(driver, limite)


def extraer_de_fuente(driver, url_fuente, limite=15):
    driver.get(url_fuente)
    time.sleep(7)

    if pide_sesion(driver):
        raise SesionRequerida(f"Facebook pide iniciar sesión para ver {url_fuente}")

    return recorrer_publicaciones(driver, limite)
