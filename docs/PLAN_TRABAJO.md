# Plan de trabajo — policia-rag-chatbot

Chatbot RAG sobre la **Ley 1801 de 2016 (Código Nacional de Policía y Convivencia)**.
Equipo: Duvan (líder), Wilder, Santiago Castro, Santiago Bulla.

> Fecha de inicio del plan: **lunes 9 de noviembre de 2026**. Entrega: **viernes 20 de noviembre de 2026**.
> Para cambiar fechas, ajustar la columna "Fecha" de la sección 5 (el resto del documento usa "Día N").

---

## 1. Objetivo y entregables

**Objetivo:** construir un chatbot web con arquitectura RAG que responda preguntas sobre la Ley 1801 de 2016 citando los artículos fuente y que reconozca cuándo una pregunta está fuera del Código.

**Entregables:**

1. Chatbot web funcional (frontend + backend + motor RAG).
2. Corpus en JSON, documentado (`corpus/README_corpus.md`, `docs/segmentacion.md`).
3. Informe de análisis lingüístico (`docs/analisis/`).
4. Repositorio con motor Python (`engine/`), backend Node.js (`backend/`) y frontend (`frontend/`).
5. Banco de **50+ preguntas** con reporte de evaluación (`eval/banco_preguntas.json`, `eval/reporte.md`).
6. Informe técnico, **máximo 15 páginas** (`docs/informe/`).
7. Video de **5 minutos**.
8. Sustentación oral.

## 2. Flujo general

```mermaid
flowchart LR
    A[Corpus<br/>texto oficial + JSON] --> B[Análisis lingüístico<br/>spaCy, n-gramas, glosario]
    B --> C[Embeddings + FAISS]
    A --> C
    C --> D[Recuperación]
    D --> E[Generación<br/>prompt anti-alucinación]
    F[Clasificador temático<br/>fuera de dominio] --> E
    E --> G[API motor<br/>/query /upload_pdf/]
    G --> H[Backend Node.js<br/>proxy + CORS]
    H --> I[Frontend<br/>chat + panel de fuentes]
    G --> J[Evaluación<br/>Precisión@k, Recall@k, MRR, fidelidad, cita]
    J --> K[Documentación<br/>informe, video, sustentación]
```

Contrato de la API (referencia compartida): [api_contract.md](api_contract.md).

## 3. Fases, entregables y peso en la nota

| Fase | Peso | Tareas concretas | Entregable |
|---|---|---|---|
| 1. Corpus | 20 % | Obtener texto oficial; limpiar; segmentar por artículo/parágrafo; definir metadatos (id, ubicación, epígrafe, texto); verificar vigencia y modificaciones (p. ej. Ley 2000 de 2019); documentar origen, fecha de consulta y licencia | Corpus JSON + `README_corpus.md` + `segmentacion.md` |
| 2. Análisis lingüístico | 15 % | Pipeline spaCy; estadísticas de frecuencia; n-gramas; KWIC; glosario jurídico; sinónimos coloquiales (p. ej. "multa" ↔ "comparendo") | Informe de análisis + `engine/glossary/` |
| 3. Motor RAG | 20 % | Embeddings; índice FAISS; recuperación top-k; prompt anti-alucinación; clasificador temático; `/query` y `/upload_pdf/` (sin regenerar embeddings); *(opcional)* búsqueda híbrida BM25 | Motor funcionando detrás de `api.py` |
| 4. Integración y funcionalidad | 15 % | Backend Express como proxy con CORS restringido; frontend de chat con historial y panel de fuentes; aviso legal; `.env`; despliegue de pruebas | Aplicación web de extremo a extremo |
| 5. Evaluación | 15 % | Banco de 50+ preguntas (incluye fuera de dominio); `run_eval.py`; Precisión@k, Recall@k, MRR, fidelidad y cita; análisis de errores | `banco_preguntas.json` + `reporte.md` |
| 6. Documentación y sustentación | 15 % | Informe técnico (≤ 15 págs.); README; video de 5 min; ensayo de sustentación | Informe + video + sustentación |

## 4. Asignación por persona

Un responsable principal por bloque. **Todos deben poder explicar el flujo completo en la sustentación.**

### Duvan — líder (motor RAG e integración)

- **Rama:** `feature/duvan-motor-rag`
- **Le pertenecen:** `engine/indexing/`, `engine/retrieval/`, `engine/generation/`, `engine/api.py`, `engine/requirements.txt`
- **Además:** gestión del repo, revisión de PR y merges a `main`, integración final.

- [ ] Cerrar y publicar el contrato de API (`docs/api_contract.md`) el día 1
- [ ] Crear las ramas de cada integrante el día 1
- [ ] Generar embeddings del corpus (sentence-transformers)
- [ ] Construir y guardar el índice FAISS (`engine/indexing/indexes/`, no versionado)
- [ ] Implementar recuperación top-k con score
- [ ] Prompt anti-alucinación: responder solo con los fragmentos recuperados y citar artículos
- [ ] Clasificador temático / detección de fuera de dominio
- [ ] Implementar `POST /query` real según el contrato
- [ ] Implementar `POST /upload_pdf/` sin regenerar embeddings
- [ ] *(Opcional)* búsqueda híbrida BM25 + FAISS
- [ ] Revisar y mergear los PR de los demás
- [ ] Integración final y pruebas de extremo a extremo
- [ ] Sección "Motor RAG" del informe técnico

### Wilder — corpus y banco de preguntas

- **Rama:** `feature/wilder-corpus`
- **Le pertenecen:** `corpus/`, `docs/segmentacion.md`, `eval/banco_preguntas.json`

- [ ] Obtener el texto oficial de la Ley 1801 de 2016 y registrar origen y fecha de consulta
- [ ] Limpiar el texto (encabezados, numeración de página, ruido de PDF)
- [ ] **Corpus provisional (20 a 30 artículos) entre los días 1 y 2** para desbloquear al resto
- [ ] Definir criterios de segmentación y documentarlos en `docs/segmentacion.md`
- [ ] Definir metadatos por fragmento (`id`, `ubicacion`, `epigrafe`, `texto`)
- [ ] Corpus completo en JSON hacia el **día 4**
- [ ] Verificar vigencia y modificaciones (Ley 2000 de 2019 y otras) y marcarlas en los metadatos
- [ ] Completar `corpus/README_corpus.md` (origen, fecha, criterios, metadatos, licencia)
- [ ] Banco de **50+ preguntas** con `respuesta_referencia` y `articulos_esperados`
- [ ] Incluir preguntas `fuera_de_dominio: true` (al menos 10 recomendado)
- [ ] Sección "Corpus" del informe técnico

### Santiago Castro — análisis lingüístico

- **Rama:** `feature/santiago-castro-linguistica`
- **Le pertenecen:** `engine/preprocess/`, `engine/analysis/`, `engine/glossary/`, `docs/analisis/`

- [ ] Configurar spaCy en español y el pipeline de preprocesamiento
- [ ] Estadísticas del corpus (tokens, vocabulario, frecuencias)
- [ ] N-gramas más frecuentes
- [ ] KWIC (concordancias) de términos clave
- [ ] Glosario de términos jurídicos
- [ ] Sinónimos y expresiones coloquiales para expansión de consultas
- [ ] Probar el análisis con el corpus provisional (días 3 a 4) y rehacerlo con el completo
- [ ] Informe de análisis lingüístico en `docs/analisis/`
- [ ] Sección "Análisis lingüístico" del informe técnico

### Santiago Bulla — backend, frontend y despliegue

- **Rama:** `feature/santiago-bulla-web`
- **Le pertenecen:** `backend/`, `frontend/`, `.env.example`, `README.md`

- [ ] Backend Express como proxy hacia el motor (`/query`, `/upload_pdf`)
- [ ] CORS restringido a `ORIGENES_PERMITIDOS`
- [ ] Manejo de errores cuando el motor no responde
- [ ] Frontend de chat con historial de conversación
- [ ] Panel de fuentes (artículos citados y fragmentos con score)
- [ ] Mostrar el caso `fuera_de_dominio`
- [ ] Aviso legal (el chatbot es informativo, no asesoría jurídica)
- [ ] Trabajar primero con datos simulados del contrato, luego con el motor real
- [ ] Configuración con `.env` (nunca versionado)
- [ ] Despliegue de pruebas
- [ ] Mantener `README.md` actualizado (instalación y ejecución)
- [ ] Sección "Integración / frontend" del informe técnico

## 5. Cronograma de 2 semanas (10 días hábiles)

Fecha de inicio: **2026-11-09** (lunes). Cambiar la columna "Fecha" si se mueve el calendario.

| Día | Fecha | Duvan | Wilder | Santiago Castro | Santiago Bulla | Hito |
|---|---|---|---|---|---|---|
| 1 | Lun 09/11 | Cierra contrato de API; crea ramas; esqueleto de indexación | Texto oficial; inicia corpus provisional | Setup spaCy; diseña el pipeline | Estructura backend y frontend con datos simulados | **Contrato de API cerrado, ramas creadas** |
| 2 | Mar 10/11 | Embeddings sobre el corpus provisional | **Corpus provisional (20–30 art.) entregado**; PR | Preprocesamiento sobre el provisional | Backend proxy + CORS | **Corpus provisional disponible** |
| 3 | Mié 11/11 | Índice FAISS y recuperación top-k | Limpieza y segmentación del corpus completo | Estadísticas y n-gramas | Chat con historial (simulado) | |
| 4 | Jue 12/11 | Prompt anti-alucinación (v1) | **Corpus completo con vigencia verificada** | KWIC y glosario | Panel de fuentes (simulado) | **Corpus completo (día 4)** |
| 5 | Vie 13/11 | Reindexa con el corpus completo; `/query` real | Documenta corpus y segmentación | Sinónimos coloquiales | Aviso legal; `.env` | **Fin de semana 1**: análisis, índice, backend y frontend con simulados |
| 6 | Lun 16/11 | Clasificador temático / fuera de dominio | Banco de preguntas (1ª mitad) | Informe de análisis (borrador) | Conecta frontend con el motor real | |
| 7 | Mar 17/11 | `/upload_pdf/`; ajusta recuperación | Banco de preguntas (completo, 50+) | Integra glosario/sinónimos al motor con Duvan | Pruebas de integración; despliegue de pruebas | **Integración real funcionando** |
| 8 | Mié 18/11 | `run_eval.py`; métricas (P@k, R@k, MRR, fidelidad, cita) | Revisa referencias del banco; apoya evaluación | Cierra informe de análisis | Corrige fallos de UI; README | **Evaluación ejecutada** |
| 9 | Jue 19/11 | Congelamiento: solo correcciones; informe técnico | Informe técnico (corpus y evaluación) | Informe técnico (lingüística) | Video de 5 min; informe técnico (web) | **Congelamiento de funcionalidades** |
| 10 | Vie 20/11 | Ensayo de sustentación; merges finales | Ensayo de sustentación | Ensayo de sustentación | Ensayo de sustentación | **Entrega** |

**Opcional (solo si sobra tiempo):** búsqueda híbrida BM25 + FAISS (Duvan, días 7 a 8). No debe poner en riesgo la evaluación ni el congelamiento del día 9.

## 6. Dependencias y riesgos

**Qué bloquea a quién**

| Bloqueo | Afecta a | Mitigación |
|---|---|---|
| Corpus provisional (día 2) | Duvan (embeddings), Santiago Castro (análisis) | Wilder prioriza 20–30 artículos antes que la limpieza total |
| Corpus completo (día 4) | Reindexado final, banco de preguntas, evaluación | Reindexar el día 5; el pipeline debe ser reproducible con un comando |
| Contrato de API (día 1) | Backend y frontend | Se cierra primero; cualquier cambio se acuerda por PR a `docs/api_contract.md` |
| Motor real (día 5–7) | Integración | Backend y frontend avanzan con datos simulados del contrato |
| Banco de preguntas (día 7) | Evaluación | Wilder empieza el banco el día 6, en paralelo al motor |

**Riesgos**

- **Retraso del corpus.** Se trabaja con el corpus provisional; si el completo no llega al día 4, el sistema se evalúa sobre el subconjunto segmentado y se documenta la limitación en el informe. Duvan decide el día 4 si se recorta el alcance.
- **Preguntas fuera de dominio.** El sistema debe responder que **la información no está en el Código** (`fuera_de_dominio: true`) en lugar de inventar. El banco incluye preguntas fuera de dominio y la evaluación mide cuántas se rechazan correctamente.
- **Vigencia de artículos.** Hay artículos modificados o derogados (p. ej. por la Ley 2000 de 2019). Wilder los marca en los metadatos; el motor no debe citar texto derogado como vigente.
- **Alucinación del LLM.** Prompt restringido a los fragmentos recuperados y verificación de que los artículos citados estén entre los fragmentos.
- **Dependencia de la clave del LLM.** Vive solo en `.env`; si falla, el sistema debe devolver un error claro y no una respuesta inventada.
- **Conflictos de integración.** Cada persona trabaja en carpetas propias; los cambios en archivos compartidos pasan por PR.

## 7. Reglas del equipo

1. **Una rama por persona** (`feature/<nombre>-<bloque>`); no se hace push directo a `main`.
2. Integración mediante **pull request a `main`, revisado por Duvan**.
3. **Las claves solo van en `.env`; nunca se sube `.env`.** Solo se versiona `.env.example` sin valores reales.
4. Commits pequeños y con mensaje claro; un PR por tarea terminada.
5. Cambios al contrato de la API solo por PR y avisando al equipo.
6. Los índices (`engine/indexing/indexes/`) no se versionan; deben poder regenerarse.

## 8. Definición de terminado por entregable

| Entregable | Terminado cuando |
|---|---|
| Corpus JSON | Texto completo segmentado, con metadatos, vigencia verificada, `README_corpus.md` completo y mergeado a `main` |
| Análisis lingüístico | Estadísticas, n-gramas, KWIC, glosario y sinónimos entregados, con informe redactado y reproducible desde `engine/analysis/` |
| Motor RAG | `/query` cumple el contrato, cita artículos, rechaza fuera de dominio; `/upload_pdf/` no regenera embeddings |
| Backend y frontend | Chat funcional con historial y panel de fuentes, CORS restringido, aviso legal, funcionando contra el motor real |
| Banco de preguntas | 50+ preguntas con respuesta de referencia y artículos esperados, con casos fuera de dominio |
| Evaluación | `run_eval.py` ejecuta y `reporte.md` contiene Precisión@k, Recall@k, MRR, fidelidad y cita, con análisis de errores |
| Informe técnico | ≤ 15 páginas, cubre todas las fases, revisado por los cuatro |
| Video | 5 min, muestra el flujo completo y una pregunta fuera de dominio |
| Sustentación | Los cuatro pueden explicar el flujo completo de extremo a extremo |
| Repositorio | `main` con todo mergeado por PR, README con instalación y ejecución, ningún `.env` versionado |
