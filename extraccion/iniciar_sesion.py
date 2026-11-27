"""Abre el navegador para iniciar sesión A MANO en una plataforma.

Uso:
    python extraccion/iniciar_sesion.py x
    python extraccion/iniciar_sesion.py facebook

La sesión queda guardada en browser_profiles/ y los extractores la
reutilizan. Ningún script escribe ni almacena contraseñas.
"""

import sys

from navegador import crear_driver

DESTINOS = {
    "x": ("X", "https://x.com/login"),
    "facebook": ("Facebook", "https://www.facebook.com/login"),
}


def main():
    if len(sys.argv) != 2 or sys.argv[1].lower() not in DESTINOS:
        print(__doc__)
        sys.exit(1)

    plataforma, url = DESTINOS[sys.argv[1].lower()]
    driver = crear_driver(plataforma)
    driver.get(url)
    input(
        f"\nInicia sesión en {plataforma} en la ventana de Chrome.\n"
        "Cuando veas tu página de inicio, vuelve aquí y presiona ENTER..."
    )
    driver.quit()
    print("Sesión guardada.")


if __name__ == "__main__":
    main()
