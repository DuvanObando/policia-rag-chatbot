"""Evaluación formal del sistema RAG (Fase 6): recuperación, fuera de dominio y corrección de la cita.

Banco: eval/banco_preguntas.json (formato de eval/ejemplo_formato.json). Si está vacío, usa el banco
de Wilder (corpus/preguntas_ley_1801.json) adaptado por eval/bancos.py. Con --indirectas agrega las
10 preguntas indirectas del 19/11 (eval/preguntas_indirectas.json).

Corre el motor EN ESTE PROCESO (no hace falta tener uvicorn encendido), con el .env de la raíz:
mismo LLM, mismo modo de búsqueda y mismos índices que la demo. Hace una pausa entre preguntas por
los límites gratuitos de Groq y Gemini, y reintenta si el LLM responde "ocupado".

Uso, desde la raíz del repo (con el venv del motor):
    engine\\.venv\\Scripts\\python eval/run_eval.py                    # banco completo, pausa 20 s
    engine\\.venv\\Scripts\\python eval/run_eval.py --indirectas --pausa 15
    engine\\.venv\\Scripts\\python eval/run_eval.py --limite 5 --pausa 5   # prueba rápida

Salida: eval/reporte.md (métricas y análisis de errores) y eval/resultados_eval.json (detalle).

Métricas (k = número de artículos distintos que el motor le entrega al LLM, 3 por defecto):
  - Precisión@k: artículos esperados entre los k recuperados / k.
  - Recall@k: artículos esperados recuperados / artículos esperados.
  - MRR: 1 / posición del primer artículo esperado (0 si no aparece en los k).
    Las tres solo sobre preguntas con artículo esperado y que no son fuera de dominio.
  - Exactitud de fuera de dominio: preguntas donde `fuera_de_dominio` coincide con lo esperado / todas.
    También se informan precisión y recall de la clase "fuera de dominio".
  - Corrección de la cita (preguntas dentro del dominio que el motor respondió):
      * cita correcta: al menos un artículo citado está entre los esperados;
      * cita exacta: TODOS los artículos citados están entre los esperados (más estricta).
"""
import argparse
import json
import re
import sys
import time
from collections import defaultdict
from datetime import datetime
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(RAIZ / "engine"))
sys.path.insert(0, str(RAIZ / "eval"))
import bancos  # noqa: E402

REPORTE = RAIZ / "eval" / "reporte.md"
DETALLE = RAIZ / "eval" / "resultados_eval.json"


def articulos_de(citados) -> list:
    """['Artículo 140', 'Ley 769 de 2002, Artículo 131'] -> ['art-140', 'ley769-art-131']."""
    salida = []
    for c in citados or []:
        if "," in c and "Ley" in c.split(",")[0] and "1801" not in c.split(",")[0]:
            m = re.match(r"Ley (\d+) de \d{4}, Artículo (\w+)", c)  # «Ley 769 de 2002, Artículo 131»
            salida.append(f"ley{m.group(1)}-art-{m.group(2)}" if m else "otra-norma:" + c)
        else:
            salida.append(bancos.normalizar_articulo(c))
    return salida


def preguntar(responder, ErrorLLM, pregunta, k, reintentos=4, espera=30):
    for intento in range(reintentos + 1):
        try:
            t = time.perf_counter()
            r = responder(pregunta, k=k, incluir_diagnostico=True)
            r["_s"] = round(time.perf_counter() - t, 2)
            return r
        except ErrorLLM as e:
            if intento == reintentos:
                return {"_error": str(e)[:200]}
            print(f"   LLM ocupado; espero {espera} s y repito ({intento + 1}/{reintentos})", flush=True)
            time.sleep(espera)


def evaluar(p, r, k):
    from retrieval.search import id_articulo
    fila = {"id": p["id"], "tipo": p["tipo"], "pregunta": p["pregunta"], "esperados": p["articulos_esperados"],
            "fuera_esperado": p["fuera_de_dominio"]}
    if "_error" in r:
        fila.update(error=r["_error"])
        return fila
    recuperados = []
    for f in r["fragmentos"]:
        a = id_articulo(f["id"])
        if a not in recuperados:
            recuperados.append(a)
    recuperados = recuperados[:k]
    citados = articulos_de(r.get("articulos_citados"))
    esperados = set(p["articulos_esperados"])
    d = r.get("diagnostico", {})
    fila.update(
        recuperados=recuperados, citados=citados, fuera_obtenido=bool(r["fuera_de_dominio"]),
        s=r.get("_s"), modelo=d.get("modelo_usado"), respaldo=d.get("uso_respaldo"),
        citas_descartadas=d.get("citas_descartadas"), respuesta=r["respuesta"],
    )
    if esperados and not p["fuera_de_dominio"]:
        aciertos = [a for a in recuperados if a in esperados]
        pos = next((i + 1 for i, a in enumerate(recuperados) if a in esperados), 0)
        fila.update(precision=len(aciertos) / k, recall=len(set(aciertos)) / len(esperados), rr=(1 / pos if pos else 0.0), pos=pos)
        if not r["fuera_de_dominio"]:
            fila.update(cita_correcta=any(c in esperados for c in citados) if citados else False,
                        cita_exacta=bool(citados) and all(c in esperados for c in citados))
    return fila


def promedio(filas, campo):
    v = [f[campo] for f in filas if campo in f]
    return (sum(v) / len(v), len(v)) if v else (float("nan"), 0)


def reporte(filas, nombre_banco, k, config, inicio, duracion):
    validas = [f for f in filas if "error" not in f]
    dom = [f for f in validas if "fuera_obtenido" in f]
    exact_fd = sum(f["fuera_obtenido"] == f["fuera_esperado"] for f in dom) / len(dom) if dom else float("nan")
    vp = sum(f["fuera_obtenido"] and f["fuera_esperado"] for f in dom)
    pred = sum(f["fuera_obtenido"] for f in dom)
    real = sum(f["fuera_esperado"] for f in dom)
    l = [
        "# Reporte de evaluación formal (Fase 6)", "",
        f"Generado por `eval/run_eval.py` el {inicio:%d/%m/%Y %H:%M} ({duracion / 60:.1f} min).", "",
        f"- **Banco:** {nombre_banco}. Preguntas: {len(filas)} ({len(filas) - len(validas)} sin respuesta del LLM).",
        f"- **Configuración:** {config}.",
        f"- **k = {k}** artículos distintos entregados al LLM (small-to-big).", "",
        "## Métricas", "",
        "| Métrica | Valor | n |", "|---|---|---|",
    ]
    for nombre, campo in (("Precisión@%d" % k, "precision"), ("Recall@%d" % k, "recall"), ("MRR", "rr")):
        m, n = promedio(validas, campo)
        l.append(f"| {nombre} | {m:.3f} | {n} |")
    l.append(f"| Exactitud de fuera de dominio | {exact_fd:.3f} | {len(dom)} |")
    l.append(f"| Fuera de dominio: precisión (de las marcadas, cuántas lo eran) | {vp / pred if pred else float('nan'):.3f} | {pred} |")
    l.append(f"| Fuera de dominio: recall (de las trampas, cuántas detectó) | {vp / real if real else float('nan'):.3f} | {real} |")
    for nombre, campo in (("Corrección de la cita (al menos un artículo citado es esperado)", "cita_correcta"),
                          ("Cita exacta (todos los citados son esperados)", "cita_exacta")):
        m, n = promedio(validas, campo)
        l.append(f"| {nombre} | {m:.3f} | {n} |")
    tiempos = [f["s"] for f in validas if f.get("s")]
    if tiempos:
        l.append(f"| Tiempo por pregunta (mediana / máximo) | {sorted(tiempos)[len(tiempos) // 2]:.1f} s / {max(tiempos):.1f} s | {len(tiempos)} |")
    modelos = defaultdict(int)
    for f in validas:
        modelos[f.get("modelo") or "?"] += 1
    l += ["", "Modelos que respondieron: " + ", ".join(f"{m} ({n})" for m, n in modelos.items()), ""]

    por_tipo = defaultdict(list)
    for f in validas:
        por_tipo[f["tipo"]].append(f)
    l += ["## Por tipo de pregunta", "", "| Tipo | n | MRR | Exactitud fuera de dominio | Cita correcta |", "|---|---|---|---|---|"]
    for t, fs in sorted(por_tipo.items()):
        mrr, _ = promedio(fs, "rr")
        ex = sum(f["fuera_obtenido"] == f["fuera_esperado"] for f in fs) / len(fs)
        cc, _ = promedio(fs, "cita_correcta")
        l.append(f"| {t} | {len(fs)} | {mrr:.3f} | {ex:.3f} | {cc:.3f} |")

    l += ["", "## Análisis de errores", ""]
    grupos = {
        "Fuera de dominio equivocado: era trampa y el motor respondió": [f for f in dom if f["fuera_esperado"] and not f["fuera_obtenido"]],
        "Fuera de dominio equivocado: estaba en la ley y el motor dijo que no": [f for f in dom if not f["fuera_esperado"] and f["fuera_obtenido"]],
        "El artículo esperado no llegó al LLM (recuperación)": [f for f in validas if f.get("pos") == 0],
        "Llegó el artículo pero la cita no es la esperada": [f for f in validas if f.get("pos") and f.get("cita_correcta") is False],
        "Sin respuesta del LLM (límites del plan gratuito)": [f for f in filas if "error" in f],
    }
    for titulo, fs in grupos.items():
        l.append(f"### {titulo} ({len(fs)})")
        l.append("")
        for f in fs:
            l.append(f"- **{f['id']}** «{f['pregunta']}» — esperados {f['esperados'] or '—'}; recuperados {f.get('recuperados')}; "
                     f"citados {f.get('citados')}; fuera_de_dominio {f.get('fuera_obtenido')}")
        if not fs:
            l.append("- Ninguna.")
        l.append("")
    return "\n".join(l) + "\n"


def main():
    ap = argparse.ArgumentParser(description="Evaluación formal del RAG")
    ap.add_argument("--pausa", type=float, default=20, help="segundos entre preguntas (límites gratuitos)")
    ap.add_argument("--limite", type=int, default=0, help="solo las primeras N preguntas")
    ap.add_argument("--indirectas", action="store_true", help="agrega eval/preguntas_indirectas.json")
    ap.add_argument("-k", type=int, default=3)
    ap.add_argument("--reporte", default=str(REPORTE))
    a = ap.parse_args()

    preguntas, nombre = bancos.banco()
    if a.indirectas:
        preguntas += bancos.indirectas()
        nombre += " + eval/preguntas_indirectas.json"
    if a.limite:
        preguntas = preguntas[: a.limite]

    from generation.llm import ErrorLLM, orden_proveedores
    from generation.responder import responder
    from retrieval.search import modo_por_defecto, normas_cargadas, precargar
    from indexing import temas_articulos
    precargar("fragmentos")
    # Preguntas que solo tienen sentido con otra norma cargada (p. ej. la Ley 769): se omiten si no está.
    cargadas = {n["norma"] for n in normas_cargadas("fragmentos")}
    omitidas = [p for p in preguntas if p.get("requiere_norma") and p["requiere_norma"] not in cargadas]
    if omitidas:
        preguntas = [p for p in preguntas if p not in omitidas]
        nombre += f" · {len(omitidas)} omitidas porque su norma no está cargada"
    config = (f"modo de búsqueda `{modo_por_defecto()}`, LLM en orden {orden_proveedores()}, "
              f"temas de Castro {'activos' if temas_articulos.activa() else 'desactivados'} (TEMAS_PROPUESTA)")
    print(f"{len(preguntas)} preguntas | {nombre}\n{config}", flush=True)

    inicio, t0, filas = datetime.now(), time.perf_counter(), []
    for i, p in enumerate(preguntas, 1):
        if i > 1:
            time.sleep(a.pausa)
        f = evaluar(p, preguntar(responder, ErrorLLM, p["pregunta"], a.k), a.k)
        filas.append(f)
        print(f"[{i}/{len(preguntas)}] {p['id']} pos={f.get('pos', '-')} citados={f.get('citados')} "
              f"fuera={f.get('fuera_obtenido')} (esperado {p['fuera_de_dominio']}) {f.get('s', '')}s {f.get('modelo', f.get('error', ''))}", flush=True)
        DETALLE.write_text(json.dumps(filas, ensure_ascii=False, indent=1), encoding="utf-8")  # se guarda a medida que avanza

    texto = reporte(filas, nombre, a.k, config, inicio, time.perf_counter() - t0)
    Path(a.reporte).write_text(texto, encoding="utf-8")
    print("\n" + texto)


if __name__ == "__main__":
    main()
