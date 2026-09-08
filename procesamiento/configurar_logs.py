import logging

from logging.handlers import RotatingFileHandler
from pathlib import Path


BASE_DIR = Path(__file__).resolve().parent.parent

LOG_DIR = BASE_DIR / "logs"

LOG_DIR.mkdir(
    parents=True,
    exist_ok=True
)


def obtener_logger(
    nombre="procesamiento"
):

    logger = logging.getLogger(
        nombre
    )

    logger.setLevel(
        logging.INFO
    )

    # Evitar duplicar handlers cuando
    # se importa varias veces.
    if logger.handlers:
        return logger


    ruta_log = (
        LOG_DIR / "procesamiento.log"
    )


    manejador = RotatingFileHandler(
        ruta_log,
        maxBytes=2_000_000,
        backupCount=3,
        encoding="utf-8"
    )


    formato = logging.Formatter(
        "%(asctime)s | "
        "%(levelname)s | "
        "%(name)s | "
        "%(message)s"
    )


    manejador.setFormatter(
        formato
    )


    logger.addHandler(
        manejador
    )

    logger.propagate = False


    return logger