"""Expansión de consultas con glosario (solo para la búsqueda léxica BM25).

    from retrieval.expansion import expandir
    expandir("¿Me ponen boleta si me cogen tomando guaro?")
    # '¿Me ponen boleta si me cogen tomando guaro? orden de comparendo bebidas alcohólicas'

El usuario dice «guaro», «boleta», «tombos»; la ley dice «bebidas alcohólicas», «orden de
comparendo», «autoridades de policía». BM25 solo compara palabras, así que no los une. Esta
expansión detecta los términos coloquiales del glosario (engine/glossary/sinonimos.json) y le
agrega a la consulta léxica las palabras del término legal.

Reglas:
  - Solo se aplica a la consulta de BM25 (modos `lexico` e `hibrido`). NUNCA a la consulta
    semántica: el modelo de embeddings ya entiende «guaro» y no necesita ayuda; agregarle
    términos solo desviaría el significado.
  - Se compara con la MISMA preparación de texto del índice (preprocess/texto_bm25.py:
    minúsculas, sin tildes, sin stopwords, lematizado o stemmer). Así «drogas» encuentra
    «droga» y no hay que listar plurales.
  - Solo se agregan palabras que la pregunta todavía no tiene (no se duplican).
  - Se activa o desactiva con BUSQUEDA_EXPANSION en el .env (activa por defecto).

El glosario es PROVISIONAL: Santiago Castro lo reemplaza con el de la Fase 2 (mismo formato).
"""
import json
import os
from functools import lru_cache
from pathlib import Path
from typing import List, Optional

from preprocess.texto_bm25 import metodo_disponible, tokens_bm25

RUTA_GLOSARIO = Path(__file__).resolve().parents[1] / "glossary" / "sinonimos.json"


def expansion_activa() -> bool:
    """BUSQUEDA_EXPANSION del .env: activa salvo que valga 0, false, no, off o inactiva."""
    return os.getenv("BUSQUEDA_EXPANSION", "1").strip().lower() not in ("0", "false", "no", "off", "inactiva", "desactivada")


@lru_cache(maxsize=None)
def _glosario(metodo: str) -> list:
    """[(término legal, sus tokens, [(coloquial, sus tokens)])], preparado con el método `metodo`."""
    datos = json.loads(RUTA_GLOSARIO.read_text(encoding="utf-8"))
    entradas = []
    for legal, coloquiales in datos.items():
        if legal.startswith("_") or not isinstance(coloquiales, list):
            continue
        tokens_legal = tuple(tokens_bm25(legal, metodo))
        coloq = [(c, tuple(tokens_bm25(c, metodo))) for c in coloquiales]
        coloq = [(c, t) for c, t in coloq if t]  # un coloquial hecho solo de stopwords no sirve
        if tokens_legal and coloq:
            entradas.append((legal, tokens_legal, coloq))
    return entradas


def recargar() -> None:
    """Vuelve a leer el glosario (después de editar sinonimos.json)."""
    _glosario.cache_clear()


def info() -> dict:
    """Datos para /health: si está activa y cuántas entradas tiene el glosario."""
    return {"activa": expansion_activa(), "entradas": len(_glosario(metodo_disponible()))}


def _contiene(tokens: List[str], sub: tuple) -> bool:
    n = len(sub)
    return any(tuple(tokens[i:i + n]) == sub for i in range(len(tokens) - n + 1))


def expandir_detalle(pregunta: str, metodo: Optional[str] = None) -> dict:
    """Expansión con detalle:
        tokens         tokens de la pregunta + los agregados (lo que se le pasa a BM25)
        agregados      solo los tokens agregados
        coincidencias  [{"coloquial", "legal", "agregados"}]
    `metodo` debe ser el de preparación del índice BM25 (el índice lo guarda).
    """
    metodo = metodo or metodo_disponible()
    base = tokens_bm25(pregunta, metodo)
    presentes = set(base)
    agregados, coincidencias = [], []
    for legal, tokens_legal, coloquiales in _glosario(metodo):
        for coloquial, tokens_col in coloquiales:
            if _contiene(base, tokens_col):
                nuevos = [t for t in tokens_legal if t not in presentes and t not in agregados]
                if nuevos:
                    agregados.extend(nuevos)
                    coincidencias.append({"coloquial": coloquial, "legal": legal, "agregados": nuevos})
                break  # con un coloquial por término legal basta
    return {"tokens": base + agregados, "agregados": agregados, "coincidencias": coincidencias}


def expandir(pregunta: str, metodo: Optional[str] = None) -> str:
    """La pregunta con los términos legales agregados al final (legible, para mostrar o depurar)."""
    legales = [c["legal"] for c in expandir_detalle(pregunta, metodo)["coincidencias"]]
    return " ".join([pregunta] + legales)


def tokens_consulta_lexica(pregunta: str, metodo: str) -> List[str]:
    """Tokens que se le pasan a BM25: con expansión si está activa, o solo los de la pregunta."""
    if expansion_activa():
        return expandir_detalle(pregunta, metodo)["tokens"]
    return tokens_bm25(pregunta, metodo)
