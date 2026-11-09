"""Construye el índice FAISS del corpus.

Uso (desde la raíz del repo):
    python engine/indexing/build_index.py [--corpus RUTA] [--estrategia articulo|fragmentos]
                                          [--tamano 250] [--solape 50]

Guarda en engine/indexing/indexes/<estrategia>/:
  - index.faiss     índice FAISS IndexFlatIP con los vectores normalizados
                    (producto punto == similitud coseno)
  - metadatos.json  modelo, fecha de construcción y, por posición del índice,
                    el fragmento (id, ubicacion, epigrafe, texto, vigencia, tema)

Estrategias:
  - articulo     un fragmento por artículo completo (epígrafe + texto).
                 El modelo corta lo que pase de 512 tokens.
  - fragmentos   trozos de tamaño fijo medido con el tokenizer del modelo
                 (--tamano tokens, con --solape tokens de solapamiento).
                 Cada trozo hereda los metadatos de su artículo, tiene id propio
                 (art-140-f2) y se vectoriza con el epígrafe antepuesto.
"""
import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

import faiss

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
TAMANO_POR_DEFECTO = 250
SOLAPE_POR_DEFECTO = 50


def fragmentos_articulo(articulos, modelo, **_):
    """Estrategia 'articulo': un fragmento por artículo completo."""
    return articulos


def trozos_de_texto(texto: str, tokenizer, tamano: int, solape: int):
    """Parte `texto` en ventanas de `tamano` tokens que se solapan `solape` tokens.

    Se cortan los caracteres originales usando las posiciones (offsets) del
    tokenizer, así cada trozo es texto literal del artículo.
    """
    if solape >= tamano:
        raise ValueError("El solapamiento debe ser menor que el tamaño del trozo")
    enc = tokenizer(texto, add_special_tokens=False, return_offsets_mapping=True)
    offsets = enc["offset_mapping"]
    n = len(offsets)
    trozos, inicio, paso = [], 0, tamano - solape
    while True:
        fin = min(inicio + tamano, n)
        trozos.append(texto[offsets[inicio][0]:offsets[fin - 1][1]].strip())
        if fin >= n:
            break
        inicio += paso
    return trozos


def fragmentos_por_tamano(articulos, modelo, tamano=TAMANO_POR_DEFECTO, solape=SOLAPE_POR_DEFECTO, **_):
    """Estrategia 'fragmentos': trozos de tamaño fijo con solapamiento.

    El epígrafe se antepone al vectorizar (embeddings_articulos usa epígrafe + texto),
    así cada trozo conserva el contexto de qué artículo es.
    """
    resultado = []
    for a in articulos:
        for i, trozo in enumerate(trozos_de_texto(a["texto"], modelo.tokenizer, tamano, solape), start=1):
            f = {c: a[c] for c in CAMPOS}
            f["id"] = f"{a['id']}-f{i}"
            f["texto"] = trozo
            resultado.append(f)
    return resultado


ESTRATEGIAS = {"articulo": fragmentos_articulo, "fragmentos": fragmentos_por_tamano}


def guardar_indice(indice, ruta: Path) -> None:
    # Se serializa y se escribe con Python: faiss.write_index puede fallar en
    # Windows con rutas que tienen tildes (esta carpeta tiene "Beltrán").
    ruta.write_bytes(faiss.serialize_index(indice).tobytes())


def construir(corpus=CORPUS_POR_DEFECTO, estrategia: str = "articulo",
              tamano: int = TAMANO_POR_DEFECTO, solape: int = SOLAPE_POR_DEFECTO) -> Path:
    if estrategia not in ESTRATEGIAS:
        raise ValueError(f"Estrategia desconocida: {estrategia!r}. Disponibles: {list(ESTRATEGIAS)}")

    modelo = cargar_modelo()
    fragmentos = ESTRATEGIAS[estrategia](cargar_corpus(corpus), modelo, tamano=tamano, solape=solape)
    vectores = embeddings_articulos(fragmentos, modelo).astype("float32")

    indice = faiss.IndexFlatIP(vectores.shape[1])
    indice.add(vectores)

    destino = CARPETA_INDICES / estrategia
    destino.mkdir(parents=True, exist_ok=True)
    guardar_indice(indice, destino / "index.faiss")

    metadatos = {
        "modelo": MODELO,
        "estrategia": estrategia,
        "parametros": {"tamano": tamano, "solape": solape} if estrategia == "fragmentos" else {},
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
    ap.add_argument("--tamano", type=int, default=TAMANO_POR_DEFECTO, help="tokens por trozo (estrategia fragmentos)")
    ap.add_argument("--solape", type=int, default=SOLAPE_POR_DEFECTO, help="tokens de solapamiento (estrategia fragmentos)")
    args = ap.parse_args()
    destino = construir(args.corpus, args.estrategia, args.tamano, args.solape)
    meta = json.loads((destino / "metadatos.json").read_text(encoding="utf-8"))
    print(f"Índice '{args.estrategia}' construido en {destino}")
    print(f"  fragmentos: {meta['n_fragmentos']} | dimensión: {meta['dimension']} | modelo: {meta['modelo']}")
    if meta["parametros"]:
        print(f"  parámetros: {meta['parametros']}")


if __name__ == "__main__":
    main()
