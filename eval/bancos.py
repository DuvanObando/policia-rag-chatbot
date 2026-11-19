"""Bancos de preguntas en un formato único para las evaluaciones.

Formato normalizado de cada pregunta:
    {"id", "pregunta", "articulos_esperados": ["art-140", ...], "fuera_de_dominio": bool,
     "respuesta_referencia": str|None, "tipo": str, "origen": str}

Fuentes:
  - eval/banco_preguntas.json (formato de eval/ejemplo_formato.json): el banco oficial. Si está vacío o
    no existe, se usa el de Wilder, corpus/preguntas_ley_1801.json, ADAPTADO:
      * "question" -> pregunta; "answer" -> respuesta_referencia;
      * los artículos esperados salen de "source" («... modifica el artículo 155 de la Ley 1801»);
      * expected_behavior "abstenerse_por_falta_de_fuente_en_el_corpus" -> fuera_de_dominio = true.
    Las preguntas cuyo artículo de la Ley 1801 no se puede identificar se marcan con articulos_esperados
    vacío: cuentan para fuera de dominio y cita, no para Precisión/Recall/MRR.
  - eval/preguntas_indirectas.json: las 10 preguntas indirectas del diagnóstico del 19/11.
"""
import json
import re
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[1]
BANCO_OFICIAL = RAIZ / "eval" / "banco_preguntas.json"
BANCO_WILDER = RAIZ / "corpus" / "preguntas_ley_1801.json"
INDIRECTAS = RAIZ / "eval" / "preguntas_indirectas.json"


def normalizar_articulo(a) -> str:
    """'Artículo 140' | 'Art. 140' | '140' | 140 | 'art-140' -> 'art-140'."""
    m = re.search(r"(\d+[A-Za-z]?)", str(a))
    return f"art-{m.group(1).upper() if m.group(1)[-1].isalpha() else m.group(1)}" if m else str(a)


def _oficial() -> list:
    if not BANCO_OFICIAL.exists():
        return []
    datos = json.loads(BANCO_OFICIAL.read_text(encoding="utf-8") or "[]")
    salida = []
    for i, p in enumerate(datos, 1):
        salida.append({
            "id": p.get("id") or f"b{i:02d}",
            "pregunta": p["pregunta"],
            "articulos_esperados": [normalizar_articulo(a) for a in p.get("articulos_esperados") or []],
            "fuera_de_dominio": bool(p.get("fuera_de_dominio")),
            "respuesta_referencia": p.get("respuesta_referencia"),
            "tipo": p.get("tipo") or ("fuera_de_dominio" if p.get("fuera_de_dominio") else "general"),
            "origen": "eval/banco_preguntas.json",
        })
    return salida


_ART_1801 = re.compile(r"art[íi]culos?\s+(\d+[A-Z]?)\b(?:(?!;).)*?Ley\s+1801", re.IGNORECASE)


def _wilder() -> list:
    datos = json.loads(BANCO_WILDER.read_text(encoding="utf-8"))
    salida = []
    for p in datos:
        fuera = p.get("expected_behavior", "").startswith("abstenerse")
        arts = []
        for n in _ART_1801.findall(p.get("source") or ""):
            a = normalizar_articulo(n)
            if a not in arts:
                arts.append(a)
        salida.append({
            "id": p["id"],
            "pregunta": p["question"],
            "articulos_esperados": arts,
            "fuera_de_dominio": fuera,
            "respuesta_referencia": p.get("answer"),
            "tipo": "fuera_de_dominio" if fuera else "norma_modificatoria",
            "origen": "corpus/preguntas_ley_1801.json (adaptado)",
        })
    return salida


def banco() -> tuple:
    """(preguntas, nombre del banco usado)."""
    oficial = _oficial()
    if oficial:
        return oficial, "eval/banco_preguntas.json"
    return _wilder(), "corpus/preguntas_ley_1801.json (banco de Wilder, adaptado: eval/banco_preguntas.json está vacío)"


def indirectas() -> list:
    datos = json.loads(INDIRECTAS.read_text(encoding="utf-8"))
    for p in datos:
        p["articulos_esperados"] = [normalizar_articulo(a) for a in p["articulos_esperados"]]
        p.setdefault("origen", "eval/preguntas_indirectas.json")
    return datos


def recuperacion_existente() -> list:
    """Preguntas de las evaluaciones anteriores (un artículo esperado cada una)."""
    salida = []
    for nombre in ("preguntas_segmentacion.json", "preguntas_clasificador.json", "preguntas_coloquiales.json",
                   "preguntas_hibrida.json"):
        for p in json.loads((RAIZ / "eval" / nombre).read_text(encoding="utf-8")):
            salida.append({"id": f"{nombre.split('_')[1].split('.')[0]}-{p['id']}", "pregunta": p["pregunta"],
                           "articulos_esperados": [p["articulo_esperado"]], "fuera_de_dominio": False,
                           "tipo": p.get("tipo", "original"), "origen": f"eval/{nombre}"})
    return salida
