# Demo de la entrega: motor + corpus real

Guion para mostrar el motor RAG sobre la Ley 1801 de 2016 (corpus de la Fase 1, 249 artículos, 471 fragmentos).

**Reglas de oro para la demo**

- **Deja 20 s entre pregunta y pregunta** (límites del plan gratuito de Groq y Gemini).
- **Si sale 503, espera 30 s y repite.**
- Levanta el motor **unos 2 minutos antes** (sección 1) y déjalo corriendo.

## 1. Arrancar el motor (hacerlo ANTES de la demo)

El arranque **tarda entre 45 y 65 s** en el PC de Duvan (medido el 12/11: 42 a 64 s; en el ensayo, 56 s). Unos 40 s son solo importar PyTorch y sentence-transformers, porque el repo está dentro de OneDrive; la carga del motor en sí son unos 12 a 17 s. Por eso: **levántalo unos 2 minutos antes y déjalo corriendo**.

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
6. Si los índices no existen (carpeta nueva), hay que construirlos antes (unos 17 min en total; no hacerlo el día de la demo): `python engine/indexing/build_index.py --estrategia articulo` y `--estrategia fragmentos`.

## 2. Cómo usar /docs (Swagger)

Abre <http://localhost:8000/docs>. Expone `GET /health`, `POST /query` y `POST /upload_pdf/`. Para cada pregunta:

1. **Despliega `POST /query`**: clic en la fila verde.
2. Pulsa **Try it out** (arriba a la derecha de la fila). El cuadro del cuerpo se vuelve editable.
3. **Request body**: borra el ejemplo y deja solo la pregunta. El `historial` es opcional y hoy no se usa:
   ```json
   { "pregunta": "¿Qué dice el artículo 163?" }
   ```
4. Pulsa **Execute** (botón azul) y espera de 1 a 5 s.
5. Baja a **Server response**: el código debe ser **200** y el JSON aparece en **Response body**. (Si es 503, ver la regla de oro de arriba.)
6. Muestra en el **Response body** el campo que dice la tabla.

| # | Pregunta | Campo del Response body que conviene mostrar |
|---|---|---|
| 1 | ¿Me pueden multar por tomar licor en el parque? | `respuesta` (explica que esa parte es inexequible) y `fragmentos`: `art-140` con `vigencia` parcial y `art-49` con `inexequible` |
| 2 | ¿La policía puede entrar a mi casa sin orden? | `citas`: una por numeral, de `Art. 163, num. 1` a `num. 7` |
| 3 | ¿Qué dice el artículo 163? | `fragmentos`: el primero es `art-163-f2`, aunque su `score` es el más bajo |
| 4 | ¿Qué es una medida correctiva? | `respuesta` (la definición) y `fragmentos` con la `vigencia` de cada artículo |
| 5 | ¿Cuánto cuesta renovar el pase de conducción? | `fuera_de_dominio: true`, `citas: []` y `articulos_citados: []` |

## 3. Cinco preguntas de demostración

Verificadas el 12/11 por la API con `LLM_ORDEN=groq,gemini` y 20 s de pausa, y también con cada modelo de Groq por separado. **Pausa recomendada: 20 s. Si sale 503, esperar 30 s y repetir.**

| # | Pregunta | Qué debe salir | Qué mostrar |
|---|---|---|---|
| 1 | ¿Me pueden multar por tomar licor en el parque? | **El caso del art. 140.** La respuesta **lo explica**: la prohibición de «bebidas alcohólicas» (num. 7) fue declarada **inexequible** (C-253 de 2019), ya no rige y no sirve de base para una multa. Cita `Art. 140, num. 7` | La respuesta; en `fragmentos`, `art-140` con vigencia `vigente_modificado_con_inexequibilidad_parcial` y `art-49` con `inexequible`. La marca `[INEXEQUIBLE: …]` va en el texto del artículo que recibe el modelo, no en el fragmento que devuelve la API |
| 2 | ¿La policía puede entrar a mi casa sin orden? | Los 7 casos de «imperiosa necesidad», uno por numeral, y el parágrafo 1 (a veces también el 2) | Una cita por cada numeral (`Art. 163, num. 1` … `num. 7`); el art. 163 sale con vigencia `vigente_modificado` en `fragmentos` y la respuesta suele avisarlo |
| 3 | ¿Qué dice el artículo 163? | Los mismos 7 casos y los parágrafos 1 y 2. Con los dos modelos de Groq | **La búsqueda por número de artículo:** el primer fragmento es `art-163-f2` aunque su `score` (0,789) es menor que el de los otros dos (0,803 y 0,799). Lo pone primero la regla «artículo por número», no la similitud |
| 4 | ¿Qué es una medida correctiva? | La **definición del art. 172** (disuadir, prevenir, superar, resarcir, procurar, educar, proteger o restablecer la convivencia), con cita `Art. 172` (según el modelo, también `par. 1` y `par. 2`). Que las medidas **no son sanciones** (par. 1) lo dice casi siempre, pero no está garantizado | En `fragmentos`, la vigencia de cada artículo: `art-173` con `vigente_modificado` y `art-172` y `art-184` con `vigente`. La vigencia sale ahí; la respuesta no siempre la menciona |
| 5 | ¿Cuánto cuesta renovar el pase de conducción? | **Fuera de dominio:** «No encontré esa información en el Código…» | `fuera_de_dominio: true`, `citas: []`, `articulos_citados: []`: el motor no inventa |

Si sobra tiempo: «¿Cuál es la tarifa del impuesto predial en Bogotá?» (otra fuera de dominio) y «¿Qué dice el Código sobre la tenencia de perros potencialmente peligrosos?» (respuesta larga con muchas citas; puede tardar más de 10 s).

**Si algo sale distinto**

- **La pregunta 1 responde «No encontré esa información…»** (y `fuera_de_dominio: true`): respondió el modelo pequeño de respaldo, `gpt-oss-20b`, porque el grande dio 429. Con ese modelo, esa pregunta sale mal. **Espera 30 s y repite.**
- **La pregunta 4 no trae `par. 1` ni dice que no son sanciones:** es normal con el modelo pequeño. Lo estable es la definición del art. 172 y los fragmentos.
- **503 («servicio ocupado»):** todos los proveedores están limitados. Espera 30 s y repite.

## 4. Qué señalar en cada respuesta

- **`respuesta`**: texto en español claro; cada afirmación lleva su cita entre paréntesis.
- **`citas`**: artículo, numeral o parágrafo (`Art. 163, num. 2`, `Art. 180, par. transitorio`). El motor descarta las citas que no están en los artículos recuperados.
- **`vigencia`** (en cada fragmento): todo lo que no sea `vigente` merece atención. Valores del corpus real: `vigente`, `vigente_modificado`, `vigente_con_inexequibilidad_parcial`, `inexequible`, etc.
- **`fragmentos`**: los 3 trozos recuperados, con `score`, `ubicacion`, `vigencia` y, si vienen, archivo y páginas del PDF fuente. Sirve para mostrar **de dónde** salió la respuesta.
- **`fuera_de_dominio`** y **`tema_detectado`** (p. ej. «Ingreso a domicilio»; con la pregunta del artículo 163 sale `general`).
- **Sobre el art. 140:** antes el bot citaba ese numeral como prohibición vigente. Ahora el cargador marca con `[INEXEQUIBLE: …]` las expresiones anuladas (`corpus/anotaciones_vigencia.json`, 5 hoy) y el prompt prohíbe presentarlas como vigentes. Pendiente de Wilder: completar ese archivo.

## 5. Si un proveedor falla: cambiar `LLM_ORDEN`

Proveedores: **Gemini** (principal y respaldo: `gemini-3.5-flash-lite`, `gemini-3.6-flash`) y **Groq** (`openai/gpt-oss-120b`, y `openai/gpt-oss-20b` si el primero da 429). Si uno falla, el motor pasa solo al siguiente; si aun así se atasca:

| Situación | Cambio en `.env` (raíz) |
|---|---|
| Gemini da 503/504 o va lento | `LLM_ORDEN=groq,gemini` (la configuración de la demo) |
| Groq da 429 o errores | `LLM_ORDEN=gemini,groq` |
| Solo quieres Gemini | `LLM_ORDEN=gemini` |

Después **reinicia el motor** (Ctrl+C y volver a arrancar; ≈1 min) y confirma `llm_orden` en `/health`. Si `LLM_ORDEN` está vacía: Gemini primero y Groq de respaldo.

**Deja 20 s entre preguntas.** Los planes gratuitos tienen límites de peticiones y de tokens por minuto (en Groq el límite de tokens por minuto es por modelo y cada pregunta usa entre 2 000 y 4 000 tokens). Con preguntas seguidas aparece un 429: el motor pasa al otro modelo o proveedor, pero si todos están limitados responde 503 («servicio ocupado»). **Si sale 503, espera 30 s y repite.**

## 6. Cifras de las pruebas del 12/11

- **Por la API** (`LLM_ORDEN=groq,gemini`, 20 s entre preguntas, guion corregido): 5 de 5 con HTTP 200, todas con `gpt-oss-120b`, de 0,84 a 2,29 s. La fuera de dominio salió bien (`fuera_de_dominio: true`, sin citas).
- **Por modelo de Groq, sin respaldo** (las 5 preguntas y la 4 repetida, 20 s entre cada una): `gpt-oss-120b` respondió las 6 como describe la sección 3. `gpt-oss-20b` respondió bien 5 de 6; **falló la pregunta 1** («No encontré…»). Las preguntas 2, 3, 4 y 5 salieron bien con los dos modelos.
- **Prueba anterior** (`LLM_ORDEN=groq,gemini`, 10 s entre preguntas, 7 preguntas): todas HTTP 200; de 1,2 a 4,8 s, salvo una de 12,8 s por un 429 del primer modelo.
- **Arranque en frío:** 56 s en el ensayo (42 a 64 s en las pruebas).

## 7. Limitaciones que conviene decir

- La vigencia sigue siendo **por artículo**; solo 5 expresiones inexequibles están marcadas a mano.
- El modelo pequeño de respaldo (`gpt-oss-20b`) es menos fiable que el grande: en la pregunta del art. 140 responde «No encontré…».
- No hay frontend ni backend Node conectado todavía: la demo es sobre la API del motor (`/docs`).
- Los planes gratuitos pueden fallar: por eso existen dos proveedores y dos modelos en cada uno.

## 8. Diagramas e informe

Página con los tres diagramas y el informe en PDF: [`docs/diagramas/index.html`](diagramas/index.html). Publicada en GitHub Pages: <https://duvanobando.github.io/policia-rag-chatbot/diagramas/>. El informe en PDF también está en [`docs/entregas/informe_avance.pdf`](entregas/informe_avance.pdf).
