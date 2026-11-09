"""Compara los tres modos de búsqueda: semantico, lexico (BM25) e hibrido (RRF).

Todos con clasificador (como pide la evaluación). Usa 16 preguntas:
  - 10 de eval/preguntas_segmentacion.json
  -  3 de eval/preguntas_clasificador.json
  -  3 de eval/preguntas_hibrida.json (términos exactos: sigla, plazo, término legal)

Muestra Acierto@1, Acierto@3, MRR y tiempo de búsqueda por modo, la posición del artículo
esperado en cada pregunta, y en qué preguntas cambió el resultado y por qué. Como dato
informativo, repite la tabla resumen sin clasificador.

Requisitos: índices 'fragmentos' construidos (con BM25) y empuje calibrado (eval/calibrar_empuje.py).

Uso (desde la raíz del repo):
    python eval/comparar_modos.py
"""
import json
import os
import sys
import time
from pathlib import Path

# Estos resultados son SIN expansión de consultas (la expansión se evalúa aparte en
# eval/comparar_expansion.py), sin importar BUSQUEDA_EXPANSION del .env.
os.environ["BUSQUEDA_EXPANSION"] = "0"

RAIZ = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(RAIZ / "engine"))
from preprocess.texto_bm25 import tokens_bm25  # noqa: E402
from retrieval import clasificador as clf  # noqa: E402
from retrieval.search import MODOS, _bm25, buscar, id_articulo, precargar_busqueda, rrf_k  # noqa: E402

ESTRATEGIA = "fragmentos"
K = 10
ARCHIVOS = ["preguntas_segmentacion.json", "preguntas_clasificador.json", "preguntas_hibrida.json"]
REPETICIONES = 3  # pasadas para promediar el tiempo


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


def correr(preguntas, modo, con_clasificador):
    """(resultados por pregunta, milisegundos promedio por búsqueda)."""
    buscar("calentamiento", k=1, estrategia=ESTRATEGIA, modo=modo, clasificador=con_clasificador)
    resultados, tiempos = None, []
    for _ in range(REPETICIONES):
        t = time.perf_counter()
        resultados = [buscar(p["pregunta"], k=K, estrategia=ESTRATEGIA, modo=modo, clasificador=con_clasificador)
                      for p in preguntas]
        tiempos.append((time.perf_counter() - t) * 1000 / len(preguntas))
    return resultados, sum(tiempos) / len(tiempos)


def corto(texto, n):
    return texto if len(texto) <= n else texto[: n - 1] + "…"


def main() -> None:
    preguntas = []
    for a in ARCHIVOS:
        preguntas += json.loads((RAIZ / "eval" / a).read_text(encoding="utf-8"))
    precargar_busqueda(ESTRATEGIA, "hibrido")
    emp = clf.cargar()["configuracion"]["empuje_por_modo"]
    print(f"RRF k = {rrf_k()} | empuje por modo = {emp}")

    res, ms, pos = {}, {}, {}
    for m in MODOS:
        res[m], ms[m] = correr(preguntas, m, True)
        pos[m] = [posicion(p["articulo_esperado"], r) for p, r in zip(preguntas, res[m])]

    print("\nPOSICIÓN DEL ARTÍCULO ESPERADO, con clasificador (1 = primero, 0 = no aparece)")
    print(f"{'#':<4}{'Esper.':<7}{'sem':>5}{'lex':>5}{'híb':>5}  {'Tipo':<24}Pregunta")
    for i, p in enumerate(preguntas):
        a, b, c = pos["semantico"][i], pos["lexico"][i], pos["hibrido"][i]
        marca = "*" if len({a, b, c}) > 1 else " "
        print(f"{p['id']:<4}{p['articulo_esperado'].replace('art-', ''):<7}{a:>5}{b:>5}{c:>5} {marca} "
              f"{p.get('tipo', 'original'):<24}{corto(p['pregunta'], 50)}")

    n_orig, n_cl = 10, 13
    grupos = (("16 preguntas", slice(0, 16)), ("13 de la evaluación anterior", slice(0, n_cl)),
              ("3 con términos exactos (p14-p16)", slice(n_cl, 16)))
    print("\nRESUMEN (todos con clasificador)")
    for nombre, sl in grupos:
        print(f"\n{nombre}")
        print(f"{'modo':<11}{'Acierto@1':>10}{'Acierto@3':>11}{'MRR':>8}{'ms/búsqueda':>13}")
        for m in MODOS:
            a1, a3, mrr = metricas(pos[m][sl])
            print(f"{m:<11}{a1:>10.2f}{a3:>11.2f}{mrr:>8.3f}{ms[m]:>13.1f}")

    print("\nINFORMATIVO: 16 preguntas SIN clasificador")
    print(f"{'modo':<11}{'Acierto@1':>10}{'Acierto@3':>11}{'MRR':>8}")
    for m in MODOS:
        r, _ = correr(preguntas, m, False)
        ps = [posicion(p["articulo_esperado"], x) for p, x in zip(preguntas, r)]
        a1, a3, mrr = metricas(ps)
        print(f"{m:<11}{a1:>10.2f}{a3:>11.2f}{mrr:>8.3f}")

    print("\nEN QUÉ PREGUNTAS CAMBIÓ EL RESULTADO Y POR QUÉ")
    bm25_tokens = json.loads((RAIZ / "engine" / "indexing" / "indexes" / ESTRATEGIA / "bm25_tokens.json")
                             .read_text(encoding="utf-8"))
    metadatos = json.loads((RAIZ / "engine" / "indexing" / "indexes" / ESTRATEGIA / "metadatos.json")
                           .read_text(encoding="utf-8"))
    _, metodo = _bm25(ESTRATEGIA)
    cambios = 0
    for i, p in enumerate(preguntas):
        if len({pos[m][i] for m in MODOS}) == 1:
            continue
        cambios += 1
        esperado = p["articulo_esperado"]
        consulta = set(tokens_bm25(p["pregunta"], metodo))
        comunes = set()
        for f, toks in zip(metadatos["fragmentos"], bm25_tokens["tokens"]):
            if id_articulo(f["id"]) == esperado:
                comunes |= consulta & set(toks)
        print(f"\n{p['id']} ({p.get('tipo', 'original')}): {p['pregunta']}")
        print(f"  esperado {esperado}: " + " | ".join(f"{m} {pos[m][i]}" for m in MODOS))
        print(f"  palabras de la pregunta (preparadas): {sorted(consulta)}")
        print(f"  de ellas, aparecen en el artículo esperado: {sorted(comunes) or 'ninguna'}")
        for m in MODOS:
            top = [(id_articulo(r['id']).replace('art-', ''), round(r['score'], 4)) for r in res[m][i][:3]]
            print(f"  {m:<10} primeros 3: {top}")
    if not cambios:
        print("  Ninguna pregunta cambió de posición entre modos.")


if __name__ == "__main__":
    main()
