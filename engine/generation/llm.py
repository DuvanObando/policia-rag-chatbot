"""Capa mínima de acceso al LLM.

Lee del .env de la raíz del repo:
    LLM_PROVEEDOR         (p. ej. gemini)
    LLM_MODELO            modelo principal (p. ej. gemini-3.5-flash-lite)
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
  Memoria de caídos: si un modelo falla con 503/504/timeout se marca como caído durante
  CAIDO_TTL_S; mientras tanto se salta directo al otro, sin gastar el intento. Si ambos
  están marcados, se intenta igual. Una respuesta correcta quita la marca.
  Gemini exige un plazo mínimo de 10 s por llamada, así que cada llamada dura al menos
  MIN_LLAMADA_S; por eso, en el peor caso caben dos llamadas (principal + respaldo).
  Los reintentos internos de la librería están desactivados: todo se ve en los mensajes [llm].

RESPALDO ENTRE EMPRESAS (Groq). Si GROQ_API_KEY está en el .env y los modelos de Gemini fallan
(503/504, sin respuesta a tiempo, 429 sin tiempo para esperar u otro error), responde Groq con
LLM_GROQ_MODELO (por defecto openai/gpt-oss-120b) y un plazo propio de GROQ_TIMEOUT_S (15 s).
Si los dos modelos de Gemini están marcados como caídos, se va directo a Groq sin gastar tiempo.
Sin GROQ_API_KEY el comportamiento es el de antes. Peor caso total: PRESUPUESTO_S + GROQ_TIMEOUT_S.

ORDEN DE PROVEEDORES: LLM_ORDEN=groq,gemini prueba Groq primero y Gemini después (o al revés con
gemini,groq). Sin LLM_ORDEN: LLM_PROVEEDOR primero y Groq de respaldo, como siempre.

Para agregar otro proveedor: escribir una función `_generar_x(sistema, usuario, modelo, timeout_s)
-> str` que lance `LimiteDePeticiones` ante un 429 y `ModeloNoDisponible` ante 5xx o timeout,
y registrarla en PROVEEDORES.
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
CAIDO_TTL_S = 180.0      # cuánto se recuerda que un modelo está caído (503/504/timeout)


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


# Estado en memoria del proceso: modelo -> instante (monotonic) hasta el que se considera caído.
_caidos: dict = {}
# Conteo de llamadas por modelo, para diagnóstico: modelo -> {"ok": n, "fallo": n}
estadisticas: dict = {}


def _contar(modelo: str, ok: bool) -> None:
    e = estadisticas.setdefault(modelo, {"ok": 0, "fallo": 0})
    e["ok" if ok else "fallo"] += 1


def _marcar_caido(modelo: str) -> None:
    _caidos[modelo] = time.monotonic() + CAIDO_TTL_S


def _segundos_caido(modelo: str) -> float:
    """Segundos que faltan para olvidar la marca de caído (0 si no está caído)."""
    return max(0.0, _caidos.get(modelo, 0.0) - time.monotonic())


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


def _config_razonamiento(types):
    """LLM_RAZONAMIENTO del .env: minimal (por defecto), low, medium, high u off (no se envía)."""
    nivel = os.getenv("LLM_RAZONAMIENTO", "minimal").strip().upper()
    if nivel in ("", "OFF", "NINGUNO", "DEFECTO") or not hasattr(types, "ThinkingLevel"):
        return None
    return types.ThinkingConfig(thinking_level=getattr(types.ThinkingLevel, nivel, types.ThinkingLevel.MINIMAL))


def _generar_gemini(sistema: str, usuario: str, modelo: str, timeout_s: float) -> str:
    from google.genai import errors, types

    tipos_timeout, tipos_red = _tipos_de_red()
    # Razonamiento mínimo: en las pruebas bajó la latencia (9.7 s vs 14.4 s y 1.6 s vs 3.6 s con el
    # mismo prompt). Si un modelo no lo acepta (error 400 que menciona "thinking"), se reintenta sin él.
    razonamiento = _config_razonamiento(types)

    try:
        try:
            r = _cliente_gemini().models.generate_content(
                model=modelo,
                contents=usuario,
                config=types.GenerateContentConfig(
                    system_instruction=sistema,
                    http_options=types.HttpOptions(timeout=int(timeout_s * 1000)),
                    thinking_config=razonamiento,
                ),
            )
        except errors.APIError as e:
            if e.code == 400 and razonamiento is not None and "think" in str(e).lower():
                r = _cliente_gemini().models.generate_content(
                    model=modelo,
                    contents=usuario,
                    config=types.GenerateContentConfig(
                        system_instruction=sistema,
                        http_options=types.HttpOptions(timeout=int(timeout_s * 1000)),
                    ),
                )
            else:
                raise
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


# ---------------------------------------------------------------- Groq (respaldo entre empresas)

GROQ_URL = "https://api.groq.com/openai/v1/chat/completions"
# Varios modelos separados por coma: el límite de tokens por minuto del plan gratuito es POR MODELO,
# así que ante un 429 se pasa al siguiente.
GROQ_MODELO_POR_DEFECTO = "openai/gpt-oss-120b,openai/gpt-oss-20b"
GROQ_ESPERA_MAX_S = 2.0  # ante un 429 con retry-after <= esto, se espera y se reintenta el mismo modelo


def respaldo_externo() -> Optional[tuple]:
    """("groq", "modelo1,modelo2") si hay GROQ_API_KEY en el .env; None si no (sin respaldo entre empresas)."""
    if not os.getenv("GROQ_API_KEY", "").strip():
        return None
    return "groq", os.getenv("LLM_GROQ_MODELO", "").strip() or GROQ_MODELO_POR_DEFECTO


def _timeout_groq() -> float:
    try:
        return max(3.0, float(os.getenv("GROQ_TIMEOUT_S", "15")))
    except ValueError:
        return 15.0


@lru_cache(maxsize=1)
def _cliente_groq():
    import httpx

    clave = os.getenv("GROQ_API_KEY", "").strip()
    if not clave:
        raise ErrorLLM("Falta GROQ_API_KEY en el archivo .env de la raíz del repo.")
    return httpx.Client(headers={"Authorization": f"Bearer {clave}"})


def _generar_groq(sistema: str, usuario: str, modelo: str, timeout_s: float) -> str:
    """Groq por su API compatible con OpenAI (chat/completions), con httpx (sin dependencias nuevas)."""
    import httpx

    cuerpo = {
        "model": modelo,
        "messages": [{"role": "system", "content": sistema}, {"role": "user", "content": usuario}],
        "temperature": 0.2,
        "max_completion_tokens": 2048,
    }
    if modelo.startswith("openai/gpt-oss"):
        cuerpo["reasoning_effort"] = "low"  # modelo de razonamiento: esfuerzo bajo = menos latencia
    try:
        r = _cliente_groq().post(GROQ_URL, json=cuerpo, timeout=timeout_s)
    except httpx.TimeoutException as e:
        raise ModeloNoDisponible(f"sin respuesta en {timeout_s:.0f} s") from e
    except httpx.TransportError as e:
        raise ModeloNoDisponible(f"error de red ({type(e).__name__})") from e
    if r.status_code == 429:
        e = LimiteDePeticiones(f"429 (retry-after: {r.headers.get('retry-after', '?')} s)")
        try:
            e.retry_after = float(r.headers.get("retry-after", ""))
        except ValueError:
            e.retry_after = None
        raise e
    if r.status_code >= 500:
        raise ModeloNoDisponible(str(r.status_code))
    if r.status_code != 200:
        try:
            detalle = r.json().get("error", {}).get("message", "")
        except ValueError:
            detalle = ""
        raise ErrorLLM(f"Groq respondió un error {r.status_code}: {detalle[:200]}")
    texto = r.json()["choices"][0]["message"].get("content") or ""
    # gpt-oss usa espacios finos/duros (U+202F, U+00A0) y guiones no separables (U+2011): caracteres normales.
    return texto.translate({0x202F: " ", 0x00A0: " ", 0x2011: "-"}).strip()


# ---------------------------------------------------------------- registro

PROVEEDORES = {
    "gemini": _generar_gemini,
    "groq": _generar_groq,
}


PRECARGADORES = {
    "gemini": _cliente_gemini,
    "groq": _cliente_groq,
}


def precargar_cliente() -> None:
    """Crea el cliente del proveedor (y el del respaldo externo, si hay) por adelantado.

    Lanza ErrorLLM si falta la clave del proveedor principal. No hace ninguna llamada de red.
    """
    proveedor, _, _ = configuracion()
    PRECARGADORES[proveedor]()
    for p in orden_proveedores():
        if p != proveedor:
            PRECARGADORES[p]()


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


def orden_proveedores() -> list:
    """Orden en que se prueban los proveedores.

    LLM_ORDEN del .env (p. ej. "groq,gemini" o "gemini,groq"). Si no está definida: el de
    LLM_PROVEEDOR primero y luego Groq, si hay GROQ_API_KEY (el comportamiento de siempre).
    Groq se omite si falta GROQ_API_KEY; los nombres repetidos o desconocidos se ignoran.
    """
    proveedor, _, _ = configuracion()
    externo = respaldo_externo()
    texto = os.getenv("LLM_ORDEN", "").strip().lower()
    if texto:
        pedidos = [p.strip() for p in texto.split(",") if p.strip()]
    else:
        pedidos = [proveedor] + ([externo[0]] if externo else [])
    orden = []
    for p in pedidos:
        if p in orden or p not in (proveedor, "groq"):
            continue
        if p == "groq" and p != proveedor and not externo:
            continue  # sin GROQ_API_KEY
        orden.append(p)
    return orden or [proveedor]


def generar(sistema: str, usuario: str) -> RespuestaLLM:
    """Prueba los proveedores en el orden de LLM_ORDEN (con reintentos y modelos de respaldo)."""
    proveedor, principal, respaldo = configuracion()
    orden = orden_proveedores()
    fallos = []
    for i, p in enumerate(orden):
        hay_siguiente = i < len(orden) - 1
        try:
            if p == proveedor:
                r = _generar_cadena(sistema, usuario, proveedor, principal, respaldo,
                                    saltar_si_caidos=hay_siguiente)
            else:
                r = _generar_externo(sistema, usuario, p)
        except ErrorLLM as e:
            fallos.append(f"{p}: {e}")
            if hay_siguiente:
                _log(f"{p} no respondió ({e}); pasando a {orden[i + 1]}")
            continue
        if i > 0:
            r.uso_respaldo = True
        return r
    raise ErrorLLM("Ningún proveedor respondió. " + " | ".join(fallos))


def _generar_externo(sistema: str, usuario: str, prov_ext: str) -> RespuestaLLM:
    """Groq: prueba sus modelos en orden (LLM_GROQ_MODELO) dentro de GROQ_TIMEOUT_S."""
    externo = respaldo_externo()
    if not externo:
        raise ErrorLLM("Falta GROQ_API_KEY en el archivo .env de la raíz del repo.")
    modelos_ext = [m.strip() for m in externo[1].split(",") if m.strip()]
    limite = time.monotonic() + _timeout_groq()  # plazo total para todos los modelos de Groq
    fallo_ext = "sin intentos"
    for modelo_ext in modelos_ext:
        reintentado = False
        while limite - time.monotonic() > 1.0:
            try:
                texto = PROVEEDORES[prov_ext](sistema, usuario, modelo_ext, limite - time.monotonic())
            except LimiteDePeticiones as e:
                _contar(modelo_ext, ok=False)
                fallo_ext = f"{modelo_ext}: límite de peticiones {e}"
                espera = getattr(e, "retry_after", None)
                if (not reintentado and espera is not None and espera <= GROQ_ESPERA_MAX_S
                        and limite - time.monotonic() - espera > 3.0):
                    _log(f"429 en {modelo_ext}; espero {espera:g} s y reintento")
                    time.sleep(espera)
                    reintentado = True
                    continue
                _log(f"429 en {modelo_ext}; paso al siguiente modelo de {prov_ext}")
                break
            except (ModeloNoDisponible, ErrorLLM) as e:
                _contar(modelo_ext, ok=False)
                fallo_ext = f"{modelo_ext}: {e}"
                break
            _contar(modelo_ext, ok=True)
            _log(f"respondió {modelo_ext} ({prov_ext})")
            return RespuestaLLM(texto, modelo_ext, prov_ext, uso_respaldo=modelo_ext != modelos_ext[0])
    raise ErrorLLM(f"falló {prov_ext} ({fallo_ext})")


def _generar_cadena(sistema: str, usuario: str, proveedor: str, principal: str,
                    respaldo: Optional[str], saltar_si_caidos: bool = False) -> RespuestaLLM:
    """Modelo principal y de respaldo del mismo proveedor (ver docstring del módulo)."""
    funcion = PROVEEDORES[proveedor]
    limite = time.monotonic() + PRESUPUESTO_S

    def restante() -> float:
        return limite - time.monotonic()

    # Orden de modelos: los no caídos primero. Si todos están marcados, se intenta igual.
    candidatos = [m for m in (principal, respaldo) if m]
    orden = []
    for m in candidatos:
        faltan = _segundos_caido(m)
        if faltan:
            _log(f"{m} marcado como caído (faltan {faltan:.0f} s para reintentarlo): se salta")
        else:
            orden.append(m)
    if not orden:
        if saltar_si_caidos:  # hay respaldo en otra empresa: no gastar tiempo en modelos caídos
            raise ErrorLLM(f"todos los modelos de {proveedor} marcados como caídos")
        orden = candidatos

    # (modelo, tope de esta llamada en s o None = lo que quede, espera previa en s,
    #  tiempo que debe quedar para intentarlo)
    pasos = []
    for i, m in enumerate(orden):
        pasos.append((m, CAP_PRINCIPAL_S if i == 0 else None, 0.0, MIN_LLAMADA_S))
        if i == 0:
            # reintento corto al mismo modelo, solo si todavía cabe otro modelo después
            pasos.append((m, CAP_REINTENTO_S, ESPERA_503_S, MIN_LLAMADA_S * (2 if len(orden) > 1 else 1)))

    ultimo_fallo = "sin intentos"
    for modelo, tope, espera, necesita in pasos:
        if restante() - espera < necesita:
            continue  # no alcanza el tiempo para este paso
        if modelo != orden[0]:
            _log(f"{orden[0]} no disponible ({ultimo_fallo}); pasando a {modelo}")
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
                _contar(modelo, ok=True)
                _caidos.pop(modelo, None)
                _log(f"respondió {modelo}" + (" (modelo de respaldo)" if modelo != principal else ""))
                return RespuestaLLM(texto, modelo, proveedor, uso_respaldo=modelo != principal)
            except LimiteDePeticiones:
                _contar(modelo, ok=False)
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
                _contar(modelo, ok=False)
                _marcar_caido(modelo)
                ultimo_fallo = f"{modelo}: {e}"
                break  # siguiente paso (reintento o respaldo)

    raise ErrorLLM(f"Ningún modelo respondió a tiempo. Último fallo: {ultimo_fallo}.")
