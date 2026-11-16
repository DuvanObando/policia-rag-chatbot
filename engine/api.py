"""API del motor RAG sobre la Ley 1801 de 2016 y las normas que se agreguen al corpus.

Contrato: ver docs/api_contract.md (y docs/reprocesamiento.md para el corpus)

Endpoints:
    GET  /health                          estado del motor y normas cargadas
    POST /query                           pregunta -> respuesta con citas (búsqueda + LLM)
    POST /upload_pdf/                     guarda un PDF como "pendiente_de_indexar" (NO regenera embeddings, RF4)
    POST /corpus/reprocesar               (token de administrador) incorpora un PDF subido como norma, en segundo plano
    GET  /corpus/reprocesar/{trabajo_id}  estado de ese trabajo
    GET  /corpus/documentos               normas cargadas y documentos subidos

Arranque (desde la carpeta engine/):
    uvicorn api:app --port 8000

PRIVACIDAD (Ley 1581 de 2012): este servicio NO registra el texto de las preguntas
ni de las respuestas, ni el historial. Los logs solo contienen estado, tiempos,
modelo usado y conteos. Tampoco se guarda nada en disco ni en base de datos.
Al agregar logs nuevos, no incluyas `q.pregunta`, `respuesta` ni `historial`, ni
imprimas objetos que los contengan.
"""
import hmac
import logging
import os
import sys
import time
from contextlib import asynccontextmanager
from pathlib import Path
from typing import List, Optional

sys.path.insert(0, str(Path(__file__).resolve().parent))  # carpeta engine/

from fastapi import FastAPI, File, Form, Header, Request, UploadFile
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from pydantic import BaseModel, field_validator

from generation.llm import ErrorLLM, configuracion, orden_proveedores, precargar_cliente, respaldo_externo
from generation.responder import ESTRATEGIA, responder
from indexing import normas, reprocesar, uploads
from indexing.embeddings import MODELO
from retrieval import expansion
from retrieval.search import buscar, info_indice, modo_por_defecto, normas_cargadas, precargar_busqueda, rrf_k, verificar_bm25

MAX_PREGUNTA = 500  # caracteres
MAX_HISTORIAL = 50  # mensajes
MENSAJE_OCUPADO = "El servicio está ocupado, intenta de nuevo en unos minutos."

log = logging.getLogger("motor")
logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")


# ---------------------------------------------------------------- arranque

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Carga todo al arrancar, para que la primera pregunta no pague la carga."""
    estado = {"listo": False, "error": None, "tiempos": {}, "modo_busqueda": None}
    app.state.motor = estado
    t0 = time.perf_counter()
    log.info("Cargando motor (embeddings, índice, cliente LLM)...")

    t = time.perf_counter()
    busqueda_ok = True
    try:
        estado["modo_busqueda"] = modo_por_defecto()   # BUSQUEDA_MODO del .env
        precargar_busqueda(ESTRATEGIA)                 # embeddings + índice FAISS (+ BM25 si el modo lo usa)
        if estado["modo_busqueda"] in ("lexico", "hibrido"):
            problema = verificar_bm25(ESTRATEGIA)      # ¿el índice BM25 se preparó igual que ahora?
            if problema:
                raise ValueError(problema)
        buscar("calentamiento", k=1, estrategia=ESTRATEGIA)  # primera codificación (más lenta)
    except (ValueError, FileNotFoundError, RuntimeError) as e:  # modo inválido, índice BM25 faltante o inconsistente
        busqueda_ok = False
        estado["error"] = str(e)
        log.error("  búsqueda no disponible: %s", e)
    estado["tiempos"]["embeddings_e_indice_s"] = round(time.perf_counter() - t, 2)
    log.info("  búsqueda (modo %s): %.1f s", estado["modo_busqueda"], estado["tiempos"]["embeddings_e_indice_s"])

    t = time.perf_counter()
    try:
        precargar_cliente()
        estado["listo"] = busqueda_ok
    except ErrorLLM as e:
        estado["error"] = estado["error"] or str(e)
        log.error("  cliente LLM no disponible: %s", e)
    estado["tiempos"]["cliente_llm_s"] = round(time.perf_counter() - t, 2)
    log.info("  cliente LLM: %.2f s", estado["tiempos"]["cliente_llm_s"])

    estado["tiempos"]["total_s"] = round(time.perf_counter() - t0, 2)
    log.info("Carga total: %.1f s | listo=%s", estado["tiempos"]["total_s"], estado["listo"])
    yield


app = FastAPI(title="Motor RAG - Ley 1801 de 2016 y otras normas", lifespan=lifespan)


# ---------------------------------------------------------------- modelos

class Query(BaseModel):
    pregunta: str
    historial: Optional[List[dict]] = None  # se acepta según el contrato, pero aún NO se usa

    @field_validator("pregunta")
    @classmethod
    def validar_pregunta(cls, v: str) -> str:
        v = v.strip()
        if not v:
            raise ValueError("La pregunta no puede estar vacía.")
        if len(v) > MAX_PREGUNTA:
            raise ValueError(f"La pregunta es demasiado larga: máximo {MAX_PREGUNTA} caracteres.")
        return v

    @field_validator("historial")
    @classmethod
    def validar_historial(cls, v):
        if v is not None and len(v) > MAX_HISTORIAL:
            raise ValueError(f"El historial es demasiado largo: máximo {MAX_HISTORIAL} mensajes.")
        return v


class UbicacionFuente(BaseModel):
    archivo: str
    pagina_inicio: int
    pagina_fin: int
    paginas: List[int]


class Fragmento(BaseModel):
    id: str
    ubicacion: str
    epigrafe: str
    texto: str
    score: float
    norma: Optional[str] = None
    vigencia: Optional[str] = None
    tema: Optional[str] = None
    fuente: Optional[str] = None
    archivo_fuente: Optional[str] = None
    pagina_inicio: Optional[int] = None
    pagina_fin: Optional[int] = None
    paginas: Optional[List[int]] = None
    ubicaciones_fuente: Optional[List[UbicacionFuente]] = None
    fuentes: Optional[List[str]] = None


class Cita(BaseModel):
    articulo: str
    numeral: Optional[str] = None
    paragrafo: Optional[str] = None
    texto: str
    norma: Optional[str] = None


class RespuestaUpload(BaseModel):
    id: str
    nombre_guardado: str
    paginas: int
    caracteres: int
    estado: str
    norma: Optional[str] = None
    fuente_url: Optional[str] = None
    mensaje: str


class PedidoReprocesar(BaseModel):
    id: str                            # id del PDF subido (lo devuelve POST /upload_pdf/)
    norma: Optional[str] = None        # si no se dio al subirlo: "Ley 769 de 2002"
    fuente_url: Optional[str] = None


class RespuestaQuery(BaseModel):
    respuesta: str
    articulos_citados: List[str]
    fragmentos: List[Fragmento]
    fuera_de_dominio: bool
    citas: Optional[List[Cita]] = None
    tema_detectado: Optional[str] = None


# ---------------------------------------------------------------- errores (todos en español)

@app.exception_handler(RequestValidationError)
async def error_de_validacion(request: Request, exc: RequestValidationError):
    mensajes = []
    for e in exc.errors():
        campo = ".".join(str(p) for p in e.get("loc", []) if p != "body")
        if e["type"] == "missing":
            mensajes.append(f"Falta el campo obligatorio '{campo}'.")
        elif e["type"] == "value_error" and e.get("ctx", {}).get("error"):
            mensajes.append(str(e["ctx"]["error"]))
        elif e["type"] in ("string_type", "list_type", "dict_type"):
            mensajes.append(f"El campo '{campo}' tiene un tipo de dato inválido.")
        elif e["type"] in ("json_invalid", "model_attributes_type"):
            mensajes.append("El cuerpo de la petición debe ser un JSON válido.")
        else:
            mensajes.append(f"El campo '{campo}' no es válido.")
    # No se devuelve el valor recibido (input) para no repetir texto del usuario.
    return JSONResponse(status_code=422, content={"error": " ".join(mensajes) or "Petición no válida."})


@app.exception_handler(Exception)
async def error_interno(request: Request, exc: Exception):
    log.error("error interno en %s: %s", request.url.path, type(exc).__name__)  # sin el mensaje: podría traer texto del usuario
    return JSONResponse(status_code=500, content={"error": "Ocurrió un error interno. Intenta de nuevo en unos minutos."})


# ---------------------------------------------------------------- endpoints

@app.get("/health")
def health(request: Request):
    estado = request.app.state.motor
    proveedor, principal, respaldo = configuracion()
    externo = respaldo_externo()
    idx = info_indice(ESTRATEGIA)
    return {
        "listo": estado["listo"],
        "error": estado["error"],
        "modelo_embeddings": MODELO,
        "estrategia_busqueda": ESTRATEGIA,
        "busqueda_modo": estado["modo_busqueda"],
        "rrf_k": rrf_k() if estado["modo_busqueda"] == "hibrido" else None,
        "busqueda_expansion": expansion.info(),
        "fragmentos_en_indice": idx["fragmentos"],
        "corpus": Path(idx["corpus"]).name if idx.get("corpus") else None,
        "normas": idx["normas"],                       # [{"norma": "Ley 1801 de 2016", "articulos": 249}, ...]
        "reprocesamiento": {"trabajo_activo": reprocesar.trabajo_activo()},
        "llm_proveedor": proveedor,
        "llm_principal": principal,
        "llm_respaldo": respaldo,
        # Respaldo entre empresas (Groq): solo nombre de proveedor y modelo, nunca la clave.
        "llm_orden": orden_proveedores(),  # LLM_ORDEN del .env (proveedores en el orden en que se prueban)
        "llm_respaldo_externo": {"proveedor": externo[0], "modelo": externo[1]} if externo else None,
        "tiempos_de_carga_s": estado["tiempos"],
    }


@app.post("/query", response_model=RespuestaQuery, response_model_exclude_none=False)
def query(q: Query, request: Request):
    # `def` (no `async`): el LLM es una llamada bloqueante; FastAPI la corre en un hilo.
    if not request.app.state.motor["listo"]:
        log.warning("/query rechazada: motor no listo")
        return JSONResponse(status_code=503, content={"error": MENSAJE_OCUPADO})

    t = time.perf_counter()
    try:
        r = responder(q.pregunta, k=3, incluir_diagnostico=True)
    except ErrorLLM as e:
        # El mensaje de ErrorLLM habla de modelos y tiempos, nunca del texto de la pregunta.
        log.warning("/query 503: LLM no disponible (%s)", e)
        return JSONResponse(status_code=503, content={"error": MENSAJE_OCUPADO})

    d = r.pop("diagnostico")
    # Solo estado, tiempos, modelo y conteos. Nunca la pregunta, la respuesta ni el historial.
    log.info(
        "/query 200 total=%.2fs busqueda=%.2fs llm=%.2fs modelo=%s respaldo=%s fuera_de_dominio=%s citas=%d",
        time.perf_counter() - t, d["tiempo_busqueda_s"], d["tiempo_llm_s"],
        d["modelo_usado"], d["uso_respaldo"], r["fuera_de_dominio"], len(r["citas"]),
    )
    return r


@app.post("/upload_pdf/", response_model=RespuestaUpload)
def upload_pdf(file: UploadFile = File(...), norma: Optional[str] = Form(None), fuente_url: Optional[str] = Form(None)):
    """Guarda un PDF y lo deja "pendiente_de_indexar". NO genera embeddings ni toca los índices (RF4).

    `norma` ("Ley 769 de 2002") y `fuente_url` son opcionales; se usan después en POST /corpus/reprocesar.
    """
    if norma is not None and norma.strip():
        try:
            norma = normas.normalizar(norma)
        except ValueError as e:
            return JSONResponse(status_code=422, content={"error": str(e)})
    else:
        norma = None
    if fuente_url is not None and fuente_url.strip():
        fuente_url = fuente_url.strip()
        if not fuente_url.lower().startswith(("http://", "https://")) or len(fuente_url) > 500:
            return JSONResponse(status_code=422, content={"error": "fuente_url debe ser una URL http(s) de máximo 500 caracteres."})
    else:
        fuente_url = None
    contenido = file.file.read(uploads.MAX_BYTES + 1)  # lee a lo sumo 10 MB + 1 byte
    if len(contenido) > uploads.MAX_BYTES:
        return JSONResponse(status_code=413, content={"error": "El archivo supera el máximo permitido de 10 MB."})
    try:
        d = uploads.guardar(contenido, file.filename, norma=norma, fuente_url=fuente_url)
    except uploads.PDFInvalido as e:
        return JSONResponse(status_code=422, content={"error": str(e)})

    # Sin nombre ni contenido del documento en el log (privacidad).
    log.info("/upload_pdf 200 bytes=%d paginas=%d caracteres=%d estado=%s",
             len(contenido), d["paginas"], d["caracteres"], d["estado"])
    if norma:
        mensaje = (f"Documento guardado como {norma}. Todavía NO está disponible en las consultas (no se "
                   f"regeneraron embeddings): para incorporarlo, un administrador debe lanzar "
                   f"POST /corpus/reprocesar con id «{d['id']}».")
    else:
        mensaje = ("Documento guardado. Todavía NO está disponible en las consultas: quedará disponible "
                   "cuando se reconstruya el índice manualmente "
                   "(python engine/indexing/build_index.py --estrategia fragmentos --incluir-uploads), "
                   "o con POST /corpus/reprocesar si se indica a qué norma corresponde. "
                   "No se regeneraron embeddings.")
    return {
        "id": d["id"],
        "nombre_guardado": d["nombre"],
        "paginas": d["paginas"],
        "caracteres": d["caracteres"],
        "estado": d["estado"],
        "norma": norma,
        "fuente_url": fuente_url,
        "mensaje": mensaje,
    }


# ---------------------------------------------------------------- corpus: reprocesamiento

def _token_valido(token: Optional[str]) -> Optional[JSONResponse]:
    """None si el token de administrador es correcto; si no, la respuesta de error."""
    esperado = os.getenv("ADMIN_TOKEN", "").strip()
    if not esperado:
        return JSONResponse(status_code=503, content={
            "error": "El reprocesamiento está deshabilitado: falta ADMIN_TOKEN en el .env del motor."})
    if not token or not hmac.compare_digest(token.strip().encode(), esperado.encode()):
        return JSONResponse(status_code=401, content={
            "error": "Falta el token de administrador o no es válido (cabecera X-Admin-Token)."})
    return None


@app.post("/corpus/reprocesar", status_code=202)
def corpus_reprocesar(p: PedidoReprocesar, x_admin_token: Optional[str] = Header(None)):
    """Incorpora un PDF subido como norma, EN SEGUNDO PLANO. Responde de inmediato (202) con trabajo_id."""
    error = _token_valido(x_admin_token)
    if error:
        log.warning("/corpus/reprocesar %d: token ausente o inválido", error.status_code)
        return error
    try:
        t = reprocesar.lanzar(p.id, p.norma, p.fuente_url)
    except KeyError:
        return JSONResponse(status_code=404, content={"error": "No existe un documento subido con ese id."})
    except reprocesar.TrabajoOcupado as e:
        return JSONResponse(status_code=409, content={
            "error": "Ya hay un reprocesamiento en curso; espera a que termine.", "trabajo_activo": str(e)})
    except ValueError as e:
        return JSONResponse(status_code=422, content={"error": str(e)})
    log.info("/corpus/reprocesar 202 trabajo=%s", t["trabajo_id"])  # sin el nombre del documento
    return {**t, "consultar": f"/corpus/reprocesar/{t['trabajo_id']}"}


@app.get("/corpus/reprocesar/{trabajo_id}")
def corpus_estado(trabajo_id: str):
    """Estado de un trabajo: en_cola, extrayendo, indexando, listo o error, con progreso (0-100)."""
    t = reprocesar.trabajo(trabajo_id)
    if t is None:
        return JSONResponse(status_code=404, content={"error": "No existe un trabajo con ese id (o el motor se reinició)."})
    return t


@app.get("/corpus/documentos")
def corpus_documentos():
    """Normas cargadas en el índice vigente y documentos subidos (sin su contenido)."""
    idx = info_indice(ESTRATEGIA)
    detalle = {normas.clave(d["norma"]): d for d in idx["normas_adicionales"]}
    lista = []
    for n in idx["normas"]:
        d = detalle.get(normas.clave(n["norma"]), {})
        lista.append({
            "norma": n["norma"],
            "titulo": normas.titulo(n["norma"]),
            "articulos": n["articulos"],
            "base": normas.es_base(n["norma"]),
            "archivo": d.get("archivo") or (Path(idx["corpus"]).name if normas.es_base(n["norma"]) else None),
            "fuente_url": d.get("fuente_url"),
            "fecha_carga": d.get("fecha_carga"),
            "vigencia_verificada": normas.es_base(n["norma"]),
        })
    documentos = [{k: d.get(k) for k in ("id", "nombre", "fecha", "paginas", "caracteres", "estado", "norma",
                                         "fuente_url", "articulos", "fecha_procesado")}
                  for d in uploads.leer_registro()]
    return {"normas": lista, "documentos": documentos}
