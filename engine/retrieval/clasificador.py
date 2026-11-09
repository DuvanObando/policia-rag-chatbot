"""Clasificador temático de preguntas, por palabras clave (Fase 4).

Orienta la búsqueda hacia el tema (y el libro o título) al que parece pertenecer la
pregunta. Los temas y sus palabras clave viven en engine/retrieval/temas.json: para
ampliarlo no hace falta tocar este archivo.

    from retrieval.clasificador import clasificar
    clasificar("¿Me pueden multar por tomar trago en el parque?")
    # {"tema": "Consumo de sustancias en espacio público", "confianza": 0.5, "libro": "Libro II", ...}

Cómo decide:
  1. Normaliza la pregunta (minúsculas, sin tildes ni signos).
  2. Busca las palabras clave de cada tema. Una palabra suma 1; una frase suma una unidad
     por palabra. Cada palabra clave cuenta una sola vez.
  3. El tema con más puntaje gana. confianza = puntaje del ganador / puntaje de todos los
     temas que coincidieron (1.0 si solo coincidió uno; 0.5 si dos empatan).
  4. Si ninguna palabra clave coincide, el tema es "general" y no hay empuje.

También detecta artículos pedidos por número ("artículo 163", "art. 163").
"""
import json
import re
import unicodedata
from functools import lru_cache
from pathlib import Path
from typing import Dict, List

RUTA_TEMAS = Path(__file__).resolve().parent / "temas.json"
GENERAL = "general"

_ARTICULO = re.compile(r"\b(?:articulos?|arts?)\.?\s*(\d+(?:\s*(?:,|y|e)\s*\d+)*)")


def normalizar(texto: str) -> str:
    """Minúsculas, sin tildes y solo letras, números y espacios."""
    t = unicodedata.normalize("NFD", texto.lower())
    t = "".join(c for c in t if unicodedata.category(c) != "Mn")
    t = re.sub(r"[^a-z0-9*\s]", " ", t)
    return re.sub(r"\s+", " ", t).strip()


def _patron(palabra: str):
    """('mult*') -> prefijo; ('sin pagar') -> frase exacta. Devuelve (regex, peso)."""
    p = normalizar(palabra)
    peso = len(p.replace("*", "").split())
    if p.endswith("*"):
        return re.compile(rf"\b{re.escape(p[:-1])}\w*"), peso
    return re.compile(rf"\b{re.escape(p)}\b"), peso


@lru_cache(maxsize=1)
def cargar() -> dict:
    """Carga temas.json (una vez por proceso; reinicia el motor para ver cambios)."""
    datos = json.loads(RUTA_TEMAS.read_text(encoding="utf-8"))
    for t in datos["temas"]:
        t["_patrones"] = [(k, *_patron(k)) for k in t["palabras_clave"]]
    return datos


def recargar() -> dict:
    cargar.cache_clear()
    return cargar()


def clasificar(pregunta: str) -> dict:
    """Tema más probable de la pregunta.

    Devuelve:
        tema        nombre del tema, o "general" si no se detectó ninguno
        confianza   0.0 a 1.0 (ver arriba)
        libro, titulo   del tema ganador (None si es "general")
        temas       todos los temas que coincidieron, de mayor a menor puntaje:
                    [{"tema", "puntaje", "confianza", "coincidencias"}]
    """
    texto = normalizar(pregunta)
    encontrados = []
    for t in cargar()["temas"]:
        puntaje, coincidencias = 0, []
        for palabra, regex, peso in t["_patrones"]:
            if regex.search(texto):
                puntaje += peso
                coincidencias.append(palabra)
        if puntaje:
            encontrados.append({"tema": t["tema"], "puntaje": puntaje, "coincidencias": coincidencias,
                                "libro": t.get("libro"), "titulo": t.get("titulo")})
    if not encontrados:
        return {"tema": GENERAL, "confianza": 0.0, "libro": None, "titulo": None, "temas": []}

    encontrados.sort(key=lambda e: -e["puntaje"])
    total = sum(e["puntaje"] for e in encontrados)
    for e in encontrados:
        e["confianza"] = round(e["puntaje"] / total, 3)
    ganador = encontrados[0]
    return {"tema": ganador["tema"], "confianza": ganador["confianza"],
            "libro": ganador["libro"], "titulo": ganador["titulo"], "temas": encontrados}


def empujes(clasificacion: dict, modo: str = "semantico") -> Dict[str, float]:
    """Cuánto sumar al score de los candidatos de cada tema: {nombre del tema: empuje}.

    Un tema recibe empuje = empuje_máximo × su confianza, si su puntaje es al menos
    `umbral_relativo` del mejor. Con un solo tema claro recibe el empuje completo; con dos
    temas parejos, cada uno recibe la mitad. Nunca es un filtro: solo suma al score.

    El empuje máximo depende del modo de búsqueda (`empuje_por_modo` en temas.json), porque
    el score tiene otra escala en cada modo (coseno, BM25 normalizado, RRF): el valor de cada
    modo equivale al mismo "empujón relativo" que el modo semántico.
    """
    cfg = cargar()["configuracion"]
    maximo = cfg["empuje_por_modo"].get(modo, 0)
    temas = clasificacion["temas"]
    if not temas or not maximo:
        return {}
    mejor = temas[0]["puntaje"]
    return {e["tema"]: maximo * e["confianza"]
            for e in temas if e["puntaje"] >= cfg["umbral_relativo"] * mejor}


def articulos_mencionados(pregunta: str) -> List[str]:
    """Números de artículo pedidos en la pregunta, en orden y sin repetir: ['163']."""
    numeros = []
    for grupo in _ARTICULO.findall(normalizar(pregunta)):
        for n in re.findall(r"\d+", grupo):
            if n not in numeros:
                numeros.append(n)
    return numeros
