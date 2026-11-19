"""Entidades por reglas del corpus: autoridades, lugares, montos y plazos (Fase 2).

El NER de spaCy (es_core_news_sm) etiqueta mal el texto juridico ("numeral" como lugar,
"destruccion" como persona), asi que estas cuatro clases se extraen con reglas explicitas:
un diccionario de formas para autoridades y lugares, y expresiones regulares para montos y plazos.

Uso, desde la raiz del repositorio:
    python engine/analysis/entidades_reglas.py            # solo texto base de la Ley 1801
    python engine/analysis/entidades_reglas.py --todo     # incluye las normas modificatorias

No necesita spaCy. Deja docs/analisis/entidades_reglas_<base|todo>.json (solo conteos, sin texto).
"""
import argparse
import json
import re
import unicodedata
from collections import Counter
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[2]
CORPUS_POR_DEFECTO = RAIZ / "corpus" / "procesados" / "corpus_ley_1801.json"
CARPETA_SALIDA = RAIZ / "docs" / "analisis"


def sin_tildes(s: str) -> str:
    return "".join(c for c in unicodedata.normalize("NFD", s.lower()) if unicodedata.category(c) != "Mn")


# Cada entidad: nombre canonico -> expresion regular sobre texto sin tildes y en minusculas.
AUTORIDADES = {
    "Policía Nacional": r"\bpolicia nacional\b",
    "personal uniformado de la Policía": r"\bpersonal uniformado\b",
    "autoridad de policía": r"\bautoridades? de policia\b",
    "alcalde": r"\balcaldes?\b",
    "gobernador": r"\bgobernador(?:es)?\b",
    "Presidente de la República": r"\bpresidente de la republica\b",
    "inspector de policía": r"\binspectores? (?:de policia|rurales|urbanos)\b",
    "corregidor": r"\bcorregidor(?:es)?\b",
    "comandante de estación": r"\bcomandantes? de (?:estacion|subestacion)\b",
    "Ministerio Público": r"\bministerio publico\b",
    "Corte Constitucional": r"\bcorte constitucional\b",
    "concejo municipal o distrital": r"\bconcejos? (?:municipal|distrital|municipales|distritales)\b",
    "Ministerio del Interior": r"\bministerio del interior\b",
    "autoridad ambiental": r"\bautoridad(?:es)? ambiental(?:es)?\b",
}
LUGARES = {
    "espacio público": r"\bespacios? publicos?\b",
    "vía pública": r"\bvias? publicas?\b",
    "parque": r"\bparques?\b",
    "establecimiento de comercio": r"\bestablecimientos? de comercio\b",
    "establecimiento educativo": r"\bestablecimientos? educativos?\b",
    "domicilio": r"\bdomicilios?\b",
    "lugar abierto al público": r"\blugares? abiertos? al publico\b",
    "transporte público": r"\btransporte (?:publico|masivo)\b",
    "estadio o escenario deportivo": r"\b(?:estadios?|escenarios? deportivos?)\b",
    "zona de recreo": r"\bzonas? de recreo\b",
    "área protegida": r"\bareas? protegidas?\b",
}
RE_MULTA_TIPO = re.compile(r"\bmulta\s+general\s+tipo\s*(\d)\b|\bmulta\s+tipo\s*(\d)\b")
RE_MULTA_ESPECIAL = re.compile(r"\bmulta\s+especial\b")
RE_SALARIO = re.compile(r"\b(?:smdlv|smldv|smlmv|smmlv|uvt|salarios?\s+minimos?)\b")
RE_PLAZO = re.compile(r"(?:\(\s*\d+\s*\)|\b\d+)\s*(horas?|minutos?|dias?|semanas?|meses|mes|anos?)\b")
UNIDAD = {"hora": "horas", "horas": "horas", "minuto": "minutos", "minutos": "minutos", "dia": "días",
          "dias": "días", "semana": "semanas", "semanas": "semanas", "mes": "meses", "meses": "meses",
          "ano": "años", "anos": "años"}


def cargar(ruta: Path, todo: bool):
    datos = json.loads(ruta.read_text(encoding="utf-8"))
    if not todo:
        datos = [d for d in datos if d.get("tipo_disposicion") == "texto_fuente_ley_base"]
    return datos


def contar(diccionario, textos):
    total, registros = Counter(), Counter()
    for t in textos:
        for nombre, patron in diccionario.items():
            n = len(re.findall(patron, t))
            if n:
                total[nombre] += n
                registros[nombre] += 1
    return {k: {"ocurrencias": total[k], "registros": registros[k]} for k, _ in total.most_common()}


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--corpus", type=Path, default=CORPUS_POR_DEFECTO)
    ap.add_argument("--carpeta-salida", type=Path, default=CARPETA_SALIDA)
    ap.add_argument("--todo", action="store_true", help="incluye las disposiciones modificatorias")
    args = ap.parse_args()

    registros = cargar(args.corpus, args.todo)
    textos = [sin_tildes(r["texto"]) for r in registros]
    alcance = "todo" if args.todo else "base"

    tipos = Counter()
    plazos = Counter()
    n_especial = n_salario = 0
    for t in textos:
        for m in RE_MULTA_TIPO.finditer(t):
            tipos[m.group(1) or m.group(2)] += 1
        n_especial += len(RE_MULTA_ESPECIAL.findall(t))
        n_salario += len(RE_SALARIO.findall(t))
        for m in RE_PLAZO.finditer(t):
            plazos[UNIDAD[m.group(1)]] += 1

    resultado = {
        "alcance": "todo el corpus" if args.todo else "solo texto base Ley 1801",
        "registros": len(registros),
        "autoridades": contar(AUTORIDADES, textos),
        "lugares": contar(LUGARES, textos),
        "montos": {
            "multa_general_por_tipo": {f"tipo {k}": tipos[k] for k in sorted(tipos)},
            "multa_especial": n_especial,
            "referencias_a_salarios_minimos": n_salario,
        },
        "plazos_por_unidad": dict(plazos.most_common()),
    }
    args.carpeta_salida.mkdir(parents=True, exist_ok=True)
    ruta = args.carpeta_salida / f"entidades_reglas_{alcance}.json"
    ruta.write_text(json.dumps(resultado, ensure_ascii=False, indent=2), encoding="utf-8")

    print(f"=== {resultado['alcance']}: {len(registros)} registros ===")
    for clave in ("autoridades", "lugares"):
        print(f"\n{clave}:")
        for k, v in resultado[clave].items():
            print(f"  {k:36s} {v['ocurrencias']:4d} ocurrencias en {v['registros']:3d} registros")
    print("\nmontos:", resultado["montos"])
    print("plazos por unidad:", resultado["plazos_por_unidad"])
    print(f"\nGuardado en {ruta}")


if __name__ == "__main__":
    main()
