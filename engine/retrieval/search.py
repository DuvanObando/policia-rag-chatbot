"""Búsqueda de fragmentos relevantes sobre el índice FAISS.

Uso como librería (desde engine/ o con engine/ en sys.path):
    from retrieval.search import buscar
    fragmentos = buscar("¿Qué pasa si no pago una multa?", k=3)

Uso por línea de comandos (desde la raíz del repo):
    python engine/retrieval/search.py "¿Qué pasa si no pago una multa?" [-k 3]
    python engine/retrieval/search.py --demo

El modelo y el índice se cargan UNA sola vez por proceso (en la primera llamada,
o antes con precargar()) y se reutilizan en las llamadas siguientes.
"""
import argparse
import json
import sys
import time
from functools import lru_cache
from pathlib import Path
from typing import List, Optional

import faiss
import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))  # carpeta engine/
from indexing.embeddings import PREGUNTAS_DEMO, cargar_modelo, embeddings_preguntas  # noqa: E402

CARPETA_INDICES = Path(__file__).resolve().parents[1] / "indexing" / "indexes"
ORDINALES = {"PRIMERO": "I", "SEGUNDO": "II", "TERCERO": "III", "CUARTO": "IV", "QUINTO": "V"}

# Modos de búsqueda. Hoy solo "semantico"; BM25 / híbrido se agregan aquí
# (nuevos valores de `modo`) sin cambiar la firma de buscar().
MODOS = ("semantico",)


@lru_cache(maxsize=1)
def _modelo():
    return cargar_modelo()


@lru_cache(maxsize=None)
def _indice(estrategia: str):
    """Carga (una sola vez por estrategia) el índice FAISS y sus metadatos."""
    carpeta = CARPETA_INDICES / estrategia
    if not (carpeta / "index.faiss").exists():
        raise FileNotFoundError(
            f"No existe el índice '{estrategia}'. Constrúyelo con: "
            f"python engine/indexing/build_index.py --estrategia {estrategia}"
        )
    datos = (carpeta / "index.faiss").read_bytes()  # lectura con Python: evita fallos con tildes en la ruta
    indice = faiss.deserialize_index(np.frombuffer(datos, dtype="uint8"))
    meta = json.loads((carpeta / "metadatos.json").read_text(encoding="utf-8"))
    return indice, meta


def precargar(estrategia: str = "articulo") -> None:
    """Carga modelo e índice por adelantado (p. ej. al arrancar la API)."""
    _modelo()
    _indice(estrategia)


def _parte(texto: Optional[str]) -> Optional[str]:
    """'Libro Segundo. De la libertad...' -> 'Libro Segundo' (lo que va antes del primer punto)."""
    return texto.split(".")[0].strip() if texto else None


def id_articulo(id_fragmento: str) -> str:
    """'art-140-f2' -> 'art-140' (un id de artículo se queda igual)."""
    return id_fragmento.split("-f")[0]


def formatear_ubicacion(ub: dict) -> str:
    """Ubicación legible, p. ej. 'Libro II, Título XIV, Capítulo II, Artículo 140'."""
    partes = []
    for clave in ("libro", "titulo", "capitulo", "articulo"):
        p = _parte(ub.get(clave))
        if not p:
            continue
        if clave == "libro":
            palabras = p.split()
            if len(palabras) > 1 and palabras[1].upper() in ORDINALES:
                p = f"Libro {ORDINALES[palabras[1].upper()]}"
        partes.append(p)
    return ", ".join(partes)


def buscar(pregunta: str, k: int = 3, estrategia: str = "articulo", modo: str = "semantico") -> List[dict]:
    """Devuelve los k fragmentos más relevantes, de mayor a menor score.

    Formato de cada fragmento (docs/api_contract.md):
        id, ubicacion (cadena), epigrafe, texto, score, vigencia, tema

    `modo` está para poder agregar BM25 o búsqueda híbrida más adelante
    sin cambiar la firma.
    """
    if modo not in MODOS:
        raise ValueError(f"Modo no soportado: {modo!r}. Disponibles: {list(MODOS)}")
    indice, meta = _indice(estrategia)
    consulta = embeddings_preguntas([pregunta], _modelo()).astype("float32")

    # Con trozos, varios del mismo artículo pueden salir a la vez. Se conserva el de
    # mayor score por artículo y se amplía la búsqueda hasta tener k artículos distintos.
    agrupar = estrategia == "fragmentos"
    n = min(k * 4 if agrupar else k, indice.ntotal)
    while True:
        scores, posiciones = indice.search(consulta, n)
        elegidos, vistos = [], set()
        for score, pos in zip(scores[0], posiciones[0]):
            f = meta["fragmentos"][pos]
            if agrupar:
                art = id_articulo(f["id"])
                if art in vistos:
                    continue
                vistos.add(art)
            elegidos.append((score, f))
            if len(elegidos) == k:
                break
        if len(elegidos) == k or n >= indice.ntotal:
            break
        n = min(n * 2, indice.ntotal)

    resultados = []
    for score, f in elegidos:
        resultados.append({
            "id": f["id"],
            "ubicacion": formatear_ubicacion(f["ubicacion"]),
            "epigrafe": f["epigrafe"],
            "texto": f["texto"],
            "score": float(score),
            "vigencia": f["vigencia"],
            "tema": f["tema"],
        })
    return resultados


def _mostrar(pregunta: str, resultados: List[dict]) -> None:
    print(f"\n{pregunta}")
    for r in resultados:
        print(f"  {r['id'].replace('art-', ''):>4}  {r['score']:.4f}  {r['epigrafe']}  [{r['vigencia']}]")
        print(f"        {r['ubicacion']}")


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawTextHelpFormatter)
    ap.add_argument("pregunta", nargs="*")
    ap.add_argument("-k", type=int, default=3)
    ap.add_argument("--estrategia", default="articulo")
    ap.add_argument("--demo", action="store_true", help="prueba 3 preguntas y mide tiempos")
    args = ap.parse_args()

    preguntas = PREGUNTAS_DEMO if args.demo else [" ".join(args.pregunta)] if args.pregunta else []
    if not preguntas:
        ap.error("indica una pregunta o usa --demo")

    t0 = time.perf_counter()
    precargar(args.estrategia)
    t_carga = time.perf_counter() - t0

    tiempos = []
    for p in preguntas:
        t = time.perf_counter()
        res = buscar(p, k=args.k, estrategia=args.estrategia)
        tiempos.append(time.perf_counter() - t)
        _mostrar(p, res)

    print(f"\nCarga inicial (modelo + índice): {t_carga:.2f} s")
    print("Tiempo por búsqueda: " + ", ".join(f"{t * 1000:.0f} ms" for t in tiempos))


if __name__ == "__main__":
    main()
