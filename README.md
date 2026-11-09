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

Abre `.env` (en la **raíz** del repo, no en `engine/`) y completa `GEMINI_API_KEY=` con tu clave de [Google AI Studio](https://aistudio.google.com/) (plan gratuito). No pegues la clave en el chat ni la subas a git: `.env` está ignorado. `LLM_MODELO` y `LLM_MODELO_RESPALDO` ya traen valores; si un modelo da 503 con frecuencia, cámbialos ahí. `BUSQUEDA_MODO` elige el tipo de búsqueda: `hibrido` (recomendado y por defecto), `semantico` o `lexico`; detalle en [docs/busqueda_hibrida.md](docs/busqueda_hibrida.md).

**3. Construir los índices** (los índices no se versionan; hay que generarlos)

```bash
python engine/indexing/build_index.py --estrategia articulo
python engine/indexing/build_index.py --estrategia fragmentos
```

- Cada comando también construye el índice léxico BM25 (`bm25_tokens.json`). **Si actualizas desde una versión anterior, reconstruye los índices.**
- `articulo`: un vector por artículo completo (el modelo corta lo que pase de 512 tokens).
- `fragmentos`: trozos de 250 tokens con 50 de solapamiento (`--tamano`, `--solape`). **Es la estrategia que usa el motor.**
- Se guardan en `engine/indexing/indexes/<estrategia>/`. Repite el comando cuando cambie el corpus.
- Corpus por defecto: `corpus/muestra/codigo_muestra.json` (10 artículos, **provisional**; ver `corpus/muestra/README.md`). Para otro corpus: `--corpus RUTA`.

**4. Arrancar el motor** (desde `engine/`)

```bash
cd engine
uvicorn api:app --port 8000
```

Carga el modelo y los índices al arrancar (unos 10 a 15 s). Evita `--reload`: recarga el modelo en cada cambio de código. Comprueba que esté listo:

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

- El corpus es una **muestra provisional de 10 artículos**; será reemplazado por el de la Fase 1.
- La **vigencia es por artículo**, no por numeral: no se sabe qué partes de un artículo modificado son inexequibles. El motor avisa que conviene verificar en la fuente oficial.
- Los **documentos complementarios** subidos aún no se citan bien en las respuestas (el extractor de citas solo entiende «Art. N»).
- El plan gratuito de Gemini a veces responde 503/504; el motor reintenta y pasa al modelo de respaldo, y si ambos fallan devuelve 503.

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
