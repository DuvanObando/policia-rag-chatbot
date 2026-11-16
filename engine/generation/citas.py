"""Extracción y verificación de citas en la respuesta del modelo.

Reconoce:
    "(Art. 163, num. 2)", "(Art. 163, par. 1)", "(Art. 183, par.)",
    "(Art. 180, par. transitorio)", "(Art. 180)",
    "(Art. 140, num. 13; Art. 140, num. 14)", "(Art. 163, num. 1 y 2)",
y también menciones en texto libre: "Artículo 140, numeral 7 y parágrafo 2",
"artículos 180 y 183".

Varias normas: "(Ley 769, Art. 131, num. 2)", "(Ley 769 de 2002, Art. 131)" y, en texto libre,
"artículo 131 de la Ley 769". Sin norma, la cita es de la norma que corresponda según el contexto
(lo decide responder.py; por defecto, la Ley 1801 de 2016).

Cada cita es un dict: {"articulo": "163", "numeral": "2" | None, "paragrafo": "1" | "único" | "transitorio" | None,
                       "norma": ("ley", "769") | None}
"""
import re
from typing import List, Optional

# Mención de artículo, con lista opcional ("artículos 180 y 183")
_ART = re.compile(r"\b(?:art[íi]culos?|arts?)\.?\s*(\d+[A-Z]?)((?:\s*(?:,|\by\b|\be\b)\s*\d+[A-Z]?)*)", re.IGNORECASE)
_NUM = re.compile(r"\bnum(?:eral(?:es)?)?\.?\s*(\d+(?:\s*(?:,|y|e)\s*\d+)*)", re.IGNORECASE)
_PAR = re.compile(r"\bpar(?:[áa]grafos?)?(?:\.|\b)\s*(\d+|transitorio|[úu]nico)?", re.IGNORECASE)
_FIN_VENTANA = re.compile(r"[;)\n]")
_TIPOS = r"ley|decreto(?:\s+ley)?|resoluci[oó]n|acuerdo"
# Norma justo ANTES de la mención: "(Ley 769, Art. 131" / "Ley 769 de 2002, artículo 131"
_NORMA_ANTES = re.compile(rf"\b({_TIPOS})\s+(\d{{1,5}})(?:\s+de\s+\d{{4}})?\s*,?\s*$", re.IGNORECASE)
# Norma DESPUÉS: "artículo 131 de la Ley 769" / "art. 2 del Decreto 555"
_NORMA_DESPUES = re.compile(rf"\bde(?:l|\s+la|\s+el)?\s+({_TIPOS})\s+(\d{{1,5}})", re.IGNORECASE)


def _clave_norma(tipo: str, numero: str):
    t = tipo.lower().replace("ó", "o")
    return ("decreto" if t.startswith("decreto") else t.split()[0], str(int(numero)))


def _norma_de(texto: str, inicio: int, ventana: str):
    """Norma de una mención de artículo: la que la precede o la que la sigue; None si no hay."""
    m = _NORMA_ANTES.search(texto[max(0, inicio - 45):inicio])
    if m:
        return _clave_norma(m.group(1), m.group(2))
    m = _NORMA_DESPUES.search(ventana)
    if m:
        return _clave_norma(m.group(1), m.group(2))
    return None


def _ventana(texto: str, inicio: int, siguiente: Optional[int]) -> str:
    """Texto que sigue a la mención del artículo, hasta ';', ')', salto de línea o la próxima mención."""
    fin = min(len(texto), inicio + 60, siguiente if siguiente is not None else len(texto))
    trozo = texto[inicio:fin]
    m = _FIN_VENTANA.search(trozo)
    return trozo[: m.start()] if m else trozo


def _en_parentesis(texto: str, pos: int) -> bool:
    """¿La posición está dentro de un paréntesis abierto? (p. ej. "(Art. 180)")"""
    abre, cierra = texto.rfind("(", 0, pos), texto.rfind(")", 0, pos)
    return abre > cierra


def extraer_citas(texto: str) -> List[dict]:
    """Citas en orden de aparición, sin repetir.

    Una mención suelta en el texto ("el artículo 140 figura como modificado") no se
    cuenta como cita si ese artículo ya tiene otras citas en la respuesta; sí se cuenta
    si es la única referencia a ese artículo. Las citas entre paréntesis siempre cuentan.
    """
    menciones = list(_ART.finditer(texto))
    citas = []
    sueltas = []  # citas genéricas que salieron de una mención fuera de paréntesis

    def agregar(articulo, numeral=None, paragrafo=None, norma=None):
        c = {"articulo": articulo, "numeral": numeral, "paragrafo": paragrafo, "norma": norma}
        if c not in citas:
            citas.append(c)

    for i, m in enumerate(menciones):
        siguiente = menciones[i + 1].start() if i + 1 < len(menciones) else None
        articulo = m.group(1)
        otros = re.findall(r"\d+[A-Z]?", m.group(2) or "")
        if otros:  # "artículos 180 y 183": solo nivel artículo
            norma = _norma_de(texto, m.start(), _ventana(texto, m.end(), siguiente))
            for a in [articulo] + otros:
                agregar(a, norma=norma)
            continue
        ventana = _ventana(texto, m.end(), siguiente)
        norma = _norma_de(texto, m.start(), ventana)
        detalles = False
        for g in _NUM.findall(ventana):
            for n in re.findall(r"\d+", g):
                agregar(articulo, numeral=n, norma=norma)
                detalles = True
        for p in _PAR.findall(ventana):
            p = p.lower()
            agregar(articulo, paragrafo={"": "único", "unico": "único"}.get(p, p), norma=norma)
            detalles = True
        if not detalles:
            agregar(articulo, norma=norma)
            if not _en_parentesis(texto, m.start()):
                sueltas.append((articulo, norma))

    def sobra(c):
        if c["numeral"] or c["paragrafo"] or (c["articulo"], c["norma"]) not in sueltas:
            return False
        return any(o["articulo"] == c["articulo"] and o["norma"] == c["norma"] and o is not c for o in citas)

    return [c for c in citas if not sobra(c)]


def existe_en_articulo(cita: dict, texto_articulo: str) -> bool:
    """¿El numeral o parágrafo citado aparece en el texto del artículo?"""
    if cita["numeral"]:
        n = re.escape(cita["numeral"])
        # "1. ..." (Ley 1801) o "B.1. ..." (literal y numeral, como en el art. 131 de la Ley 769)
        return bool(re.search(rf"(?m)^\s*(?:[A-Z]\.)?{n}\.\s", texto_articulo) or re.search(rf"\bNumeral {n}\b", texto_articulo))
    p = cita["paragrafo"]
    if p == "transitorio":
        return bool(re.search(r"PAR[ÁA]GRAFO TRANSITORIO", texto_articulo, re.IGNORECASE))
    if p == "único":
        return bool(re.search(r"PAR[ÁA]GRAFO( [ÚU]NICO)?\.", texto_articulo, re.IGNORECASE))
    if p:
        return bool(re.search(rf"PAR[ÁA]GRAFO {re.escape(p)}o?\.", texto_articulo, re.IGNORECASE))
    return True  # cita a nivel de artículo


def texto_cita(cita: dict, norma_corta: str = None) -> str:
    """Forma legible: 'Art. 163, num. 2', 'Art. 183, par.', 'Art. 180'.

    Con norma_corta (otra norma distinta de la Ley 1801): 'Ley 769, Art. 131, num. 2'.
    """
    s = f"{norma_corta}, Art. {cita['articulo']}" if norma_corta else f"Art. {cita['articulo']}"
    if cita["numeral"]:
        s += f", num. {cita['numeral']}"
    elif cita["paragrafo"] == "único":
        s += ", par."
    elif cita["paragrafo"]:
        s += f", par. {cita['paragrafo']}"
    return s
