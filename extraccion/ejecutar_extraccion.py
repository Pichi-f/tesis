"""Ejecuta un ciclo de extracción de X y Facebook y lo guarda en la base.

Uso:
    python extraccion/ejecutar_extraccion.py                 # un ciclo, ambas plataformas
    python extraccion/ejecutar_extraccion.py --plataforma x
    python extraccion/ejecutar_extraccion.py --max-consultas 3   # prueba corta
    python extraccion/ejecutar_extraccion.py --continuo      # repite cada intervalo_horas

Las consultas y los parámetros están en config/extraccion.json.
"""

import argparse
import time

import extractor_facebook
import extractor_x
from filtros import cargar_fuentes_excluidas, filtrar
from guardar_reportes import guardar_publicaciones
from navegador import cargar_config, crear_driver, esperar, obtener_logger

logger = obtener_logger()


def tareas_de(plataforma, config):
    """Lista de (descripción, función, argumento, límite, palabras clave a exigir)."""
    if plataforma == "X":
        return [
            (consulta, extractor_x.buscar_publicaciones, consulta, config["limite_por_consulta"], None)
            for consulta in config["x"]["consultas"]
        ]

    seccion = config["facebook"]
    busquedas = [
        (consulta, extractor_facebook.buscar_publicaciones, consulta,
         config["limite_por_consulta"], config["palabras_clave"])
        for consulta in seccion["busquedas"]
    ]
    fuentes = [
        (url, extractor_facebook.extraer_de_fuente, url,
         seccion.get("limite_por_fuente", config["limite_por_consulta"]), config["palabras_clave"])
        for url in seccion["fuentes"]
    ]
    # Las fuentes públicas van primero: no dependen de la sesión.
    return fuentes + busquedas


def con_reintentos(funcion, driver, argumento, limite, config):
    """RNF-EXT-02: hasta max_reintentos ante errores de red o de carga."""
    intentos = config.get("max_reintentos", 3)
    for intento in range(1, intentos + 1):
        try:
            return funcion(driver, argumento, limite)
        except (extractor_x.SesionRequerida, extractor_facebook.SesionRequerida):
            raise
        except Exception as error:
            logger.warning("Intento %d/%d falló | %s | %s", intento, intentos, argumento, error)
            if intento == intentos:
                logger.error("Se agotaron los reintentos | %s", argumento)
                return []
            esperar(config)


def extraer_plataforma(plataforma, config, excluidas, max_consultas=None):
    tareas = tareas_de(plataforma, config)[:max_consultas]
    totales = {"extraidas": 0, "validas": 0, "insertados": 0, "duplicados": 0}
    if not tareas:
        return totales

    driver = crear_driver(plataforma)
    try:
        for numero, (descripcion, funcion, argumento, limite, palabras) in enumerate(tareas, start=1):
            try:
                publicaciones = con_reintentos(
                    funcion, driver, argumento, limite, config
                )
            except (extractor_x.SesionRequerida, extractor_facebook.SesionRequerida) as error:
                logger.error(
                    "%s | %s. Ejecuta: python extraccion/iniciar_sesion.py %s",
                    plataforma, error, plataforma.lower(),
                )
                if funcion is extractor_facebook.extraer_de_fuente:
                    continue
                break

            validas, descartes = filtrar(publicaciones, excluidas, palabras)
            guardado = guardar_publicaciones(validas)

            totales["extraidas"] += len(publicaciones)
            totales["validas"] += len(validas)
            totales["insertados"] += guardado["insertados"]
            totales["duplicados"] += guardado["duplicados"]

            logger.info(
                "%s %d/%d | %s | extraidas=%d validas=%d nuevas=%d duplicadas=%d descartes=%s",
                plataforma, numero, len(tareas), descripcion, len(publicaciones),
                len(validas), guardado["insertados"], guardado["duplicados"], descartes,
            )

            if numero < len(tareas):
                esperar(config)
    finally:
        driver.quit()

    return totales


def ejecutar_ciclo(plataformas, max_consultas=None):
    config = cargar_config()
    excluidas = cargar_fuentes_excluidas()

    for plataforma in plataformas:
        logger.info("Inicio de extracción | %s", plataforma)
        totales = extraer_plataforma(plataforma, config, excluidas, max_consultas)
        logger.info("Fin de extracción | %s | %s", plataforma, totales)


def main():
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--plataforma", choices=["x", "facebook", "todas"], default="todas")
    parser.add_argument("--max-consultas", type=int, help="limita las consultas (para pruebas)")
    parser.add_argument("--continuo", action="store_true", help="repite cada intervalo_horas")
    argumentos = parser.parse_args()

    plataformas = {
        "x": ["X"], "facebook": ["Facebook"], "todas": ["X", "Facebook"],
    }[argumentos.plataforma]

    while True:
        ejecutar_ciclo(plataformas, argumentos.max_consultas)
        if not argumentos.continuo:
            break
        horas = cargar_config().get("intervalo_horas", 6)
        logger.info("Próximo ciclo en %s horas", horas)
        time.sleep(horas * 3600)


if __name__ == "__main__":
    main()
