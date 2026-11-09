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
  - DETECCIÓN por PALABRAS COMPLETAS normalizadas (minúsculas, sin tildes; la normalización es
    `sin_tildes` de preprocess/texto_bm25.py), NO por raíces del stemmer. Con raíces, «caso» y
    «casa» (ambas «cas») se confundían. Un coloquial de varias palabras ('multa de la policía')
    debe aparecer completo y en ese orden. Consecuencia: las variantes (plural, género) hay que
    listarlas en el glosario («perro», «perros»).
  - AGREGADO: las palabras del término LEGAL sí pasan por la preparación de texto de BM25
    (tokens_bm25: sin stopwords, stemming o lematización), igual que el texto del índice, para
    que coincidan con él. Solo se agregan las que la pregunta todavía no tiene.
  - Se activa o desactiva con BUSQUEDA_EXPANSION en el .env (activa por defecto).

El glosario es PROVISIONAL: Santiago Castro lo reemplaza con el de la Fase 2 (mismo formato).
"""
import json
import os
import re
from functools import lru_cache
from pathlib import Path
from typing import List, Optional

from preprocess.texto_bm25 import metodo_disponible, sin_tildes, tokens_bm25

RUTA_GLOSARIO = Path(__file__).resolve().parents[1] / "glossary" / "sinonimos.json"


def expansion_activa() -> bool:
    """BUSQUEDA_EXPANSION del .env: activa salvo que valga 0, false, no, off o inactiva."""
    return os.getenv("BUSQUEDA_EXPANSION", "1").strip().lower() not in ("0", "false", "no", "off", "inactiva", "desactivada")


def palabras(texto: str) -> tuple:
    """Palabras completas normalizadas: minúsculas y sin tildes. 'Los TOMBOS, ya' -> ('los','tombos','ya')."""
    return tuple(re.findall(r"\w+", sin_tildes(texto.lower())))


@lru_cache(maxsize=None)
def _glosario(metodo: str) -> list:
    """[(término legal, sus tokens BM25, [(coloquial, sus palabras completas)])].

    `metodo` solo afecta a los tokens del término legal (que se agregan a la consulta BM25).
    """
    datos = json.loads(RUTA_GLOSARIO.read_text(encoding="utf-8"))
    entradas = []
    for legal, coloquiales in datos.items():
        if legal.startswith("_") or not isinstance(coloquiales, list):
            continue
        tokens_legal = tuple(tokens_bm25(legal, metodo))
        coloq = [(c, palabras(c)) for c in coloquiales]
        coloq = [(c, w) for c, w in coloq if w]
        if tokens_legal and coloq:
            entradas.append((legal, tokens_legal, coloq))
    return entradas


def recargar() -> None:
    """Vuelve a leer el glosario (después de editar sinonimos.json)."""
    _glosario.cache_clear()


def info() -> dict:
    """Datos para /health: si está activa y cuántas entradas tiene el glosario."""
    return {"activa": expansion_activa(), "entradas": len(_glosario(metodo_disponible()))}


def _contiene(palabras_pregunta: tuple, sub: tuple) -> bool:
    n = len(sub)
    return any(palabras_pregunta[i:i + n] == sub for i in range(len(palabras_pregunta) - n + 1))


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
    texto = palabras(pregunta)
    agregados, coincidencias = [], []
    for legal, tokens_legal, coloquiales in _glosario(metodo):
        for coloquial, palabras_col in coloquiales:
            if _contiene(texto, palabras_col):
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
