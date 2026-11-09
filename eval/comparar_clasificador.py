"""Compara la búsqueda con y sin clasificador temático.

Usa las preguntas de eval/preguntas_segmentacion.json (10) y de
eval/preguntas_clasificador.json (3 nuevas: artículo por número, ambigua entre dos
temas y sin tema claro). Estrategia de búsqueda: 'fragmentos'; modo semántico.

Para cada pregunta muestra el tema detectado y la posición del artículo esperado sin
y con clasificador; calcula Acierto@1, Acierto@3 y MRR; explica en qué preguntas cambió
el resultado y por qué; y, solo como información, cómo varía el resultado con el empuje.

Requisito: tener construido el índice 'fragmentos':
    python engine/indexing/build_index.py --estrategia fragmentos

Uso (desde la raíz del repo):
    python eval/comparar_clasificador.py
"""
import json
import sys
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(RAIZ / "engine"))
from retrieval import clasificador as clf  # noqa: E402
from retrieval.search import buscar, id_articulo, precargar  # noqa: E402

ESTRATEGIA = "fragmentos"
K = 10  # todos los artículos de la muestra
ARCHIVOS = ["preguntas_segmentacion.json", "preguntas_clasificador.json"]


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


def correr(preguntas, con_clasificador):
    return [buscar(p["pregunta"], k=K, estrategia=ESTRATEGIA, modo="semantico", clasificador=con_clasificador) for p in preguntas]


def corto(texto, n):
    return texto if len(texto) <= n else texto[: n - 1] + "…"


def main() -> None:
    preguntas = []
    for a in ARCHIVOS:
        preguntas += json.loads((RAIZ / "eval" / a).read_text(encoding="utf-8"))
    precargar(ESTRATEGIA)
    buscar("calentamiento", k=1, estrategia=ESTRATEGIA, modo="semantico")

    sin = correr(preguntas, False)
    con = correr(preguntas, True)
    pos_sin = [posicion(p["articulo_esperado"], r) for p, r in zip(preguntas, sin)]
    pos_con = [posicion(p["articulo_esperado"], r) for p, r in zip(preguntas, con)]
    clas = [clf.clasificar(p["pregunta"]) for p in preguntas]

    print(f"\nEmpuje (modo semantico): {clf.cargar()['configuracion']['empuje_por_modo']['semantico']} | "
          f"umbral relativo: {clf.cargar()['configuracion']['umbral_relativo']}")
    print("\nPOSICIÓN DEL ARTÍCULO ESPERADO (1 = primero, 0 = no aparece)")
    print(f"{'#':<4}{'Esper.':<7}{'sin':>4}{'con':>5}  {'':<3}{'Tema detectado':<42}{'conf.':>6}  Pregunta")
    for p, a, b, c in zip(preguntas, pos_sin, pos_con, clas):
        marca = "↑" if (b and (not a or b < a)) else ("↓" if (a and (not b or b > a)) else " ")
        print(f"{p['id']:<4}{p['articulo_esperado'].replace('art-', ''):<7}{a:>4}{b:>5}  {marca:<3}"
              f"{corto(c['tema'], 41):<42}{c['confianza']:>6.2f}  {corto(p['pregunta'], 52)}")

    print("\nRESUMEN (13 preguntas)")
    print(f"{'':<22}{'Acierto@1':>10}{'Acierto@3':>11}{'MRR':>8}")
    for nombre, ps in (("sin clasificador", pos_sin), ("con clasificador", pos_con)):
        a1, a3, mrr = metricas(ps)
        print(f"{nombre:<22}{a1:>10.2f}{a3:>11.2f}{mrr:>8.3f}")

    print("\nRESUMEN solo las 10 preguntas originales")
    for nombre, ps in (("sin clasificador", pos_sin[:10]), ("con clasificador", pos_con[:10])):
        a1, a3, mrr = metricas(ps)
        print(f"{nombre:<22}{a1:>10.2f}{a3:>11.2f}{mrr:>8.3f}")

    print("\nQUÉ CAMBIÓ Y POR QUÉ")
    cambios = 0
    for i, p in enumerate(preguntas):
        if pos_sin[i] == pos_con[i]:
            continue
        cambios += 1
        esperado = p["articulo_esperado"]
        top_sin, top_con = id_articulo(sin[i][0]["id"]), id_articulo(con[i][0]["id"])
        tema_esperado = next(r["tema"] for r in sin[i] if id_articulo(r["id"]) == esperado)
        sc_sin = next(r["score"] for r in sin[i] if id_articulo(r["id"]) == esperado)
        sc_con = next(r["score"] for r in con[i] if id_articulo(r["id"]) == esperado)
        print(f"\n{p['id']} ({p.get('tipo', 'original')}): {p['pregunta']}")
        print(f"  esperado {esperado}: posición {pos_sin[i]} -> {pos_con[i]} | primero: {top_sin} -> {top_con}")
        print(f"  tema del artículo esperado: {tema_esperado!r}; score del esperado {sc_sin:.3f} -> {sc_con:.3f}")
        for t in clas[i]["temas"]:
            print(f"  tema detectado {t['tema']!r}: puntaje {t['puntaje']}, confianza {t['confianza']}, "
                  f"coincidencias {t['coincidencias']}")
        print(f"  empuje aplicado: { {k: round(v, 3) for k, v in clf.empujes(clas[i], 'semantico').items()} or 'ninguno' }")
        print(f"  artículos pedidos por número: {clf.articulos_mencionados(p['pregunta']) or 'ninguno'}")
    if not cambios:
        print("  Ninguna pregunta cambió de posición.")

    print("\nPREGUNTAS DONDE EL TEMA DETECTADO NO COINCIDE CON EL TEMA DEL ARTÍCULO ESPERADO")
    temas_corpus = {id_articulo(r["id"]): r["tema"] for r in sin[0]}
    for p, c in zip(preguntas, clas):
        te = temas_corpus[p["articulo_esperado"]]
        detectados = [t["tema"] for t in c["temas"]]
        if te not in detectados:
            print(f"  {p['id']}: esperado tema {te!r}; detectado {detectados or ['general']}")

    print("\nSENSIBILIDAD AL EMPUJE (solo informativo: el valor por defecto se fijó antes de evaluar)")
    cfg = clf.cargar()["configuracion"]["empuje_por_modo"]
    original = cfg["semantico"]
    print(f"{'empuje':>8}{'Acierto@1':>11}{'Acierto@3':>11}{'MRR':>8}")
    for e in (0.0, 0.01, 0.02, 0.03, 0.05, 0.08, 0.12):
        cfg["semantico"] = e
        ps = [posicion(p["articulo_esperado"], r) for p, r in zip(preguntas, correr(preguntas, True))]
        a1, a3, mrr = metricas(ps)
        print(f"{e:>8.2f}{a1:>11.2f}{a3:>11.2f}{mrr:>8.3f}")
    cfg["semantico"] = original


if __name__ == "__main__":
    main()
