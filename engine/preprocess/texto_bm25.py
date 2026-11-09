"""Preparación de texto para la búsqueda léxica (BM25).

    from preprocess.texto_bm25 import tokens_bm25
    tokens_bm25("¿Cuántos smdlv cuesta una multa tipo 4?")   # ['smdlv', 'cuest', 'mult', 'tip', '4']

Pasos: minúsculas -> tokenización -> sin stopwords en español -> lematización (o stemming)
-> sin tildes. Los números se conservan (plazos, porcentajes, "tipo 4").

PUNTO DE CONEXIÓN CON LA FASE 2 (Santiago Castro): esta función es la única que prepara texto
para BM25. Cuando el preprocesamiento de la Fase 2 (normalización, tokenización y
lematización con spaCy) esté listo, basta con reemplazar el cuerpo de `_tokens_spacy` /
`tokens_bm25` por su pipeline: el índice BM25 (build_index.py) y la búsqueda (search.py)
llaman siempre a esta función, y guardan en el índice con qué método se prepararon los textos.

Dos métodos (se elige el mejor disponible; se puede forzar con `metodo=`):
  - "spacy":    lematiza con spaCy (modelo es_core_news_sm). Instalación del modelo:
                    python -m spacy download es_core_news_sm
  - "snowball": stemmer Snowball en español (Python puro). Es el RESPALDO para equipos donde
                spaCy no carga (p. ej. Windows con "Control de aplicaciones" bloqueando una
                extensión nativa de spaCy). Es stemming (recorta la palabra a su raíz:
                "multas", "multar" -> "mult"), no lematización: aproxima, pero es más burdo.

Las stopwords son las mismas con los dos métodos; solo cambia cómo se reduce cada palabra.
"""
import re
import unicodedata
from functools import lru_cache
from typing import List, Optional

MODELO_SPACY = "es_core_news_sm"

# Stopwords del español, sin tildes. Se omiten a propósito palabras con significado jurídico:
# "sin" y "contra" se conservan.
_STOPWORDS = """
a al algo algun alguna algunas alguno algunos ante antes aqui asi aun aunque cada como con cual cuales
cuando cuanto cuantos cuya cuyas cuyo cuyos de del desde donde dos e el ella ellas ello ellos en entre
era eran eras eres es esa esas ese eso esos esta estaba estaban estado estamos estan estar estas este
esto estos estoy fue fueron fui ha haber habia han has hasta hay la las le les lo los mas me mi mis mucho
muy nada ni no nos nosotros nuestra nuestro o os otra otras otro otros para pero poco por porque que
quien quienes se sea sean ser si sido sobre son su sus tal tambien tanto te tener tiene tienen toda todas
todo todos tu tus un una unas uno unos usted ustedes va vamos van y ya yo
""".split()
STOPWORDS_ES = frozenset(_STOPWORDS)


def sin_tildes(texto: str) -> str:
    n = unicodedata.normalize("NFD", texto)
    return "".join(c for c in n if unicodedata.category(c) != "Mn")


@lru_cache(maxsize=1)
def _spacy():
    """Modelo spaCy, o None si no se puede usar (no instalado, modelo ausente o bloqueado por el SO)."""
    try:
        import spacy

        return spacy.load(MODELO_SPACY, disable=["parser", "ner"])
    except Exception:  # ImportError incluye "DLL load failed ... Control de aplicaciones"
        return None


@lru_cache(maxsize=1)
def _stemmer():
    import snowballstemmer

    return snowballstemmer.stemmer("spanish")


def metodo_disponible() -> str:
    """Mejor método que se puede usar ahora: "spacy" o "snowball"."""
    return "spacy" if _spacy() is not None else "snowball"


def _resolver(metodo: Optional[str]) -> str:
    if metodo is None:
        return metodo_disponible()
    if metodo not in ("spacy", "snowball"):
        raise ValueError(f"Método desconocido: {metodo!r}. Usa 'spacy' o 'snowball'.")
    if metodo == "spacy" and _spacy() is None:
        raise RuntimeError(
            "El índice BM25 se preparó con spaCy, pero spaCy o el modelo no se pueden cargar aquí. "
            f"Instala el modelo ('python -m spacy download {MODELO_SPACY}') o reconstruye el índice "
            "(python engine/indexing/build_index.py)."
        )
    return metodo


def _tokens_snowball(texto: str) -> List[str]:
    tokens = []
    for palabra in re.findall(r"\w+", texto.lower()):
        if sin_tildes(palabra) in STOPWORDS_ES:
            continue
        tokens.append(sin_tildes(_stemmer().stemWord(palabra)))
    return tokens


def _tokens_spacy(doc) -> List[str]:
    tokens = []
    # NOTA: esta rama necesita spaCy; en el equipo donde se escribió spaCy está bloqueado por
    # Windows, así que NO se pudo ejecutar. Probarla donde spaCy cargue.
    for t in doc:
        if t.is_space or t.is_punct:
            continue
        lema = sin_tildes((t.lemma_ or t.text).lower())
        if not re.search(r"\w", lema) or lema in STOPWORDS_ES or sin_tildes(t.lower_) in STOPWORDS_ES:
            continue
        tokens.append(lema)
    return tokens


def tokens_bm25(texto: str, metodo: Optional[str] = None) -> List[str]:
    """Tokens listos para BM25: minúsculas, sin tildes, sin stopwords, lematizados."""
    return tokens_bm25_lote([texto], metodo)[0]


def tokens_bm25_lote(textos: List[str], metodo: Optional[str] = None) -> List[List[str]]:
    """Igual que tokens_bm25, para varios textos a la vez (más rápido con spaCy)."""
    metodo = _resolver(metodo)
    if metodo == "spacy":
        return [_tokens_spacy(doc) for doc in _spacy().pipe(textos)]
    return [_tokens_snowball(t) for t in textos]


def descripcion_metodo(metodo: str) -> str:
    """Texto para guardar en el índice: 'spacy:es_core_news_sm-3.8.0' o 'snowball:spanish'."""
    if metodo == "spacy":
        return f"spacy:{MODELO_SPACY}-{_spacy().meta['version']}"
    return "snowball:spanish"
