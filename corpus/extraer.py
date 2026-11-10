"""Extrae el texto por página de los PDF guardados en corpus/documentos/."""
import argparse
import hashlib
import json
import re
from pathlib import Path

import pymupdf

if __package__:
    from .limpiar import clean_page_text
else:
    from limpiar import clean_page_text


RAIZ_CORPUS = Path(__file__).resolve().parent
CARPETA_DOCUMENTOS = RAIZ_CORPUS / "documentos"
CARPETA_EXTRAIDOS = RAIZ_CORPUS / "procesados" / "texto_extraido"
PATRON_ARCHIVO = re.compile(
    r"^(?P<clase>Mod|Adi)?_?(?P<tipo>Ley|Decreto)_(?P<numero>\d+)_de_(?P<anio>\d{4})$",
    re.IGNORECASE,
)


def _metadatos_documento(pdf_path):
    match = PATRON_ARCHIVO.match(pdf_path.stem)
    if not match:
        raise ValueError(
            f"Nombre de PDF no reconocido: {pdf_path.name}. "
            "Usa, por ejemplo, Ley_1801_de_2016.pdf o Mod_Ley_2000_de_2019.pdf."
        )

    tipo = match.group("tipo").lower()
    clase = (match.group("clase") or "Base").lower()
    prefijos = {"mod": "modificatoria", "adi": "adicionatoria", "base": "base"}
    return {
        "id": f"{tipo}-{match.group('numero')}-{match.group('anio')}-{clase}",
        "tipo_norma": tipo,
        "numero": int(match.group("numero")),
        "anio": int(match.group("anio")),
        "clase_documento": prefijos[clase],
        "titulo": f"{match.group('tipo')} {match.group('numero')} de {match.group('anio')}",
        "archivo": pdf_path.name,
    }


def extract_pdf(pdf_path):
    """Devuelve el texto extraído por página, manteniendo la API previa."""
    pdf_path = Path(pdf_path)
    metadata = _metadatos_documento(pdf_path)
    document = pymupdf.open(pdf_path)
    try:
        pages = [
            {
                "page": page_number,
                "content": clean_page_text(
                    page.get_text("text"),
                    document_title=metadata["titulo"],
                    page_number=page_number,
                ),
            }
            for page_number, page in enumerate(document, start=1)
        ]
    finally:
        document.close()

    if not any(page["content"] for page in pages):
        raise ValueError(
            f"No se pudo extraer texto de {pdf_path}. "
            "El PDF podría ser escaneado y requerir OCR."
        )
    return pages


def extract_document(pdf_path):
    pdf_path = Path(pdf_path)
    metadata = _metadatos_documento(pdf_path)
    digest = hashlib.sha256(pdf_path.read_bytes()).hexdigest()
    return {
        "documento": {**metadata, "sha256": digest},
        "paginas": extract_pdf(pdf_path),
    }


def extract_all(input_dir=CARPETA_DOCUMENTOS, output_dir=CARPETA_EXTRAIDOS):
    input_dir = Path(input_dir)
    output_dir = Path(output_dir)
    pdf_paths = sorted(input_dir.rglob("*.pdf"))
    if not pdf_paths:
        raise FileNotFoundError(f"No se encontraron archivos PDF en {input_dir}")

    for pdf_path in pdf_paths:
        document = extract_document(pdf_path)
        category = "decretos" if document["documento"]["tipo_norma"] == "decreto" else "leyes"
        destination = output_dir / category / f"{pdf_path.stem}.json"
        destination.parent.mkdir(parents=True, exist_ok=True)
        destination.write_text(
            json.dumps(document, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
        print(f"{pdf_path.name}: {len(document['paginas'])} páginas -> {destination}")
    return len(pdf_paths)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input-dir", type=Path, default=CARPETA_DOCUMENTOS)
    parser.add_argument("--output-dir", type=Path, default=CARPETA_EXTRAIDOS)
    args = parser.parse_args()
    extract_all(args.input_dir, args.output_dir)


if __name__ == "__main__":
    main()
