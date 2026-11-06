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

## Instalación

```bash
cp .env.example .env   # completar valores; nunca se versiona
```

**Motor (Python):**

```bash
cd engine
python -m venv .venv
.venv\Scripts\activate      # Linux/Mac: source .venv/bin/activate
pip install -r requirements.txt
```

**Backend (Node):**

```bash
cd backend && npm install
```

**Frontend:** pendiente (placeholder).

## Ejecución

```bash
# Motor (puerto 8000)
cd engine && uvicorn api:app --reload --port 8000
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
