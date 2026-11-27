"""Utilidades compartidas por los extractores: navegador, esperas y bitácora.

Cada plataforma usa su propio perfil persistente de Chrome dentro de
browser_profiles/. El inicio de sesión se hace a mano una sola vez con
iniciar_sesion.py; los extractores nunca escriben credenciales ni
intentan evadir controles de acceso.
"""

import json
import logging
import random
import time
from pathlib import Path

from selenium import webdriver
from selenium.webdriver.chrome.options import Options

BASE_DIR = Path(__file__).resolve().parent.parent
RUTA_CONFIG = BASE_DIR / "config" / "extraccion.json"
RUTA_LOG = BASE_DIR / "logs" / "extraccion.log"

PERFILES = {
    "X": BASE_DIR / "browser_profiles" / "x_manual",
    "Facebook": BASE_DIR / "browser_profiles" / "facebook",
}


def cargar_config():
    with open(RUTA_CONFIG, "r", encoding="utf-8") as archivo:
        return json.load(archivo)


def obtener_logger():
    logger = logging.getLogger("extraccion")
    if logger.handlers:
        return logger

    RUTA_LOG.parent.mkdir(exist_ok=True)
    formato = logging.Formatter("%(asctime)s | %(levelname)s | %(message)s")

    archivo = logging.FileHandler(RUTA_LOG, encoding="utf-8")
    archivo.setFormatter(formato)
    consola = logging.StreamHandler()
    consola.setFormatter(formato)

    logger.setLevel(logging.INFO)
    logger.addHandler(archivo)
    logger.addHandler(consola)
    return logger


def crear_driver(plataforma):
    perfil = PERFILES[plataforma]
    perfil.mkdir(parents=True, exist_ok=True)

    opciones = Options()
    opciones.add_argument("--start-maximized")
    opciones.add_argument("--disable-notifications")
    opciones.add_argument("--lang=es")
    opciones.add_argument(f"--user-data-dir={perfil}")
    return webdriver.Chrome(options=opciones)


def esperar(config):
    """Pausa aleatoria entre solicitudes (RNF-EXT-01: 5 a 15 segundos)."""
    segundos = random.uniform(
        config.get("espera_min_segundos", 5),
        config.get("espera_max_segundos", 15),
    )
    time.sleep(segundos)
    return segundos


def desplazar(driver):
    driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
