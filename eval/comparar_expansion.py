"""Compara la búsqueda con y sin expansión de consultas (glosario de sinónimos coloquiales).

Modo híbrido (con clasificador, la configuración por defecto) y, solo como dato informativo,
modo léxico. Usa 19 preguntas:
  - 10 de eval/preguntas_segmentacion.json
  -  3 de eval/preguntas_clasificador.json
  -  3 de eval/preguntas_hibrida.json
  -  3 de eval/preguntas_coloquiales.json (lenguaje muy coloquial, escritas antes de evaluar)

La expansión se activa y desactiva con la variable BUSQUEDA_EXPANSION (la lee en cada búsqueda).

Requisito: índices 'fragmentos' construidos (con BM25).

Uso (desde la raíz del repo):
    python eval/comparar_expansion.py
"""
import json
import os
import sys
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(RAIZ / "engine"))
from retrieval.expansion import expandir_detalle, info  # noqa: E402
from retrieval.search import _bm25, buscar, id_articulo, precargar_busqueda  # noqa: E402

ESTRATEGIA = "fragmentos"
K = 10
ARCHIVOS = ["preguntas_segmentacion.json", "preguntas_clasificador.json", "preguntas_hibrida.json",
            "preguntas_coloquiales.json"]


def posicion(esperado, resultados):
    for i, r in enumerate(resultados, start=1):
        if id_articulo(r["id"]) == esperado:
            return i
    return 0


def metricas(posiciones):
    n = len(posiciones)
    return (sum(p == 1 for p in posiciones) / n,
            sum(1 <= p <= 3 for p in posiciones) / n,
            sum(1 / p if p else 0 for p in posiciones) / n)


def correr(preguntas, modo, expansion):
    os.environ["BUSQUEDA_EXPANSION"] = "1" if expansion else "0"
    return [buscar(p["pregunta"], k=K, estrategia=ESTRATEGIA, modo=modo, clasificador=True) for p in preguntas]


def corto(texto, n):
    return texto if len(texto) <= n else texto[: n - 1] + "…"


def main() -> None:
    preguntas = []
    for a in ARCHIVOS:
        preguntas += json.loads((RAIZ / "eval" / a).read_text(encoding="utf-8"))
    precargar_busqueda(ESTRATEGIA, "hibrido")
    buscar("calentamiento", k=1, estrategia=ESTRATEGIA, modo="hibrido")
    _, metodo = _bm25(ESTRATEGIA)
    os.environ["BUSQUEDA_EXPANSION"] = "1"
    print(f"Glosario: {info()['entradas']} entradas | método de preparación del índice BM25: {metodo}")

    res = {(m, e): correr(preguntas, m, e) for m in ("hibrido", "lexico") for e in (False, True)}
    pos = {k: [posicion(p["articulo_esperado"], r) for p, r in zip(preguntas, v)] for k, v in res.items()}

    print("\nPOSICIÓN DEL ARTÍCULO ESPERADO en modo híbrido (1 = primero, 0 = no aparece)")
    print(f"{'#':<4}{'Esper.':<7}{'sin':>4}{'con':>5}   Pregunta")
    for i, p in enumerate(preguntas):
        a, b = pos[("hibrido", False)][i], pos[("hibrido", True)][i]
        marca = "↑" if (b and (not a or b < a)) else ("↓" if (a and (not b or b > a)) else " ")
        print(f"{p['id']:<4}{p['articulo_esperado'].replace('art-', ''):<7}{a:>4}{b:>5} {marca} {corto(p['pregunta'], 62)}")

    grupos = (("19 preguntas", slice(0, 19)), ("16 de la evaluación anterior", slice(0, 16)),
              ("3 muy coloquiales (p17-p19)", slice(16, 19)))
    for modo, titulo in (("hibrido", "MODO HÍBRIDO"), ("lexico", "INFORMATIVO: MODO LÉXICO")):
        print(f"\n{titulo}")
        for nombre, sl in grupos:
            print(f"\n{nombre}\n{'':<22}{'Acierto@1':>10}{'Acierto@3':>11}{'MRR':>8}")
            for etiqueta, e in (("sin expansión", False), ("con expansión", True)):
                a1, a3, mrr = metricas(pos[(modo, e)][sl])
                print(f"{etiqueta:<22}{a1:>10.2f}{a3:>11.2f}{mrr:>8.3f}")

    print("\nEN QUÉ PREGUNTAS CAMBIÓ EL RESULTADO (modo híbrido) Y POR QUÉ")
    cambios = 0
    for i, p in enumerate(preguntas):
        a, b = pos[("hibrido", False)][i], pos[("hibrido", True)][i]
        if a == b:
            continue
        cambios += 1
        d = expandir_detalle(p["pregunta"], metodo)
        print(f"\n{p['id']} ({p.get('tipo', 'original')}): {p['pregunta']}")
        print(f"  esperado {p['articulo_esperado']}: posición {a} -> {b}")
        for c in d["coincidencias"]:
            print(f"  coloquial {c['coloquial']!r} -> legal {c['legal']!r}: agrega {c['agregados']}")
        for etiqueta, e in (("sin", False), ("con", True)):
            top = [(id_articulo(r['id']).replace('art-', ''), round(r['score'], 4)) for r in res[("hibrido", e)][i][:3]]
            print(f"  {etiqueta} expansión, primeros 3: {top}")
    if not cambios:
        print("  Ninguna pregunta cambió de posición.")

    print("\nPREGUNTAS EN LAS QUE LA EXPANSIÓN AGREGÓ PALABRAS (aunque no cambiara la posición)")
    for p in preguntas:
        d = expandir_detalle(p["pregunta"], metodo)
        if d["agregados"]:
            print(f"  {p['id']}: " + "; ".join(f"{c['coloquial']!r}→{c['legal']!r}" for c in d["coincidencias"]))


if __name__ == "__main__":
    main()
