"""Prueba del diccionario de chapinismos (RF-PLN-03) con frases en jerga local.

Entrena dos modelos con el mismo dataset y el mismo algoritmo: uno prepara el
texto con el diccionario de chapinismos y la desofuscación, y el otro sin
ellos. Luego ambos clasifican un conjunto de frases escritas con jerga
guatemalteca. La diferencia entre los dos mide el aporte del diccionario.

Las frases no son publicaciones reales: se redactaron para cubrir la jerga
del diccionario, incluidos casos de ruido con palabras ambiguas ("la mara"
como gente, "palmar" de cansancio). Ninguna está en el dataset.

Uso: python procesamiento/prueba_jerga.py
"""

import sys

from sklearn.metrics import accuracy_score

import clasificar
import preprocesar
from entrenar_modelo import cargar_dataset, crear_svm, crear_vectorizador

sys.stdout.reconfigure(errors="replace")

FRASES = [
    ("Unos cacos me bajaron el cel en la parada de la Roosevelt", "robo"),
    ("Cuidado mucha, andan rateros en moto en la zona 7, a mi vecina le quitaron el pisto", "robo"),
    ("Atracaron a un piloto de tuc tuc en Villa Nueva y se llevaron la moto", "robo"),
    ("Choros asaltaron la camioneta de la ruta a Mixco, se llevaron celus y billeteras", "robo"),
    ("Otra vez los cacos se metieron a la tienda de la esquina en la colonia", "robo"),
    ("Le volaron el cel a un patojo saliendo del Trébol", "robo"),
    ("Me encañonaron con un cuete y me bajaron todo en la parada", "robo"),
    ("Atraco en la gasolinera de la zona 12, se llevaron el pisto de la caja", "robo"),
    ("Los mareros le están cobrando la renta a las tiendas en Mixco", "extorsion"),
    ("Ya no se aguanta el cobro de piso, a los pilotos de bus les piden mil quetzales a la semana", "extorsion"),
    ("Cae rentero cuando recogía el pisto en Villa Nueva", "extorsion"),
    ("La clica manda notas a los negocios pidiendo renta, si no pagan les queman el local", "extorsion"),
    ("Me llamaron diciendo que eran de la mara y que si no pago la renta me matan", "extorsion"),
    ("En la colonia ya cerraron tres tiendas por la renta", "extorsion"),
    ("Plomacera en la zona 18, dicen que hay un patojo herido", "agresion"),
    ("Le metieron bala a un piloto de tuc tuc en Villa Nueva", "agresion"),
    ("Gatilleros en moto le dieron plomazos a un señor frente a su casa en Mixco", "agresion"),
    ("Apareció un encostalado en el barranco de la zona 6", "agresion"),
    ("Tiroteo entre mareros en la colonia, hay dos muertos", "agresion"),
    ("Un pistolero palmó a un motorista en la zona 12", "agresion"),
    ("Se escucharon un montón de balazos por el mercado", "agresion"),
    ("B4L4C3R4 en Villa Nueva, 4S3S1N4N a un J0V3N", "agresion"),
    ("Levantón de un comerciante en la zona 10, se lo llevaron en una camioneta", "otro"),
    ("Plagio de un niño en Mixco, la PNC ya lo busca", "otro"),
    ("Capturan a dos de la clica con chimbas y droga en un allanamiento", "otro"),
    ("Qué chilero el concierto de anoche, mucha", "ruido"),
    ("Ese patojo se robó el show en el partido", "ruido"),
    ("La mara estaba bien alegre en la feria del pueblo", "ruido"),
    ("Este gobierno nos asalta con los impuestos", "ruido"),
    ("Vendo cel en buen estado, precio negociable, zona 11", "ruido"),
    ("Ya palmé de cansancio después del trabajo", "ruido"),
]


def entrenar(textos, categorias):
    vectorizador = crear_vectorizador()
    modelo = crear_svm()
    modelo.fit(vectorizador.fit_transform(textos), categorias)
    return vectorizador, modelo


def evaluar(nombre, vectorizador, modelo, textos, esperadas):
    predichas = modelo.predict(vectorizador.transform(textos))
    incidente = [c != "ruido" for c in esperadas]
    incidente_predicho = [c != "ruido" for c in predichas]
    print(
        f"{nombre:<28} categoría: {accuracy_score(esperadas, predichas):6.1%}"
        f"   incidente vs. ruido: {accuracy_score(incidente, incidente_predicho):6.1%}"
    )
    return predichas


def main():
    frases = [frase for frase, _ in FRASES]
    esperadas = [categoria for _, categoria in FRASES]

    print("Preparando el texto CON diccionario y desofuscación...")
    textos_con, categorias, _ = cargar_dataset()
    frases_con = [clasificar.preparar_texto(f) for f in frases]
    vec_con, mod_con = entrenar(textos_con, categorias)

    print("Preparando el texto SIN diccionario ni desofuscación...")
    preprocesar.cargar_ofuscacion = lambda: {}
    clasificar.normalizar_chapinismos = lambda texto: texto
    textos_sin, _, _ = cargar_dataset()
    frases_sin = [clasificar.preparar_texto(f) for f in frases]
    vec_sin, mod_sin = entrenar(textos_sin, categorias)

    print(f"\nFRASES CON JERGA: {len(FRASES)}\n")
    pred_con = evaluar("Con diccionario", vec_con, mod_con, frases_con, esperadas)
    pred_sin = evaluar("Sin diccionario", vec_sin, mod_sin, frases_sin, esperadas)

    print("\nDETALLE (esperada | con diccionario | sin diccionario)")
    for frase, esperada, con, sin in zip(frases, esperadas, pred_con, pred_sin):
        marca = "  " if con == sin else ("+ " if con == esperada else ("- " if sin == esperada else "~ "))
        print(f"{marca}{esperada:<10} {con:<10} {sin:<10} {frase[:70]}")
    print("\n+ acierta solo con diccionario   - acierta solo sin diccionario   ~ ambos fallan distinto")


if __name__ == "__main__":
    main()
