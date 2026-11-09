"""Respuesta RAG: búsqueda por trozos -> artículo completo -> LLM.

Uso como librería (con engine/ en sys.path):
    from generation.responder import responder
    r = responder("¿Qué pasa si no pago una multa?", k=3)

Uso por línea de comandos (desde la raíz del repo):
    python engine/generation/responder.py "pregunta" [-k 3]
    python engine/generation/responder.py --demo [--pausa 10]

Devuelve el formato de docs/api_contract.md:
    respuesta, articulos_citados, fragmentos, fuera_de_dominio
    + citas (opcional): artículo y, si aparece, numeral o parágrafo de cada cita
    + tema_detectado (opcional): tema que detectó el clasificador temático, o "general"
(con incluir_diagnostico=True agrega "diagnostico": tiempos, modelo y citas descartadas).
"""
import argparse
import sys
import time
from pathlib import Path
from typing import List

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))  # carpeta engine/
from generation.citas import existe_en_articulo, extraer_citas, texto_cita  # noqa: E402
from generation.llm import ErrorLLM, estadisticas, generar  # noqa: E402
from generation.prompt import FRASE_NO_ENCONTRADO, SISTEMA, construir_mensaje  # noqa: E402
from retrieval.clasificador import clasificar  # noqa: E402
from retrieval.search import articulo_completo, buscar, id_articulo, precargar  # noqa: E402

ESTRATEGIA = "fragmentos"

PREGUNTAS_DEMO = [
    "¿Me pueden multar por tomar licor en el parque?",
    "¿La policía puede entrar a mi casa sin orden?",
    "¿Hay descuento si pago la multa rápido?",
    "¿Cuánto cuesta renovar el pase de conducción?",
    "¿Cuál es la tarifa del impuesto predial en Bogotá?",
]

def numero_articulo(id_art: str) -> str:
    return id_art.replace("art-", "")


def responder(pregunta: str, k: int = 3, incluir_diagnostico: bool = False) -> dict:
    t0 = time.perf_counter()

    # 1. Búsqueda por trozos (k artículos distintos; el mejor trozo de cada uno).
    fragmentos = buscar(pregunta, k=k, estrategia=ESTRATEGIA)
    t_busqueda = time.perf_counter() - t0

    # 2. Small-to-big: artículo completo de cada trozo, sin repetir.
    articulos, vistos = [], set()
    for f in fragmentos:
        art = id_articulo(f["id"])
        if art not in vistos:
            vistos.add(art)
            a = articulo_completo(f["id"], ESTRATEGIA)
            articulos.append({**a, "numero": numero_articulo(a["id"])})

    # 3. Prompt + LLM.
    t1 = time.perf_counter()
    llm = generar(SISTEMA, construir_mensaje(pregunta, articulos))
    respuesta = llm.texto
    t_llm = time.perf_counter() - t1

    # 4. Citas: solo se aceptan artículos que estaban en el contexto, y solo los
    #    numerales/parágrafos que existen en el texto de ese artículo.
    textos = {a["numero"]: a["texto"] for a in articulos}
    fuera_de_dominio = FRASE_NO_ENCONTRADO.rstrip(".").lower() in respuesta.lower()
    citas, descartadas, inexistentes, articulos_ok = [], [], [], []
    for c in extraer_citas(respuesta):
        if c["articulo"] not in textos:
            descartadas.append(texto_cita(c))  # artículo que no estaba en el contexto
            continue
        if c["articulo"] not in articulos_ok:
            articulos_ok.append(c["articulo"])
        if not existe_en_articulo(c, textos[c["articulo"]]):
            inexistentes.append(texto_cita(c))  # numeral o parágrafo que el artículo no tiene
            continue
        citas.append({
            "articulo": f"Artículo {c['articulo']}",
            "numeral": c["numeral"],
            "paragrafo": c["paragrafo"],
            "texto": texto_cita(c),
        })

    resultado = {
        "respuesta": respuesta,
        "articulos_citados": [] if fuera_de_dominio else [f"Artículo {n}" for n in articulos_ok],
        "fragmentos": fragmentos,
        "fuera_de_dominio": fuera_de_dominio,
        "citas": [] if fuera_de_dominio else citas,
        "tema_detectado": clasificar(pregunta)["tema"],
    }
    if incluir_diagnostico:
        resultado["diagnostico"] = {
            "modelo_usado": llm.modelo,
            "uso_respaldo": llm.uso_respaldo,
            "articulos_en_contexto": [a["numero"] for a in articulos],
            "citas_descartadas": descartadas,
            "citas_inexistentes": inexistentes,
            "tiempo_busqueda_s": round(t_busqueda, 2),
            "tiempo_llm_s": round(t_llm, 2),
            "tiempo_total_s": round(time.perf_counter() - t0, 2),
        }
    return resultado


def _mostrar(pregunta: str, r: dict) -> None:
    d = r.get("diagnostico", {})
    print("=" * 80)
    print(f"PREGUNTA: {pregunta}")
    print("-" * 80)
    print(r["respuesta"], flush=True)
    print("-" * 80)
    print(f"articulos_citados: {r['articulos_citados']}")
    print("citas:             " + (", ".join(c["texto"] for c in r.get("citas", [])) or "ninguna"))
    print(f"tema_detectado:    {r.get('tema_detectado')}")
    print(f"fuera_de_dominio:  {r['fuera_de_dominio']}")
    print("fragmentos:        " + ", ".join(f"{f['id']} ({f['score']:.3f})" for f in r["fragmentos"]))
    if d:
        print(f"contexto:          artículos {d['articulos_en_contexto']}")
        print(f"citas descartadas: {d['citas_descartadas'] or 'ninguna'} (artículo fuera del contexto)")
        print(f"citas inexistentes: {d['citas_inexistentes'] or 'ninguna'} (numeral/parágrafo que no existe)")
        print(f"tiempo:            total {d['tiempo_total_s']} s "
              f"(búsqueda {d['tiempo_busqueda_s']} s, LLM {d['tiempo_llm_s']} s)")
        print(f"modelo usado:      {d['modelo_usado']}" + (" (RESPALDO)" if d["uso_respaldo"] else ""), flush=True)


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawTextHelpFormatter)
    ap.add_argument("pregunta", nargs="*")
    ap.add_argument("-k", type=int, default=3)
    ap.add_argument("--demo", action="store_true", help="prueba 5 preguntas")
    ap.add_argument("--pausa", type=float, default=10, help="segundos entre preguntas (plan gratuito)")
    args = ap.parse_args()

    preguntas = PREGUNTAS_DEMO if args.demo else [" ".join(args.pregunta)] if args.pregunta else []
    if not preguntas:
        ap.error("indica una pregunta o usa --demo")

    t = time.perf_counter()
    precargar(ESTRATEGIA)
    print(f"Carga inicial (modelo de embeddings + índice): {time.perf_counter() - t:.1f} s", flush=True)

    for i, p in enumerate(preguntas):
        if i:
            time.sleep(args.pausa)
        try:
            _mostrar(p, responder(p, k=args.k, incluir_diagnostico=True))
        except ErrorLLM as e:
            print("=" * 80)
            print(f"PREGUNTA: {p}\nERROR: {e}", flush=True)
    print("\nLlamadas al LLM por modelo (ok / fallo): "
          +(", ".join(f"{m}: {e['ok']} / {e['fallo']}" for m, e in estadisticas.items()) or "ninguna"), flush=True)


if __name__ == "__main__":
    main()
