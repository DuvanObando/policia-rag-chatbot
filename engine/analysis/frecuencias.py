"""Frecuencias, n-gramas, colocaciones y KWIC del corpus (Fase 2, dia 4).

Uso, desde la raiz del repositorio y con el entorno virtual activo:
    python engine/analysis/frecuencias.py
    python engine/analysis/frecuencias.py --todo
    python engine/analysis/frecuencias.py --terminos "multa" "arresto"   # otros terminos

Por defecto analiza el texto base de la Ley 1801; con --todo incluye las normas que la modifican.
Terminos por defecto: multa, comparendo, medida correctiva, espacio publico. Se buscan por lema y
sin tildes, asi "multas" y "multar" cuentan como "multa", "medidas correctivas" como "medida correctiva"
y "espacios publicos" como "espacio publico". Las colocaciones no incluyen palabras vacias ni numeros.

Salidas en docs/analisis/ (base o todo segun la opcion):
    frecuencias_<alcance>.json   frecuencias, n-gramas, colocaciones y conteo de cada termino
    kwic_<alcance>.txt           concordancias (palabra clave en contexto), legible
"""
import argparse
import json
import math
import re
import unicodedata
from collections import Counter
from pathlib import Path

import spacy

RAIZ = Path(__file__).resolve().parents[2]
CORPUS_POR_DEFECTO = RAIZ / "corpus" / "procesados" / "corpus_ley_1801.json"
CARPETA_SALIDA = RAIZ / "docs" / "analisis"
MODELO = "es_core_news_sm"
TERMINOS_POR_DEFECTO = ["multa", "comparendo", "medida correctiva", "espacio publico"]
VENTANA_KWIC = 8        # palabras de contexto a cada lado
VENTANA_COLOC = 4       # ventana para colocaciones
MIN_COLOC = 5           # frecuencia minima conjunta para listar una colocacion
KWIC_MAX = 30           # ejemplos guardados por termino


def sin_tildes(s: str) -> str:
    return "".join(c for c in unicodedata.normalize("NFD", s) if unicodedata.category(c) != "Mn")


def norma(s: str) -> str:
    return sin_tildes(s.lower())


def cargar(ruta: Path, todo: bool):
    with open(ruta, encoding="utf-8") as f:
        datos = json.load(f)
    if not todo:
        datos = [d for d in datos if d.get("tipo_disposicion") == "texto_fuente_ley_base"]
    return datos


def es_palabra(t) -> bool:
    return not (t.is_space or t.is_punct) and bool(re.search(r"\w", t.text))


def lema(t) -> str:
    return norma(t.lemma_ or t.text)


def ngramas(secuencia, n):
    """n-gramas de lemas que no empiezan ni terminan en palabra vacia (de, la, que...)."""
    cuenta = Counter()
    for i in range(len(secuencia) - n + 1):
        ventana = secuencia[i:i + n]
        if ventana[0][1] or ventana[-1][1]:
            continue
        cuenta[" ".join(l for l, _ in ventana)] += 1
    return cuenta


def posiciones(lemas, objetivo):
    """Indices donde empieza la secuencia de lemas `objetivo` (lista de lemas)."""
    n = len(objetivo)
    return [i for i in range(len(lemas) - n + 1) if lemas[i:i + n] == objetivo]


def pmi(c_xy, c_x, c_y, total):
    return math.log2((c_xy * total) / (c_x * c_y))


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--corpus", type=Path, default=CORPUS_POR_DEFECTO)
    ap.add_argument("--carpeta-salida", type=Path, default=CARPETA_SALIDA)
    ap.add_argument("--todo", action="store_true", help="incluye las disposiciones modificatorias")
    ap.add_argument("--terminos", nargs="+", default=TERMINOS_POR_DEFECTO,
                    help="terminos a analizar (entre comillas si tienen varias palabras)")
    args = ap.parse_args()

    alcance = "todo" if args.todo else "base"
    registros = cargar(args.corpus, args.todo)
    nlp = spacy.load(MODELO, disable=["parser", "ner"])
    nlp.max_length = 2_000_000

    # Los terminos se lematizan igual que el corpus ("medida correctiva" -> medida correctivo).
    objetivos = {t: [lema(x) for x in nlp(t) if es_palabra(x)] for t in args.terminos}

    frec_lemas = Counter()          # solo palabras con contenido (sin palabras vacias)
    frec_total_lemas = Counter()    # todas, para PMI
    big, tri = Counter(), Counter()
    total_palabras = 0
    conteo_termino = {t: 0 for t in objetivos}
    registros_con = {t: set() for t in objetivos}
    vecinos = {t: Counter() for t in objetivos}
    kwic = {t: [] for t in objetivos}

    textos = [r["texto"] for r in registros]
    for r, doc in zip(registros, nlp.pipe(textos, batch_size=8)):
        palabras = [t for t in doc if es_palabra(t)]
        lemas = [lema(t) for t in palabras]
        marcados = [(l, t.is_stop) for l, t in zip(lemas, palabras)]
        total_palabras += len(palabras)
        frec_total_lemas.update(lemas)
        frec_lemas.update(l for l, vacia in marcados if not vacia)
        big.update(ngramas(marcados, 2))
        tri.update(ngramas(marcados, 3))

        for termino, obj in objetivos.items():
            for i in posiciones(lemas, obj):
                conteo_termino[termino] += 1
                registros_con[termino].add(r["id"])
                a, b = max(0, i - VENTANA_COLOC), min(len(palabras), i + len(obj) + VENTANA_COLOC)
                for j in range(a, b):
                    if not (i <= j < i + len(obj)) and not palabras[j].is_stop and not palabras[j].like_num:
                        vecinos[termino][lemas[j]] += 1
                if len(kwic[termino]) < KWIC_MAX:
                    ini, fin = max(0, i - VENTANA_KWIC), min(len(palabras), i + len(obj) + VENTANA_KWIC)
                    izq = " ".join(p.text for p in palabras[ini:i])
                    centro = " ".join(p.text for p in palabras[i:i + len(obj)])
                    der = " ".join(p.text for p in palabras[i + len(obj):fin])
                    kwic[termino].append({"registro": r["id"], "izq": izq, "centro": centro, "der": der})

    colocaciones = {}
    for termino, cuenta in vecinos.items():
        c_x = conteo_termino[termino]
        filas = []
        for pal, c_xy in cuenta.items():
            if c_xy >= MIN_COLOC and c_x:
                filas.append({"palabra": pal, "juntas": c_xy, "frecuencia": frec_total_lemas[pal],
                              "pmi": round(pmi(c_xy, c_x, frec_total_lemas[pal], total_palabras), 2)})
        colocaciones[termino] = {
            "por_frecuencia": sorted(filas, key=lambda f: -f["juntas"])[:15],
            "por_pmi": sorted(filas, key=lambda f: -f["pmi"])[:15],
        }

    resultado = {
        "alcance": "todo el corpus" if args.todo else "solo texto base Ley 1801",
        "modelo": f"{MODELO}-{nlp.meta['version']}",
        "registros": len(registros),
        "palabras": total_palabras,
        "top_lemas": frec_lemas.most_common(40),
        "top_bigramas": big.most_common(30),
        "top_trigramas": tri.most_common(30),
        "terminos": {t: {"ocurrencias": conteo_termino[t], "registros": len(registros_con[t])} for t in objetivos},
        "colocaciones": colocaciones,
    }
    args.carpeta_salida.mkdir(parents=True, exist_ok=True)
    ruta_json = args.carpeta_salida / f"frecuencias_{alcance}.json"
    ruta_json.write_text(json.dumps(resultado, ensure_ascii=False, indent=2), encoding="utf-8")

    lineas = [f"KWIC ({resultado['alcance']}), ventana de {VENTANA_KWIC} palabras, hasta {KWIC_MAX} ejemplos por termino", ""]
    for t, filas in kwic.items():
        lineas.append(f"=== {t} ({conteo_termino[t]} ocurrencias en {len(registros_con[t])} registros) ===")
        for k in filas:
            lineas.append(f"{k['izq']:>60} [{k['centro']}] {k['der']}   ({k['registro']})")
        lineas.append("")
    ruta_kwic = args.carpeta_salida / f"kwic_{alcance}.txt"
    ruta_kwic.write_text("\n".join(lineas), encoding="utf-8")

    print(f"\n=== {resultado['alcance']}: {len(registros)} registros, {total_palabras} palabras ===")
    print("\nTop lemas (sin palabras vacias):", resultado["top_lemas"][:15])
    print("\nTop bigramas:", resultado["top_bigramas"][:12])
    print("\nTop trigramas:", resultado["top_trigramas"][:8])
    for t in objetivos:
        d = resultado["terminos"][t]
        print(f"\n--- {t}: {d['ocurrencias']} ocurrencias en {d['registros']} registros ---")
        print("  colocaciones (por frecuencia):", [(f["palabra"], f["juntas"]) for f in colocaciones[t]["por_frecuencia"][:8]])
        print("  colocaciones (por PMI):", [(f["palabra"], f["pmi"]) for f in colocaciones[t]["por_pmi"][:6]])
    print(f"\nGuardado en {ruta_json}\nGuardado en {ruta_kwic}")


if __name__ == "__main__":
    main()
