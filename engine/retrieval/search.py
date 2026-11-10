"""Búsqueda de fragmentos relevantes sobre el índice FAISS.

Uso como librería (desde engine/ o con engine/ en sys.path):
    from retrieval.search import buscar
    fragmentos = buscar("¿Qué pasa si no pago una multa?", k=3)

Uso por línea de comandos (desde la raíz del repo):
    python engine/retrieval/search.py "¿Qué pasa si no pago una multa?" [-k 3]
    python engine/retrieval/search.py --demo

El modelo y el índice se cargan UNA sola vez por proceso (en la primera llamada,
o antes con precargar()) y se reutilizan en las llamadas siguientes.
"""
import argparse
import json
import os
import re
import sys
import time
from functools import lru_cache
from pathlib import Path
from typing import List, Optional

import faiss
import numpy as np
from dotenv import load_dotenv
from rank_bm25 import BM25Okapi

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))  # carpeta engine/
from indexing.embeddings import PREGUNTAS_DEMO, cargar_modelo, embeddings_preguntas  # noqa: E402
from preprocess.texto_bm25 import descripcion_metodo, metodo_disponible  # noqa: E402
from retrieval.expansion import tokens_consulta_lexica  # noqa: E402
from retrieval.clasificador import articulos_mencionados, clasificar, empujes  # noqa: E402

load_dotenv(Path(__file__).resolve().parents[2] / ".env")

CARPETA_INDICES = Path(__file__).resolve().parents[1] / "indexing" / "indexes"
ORDINALES = {"PRIMERO": "I", "SEGUNDO": "II", "TERCERO": "III", "CUARTO": "IV", "QUINTO": "V"}

# Modos de búsqueda (el `score` de cada fragmento tiene otra escala según el modo):
#   "semantico"  similitud coseno de los embeddings (0 a 1)
#   "lexico"     BM25 normalizado por el mejor resultado (0 a 1); solo trae fragmentos que
#                comparten alguna palabra con la pregunta
#   "hibrido"    Reciprocal Rank Fusion de los dos rankings: suma de 1/(k + posición); ~0.01 a 0.03
MODOS = ("semantico", "lexico", "hibrido")
MODO_POR_DEFECTO = "hibrido"  # si no hay BUSQUEDA_MODO en el .env (recomendado: ver docs/busqueda_hibrida.md)


def modo_por_defecto() -> str:
    """Modo del .env (BUSQUEDA_MODO) o MODO_POR_DEFECTO. Lanza ValueError si el valor no existe."""
    modo = os.getenv("BUSQUEDA_MODO", "").strip().lower() or MODO_POR_DEFECTO
    if modo not in MODOS:
        raise ValueError(f"BUSQUEDA_MODO={modo!r} no existe. Opciones: {list(MODOS)}")
    return modo


def rrf_k() -> int:
    """Constante k de Reciprocal Rank Fusion (BUSQUEDA_RRF_K en el .env; 60 por defecto)."""
    return int(os.getenv("BUSQUEDA_RRF_K", "60"))


POOL_MAX = 2000  # máximo de candidatos que se traen del índice para reordenar (empuje por tema)


@lru_cache(maxsize=1)
def _modelo():
    return cargar_modelo()


@lru_cache(maxsize=None)
def _indice(estrategia: str):
    """Carga (una sola vez por estrategia) el índice FAISS y sus metadatos."""
    carpeta = CARPETA_INDICES / estrategia
    if not (carpeta / "index.faiss").exists():
        raise FileNotFoundError(
            f"No existe el índice '{estrategia}'. Constrúyelo con: "
            f"python engine/indexing/build_index.py --estrategia {estrategia}"
        )
    datos = (carpeta / "index.faiss").read_bytes()  # lectura con Python: evita fallos con tildes en la ruta
    indice = faiss.deserialize_index(np.frombuffer(datos, dtype="uint8"))
    meta = json.loads((carpeta / "metadatos.json").read_text(encoding="utf-8"))
    return indice, meta


def precargar(estrategia: str = "articulo") -> None:
    """Carga modelo e índice por adelantado (p. ej. al arrancar la API)."""
    _modelo()
    _indice(estrategia)


def info_indice(estrategia: str = "articulo") -> dict:
    """Datos del índice cargado: estrategia, modelo de embeddings y número de fragmentos."""
    indice, meta = _indice(estrategia)
    return {"estrategia": estrategia, "modelo": meta["modelo"], "fragmentos": int(indice.ntotal)}


@lru_cache(maxsize=None)
def _articulos_del_corpus(estrategia: str) -> dict:
    """Artículos completos del corpus con que se construyó el índice, por id (se carga una vez)."""
    ruta = Path(_indice(estrategia)[1]["corpus"])
    return {a["id"]: a for a in json.loads(ruta.read_text(encoding="utf-8"))}


def articulo_completo(id_fragmento: str, estrategia: str = "fragmentos") -> dict:
    """Artículo completo al que pertenece un fragmento (para small-to-big).

    Devuelve id, ubicacion (cadena), epigrafe, texto, vigencia y tema del artículo.
    """
    a = _articulos_del_corpus(estrategia).get(id_articulo(id_fragmento))
    if a is None:
        # Documento complementario (subido por /upload_pdf/): no está en el corpus,
        # así que se usa el propio fragmento como contexto.
        _, meta = _indice(estrategia)
        a = next(f for f in meta["fragmentos"] if f["id"] == id_fragmento)
        a = {**a, "id": id_articulo(a["id"])}
    return {
        "id": a["id"],
        "ubicacion": formatear_ubicacion(a["ubicacion"]),
        "epigrafe": a["epigrafe"],
        "texto": a["texto"],
        "vigencia": a["vigencia"],
        "tema": a["tema"],
        "fuente": a.get("fuente"),
        "archivo_fuente": a.get("archivo_fuente"),
        "pagina_inicio": a.get("pagina_inicio"),
        "pagina_fin": a.get("pagina_fin"),
        "paginas": a.get("paginas"),
        "ubicaciones_fuente": a.get("ubicaciones_fuente"),
        "fuentes": a.get("fuentes"),
    }


def _parte(texto: Optional[str]) -> Optional[str]:
    """'Libro Segundo. De la libertad...' -> 'Libro Segundo' (lo que va antes del primer punto)."""
    return texto.split(".")[0].strip() if texto else None


def id_articulo(id_fragmento: str) -> str:
    """'art-140-f2' -> 'art-140' (un id de artículo se queda igual)."""
    return re.sub(r"-f\d+$", "", id_fragmento)


def formatear_ubicacion(ub: dict) -> str:
    """Ubicación legible, p. ej. 'Libro II, Título XIV, Capítulo II, Artículo 140'."""
    partes = []
    for clave in ("libro", "titulo", "capitulo", "articulo"):
        p = _parte(ub.get(clave))
        if not p:
            continue
        if clave == "libro":
            palabras = p.split()
            if len(palabras) > 1 and palabras[1].upper() in ORDINALES:
                p = f"Libro {ORDINALES[palabras[1].upper()]}"
        partes.append(p)
    return ", ".join(partes)


@lru_cache(maxsize=None)
def _bm25(estrategia: str):
    """(BM25Okapi, método de preparación del texto) del índice, cargado una sola vez."""
    ruta = CARPETA_INDICES / estrategia / "bm25_tokens.json"
    if not ruta.exists():
        raise FileNotFoundError(
            f"No existe el índice BM25 de '{estrategia}'. Reconstruye el índice: "
            f"python engine/indexing/build_index.py --estrategia {estrategia}"
        )
    datos = json.loads(ruta.read_text(encoding="utf-8"))
    return BM25Okapi(datos["tokens"], k1=datos["k1"], b=datos["b"]), datos["metodo"]


def verificar_bm25(estrategia: str) -> Optional[str]:
    """None si el índice BM25 es consistente con el entorno; si no, un mensaje de error.

    El índice guarda con qué método se prepararon sus textos ("spacy:es_core_news_sm-3.8.0" o
    "snowball:spanish"). Las preguntas deben prepararse igual; si el método disponible ahora es
    otro (p. ej. se instaló spaCy después), las palabras ya no coincidirían y BM25 fallaría
    en silencio.
    """
    ruta = CARPETA_INDICES / estrategia / "bm25_tokens.json"
    if not ruta.exists():
        return (f"No existe el índice BM25 de '{estrategia}'. Reconstruye el índice: "
                f"python engine/indexing/build_index.py --estrategia {estrategia}")
    guardado = json.loads(ruta.read_text(encoding="utf-8")).get("descripcion_metodo", "desconocido")
    actual = descripcion_metodo(metodo_disponible())
    if guardado != actual:
        return (f"El índice BM25 de '{estrategia}' se construyó con la preparación de texto '{guardado}', "
                f"pero ahora está disponible '{actual}'. Hay que reconstruir el índice: "
                f"python engine/indexing/build_index.py --estrategia {estrategia}")
    return None


def precargar_busqueda(estrategia: str, modo: Optional[str] = None) -> None:
    """Carga lo que necesita el modo (modelo, índice FAISS y, si hace falta, BM25)."""
    precargar(estrategia)
    if (modo or modo_por_defecto()) in ("lexico", "hibrido"):
        _bm25(estrategia)


def _puntajes_base(pregunta: str, estrategia: str, modo: str) -> list:
    """[(score, fragmento)] de mayor a menor, según el modo y SIN clasificador."""
    indice, meta = _indice(estrategia)
    frs = meta["fragmentos"]

    sem, lex = [], []
    if modo in ("semantico", "hibrido"):
        consulta = embeddings_preguntas([pregunta], _modelo()).astype("float32")
        sc, ps = indice.search(consulta, min(POOL_MAX, indice.ntotal))
        sem = [(int(p), float(s)) for s, p in zip(sc[0], ps[0])]
    if modo in ("lexico", "hibrido"):
        bm25, metodo = _bm25(estrategia)
        # La expansión con glosario (BUSQUEDA_EXPANSION) se aplica SOLO a esta consulta léxica.
        pesos = bm25.get_scores(tokens_consulta_lexica(pregunta, metodo))
        orden = np.argsort(-pesos, kind="stable")[:POOL_MAX]
        lex = [(int(i), float(pesos[i])) for i in orden if pesos[i] > 0]  # solo los que comparten palabras

    if modo == "semantico":
        base = sem
    elif modo == "lexico":
        base = [(i, s / lex[0][1]) for i, s in lex] if lex else []
    else:  # hibrido: Reciprocal Rank Fusion
        k = rrf_k()
        puntos = {}
        for lista in (sem, lex):
            for rango, (i, _) in enumerate(lista, start=1):
                puntos[i] = puntos.get(i, 0.0) + 1.0 / (k + rango)
        base = sorted(puntos.items(), key=lambda x: -x[1])
    return [(s, frs[i]) for i, s in base]


def buscar(pregunta: str, k: int = 3, estrategia: str = "articulo", modo: Optional[str] = None,
           clasificador: bool = True) -> List[dict]:
    """Devuelve los k fragmentos más relevantes, de mayor a menor score.

    Formato de cada fragmento (docs/api_contract.md):
        id, ubicacion (cadena), epigrafe, texto, score, vigencia, tema

    modo: "semantico", "lexico" (BM25) o "hibrido" (RRF de los dos). Si es None se usa
        BUSQUEDA_MODO del .env. La escala del `score` cambia con el modo (ver MODOS).

    Con `clasificador=True` (por defecto), igual en los tres modos:
      - Tema: el clasificador (retrieval/clasificador.py + temas.json) detecta el tema de la
        pregunta y SUMA un empuje al score de los candidatos de ese tema. Es un empuje, nunca
        un filtro. El empuje es el equivalente en la escala de cada modo (`empuje_por_modo`).
        El `score` devuelto incluye el empuje, que es el que decide el orden.
      - Artículo por número: si la pregunta pide "artículo N" / "art. N" y ese artículo existe
        en el índice, va primero (en ese caso la lista puede no quedar ordenada por score).
    Con `clasificador=False` el orden es solo el del modo elegido.

    Se devuelve como máximo un fragmento por artículo (el de mayor score).
    """
    modo = modo or modo_por_defecto()
    if modo not in MODOS:
        raise ValueError(f"Modo no soportado: {modo!r}. Disponibles: {list(MODOS)}")
    _, meta = _indice(estrategia)
    candidatos = _puntajes_base(pregunta, estrategia, modo)

    pedidos = []
    if clasificador:
        empuje = empujes(clasificar(pregunta), modo)
        if empuje:
            candidatos = [(sc + empuje.get(f["tema"], 0.0), f) for sc, f in candidatos]
            candidatos.sort(key=lambda c: -c[0])
        existentes = {id_articulo(f["id"]) for f in meta["fragmentos"]}
        pedidos = [f"art-{n}" for n in articulos_mencionados(pregunta) if f"art-{n}" in existentes]

    # Un solo fragmento por artículo: el de mayor score.
    mejores, vistos = [], set()
    for sc, f in candidatos:
        art = id_articulo(f["id"])
        if art not in vistos:
            vistos.add(art)
            mejores.append((sc, f))

    # Artículos pedidos por número: primero y en el orden en que se pidieron. Si el modo no
    # trajo ese artículo (p. ej. léxico sin coincidencias), entra su primer fragmento con score 0.
    primeros = []
    for art in pedidos:
        c = next((c for c in mejores if id_articulo(c[1]["id"]) == art), None)
        primeros.append(c or (0.0, next(f for f in meta["fragmentos"] if id_articulo(f["id"]) == art)))
    resto = [c for c in mejores if id_articulo(c[1]["id"]) not in pedidos]
    elegidos = (primeros + resto)[:k]

    resultados = []
    for score, f in elegidos:
        resultados.append({
            "id": f["id"],
            "ubicacion": formatear_ubicacion(f["ubicacion"]),
            "epigrafe": f["epigrafe"],
            "texto": f["texto"],
            "score": float(score),
            "vigencia": f["vigencia"],
            "tema": f["tema"],
            "fuente": f.get("fuente"),
            "archivo_fuente": f.get("archivo_fuente"),
            "pagina_inicio": f.get("pagina_inicio"),
            "pagina_fin": f.get("pagina_fin"),
            "paginas": f.get("paginas"),
            "ubicaciones_fuente": f.get("ubicaciones_fuente"),
            "fuentes": f.get("fuentes"),
        })
    return resultados


def _mostrar(pregunta: str, resultados: List[dict]) -> None:
    print(f"\n{pregunta}")
    for r in resultados:
        print(f"  {r['id'].replace('art-', ''):>4}  {r['score']:.4f}  {r['epigrafe']}  [{r['vigencia']}]")
        print(f"        {r['ubicacion']}")


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawTextHelpFormatter)
    ap.add_argument("pregunta", nargs="*")
    ap.add_argument("-k", type=int, default=3)
    ap.add_argument("--estrategia", default="articulo")
    ap.add_argument("--demo", action="store_true", help="prueba 3 preguntas y mide tiempos")
    ap.add_argument("--sin-clasificador", action="store_true", help="sin empuje por tema ni regla del artículo por número")
    ap.add_argument("--modo", choices=MODOS, default=None, help="semantico, lexico o hibrido (por defecto BUSQUEDA_MODO)")
    args = ap.parse_args()

    preguntas = PREGUNTAS_DEMO if args.demo else [" ".join(args.pregunta)] if args.pregunta else []
    if not preguntas:
        ap.error("indica una pregunta o usa --demo")

    t0 = time.perf_counter()
    precargar_busqueda(args.estrategia, args.modo)
    t_carga = time.perf_counter() - t0

    tiempos = []
    for p in preguntas:
        t = time.perf_counter()
        res = buscar(p, k=args.k, estrategia=args.estrategia, modo=args.modo, clasificador=not args.sin_clasificador)
        tiempos.append(time.perf_counter() - t)
        _mostrar(p, res)

    print(f"\nCarga inicial (modelo + índice): {t_carga:.2f} s")
    print("Tiempo por búsqueda: " + ", ".join(f"{t * 1000:.0f} ms" for t in tiempos))


if __name__ == "__main__":
    main()
