# Demo de la entrega: motor + corpus real

Guion para mostrar el motor RAG sobre la Ley 1801 de 2016 (corpus de la Fase 1, 249 artículos, 471 fragmentos).

## 1. Arrancar el motor (hacerlo ANTES de la demo)

El arranque **tarda entre 45 y 65 s** en el PC de Duvan (medido el 12/11: 42–64 s). Unos 30 s son solo importar PyTorch y sentence-transformers, porque el repo está dentro de OneDrive; la carga del motor en sí son unos 12–17 s. Por eso: **levántalo unos 2 minutos antes y déjalo corriendo**.

1. Abre una terminal en la raíz del repo.
2. Activa el entorno virtual (Windows):
   ```bash
   engine\.venv\Scripts\activate
   ```
3. Revisa el `.env` (en la raíz, nunca se sube a git): `GEMINI_API_KEY`, `GROQ_API_KEY`, `LLM_ORDEN` y `CORPUS_RUTA=corpus/procesados/corpus_ley_1801.json`.
4. Arranca (sin `--reload`):
   ```bash
   cd engine
   uvicorn api:app --port 8000
   ```
5. Espera la línea `Application startup complete` y comprueba:
   ```bash
   curl http://localhost:8000/health
   ```
   Debe decir `"listo": true`, `"corpus": "corpus_ley_1801.json"`, `"busqueda_modo": "semantico"`, `"llm_orden": ["groq", "gemini"]`.
6. Si los índices no existen (carpeta nueva), hay que construirlos antes (≈17 min en total; no hacerlo el día de la demo): `python engine/indexing/build_index.py --estrategia articulo` y `--estrategia fragmentos`.

## 2. Probar desde Swagger

Abre <http://localhost:8000/docs> (verificado: carga, y expone `GET /health`, `POST /query` y `POST /upload_pdf/`).

1. Despliega **POST /query** → **Try it out**.
2. En el cuerpo escribe solo la pregunta (el `historial` es opcional y hoy no se usa):
   ```json
   { "pregunta": "¿Me pueden multar por tomar licor en el parque?" }
   ```
3. **Execute**. La respuesta aparece abajo con código 200.

## 3. Cinco preguntas de demostración

Verificadas el 12/11 con `LLM_ORDEN=groq,gemini`. **Deja 10 s o más entre preguntas** (límites del plan gratuito: ver sección 5).

| # | Pregunta | Qué debe salir | Qué mostrar |
|---|---|---|---|
| 1 | ¿Me pueden multar por tomar licor en el parque? | **El caso del art. 140.** Dice que lo de «bebidas alcohólicas» en el num. 7 fue declarado **inexequible** (C-253 de 2019) y que ya no rige; no lo presenta como prohibido. Cita `Art. 140, num. 7` | Las citas; en `fragmentos`, `art-140` con vigencia `vigente_modificado_con_inexequibilidad_parcial` y `art-49` con `inexequible`; el texto del fragmento con la marca `[INEXEQUIBLE: bebidas alcohólicas]` |
| 2 | ¿La policía puede entrar a mi casa sin orden? | Los 7 casos de «imperiosa necesidad», uno por numeral | Una cita por cada numeral (`Art. 163, num. 1` … `num. 7`) y el aviso de que el art. 163 figura como modificado |
| 3 | ¿Hay descuento si pago la multa rápido? | 50 % si paga en 5 días hábiles (art. 180) | Lenguaje coloquial («rápido») que la búsqueda semántica asocia con «pronto pago»; cita `Art. 180` |
| 4 | ¿Qué es una medida correctiva? | Definición del art. 172 y que no son sanciones | Cita de parágrafo (`Art. 172, par. 1`) y el aviso de vigencia sobre el art. 173 |
| 5 | ¿Cuánto cuesta renovar el pase de conducción? | **Fuera de dominio:** «No encontré esa información en el Código…» | `fuera_de_dominio: true`, `citas: []`, `articulos_citados: []`: el motor no inventa |

Si sobra tiempo: «¿Cuál es la tarifa del impuesto predial en Bogotá?» (otra fuera de dominio) y «¿Qué dice el Código sobre la tenencia de perros potencialmente peligrosos?» (respuesta larga con muchas citas; puede tardar más de 10 s).

## 4. Qué señalar en cada respuesta

- **`respuesta`**: texto en español claro; cada afirmación lleva su cita entre paréntesis.
- **`citas`**: artículo, numeral o parágrafo (`Art. 163, num. 2`, `Art. 180, par. transitorio`). El motor descarta las citas que no están en los artículos recuperados.
- **`vigencia`** (en cada fragmento): todo lo que no sea `vigente` lleva aviso en la respuesta. Valores del corpus real: `vigente`, `vigente_modificado`, `vigente_con_inexequibilidad_parcial`, `inexequible`, etc.
- **`fragmentos`**: los 3 trozos recuperados, con `score`, `ubicacion`, `vigencia` y, si vienen, archivo y páginas del PDF fuente. Sirve para mostrar **de dónde** salió la respuesta.
- **`fuera_de_dominio`** y **`tema_detectado`** (p. ej. «Ingreso a domicilio»).
- **Sobre el art. 140:** antes el bot citaba ese numeral como prohibición vigente. Ahora el cargador marca con `[INEXEQUIBLE: …]` las expresiones anuladas (`corpus/anotaciones_vigencia.json`, 5 hoy) y el prompt prohíbe presentarlas como vigentes. Pendiente de Wilder: completar ese archivo.

## 5. Si un proveedor falla: cambiar `LLM_ORDEN`

Proveedores: **Gemini** (principal y respaldo: `gemini-3.5-flash-lite`, `gemini-3.6-flash`) y **Groq** (`openai/gpt-oss-120b`, y `openai/gpt-oss-20b` si el primero da 429). Si uno falla, el motor pasa solo al siguiente; si aun así se atasca:

| Situación | Cambio en `.env` (raíz) |
|---|---|
| Gemini da 503/504 o va lento | `LLM_ORDEN=groq,gemini` (la configuración de la demo) |
| Groq da 429 o errores | `LLM_ORDEN=gemini,groq` |
| Solo quieres Gemini | `LLM_ORDEN=gemini` |

Después **reinicia el motor** (Ctrl+C y volver a arrancar; ≈1 min) y confirma `llm_orden` en `/health`. Si `LLM_ORDEN` está vacía: Gemini primero y Groq de respaldo.

**Deja unos segundos (10 s o más) entre preguntas.** Los planes gratuitos tienen límites de peticiones y de tokens por minuto (en Groq el límite de tokens por minuto es por modelo y cada pregunta usa entre 2 000 y 4 000 tokens). Con preguntas seguidas aparece un 429: el motor pasa al otro modelo o proveedor, pero si todos están limitados responde 503 («servicio ocupado») y basta con esperar medio minuto.

## 6. Cifras de la prueba del 12/11 (`LLM_ORDEN=groq,gemini`)

7 preguntas, 10 s entre cada una, todas HTTP 200. Todas respondieron Groq (6 con `gpt-oss-120b`, 1 con `gpt-oss-20b` tras un 429). Tiempos de 1.2 a 4.8 s, salvo la pregunta del pase de conducción (12.8 s, un 429 del primer modelo). Las dos fuera de dominio salieron bien (`fuera_de_dominio: true`, sin citas).

## 7. Limitaciones que conviene decir

- La vigencia sigue siendo **por artículo**; solo 5 expresiones inexequibles están marcadas a mano.
- No hay frontend ni backend Node conectado todavía: la demo es sobre la API del motor (`/docs`).
- Los planes gratuitos pueden fallar: por eso existen dos proveedores y dos modelos en cada uno.
