"""Carga el corpus y lo adapta al esquema que usa el motor, SIN modificar el archivo del corpus.

El motor necesita, por artículo: id `art-N`, `ubicacion` como objeto
{libro, titulo, capitulo, articulo}, `epigrafe`, `texto`, `vigencia` y `tema`.

Acepta dos formatos:
  1. Corpus de muestra (corpus/muestra/codigo_muestra.json): ya viene en ese esquema; se
     devuelve tal cual.
  2. Corpus de la Fase 1 (corpus/procesados/corpus_ley_1801.json, de Wilder). Diferencias que
     se adaptan aquí, al cargar:
       - `ubicacion` viene como TEXTO ("Ley 1801 de 2016, artículo 140 (versión del PDF...)").
         Se convierte en objeto; el texto original queda en `ubicacion_texto`. El libro y el
         capítulo se reconstruyen con los encabezados que el PDF dejó al final del artículo
         anterior (ver abajo). El título no se puede reconstruir: el PDF no trae la línea
         «TÍTULO N», solo su nombre (queda en `titulo_nombre`).
       - Encabezados pegados al final del texto: 42 artículos terminan con los encabezados de
         la sección siguiente ("CAPÍTULO I / CIRCULACIÓN Y DERECHO DE VÍA"). Se quitan del
         texto (no son de ese artículo) y se usan para ubicar los artículos que siguen.
       - Líneas "*jurisprudencia*" (marcador editorial vacío): se quitan.
       - ids con sufijo en minúscula (`art-185a`) -> `art-185A`, como los escribe la ley y las
         citas del modelo.
       - Registros de normas que modifican, corrigen o adicionan la ley (41, `tipo_disposicion`
         distinto de `texto_fuente_ley_base`): por defecto NO se indexan. Su efecto ya está
         integrado en el texto del artículo de la ley (vigencia `efecto_integrado`) y el motor
         todavía no sabe citar artículos de otras normas. Se incluyen con
         CORPUS_INCLUIR_REFORMAS=1.
       - Campos extra (fuente, páginas, norma...) se conservan.
       - `vigencia` se conserva tal cual (más valores que el contrato original; ver
         docs/api_contract.md).
"""
import json
import os
import re
from pathlib import Path
from typing import List

ULTIMA_CARGA: dict = {}  # resumen de la última carga (para mostrarlo en build_index)

_ENCABEZADO = re.compile(r"\s*(LIBRO|T[ÍI]TULO|CAP[ÍI]TULO)\b", re.IGNORECASE)
_ORDINAL = {"PRIMERO": "Primero", "SEGUNDO": "Segundo", "TERCERO": "Tercero", "CUARTO": "Cuarto", "QUINTO": "Quinto"}


def incluir_reformas() -> bool:
    return os.getenv("CORPUS_INCLUIR_REFORMAS", "0").strip().lower() in ("1", "true", "si", "sí", "yes")


def _bloque_final(texto: str):
    """(texto sin el bloque final de encabezados, líneas del bloque). Bloque vacío si no hay."""
    lineas = texto.rstrip().split("\n")
    i = len(lineas)
    while (i > 0 and lineas[i - 1].strip() and not re.search(r"[a-záéíóúñü]", lineas[i - 1])
           and not re.match(r"\s*(\d|PAR[ÁA]GRAFO|ART[ÍI]CULO|\()", lineas[i - 1])):
        i -= 1
    bloque = [l.strip() for l in lineas[i:]]
    if not any(_ENCABEZADO.match(l) for l in bloque):
        return texto, []
    return "\n".join(lineas[:i]).rstrip(), bloque


def _nombre(texto: str) -> str:
    t = texto.strip().rstrip(".")
    return t[:1].upper() + t[1:].lower() if t else t


def _actualizar_estado(estado: dict, bloque: List[str]) -> None:
    """Aplica los encabezados del bloque (LIBRO / CAPÍTULO / nombre de título) al estado."""
    i = 0
    while i < len(bloque):
        linea = bloque[i]
        siguiente = bloque[i + 1] if i + 1 < len(bloque) and not _ENCABEZADO.match(bloque[i + 1]) else None
        m = re.match(r"(?i)\s*LIBRO\s+(\w+)", linea)
        if m:
            num = _ORDINAL.get(m.group(1).upper(), m.group(1).capitalize())
            estado.update(libro=f"Libro {num}" + (f". {_nombre(siguiente)}" if siguiente else ""),
                          titulo=None, titulo_nombre=None, capitulo=None)
            i += 2 if siguiente else 1
            continue
        m = re.match(r"(?i)\s*CAP[ÍI]TULO\s+(.+)", linea)
        if m:
            estado["capitulo"] = f"Capítulo {m.group(1).strip().upper().replace('ÚNICO', 'Único')}" + (
                f". {_nombre(siguiente)}" if siguiente else "")
            i += 2 if siguiente else 1
            continue
        m = re.match(r"(?i)\s*T[ÍI]TULO\s+(\w+)", linea)
        if m:
            estado.update(titulo=f"Título {m.group(1).upper()}" + (f". {_nombre(siguiente)}" if siguiente else ""),
                          capitulo=None)
            i += 2 if siguiente else 1
            continue
        # Línea con solo el nombre de un título (el PDF no trae «TÍTULO N»).
        estado.update(titulo_nombre=_nombre(linea), titulo=None, capitulo=None)
        i += 1


def _clave_articulo(numero: str):
    m = re.match(r"(\d+)([A-Za-z]?)", str(numero))
    return (int(m.group(1)), m.group(2).upper()) if m else (10 ** 6, str(numero))


def _es_formato_fase1(registros: List[dict]) -> bool:
    return any(isinstance(r.get("ubicacion"), str) for r in registros)


def adaptar(registros: List[dict]) -> List[dict]:
    """Adapta registros del formato de la Fase 1 al esquema del motor (ver docstring del módulo)."""
    resumen = {"registros_en_archivo": len(registros), "formato": "fase1", "reformas_excluidas": 0,
               "encabezados_quitados": 0, "marcas_jurisprudencia_quitadas": 0, "ids_normalizados": 0}
    base, reformas = [], []
    for r in registros:
        (base if r.get("tipo_disposicion", "texto_fuente_ley_base") == "texto_fuente_ley_base" else reformas).append(r)
    base.sort(key=lambda r: _clave_articulo(r.get("articulo_fuente") or r["id"].replace("art-", "")))

    estado = {"libro": "Libro Primero", "titulo": None, "titulo_nombre": None, "capitulo": None}
    salida = []
    for r in base:
        a = dict(r)
        texto, marcas = re.subn(r"(?m)^\s*\*jurisprudencia\*\s*\n?", "", a["texto"])
        resumen["marcas_jurisprudencia_quitadas"] += marcas
        texto, bloque = _bloque_final(texto)
        nuevo_id = re.sub(r"^(art-\d+)([a-z])$", lambda m: m.group(1) + m.group(2).upper(), a["id"])
        resumen["ids_normalizados"] += nuevo_id != a["id"]
        numero = nuevo_id.replace("art-", "")
        a.update(
            id=nuevo_id,
            texto=texto.strip(),
            ubicacion_texto=r["ubicacion"],
            ubicacion={"libro": estado["libro"], "titulo": estado["titulo"],
                       "capitulo": estado["capitulo"], "articulo": f"Artículo {numero}"},
            titulo_nombre=estado["titulo_nombre"],
        )
        salida.append(a)
        if bloque:  # los encabezados del final ubican a los artículos que siguen
            resumen["encabezados_quitados"] += 1
            _actualizar_estado(estado, bloque)

    if incluir_reformas():
        for r in reformas:
            a = dict(r)
            a.update(ubicacion_texto=r["ubicacion"],
                     ubicacion={"libro": None, "titulo": None, "capitulo": None, "articulo": r["ubicacion"]})
            salida.append(a)
    else:
        resumen["reformas_excluidas"] = len(reformas)
    resumen["registros_cargados"] = len(salida)
    ULTIMA_CARGA.clear()
    ULTIMA_CARGA.update(resumen)
    return salida


def cargar(ruta) -> List[dict]:
    """Lee el corpus de `ruta` y lo devuelve en el esquema del motor."""
    registros = json.loads(Path(ruta).read_text(encoding="utf-8"))
    if _es_formato_fase1(registros):
        return adaptar(registros)
    ULTIMA_CARGA.clear()
    ULTIMA_CARGA.update(registros_en_archivo=len(registros), formato="muestra", registros_cargados=len(registros))
    return registros
