import time
from collections import Counter

from clasificar import (
    cargar_modelos,
    clasificar_texto
)


def generar_publicaciones(cantidad=500):

    ejemplos = [

        # Robo
        "Me quitaron el celular cuando caminaba por zona 1.",
        "Dos hombres asaltaron a una persona y le robaron la cartera.",
        "Reportan un asalto cerca del mercado de Mixco.",
        "Un caco se llevó una motocicleta durante la noche.",

        # Extorsión
        "Están cobrando renta a comerciantes en Mixco.",
        "Amenazaron a un negocio para exigirle dinero.",
        "Vecinos denuncian cobro de extorsión en la colonia.",
        "Están exigiendo dinero a varios comerciantes.",

        # Agresión
        "Golpearon a un joven afuera del mercado.",
        "Reportan una pelea fuerte entre varias personas.",
        "Una persona fue agredida durante una discusión.",
        "Se escucharon disparos durante una pelea.",

        # Otro
        "Reportan un vehículo sospechoso cerca del sector.",
        "Hay movimiento extraño durante la madrugada.",
        "Vecinos reportan una situación sospechosa.",
        "Se observa actividad inusual cerca del lugar.",

        # Ruido
        "Qué buen partido estuvo el de anoche.",
        "Hoy estuvo muy bonito el clima.",
        "Vamos a comer con la familia este domingo.",
        "Feliz cumpleaños para todos mis amigos."
    ]

    publicaciones = []

    for indice in range(cantidad):

        texto = ejemplos[
            indice % len(ejemplos)
        ]

        publicaciones.append(texto)

    return publicaciones


def ejecutar_prueba():

    print("\n" + "=" * 70)
    print("PRUEBA DE RENDIMIENTO DEL MÓDULO PLN")
    print("=" * 70)

    publicaciones = generar_publicaciones(
        500
    )

    print(
        f"Publicaciones generadas: "
        f"{len(publicaciones)}"
    )

    # ==========================================
    # CARGA DEL MODELO
    # ==========================================

    inicio_carga = time.perf_counter()

    vectorizador, modelo = cargar_modelos()

    fin_carga = time.perf_counter()

    tiempo_carga = (
        fin_carga - inicio_carga
    )

    print(
        f"Tiempo de carga del modelo: "
        f"{tiempo_carga:.4f} segundos"
    )


    # ==========================================
    # PROCESAMIENTO
    # ==========================================

    resultados = []

    inicio = time.perf_counter()

    for texto in publicaciones:

        categoria, score, texto_procesado = (
            clasificar_texto(
                texto,
                vectorizador,
                modelo
            )
        )

        resultados.append(
            categoria
        )

    fin = time.perf_counter()

    tiempo_total = (
        fin - inicio
    )


    # ==========================================
    # RESULTADOS
    # ==========================================

    promedio = (
        tiempo_total
        / len(publicaciones)
    )

    publicaciones_segundo = (
        len(publicaciones)
        / tiempo_total
    )

    conteo = Counter(
        resultados
    )


    print("\n" + "=" * 70)

    print("RESULTADOS")

    print("=" * 70)

    print(
        f"Tiempo procesando 500: "
        f"{tiempo_total:.4f} segundos"
    )

    print(
        f"Tiempo promedio por publicación: "
        f"{promedio:.6f} segundos"
    )

    print(
        f"Publicaciones por segundo: "
        f"{publicaciones_segundo:.2f}"
    )


    print("\nClasificaciones obtenidas:")

    for categoria, cantidad in conteo.items():

        print(
            f"  {categoria}: "
            f"{cantidad}"
        )


    # ==========================================
    # VALIDACIÓN DE META
    # ==========================================

    limite_segundos = 120

    print("\n" + "=" * 70)

    if tiempo_total <= limite_segundos:

        print(
            "RESULTADO: CUMPLE"
        )

        print(
            "El procesamiento de 500 "
            "publicaciones tomó menos "
            "de 120 segundos."
        )

    else:

        print(
            "RESULTADO: NO CUMPLE"
        )

        print(
            "El procesamiento superó "
            "los 120 segundos."
        )

    print("=" * 70)


if __name__ == "__main__":
    ejecutar_prueba()