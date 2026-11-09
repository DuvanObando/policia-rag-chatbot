"""Capa mínima de acceso al LLM.

Lee del .env de la raíz del repo:
    LLM_PROVEEDOR         (p. ej. gemini)
    LLM_MODELO            modelo principal (p. ej. gemini-3.8-flash)
    LLM_MODELO_RESPALDO   modelo de respaldo, opcional (p. ej. gemini-3.6-flash)
    GEMINI_API_KEY        clave del proveedor; nunca se versiona

Uso:
    from generation.llm import generar
    r = generar(sistema="...", usuario="...")
    r.texto, r.modelo, r.uso_respaldo

Comportamiento (presupuesto total PRESUPUESTO_S, ~21 s en el peor caso):
  1. Modelo principal, con límite de CAP_PRINCIPAL_S.
  2. Si da 503 / no responde: espera corta (ESPERA_503_S) y un reintento al principal,
     pero solo si queda tiempo para el respaldo.
  3. Si vuelve a fallar: pasa al modelo de respaldo con el tiempo que quede.
  4. Un 429 (límite de peticiones) se reintenta con espera creciente mientras alcance el presupuesto.
  Gemini exige un plazo mínimo de 10 s por llamada, así que cada llamada dura al menos
  MIN_LLAMADA_S; por eso, en el peor caso caben dos llamadas (principal + respaldo).
  Los reintentos internos de la librería están desactivados: todo se ve en los mensajes [llm].

Para agregar otro proveedor (p. ej. Groq): escribir una función
`_generar_groq(sistema, usuario, modelo, timeout_s) -> str` que lance
`LimiteDePeticiones` ante un 429 y `ModeloNoDisponible` ante 5xx o timeout,
y registrarla en PROVEEDORES. El resto del código no cambia.
"""
import os
import time
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path
from typing import Optional

from dotenv import load_dotenv

RAIZ = Path(__file__).resolve().parents[2]
load_dotenv(RAIZ / ".env")
load_dotenv(RAIZ / "engine" / ".env")  # opcional; no pisa lo ya definido

MIN_LLAMADA_S = 10.0     # Gemini rechaza plazos menores a 10 s (error 400)
PRESUPUESTO_S = 21.0     # tiempo máximo total de la parte del LLM
CAP_PRINCIPAL_S = 10.0   # límite de la primera llamada al modelo principal
CAP_REINTENTO_S = 10.0   # límite del reintento al modelo principal
ESPERA_503_S = 1.0       # espera corta antes del reintento
ESPERA_429_S = 2.0       # 2, 4, 8... s ante un 429


class LimiteDePeticiones(Exception):
    """El proveedor respondió 429 (límite de peticiones o de cuota)."""


class ModeloNoDisponible(Exception):
    """503/5xx o sin respuesta a tiempo: el modelo no está disponible ahora."""


class ErrorLLM(Exception):
    """Error del LLM con un mensaje claro para mostrar."""


@dataclass
class RespuestaLLM:
    texto: str
    modelo: str
    proveedor: str
    uso_respaldo: bool


def _log(msg: str) -> None:
    print(f"[llm] {msg}", flush=True)


# ---------------------------------------------------------------- Gemini

@lru_cache(maxsize=1)
def _cliente_gemini():
    from google import genai
    from google.genai import types

    clave = os.getenv("GEMINI_API_KEY")
    if not clave:
        raise ErrorLLM("Falta GEMINI_API_KEY en el archivo .env de la raíz del repo.")
    # attempts=1: sin reintentos internos de la librería (los hacemos nosotros, visibles)
    return genai.Client(
        api_key=clave,
        http_options=types.HttpOptions(retry_options=types.HttpRetryOptions(attempts=1)),
    )


def _tipos_de_red() -> tuple:
    """Excepciones de timeout y de red. google-genai 3.x usa 'httpx2'; también se cubre 'httpx'."""
    import importlib

    tiempo, red = [TimeoutError], []
    for nombre in ("httpx2", "httpx"):
        try:
            m = importlib.import_module(nombre)
        except ImportError:
            continue
        tiempo.append(m.TimeoutException)
        red.append(m.TransportError)
    return tuple(tiempo), tuple(red)


def _generar_gemini(sistema: str, usuario: str, modelo: str, timeout_s: float) -> str:
    from google.genai import errors, types

    tipos_timeout, tipos_red = _tipos_de_red()

    try:
        r = _cliente_gemini().models.generate_content(
            model=modelo,
            contents=usuario,
            config=types.GenerateContentConfig(
                system_instruction=sistema,
                http_options=types.HttpOptions(timeout=int(timeout_s * 1000)),
            ),
        )
    except errors.APIError as e:
        if e.code == 429:
            raise LimiteDePeticiones(str(e)) from e
        if e.code in (500, 502, 503, 504):
            raise ModeloNoDisponible(f"{e.code} {e.status or ''}".strip()) from e
        raise ErrorLLM(f"Gemini respondió un error {e.code}: {e.message}") from e
    except tipos_timeout as e:
        raise ModeloNoDisponible(f"sin respuesta en {timeout_s:.0f} s") from e
    except tipos_red as e:
        raise ModeloNoDisponible(f"error de red ({type(e).__name__})") from e
    return (r.text or "").strip()


# ---------------------------------------------------------------- registro

PROVEEDORES = {
    "gemini": _generar_gemini,
}


def configuracion() -> tuple:
    """(proveedor, modelo principal, modelo de respaldo o None)."""
    proveedor = os.getenv("LLM_PROVEEDOR", "gemini").strip().lower()
    modelo = os.getenv("LLM_MODELO", "").strip()
    respaldo = os.getenv("LLM_MODELO_RESPALDO", "").strip() or None
    if proveedor not in PROVEEDORES:
        raise ErrorLLM(f"LLM_PROVEEDOR={proveedor!r} no soportado. Disponibles: {list(PROVEEDORES)}")
    if not modelo:
        raise ErrorLLM("Falta LLM_MODELO en el archivo .env de la raíz del repo.")
    if respaldo == modelo:
        respaldo = None
    return proveedor, modelo, respaldo


def generar(sistema: str, usuario: str) -> RespuestaLLM:
    """Llama al LLM configurado (con reintentos y respaldo) y dice qué modelo respondió."""
    proveedor, principal, respaldo = configuracion()
    funcion = PROVEEDORES[proveedor]
    limite = time.monotonic() + PRESUPUESTO_S

    def restante() -> float:
        return limite - time.monotonic()

    # (modelo, tope de esta llamada en s o None = lo que quede, espera previa en s,
    #  tiempo que debe quedar para intentarlo)
    pasos = [
        (principal, CAP_PRINCIPAL_S, 0.0, MIN_LLAMADA_S),
        # el reintento al principal solo se hace si todavía cabe el respaldo después
        (principal, CAP_REINTENTO_S, ESPERA_503_S, MIN_LLAMADA_S * (2 if respaldo else 1)),
    ]
    if respaldo:
        pasos.append((respaldo, None, 0.0, MIN_LLAMADA_S))

    ultimo_fallo = "sin intentos"
    for modelo, tope, espera, necesita in pasos:
        if restante() - espera < necesita:
            continue  # no alcanza el tiempo para este paso
        if modelo != principal:
            _log(f"{principal} no disponible ({ultimo_fallo}); pasando al modelo de respaldo {modelo}")
        elif espera:
            _log(f"{modelo} no disponible ({ultimo_fallo}); reintento en {espera:g} s")
            time.sleep(espera)

        espera_429 = ESPERA_429_S
        while True:
            if restante() < MIN_LLAMADA_S:
                raise ErrorLLM(
                    f"Se agotó el tiempo ({PRESUPUESTO_S:.0f} s) sin respuesta del LLM. Último fallo: {ultimo_fallo}."
                )
            timeout = min(tope, restante()) if tope else restante()
            try:
                texto = funcion(sistema, usuario, modelo, timeout)
                _log(f"respondió {modelo}" + (" (modelo de respaldo)" if modelo != principal else ""))
                return RespuestaLLM(texto, modelo, proveedor, uso_respaldo=modelo != principal)
            except LimiteDePeticiones:
                ultimo_fallo = "429 límite de peticiones"
                if restante() - espera_429 < MIN_LLAMADA_S:
                    raise ErrorLLM(
                        f"Se alcanzó el límite de peticiones de {proveedor} ({modelo}) y no alcanzó el tiempo "
                        "para esperar. Espera un minuto y vuelve a intentar; si persiste, puede que se haya "
                        "agotado la cuota diaria del plan gratuito."
                    )
                _log(f"429 en {modelo}: límite de peticiones. Espero {espera_429:g} s y reintento")
                time.sleep(espera_429)
                espera_429 *= 2
            except ModeloNoDisponible as e:
                ultimo_fallo = f"{modelo}: {e}"
                break  # siguiente paso (reintento o respaldo)

    raise ErrorLLM(f"Ningún modelo respondió a tiempo. Último fallo: {ultimo_fallo}.")
