"""Embeddings de artículos y preguntas con intfloat/multilingual-e5-base.

Reglas del modelo E5:
  - cada artículo se codifica como "passage: <texto>"
  - cada pregunta se codifica como "query: <pregunta>"
  - los vectores se normalizan (norma 1), así el producto punto es la similitud coseno.

Se genera un embedding por artículo completo (epígrafe + texto).

Uso (desde la raíz del repo):
    python engine/indexing/embeddings.py [--corpus RUTA] [--demo]

  --corpus  ruta del corpus JSON (por defecto CORPUS_RUTA del .env, o el corpus de la Fase 1)
  --demo    muestra la tabla de tokens por artículo y prueba 3 preguntas
"""
import argparse
import os
import sys
from pathlib import Path
from typing import List

import numpy as np
from dotenv import load_dotenv
from sentence_transformers import SentenceTransformer

MODELO = "intfloat/multilingual-e5-base"
PREFIJO_ARTICULO = "passage: "
PREFIJO_PREGUNTA = "query: "
RAIZ = Path(__file__).resolve().parents[2]
load_dotenv(RAIZ / ".env")
sys.path.insert(0, str(RAIZ / "engine"))
from indexing.cargador_corpus import cargar as _cargar_adaptado  # noqa: E402

# Corpus que usa el motor. CORPUS_RUTA en el .env (relativa a la raíz del repo o absoluta).
#   corpus de la Fase 1 (real):  corpus/procesados/corpus_ley_1801.json   <- por defecto
#   corpus de muestra (10 art.): corpus/muestra/codigo_muestra.json
CORPUS_REAL = RAIZ / "corpus" / "procesados" / "corpus_ley_1801.json"
CORPUS_MUESTRA = RAIZ / "corpus" / "muestra" / "codigo_muestra.json"
_ruta_env = os.getenv("CORPUS_RUTA", "").strip()
CORPUS_POR_DEFECTO = (Path(_ruta_env) if Path(_ruta_env).is_absolute() else RAIZ / _ruta_env) if _ruta_env else CORPUS_REAL

PREGUNTAS_DEMO = [
    "¿Me pueden multar por tomar licor en el parque?",
    "¿La policía puede entrar a mi casa sin orden?",
    "¿Qué pasa si no pago una multa?",
]


def cargar_corpus(ruta=CORPUS_POR_DEFECTO) -> List[dict]:
    """Corpus en el esquema del motor; adapta el formato de la Fase 1 sin tocar el archivo."""
    return _cargar_adaptado(ruta)


def texto_articulo(articulo: dict) -> str:
    """Texto que se vectoriza: epígrafe + texto del artículo completo."""
    return f"{articulo['epigrafe']}\n{articulo['texto']}"


def cargar_modelo(nombre: str = MODELO) -> SentenceTransformer:
    return SentenceTransformer(nombre)


def embeddings_articulos(articulos: List[dict], modelo: SentenceTransformer) -> np.ndarray:
    """Un vector normalizado por artículo. Forma: (n_articulos, dimension)."""
    textos = [PREFIJO_ARTICULO + texto_articulo(a) for a in articulos]
    # Barra de progreso (en stderr) al indexar muchos textos: en CPU puede tardar varios minutos.
    return modelo.encode(textos, normalize_embeddings=True, convert_to_numpy=True,
                         show_progress_bar=len(textos) > 50)


def embeddings_preguntas(preguntas: List[str], modelo: SentenceTransformer) -> np.ndarray:
    """Un vector normalizado por pregunta. Forma: (n_preguntas, dimension)."""
    textos = [PREFIJO_PREGUNTA + p for p in preguntas]
    return modelo.encode(textos, normalize_embeddings=True, convert_to_numpy=True)


def contar_tokens(articulos: List[dict], modelo: SentenceTransformer) -> List[int]:
    """Tokens que ve el modelo por artículo (con el prefijo "passage: ")."""
    tok = modelo.tokenizer
    return [len(tok(PREFIJO_ARTICULO + texto_articulo(a))["input_ids"]) for a in articulos]


def demo(articulos: List[dict], modelo: SentenceTransformer, vectores: np.ndarray) -> None:
    limite = modelo.max_seq_length
    print(f"\nTokens por artículo (límite del modelo: {limite})")
    print(f"{'Artículo':<10}{'Tokens':>8}  ¿Supera el límite?")
    for a, n in zip(articulos, contar_tokens(articulos, modelo)):
        print(f"{a['id'].replace('art-', ''):<10}{n:>8}  {'SÍ, se corta' if n > limite else 'no'}")

    print(f"\nDimensión del vector: {vectores.shape[1]}  (matriz: {vectores.shape})")
    print(f"Norma del primer vector: {np.linalg.norm(vectores[0]):.4f}")

    for p, q in zip(PREGUNTAS_DEMO, embeddings_preguntas(PREGUNTAS_DEMO, modelo)):
        scores = vectores @ q  # coseno, porque están normalizados
        print(f"\n{p}")
        for i in np.argsort(-scores):
            a = articulos[i]
            print(f"  {a['id'].replace('art-', ''):>4}  {scores[i]:.4f}  {a['epigrafe']}")


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawTextHelpFormatter)
    ap.add_argument("--corpus", default=str(CORPUS_POR_DEFECTO))
    ap.add_argument("--demo", action="store_true")
    args = ap.parse_args()

    articulos = cargar_corpus(args.corpus)
    modelo = cargar_modelo()
    vectores = embeddings_articulos(articulos, modelo)
    print(f"{len(articulos)} artículos -> vectores {vectores.shape}")
    if args.demo:
        demo(articulos, modelo, vectores)


if __name__ == "__main__":
    main()
