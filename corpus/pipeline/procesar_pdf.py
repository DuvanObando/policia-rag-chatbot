"""Convierte el PDF de una norma en registros del corpus (interfaz del pipeline de la Fase 1).

    procesar_pdf(ruta_pdf, norma, fuente_url=None) -> list[dict]

La usa el motor al reprocesar el corpus (engine/indexing/reprocesar.py, POST /corpus/reprocesar).

=====================================================================================================
PARA WILDER: esta es una versión BÁSICA para que el flujo funcione hoy. Reemplaza el INTERIOR de
procesar_pdf() con tu limpieza y segmentación reales (encabezados y pies de página, notas
editoriales, libro / título / capítulo, numerales, vigencia verificada...), SIN CAMBIAR:
  1. la firma: procesar_pdf(ruta_pdf, norma, fuente_url=None) -> list[dict]
  2. el formato de salida: una lista de registros (uno por artículo) con estas claves:

     clave       tipo          ejemplo / regla
     ----------  ------------  -------------------------------------------------------------------
     id          str           "ley769-art-131": usa id_articulo(norma, numero) de engine/indexing/normas.py
                               (la Ley 1801 no lleva prefijo: "art-140"). Único dentro de la norma.
     norma       str           "Ley 769 de 2002" (tal cual llega en el parámetro `norma`)
     ubicacion   dict          {"libro": str|None, "titulo": str|None, "capitulo": str|None,
                                "articulo": "Artículo 131"}
     epigrafe    str           "Multas" (título del artículo; si no tiene, "Artículo 131")
     texto       str           texto del artículo, sin encabezados ni pies de página
     vigencia    str           "no_verificada" mientras nadie la revise (o tus valores verificados:
                               "vigente", "vigente_modificado", "inexequible", ...)
     tema        str           tema del artículo (si no lo sabes: "texto fuente Ley 769 de 2002")
     pdf         str           nombre del archivo PDF de origen
     pagina      int           página (desde 1) donde empieza el artículo
     fuente_url  str|None      URL oficial de donde se descargó (si se conoce)

  Campos extra se permiten (se conservan), pero esas 10 deben estar siempre.
  Debe lanzar ValueError con un mensaje claro si el PDF no sirve (escaneado, vacío, sin artículos).

Prueba rápida, desde la raíz del repo:
    engine\\.venv\\Scripts\\python corpus/pipeline/procesar_pdf.py ruta.pdf "Ley 769 de 2002" [--salida x.json]
=====================================================================================================

Qué hace esta versión básica:
  - extrae el texto página por página con PyMuPDF (o pypdf si no está instalado);
  - quita las líneas que se repiten en más de la mitad de las páginas (encabezados y pies);
  - parte por líneas que empiezan con «ARTÍCULO N» (acepta 1o., 2°, 131A...), sin confundir
    menciones en minúscula dentro del texto con encabezados;
  - toma como epígrafe lo que sigue a «ARTÍCULO N.» hasta el primer punto, si es corto;
  - lleva la cuenta de LIBRO / TÍTULO / CAPÍTULO cuando aparecen como encabezados;
  - marca todo con vigencia "no_verificada" (nadie la ha revisado).
"""
import argparse
import json
import re
import sys
from collections import Counter
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(RAIZ / "engine"))
from indexing import pdf_texto  # noqa: E402
from indexing.normas import id_articulo  # noqa: E402

_ARTICULO_MARCA = re.compile(
    r"\bART[ÍI]CULO\s*(\d{1,4})"
    r"(?:\s*(?:[oOº°]|([A-Z])(?=\s*[.\-:–—])))?"
    r"\s*[.\-:–—]?",
    re.IGNORECASE,
)
_ARTICULO_LINEA = re.compile(
    r"^\s*ART[ÍI]CULO\s*(\d{1,4})"
    r"(?:\s*(?:[oOº°]|([A-Z])(?=\s*[.\-:–—])))?"
    r"\s*[.\-:–—]?\s*(.*)$",
    re.IGNORECASE,
)
_LIBRO = re.compile(r"^\s*LIBRO\s+([A-ZÁÉÍÓÚ]+|[IVXLC]+|\d+)\b\.?\s*(.*)$")
_TITULO = re.compile(r"^\s*T[ÍI]TULO\s+([IVXLC]+|\d+|[ÚU]NICO|PRELIMINAR)\b\.?\s*(.*)$")
_CAPITULO = re.compile(r"^\s*CAP[ÍI]TULO\s+([IVXLC]+|\d+|[ÚU]NICO)\b\.?\s*(.*)$")
_SUBSECCION_131 = re.compile(
    r"(?<=\S)[ \t]+(?=(?:[A-F]\.\s+|[A-F]\.\d{1,2}\.\s+)[A-ZÁÉÍÓÚÜÑ])"
)


def _paginas(ruta_pdf: Path):
    datos = ruta_pdf.read_bytes()
    # Algunos PDF oficiales traen bytes antes de "%PDF-" (p. ej. la Función Pública): se descartan,
    # porque corren las posiciones internas del archivo.
    inicio = datos.find(b"%PDF-", 0, 1024)
    # PyMuPDF si está instalado (rápido) y pypdf como respaldo (ver engine/indexing/pdf_texto.py).
    # pdf_texto.PDFNoLegible es un ValueError con un mensaje en español.
    return pdf_texto.paginas(datos[inicio:] if inicio > 0 else datos)


def _sin_repetidas(paginas):
    """Quita las líneas que aparecen en más de la mitad de las páginas (encabezados y pies)."""
    if len(paginas) < 4:
        return [p.splitlines() for p in paginas]
    cuenta = Counter(l.strip() for p in paginas for l in set(p.splitlines()) if l.strip())
    repetidas = {l for l, n in cuenta.items() if n > len(paginas) / 2}
    return [[l for l in p.splitlines() if l.strip() not in repetidas] for p in paginas]


def _epigrafe(resto: str, numero: str) -> str:
    """'MULTAS. Los infractores...' -> 'Multas'. Si no hay un título corto, 'Artículo N'."""
    resto = re.sub(r"<[^>]*>", "", resto).strip()
    m = re.match(r"([^.<]{3,120})\.", resto)
    if m:
        t = m.group(1).strip()
        return t[:1].upper() + t[1:].lower() if t.isupper() else t
    return f"Artículo {numero}"


def _numero_natural(numero: str, sufijo: str) -> tuple:
    """Clave estable para comparar artículos con ordinal o literal."""
    return int(numero), (sufijo or "").upper()


def _es_encabezado_articulo(texto: str, coincidencia) -> bool:
    """Acepta encabezados en una línea o separados por texto, sin tomar referencias minúsculas."""
    inicio = coincidencia.start()
    if inicio and texto[inicio - 1] not in "\r\n\t ":
        return False
    linea_inicio = texto.rfind("\n", 0, inicio) + 1
    prefijo = texto[linea_inicio:inicio].strip()
    if prefijo:
        return False
    resto = texto[coincidencia.end():coincidencia.end() + 160].lstrip(" \t.-:–—")
    if not resto:
        return False
    return resto[0].isupper() or resto[0].isdigit()


def _texto_completo(lineas_por_pagina):
    partes = []
    rangos = []
    cursor = 0
    for pagina, lineas in enumerate(lineas_por_pagina, start=1):
        texto = "\n".join(linea.strip() for linea in lineas if linea.strip())
        if texto:
            inicio = cursor
            fin = inicio + len(texto)
            rangos.append((inicio, fin, pagina))
            partes.append(texto)
            cursor = fin + 2
    return "\n\n".join(partes), rangos


def _pagina_offset(rangos, offset):
    for inicio, fin, pagina in rangos:
        if inicio <= offset < fin:
            return pagina
    return rangos[-1][2] if rangos else 1


def _ubicacion_en_offset(texto: str, offset: int) -> dict:
    ubicacion = {"libro": None, "titulo": None, "capitulo": None}
    prefijo = texto[:offset]
    for linea in prefijo.splitlines():
        limpia = linea.strip()
        if not limpia:
            continue
        for patron, campo in ((_LIBRO, "libro"), (_TITULO, "titulo"), (_CAPITULO, "capitulo")):
            coincidencia = patron.match(limpia)
            if coincidencia and limpia.isupper():
                ubicacion[campo] = limpia.title()
                if campo == "libro":
                    ubicacion.update(titulo=None, capitulo=None)
                elif campo == "titulo":
                    ubicacion["capitulo"] = None
    return ubicacion


def _separar_subsecciones_131(texto: str) -> str:
    """Conserva el artículo 131 como un registro y separa sus literales/numerales en líneas."""
    return _SUBSECCION_131.sub("\n", texto)


def procesar_pdf(ruta_pdf, norma, fuente_url=None) -> list:
    """Registros del corpus (uno por artículo) a partir del PDF de una norma. Ver el docstring del módulo."""
    ruta_pdf = Path(ruta_pdf)
    lineas_por_pagina = _sin_repetidas(_paginas(ruta_pdf))
    if not any(l.strip() for p in lineas_por_pagina for l in p):
        raise ValueError("El PDF no tiene texto que se pueda extraer (¿es un documento escaneado?).")

    texto, rangos = _texto_completo(lineas_por_pagina)
    encabezados = []
    for coincidencia in _ARTICULO_MARCA.finditer(texto):
        if not _es_encabezado_articulo(texto, coincidencia):
            continue
        sufijo = coincidencia.group(2) or ""
        numero = coincidencia.group(1) + sufijo.upper()
        clave = _numero_natural(coincidencia.group(1), sufijo)
        encabezados.append((coincidencia, clave, numero))

    # Conserva el orden real y elimina duplicados del mismo encabezado.
    encabezados_unicos = []
    ultimo_encabezado = None
    for encabezado in encabezados:
        coincidencia, clave, numero = encabezado
        if ultimo_encabezado is not None and coincidencia.start() == ultimo_encabezado:
            continue
        encabezados_unicos.append(encabezado)
        ultimo_encabezado = coincidencia.start()

    registros = []
    ultimo_clave = (0, "")
    for indice, (coincidencia, clave, numero) in enumerate(encabezados_unicos):
        if clave <= ultimo_clave:
            continue
        ultimo_clave = clave
        inicio = coincidencia.start()
        fin = encabezados_unicos[indice + 1][0].start() if indice + 1 < len(encabezados_unicos) else len(texto)
        linea_encabezado_fin = texto.find("\n", coincidencia.end())
        if linea_encabezado_fin >= 0 and linea_encabezado_fin < fin:
            resto_offset = linea_encabezado_fin + 1
        else:
            resto_offset = coincidencia.end()
        resto = texto[resto_offset:fin].strip()
        encabezado_linea = texto[inicio: texto.find("\n", inicio) if texto.find("\n", inicio) >= 0 else fin].strip()
        cuerpo = "\n".join(parte for parte in (encabezado_linea, resto) if parte).strip()
        if r"\n" in cuerpo:
            cuerpo = cuerpo.replace(r"\n", "\n")
        texto_cuerpo = cuerpo
        if numero.upper().startswith("131"):
            texto_cuerpo = _separar_subsecciones_131(texto_cuerpo)
        coincidencia_linea = _ARTICULO_LINEA.match(encabezado_linea)
        resto_epigrafe = coincidencia_linea.group(3) if coincidencia_linea else ""
        registro = {
            "id": id_articulo(norma, numero),
            "norma": norma,
            "ubicacion": {**_ubicacion_en_offset(texto, inicio), "articulo": f"Artículo {numero}"},
            "epigrafe": _epigrafe(resto_epigrafe, numero),
            "texto": texto_cuerpo,
            "vigencia": "no_verificada",
            "tema": f"texto fuente {norma}",
            "pdf": ruta_pdf.name,
            "pagina": _pagina_offset(rangos, inicio),
            "fuente_url": fuente_url,
        }
        registros.append(registro)
    if not registros:
        raise ValueError("No se encontró ningún «ARTÍCULO N» en el PDF.")
    return registros


def main():
    ap = argparse.ArgumentParser(description="Prueba procesar_pdf() con un PDF")
    ap.add_argument("pdf")
    ap.add_argument("norma", help='p. ej. "Ley 769 de 2002"')
    ap.add_argument("--url", default=None, help="URL oficial de la fuente")
    ap.add_argument("--salida", default=None, help="guarda los registros en este JSON")
    args = ap.parse_args()
    registros = procesar_pdf(args.pdf, args.norma, args.url)
    print(f"{len(registros)} artículos | primero: {registros[0]['id']} ({registros[0]['epigrafe']}) | "
          f"último: {registros[-1]['id']} ({registros[-1]['epigrafe']})")
    if args.salida:
        Path(args.salida).write_text(json.dumps(registros, ensure_ascii=False, indent=1), encoding="utf-8")
        print(f"Guardado en {args.salida}")


if __name__ == "__main__":
    main()
