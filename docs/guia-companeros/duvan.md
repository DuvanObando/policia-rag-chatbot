# Cierre de Duvan: motor RAG

**Mi parte quedó CERRADA el jueves 19 de noviembre de 2026.** El motor RAG está completo en `main`, integrado con el frontend y el backend de Santiago Bulla y con la Fase 2 de Santiago Castro, verificado de punta a punta y evaluado. Para la sustentación del viernes 20, Santiago Castro hace correr el proyecto en su PC con la [guía de traspaso](traspaso-santiago-castro.md).

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
| **19/11:** temas de Castro en el clasificador, corrección de las preguntas indirectas, extracto de artículos enormes, evaluación formal | [resultados_temas.md](../resultados_temas.md) · [`eval/reporte.md`](../../eval/reporte.md) · [demo_entrega.md](../demo_entrega.md) |
| **19/11:** arranque con un clic y traspaso | `iniciar_todo.bat` · `detener_todo.bat` · [traspaso-santiago-castro.md](traspaso-santiago-castro.md) |

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
| [#17](https://github.com/DuvanObando/policia-rag-chatbot/pull/17) | Cierre de Duvan en las guías: calendario, mensajes y duvan.md |
| [#19](https://github.com/DuvanObando/policia-rag-chatbot/pull/19) | **Entrega final (19/11):** integra el PR #18 de Bulla y la rama de Castro, temas de Castro en el clasificador, correcciones de las preguntas indirectas, evaluación formal, documentos y traspaso |

Los de mis compañeros que ya están fusionados: [#4](https://github.com/DuvanObando/policia-rag-chatbot/pull/4) (Santiago Castro: análisis lingüístico, Fase 2), [#14](https://github.com/DuvanObando/policia-rag-chatbot/pull/14) y [#18](https://github.com/DuvanObando/policia-rag-chatbot/pull/18) (Santiago Bulla: backend, frontend con administración del corpus y Docker; el #18 entró con el #19), y la rama `feature/santiago-castro-linguistica` de Santiago Castro (glosario de 49 términos, informe, entidades y propuesta de temas; no abrió PR, entró con el #19).

## Qué entregué el 19/11 (cierre)

1. **Integración:** la rama de Castro y el PR #18 de Bulla, sin conflictos ni cambios de contrato. Ninguna clave quedó en el repositorio (revisados los 59 commits del historial); `ADMIN_TOKEN` y `ADMIN_CLAVE` se leen del `.env` de la raíz (motor, backend y Docker) y están vacíos en `.env.example`.
2. **Verificación de punta a punta** con el entorno virtual: motor, backend y frontend; chat, panel de fragmentos, vigencia y pantalla de Administración (401 con una clave equivocada). Docker no se probó en mi PC (queda como alternativa en la guía de traspaso).
3. **Preguntas indirectas:** había dos errores reales (la de la cédula salía fuera de dominio por la búsqueda; la de la moto aplicaba un artículo por analogía). Corregidos con los temas de Castro y la regla 4b del prompt: 9 de 9 responden con el artículo esperado y la de la moto sale fuera de dominio.
4. **Temas de Castro** aplicados en el clasificador sin editar el corpus: MRR de 0,805 a 0,863 en 68 preguntas, sin que ningún grupo empeore ([resultados_temas.md](../resultados_temas.md)).
5. **Demostración de la Ley 769** por la pantalla de Administración: fuera de dominio antes, cita la Ley 769 después, el chat siguió respondiendo durante la carga y el corpus quedó solo con la Ley 1801 (índices idénticos al respaldo). Para la pregunta de la moto se mejoró el extracto de los artículos enormes.
6. **Evaluación formal (Fase 6):** `eval/run_eval.py` completo y [`eval/reporte.md`](../../eval/reporte.md):

| Métrica (60 preguntas: banco de Wilder adaptado + 10 indirectas) | Valor |
   |---|---|
   | Recall@3 / MRR | 0,942 / 0,908 |
   | Exactitud de fuera de dominio | 0,933 |
   | Corrección de la cita / cita exacta | 0,935 / 0,783 |
   | Precisión@3 | 0,333 (techo con un artículo esperado y 3 entregados) |

   Con el `gpt-oss-120b` agotado, respondieron el `gpt-oss-20b` y Gemini; los errores se concentran ahí.

7. **Documentos:** informe ([informe_avance.md](../informe_avance.md) y su PDF), guion de la demo, clasificador, resultados de las comparaciones ([`docs/resultados_19nov/`](../resultados_19nov/README.md)), guía de traspaso y este cierre.

## Qué queda a cargo de cada compañero

Estado al 19/11 (la fecha límite de los PR era el miércoles 18).

| Quién | Pendiente | Guía |
|---|---|---|
| **Wilder** (no entregó nada desde el 16/11) | Mejorar `corpus/pipeline/procesar_pdf.py` (a la Ley 769 le faltan los art. 3, 18 y 128 y el 131 sale en un solo bloque), completar `corpus/anotaciones_vigencia.json`, dar la fecha de consulta del corpus para `corpus/README_corpus.md` y pasar el banco de preguntas a `eval/banco_preguntas.json` (trampas variadas, coloquiales, ambiguas y por número de artículo) | [wilder.md](wilder.md) |
| **Santiago Castro** | Glosario y temas entregados e integrados el 19/11. Pendiente: hacer correr todo en su PC para la sustentación y verificar Docker ([traspaso](traspaso-santiago-castro.md)) | [santiago-castro.md](santiago-castro.md) |
| **Santiago Bulla** | Frontend y backend del reprocesamiento entregados e integrados el 19/11 (PR #18). Pendiente: su sección del informe técnico (integración y despliegue) y el video de 5 minutos | [santiago-bulla.md](santiago-bulla.md) |

## Límites conocidos del motor (para el informe)

- La vigencia es por artículo y, en las normas nuevas, sigue en `no_verificada` mientras nadie la revise.
- No hay pruebas automatizadas de código; la evaluación formal usa el banco anterior de Wilder adaptado, porque el oficial (`eval/banco_preguntas.json`) está vacío.
- La extracción de normas nuevas es básica (pendiente de Wilder): en la Ley 769 el art. 131 queda en un bloque de 28.000 caracteres y al LLM se le manda un extracto.
- Los trabajos de reprocesamiento viven en memoria (se pierden si el motor se reinicia) y solo corre uno a la vez.
- El plan gratuito de Groq y Gemini limita las peticiones: el motor reintenta y cambia de proveedor, pero con ambos saturados responde 503.
