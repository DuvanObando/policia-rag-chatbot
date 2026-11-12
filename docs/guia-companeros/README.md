# Guía para el equipo

Esta carpeta es el punto de partida de **cada integrante**. Todo lo que necesitas para empezar sin preguntarle a nadie está aquí o enlazado desde aquí.

## Cómo usar esta carpeta

1. **Lee este README completo** (10 minutos): qué hay hecho, cómo levantarlo y las reglas que valen para todos.
2. **Abre tu guía personal**: ahí están tu rol, tus tareas con fechas, los archivos que te pertenecen y lo que ya está listo para ti.

| Persona | Rol | Guía |
|---|---|---|
| Wilder | Corpus (Fase 1) y banco de preguntas | [wilder.md](wilder.md) |
| Santiago Castro | Análisis lingüístico (Fase 2) | [santiago-castro.md](santiago-castro.md) |
| Santiago Bulla | Backend, frontend e integración | [santiago-bulla.md](santiago-bulla.md) |
| Duvan | Líder y motor RAG (entregado) | este README |

3. **Cronograma y requisitos del enunciado:** [PLAN_TRABAJO.md](PLAN_TRABAJO.md) (9 al 20 de noviembre de 2026; el día 1 es el lunes 9). Las guías personales copian de ahí tus fechas.
4. Marca tus casillas `[x]` en tu guía cuando termines una tarea (en tu rama, con tu PR).

**El proyecto en tres líneas:** un chatbot web que responde preguntas sobre la **Ley 1801 de 2016 (Código Nacional de Seguridad y Convivencia Ciudadana)** con arquitectura RAG: busca los artículos relevantes, se los da a un LLM (Gemini) y responde **citando artículo, numeral o parágrafo**. Si la respuesta no está en el Código, debe decirlo. El proyecto es para el curso de Procesamiento de Lenguaje Natural (UNIR); se entrega el **viernes 20 de noviembre**.

---

## Estado del motor RAG (entrega de Duvan)

Ya está en `main`, funcionando y documentado. **No hay que esperar a nadie para usarlo.**

### Qué hace

1. Recibe una pregunta en español.
2. **Clasificador temático** (palabras clave): detecta el tema y empuja los resultados de ese tema. Si la pregunta pide «el artículo 163», ese artículo va primero.
3. **Búsqueda híbrida** (por defecto): une la búsqueda *semántica* (embeddings `multilingual-e5-base` + FAISS) con la *léxica* (BM25) mediante Reciprocal Rank Fusion. La consulta léxica se amplía con un **glosario de sinónimos coloquiales** («guaro» → «bebidas alcohólicas»).
4. Toma el **artículo completo** de cada fragmento encontrado y se lo entrega a **Gemini** (`gemini-3.5-flash-lite`, con `gemini-3.6-flash` de respaldo) con un prompt que obliga a responder solo con esos artículos, citar `(Art. 163, num. 2)` y avisar si la vigencia no es «vigente».
5. Verifica las citas (descarta artículos que no estaban en el contexto y numerales o parágrafos que no existen) y marca `fuera_de_dominio` si el modelo dice que no está en el Código.

Tiempo típico por pregunta: **1 a 4 segundos**; en el peor caso (Gemini saturado) unos 21 s.

### Endpoints

Contrato completo y ejemplos: [`docs/api_contract.md`](../api_contract.md). El motor corre en `http://localhost:8000` (el backend es quien lo llama).

| Endpoint | Para qué |
|---|---|
| `GET /health` | Estado del motor. `listo: true` = puede responder. Si es `false`, el campo `error` dice por qué. Muestra el modo de búsqueda activo, el LLM, el número de fragmentos del índice y si la expansión está activa |
| `POST /query` | Entrada `{pregunta, historial?}`. Salida: `respuesta`, `articulos_citados`, `fragmentos`, `fuera_de_dominio` y los opcionales `citas` y `tema_detectado` |
| `POST /upload_pdf/` | Sube un PDF (campo `file`, máx. 10 MB). Lo guarda y lo deja `pendiente_de_indexar`; **no regenera embeddings** (RF4). Para que entre al buscador, Duvan reconstruye el índice con `--incluir-uploads` |

Errores (todos con `{"error": "mensaje en español"}`): **422** entrada inválida, **413** PDF de más de 10 MB, **503** ningún modelo respondió o el motor no está listo («El servicio está ocupado, intenta de nuevo en unos minutos»), **500** error interno.

### Campos de la respuesta de `/query`

| Campo | Qué es |
|---|---|
| `respuesta` | Texto para el usuario, ya con las citas y los avisos de vigencia |
| `articulos_citados` | `["Artículo 140", ...]` |
| `citas` *(opcional)* | Detalle: `{articulo, numeral, paragrafo, texto}` — `texto` es la forma legible, p. ej. `"Art. 163, num. 2"` |
| `fragmentos` | Los fragmentos recuperados: `id`, `ubicacion` (cadena, p. ej. `"Libro II, Título XIV, Capítulo II, Artículo 140"`), `epigrafe`, `texto`, `score`, y los opcionales `vigencia` y `tema` |
| `fuera_de_dominio` | `true` si la pregunta no se puede responder con el Código |
| `tema_detectado` *(opcional)* | Tema que detectó el clasificador, o `"general"` |

`vigencia` puede ser `vigente`, `modificado`, `inexequible`, `exequible_condicionado` o `no_verificada` (documentos subidos). `historial` se acepta pero **el motor todavía no lo usa**.

### Modo de búsqueda por defecto

**Semántico + clasificador temático** (desde el 12/11, con el corpus real; antes era híbrido). Se cambia en el `.env` con `BUSQUEDA_MODO` (`semantico`, `hibrido` o `lexico`); la expansión con glosario (`BUSQUEDA_EXPANSION`) solo actúa en `hibrido` y `lexico`. El corpus se elige con `CORPUS_RUTA` (por defecto el de la Fase 1, `corpus/procesados/corpus_ley_1801.json`). Detalle: [`docs/busqueda_hibrida.md`](../busqueda_hibrida.md) y [`docs/clasificador.md`](../clasificador.md).

### Resultados de las evaluaciones

Todas con el **corpus de muestra de 10 artículos** y 13 a 19 preguntas escritas a mano. Son una primera señal, **no una conclusión**: una pregunta mueve 5 a 8 puntos, y se repetirán con el corpus completo y el banco de 50+ preguntas.

| Evaluación | Comparación | Resultado |
|---|---|---|
| Segmentación ([doc](../segmentacion.md)) | Artículo completo vs. fragmentos de 250 tokens | Acierto@1 0.70 → **0.80**; MRR 0.792 → **0.850**. Gana `fragmentos` (4 de 10 artículos pasan de 512 tokens y se cortan) |
| Clasificador ([doc](../clasificador.md)) | Sin vs. con clasificador (13 preguntas) | Acierto@1 0.69 → **0.77**; Acierto@3 0.85 → **0.92**; MRR 0.808 → **0.865** |
| Modos de búsqueda ([doc](../busqueda_hibrida.md)) | semántico / léxico / híbrido (16 preguntas) | Acierto@1 0.75 / 0.88 / **0.88**; Acierto@3 0.94 / 0.94 / **1.00**; MRR 0.859 / 0.906 / **0.927** |
| Expansión con glosario (mismo doc) | Sin vs. con expansión, híbrido (19 preguntas) | Acierto@1 0.84 → **0.89**; MRR 0.912 → **0.947**; ninguna pregunta empeora |
| Fuera de dominio, LLM real | «pase de conducción», «impuesto predial» | `fuera_de_dominio: true` en ambas |

### Limitaciones conocidas (léelas antes de contar con algo)

- **Corpus:** desde el 12/11 el motor usa el corpus de la Fase 1 (249 artículos), adaptado al cargar por `engine/indexing/cargador_corpus.py`. Las tablas de resultados de arriba son de la muestra de 10 artículos; las del corpus real están en [`docs/busqueda_hibrida.md`](../busqueda_hibrida.md).
- **La vigencia es por artículo, no por numeral.** Hay numerales con apartes inexequibles que el motor no puede distinguir: hoy el chatbot, por ejemplo, cita el art. 140, num. 7 (consumo de bebidas alcohólicas en parques) aunque la fuente marca esos apartes como inexequibles. Mientras tanto, las expresiones inexequibles conocidas se marcan como `[INEXEQUIBLE: ...]` con `corpus/anotaciones_vigencia.json` (hoy 6, del HTML del Senado; Wilder lo completa; ver [wilder.md](wilder.md)).
- **BM25 usa stemming (Snowball), no lematización**, porque spaCy está bloqueado por Windows en el equipo de Duvan (ver [santiago-castro.md](santiago-castro.md)). La rama de spaCy del código **nunca se ha ejecutado**.
- **Glosario de sinónimos y `temas.json` provisionales**, escritos para los 10 artículos de muestra.
- **Documentos subidos por `/upload_pdf/`:** al indexarlos se recuperan, pero todavía no se citan bien en las respuestas.
- **El `score` no es un porcentaje y cambia de escala con el modo de búsqueda** (en híbrido es un puntaje de fusión de ~0.01 a 0.04).
- El plan gratuito de Gemini a veces responde 503/504: el motor reintenta y cambia de modelo, pero con ambos saturados responde 503.
- No hay pruebas automatizadas; `eval/run_eval.py` (evaluación completa con el banco) está pendiente de Duvan.

---

## Cómo levantar el motor

Los pasos completos (entorno virtual, dependencias, `.env`, índices y `uvicorn`) están en la sección **[«Motor RAG (engine/)» del README raíz](../../README.md#motor-rag-engine)**. Resumen:

```bash
python -m venv engine/.venv
engine\.venv\Scripts\activate            # Linux/Mac: source engine/.venv/bin/activate
pip install -r engine/requirements.txt   # pesado (PyTorch): unos 4 minutos
cp .env.example .env                     # y pon tu GEMINI_API_KEY (ver reglas)
python engine/indexing/build_index.py --estrategia articulo
python engine/indexing/build_index.py --estrategia fragmentos
cd engine && uvicorn api:app --port 8000
```

La primera vez se descargan unos 1.1 GB del modelo de embeddings. Comprueba con `http://localhost:8000/health` (`"listo": true`).

**Si algo falla:**

| Síntoma | Causa y solución |
|---|---|
| `listo: false` y `error` dice «Falta GEMINI_API_KEY» | No hay clave en el `.env` de la **raíz** del repo |
| `listo: false` y `error` habla del índice BM25 | Reconstruye los índices (los dos comandos `build_index`) |
| `/query` responde 503 | Gemini saturado; espera un minuto. Si persiste, mira `/health` |
| El puerto 8000 está ocupado | Usa otro: `uvicorn api:app --port 8010` y cambia `MOTOR_URL` en el `.env` |
| Error de DLL / «Control de aplicaciones bloqueó este archivo» | Windows está bloqueando una librería nativa. Ver [santiago-castro.md](santiago-castro.md); **no desactives la protección** |

---

## Reglas comunes para TODOS

1. **Trabaja el repositorio FUERA de OneDrive**, por ejemplo en `C:\dev\policia-rag-chatbot`. OneDrive sincroniza y bloquea miles de archivos del entorno virtual, y las rutas con tildes ya dieron problemas. Clona con `git clone https://github.com/DuvanObando/policia-rag-chatbot.git C:\dev\policia-rag-chatbot`.
2. **Cada uno saca su propia clave gratuita de Gemini** en [Google AI Studio](https://aistudio.google.com/) y la pone en su `.env` local (en la raíz del repo, línea `GEMINI_API_KEY=`). **Nunca se sube a git ni se comparte** (ni por chat, ni por correo, ni en capturas). El `.env` ya está en `.gitignore`; no lo fuerces.
3. **Después de actualizar `main`, reconstruye los índices** (no se versionan):
   ```bash
   python engine/indexing/build_index.py --estrategia articulo
   python engine/indexing/build_index.py --estrategia fragmentos
   ```
   Si no, el motor puede arrancar con `listo: false` o buscar con un índice viejo.
4. **Una rama por persona**, siempre desde `main` actualizado: `git checkout main && git pull`, luego `git checkout -b feature/<nombre>-<bloque>` (por ejemplo `feature/wilder-corpus`). Los cambios entran por **pull request a `main`, que revisa Duvan**. Nada de push directo a `main`.
5. **FAISS en Windows falla con rutas con tildes** (por ejemplo `...Beltrán...`). El código **ya lo evita** (guarda y lee el índice con Python). Si aparece un error raro de ruta, es eso: avisa a Duvan y, de paso, mueve el repo a una ruta sin tildes ni OneDrive.
6. **La evaluación con Gemini gratis se corre con pausas** (8 a 10 s entre preguntas): el plan gratuito tiene límite de peticiones y a veces responde 503. Los scripts ya traen pausas; no las quites.
7. **Privacidad (Ley 1581 de 2012):** no registres en logs ni guardes el texto de las preguntas, las respuestas ni el contenido de los documentos subidos. Aplica al motor, al backend y al frontend.
8. **No subas a git:** `.env`, `engine/.venv/`, los índices (`engine/indexing/indexes/`), `corpus/uploads/` ni PDFs de `docs/`. Ya están en `.gitignore`.
9. **En la sustentación todos deben poder explicar el flujo completo** (corpus → análisis lingüístico → embeddings y FAISS → recuperación y generación → backend y frontend → evaluación), no solo su parte. Leer este README y recorrer el flujo una vez con el motor corriendo es suficiente para empezar.
10. Si cambias un **contrato** (campos de la API, formato del corpus, de `sinonimos.json` o de `temas.json`), avisa antes a Duvan y a quien lo use.
