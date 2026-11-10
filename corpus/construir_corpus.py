"""Extrae los PDF del corpus y genera corpus/procesados/corpus_ley_1801.json."""
import argparse
from pathlib import Path

if __package__:
    from .extraer import CARPETA_DOCUMENTOS, CARPETA_EXTRAIDOS, extract_all
    from .segmentar import SALIDA_POR_DEFECTO, construir_corpus
else:
    from extraer import CARPETA_DOCUMENTOS, CARPETA_EXTRAIDOS, extract_all
    from segmentar import SALIDA_POR_DEFECTO, construir_corpus


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input-dir", type=Path, default=CARPETA_DOCUMENTOS)
    parser.add_argument("--output-dir", type=Path, default=CARPETA_EXTRAIDOS)
    parser.add_argument("--output", type=Path, default=SALIDA_POR_DEFECTO)
    args = parser.parse_args()

    extract_all(args.input_dir, args.output_dir)
    construir_corpus(args.output_dir, args.output)


if __name__ == "__main__":
    main()
