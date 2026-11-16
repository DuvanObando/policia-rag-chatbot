"""Utilidades para un corpus con varias normas (Ley 1801, Ley 769, ...).

Convenciones:
  - Cada registro del corpus lleva el campo "norma" con el nombre completo: "Ley 769 de 2002".
  - La Ley 1801 de 2016 es la norma base: sus ids siguen siendo "art-140" (sin prefijo) y es la
    norma por defecto de cualquier registro que no traiga el campo.
  - Las demás normas usan un prefijo en el id: "ley769-art-131", "decreto555-art-2".
  - Para comparar normas se usa la "clave" (tipo, número): ("ley", "769"). Así "Ley 769",
    "ley 769 de 2002" y "LEY 769 DE 2002" son la misma norma.
"""
import re
import unicodedata
from typing import List, Optional, Tuple

NORMA_BASE = "Ley 1801 de 2016"

# Nombre común de las normas conocidas (solo para presentarlas; no es obligatorio).
TITULOS = {
    ("ley", "1801"): "Código Nacional de Seguridad y Convivencia Ciudadana",
    ("ley", "769"): "Código Nacional de Tránsito Terrestre",
}

# Cómo nombra la gente a cada norma sin decir su número («artículo 131 del Código de Tránsito»).
# Se comparan sin tildes y en minúsculas. Una norma sin alias solo se reconoce por «Ley 769».
ALIAS = {
    ("ley", "1801"): ["codigo nacional de policia", "codigo de policia", "codigo nacional de seguridad y convivencia",
                      "codigo de seguridad y convivencia", "codigo de convivencia"],
    ("ley", "769"): ["codigo nacional de transito", "codigo de transito", "codigo de transito terrestre"],
}

_TIPOS = r"ley|decreto(?:\s+ley)?|decreto-ley|resoluci[oó]n|acuerdo|acto\s+legislativo"
_NORMA = re.compile(rf"^\s*({_TIPOS})\s+(?:n[oº°]\.?\s*)?(\d{{1,5}})(?:\s+de\s+(\d{{4}}))?\s*$", re.IGNORECASE)
_EN_TEXTO = re.compile(rf"\b({_TIPOS})\s+(\d{{1,5}})(?:\s+de\s+(\d{{4}}))?", re.IGNORECASE)


def _sin_tildes(t: str) -> str:
    return "".join(c for c in unicodedata.normalize("NFKD", t) if not unicodedata.combining(c))


def _tipo(t: str) -> str:
    """'Decreto Ley' -> 'decreto', 'Resolución' -> 'resolucion' (para comparar)."""
    t = re.sub(r"[\s-]+", " ", _sin_tildes(t).lower()).strip()
    return "decreto" if t.startswith("decreto") else t


def normalizar(texto: str) -> str:
    """'ley 769 de 2002' -> 'Ley 769 de 2002'. Lanza ValueError si no parece una norma con año."""
    m = _NORMA.match(texto or "")
    if not m or not m.group(3):
        raise ValueError(
            "La norma debe escribirse como «Ley 769 de 2002» (tipo, número y año)."
        )
    tipo = re.sub(r"\s+", " ", m.group(1).strip())
    tipo = tipo[0].upper() + tipo[1:].lower()
    return f"{tipo} {int(m.group(2))} de {m.group(3)}"


def clave(texto: Optional[str]) -> Tuple[str, str]:
    """('ley', '769') a partir de 'Ley 769 de 2002', 'Ley 769' o 'ley 769'. None -> norma base."""
    m = _EN_TEXTO.search(texto or NORMA_BASE)
    if not m:
        return clave(NORMA_BASE)
    return _tipo(m.group(1)), str(int(m.group(2)))


def es_base(norma: Optional[str]) -> bool:
    return clave(norma) == clave(NORMA_BASE)


def corta(norma: Optional[str]) -> str:
    """'Ley 769 de 2002' -> 'Ley 769' (la forma que se usa en las citas)."""
    tipo, numero = clave(norma)
    nombre = {"ley": "Ley", "decreto": "Decreto", "resolucion": "Resolución", "acuerdo": "Acuerdo"}.get(tipo, tipo.capitalize())
    return f"{nombre} {numero}"


def prefijo_id(norma: Optional[str]) -> str:
    """Prefijo de los ids de una norma: '' para la base (art-140), 'ley769-' para las demás."""
    if es_base(norma):
        return ""
    tipo, numero = clave(norma)
    return f"{tipo.replace(' ', '')}{numero}-"


def id_articulo(norma: Optional[str], numero: str) -> str:
    """('Ley 769 de 2002', '131') -> 'ley769-art-131'; ('Ley 1801 de 2016', '140') -> 'art-140'."""
    return f"{prefijo_id(norma)}art-{numero}"


def numero_de_id(id_art: str) -> str:
    """'ley769-art-131-f2' -> '131'; 'art-185A' -> '185A'. Si no es un artículo, devuelve el id."""
    m = re.search(r"art-([0-9]+[A-Za-z]?)(?:-f\d+)?$", id_art)
    return m.group(1) if m else id_art


def nombre_archivo(norma: str) -> str:
    """'Ley 769 de 2002' -> 'ley_769_de_2002.json' (archivo del corpus de esa norma)."""
    return re.sub(r"[^a-z0-9]+", "_", _sin_tildes(norma).lower()).strip("_") + ".json"


def titulo(norma: str) -> Optional[str]:
    return TITULOS.get(clave(norma))


def describir(norma: str) -> str:
    """'Ley 1801 de 2016 (Código Nacional de Seguridad y Convivencia Ciudadana)'."""
    t = titulo(norma)
    return f"{norma} ({t})" if t else norma


def mencionadas(texto: str) -> List[Tuple[str, str]]:
    """Claves de las normas que se mencionan en un texto, por número («Ley 769») o por su nombre
    común («Código de Tránsito»): [('ley', '769')]."""
    vistas = []
    for m in _EN_TEXTO.finditer(texto or ""):
        k = (_tipo(m.group(1)), str(int(m.group(2))))
        if k not in vistas:
            vistas.append(k)
    plano = re.sub(r"\s+", " ", _sin_tildes(texto or "").lower())
    for k, nombres in ALIAS.items():
        if k not in vistas and any(re.search(rf"\b{re.escape(n)}\b", plano) for n in nombres):
            vistas.append(k)
    return vistas


def ordenar(normas: List[str]) -> List[str]:
    """La norma base primero; las demás en orden alfabético."""
    return sorted(set(normas), key=lambda n: (not es_base(n), n))


def norma_principal() -> str:
    """Norma que tiene prioridad cuando la pregunta pide «artículo N» sin decir la norma.

    NORMA_PRINCIPAL del .env (p. ej. «Ley 1801 de 2016»); si falta o está mal escrita, la norma base.
    """
    import os

    valor = (os.getenv("NORMA_PRINCIPAL") or "").strip()
    if not valor:
        return NORMA_BASE
    try:
        return normalizar(valor)
    except ValueError:
        return NORMA_BASE


def por_prioridad(cargadas: List[str]) -> List[str]:
    """Normas cargadas en orden de prioridad: la principal primero, luego la base y las demás."""
    principal = clave(norma_principal())
    return sorted(ordenar(cargadas), key=lambda n: clave(n) != principal)
