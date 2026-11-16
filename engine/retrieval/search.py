"""Búsqueda de fragmentos relevantes sobre el índice FAISS.

Uso como librería (desde engine/ o con engine/ en sys.path):
    from retrieval.search import buscar
    fragmentos = buscar("¿Qué pasa si no pago una multa?", k=3)

Uso por línea de comandos (desde la raíz del repo):
    python engine/retrieval/search.py "¿Qué pasa si no pago una multa?" [-k 3]
    python engine/retrieval/search.py --demo

El modelo y el índice se cargan UNA sola vez por proceso (en la primera llamada,
o antes con precargar()) y se reutilizan en las llamadas siguientes.

VERSIONES DEL ÍNDICE (reprocesamiento del corpus): el índice de cada estrategia vive en memoria
como una «versión» (FAISS + metadatos + tokens BM25 + artículos completos) que se reemplaza ENTERA
y de una sola vez con instalar_version() cuando termina un reprocesamiento. Cada búsqueda toma una
sola versión al empezar y la usa hasta el final, así nunca mezcla datos viejos y nuevos.
"""
import argparse
import json
import os
import re
import sys
import threading
import time
from functools import lru_cache
from pathlib import Path
from typing import List, Optional

import faiss
import numpy as np
from dotenv import load_dotenv
from rank_bm25 import BM25Okapi

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))  # carpeta engine/
from indexing import normas  # noqa: E402
from indexing.embeddings import PREGUNTAS_DEMO, cargar_corpus_completo, cargar_modelo, embeddings_preguntas  # noqa: E402
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
MODO_POR_DEFECTO = "semantico"  # si no hay BUSQUEDA_MODO en el .env. Con el corpus real (249 art.) gana el semántico: ver docs/busqueda_hibrida.md


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


class Version:
    """Una versión completa del índice de una estrategia. Inmutable una vez creada."""

    def __init__(self, indice, meta: dict, datos_bm25: Optional[dict], articulos: Optional[dict] = None):
        self.indice = indice
        self.meta = meta
        self.datos_bm25 = datos_bm25          # {"metodo", "descripcion_metodo", "k1", "b", "tokens"} o None
        self._bm25 = None
        self._candado = threading.Lock()
        # Artículos completos (small-to-big): corpus base + normas adicionales de ESTA versión.
        # El reprocesamiento los pasa ya armados (`articulos`), para no leer archivos que aún no confirmó.
        self.articulos = articulos if articulos is not None else {
            a["id"]: a for a in cargar_corpus_completo(Path(meta["corpus"]), meta.get("corpus_adicionales", []))}

    def bm25(self):
        """(BM25Okapi, método de preparación del texto); se arma la primera vez que se pide."""
        if self._bm25 is None:
            if self.datos_bm25 is None:
                raise FileNotFoundError(
                    f"No existe el índice BM25 de '{self.meta.get('estrategia')}'. Reconstruye el índice: "
                    f"python engine/indexing/build_index.py --estrategia {self.meta.get('estrategia')}"
                )
            with self._candado:
                if self._bm25 is None:
                    d = self.datos_bm25
                    self._bm25 = (BM25Okapi(d["tokens"], k1=d["k1"], b=d["b"]), d["metodo"])
        return self._bm25

    def normas(self) -> List[dict]:
        """[{"norma": "Ley 1801 de 2016", "articulos": 249}, ...] (la base primero)."""
        conteo = {}
        for a in self.articulos.values():
            n = a.get("norma") or normas.NORMA_BASE
            conteo[n] = conteo.get(n, 0) + 1
        return [{"norma": n, "articulos": conteo[n]} for n in normas.ordenar(list(conteo))]


_VERSIONES = {}                  # estrategia -> Version vigente
_CANDADO_VERSIONES = threading.Lock()


def leer_version(carpeta: Path) -> Version:
    """Lee de disco una versión del índice (index.faiss, metadatos.json y bm25_tokens.json)."""
    if not (carpeta / "index.faiss").exists():
        raise FileNotFoundError(
            f"No existe el índice '{carpeta.name}'. Constrúyelo con: "
            f"python engine/indexing/build_index.py --estrategia {carpeta.name}"
        )
    datos = (carpeta / "index.faiss").read_bytes()  # lectura con Python: evita fallos con tildes en la ruta
    indice = faiss.deserialize_index(np.frombuffer(datos, dtype="uint8"))
    meta = json.loads((carpeta / "metadatos.json").read_text(encoding="utf-8"))
    ruta_bm25 = carpeta / "bm25_tokens.json"
    datos_bm25 = json.loads(ruta_bm25.read_text(encoding="utf-8")) if ruta_bm25.exists() else None
    return Version(indice, meta, datos_bm25)


def _version(estrategia: str) -> Version:
    """Versión vigente del índice de esa estrategia (la carga de disco la primera vez)."""
    v = _VERSIONES.get(estrategia)
    if v is None:
        with _CANDADO_VERSIONES:
            v = _VERSIONES.get(estrategia)
            if v is None:
                v = leer_version(CARPETA_INDICES / estrategia)
                _VERSIONES[estrategia] = v
    return v


def instalar_version(estrategia: str, version: Version) -> None:
    """Cambia a `version` de forma atómica: las búsquedas que empiecen después ya la usan."""
    if version.datos_bm25 is not None and modo_por_defecto() in ("lexico", "hibrido"):
        version.bm25()  # se prepara antes del cambio, para que la primera búsqueda no lo pague
    with _CANDADO_VERSIONES:
        _VERSIONES[estrategia] = version


def recargar(estrategia: str) -> None:
    """Vuelve a leer de disco el índice de esa estrategia y lo instala."""
    instalar_version(estrategia, leer_version(CARPETA_INDICES / estrategia))


def _indice(estrategia: str):
    """(índice FAISS, metadatos) de la versión vigente."""
    v = _version(estrategia)
    return v.indice, v.meta


def precargar(estrategia: str = "articulo") -> None:
    """Carga modelo e índice por adelantado (p. ej. al arrancar la API)."""
    _modelo()
    _version(estrategia)


def info_indice(estrategia: str = "articulo") -> dict:
    """Datos del índice cargado: estrategia, modelo, número de fragmentos y normas."""
    v = _version(estrategia)
    return {"estrategia": estrategia, "modelo": v.meta["modelo"], "fragmentos": int(v.indice.ntotal),
            "corpus": v.meta.get("corpus"), "carga_corpus": v.meta.get("carga_corpus"),
            "corpus_adicionales": v.meta.get("corpus_adicionales", []),
            "normas_adicionales": v.meta.get("normas_adicionales", []), "normas": v.normas()}


def normas_cargadas(estrategia: str = "fragmentos") -> List[dict]:
    """Normas que tiene el índice vigente, con su número de artículos."""
    return _version(estrategia).normas()


def _articulos_del_corpus(estrategia: str) -> dict:
    """Artículos completos (corpus base + normas adicionales) de la versión vigente, por id."""
    return _version(estrategia).articulos


def articulo_completo(id_fragmento: str, estrategia: str = "fragmentos", version: Optional[Version] = None) -> dict:
    """Artículo completo al que pertenece un fragmento (para small-to-big).

    Devuelve id, norma, ubicacion (cadena), epigrafe, texto, vigencia y tema del artículo.
    """
    v = version or _version(estrategia)
    a = v.articulos.get(id_articulo(id_fragmento))
    if a is None:
        # Documento complementario (subido por /upload_pdf/): no está en el corpus,
        # así que se usa el propio fragmento como contexto.
        a = next(f for f in v.meta["fragmentos"] if f["id"] == id_fragmento)
        a = {**a, "id": id_articulo(a["id"])}
    return {
        "id": a["id"],
        "norma": a.get("norma") or normas.NORMA_BASE,
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


MAX_CARACTERES_CONTEXTO = 12000  # el artículo más largo de la Ley 1801 tiene ~9.000; la Ley 769 tiene uno de 28.000


def articulo_para_contexto(id_fragmento: str, estrategia: str = "fragmentos", version: Optional[Version] = None,
                           max_caracteres: int = MAX_CARACTERES_CONTEXTO) -> dict:
    """Small-to-big con tope: el artículo completo, salvo que sea enorme.

    Si el artículo pasa de `max_caracteres` (p. ej. el art. 131 de la Ley 769, con todas las multas),
    se manda al modelo solo el trozo encontrado y sus vecinos, avisando que es un extracto. Así el
    prompt no se dispara de tamaño (los planes gratuitos limitan los tokens por minuto).
    """
    v = version or _version(estrategia)
    a = articulo_completo(id_fragmento, estrategia, v)
    if len(a["texto"]) <= max_caracteres:
        return a
    m = re.search(r"-f(\d+)$", id_fragmento)
    if m:
        n, base = int(m.group(1)), id_articulo(id_fragmento)
        por_id = {f["id"]: f["texto"] for f in v.meta["fragmentos"] if id_articulo(f["id"]) == base}
        trozos = [por_id[f"{base}-f{i}"] for i in (n - 1, n, n + 1) if f"{base}-f{i}" in por_id]
        texto = "\n[...]\n".join(trozos)
    else:
        texto = a["texto"][:max_caracteres]
    aviso = ("[EXTRACTO: este artículo es muy largo; aquí van solo los trozos más relevantes para la pregunta. "
             "Si la respuesta necesita otra parte del artículo, dilo.]\n")
    return {**a, "texto": aviso + texto[:max_caracteres]}


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


def _bm25(estrategia: str):
    """(BM25Okapi, método de preparación del texto) de la versión vigente."""
    return _version(estrategia).bm25()


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


def _puntajes_base(pregunta: str, estrategia: str, modo: str, version: Optional[Version] = None) -> list:
    """[(score, fragmento)] de mayor a menor, según el modo y SIN clasificador."""
    v = version or _version(estrategia)
    indice, meta = v.indice, v.meta
    frs = meta["fragmentos"]

    sem, lex = [], []
    if modo in ("semantico", "hibrido"):
        consulta = embeddings_preguntas([pregunta], _modelo()).astype("float32")
        sc, ps = indice.search(consulta, min(POOL_MAX, indice.ntotal))
        sem = [(int(p), float(s)) for s, p in zip(sc[0], ps[0])]
    if modo in ("lexico", "hibrido"):
        bm25, metodo = v.bm25()
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


def _pedidos_por_numero(pregunta: str, v: "Version") -> tuple:
    """Artículos que la pregunta pide por número («artículo 131»), con varias normas cargadas.

    Devuelve (pedidos, otras):
      - pedidos: ids de artículo, en el orden en que se pidieron.
      - otras: [{"numero", "norma", "otras": [...]}] cuando la pregunta NO nombra la norma y más de
        una norma cargada tiene ese número: se usa la de mayor prioridad (NORMA_PRINCIPAL, por defecto
        la Ley 1801 de 2016) y `otras` son las demás.
    Si la pregunta nombra la norma («artículo 131 de la Ley 769», «del Código de Tránsito»), el número
    es de esa norma. Si nombra una norma que no está cargada, no se prioriza ningún artículo.
    """
    numeros = articulos_mencionados(pregunta)
    if not numeros:
        return [], []
    existentes = {id_articulo(f["id"]) for f in v.meta["fragmentos"]}
    cargadas = {normas.clave(x["norma"]): x["norma"] for x in v.normas()}
    menciones = normas.mencionadas(pregunta)
    nombradas = [cargadas[c] for c in menciones if c in cargadas]
    if menciones and not nombradas:
        return [], []
    orden = normas.por_prioridad(list(cargadas.values()))
    pedidos, otras = [], []
    for n in numeros:
        if nombradas:
            for norma in nombradas:
                ida = normas.id_articulo(norma, n)
                if ida in existentes and ida not in pedidos:
                    pedidos.append(ida)
            continue
        con = [x for x in orden if normas.id_articulo(x, n) in existentes]
        if con:
            ida = normas.id_articulo(con[0], n)
            if ida not in pedidos:
                pedidos.append(ida)
            if len(con) > 1:
                otras.append({"numero": n, "norma": con[0], "otras": con[1:]})
    return pedidos, otras


def otras_normas_con_articulo(pregunta: str, estrategia: str = "fragmentos") -> List[dict]:
    """Si la pregunta pide «artículo N» sin decir la norma y otras normas cargadas también tienen un
    artículo N: [{"numero": "163", "norma": "Ley 1801 de 2016", "otras": ["Ley 769 de 2002"]}]."""
    return _pedidos_por_numero(pregunta, _version(estrategia))[1]


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
    v = _version(estrategia)  # una sola versión durante toda la búsqueda
    meta = v.meta
    candidatos = _puntajes_base(pregunta, estrategia, modo, v)

    pedidos = []
    if clasificador:
        empuje = empujes(clasificar(pregunta), modo)
        if empuje:
            candidatos = [(sc + empuje.get(f["tema"], 0.0), f) for sc, f in candidatos]
            candidatos.sort(key=lambda c: -c[0])
        pedidos, otras = _pedidos_por_numero(pregunta, v)
        # Si la pregunta no dijo la norma, los artículos con ese mismo número de las demás normas no
        # se mezclan en la respuesta: el responder solo avisa que existen (ver otras_normas_con_articulo).
        excluir = {normas.id_articulo(o, x["numero"]) for x in otras for o in x["otras"]}
        candidatos = [c for c in candidatos if id_articulo(c[1]["id"]) not in excluir]

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
            "norma": f.get("norma") or normas.NORMA_BASE,
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
