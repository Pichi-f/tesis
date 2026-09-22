from extractor_x import buscar_publicaciones

from guardar_reportes import (
    guardar_publicaciones
)


def ejecutar():

    consulta = (
        '"asalto" Guatemala'
    )


    print(
        "\n"
        + "=" * 70
    )

    print(
        "EXTRACCIÓN DE PUBLICACIONES DE X"
    )

    print(
        "=" * 70
    )


    publicaciones = buscar_publicaciones(
        consulta,
        limite=10
    )


    print(
        f"\nPublicaciones extraídas: "
        f"{len(publicaciones)}"
    )


    if not publicaciones:

        print(
            "No existen publicaciones "
            "para almacenar."
        )

        return


    resultado = guardar_publicaciones(
        publicaciones
    )


    print(
        "\n"
        + "=" * 70
    )

    print(
        "RESULTADO DE ALMACENAMIENTO"
    )

    print(
        "=" * 70
    )

    print(
        f"Insertadas: "
        f"{resultado['insertados']}"
    )

    print(
        f"Duplicadas: "
        f"{resultado['duplicados']}"
    )

    print(
        f"Inválidas: "
        f"{resultado['invalidos']}"
    )


if __name__ == "__main__":

    ejecutar()