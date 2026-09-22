import time
from urllib.parse import quote

from selenium import webdriver

from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.options import Options

from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent

PERFIL_X = (
    BASE_DIR
    / "browser_profiles"
    / "x_manual"
)

def crear_driver():

    PERFIL_X.mkdir(
        parents=True,
        exist_ok=True
    )

    opciones = Options()

    opciones.add_argument(
        "--start-maximized"
    )

    opciones.add_argument(
        "--disable-notifications"
    )

    opciones.add_argument(
        "--lang=es"
    )

    opciones.add_argument(
        f"--user-data-dir={PERFIL_X}"
    )

    driver = webdriver.Chrome(
        options=opciones
    )

    return driver


def construir_url_busqueda(
    consulta
):

    consulta_codificada = quote(
        consulta
    )

    return (
        "https://x.com/search"
        f"?q={consulta_codificada}"
        "&src=typed_query"
        "&f=live"
    )


def detectar_bloqueo_login(
    driver
):

    url_actual = driver.current_url.lower()

    if (
        "/login" in url_actual
        or
        "/i/flow/login" in url_actual
    ):
        return True


    textos = [
        "iniciar sesión",
        "log in",
        "sign in",
        "crear cuenta",
        "sign up"
    ]


    contenido = driver.page_source.lower()


    for texto in textos:

        if (
            texto in contenido
            and
            not driver.find_elements(
                By.CSS_SELECTOR,
                'article[data-testid="tweet"]'
            )
        ):
            return True


    return False


def extraer_publicacion(
    articulo
):

    # ==========================================
    # TEXTO
    # ==========================================

    try:

        texto = articulo.find_element(
            By.CSS_SELECTOR,
            '[data-testid="tweetText"]'
        ).text.strip()

    except Exception:

        texto = ""


    # ==========================================
    # FECHA
    # ==========================================

    try:

        elemento_fecha = articulo.find_element(
            By.TAG_NAME,
            "time"
        )

        fecha = elemento_fecha.get_attribute(
            "datetime"
        )

    except Exception:

        fecha = None


    # ==========================================
    # URL DE PUBLICACIÓN
    # ==========================================

    url = None

    try:

        enlaces = articulo.find_elements(
            By.CSS_SELECTOR,
            'a[href*="/status/"]'
        )

        for enlace in enlaces:

            href = enlace.get_attribute(
                "href"
            )

            if (
                href
                and "/status/" in href
            ):
                url = href
                break

    except Exception:

        pass


    # ==========================================
    # IDENTIFICADOR / USUARIO VISIBLE
    # ==========================================

    usuario = None

    try:

        bloque_usuario = articulo.find_element(
            By.CSS_SELECTOR,
            '[data-testid="User-Name"]'
        )

        texto_usuario = (
            bloque_usuario.text
            .strip()
        )

        for parte in texto_usuario.split():

            if parte.startswith("@"):

                usuario = parte

                break

    except Exception:

        pass


    if not texto:

        return None


    return {
        "plataforma": "X",
        "usuario_publico": usuario,
        "texto": texto,
        "fecha": fecha,
        "url": url
    }


def buscar_publicaciones(
    consulta,
    limite=10
):

    driver = crear_driver()

    publicaciones = []


    try:

        url = construir_url_busqueda(
            consulta
        )

        print(
            f"\nAbriendo búsqueda:"
            f"\n{url}\n"
        )


        driver.get(
            url
        )


        # Espera inicial deliberada.
        # También ayuda a respetar el
        # ritmo de solicitudes.
        time.sleep(
            8
        )


        # ==========================================
        # COMPROBAR SI X EXIGE LOGIN
        # ==========================================

        if detectar_bloqueo_login(
            driver
        ):

            print(
                "X está mostrando una pantalla "
                "de inicio de sesión o bloqueando "
                "la búsqueda pública."
            )

            print(
                "No se intentará evadir "
                "el control de acceso."
            )

            return []


        # ==========================================
        # ESPERAR PUBLICACIONES
        # ==========================================

        try:

            WebDriverWait(
                driver,
                15
            ).until(

                EC.presence_of_element_located(
                    (
                        By.CSS_SELECTOR,
                        'article[data-testid="tweet"]'
                    )
                )

            )

        except Exception:

            print(
                "No se encontraron publicaciones "
                "visibles con el selector esperado."
            )

            return []


        ids_vistos = set()

        intentos_sin_nuevos = 0


        while (
            len(publicaciones) < limite
            and
            intentos_sin_nuevos < 3
        ):

            articulos = driver.find_elements(
                By.CSS_SELECTOR,
                'article[data-testid="tweet"]'
            )


            cantidad_antes = len(
                publicaciones
            )


            for articulo in articulos:

                publicacion = (
                    extraer_publicacion(
                        articulo
                    )
                )


                if not publicacion:

                    continue


                identificador = (
                    publicacion["url"]
                    or
                    (
                        publicacion["texto"]
                        + str(
                            publicacion["fecha"]
                        )
                    )
                )


                if identificador in ids_vistos:

                    continue


                ids_vistos.add(
                    identificador
                )


                publicaciones.append(
                    publicacion
                )


                if (
                    len(publicaciones)
                    >= limite
                ):
                    break


            if (
                len(publicaciones)
                == cantidad_antes
            ):

                intentos_sin_nuevos += 1

            else:

                intentos_sin_nuevos = 0


            if (
                len(publicaciones)
                >= limite
            ):

                break


            driver.execute_script(
                "window.scrollTo("
                "0,"
                "document.body.scrollHeight"
                ");"
            )


            # 5–15 segundos según lo que
            # planteamos para la extracción.
            time.sleep(
                7
            )


        return publicaciones


    finally:

        driver.quit()


if __name__ == "__main__":

    consulta = (
        '"asalto" Guatemala'
    )


    publicaciones = buscar_publicaciones(
        consulta,
        limite=10
    )


    print(
        f"\nPublicaciones encontradas: "
        f"{len(publicaciones)}\n"
    )


    for numero, publicacion in enumerate(
        publicaciones,
        start=1
    ):

        print(
            "=" * 70
        )

        print(
            f"PUBLICACIÓN {numero}"
        )

        print(
            f"Usuario: "
            f"{publicacion['usuario_publico']}"
        )

        print(
            f"Fecha: "
            f"{publicacion['fecha']}"
        )

        print(
            f"URL: "
            f"{publicacion['url']}"
        )

        print(
            "Texto:"
        )

        print(
            publicacion["texto"]
        )