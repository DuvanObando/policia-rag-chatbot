"""Compara las estrategias de segmentación 'articulo' y 'fragmentos'.

Ejecuta eval/preguntas_segmentacion.json con ambas estrategias y calcula
Acierto@1, Acierto@3 y MRR (a nivel de artículo), el número de vectores de
cada índice y el tiempo medio de búsqueda.

Requisito: construir antes los dos índices:
    python engine/indexing/build_index.py --estrategia articulo
    python engine/indexing/build_index.py --estrategia fragmentos

Uso (desde la raíz del repo):
    python eval/comparar_segmentacion.py [--preguntas RUTA] [--tamano-busqueda 10]
"""
import argparse
import json
import statistics
import sys
import time
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(RAIZ / "engine"))
from retrieval.search import _indice, buscar, id_articulo, precargar  # noqa: E402

ESTRATEGIAS = ("articulo", "fragmentos")


def posicion(esperado: str, resultados) -> int:
    """Posición (1 = primero) del artículo esperado; 0 si no aparece."""
    for i, r in enumerate(resultados, start=1):
        if id_articulo(r["id"]) == esperado:
            return i
    return 0


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawTextHelpFormatter)
    ap.add_argument("--preguntas", default=str(RAIZ / "eval" / "preguntas_segmentacion.json"))
    ap.add_argument("--tamano-busqueda", type=int, default=10, help="k de la búsqueda (todos los artículos de la muestra)")
    args = ap.parse_args()

    preguntas = json.loads(Path(args.preguntas).read_text(encoding="utf-8"))
    k = args.tamano_busqueda

    pos = {e: [] for e in ESTRATEGIAS}
    tiempos = {e: [] for e in ESTRATEGIAS}
    vectores = {}
    for e in ESTRATEGIAS:
        precargar(e)
        vectores[e] = _indice(e)[0].ntotal
        buscar(preguntas[0]["pregunta"], k=k, estrategia=e)  # calentamiento: no se mide
        for p in preguntas:
            t = time.perf_counter()
            res = buscar(p["pregunta"], k=k, estrategia=e)
            tiempos[e].append((time.perf_counter() - t) * 1000)
            pos[e].append(posicion(p["articulo_esperado"], res))

    print("\nPOSICIÓN DEL ARTÍCULO ESPERADO (1 = primero, 0 = no aparece)")
    print(f"{'#':<4}{'Esperado':<10}{'>512':<6}{'articulo':>10}{'fragmentos':>12}  Pregunta")
    for i, p in enumerate(preguntas):
        print(f"{p['id']:<4}{p['articulo_esperado'].replace('art-', ''):<10}"
              f"{'sí' if p['despues_del_token_512'] else 'no':<6}"
              f"{pos['articulo'][i]:>10}{pos['fragmentos'][i]:>12}  {p['pregunta'][:60]}")

    def metricas(posiciones, mascara=None):
        ps = [x for x, m in zip(posiciones, mascara or [True] * len(posiciones)) if m]
        n = len(ps)
        return (sum(p == 1 for p in ps) / n,
                sum(1 <= p <= 3 for p in ps) / n,
                sum(1 / p if p else 0 for p in ps) / n)

    despues = [p["despues_del_token_512"] for p in preguntas]
    antes = [not d for d in despues]
    print("\nRESUMEN")
    print(f"{'Estrategia':<12}{'Vectores':>9}{'Acierto@1':>11}{'Acierto@3':>11}{'MRR':>8}{'ms/búsq.':>10}")
    for e in ESTRATEGIAS:
        a1, a3, mrr = metricas(pos[e])
        print(f"{e:<12}{vectores[e]:>9}{a1:>11.2f}{a3:>11.2f}{mrr:>8.3f}{statistics.mean(tiempos[e]):>10.0f}")

    print("\nSOLO PREGUNTAS CUYA RESPUESTA ESTÁ DESPUÉS DEL TOKEN 512 (4)")
    print(f"{'Estrategia':<12}{'Acierto@1':>11}{'Acierto@3':>11}{'MRR':>8}")
    for e in ESTRATEGIAS:
        a1, a3, mrr = metricas(pos[e], despues)
        print(f"{e:<12}{a1:>11.2f}{a3:>11.2f}{mrr:>8.3f}")
    print("\nSOLO PREGUNTAS SOBRE TEXTO QUE SÍ ENTRA EN 512 TOKENS (6)")
    print(f"{'Estrategia':<12}{'Acierto@1':>11}{'Acierto@3':>11}{'MRR':>8}")
    for e in ESTRATEGIAS:
        a1, a3, mrr = metricas(pos[e], antes)
        print(f"{e:<12}{a1:>11.2f}{a3:>11.2f}{mrr:>8.3f}")


if __name__ == "__main__":
    main()
