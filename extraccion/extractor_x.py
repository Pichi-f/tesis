"""Extractor de publicaciones públicas de X mediante la búsqueda del sitio.

Requiere una sesión iniciada a mano en el perfil de Chrome de X
(python extraccion/iniciar_sesion.py x).
"""

import re
import time
from datetime import datetime, timezone
from urllib.parse import quote

from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait

from navegador import desplazar

PLATAFORMA = "X"

# Los identificadores de X (snowflake) llevan la fecha de creación
# en sus bits altos, contados en milisegundos desde esta época.
EPOCA_X_MS = 1288834974657

TEXTOS_VER_ORIGINAL = ("show original", "mostrar original", "ver original")


class SesionRequerida(Exception):
    """La plataforma pide iniciar sesión; no se intenta evadirlo."""


def construir_url_busqueda(consulta):
    return f"https://x.com/search?q={quote(consulta)}&src=typed_query&f=live"


def fecha_desde_id(id_publicacion):
    milisegundos = (int(id_publicacion) >> 22) + EPOCA_X_MS
    fecha = datetime.fromtimestamp(milisegundos / 1000, tz=timezone.utc)
    return fecha.strftime("%Y-%m-%dT%H:%M:%S.000Z")


def pide_sesion(driver):
    url = driver.current_url.lower()
    return "/login" in url or "/i/flow/" in url


def mostrar_texto_original(articulo):
    """X traduce automáticamente; se pide el texto original en español."""
    for boton in articulo.find_elements(By.CSS_SELECTOR, "button, [role='button']"):
        if boton.text.strip().lower() in TEXTOS_VER_ORIGINAL:
            try:
                boton.click()
                time.sleep(0.5)
            except Exception:
                pass
            return


# El cuerpo de la publicación es el primer bloque dir="auto" que no está
# dentro de un enlace (el nombre del autor y las menciones sí lo están).
JS_TEXTO = """
const bloques = [...arguments[0].querySelectorAll('div[dir="auto"]')]
    .filter(b => !b.closest('a') && !b.parentElement.closest('div[dir="auto"]'));
return bloques.length ? bloques[0].innerText : '';
"""


def leer_texto(articulo):
    texto = articulo.parent.execute_script(JS_TEXTO, articulo) or ""
    return texto.strip()


def extraer_publicacion(articulo):
    enlace = None
    for candidato in articulo.find_elements(By.CSS_SELECTOR, 'a[href*="/status/"]'):
        href = candidato.get_attribute("href") or ""
        if re.search(r"/status/\d+$", href):
            enlace = href
            break
    if not enlace:
        return None

    coincidencia = re.search(r"x\.com/([^/]+)/status/(\d+)", enlace)
    if not coincidencia:
        return None
    usuario, id_publicacion = coincidencia.groups()

    mostrar_texto_original(articulo)

    texto = leer_texto(articulo)
    if not texto:
        return None

    return {
        "id_publicacion_plataforma": id_publicacion,
        "plataforma": PLATAFORMA,
        "usuario_publico": f"@{usuario}",
        "texto": texto,
        "fecha": fecha_desde_id(id_publicacion),
        "url": enlace,
    }


def buscar_publicaciones(driver, consulta, limite=15, pausa_scroll=6):
    driver.get(construir_url_busqueda(consulta))
    time.sleep(6)

    if pide_sesion(driver):
        raise SesionRequerida("X pide iniciar sesión")

    try:
        WebDriverWait(driver, 15).until(
            EC.presence_of_element_located((By.TAG_NAME, "article"))
        )
    except Exception:
        return []

    publicaciones = {}
    vueltas_sin_nuevas = 0

    while len(publicaciones) < limite and vueltas_sin_nuevas < 3:
        antes = len(publicaciones)

        for articulo in driver.find_elements(By.TAG_NAME, "article"):
            try:
                publicacion = extraer_publicacion(articulo)
            except Exception:
                continue
            if publicacion:
                publicaciones.setdefault(
                    publicacion["id_publicacion_plataforma"], publicacion
                )
            if len(publicaciones) >= limite:
                break

        vueltas_sin_nuevas = vueltas_sin_nuevas + 1 if len(publicaciones) == antes else 0

        if len(publicaciones) < limite:
            desplazar(driver)
            time.sleep(pausa_scroll)

    return list(publicaciones.values())
