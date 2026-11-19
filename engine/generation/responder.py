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
from generation.prompt import INICIO_NO_ENCONTRADO, construir_mensaje, sistema  # noqa: E402
from indexing import normas as normas_mod  # noqa: E402
from retrieval.clasificador import clasificar  # noqa: E402
from retrieval.search import (  # noqa: E402
    articulo_para_contexto, buscar, id_articulo, normas_cargadas, otras_normas_con_articulo, precargar,
)

ESTRATEGIA = "fragmentos"

PREGUNTAS_DEMO = [
    "¿Me pueden multar por tomar licor en el parque?",
    "¿La policía puede entrar a mi casa sin orden?",
    "¿Hay descuento si pago la multa rápido?",
    "¿Cuánto cuesta renovar el pase de conducción?",
    "¿Cuál es la tarifa del impuesto predial en Bogotá?",
]

def numero_articulo(id_art: str) -> str:
    """'art-140' -> '140'; 'ley769-art-131' -> '131'."""
    return normas_mod.numero_de_id(id_art)


def _norma_de_cita(cita: dict, textos: dict) -> tuple:
    """Clave de norma de una cita. Si la cita no dice la norma: la única del contexto que tiene ese
    número de artículo; si hay varias o ninguna, la Ley 1801 (norma base)."""
    if cita["norma"]:
        return cita["norma"]
    candidatas = [k for (k, n) in textos if n == cita["articulo"]]
    if len(candidatas) == 1:
        return candidatas[0]
    return normas_mod.clave(normas_mod.NORMA_BASE)


def _nota_otras_normas(pregunta: str) -> str:
    """Aviso para «artículo N» sin norma cuando otras normas cargadas también tienen ese número."""
    partes = []
    for x in otras_normas_con_articulo(pregunta, ESTRATEGIA):
        otras = [normas_mod.corta(o) for o in x["otras"]]
        lista = otras[0] if len(otras) == 1 else ", ".join(otras[:-1]) + " y " + otras[-1]
        verbo = "también tiene" if len(otras) == 1 else "también tienen"
        ejemplo = f"«artículo {x['numero']} de la {normas_mod.corta(x['otras'][0])}»"
        partes.append(
            f"No indicaste la norma del artículo {x['numero']}, así que respondí con la {x['norma']}. "
            f"La {lista} {verbo} un artículo {x['numero']}; si te refieres a esa norma, pregunta {ejemplo}."
        )
    return ("\n\n" + " ".join(partes)) if partes else ""


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
            a = articulo_para_contexto(f["id"], ESTRATEGIA, pregunta=pregunta)  # completo, o un extracto si es enorme
            articulos.append({**a, "numero": numero_articulo(a["id"])})

    # 3. Prompt + LLM. El dominio son las normas cargadas en el índice vigente.
    lista_normas = [n["norma"] for n in normas_cargadas(ESTRATEGIA)]
    nombres = {normas_mod.clave(n): n for n in lista_normas}
    t1 = time.perf_counter()
    llm = generar(sistema(lista_normas), construir_mensaje(pregunta, articulos))
    respuesta = llm.texto
    t_llm = time.perf_counter() - t1

    # 4. Citas: solo se aceptan artículos que estaban en el contexto, y solo los
    #    numerales/parágrafos que existen en el texto de ese artículo.
    # textos por (norma, número): con varias normas, el mismo número puede existir en más de una.
    textos = {(normas_mod.clave(a.get("norma")), a["numero"]): a["texto"] for a in articulos}
    menciona_no_encontrado = INICIO_NO_ENCONTRADO.lower() in respuesta.lower()
    citas, descartadas, inexistentes, articulos_ok = [], [], [], []
    for c in extraer_citas(respuesta):
        k = _norma_de_cita(c, textos)
        es_base = k == normas_mod.clave(normas_mod.NORMA_BASE)
        nombre = nombres.get(k) or (normas_mod.NORMA_BASE if es_base else normas_mod.corta(" ".join(k)))
        legible = texto_cita(c, None if es_base else normas_mod.corta(nombre))
        if (k, c["articulo"]) not in textos:
            descartadas.append(legible)  # artículo (de esa norma) que no estaba en el contexto
            continue
        etiqueta = f"Artículo {c['articulo']}" if es_base else f"{nombre}, Artículo {c['articulo']}"
        if etiqueta not in articulos_ok:
            articulos_ok.append(etiqueta)
        if not existe_en_articulo(c, textos[(k, c["articulo"])]):
            inexistentes.append(legible)  # numeral o parágrafo que el artículo no tiene
            continue
        if any(x["texto"] == legible for x in citas):
            continue  # la misma cita repetida en la respuesta
        citas.append({
            "articulo": f"Artículo {c['articulo']}",
            "numeral": c["numeral"],
            "paragrafo": c["paragrafo"],
            "texto": legible,
            "norma": nombre,
        })

    # Fuera de dominio si la respuesta EMPIEZA con la frase, o si la menciona y no trae ninguna cita
    # válida. A veces el modelo responde bien (con citas) y agrega la frase al final para una parte
    # de la pregunta que no está en el corpus: eso no es una respuesta fuera de dominio.
    empieza = respuesta.lstrip(" *_#>\n").lower().startswith(INICIO_NO_ENCONTRADO.lower())
    fuera_de_dominio = empieza or (menciona_no_encontrado and not citas)

    # «Artículo N» sin decir la norma: se respondió con la de mayor prioridad (NORMA_PRINCIPAL, por
    # defecto la Ley 1801) y se avisa, con un texto fijo (no del LLM), que otra norma cargada también
    # tiene un artículo N. Va después de extraer las citas: no cuenta como cita.
    nota = "" if fuera_de_dominio else _nota_otras_normas(pregunta)

    resultado = {
        "respuesta": respuesta + nota,
        "articulos_citados": [] if fuera_de_dominio else articulos_ok,
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
