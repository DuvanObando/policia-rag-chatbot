"""Construye el índice FAISS del corpus.

Uso (desde la raíz del repo):
    python engine/indexing/build_index.py [--corpus RUTA] [--estrategia articulo]

Guarda en engine/indexing/indexes/<estrategia>/:
  - index.faiss     índice FAISS IndexFlatIP con los vectores normalizados
                    (producto punto == similitud coseno)
  - metadatos.json  modelo, fecha de construcción y, por posición del índice,
                    el fragmento (id, ubicacion, epigrafe, texto, vigencia, tema)

Estrategias:
  - articulo   un fragmento por artículo completo (epígrafe + texto)
  (más adelante: fragmentos de tamaño fijo con solapamiento)
"""
import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

import faiss
import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))  # carpeta engine/
from indexing.embeddings import (  # noqa: E402
    CORPUS_POR_DEFECTO,
    MODELO,
    cargar_corpus,
    cargar_modelo,
    embeddings_articulos,
)

CARPETA_INDICES = Path(__file__).resolve().parent / "indexes"
CAMPOS = ("id", "ubicacion", "epigrafe", "texto", "vigencia", "tema")


def fragmentos_articulo(articulos):
    """Estrategia 'articulo': un fragmento por artículo completo."""
    return articulos


ESTRATEGIAS = {"articulo": fragmentos_articulo}


def guardar_indice(indice, ruta: Path) -> None:
    # Se serializa y se escribe con Python: faiss.write_index puede fallar en
    # Windows con rutas que tienen tildes (esta carpeta tiene "Beltrán").
    ruta.write_bytes(faiss.serialize_index(indice).tobytes())


def construir(corpus=CORPUS_POR_DEFECTO, estrategia: str = "articulo") -> Path:
    if estrategia not in ESTRATEGIAS:
        raise ValueError(f"Estrategia desconocida: {estrategia!r}. Disponibles: {list(ESTRATEGIAS)}")

    fragmentos = ESTRATEGIAS[estrategia](cargar_corpus(corpus))
    modelo = cargar_modelo()
    vectores = embeddings_articulos(fragmentos, modelo).astype("float32")

    indice = faiss.IndexFlatIP(vectores.shape[1])
    indice.add(vectores)

    destino = CARPETA_INDICES / estrategia
    destino.mkdir(parents=True, exist_ok=True)
    guardar_indice(indice, destino / "index.faiss")

    metadatos = {
        "modelo": MODELO,
        "estrategia": estrategia,
        "fecha_construccion": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "corpus": str(corpus),
        "dimension": int(vectores.shape[1]),
        "n_fragmentos": len(fragmentos),
        "fragmentos": [{c: f[c] for c in CAMPOS} for f in fragmentos],
    }
    (destino / "metadatos.json").write_text(
        json.dumps(metadatos, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    return destino


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawTextHelpFormatter)
    ap.add_argument("--corpus", default=str(CORPUS_POR_DEFECTO))
    ap.add_argument("--estrategia", default="articulo", choices=list(ESTRATEGIAS))
    args = ap.parse_args()
    destino = construir(args.corpus, args.estrategia)
    meta = json.loads((destino / "metadatos.json").read_text(encoding="utf-8"))
    print(f"Índice '{args.estrategia}' construido en {destino}")
    print(f"  fragmentos: {meta['n_fragmentos']} | dimensión: {meta['dimension']} | modelo: {meta['modelo']}")


if __name__ == "__main__":
    main()
