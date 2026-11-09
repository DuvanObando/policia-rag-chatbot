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
import re
import sys
import time
from functools import lru_cache
from pathlib import Path
from typing import List, Optional

import faiss
import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))  # carpeta engine/
from indexing.embeddings import PREGUNTAS_DEMO, cargar_modelo, embeddings_preguntas  # noqa: E402
from retrieval.clasificador import articulos_mencionados, clasificar, empujes  # noqa: E402

CARPETA_INDICES = Path(__file__).resolve().parents[1] / "indexing" / "indexes"
ORDINALES = {"PRIMERO": "I", "SEGUNDO": "II", "TERCERO": "III", "CUARTO": "IV", "QUINTO": "V"}

# Modos de búsqueda. Hoy solo "semantico"; BM25 / híbrido se agregan aquí
# (nuevos valores de `modo`) sin cambiar la firma de buscar().
MODOS = ("semantico",)

POOL_MAX = 2000  # máximo de candidatos que se traen del índice para reordenar (empuje por tema)


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


def info_indice(estrategia: str = "articulo") -> dict:
    """Datos del índice cargado: estrategia, modelo de embeddings y número de fragmentos."""
    indice, meta = _indice(estrategia)
    return {"estrategia": estrategia, "modelo": meta["modelo"], "fragmentos": int(indice.ntotal)}


@lru_cache(maxsize=None)
def _articulos_del_corpus(estrategia: str) -> dict:
    """Artículos completos del corpus con que se construyó el índice, por id (se carga una vez)."""
    ruta = Path(_indice(estrategia)[1]["corpus"])
    return {a["id"]: a for a in json.loads(ruta.read_text(encoding="utf-8"))}


def articulo_completo(id_fragmento: str, estrategia: str = "fragmentos") -> dict:
    """Artículo completo al que pertenece un fragmento (para small-to-big).

    Devuelve id, ubicacion (cadena), epigrafe, texto, vigencia y tema del artículo.
    """
    a = _articulos_del_corpus(estrategia).get(id_articulo(id_fragmento))
    if a is None:
        # Documento complementario (subido por /upload_pdf/): no está en el corpus,
        # así que se usa el propio fragmento como contexto.
        _, meta = _indice(estrategia)
        a = next(f for f in meta["fragmentos"] if f["id"] == id_fragmento)
        a = {**a, "id": id_articulo(a["id"])}
    return {
        "id": a["id"],
        "ubicacion": formatear_ubicacion(a["ubicacion"]),
        "epigrafe": a["epigrafe"],
        "texto": a["texto"],
        "vigencia": a["vigencia"],
        "tema": a["tema"],
    }


def _parte(texto: Optional[str]) -> Optional[str]:
    """'Libro Segundo. De la libertad...' -> 'Libro Segundo' (lo que va antes del primer punto)."""
    return texto.split(".")[0].strip() if texto else None


def id_articulo(id_fragmento: str) -> str:
    """'art-140-f2' -> 'art-140' (un id de artículo se queda igual)."""
    return re.sub(r"-f\d+$", "", id_fragmento)


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


def buscar(pregunta: str, k: int = 3, estrategia: str = "articulo", modo: str = "semantico",
           clasificador: bool = True) -> List[dict]:
    """Devuelve los k fragmentos más relevantes, de mayor a menor score.

    Formato de cada fragmento (docs/api_contract.md):
        id, ubicacion (cadena), epigrafe, texto, score, vigencia, tema

    `modo` está para poder agregar BM25 o búsqueda híbrida más adelante
    sin cambiar la firma.

    Con `clasificador=True` (por defecto):
      - Tema: el clasificador (retrieval/clasificador.py + temas.json) detecta el tema de la
        pregunta y SUMA un empuje al score de los candidatos de ese tema. Es un empuje, nunca
        un filtro: un candidato de otro tema todavía puede ganar. El `score` devuelto incluye
        el empuje, que es el que decide el orden.
      - Artículo por número: si la pregunta pide "artículo N" / "art. N" y ese artículo existe
        en el índice, va primero (en ese caso la lista puede no quedar ordenada por score).
    Con `clasificador=False` el orden es solo por similitud semántica.

    Se devuelve como máximo un fragmento por artículo (el de mayor score).
    """
    if modo not in MODOS:
        raise ValueError(f"Modo no soportado: {modo!r}. Disponibles: {list(MODOS)}")
    indice, meta = _indice(estrategia)
    consulta = embeddings_preguntas([pregunta], _modelo()).astype("float32")

    # Se piden todos los candidatos del índice (hasta POOL_MAX): el empuje por tema puede
    # subir a uno que quedaba fuera de los primeros k.
    scores, posiciones = indice.search(consulta, min(POOL_MAX, indice.ntotal))
    candidatos = [(float(sc), meta["fragmentos"][pos]) for sc, pos in zip(scores[0], posiciones[0])]

    pedidos = []
    if clasificador:
        empuje = empujes(clasificar(pregunta))
        if empuje:
            candidatos = [(sc + empuje.get(f["tema"], 0.0), f) for sc, f in candidatos]
            candidatos.sort(key=lambda c: -c[0])
        existentes = {id_articulo(f["id"]) for _, f in candidatos}
        pedidos = [f"art-{n}" for n in articulos_mencionados(pregunta) if f"art-{n}" in existentes]

    # Un solo fragmento por artículo: el de mayor score.
    mejores, vistos = [], set()
    for sc, f in candidatos:
        art = id_articulo(f["id"])
        if art not in vistos:
            vistos.add(art)
            mejores.append((sc, f))

    # Artículos pedidos por número: primero y en el orden en que se pidieron.
    primeros = [next(c for c in mejores if id_articulo(c[1]["id"]) == art) for art in pedidos]
    resto = [c for c in mejores if id_articulo(c[1]["id"]) not in pedidos]
    elegidos = (primeros + resto)[:k]

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
    ap.add_argument("--sin-clasificador", action="store_true", help="solo similitud semántica, sin empuje por tema")
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
        res = buscar(p, k=args.k, estrategia=args.estrategia, clasificador=not args.sin_clasificador)
        tiempos.append(time.perf_counter() - t)
        _mostrar(p, res)

    print(f"\nCarga inicial (modelo + índice): {t_carga:.2f} s")
    print("Tiempo por búsqueda: " + ", ".join(f"{t * 1000:.0f} ms" for t in tiempos))


if __name__ == "__main__":
    main()
