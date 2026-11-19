"""Compara el clasificador temático con y sin la propuesta de temas de Santiago Castro.

Solo recuperación (no llama al LLM). Modo semántico (el de la demo), estrategia fragmentos, k=10.

Configuraciones (cada una en su propio proceso, porque el tema se fija al cargar el índice):
  A  sin clasificador (ni empuje por tema ni regla del artículo por número)
  B  clasificador ANTERIOR: eval/temas_anterior.json y el tema del corpus (TEMAS_PROPUESTA=0).
     Con el corpus real todos los artículos tienen el mismo tema, así que solo actúa la regla del número.
  C  clasificador NUEVO: 32 temas de la propuesta (temas.json) + tema por artículo (TEMAS_PROPUESTA=1)
  C con otros empujes (sensibilidad): 0.01, 0.02, 0.05

Preguntas: las evaluaciones anteriores (eval/preguntas_*.json), las 9 indirectas del 19/11 y las del
banco de Wilder con artículo de la Ley 1801 identificable.

Uso, desde la raíz:  python eval/comparar_temas.py [--salida docs/resultados_temas.md]
"""
import argparse
import json
import os
import subprocess
import sys
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(RAIZ / "eval"))
import bancos  # noqa: E402

K = 10


def conjunto():
    preguntas = bancos.recuperacion_existente()
    preguntas += [p for p in bancos.indirectas() if p["articulos_esperados"]]
    preguntas += [p for p in bancos.banco()[0] if p["articulos_esperados"] and not p["fuera_de_dominio"]]
    return preguntas


def hijo(config: str, empuje: float = None):
    """Corre una configuración y devuelve, por pregunta, la posición del primer artículo esperado."""
    sys.path.insert(0, str(RAIZ / "engine"))
    from retrieval import clasificador as clf
    from retrieval.search import buscar, id_articulo, precargar
    if empuje is not None:
        clf.cargar()["configuracion"]["empuje_por_modo"]["semantico"] = empuje
    precargar("fragmentos")
    salida = []
    for p in conjunto():
        r = buscar(p["pregunta"], k=K, estrategia="fragmentos", modo="semantico", clasificador=(config != "A"))
        arts = [id_articulo(x["id"]) for x in r]
        pos = next((i + 1 for i, a in enumerate(arts) if a in p["articulos_esperados"]), 0)
        salida.append({"id": p["id"], "pos": pos, "top": arts[:3], "tema": clf.clasificar(p["pregunta"])["tema"]})
    print("JSON:" + json.dumps(salida, ensure_ascii=False))


def correr(config, empuje=None):
    env = dict(os.environ, PYTHONIOENCODING="utf-8", HF_HUB_DISABLE_SYMLINKS_WARNING="1")
    if config == "B":
        env.update(TEMAS_PROPUESTA="0", TEMAS_RUTA=str(RAIZ / "eval" / "temas_anterior.json"))
    else:
        env.update(TEMAS_PROPUESTA="1")
        env.pop("TEMAS_RUTA", None)
    args = [sys.executable, __file__, "--hijo", config] + (["--empuje", str(empuje)] if empuje is not None else [])
    for intento in range(2):  # un reintento: en Windows el proceso hijo a veces falla al cargar el modelo
        p = subprocess.run(args, capture_output=True, text=True, encoding="utf-8", errors="replace", env=env, cwd=RAIZ)
        linea = next((l for l in p.stdout.splitlines() if l.startswith("JSON:")), None)
        if linea:
            return json.loads(linea[5:])
        print(f"La configuración {config} (empuje {empuje}) falló:\n{p.stderr[-1500:]}", file=sys.stderr)
    raise SystemExit(f"No se pudo correr la configuración {config}.")


def metricas(res, ids=None):
    ps = [r["pos"] for r in res if ids is None or r["id"] in ids]
    n = len(ps) or 1
    return (sum(1 for p in ps if p == 1) / n, sum(1 for p in ps if 1 <= p <= 3) / n,
            sum(1 / p for p in ps if p) / n, len(ps))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--hijo")
    ap.add_argument("--empuje", type=float)
    ap.add_argument("--salida", default=str(RAIZ / "docs" / "resultados_temas.md"))
    a = ap.parse_args()
    if a.hijo:
        return hijo(a.hijo, a.empuje)

    preguntas = conjunto()
    res = {"A": correr("A"), "B": correr("B"), "C": correr("C")}
    sens = {e: correr("C", e) for e in (0.01, 0.03, 0.05)}
    grupos = {
        "todas": None,
        "evaluaciones anteriores": {p["id"] for p in preguntas if p["origen"].startswith("eval/preguntas_") and "indirectas" not in p["origen"]},
        "indirectas (19/11)": {p["id"] for p in preguntas if "indirectas" in p["origen"]},
        "banco de Wilder": {p["id"] for p in preguntas if "1801" in p["origen"]},
    }
    l = ["# Clasificador temático: con y sin la propuesta de temas de Santiago Castro", "",
         f"Generado por `eval/comparar_temas.py`. Solo recuperación (sin LLM), modo semántico, fragmentos, k={K}. "
         "Posición = lugar del primer artículo esperado (0 = no aparece en los 10).", "",
         "- **A**: sin clasificador. **B**: clasificador anterior (10 temas del corpus de muestra; con el corpus real "
         "todos los artículos tienen el mismo tema, así que solo actúa la regla del artículo por número). "
         "**C**: propuesta de Castro (32 temas por rangos de artículos) con el empuje de temas.json (0.02 desde el 19/11).", "",
         "| Grupo | n | A Acierto@1 | A Acierto@3 | A MRR | B Acierto@1 | B Acierto@3 | B MRR | C Acierto@1 | C Acierto@3 | C MRR |",
         "|---|---|---|---|---|---|---|---|---|---|---|"]
    for nombre, ids in grupos.items():
        fila = [nombre, str(metricas(res["A"], ids)[3])]
        for c in "ABC":
            a1, a3, mrr, _ = metricas(res[c], ids)
            fila += [f"{a1:.2f}", f"{a3:.2f}", f"{mrr:.3f}"]
        l.append("| " + " | ".join(fila) + " |")
    l += ["", "Sensibilidad de C al empuje (todas las preguntas):", "", "| empuje | Acierto@1 | Acierto@3 | MRR |", "|---|---|---|---|"]
    for e, r in [(0.01, sens[0.01]), (0.02, res["C"]), (0.03, sens[0.03]), (0.05, sens[0.05])]:
        a1, a3, mrr, _ = metricas(r)
        l.append(f"| {e} | {a1:.2f} | {a3:.2f} | {mrr:.3f} |")
    l += ["", "## Preguntas que cambian entre B y C", "", "| id | pregunta | esperado | B | C | tema detectado (C) | primero en C |", "|---|---|---|---|---|---|---|"]
    por_id = {p["id"]: p for p in preguntas}
    for b, c in zip(res["B"], res["C"]):
        if b["pos"] != c["pos"]:
            p = por_id[b["id"]]
            l.append(f"| {b['id']} | {p['pregunta'][:70]} | {', '.join(p['articulos_esperados'])} | {b['pos']} | {c['pos']} | {c['tema']} | {c['top'][0]} |")
    Path(a.salida).write_text("\n".join(l) + "\n", encoding="utf-8")
    print("\n".join(l))


if __name__ == "__main__":
    main()
