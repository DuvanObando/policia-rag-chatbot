"""Texto de un PDF, página por página: PyMuPDF si está instalado y pypdf como respaldo.

PyMuPDF es unas 50 a 100 veces más rápido que pypdf con PDF largos (la Ley 769 de 2002, 56
páginas, pasó de ~52 s a menos de 1 s; ver docs/reprocesamiento.md). Si no está instalado
(`pip install pymupdf`, ya declarado en engine/requirements.txt) o no puede abrir el archivo,
se usa pypdf, que es más lento pero tolera más PDF dañados.

Lo usan la subida (engine/indexing/uploads.py) y el pipeline (corpus/pipeline/procesar_pdf.py).
"""
from io import BytesIO
from typing import List

try:  # el nombre actual del paquete es "pymupdf"; "fitz" es el antiguo
    import pymupdf as _pymupdf
except ImportError:
    try:
        import fitz as _pymupdf
    except ImportError:
        _pymupdf = None


class PDFNoLegible(ValueError):
    """El PDF no se pudo leer; el mensaje está en español y se puede mostrar al usuario."""


class _ConContrasena(Exception):
    pass


def motor() -> str:
    """Qué librería se usaría ahora: 'pymupdf' o 'pypdf'."""
    return "pymupdf" if _pymupdf is not None else "pypdf"


def _con_pymupdf(contenido: bytes) -> List[str]:
    doc = _pymupdf.open(stream=contenido, filetype="pdf")
    try:
        if doc.needs_pass and not doc.authenticate(""):
            raise _ConContrasena()
        return [pagina.get_text("text") or "" for pagina in doc]
    finally:
        doc.close()


def _con_pypdf(contenido: bytes) -> List[str]:
    from pypdf import PdfReader

    lector = PdfReader(BytesIO(contenido))
    if lector.is_encrypted and not lector.decrypt(""):
        raise _ConContrasena()
    return [(p.extract_text() or "") for p in lector.pages]


def paginas(contenido: bytes) -> List[str]:
    """Texto de cada página. Lanza PDFNoLegible (ValueError) si está dañado o protegido con contraseña."""
    metodos = ([_con_pymupdf] if _pymupdf is not None else []) + [_con_pypdf]
    for i, metodo in enumerate(metodos):
        try:
            return metodo(contenido)
        except _ConContrasena:
            raise PDFNoLegible("El PDF está protegido con contraseña y no se puede leer.") from None
        except Exception as e:
            if i == len(metodos) - 1:
                raise PDFNoLegible(f"No se pudo leer el PDF ({type(e).__name__}).") from e
            # PyMuPDF no pudo con el archivo: se intenta con pypdf
    raise PDFNoLegible("No se pudo leer el PDF.")  # no se llega aquí
