"""Tema de cada artículo de la Ley 1801 según la propuesta de Santiago Castro (Fase 2).

El corpus de Wilder trae en `tema` un valor genérico ("texto fuente Ley 1801") en los 249 artículos,
así que el clasificador temático no tenía a qué artículos empujar. Castro propuso 32 temas por rangos
de artículos (docs/analisis/propuesta_temas.json); el mapeo id -> tema está en
engine/retrieval/temas_por_articulo.json y los temas (con sus palabras clave) en temas.json.

NO se edita el corpus: el tema se reemplaza al cargarlo (cargador_corpus.cargar) y al leer un
índice ya construido (retrieval/search.Version), así que no hace falta reconstruir los índices.
El tema original queda en `tema_corpus`, para poder volver atrás.

Se activa con TEMAS_PROPUESTA=1 en el .env (por defecto activo: ver docs/clasificador.md).
Solo afecta a los artículos de la norma base (ids "art-N"); las normas nuevas no cambian.
"""
import json
import os
import re
from functools import lru_cache
from pathlib import Path
from typing import Iterable, Optional

RUTA = Path(__file__).resolve().parents[1] / "retrieval" / "temas_por_articulo.json"


def activa() -> bool:
    return os.getenv("TEMAS_PROPUESTA", "1").strip().lower() in ("1", "true", "si", "sí", "yes")


@lru_cache(maxsize=1)
def _mapeo() -> dict:
    if not RUTA.exists():
        return {}
    return json.loads(RUTA.read_text(encoding="utf-8")).get("por_articulo", {})


def _id_articulo(id_: str) -> str:
    """'art-35-f2' -> 'art-35' (solo la norma base: sin prefijo de otra norma)."""
    return re.sub(r"-f\d+$", "", id_)


def tema_propuesto(id_: str) -> Optional[str]:
    return _mapeo().get(_id_articulo(id_))


def aplicar(registros: Iterable[dict]) -> None:
    """Pone en `tema` el tema propuesto (si está activo) o el del corpus (si no). Idempotente."""
    usar = activa()
    for r in registros:
        original = r.get("tema_corpus", r.get("tema"))
        nuevo = tema_propuesto(r.get("id", "")) if usar else None
        if nuevo:
            r["tema_corpus"] = original
            r["tema"] = nuevo
        elif "tema_corpus" in r:
            r["tema"] = r.pop("tema_corpus")
