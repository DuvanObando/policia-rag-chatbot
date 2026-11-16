"""Reprocesamiento del corpus: agrega, reemplaza o quita una NORMA en los índices, de forma INCREMENTAL.

Lo usa la API (POST /corpus/reprocesar) y también se puede correr a mano:

    # agregar (o reemplazar) una norma desde su PDF
    python engine/indexing/reprocesar.py --pdf ley769.pdf --norma "Ley 769 de 2002" [--url URL]
    # volver a cargar una norma ya procesada, desde su JSON (sin el PDF)
    python engine/indexing/reprocesar.py --json corpus/procesados/ley_769_de_2002.json
    # quitar una norma de los índices (el JSON se conserva en corpus/procesados/)
    python engine/indexing/reprocesar.py --quitar "Ley 769 de 2002"

Cómo funciona (para las dos estrategias, «articulo» y «fragmentos»):
  1. EXTRAE: corpus/pipeline/procesar_pdf.py convierte el PDF en registros (uno por artículo).
  2. INDEXA: parte de la versión VIGENTE del índice (la que está respondiendo), le quita los
     fragmentos de esa norma si ya estaba, calcula embeddings SOLO de los fragmentos nuevos y los
     agrega a una COPIA del índice FAISS, de los tokens BM25 y de los metadatos. Los tokens BM25
     nuevos se preparan con el MISMO método con que se construyó el índice (no con el disponible
     ahora), para que sigan coincidiendo.
  3. GUARDA la versión nueva en indexes/<estrategia>.nuevo/.
  4. CAMBIA de versión solo si las dos estrategias terminaron bien: escribe el JSON de la norma
     en corpus/procesados/, renombra indexes/<estrategia> -> <estrategia>.anterior y
     <estrategia>.nuevo -> <estrategia>, y recién entonces instala las versiones nuevas en memoria.
  Mientras tanto el motor sigue respondiendo con la versión anterior. Si algo falla antes del
  cambio, se borran los .nuevo y todo queda como estaba. La versión previa queda en .anterior.

Solo un trabajo a la vez (TrabajoOcupado). Los trabajos viven en memoria: si se reinicia el motor,
se pierde su historial (los índices sí quedan en disco).

La Ley 1801 (norma base) no se reprocesa por aquí: para cambiarla, reconstruir con build_index.py.
"""
import argparse
import importlib.util
import json
import os
import shutil
import sys
import threading
import time
import uuid
from datetime import datetime
from pathlib import Path
from typing import List, Optional

import faiss
import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))  # carpeta engine/
from indexing import normas, uploads  # noqa: E402
from indexing.build_index import CAMPOS, CARPETA_INDICES, ESTRATEGIAS, SOLAPE_POR_DEFECTO, TAMANO_POR_DEFECTO, guardar_indice  # noqa: E402
from indexing.cargador_corpus import adaptar_norma  # noqa: E402
from indexing.embeddings import RAIZ, embeddings_articulos, ruta_relativa, texto_articulo  # noqa: E402
from preprocess.texto_bm25 import tokens_bm25_lote  # noqa: E402
from retrieval import search  # noqa: E402

ESTRATEGIAS_INDICE = ("articulo", "fragmentos")
CARPETA_PROCESADOS = RAIZ / "corpus" / "procesados"
RUTA_PIPELINE = RAIZ / "corpus" / "pipeline" / "procesar_pdf.py"

ESTADOS = ("en_cola", "extrayendo", "indexando", "listo", "error")


class TrabajoOcupado(Exception):
    """Ya hay un reprocesamiento en curso."""


class ErrorReproceso(Exception):
    """Error con un mensaje claro en español, que se puede mostrar al usuario."""


# ---------------------------------------------------------------- utilidades

def _procesar_pdf():
    """Función procesar_pdf del pipeline (se carga del archivo cada vez: Wilder puede cambiarlo)."""
    spec = importlib.util.spec_from_file_location("procesar_pdf_pipeline", RUTA_PIPELINE)
    modulo = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(modulo)
    return modulo.procesar_pdf


def _reintentar(funcion, intentos: int = 30, espera: float = 0.5):
    """Windows/OneDrive a veces bloquean un archivo unos instantes: se reintenta antes de fallar."""
    for i in range(intentos):
        try:
            return funcion()
        except PermissionError:
            if i == intentos - 1:
                raise
            time.sleep(espera)


def validar_registros(registros: List[dict], norma: str) -> None:
    """Comprueba que la salida de procesar_pdf() tenga el formato acordado."""
    obligatorias = ("id", "norma", "ubicacion", "epigrafe", "texto", "vigencia", "tema", "pdf", "pagina", "fuente_url")
    if not registros:
        raise ErrorReproceso("El PDF no produjo ningún artículo.")
    ids = set()
    for r in registros:
        faltan = [c for c in obligatorias if c not in r]
        if faltan:
            raise ErrorReproceso(f"El registro {r.get('id', '?')} no trae los campos {faltan} (ver corpus/pipeline/procesar_pdf.py).")
        if normas.clave(r["norma"]) != normas.clave(norma):
            raise ErrorReproceso(f"El registro {r['id']} dice ser de {r['norma']}, no de {norma}.")
        if not r["id"].startswith(normas.prefijo_id(norma) + "art-"):
            raise ErrorReproceso(f"El id {r['id']} no sigue el formato {normas.id_articulo(norma, 'N')}.")
        if r["id"] in ids:
            raise ErrorReproceso(f"El id {r['id']} está repetido.")
        ids.add(r["id"])


# ---------------------------------------------------------------- versión nueva (en memoria)

def _fragmentos(registros: List[dict], estrategia: str, meta: dict, modelo) -> List[dict]:
    parametros = meta.get("parametros") or {}
    trozos = ESTRATEGIAS[estrategia](registros, modelo, tamano=parametros.get("tamano", TAMANO_POR_DEFECTO),
                                     solape=parametros.get("solape", SOLAPE_POR_DEFECTO))
    return [{c: f.get(c) for c in CAMPOS} for f in trozos]


def preparar_version(estrategia: str, norma: str, registros: Optional[List[dict]], archivo_rel: Optional[str],
                     info_norma: Optional[dict] = None) -> search.Version:
    """Versión nueva = versión vigente - fragmentos de `norma` + fragmentos de `registros`.

    registros=None quita la norma. No toca disco ni la versión vigente.
    """
    v = search._version(estrategia)
    clave = normas.clave(norma)
    viejos = v.meta["fragmentos"]
    quitar = [i for i, f in enumerate(viejos) if f.get("norma") and normas.clave(f["norma"]) == clave]
    conservar_pos = sorted(set(range(len(viejos))) - set(quitar))

    indice = faiss.clone_index(v.indice)
    if quitar:
        indice.remove_ids(np.array(quitar, dtype="int64"))
    fragmentos = [viejos[i] for i in conservar_pos]
    datos = v.datos_bm25 or {}
    tokens = [datos["tokens"][i] for i in conservar_pos] if datos else None

    nuevos = []
    if registros:
        nuevos = _fragmentos(registros, estrategia, v.meta, search._modelo())
        vectores = embeddings_articulos(nuevos, search._modelo()).astype("float32")
        indice.add(vectores)
        fragmentos += nuevos
        if tokens is not None:
            # El MISMO método del índice (p. ej. snowball), aunque ahora haya otro disponible.
            tokens += tokens_bm25_lote([texto_articulo(f) for f in nuevos], datos["metodo"])
    if indice.ntotal != len(fragmentos) or (tokens is not None and len(tokens) != len(fragmentos)):
        raise ErrorReproceso(f"Índice '{estrategia}' inconsistente tras el cambio (vectores {indice.ntotal}, "
                             f"fragmentos {len(fragmentos)}): no se aplicó nada.")

    meta = dict(v.meta)
    adicionales = [a for a in meta.get("corpus_adicionales", []) if not _es_archivo_de(a, norma)]
    detalle = [d for d in meta.get("normas_adicionales", []) if normas.clave(d["norma"]) != clave]
    if registros:
        adicionales.append(archivo_rel)
        detalle.append({**(info_norma or {}), "norma": norma, "archivo": archivo_rel, "articulos": len(registros),
                        "fragmentos": len(nuevos), "fecha_carga": datetime.now().isoformat(timespec="seconds")})
    meta.update(
        fragmentos=fragmentos, n_fragmentos=len(fragmentos), corpus_adicionales=adicionales, normas_adicionales=detalle,
        fecha_actualizacion=datetime.now().isoformat(timespec="seconds"),
        historial_reprocesos=(meta.get("historial_reprocesos") or []) + [{
            "fecha": datetime.now().isoformat(timespec="seconds"), "accion": "agregar" if registros else "quitar",
            "norma": norma, "fragmentos_quitados": len(quitar), "fragmentos_agregados": len(nuevos)}],
    )
    datos_nuevos = {**datos, "tokens": tokens} if tokens is not None else None

    articulos = {i: a for i, a in v.articulos.items() if not (a.get("norma") and normas.clave(a["norma"]) == clave)}
    for a in adaptar_norma(registros or []):
        articulos[a["id"]] = a
    return search.Version(indice, meta, datos_nuevos, articulos=articulos)


def _es_archivo_de(ruta_rel: str, norma: str) -> bool:
    return Path(ruta_rel).name == normas.nombre_archivo(norma)


# ---------------------------------------------------------------- disco y cambio atómico

def _guardar(version: search.Version, carpeta: Path) -> None:
    _apartar(carpeta)
    carpeta.mkdir(parents=True)
    guardar_indice(version.indice, carpeta / "index.faiss")
    if version.datos_bm25 is not None:
        (carpeta / "bm25_tokens.json").write_text(json.dumps(version.datos_bm25, ensure_ascii=False), encoding="utf-8")
    (carpeta / "metadatos.json").write_text(json.dumps(version.meta, ensure_ascii=False, indent=2), encoding="utf-8")


def _apartar(carpeta: Path) -> None:
    """Saca del camino una carpeta vieja sin hacer fallar el cambio.

    OneDrive a veces bloquea el borrado de una carpeta (incluso vacía) pero sí deja renombrarla:
    se renombra a <nombre>.borrar-<n> y se intenta borrar; si no se puede, la limpia el próximo
    reprocesamiento (_limpiar_nuevas).
    """
    if not carpeta.exists():
        return
    basura = carpeta.with_name(f"{carpeta.name}.borrar-{time.time_ns()}")
    _reintentar(lambda: os.replace(carpeta, basura))
    shutil.rmtree(basura, ignore_errors=True)


def _cambiar_carpetas(estrategia: str) -> None:
    """indexes/<e> -> <e>.anterior y <e>.nuevo -> <e>."""
    actual, nueva, anterior = (CARPETA_INDICES / estrategia, CARPETA_INDICES / f"{estrategia}.nuevo",
                               CARPETA_INDICES / f"{estrategia}.anterior")
    _apartar(anterior)
    _reintentar(lambda: os.replace(actual, anterior))
    try:
        _reintentar(lambda: os.replace(nueva, actual))
    except Exception:
        _reintentar(lambda: os.replace(anterior, actual))  # deja la versión de antes
        raise


def _deshacer_carpetas(estrategia: str) -> None:
    actual, anterior = CARPETA_INDICES / estrategia, CARPETA_INDICES / f"{estrategia}.anterior"
    if anterior.exists():
        _apartar(actual)
        _reintentar(lambda: os.replace(anterior, actual))


def _limpiar_nuevas() -> None:
    for e in ESTRATEGIAS_INDICE:
        carpeta = CARPETA_INDICES / f"{e}.nuevo"
        if carpeta.exists():
            shutil.rmtree(carpeta, ignore_errors=True)
    for basura in CARPETA_INDICES.glob("*.borrar-*"):  # restos que OneDrive no dejó borrar antes
        shutil.rmtree(basura, ignore_errors=True)


_CANDADO_CAMBIO = threading.Lock()


def aplicar(norma: str, registros: Optional[List[dict]], info_norma: Optional[dict] = None, avisar=None) -> dict:
    """Agrega/reemplaza (registros) o quita (registros=None) una norma en las dos estrategias.

    Todo o nada: si algo falla antes del cambio, los índices y el corpus quedan como estaban.
    avisar(estado, progreso) informa el avance. Devuelve un resumen con tiempos y conteos.
    """
    avisar = avisar or (lambda *a: None)
    if normas.es_base(norma):
        raise ErrorReproceso("La Ley 1801 de 2016 es la norma base: para cambiarla, reconstruye los índices con build_index.py.")
    archivo = CARPETA_PROCESADOS / normas.nombre_archivo(norma)
    archivo_rel = ruta_relativa(archivo)
    versiones, tiempos = {}, {}
    try:
        for i, estrategia in enumerate(ESTRATEGIAS_INDICE):
            avisar("indexando", 30 + 30 * i)
            t = time.perf_counter()
            versiones[estrategia] = preparar_version(estrategia, norma, registros, archivo_rel, info_norma)
            _guardar(versiones[estrategia], CARPETA_INDICES / f"{estrategia}.nuevo")
            tiempos[estrategia] = round(time.perf_counter() - t, 1)
        avisar("indexando", 92)
        with _CANDADO_CAMBIO:
            if registros:
                temporal = archivo.with_suffix(".json.tmp")
                temporal.write_text(json.dumps(registros, ensure_ascii=False, indent=1), encoding="utf-8")
                _reintentar(lambda: os.replace(temporal, archivo))
            hechas = []
            try:
                for estrategia in ESTRATEGIAS_INDICE:
                    _cambiar_carpetas(estrategia)
                    hechas.append(estrategia)
            except Exception:
                for estrategia in hechas:
                    _deshacer_carpetas(estrategia)
                raise
            for estrategia in ESTRATEGIAS_INDICE:   # recién ahora: el motor pasa a la versión nueva
                search.instalar_version(estrategia, versiones[estrategia])
    finally:
        _limpiar_nuevas()
    return {
        "norma": norma,
        "archivo": archivo_rel if registros else None,
        "articulos": len(registros or []),
        "fragmentos_nuevos": {e: sum(1 for f in versiones[e].meta["fragmentos"] if f.get("norma") and normas.clave(f["norma"]) == normas.clave(norma))
                              for e in ESTRATEGIAS_INDICE},
        "tiempos_indexado_s": tiempos,
    }


# ---------------------------------------------------------------- trabajos en segundo plano (API)

_TRABAJOS = {}
_CANDADO_TRABAJOS = threading.Lock()
_ACTIVO = {"id": None}


def _ahora() -> str:
    return datetime.now().isoformat(timespec="seconds")


def trabajo(trabajo_id: str) -> Optional[dict]:
    t = _TRABAJOS.get(trabajo_id)
    return dict(t) if t else None


def trabajo_activo() -> Optional[str]:
    return _ACTIVO["id"]


def lanzar(documento_id: str, norma: Optional[str] = None, fuente_url: Optional[str] = None) -> dict:
    """Valida y lanza el reprocesamiento de un PDF subido. Responde de inmediato con el trabajo.

    Lanza KeyError si el documento no existe, ValueError si falta o no sirve la norma,
    TrabajoOcupado si ya hay un trabajo corriendo.
    """
    doc = next((d for d in uploads.leer_registro() if d["id"] == documento_id), None)
    if doc is None or not (uploads.CARPETA_UPLOADS / doc["nombre"]).exists():
        raise KeyError(documento_id)
    norma = normas.normalizar(norma or doc.get("norma") or "")
    if normas.es_base(norma):
        raise ValueError("La Ley 1801 de 2016 es la norma base: no se reprocesa por aquí (ver docs/reprocesamiento.md).")
    fuente_url = fuente_url or doc.get("fuente_url")

    with _CANDADO_TRABAJOS:
        if _ACTIVO["id"]:
            raise TrabajoOcupado(_ACTIVO["id"])
        t = {"trabajo_id": uuid.uuid4().hex[:12], "documento": documento_id, "norma": norma, "estado": "en_cola",
             "progreso": 0, "articulos_procesados": 0, "fragmentos_nuevos": None, "error": None,
             "creado": _ahora(), "inicio": None, "fin": None, "duracion_s": None, "tiempos_s": {}}
        _TRABAJOS[t["trabajo_id"]] = t
        _ACTIVO["id"] = t["trabajo_id"]
    threading.Thread(target=_ejecutar, args=(t["trabajo_id"], doc, norma, fuente_url), daemon=True,
                     name=f"reprocesar-{t['trabajo_id']}").start()
    return dict(t)


def _ejecutar(trabajo_id: str, doc: dict, norma: str, fuente_url: Optional[str]) -> None:
    t = _TRABAJOS[trabajo_id]
    t0 = time.perf_counter()
    t["inicio"] = _ahora()

    def avisar(estado, progreso):
        t["estado"], t["progreso"] = estado, progreso

    try:
        avisar("extrayendo", 5)
        te = time.perf_counter()
        registros = _procesar_pdf()(uploads.CARPETA_UPLOADS / doc["nombre"], norma, fuente_url)
        validar_registros(registros, norma)
        t["articulos_procesados"] = len(registros)
        t["tiempos_s"]["extraccion"] = round(time.perf_counter() - te, 1)
        avisar("indexando", 25)
        r = aplicar(norma, registros, {"fuente_url": fuente_url, "documento": doc["id"], "pdf": doc["nombre"]}, avisar)
        t["fragmentos_nuevos"] = r["fragmentos_nuevos"]
        t["tiempos_s"]["indexado"] = r["tiempos_indexado_s"]
        t["archivo"] = r["archivo"]
        uploads.marcar_procesado(doc["id"], norma, len(registros))
        avisar("listo", 100)
    except Exception as e:  # el mensaje no lleva texto del documento, solo el motivo
        t["estado"] = "error"
        t["error"] = str(e) if isinstance(e, (ErrorReproceso, ValueError)) else (
            f"Falló el reprocesamiento ({type(e).__name__}). Los índices quedaron como estaban.")
    finally:
        t["fin"] = _ahora()
        t["duracion_s"] = round(time.perf_counter() - t0, 1)
        _ACTIVO["id"] = None


# ---------------------------------------------------------------- línea de comandos

def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawTextHelpFormatter)
    grupo = ap.add_mutually_exclusive_group(required=True)
    grupo.add_argument("--pdf", help="PDF de la norma (se procesa con corpus/pipeline/procesar_pdf.py)")
    grupo.add_argument("--json", help="JSON ya procesado de una norma (p. ej. corpus/procesados/ley_769_de_2002.json)")
    grupo.add_argument("--quitar", metavar="NORMA", help='norma que se quita de los índices, p. ej. "Ley 769 de 2002"')
    ap.add_argument("--norma", help='norma del PDF, p. ej. "Ley 769 de 2002" (obligatoria con --pdf)')
    ap.add_argument("--url", default=None, help="URL oficial de la fuente (con --pdf)")
    args = ap.parse_args()

    t0 = time.perf_counter()
    if args.quitar:
        norma, registros = normas.normalizar(args.quitar), None
    elif args.pdf:
        if not args.norma:
            ap.error("--norma es obligatoria con --pdf")
        norma = normas.normalizar(args.norma)
        registros = _procesar_pdf()(Path(args.pdf), norma, args.url)
    else:
        registros = json.loads(Path(args.json).read_text(encoding="utf-8"))
        norma = normas.normalizar(registros[0]["norma"]) if registros else ap.error("el JSON está vacío")
    if registros is not None:
        validar_registros(registros, norma)
    print(f"{'Quitando' if registros is None else 'Agregando'} {norma}"
          + ("" if registros is None else f": {len(registros)} artículos") + " ...")
    r = aplicar(norma, registros, {"fuente_url": args.url} if args.url else None,
                lambda e, p: print(f"  {e} {p}%", flush=True))
    print(f"Listo en {time.perf_counter() - t0:.1f} s: {r}")
    for e in ESTRATEGIAS_INDICE:
        print(f"  {e}: {search.info_indice(e)['normas']}")
    print("Si el motor está corriendo, reinícialo para que use los índices nuevos.")


if __name__ == "__main__":
    main()
