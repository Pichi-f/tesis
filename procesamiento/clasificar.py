import joblib
from pathlib import Path

from preprocesar import preprocesar_texto
from normalizar_chapinismos import normalizar_chapinismos


BASE_DIR = Path(__file__).resolve().parent.parent

RUTA_MODELO = (
    BASE_DIR / "modelos" / "clasificador.pkl"
)

RUTA_VECTORIZADOR = (
    BASE_DIR / "modelos" / "vectorizador.pkl"
)


def cargar_modelos():

    vectorizador = joblib.load(
        RUTA_VECTORIZADOR
    )

    modelo = joblib.load(
        RUTA_MODELO
    )

    return vectorizador, modelo


def preparar_texto(texto):

    texto_procesado = preprocesar_texto(
        texto
    )

    texto_normalizado = normalizar_chapinismos(
        texto_procesado
    )

    return texto_normalizado


def clasificar_texto(
    texto,
    vectorizador,
    modelo
):

    texto_preparado = preparar_texto(
        texto
    )

    vector = vectorizador.transform(
        [texto_preparado]
    )

    categoria = modelo.predict(
        vector
    )[0]

    probabilidades = modelo.predict_proba(
        vector
    )[0]

    indice_categoria = list(
        modelo.classes_
    ).index(categoria)

    score = probabilidades[
        indice_categoria
    ]

    return (
        categoria,
        float(score),
        texto_preparado
    )


if __name__ == "__main__":

    vectorizador, modelo = cargar_modelos()

    texto_prueba = (
        "Están cobrando renta a varios "
        "negocios en Mixco."
    )

    categoria, score, texto_preparado = clasificar_texto(
        texto_prueba,
        vectorizador,
        modelo
    )

    print("\nTEXTO ORIGINAL:")
    print(texto_prueba)

    print("\nTEXTO PREPARADO:")
    print(texto_preparado)

    print("\nRESULTADO:")
    print(f"Categoría: {categoria}")
    print(f"Score: {score:.4f}")
    print(
        f"Confianza: "
        f"{score * 100:.2f}%"
    )