import re
import spacy

from anonimizar import anonimizar_texto


# cargar modelo de español
nlp = spacy.load("es_core_news_sm")


def preprocesar_texto(texto):

    if not texto:
        return ""

    # 1. anonimizar antes de cualquier procesamiento
    texto = anonimizar_texto(texto)

    # 2. convertir a minúsculas
    texto = texto.lower()

    # 3. eliminar marcadores que ya no necesitamos
    texto = texto.replace("[url]", " ")
    texto = texto.replace("[usuario]", " ")
    texto = texto.replace("[email]", " ")
    texto = texto.replace("[telefono]", " ")
    texto = texto.replace("[persona]", " ")

    # 4. eliminar caracteres especiales y números aislados
    # los números de zona se conservarán posteriormente
    texto = re.sub(
        r"[^a-záéíóúñü0-9\s]",
        " ",
        texto
    )

    # 5. eliminar espacios duplicados
    texto = re.sub(
        r"\s+",
        " ",
        texto
    ).strip()

    # 6. procesamiento lingüístico con spaCy
    documento = nlp(texto)

    tokens_limpios = []

    for token in documento:

        # ignorar espacios
        if token.is_space:
            continue

        # ignorar signos de puntuación
        if token.is_punct:
            continue

        # eliminar stopwords
        if token.is_stop:
            continue

        # obtener lema
        lema = token.lemma_.strip().lower()

        if not lema:
            continue

        tokens_limpios.append(lema)

    # 7. reconstruir el texto
    texto_procesado = " ".join(tokens_limpios)

    return texto_procesado


if __name__ == "__main__":

    texto_prueba = (
        "Juan Pérez fue asaltado en la zona 1. "
        "Los delincuentes estaban robando teléfonos "
        "y huyeron rápidamente!!! 😨"
    )

    resultado = preprocesar_texto(texto_prueba)

    print("\nTEXTO ORIGINAL:")
    print(texto_prueba)

    print("\nTEXTO PROCESADO:")
    print(resultado)