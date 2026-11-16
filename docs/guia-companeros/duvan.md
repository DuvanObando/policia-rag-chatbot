# Cierre de Duvan: motor RAG

Estado al 16 de noviembre de 2026. El motor RAG, que es mi parte, está **completo en `main`**. Esta página resume qué entregué, qué PR están fusionados, qué queda a cargo de cada compañero y qué haré en las pruebas finales del jueves 19. Calendario completo: [README](README.md#calendario-de-cierre).

## Qué entregué

| Funcionalidad | Dónde está y dónde se explica |
|---|---|
| Búsqueda semántica (embeddings `multilingual-e5-base` + FAISS) con **clasificador temático** y artículo por número | [`engine/retrieval/`](../../engine/retrieval/) · [clasificador.md](../clasificador.md) |
| Búsqueda **léxica y híbrida** (BM25 + Reciprocal Rank Fusion) y expansión con glosario | [busqueda_hibrida.md](../busqueda_hibrida.md) |
| Segmentación: artículo completo o fragmentos de 250 tokens (small-to-big) | [segmentacion.md](../segmentacion.md) |
| Generación con **citas por artículo, numeral y parágrafo**, verificadas contra el texto; aviso de vigencia | [`engine/generation/`](../../engine/generation/) · [api_contract.md](../api_contract.md) |
| **Fuera de dominio:** el motor dice que no está en las normas cargadas | [api_contract.md](../api_contract.md) · [demo_entrega.md](../demo_entrega.md) |
| **Respaldo Groq y Gemini** (`LLM_ORDEN` configurable) | [`.env.example`](../../.env.example) · [README raíz](../../README.md) |
| API: `/health`, `/query`, `/upload_pdf/` | [api_contract.md](../api_contract.md) |
| **Reprocesamiento de normas nuevas** desde un PDF (`/corpus/reprocesar`), incremental, sin reiniciar el motor; corpus con varias normas; regla del «artículo N» (`NORMA_PRINCIPAL`) | [reprocesamiento.md](../reprocesamiento.md) |
| Lectura de PDF con **PyMuPDF** (pypdf de respaldo): subida de 63 s a 0,4 s | [reprocesamiento.md](../reprocesamiento.md#pymupdf-tiempos-antes-y-después-mismo-pdf-56-páginas) |
| Evaluaciones con el corpus real | [busqueda_hibrida.md](../busqueda_hibrida.md) · [informe_avance.md](../informe_avance.md) |
| Informe de avance (y PDF) y **diagramas** | [informe_avance.md](../informe_avance.md) · [diagramas](../diagramas/index.html) · [GitHub Pages](https://duvanobando.github.io/policia-rag-chatbot/diagramas/) |
| Guion y scripts de la demo | [demo_entrega.md](../demo_entrega.md) |
| Guías y plan de trabajo del equipo | [README](README.md) · [PLAN_TRABAJO.md](PLAN_TRABAJO.md) |

## PR fusionados

Mis PR (todos fusionados con merge commit):

| PR | Qué trae |
|---|---|
| [#1](https://github.com/DuvanObando/policia-rag-chatbot/pull/1) | Motor RAG: búsqueda, generación con citas y API real |
| [#2](https://github.com/DuvanObando/policia-rag-chatbot/pull/2) | Clasificador temático, búsqueda híbrida BM25+RRF y expansión con glosario |
| [#3](https://github.com/DuvanObando/policia-rag-chatbot/pull/3) | Guías para compañeros y plan de trabajo |
| [#5](https://github.com/DuvanObando/policia-rag-chatbot/pull/5) | Integración entrega 1: motor + corpus real de la Fase 1 + análisis de Castro |
| [#6](https://github.com/DuvanObando/policia-rag-chatbot/pull/6) | Groq como respaldo entre empresas |
| [#7](https://github.com/DuvanObando/policia-rag-chatbot/pull/7) | `LLM_ORDEN` configurable, guion de demo y README al día |
| [#8](https://github.com/DuvanObando/policia-rag-chatbot/pull/8) | Diagramas del proyecto con Archify |
| [#9](https://github.com/DuvanObando/policia-rag-chatbot/pull/9) | Informe de avance del proyecto |
| [#10](https://github.com/DuvanObando/policia-rag-chatbot/pull/10) | Resultados con el corpus real, regla de idioma y pendientes del informe |
| [#11](https://github.com/DuvanObando/policia-rag-chatbot/pull/11) | Informe de avance en PDF y diagrama Mermaid más claro |
| [#12](https://github.com/DuvanObando/policia-rag-chatbot/pull/12) | Página de entrada de los diagramas y guion de la demo corregido |
| [#13](https://github.com/DuvanObando/policia-rag-chatbot/pull/13) | Scripts de inicio y apagado de la demo y sección «Arranque rápido» |
| [#15](https://github.com/DuvanObando/policia-rag-chatbot/pull/15) | Reprocesamiento del corpus: normas nuevas desde PDF sin reiniciar el motor |
| [#16](https://github.com/DuvanObando/policia-rag-chatbot/pull/16) | PyMuPDF para leer PDF y norma principal para «artículo N» |

Los de mis compañeros que ya están fusionados: [#4](https://github.com/DuvanObando/policia-rag-chatbot/pull/4) (Santiago Castro: análisis lingüístico, Fase 2) y [#14](https://github.com/DuvanObando/policia-rag-chatbot/pull/14) (Santiago Bulla: backend, frontend y Docker).

## Qué queda a cargo de cada compañero

Fecha límite de todos los PR: **miércoles 18 de noviembre**. El detalle de cada uno está en su guía, sección «Nuevo (16/11)».

| Quién | Pendiente | Guía |
|---|---|---|
| **Wilder** | Mejorar `corpus/pipeline/procesar_pdf.py` (a la Ley 769 le faltan los art. 3, 18 y 128 y el 131 sale en un solo bloque), completar `corpus/anotaciones_vigencia.json`, dar la fecha de consulta del corpus para `corpus/README_corpus.md` y pasar el banco de preguntas a `eval/banco_preguntas.json` (trampas variadas, coloquiales, ambiguas y por número de artículo) | [wilder.md](wilder.md) |
| **Santiago Castro** | Subir el glosario de 49 términos a `engine/glossary/sinonimos.json`, alinear `engine/retrieval/temas.json` con el campo `tema` del corpus real (con Wilder) y su parte del informe técnico | [santiago-castro.md](santiago-castro.md) |
| **Santiago Bulla** | Flujo de 3 llamadas en el frontend (subir, reprocesar, consultar estado), token de administrador solo en el backend, reenviar `norma` y `fuente_url`, devolver el `id` de la subida, timeout de 60 s, mostrar las normas de `/health` y su parte del informe (integración y despliegue) | [santiago-bulla.md](santiago-bulla.md) |

## Qué haré en las pruebas finales (jueves 19)

1. **Integrar los PR** de los tres compañeros a `main` (revisión y merge commit), reconstruir los índices con `python engine/indexing/build_index.py --todas` y comprobar `/health`.
2. **Evaluación formal** con el banco de preguntas de Wilder: ejecutar `eval/run_eval.py` (hoy pendiente) sobre el corpus completo y con el glosario real, y analizar por tipo de pregunta (trampas, coloquiales, ambiguas, por número).
3. **Pruebas de punta a punta:** motor, backend y frontend juntos, incluido el flujo de subir y reprocesar una norma (con la Ley 769 de ejemplo: [reprocesamiento.md](../reprocesamiento.md)); al terminar, dejar el corpus solo con la Ley 1801.
4. **Actualizar el informe** ([informe_avance.md](../informe_avance.md)) con los resultados finales y compilar el informe técnico (máximo 15 páginas) con las secciones de cada uno.
5. **Regenerar el PDF y los diagramas** ([docs/diagramas](../diagramas/index.html)) y publicar de nuevo la página de GitHub Pages.
6. Ensayo de la sustentación con todo el equipo.

## Límites conocidos del motor (para el informe)

- La vigencia es por artículo y, en las normas nuevas, sigue en `no_verificada` mientras nadie la revise.
- No hay pruebas automatizadas; la evaluación formal queda para el jueves 19.
- Los trabajos de reprocesamiento viven en memoria (se pierden si el motor se reinicia) y solo corre uno a la vez.
- El plan gratuito de Groq y Gemini limita las peticiones: el motor reintenta y cambia de proveedor, pero con ambos saturados responde 503.
