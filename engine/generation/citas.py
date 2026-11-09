"""Extracción y verificación de citas en la respuesta del modelo.

Reconoce:
    "(Art. 163, num. 2)", "(Art. 163, par. 1)", "(Art. 183, par.)",
    "(Art. 180, par. transitorio)", "(Art. 180)",
    "(Art. 140, num. 13; Art. 140, num. 14)", "(Art. 163, num. 1 y 2)",
y también menciones en texto libre: "Artículo 140, numeral 7 y parágrafo 2",
"artículos 180 y 183".

Cada cita es un dict: {"articulo": "163", "numeral": "2" | None, "paragrafo": "1" | "único" | "transitorio" | None}
"""
import re
from typing import List, Optional

# Mención de artículo, con lista opcional ("artículos 180 y 183")
_ART = re.compile(r"\b(?:art[íi]culos?|arts?)\.?\s*(\d+[A-Z]?)((?:\s*(?:,|\by\b|\be\b)\s*\d+[A-Z]?)*)", re.IGNORECASE)
_NUM = re.compile(r"\bnum(?:eral(?:es)?)?\.?\s*(\d+(?:\s*(?:,|y|e)\s*\d+)*)", re.IGNORECASE)
_PAR = re.compile(r"\bpar(?:[áa]grafos?)?(?:\.|\b)\s*(\d+|transitorio|[úu]nico)?", re.IGNORECASE)
_FIN_VENTANA = re.compile(r"[;)\n]")


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

    def agregar(articulo, numeral=None, paragrafo=None):
        c = {"articulo": articulo, "numeral": numeral, "paragrafo": paragrafo}
        if c not in citas:
            citas.append(c)

    for i, m in enumerate(menciones):
        siguiente = menciones[i + 1].start() if i + 1 < len(menciones) else None
        articulo = m.group(1)
        otros = re.findall(r"\d+[A-Z]?", m.group(2) or "")
        if otros:  # "artículos 180 y 183": solo nivel artículo
            for a in [articulo] + otros:
                agregar(a)
            continue
        ventana = _ventana(texto, m.end(), siguiente)
        detalles = False
        for g in _NUM.findall(ventana):
            for n in re.findall(r"\d+", g):
                agregar(articulo, numeral=n)
                detalles = True
        for p in _PAR.findall(ventana):
            p = p.lower()
            agregar(articulo, paragrafo={"": "único", "unico": "único"}.get(p, p))
            detalles = True
        if not detalles:
            agregar(articulo)
            if not _en_parentesis(texto, m.start()):
                sueltas.append(articulo)

    def sobra(c):
        if c["numeral"] or c["paragrafo"] or c["articulo"] not in sueltas:
            return False
        return any(o["articulo"] == c["articulo"] and o is not c for o in citas)

    return [c for c in citas if not sobra(c)]


def existe_en_articulo(cita: dict, texto_articulo: str) -> bool:
    """¿El numeral o parágrafo citado aparece en el texto del artículo?"""
    if cita["numeral"]:
        n = re.escape(cita["numeral"])
        return bool(re.search(rf"(?m)^\s*{n}\.\s", texto_articulo) or re.search(rf"\bNumeral {n}\b", texto_articulo))
    p = cita["paragrafo"]
    if p == "transitorio":
        return bool(re.search(r"PAR[ÁA]GRAFO TRANSITORIO", texto_articulo, re.IGNORECASE))
    if p == "único":
        return bool(re.search(r"PAR[ÁA]GRAFO( [ÚU]NICO)?\.", texto_articulo, re.IGNORECASE))
    if p:
        return bool(re.search(rf"PAR[ÁA]GRAFO {re.escape(p)}o?\.", texto_articulo, re.IGNORECASE))
    return True  # cita a nivel de artículo


def texto_cita(cita: dict) -> str:
    """Forma legible: 'Art. 163, num. 2', 'Art. 183, par.', 'Art. 180'."""
    s = f"Art. {cita['articulo']}"
    if cita["numeral"]:
        s += f", num. {cita['numeral']}"
    elif cita["paragrafo"] == "único":
        s += ", par."
    elif cita["paragrafo"]:
        s += f", par. {cita['paragrafo']}"
    return s
