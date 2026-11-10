"""Segmenta normas extraídas y genera registros RAG con su fuente normativa."""
import argparse
import json
import re
import unicodedata
from pathlib import Path


RAIZ_CORPUS = Path(__file__).resolve().parent
CARPETA_EXTRAIDOS = RAIZ_CORPUS / "procesados" / "texto_extraido"
SALIDA_POR_DEFECTO = RAIZ_CORPUS / "procesados" / "corpus_ley_1801.json"
PATRON_ARTICULO = re.compile(
    r"(?m)^[ \t]*[A\u00c0\u00c1]RT(?:I|\u00cd)CULO[ \t]+"
    r"(?P<numero>\d+[A-Z]?)(?:[ \t]*(?P<ordinal>[°ºo]))?[ \t]*\.?[ \t]*"
    r"(?P<resto>[^\n]*)"
)
PATRON_REFERENCIA = re.compile(
    r"\b(?:modif\w*|adici\w*|corr\w*|derog\w*)\b.{0,220}?"
    r"\bart(?:i|\u00ed)culos?\s+"
    r"(?P<articulos>\d+[A-Z]?(?:\s*(?:,|y|e|a|al)\s*\d+[A-Z]?)*)"
    r".{0,120}?\bley\s+1801\b",
    re.IGNORECASE,
)


def _texto_y_paginas(documento):
    partes = []
    rangos_paginas = []
    cursor = 0
    for pagina in documento["paginas"]:
        contenido = pagina["content"]
        inicio = cursor
        fin = inicio + len(contenido)
        if contenido:
            rangos_paginas.append((inicio, fin, pagina["page"]))
        partes.append(contenido)
        cursor = fin + 2
    return "\n\n".join(partes), rangos_paginas


def _ubicacion_paginas(rangos_paginas, inicio, fin):
    paginas = [
        numero
        for inicio_pagina, fin_pagina, numero in rangos_paginas
        if inicio_pagina < fin and fin_pagina > inicio
    ]
    if not paginas:
        raise ValueError(
            f"No se pudo determinar la página del texto entre offsets {inicio} y {fin}."
        )
    return {
        "pagina_inicio": paginas[0],
        "pagina_fin": paginas[-1],
        "paginas": paginas,
    }


def _seleccionar_encabezados(texto, es_ley_base):
    encabezados = list(PATRON_ARTICULO.finditer(texto))
    if es_ley_base:
        return encabezados

    seleccionados = []
    siguiente = 1
    for encabezado in encabezados:
        numero = int(re.match(r"\d+", encabezado.group("numero")).group())
        if numero >= siguiente and (
            numero <= siguiente + 2 or encabezado.group("ordinal")
        ):
            seleccionados.append(encabezado)
            siguiente = numero + 1
    return seleccionados


def _referencias_ley_1801(texto):
    texto_plano = " ".join(unicodedata.normalize("NFKC", texto).split())
    articulos = []
    for match in PATRON_REFERENCIA.finditer(texto_plano):
        articulos.extend(re.findall(r"\d+[A-Z]?", match.group("articulos"), re.IGNORECASE))
    return list(dict.fromkeys(articulos))


def _epigrafe(resto, numero_articulo):
    primera_frase = resto.strip().split("\n", 1)[0].strip()
    frase = re.split(r"(?<=[.!?])\s+", primera_frase, maxsplit=1)[0]
    if len(frase) > 180:
        frase = frase[:177].rstrip() + "..."
    return frase or f"Artículo {numero_articulo}"


def _relacion_documento(metadata, texto):
    texto = unicodedata.normalize("NFKC", texto).casefold()
    modifica = bool(re.search(r"\bmodif\w*", texto))
    adiciona = bool(re.search(r"\badici\w*", texto))
    corrige = bool(re.search(r"\bcorr(?:i|\u00ed)g\w*|\bcorr(?:i|\u00ed)j\w*", texto))
    if corrige:
        return "corrige"
    if modifica and adiciona:
        return "modifica y adiciona"
    if adiciona:
        return "adiciona"
    if modifica:
        return "modifica"
    if metadata["clase_documento"] == "modificatoria":
        return "modifica"
    if metadata["clase_documento"] == "adicionatoria":
        return "adiciona"
    return "dispone sobre"


def _segmentar_documento(documento):
    metadata = documento["documento"]
    es_ley_base = (
        metadata["tipo_norma"] == "ley"
        and metadata["numero"] == 1801
        and metadata["anio"] == 2016
        and metadata["clase_documento"] == "base"
    )
    texto, rangos_paginas = _texto_y_paginas(documento)
    encabezados = _seleccionar_encabezados(texto, es_ley_base)
    provisiones = []

    for indice, encabezado in enumerate(encabezados):
        inicio = encabezado.start()
        fin = encabezados[indice + 1].start() if indice + 1 < len(encabezados) else len(texto)
        resto = encabezado.group("resto").strip()
        continuacion = texto[encabezado.end():fin].strip()
        cuerpo = "\n".join(parte for parte in (resto, continuacion) if parte).strip()
        numero = encabezado.group("numero") + (encabezado.group("ordinal") or "")
        provisiones.append(
            {
                "numero": numero,
                "texto": cuerpo,
                "referencias_ley_1801": _referencias_ley_1801(cuerpo),
                **_ubicacion_paginas(rangos_paginas, inicio, fin),
            }
        )
    return es_ley_base, provisiones


def _registro(metadata, provision, es_ley_base):
    numero_fuente = provision["numero"]
    referencias = provision["referencias_ley_1801"]
    ubicacion_fuente = {
        "archivo": metadata["archivo_fuente"],
        "pagina_inicio": provision["pagina_inicio"],
        "pagina_fin": provision["pagina_fin"],
        "paginas": provision["paginas"],
    }
    if es_ley_base:
        return {
            "id": f"art-{numero_fuente.lower()}",
            "ubicacion": f"{metadata['titulo']}, artículo {numero_fuente} (versión del PDF; vigencia por verificar)",
            "epigrafe": _epigrafe(provision["texto"], numero_fuente),
            "texto": provision["texto"],
            "vigencia": "no_verificada",
            "tema": "texto fuente Ley 1801",
            "fuente": metadata["archivo"],
            "archivo_fuente": metadata["archivo_fuente"],
            "pagina_inicio": provision["pagina_inicio"],
            "pagina_fin": provision["pagina_fin"],
            "paginas": provision["paginas"],
            "ubicaciones_fuente": [ubicacion_fuente],
            "norma": metadata["titulo"],
            "articulo_fuente": numero_fuente,
            "articulos_ley_1801": [numero_fuente],
            "tipo_disposicion": "texto_fuente_ley_base",
        }

    relacion = _relacion_documento(metadata, provision["texto"])
    objetivos = ", ".join(f"artículo {numero}" for numero in referencias)
    destino = f" ({relacion} Ley 1801 de 2016, {objetivos})"
    return {
        "id": (
            f"{metadata['tipo_norma']}-{metadata['numero']}-{metadata['anio']}-"
            f"{metadata['clase_documento']}-art-{numero_fuente.lower()}"
        ),
        "ubicacion": f"{metadata['titulo']}, artículo {numero_fuente}{destino}",
        "epigrafe": (
            f"Artículo {numero_fuente} de {metadata['titulo']}: "
            f"{relacion} Ley 1801, artículo(s) {', '.join(referencias)}"
        ),
        "texto": provision["texto"],
        "vigencia": "no_verificada",
        "tema": f"disposición que {relacion} Ley 1801",
        "fuente": metadata["archivo"],
        "archivo_fuente": metadata["archivo_fuente"],
        "pagina_inicio": provision["pagina_inicio"],
        "pagina_fin": provision["pagina_fin"],
        "paginas": provision["paginas"],
        "ubicaciones_fuente": [ubicacion_fuente],
        "norma": metadata["titulo"],
        "articulo_fuente": numero_fuente,
        "articulos_ley_1801": referencias,
        "tipo_disposicion": relacion,
    }


def construir_corpus(input_dir=CARPETA_EXTRAIDOS, output_path=SALIDA_POR_DEFECTO):
    input_dir = Path(input_dir)
    output_path = Path(output_path)
    archivos = sorted(input_dir.rglob("*.json"))
    if not archivos:
        raise FileNotFoundError(f"No se encontraron JSON extraídos en {input_dir}")

    registros = []
    revision = []
    registros_unicos = {}
    ley_base_encontrada = False
    for archivo in archivos:
        documento = json.loads(archivo.read_text(encoding="utf-8"))
        if not isinstance(documento, dict) or not {"documento", "paginas"} <= documento.keys():
            revision.append(
                {
                    "archivo": archivo.name,
                    "motivo": "Formato legado o incompleto; se requiere el JSON de extraer.py "
                    "con metadatos de documento y páginas.",
                }
            )
            continue
        metadata = documento["documento"]
        es_ley_base, provisiones = _segmentar_documento(documento)
        ley_base_encontrada = ley_base_encontrada or es_ley_base

        if not provisiones:
            revision.append(
                {"archivo": metadata["archivo"], "motivo": "No se detectaron encabezados de artículo."}
            )
            continue
        if es_ley_base:
            for provision in provisiones:
                registro = _registro(metadata, provision, True)
                registros.append(registro)
                registros_unicos[
                    (registro["norma"], registro["articulo_fuente"], registro["texto"])
                ] = registro
            continue

        relacionadas = [
            provision for provision in provisiones if provision["referencias_ley_1801"]
        ]
        if not relacionadas:
            revision.append(
                {
                    "archivo": metadata["archivo"],
                    "motivo": "No se detectaron referencias explícitas a la Ley 1801; "
                    "se conserva en texto_extraido, pero no se agrega al corpus RAG.",
                }
            )
            continue
        for provision in relacionadas:
            registro = _registro(metadata, provision, False)
            clave = (
                registro["norma"],
                registro["articulo_fuente"],
                " ".join(unicodedata.normalize("NFKC", registro["texto"]).split()),
            )
            existente = registros_unicos.get(clave)
            if existente is not None:
                fuentes = existente.setdefault("fuentes", [existente["fuente"]])
                if registro["fuente"] not in fuentes:
                    fuentes.append(registro["fuente"])
                ubicaciones = existente.setdefault(
                    "ubicaciones_fuente",
                    [
                        {
                            "archivo": existente["archivo_fuente"],
                            "pagina_inicio": existente["pagina_inicio"],
                            "pagina_fin": existente["pagina_fin"],
                            "paginas": existente["paginas"],
                        }
                    ],
                )
                ubicaciones.append(registro["ubicaciones_fuente"][0])
                revision.append(
                    {
                        "archivo": metadata["archivo"],
                        "motivo": f"Disposición idéntica fusionada con {existente['fuente']} "
                        f"(artículo fuente {registro['articulo_fuente']}).",
                    }
                )
                continue
            registros.append(registro)
            registros_unicos[clave] = registro

    if not ley_base_encontrada:
        raise ValueError(
            "No se encontró Ley_1801_de_2016.pdf como norma base en los JSON extraídos."
        )
    if not registros:
        raise ValueError("No se generaron registros para el corpus.")

    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(
        json.dumps(registros, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    revision_path = output_path.with_name(f"{output_path.stem}_revision.json")
    revision_path.write_text(
        json.dumps(revision, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    print(f"Corpus: {len(registros)} registros -> {output_path}")
    print(f"Revisión: {len(revision)} documentos no incluidos o pendientes -> {revision_path}")
    for item in revision:
        print(f"  Revisar {item['archivo']}: {item['motivo']}")
    return registros


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input-dir", type=Path, default=CARPETA_EXTRAIDOS)
    parser.add_argument("--output", type=Path, default=SALIDA_POR_DEFECTO)
    args = parser.parse_args()
    construir_corpus(args.input_dir, args.output)


if __name__ == "__main__":
    main()
