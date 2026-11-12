"""Estadisticas lingüisticas del corpus (Fase 2, dia 3): tokens, tipos, TTR, POS y NER.

Uso, desde la raiz del repositorio y con el entorno virtual activo:
    python engine/analysis/estadisticas.py
    python engine/analysis/estadisticas.py --corpus corpus/procesados/corpus_ley_1801.json --todo

Por defecto analiza solo el texto base de la Ley 1801 (tipo_disposicion = texto_fuente_ley_base).
Con --todo incluye tambien las disposiciones que modifican, adicionan o corrigen la ley.
Deja el resultado en docs/analisis/estadisticas_base.json (o estadisticas_todo.json con --todo),
asi una corrida no sobrescribe a la otra, y lo imprime como tablas.
No guarda el texto del corpus en la salida, solo conteos.
"""
import argparse
import json
import re
import statistics
from collections import Counter
from pathlib import Path

import spacy

RAIZ = Path(__file__).resolve().parents[2]
CORPUS_POR_DEFECTO = RAIZ / "corpus" / "procesados" / "corpus_ley_1801.json"
CARPETA_SALIDA = RAIZ / "docs" / "analisis"
MODELO = "es_core_news_sm"

# Montos y plazos: spaCy sm no los etiqueta bien, se detectan con expresiones regulares.
# En la Ley 1801 las sanciones se expresan como "Multa General tipo N"; SMDLV/salarios aparecen poco.
RE_MONTO = re.compile(
    r"\bmulta\s+(?:general\s+)?tipo\s*\d\b|\bsmldv\b|\bsmdlv\b|\bsmlmv\b|\bsmmlv\b|\buvt\b"
    r"|\bsalarios?\s+m[ií]nimos?\b",
    re.I,
)
# Plazos escritos como "tres (3) meses" o "48 horas": se cuenta el numero entre parentesis o en cifras.
RE_PLAZO = re.compile(
    r"(?:\(\s*\d+\s*\)|\b\d+)\s*(horas?|minutos?|d[ií]as?|semanas?|meses|mes|a[nñ]os?)\b",
    re.I,
)


def cargar(ruta: Path, todo: bool):
    with open(ruta, encoding="utf-8") as f:
        datos = json.load(f)
    if not todo:
        datos = [d for d in datos if d.get("tipo_disposicion") == "texto_fuente_ley_base"]
    return datos


def es_palabra(t) -> bool:
    return not (t.is_space or t.is_punct) and bool(re.search(r"\w", t.text))


def analizar(registros, nlp):
    textos = [r["texto"] for r in registros]
    formas, lemas = Counter(), Counter()
    pos, ner = Counter(), Counter()
    ents_ejemplo = {}
    tokens_por_reg = []
    montos = plazos = 0

    for doc, texto in zip(nlp.pipe(textos, batch_size=8), textos):
        palabras = [t for t in doc if es_palabra(t)]
        tokens_por_reg.append(len(palabras))
        for t in palabras:
            formas[t.lower_] += 1
            lemas[(t.lemma_ or t.text).lower()] += 1
            pos[t.pos_] += 1
        for e in doc.ents:
            ner[e.label_] += 1
            ents_ejemplo.setdefault(e.label_, Counter())[e.text.strip().lower()] += 1
        montos += len(RE_MONTO.findall(texto))
        plazos += len(RE_PLAZO.findall(texto))

    total = sum(tokens_por_reg)
    return {
        "registros": len(registros),
        "tokens": total,
        "tipos_forma": len(formas),
        "tipos_lema": len(lemas),
        "ttr_forma": round(len(formas) / total, 4) if total else 0,
        "ttr_lema": round(len(lemas) / total, 4) if total else 0,
        "longitud_media_tokens": round(statistics.mean(tokens_por_reg), 1) if tokens_por_reg else 0,
        "longitud_mediana_tokens": statistics.median(tokens_por_reg) if tokens_por_reg else 0,
        "longitud_min": min(tokens_por_reg, default=0),
        "longitud_max": max(tokens_por_reg, default=0),
        "pos": dict(pos.most_common()),
        "ner": dict(ner.most_common()),
        "ner_top5_por_etiqueta": {k: v.most_common(5) for k, v in ents_ejemplo.items()},
        "montos_regex": montos,
        "plazos_regex": plazos,
        "top_formas": formas.most_common(15),
        "top_lemas": lemas.most_common(15),
    }


def imprimir(res: dict, titulo: str) -> None:
    print(f"\n=== {titulo} ===")
    for k in ("registros", "tokens", "tipos_forma", "tipos_lema", "ttr_forma", "ttr_lema",
              "longitud_media_tokens", "longitud_mediana_tokens", "longitud_min", "longitud_max",
              "montos_regex", "plazos_regex"):
        print(f"{k:28s} {res[k]}")
    print("POS:", res["pos"])
    print("NER (spaCy):", res["ner"])


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--corpus", type=Path, default=CORPUS_POR_DEFECTO)
    ap.add_argument("--salida", type=Path, default=None,
                    help="por defecto: docs/analisis/estadisticas_base.json o estadisticas_todo.json")
    ap.add_argument("--todo", action="store_true", help="incluye las disposiciones modificatorias")
    args = ap.parse_args()

    if args.salida is None:
        args.salida = CARPETA_SALIDA / f"estadisticas_{'todo' if args.todo else 'base'}.json"
    registros = cargar(args.corpus, args.todo)
    nlp = spacy.load(MODELO, disable=["parser"])
    nlp.max_length = 2_000_000
    res = analizar(registros, nlp)
    res["alcance"] = "todo" if args.todo else "solo texto base Ley 1801"
    res["modelo"] = f"{MODELO}-{nlp.meta['version']}"

    imprimir(res, res["alcance"])
    args.salida.parent.mkdir(parents=True, exist_ok=True)
    args.salida.write_text(json.dumps(res, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"\nGuardado en {args.salida}")


if __name__ == "__main__":
    main()
