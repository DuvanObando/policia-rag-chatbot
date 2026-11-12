# policia-rag-chatbot

Chatbot RAG sobre la **Ley 1801 de 2016 (Código Nacional de Policía y Convivencia)**.

## Estructura

```
corpus/      Texto de la ley y README_corpus.md
engine/      Motor Python (FastAPI): preprocess, analysis, indexing, retrieval, generation, glossary
backend/     Node.js + Express: proxy hacia el motor
frontend/    Interfaz (placeholder)
eval/        Banco de preguntas y evaluación
docs/        Contrato de API, análisis, informe, segmentación
```

Contrato de la API: [docs/api_contract.md](docs/api_contract.md)

## Extraer el corpus documental

Guarda los PDF de la Ley 1801, sus normas modificatorias y decretos en
`corpus/documentos/`. Desde la raíz del repositorio, ejecuta:

```powershell
.\engine\.venv\Scripts\python.exe corpus\construir_corpus.py
```

El proceso deja los textos extraídos por página y el JSON segmentado en
`corpus/procesados/`. Conserva las reformas como disposiciones separadas y no
afirma que el resultado sea una consolidación legal vigente. Criterios, campos
generados y revisión manual: [corpus/README_corpus.md](corpus/README_corpus.md).

## Motor RAG (engine/)

Búsqueda semántica (FAISS + `intfloat/multilingual-e5-base`) sobre la ley, respuesta con Gemini y citas por artículo, numeral o parágrafo. Requiere **Python 3.10+**. Todos los comandos se ejecutan **desde la raíz del repo**, salvo `uvicorn`.

**1. Entorno virtual e instalación de dependencias**

```bash
python -m venv engine/.venv
engine\.venv\Scripts\activate        # Linux/Mac: source engine/.venv/bin/activate
pip install -r engine/requirements.txt
```

Para la búsqueda léxica (BM25) se lematiza con spaCy. Descarga el modelo del español (una vez, con el entorno activado):

```bash
python -m spacy download es_core_news_sm
```

Si spaCy no se puede cargar (por ejemplo, Windows con «Control de aplicaciones» bloqueando una de sus extensiones), el motor usa **automáticamente** un stemmer de respaldo (Snowball) y funciona igual, con una preparación de texto algo más burda; el índice guarda cuál método se usó.

La instalación es pesada (incluye PyTorch). La primera vez que se usa el modelo de embeddings, se descargan unos **1.1 GB** de Hugging Face (queda en caché); aparece un aviso sobre `HF_TOKEN` que se puede ignorar.

**2. Variables de entorno (`.env`)**

```bash
cp .env.example .env
```

Abre `.env` (en la **raíz** del repo, no en `engine/`) y completa `GEMINI_API_KEY=` con tu clave de [Google AI Studio](https://aistudio.google.com/) (plan gratuito). No pegues la clave en el chat ni la subas a git: `.env` está ignorado. `LLM_MODELO` y `LLM_MODELO_RESPALDO` ya traen valores; si un modelo da 503 con frecuencia, cámbialos ahí. `BUSQUEDA_MODO` elige el tipo de búsqueda: `semantico` (por defecto desde el 12/11, gana con el corpus real), `hibrido` o `lexico`; detalle en [docs/busqueda_hibrida.md](docs/busqueda_hibrida.md). `BUSQUEDA_EXPANSION=1` (por defecto) activa la expansión de consultas con el glosario `engine/glossary/sinonimos.json` (provisional; solo afecta a la búsqueda léxica).

**Respaldo entre empresas (Groq) y orden de proveedores:** con `GROQ_API_KEY` (gratis en [console.groq.com](https://console.groq.com/)), si los dos modelos de Gemini fallan responde Groq (`LLM_GROQ_MODELO`, por defecto `openai/gpt-oss-120b,openai/gpt-oss-20b`). `LLM_ORDEN=groq,gemini` prueba Groq primero; `gemini,groq` o vacía, Gemini primero. `/health` muestra el orden activo (`llm_orden`).

**Corpus que se indexa:** `CORPUS_RUTA` en el `.env` (por defecto `corpus/procesados/corpus_ley_1801.json`, el corpus de la Fase 1; la muestra de 10 artículos sigue en `corpus/muestra/codigo_muestra.json`). El cargador `engine/indexing/cargador_corpus.py` adapta el formato de la Fase 1 al esquema del motor sin modificar el archivo. `CORPUS_INCLUIR_REFORMAS=1` indexa también los registros de las normas que modifican la ley.

**3. Construir los índices** (los índices no se versionan; hay que generarlos)

```bash
python engine/indexing/build_index.py --estrategia articulo
python engine/indexing/build_index.py --estrategia fragmentos
```

- Cada comando también construye el índice léxico BM25 (`bm25_tokens.json`). **Si actualizas desde una versión anterior, reconstruye los índices.**
- `articulo`: un vector por artículo completo (el modelo corta lo que pase de 512 tokens).
- `fragmentos`: trozos de 250 tokens con 50 de solapamiento (`--tamano`, `--solape`). **Es la estrategia que usa el motor.**
- Se guardan en `engine/indexing/indexes/<estrategia>/`. Repite el comando cuando cambie el corpus.
- Corpus por defecto: el de `CORPUS_RUTA` (corpus de la Fase 1, 249 artículos). Para otro corpus: `--corpus RUTA`. Construir `articulo` tarda unos 10 min y `fragmentos` unos 7 min en CPU.

**4. Arrancar el motor** (desde `engine/`)

```bash
cd engine
uvicorn api:app --port 8000
```

Carga el modelo y los índices al arrancar (unos 20 s con el corpus real). Evita `--reload`: recarga el modelo en cada cambio de código. Comprueba que esté listo:

```bash
curl http://localhost:8000/health
```

`"listo": true` indica que puede responder. Si dice `false`, el campo `error` explica por qué (normalmente falta `GEMINI_API_KEY`). Detalle de `POST /query`, `GET /health` y `POST /upload_pdf/` en [docs/api_contract.md](docs/api_contract.md).

**5. Probar desde la terminal (sin API)**

```bash
python engine/retrieval/search.py "¿Qué pasa si no pago una multa?"     # solo búsqueda
python engine/generation/responder.py --demo --pausa 8                    # 5 preguntas con el LLM
python eval/comparar_segmentacion.py                                      # compara articulo vs fragmentos
```

**Clasificador temático:** el motor detecta el tema de la pregunta por palabras clave y empuja el orden de la búsqueda hacia ese tema. Los temas y las palabras clave están en `engine/retrieval/temas.json`: se amplían editando ese archivo, sin tocar Python (hay que reiniciar el motor). Detalle y resultados en [docs/clasificador.md](docs/clasificador.md).

**Subir documentos (`POST /upload_pdf/`)**: guarda el PDF y lo deja `pendiente_de_indexar`; **no** regenera los embeddings (RF4). Para que entre al buscador hay que reconstruir el índice a mano y reiniciar el motor:

```bash
python engine/indexing/build_index.py --estrategia fragmentos --incluir-uploads
```

Repite `--incluir-uploads` en cada reconstrucción o los documentos salen del índice.

**Privacidad (Ley 1581 de 2012):** el motor no registra en logs el texto de las preguntas, las respuestas ni los documentos.

**Limitaciones conocidas**

- La **vigencia es por artículo**, no por numeral. Las expresiones inexequibles conocidas se marcan como `[INEXEQUIBLE: ...]` con `corpus/anotaciones_vigencia.json` (hoy 5); el resto, el motor avisa que conviene verificar en la fuente oficial.
- Los **documentos complementarios** subidos aún no se citan bien en las respuestas (el extractor de citas solo entiende «Art. N»).
- El plan gratuito de Gemini a veces responde 503/504 y el de Groq limita los tokens por minuto (429): el motor reintenta, pasa al modelo de respaldo y al otro proveedor, y si todos fallan devuelve 503. Deja unos segundos entre preguntas.

## Instalación (resto del proyecto)

**Backend (Node):**

```bash
cd backend && npm install
```

**Frontend:** pendiente (placeholder).

## Ejecución

```bash
# Motor (puerto 8000); ver la sección "Motor RAG (engine/)"
cd engine && uvicorn api:app --port 8000
```

```bash
# Backend (puerto PORT, por defecto 4000)
cd backend && npm run dev
```

```bash
# Evaluación
python eval/run_eval.py
```

## Reparto de responsabilidades

| Persona | Rol | Carpetas |
|---|---|---|
| A | Corpus | `corpus/`, `docs/segmentacion.md` |
| B | Lingüística | `engine/preprocess/`, `engine/analysis/`, `engine/glossary/`, `docs/analisis/` |
| C | Motor RAG | `engine/indexing/`, `engine/retrieval/`, `engine/generation/`, `engine/api.py` |
| D | Integración | `backend/`, `frontend/`, `eval/`, `docs/informe/` |

## Flujo de trabajo

Cada persona trabaja en su **propia rama** (p. ej. `feat/corpus`, `feat/motor`) y se integra a `main` mediante **pull request**. No se hace push directo a `main`.
