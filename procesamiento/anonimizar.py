import re
import spacy


# cargar una sola vez el modelo de español
nlp = spacy.load("es_core_news_sm")


def anonimizar_nombres(texto):

    documento = nlp(texto)

    posiciones = []

    # nombres detectados por spaCy
    for entidad in documento.ents:

        if entidad.label_ == "PER":
            posiciones.append(
                (
                    entidad.start_char,
                    entidad.end_char
                )
            )

    # nombres completos que spaCy pudo no detectar
    patron_nombre = (
        r'\b'
        r'[A-ZÁÉÍÓÚÑ][a-záéíóúñ]+'
        r'\s+'
        r'[A-ZÁÉÍÓÚÑ][a-záéíóúñ]+'
        r'\b'
    )

    for coincidencia in re.finditer(
        patron_nombre,
        texto
    ):

        inicio = coincidencia.start()
        fin = coincidencia.end()
        candidato = coincidencia.group()

        es_ubicacion = False

        # comprobar entidades geográficas detectadas por spaCy
        for entidad in documento.ents:

            if (
                entidad.start_char <= inicio
                and entidad.end_char >= fin
                and entidad.label_ in (
                    "LOC",
                    "ORG",
                    "MISC"
                )
            ):
                es_ubicacion = True
                break

        # ubicaciones conocidas que queremos conservar
        ubicaciones_protegidas = (
            "Villa Nueva",
            "San Miguel Petapa",
            "Ciudad de Guatemala",
            "Villa Canales",
            "Santa Catarina Pinula",
            "San José Pinula"
        )

        if candidato in ubicaciones_protegidas:
            es_ubicacion = True

        if not es_ubicacion:
            posiciones.append(
                (
                    inicio,
                    fin
                )
            )

    # ordenar posiciones
    posiciones.sort()

    # unir posiciones que estén superpuestas
    posiciones_unidas = []

    for inicio, fin in posiciones:

        if not posiciones_unidas:

            posiciones_unidas.append(
                [inicio, fin]
            )

        else:

            ultimo_inicio, ultimo_fin = posiciones_unidas[-1]

            if inicio <= ultimo_fin:

                posiciones_unidas[-1][1] = max(
                    ultimo_fin,
                    fin
                )

            else:

                posiciones_unidas.append(
                    [inicio, fin]
                )

    # realizar reemplazos
    resultado = ""
    posicion_actual = 0

    for inicio, fin in posiciones_unidas:

        resultado += texto[
            posicion_actual:inicio
        ]

        resultado += "[PERSONA]"

        posicion_actual = fin

    resultado += texto[posicion_actual:]

    return resultado


def anonimizar_texto(texto):

    if not texto:
        return ""

    texto_anonimo = texto

    # eliminar o reemplazar URLs
    patron_url = r'https?://\S+|www\.\S+'

    texto_anonimo = re.sub(
        patron_url,
        '[URL]',
        texto_anonimo
    )

    # anonimizar correos electrónicos
    patron_email = r'\b[\w\.-]+@[\w\.-]+\.\w+\b'

    texto_anonimo = re.sub(
        patron_email,
        '[EMAIL]',
        texto_anonimo
    )

    # anonimizar usuarios de redes sociales
    patron_usuario = r'(?<!\w)@[A-Za-z0-9_]+'

    texto_anonimo = re.sub(
        patron_usuario,
        '[USUARIO]',
        texto_anonimo
    )

    # anonimizar números de teléfono
    patron_telefono = (
        r'(?<!\d)'
        r'(?:\+502[\s-]?)?'
        r'\d{4}[\s-]?\d{4}'
        r'(?!\d)'
    )

    texto_anonimo = re.sub(
        patron_telefono,
        '[TELEFONO]',
        texto_anonimo
    )

    # detectar nombres de personas usando spaCy
    texto_anonimo = anonimizar_nombres(texto_anonimo)

    # eliminar espacios duplicados
    texto_anonimo = re.sub(
        r'\s+',
        ' ',
        texto_anonimo
    )

    return texto_anonimo.strip()


if __name__ == "__main__":

    texto_prueba = (
    "Juan Pérez fue asaltado en la zona 1. "
    "María López llamó al 4444-5555. "
    "Carlos Méndez reportó el incidente desde Villa Nueva. "
    "Ana García también estaba cerca del Trébol."
)

    resultado = anonimizar_texto(texto_prueba)

    print("\nTEXTO ORIGINAL:")
    print(texto_prueba)

    print("\nTEXTO ANONIMIZADO:")
    print(resultado)