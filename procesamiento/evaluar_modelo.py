from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.naive_bayes import MultinomialNB

from sklearn.model_selection import (
    StratifiedKFold,
    cross_val_score,
    cross_val_predict
)

from sklearn.pipeline import Pipeline

from sklearn.metrics import (
    classification_report,
    confusion_matrix
)

from entrenar_modelo import cargar_dataset


def evaluar_modelo():

    textos, categorias = cargar_dataset()

    print(
        f"\nRegistros evaluados: "
        f"{len(textos)}"
    )

    # pipeline para evitar que TF-IDF
    # conozca previamente los datos de prueba
    pipeline = Pipeline([
        (
            "tfidf",
            TfidfVectorizer()
        ),
        (
            "modelo",
            MultinomialNB()
        )
    ])

    # validación cruzada estratificada
    kfold = StratifiedKFold(
        n_splits=5,
        shuffle=True,
        random_state=42
    )

    resultados = cross_val_score(
        pipeline,
        textos,
        categorias,
        cv=kfold,
        scoring="accuracy"
    )

    print("\nACCURACY POR PLIEGUE:")

    for indice, resultado in enumerate(
        resultados,
        start=1
    ):

        print(
            f"Pliegue {indice}: "
            f"{resultado * 100:.2f}%"
        )

    promedio = resultados.mean()

    print("\n" + "=" * 50)

    print(
        f"Accuracy promedio: "
        f"{promedio * 100:.2f}%"
    )

    if promedio >= 0.80:

        print(
            "Resultado: cumple el mínimo "
            "del 80%."
        )

    else:

        print(
            "Resultado: todavía NO cumple "
            "el mínimo del 80%."
        )

    # obtener predicciones de validación cruzada
    predicciones = cross_val_predict(
        pipeline,
        textos,
        categorias,
        cv=kfold
    )

    print("\n" + "=" * 50)

    print("\nREPORTE DE CLASIFICACIÓN:\n")

    print(
        classification_report(
            categorias,
            predicciones,
            zero_division=0
        )
    )

    print("MATRIZ DE CONFUSIÓN:\n")

    etiquetas = [
        "robo",
        "extorsion",
        "agresion",
        "otro",
        "ruido"
    ]

    matriz = confusion_matrix(
        categorias,
        predicciones,
        labels=etiquetas
    )

    print(
        "Orden de categorías:"
    )

    print(etiquetas)

    print()

    print(matriz)


if __name__ == "__main__":
    evaluar_modelo()