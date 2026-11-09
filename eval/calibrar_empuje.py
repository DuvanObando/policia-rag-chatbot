"""Calcula el empuje por tema equivalente en cada modo de búsqueda.

El score tiene otra escala en cada modo (coseno ~0.7-0.9, BM25 normalizado 0-1, RRF ~0.01-0.03),
así que sumar el mismo empuje (0.03) a los tres no empujaría lo mismo. Para que el clasificador
"funcione igual" en los tres modos, el empuje de cada modo se calcula con la dispersión de sus
scores:

    empuje_modo = 0.03 × dispersión_mediana(modo) / dispersión_mediana(semantico)

donde la dispersión de una pregunta es score(posición 1) − score(posición 10) entre los
fragmentos candidatos, SIN clasificador, y la mediana se toma sobre las preguntas de evaluación.

IMPORTANTE: usa solo los scores de las preguntas, NUNCA el artículo esperado ni si acertó, así
que no ajusta el empuje a los resultados. Se ejecuta antes de evaluar (eval/comparar_modos.py) y
sus valores se copian a engine/retrieval/temas.json (configuracion.empuje_por_modo).

Uso (desde la raíz del repo):
    python eval/calibrar_empuje.py
"""
import json
import os
import statistics
import sys
from pathlib import Path

# Estos resultados son SIN expansión de consultas (la expansión se evalúa aparte en
# eval/comparar_expansion.py), sin importar BUSQUEDA_EXPANSION del .env.
os.environ["BUSQUEDA_EXPANSION"] = "0"

RAIZ = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(RAIZ / "engine"))
from retrieval.search import MODOS, _puntajes_base, precargar_busqueda  # noqa: E402

ESTRATEGIA = "fragmentos"
EMPUJE_SEMANTICO = 0.03  # valor de referencia, fijado antes en docs/clasificador.md
ARCHIVOS = ["preguntas_segmentacion.json", "preguntas_clasificador.json", "preguntas_hibrida.json"]
POSICION = 10


def main() -> None:
    preguntas = []
    for a in ARCHIVOS:
        preguntas += json.loads((RAIZ / "eval" / a).read_text(encoding="utf-8"))
    precargar_busqueda(ESTRATEGIA, "hibrido")

    dispersiones = {m: [] for m in MODOS}
    for p in preguntas:
        for m in MODOS:
            scores = [s for s, _ in _puntajes_base(p["pregunta"], ESTRATEGIA, m)]
            if len(scores) >= 2:
                dispersiones[m].append(scores[0] - scores[min(POSICION, len(scores)) - 1])

    print(f"Preguntas: {len(preguntas)} | dispersión = score(1) - score({POSICION}) sin clasificador\n")
    print(f"{'modo':<11}{'preguntas con ≥2 resultados':>28}{'dispersión mediana':>20}{'empuje equivalente':>20}")
    ref = statistics.median(dispersiones["semantico"])
    for m in MODOS:
        med = statistics.median(dispersiones[m]) if dispersiones[m] else float("nan")
        print(f"{m:<11}{len(dispersiones[m]):>28}{med:>20.5f}{EMPUJE_SEMANTICO * med / ref:>20.5f}")


if __name__ == "__main__":
    main()
