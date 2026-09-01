import csv
import joblib
from pathlib import Path

from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.naive_bayes import MultinomialNB

from preprocesar import preprocesar_texto
from normalizar_chapinismos import normalizar_chapinismos


BASE_DIR = Path(__file__).resolve().parent.parent
RUTA_DATASET = BASE_DIR / "data" / "dataset_entrenamiento.csv"

RUTA_MODELOS = BASE_DIR / "modelos"

RUTA_VECTORIZADOR = (
    RUTA_MODELOS / "vectorizador.pkl"
)

RUTA_MODELO = (
    RUTA_MODELOS / "clasificador.pkl"
)

def cargar_dataset():

    textos = []
    categorias = []

    with open(
        RUTA_DATASET,
        "r",
        encoding="utf-8"
    ) as archivo:

        lector = csv.DictReader(archivo)

        for fila in lector:

            texto_original = fila["texto"]
            categoria = fila["categoria"]

            # primero aplicamos el preprocesamiento
            texto_procesado = preprocesar_texto(
                texto_original
            )

            # después normalizamos chapinismos
            texto_normalizado = normalizar_chapinismos(
                texto_procesado
            )

            textos.append(
                texto_normalizado
            )

            categorias.append(
                categoria
            )

    return textos, categorias


def entrenar_modelo():

    textos, categorias = cargar_dataset()

    print(
        f"\nRegistros cargados: "
        f"{len(textos)}"
    )

    print("\nEjemplos procesados:")

    for i in range(5):

        print(
            f"{i + 1}. {textos[i]} "
            f"-> {categorias[i]}"
        )

    # vectorización TF-IDF
    vectorizador = TfidfVectorizer()

    vectores = vectorizador.fit_transform(
        textos
    )

    print(
        f"\nCaracterísticas TF-IDF: "
        f"{len(vectorizador.get_feature_names_out())}"
    )

    # entrenamiento con Naive Bayes
    modelo = MultinomialNB()

    modelo.fit(
        vectores,
        categorias
    )

    RUTA_MODELOS.mkdir(
    exist_ok=True
    )

    joblib.dump(
        vectorizador,
        RUTA_VECTORIZADOR
    )

    joblib.dump(
        modelo,
        RUTA_MODELO
    )

    print(
        "Modelo entrenado correctamente."
    )
    
    print(
    f"Vectorizador guardado en: "
    f"{RUTA_VECTORIZADOR}"
    )

    print(
        f"Clasificador guardado en: "
        f"{RUTA_MODELO}"
    )

    return vectorizador, modelo


if __name__ == "__main__":
    entrenar_modelo()