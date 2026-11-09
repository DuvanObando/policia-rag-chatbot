"""Documentos PDF subidos por la API (POST /upload_pdf/).

Flujo de dos pasos (RF4): la API solo GUARDA el documento y lo registra como
"pendiente_de_indexar". NO genera embeddings ni toca los índices. El documento entra
al buscador cuando alguien reconstruye el índice a mano:
    python engine/indexing/build_index.py --estrategia fragmentos --incluir-uploads

Archivos (carpeta corpus/uploads/, ignorada por git):
    <nombre>_<fecha-hora>.pdf     el PDF original
    <nombre>_<fecha-hora>.txt     el texto extraído
    pendientes.json               registro: id, nombre, texto, fecha, paginas, caracteres, estado

PRIVACIDAD: no registres en logs el nombre ni el contenido de los documentos.
"""
import json
import os
import re
import threading
import unicodedata
from datetime import datetime
from io import BytesIO
from pathlib import Path
from typing import List

RAIZ = Path(__file__).resolve().parents[2]
CARPETA_UPLOADS = RAIZ / "corpus" / "uploads"
REGISTRO = CARPETA_UPLOADS / "pendientes.json"

MAX_BYTES = 10 * 1024 * 1024  # 10 MB
ESTADO_PENDIENTE = "pendiente_de_indexar"
ESTADO_INDEXADO = "indexado"

_candado = threading.Lock()  # protege el registro cuando llegan varias subidas a la vez


class PDFInvalido(Exception):
    """El archivo no sirve; el mensaje está en español y se puede mostrar al usuario."""


# ---------------------------------------------------------------- nombre y validación

def limpiar_nombre(nombre: str) -> str:
    """Nombre seguro (sin extensión): sin rutas, sin '../', solo letras, números, '_' y '-'."""
    base = re.split(r"[\\/]", nombre or "")[-1]                       # quita carpetas: ../, ..\, C:\...
    base = unicodedata.normalize("NFKD", base).encode("ascii", "ignore").decode()  # quita tildes
    if base.lower().endswith(".pdf"):
        base = base[:-4]
    base = re.sub(r"[^A-Za-z0-9_-]+", "_", base).strip("_-")[:80]
    return base or "documento"


def extraer_texto(contenido: bytes):
    """(páginas, texto) del PDF. Lanza PDFInvalido si está dañado, protegido o sin texto."""
    from pypdf import PdfReader

    try:
        lector = PdfReader(BytesIO(contenido))
        if lector.is_encrypted and not lector.decrypt(""):
            raise PDFInvalido("El PDF está protegido con contraseña y no se puede leer.")
        paginas = [(p.extract_text() or "").strip() for p in lector.pages]
    except PDFInvalido:
        raise
    except Exception:  # pypdf lanza muchos tipos de error con archivos dañados
        raise PDFInvalido("No se pudo leer el PDF: el archivo está dañado o no es un PDF válido.")
    texto = "\n\n".join(p for p in paginas if p)
    if not texto.strip():
        raise PDFInvalido("El PDF no contiene texto que se pueda extraer (¿es un documento escaneado?).")
    return len(paginas), texto


# ---------------------------------------------------------------- registro

def leer_registro() -> List[dict]:
    if not REGISTRO.exists():
        return []
    return json.loads(REGISTRO.read_text(encoding="utf-8"))


def _escribir_registro(registro: List[dict]) -> None:
    temporal = REGISTRO.with_suffix(".tmp")
    temporal.write_text(json.dumps(registro, ensure_ascii=False, indent=2), encoding="utf-8")
    os.replace(temporal, REGISTRO)  # escritura atómica


def guardar(contenido: bytes, nombre_original: str) -> dict:
    """Valida, guarda PDF y texto, y registra el documento como pendiente de indexar.

    No escribe nada en disco si el PDF no es válido. Devuelve la entrada del registro.
    """
    if not contenido.startswith(b"%PDF"):
        raise PDFInvalido("El archivo no es un PDF válido (no empieza con la cabecera %PDF).")
    paginas, texto = extraer_texto(contenido)

    CARPETA_UPLOADS.mkdir(parents=True, exist_ok=True)
    ahora = datetime.now()
    base = f"{limpiar_nombre(nombre_original)}_{ahora:%Y%m%d-%H%M%S}"

    with _candado:
        # Nombre único: si ya existe (mismo nombre y mismo segundo), se agrega un contador.
        id_doc, n = base, 1
        while (CARPETA_UPLOADS / f"{id_doc}.pdf").exists():
            n += 1
            id_doc = f"{base}-{n}"
        ruta_pdf = (CARPETA_UPLOADS / f"{id_doc}.pdf").resolve()
        ruta_txt = (CARPETA_UPLOADS / f"{id_doc}.txt").resolve()
        if ruta_pdf.parent != CARPETA_UPLOADS.resolve():  # defensa extra contra rutas maliciosas
            raise PDFInvalido("Nombre de archivo no válido.")
        ruta_pdf.write_bytes(contenido)
        ruta_txt.write_text(texto, encoding="utf-8")

        entrada = {
            "id": id_doc,
            "nombre": ruta_pdf.name,
            "texto": ruta_txt.name,
            "fecha": ahora.isoformat(timespec="seconds"),
            "paginas": paginas,
            "caracteres": len(texto),
            "estado": ESTADO_PENDIENTE,
        }
        registro = leer_registro()
        registro.append(entrada)
        _escribir_registro(registro)
    return entrada


def documentos_para_indexar() -> List[dict]:
    """Documentos que deben entrar al índice: los pendientes y los ya indexados.

    Los ya indexados se incluyen para que reconstruir el índice con --incluir-uploads
    no los pierda.
    """
    return [d for d in leer_registro()
            if d["estado"] in (ESTADO_PENDIENTE, ESTADO_INDEXADO) and (CARPETA_UPLOADS / d["texto"]).exists()]


def marcar_indexados(ids: List[str]) -> int:
    """Pasa a 'indexado' los pendientes cuyo id está en `ids`. Devuelve cuántos cambió."""
    cambiados = 0
    with _candado:
        registro = leer_registro()
        for d in registro:
            if d["id"] in ids and d["estado"] == ESTADO_PENDIENTE:
                d["estado"] = ESTADO_INDEXADO
                d["fecha_indexado"] = datetime.now().isoformat(timespec="seconds")
                cambiados += 1
        if cambiados:
            _escribir_registro(registro)
    return cambiados
