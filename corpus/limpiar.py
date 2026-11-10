import re
import unicodedata


ENCABEZADOS_REPETIDOS = {
    "Departamento Administrativo de la Función Pública",
    "EVA - Gestor Normativo",
    "Los datos publicados tienen propósitos exclusivamente informativos. El Departamento Administrativo de la Función Pública no se hace",
    "responsable de la vigencia de la presente norma. Nos encontramos en un proceso permanente de actualización de los contenidos.",
}


def clean_text(text):
    text = unicodedata.normalize("NFKC", text)
    text = text.replace("\r\n", "\n").replace("\r", "\n").replace("\x00", "")
    text = re.sub(r"(?<=\w)-\n(?=[a-záéíóúüñ])", "", text)
    text = re.sub(r"[ \t]+\n", "\n", text)
    text = re.sub(r"\n[ \t]+", "\n", text)
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()


def clean_page_text(text, document_title="", page_number=None):
    lines = clean_text(text).splitlines()
    cleaned = []
    for line in lines:
        normalized = line.strip()
        if not normalized or normalized in ENCABEZADOS_REPETIDOS:
            continue
        if document_title and normalized.casefold() == document_title.casefold():
            continue
        if page_number is not None and normalized == str(page_number):
            continue
        cleaned.append(normalized)
    return clean_text("\n".join(cleaned))
