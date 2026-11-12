"""Prueba liviana del glosario: que coloquiales se activan en una pregunta y que terminos legales se agregan.

Usa el mismo codigo de expansion del motor (engine/retrieval/expansion.py), pero NO necesita indices,
embeddings ni claves de API. Sirve para revisar rapido si una palabra del glosario dispara lo que debe.

Uso, desde la raiz del repositorio y con el entorno virtual activo:
    python engine/analysis/probar_glosario.py                       # preguntas de eval/preguntas_*.json
    python engine/analysis/probar_glosario.py "me cogieron con un porro" "pelea de perros"
    python engine/analysis/probar_glosario.py --glosario otro.json "mi pregunta"
    python engine/analysis/probar_glosario.py --solo-activadas      # solo preguntas que activan algo

Muestra, por pregunta, cada coloquial detectado y el termino legal que agrega. Si una pregunta con
una palabra ambigua activa el termino equivocado, esa palabra hay que quitarla o convertirla en frase.
"""
import argparse
import json
import sys
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(RAIZ / "engine"))
from retrieval import expansion as ex  # noqa: E402


def preguntas_del_repo():
    for ruta in sorted((RAIZ / "eval").glob("preguntas_*.json")):
        try:
            datos = json.loads(ruta.read_text(encoding="utf-8"))
        except (OSError, ValueError):
            continue
        if isinstance(datos, list):
            for d in datos:
                if isinstance(d, dict) and d.get("pregunta"):
                    yield d["pregunta"]


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("preguntas", nargs="*", help="preguntas a probar (si no hay, se usan las de eval/)")
    ap.add_argument("--glosario", type=Path, default=None, help="otro sinonimos.json (por defecto el del motor)")
    ap.add_argument("--solo-activadas", action="store_true", help="oculta las preguntas que no activan nada")
    args = ap.parse_args()

    if args.glosario:
        ex.RUTA_GLOSARIO = args.glosario
        ex.recargar()
    preguntas = args.preguntas or list(preguntas_del_repo())
    print(f"glosario: {ex.RUTA_GLOSARIO}  |  entradas: {ex.info()['entradas']}  |  metodo: {ex.metodo_disponible()}")

    activadas = 0
    for q in preguntas:
        coincidencias = ex.expandir_detalle(q)["coincidencias"]
        activadas += bool(coincidencias)
        if args.solo_activadas and not coincidencias:
            continue
        print(f"\n{q}")
        if not coincidencias:
            print("   (no activa ningun coloquial)")
        for c in coincidencias:
            print(f"   {c['coloquial']!r:40} -> {c['legal']}")
    print(f"\n{activadas} de {len(preguntas)} preguntas activan al menos un coloquial.")


if __name__ == "__main__":
    main()
