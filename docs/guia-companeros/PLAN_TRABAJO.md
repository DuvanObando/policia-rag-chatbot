# Plan de trabajo — policia-rag-chatbot

Chatbot RAG sobre la **Ley 1801 de 2016 (Código Nacional de Seguridad y Convivencia Ciudadana, "Código Nacional de Policía")**.
Equipo: Duvan (líder), Wilder, Santiago Castro, Santiago Bulla.

> **Estado actual:** el bloque de Duvan (motor RAG: embeddings, FAISS, búsqueda híbrida, clasificador, generación con citas, API y `/upload_pdf/`) **ya está entregado y fusionado a `main`**, antes de lo que marca el cronograma. Su estado detallado, las reglas comunes y las guías por persona están en el [README de esta carpeta](README.md). Las casillas `[ ]` de Duvan en este plan no se actualizaron.

> Fecha de inicio del plan: **lunes 9 de noviembre de 2026**. Entrega: **viernes 20 de noviembre de 2026**.
> Para cambiar fechas, ajustar la columna "Fecha" de la sección 5 (el resto del documento usa "Día N").
>
> Fuente de requisitos: enunciado oficial del proyecto (UNIR, *Procesamiento de Lenguaje Natural / Lingüística Computacional*, docente Armando Ricardo Medina Nieto). La sección 11 traza cada requisito a tarea, responsable y día.

---

## 1. Objetivo y entregables

**Objetivo general (enunciado):** diseñar e implementar un chatbot que responda preguntas en lenguaje natural sobre el Código, a partir de un corpus lingüístico estructurado y anotado y de una arquitectura RAG, citando los artículos que fundamentan cada respuesta y minimizando las alucinaciones.

**Alcance incluido:** corpus del texto vigente con sus modificaciones identificadas; preguntas en español sobre comportamientos contrarios a la convivencia, medidas correctivas, multas, autoridades, procedimientos y derechos; respuestas con cita de artículo, parágrafo o numeral; interfaz web de chat y API de consulta documentada.

**Fuera de alcance:** asesoría jurídica personalizada; normas distintas al Código (solo como corpus complementario si el equipo lo justifica por escrito; por defecto la jurisprudencia se usa únicamente como metadato de vigencia); integración con sistemas de la Policía Nacional o el Registro Nacional de Medidas Correctivas.

**Entregables:**

1. **Corpus** del Código en JSON, con un documento que describe origen, fecha de consulta, criterios de segmentación, metadatos y licencia de uso (`corpus/`, `corpus/README_corpus.md`, `docs/segmentacion.md`).
2. **Informe de análisis lingüístico** con estadísticas, frecuencias, concordancias y glosario (`docs/analisis/`).
3. **Repositorio Git** con el motor documental (Python), el backend (Node.js) y el frontend, más un README con instalación y ejecución.
4. **Banco de preguntas (50+)** y **reporte de evaluación** con métricas y análisis de errores (`eval/`).
5. **Informe técnico final (máximo 15 páginas)** y **video demostrativo de 5 minutos**.
6. **Sustentación oral.**

## 2. Flujo general

```mermaid
flowchart LR
    A[Corpus<br/>fuentes oficiales, limpieza,<br/>segmentación regex, metadatos] --> B[Análisis lingüístico<br/>spaCy/Stanza, POS, NER,<br/>n-gramas, KWIC, glosario]
    B --> C[Embeddings + FAISS<br/>2 estrategias de segmentación]
    A --> C
    C --> D[Recuperación top-k<br/>+ BM25 opcional]
    F[Clasificador temático<br/>libro / título] --> D
    D --> E[Generación<br/>prompt: solo contexto, cita,<br/>declara si no está en el Código]
    E --> G[API motor<br/>/query /upload_pdf/]
    G --> H[Backend Node.js<br/>proxy + CORS]
    H --> I[Frontend<br/>chat, historial, fuentes, aviso legal]
    G --> J[Evaluación<br/>P@k, R@k, MRR, exactitud,<br/>fidelidad, cita, errores]
    J --> K[Documentación<br/>informe, video, sustentación]
```

Contrato de la API (referencia compartida): [api_contract.md](../api_contract.md).

## 3. Fases, entregables y peso en la nota

Pesos tomados del enunciado (criterios de evaluación, total 100 %).

| Fase | Peso | Tareas concretas (según el enunciado) | Entregable |
|---|---|---|---|
| 1. Corpus lingüístico | 20 % | Recopilar el texto oficial y vigente desde fuentes oficiales (Secretaría del Senado, SUIN-Juriscol o Función Pública) y **registrar la fecha de consulta**; identificar modificaciones (Ley 2000 de 2019) y **sentencias de la Corte Constitucional** (inexequibilidad o exequibilidad condicionada); limpiar (encabezados, pies de página, numeración, notas editoriales, caracteres corruptos); **segmentar por libro, título, capítulo, artículo, parágrafo y numeral con expresiones regulares**; metadatos: **id, ubicación jerárquica, epígrafe, vigencia y tema** | Corpus JSON + `README_corpus.md` (origen, fecha, segmentación, metadatos, licencia) + `segmentacion.md` |
| 2. Análisis lingüístico | 15 % | Normalizar, tokenizar y lematizar con **spaCy (`es_core_news`) o Stanza**; **POS** y **NER** (autoridades, lugares, montos, plazos); estadísticas (nº de artículos, tokens, tipos, relación tipo/token, longitud media por fragmento); frecuencias, **n-gramas, colocaciones y KWIC** de «multa», «comparendo», «medida correctiva», «espacio público»; **glosario** jurídico y **sinónimos coloquiales** (p. ej. «comparendo» ↔ «orden de comparendo», «multa general tipo 2») | Informe de análisis lingüístico + `engine/glossary/` |
| 3. Representación vectorial e indexación | (dentro de Motor RAG, 20 %) | **Seleccionar y justificar el modelo de embeddings** (sentence-transformers multilingüe u OpenAI); generar embeddings e **índice FAISS**; **comparar al menos dos estrategias de segmentación** (artículo completo vs. tamaño fijo con solapamiento) y documentar el efecto en la recuperación | Índice FAISS reproducible + sección de justificación y comparación en el informe |
| 4. Recuperación y generación (RAG) | Motor RAG 20 % | Búsqueda semántica de los **k fragmentos** más relevantes (opcional: híbrido con **BM25**); **prompt** que obligue a responder solo con el contexto, citar artículos y declarar cuando no está en el Código; **clasificador temático** (palabras clave o modelo) que oriente la búsqueda hacia el libro o título | Motor funcionando detrás de `engine/api.py` |
| 5. Interfaz y despliegue | Integración y funcionalidad 15 % | Frontend de chat con **historial** y **visualización de las fuentes citadas**; **aviso visible** de herramienta informativa; credenciales en **`.env`**; **despliegue en entorno de pruebas** | Aplicación web de extremo a extremo |
| 6. Evaluación | 15 % | Banco de **50+ preguntas** con respuesta de referencia y artículos esperados, **incluidas preguntas trampa fuera de dominio** (tránsito, impuestos); recuperación: **Precisión@k, Recall@k, MRR**; respuesta: **exactitud, fidelidad al contexto, corrección de la cita**; **análisis de errores** y mejoras | `banco_preguntas.json` + `reporte.md` |
| Transversal: documentación y sustentación | 15 % | Informe técnico (≤ 15 págs.), README, video de 5 min, defensa oral | Informe + video + sustentación |

Resumen de pesos: corpus 20 % · análisis lingüístico 15 % · motor RAG 20 % (fases 3 y 4) · integración y funcionalidad 15 % · evaluación 15 % · documentación y sustentación 15 %.

## 4. Asignación por persona

Un responsable principal por bloque. **Todos deben poder explicar el flujo completo en la sustentación.**

### Duvan — líder (embeddings, FAISS, motor RAG e integración)

- **Rama:** `feature/duvan-motor-rag`
- **Le pertenecen:** `engine/indexing/`, `engine/retrieval/`, `engine/generation/`, `engine/api.py`, `engine/requirements.txt`, `eval/run_eval.py`, `eval/reporte.md`
- **Además:** gestión del repo, revisión de PR y merges a `main`, integración final, compilación del informe técnico.

- [ ] Cerrar y publicar el contrato de API (`docs/api_contract.md`) el día 1
- [ ] Crear las ramas de cada integrante el día 1
- [ ] **Seleccionar y justificar el modelo de embeddings** (alternativas, criterio, costo/latencia) por escrito
- [ ] Generar embeddings de los fragmentos y construir el **índice FAISS** (`engine/indexing/indexes/`, no versionado)
- [ ] **Estrategia A:** un fragmento por artículo completo
- [ ] **Estrategia B:** fragmentos de tamaño fijo con solapamiento
- [ ] **Comparar A vs. B** con el banco de preguntas y documentar el efecto en la recuperación (tabla en el informe)
- [ ] Búsqueda semántica top-k con score
- [ ] Prompt: responder **solo con el contexto recuperado**, **citar artículos** y **declarar que no está en el Código** cuando corresponda
- [ ] **Clasificador temático** (palabras clave o modelo) que oriente la búsqueda hacia el libro o título
- [ ] `POST /query` real según el contrato (RF1, RF2, RF3)
- [ ] `POST /upload_pdf/` que **no regenera embeddings** automáticamente (RF4)
- [ ] Medir el tiempo de respuesta y mantenerlo **< 10 s** en el entorno de pruebas (RNF1)
- [ ] *(Opcional)* búsqueda híbrida BM25 + FAISS
- [ ] `run_eval.py`: Precisión@k, Recall@k, MRR, exactitud, fidelidad al contexto y corrección de la cita
- [ ] Análisis de errores y mejoras propuestas (con Wilder)
- [ ] Análisis de **sesgos y riesgos** de respuestas incorrectas (sección del informe)
- [ ] Revisar y mergear los PR de los demás
- [ ] Compilar el **informe técnico (≤ 15 págs.)** y verificar que no pase el límite
- [ ] Integración final y pruebas de extremo a extremo

### Wilder — corpus y banco de preguntas

- **Rama:** `feature/wilder-corpus`
- **Le pertenecen:** `corpus/` (incluidos los scripts de limpieza y segmentación), `docs/segmentacion.md`, `eval/banco_preguntas.json`

- [ ] Obtener el texto de la Ley 1801 de 2016 de una **fuente oficial** (Secretaría del Senado, SUIN-Juriscol o Función Pública) y **registrar la fecha de consulta**
- [ ] **Limpiar** el texto: encabezados, pies de página, numeración de páginas, notas editoriales y caracteres corruptos
- [ ] **Segmentar con expresiones regulares** por libro, título, capítulo, artículo, parágrafo y numeral
- [ ] **Corpus provisional (20 a 30 artículos) entre los días 1 y 2** para desbloquear al resto
- [ ] Definir **metadatos** por fragmento: `id`, `ubicacion` (jerarquía), `epigrafe`, `vigencia`, `tema`
- [ ] Identificar **modificaciones** posteriores (Ley 2000 de 2019 y otras) y marcarlas en `vigencia`
- [ ] Identificar **sentencias de la Corte Constitucional** con inexequibilidad o exequibilidad condicionada y anotarlas en `vigencia`
- [ ] **Verificar vigencia de cada artículo** antes de incluirlo en el corpus
- [ ] Corpus completo en JSON hacia el **día 4**
- [ ] Documento de origen: `corpus/README_corpus.md` con origen, fecha de consulta, criterios de segmentación, metadatos y **licencia de uso**
- [ ] Documentar la segmentación (reglas regex y casos borde) en `docs/segmentacion.md`
- [ ] Banco de **50+ preguntas** con `respuesta_referencia` y `articulos_esperados`, partiendo de las 10 preguntas de ejemplo del enunciado
- [ ] Incluir **preguntas trampa / fuera de dominio** (tránsito, impuestos, etc.), al menos 10
- [ ] Apoyar la revisión manual de exactitud, fidelidad y cita, y el análisis de errores (día 8)
- [ ] Sección "Corpus" del informe técnico

### Santiago Castro — análisis lingüístico

- **Rama:** `feature/santiago-castro-linguistica`
- **Le pertenecen:** `engine/preprocess/`, `engine/analysis/`, `engine/glossary/`, `docs/analisis/`

- [ ] Configurar **spaCy (`es_core_news`) o Stanza** y justificar la elección
- [ ] Normalizar, **tokenizar y lematizar** el corpus (empezar con el provisional)
- [ ] **POS** y **NER**: autoridades, lugares, montos y plazos
- [ ] **Estadísticas:** número de artículos, tokens, tipos, relación tipo/token y longitud media por fragmento
- [ ] **Frecuencias, n-gramas, colocaciones y KWIC** de «multa», «comparendo», «medida correctiva» y «espacio público»
- [ ] **Glosario** de términos jurídicos
- [ ] **Sinónimos coloquiales** (p. ej. «comparendo» ↔ «orden de comparendo», «multa general tipo 2») para expandir consultas
- [ ] Rehacer el análisis con el corpus completo (a partir del día 4)
- [ ] Entregar a Duvan el glosario y los sinónimos en un formato consumible por el motor (día 7)
- [ ] **Informe de análisis lingüístico** en `docs/analisis/` (estadísticas, frecuencias, concordancias y glosario)
- [ ] Sección "Análisis lingüístico" del informe técnico

### Santiago Bulla — backend, frontend, despliegue y protección de datos

- **Rama:** `feature/santiago-bulla-web`
- **Le pertenecen:** `backend/`, `frontend/`, `.env.example`, `README.md`

- [ ] Backend Express como proxy hacia el motor (`/query`, `/upload_pdf`)
- [ ] **CORS restringido** a `ORIGENES_PERMITIDOS` (RNF3)
- [ ] Manejo de errores cuando el motor no responde
- [ ] Frontend de chat con **historial de conversación**
- [ ] **Visualización de las fuentes citadas** (artículos y fragmentos recuperados, con score) (RF5), mostrando la **vigencia** de cada fragmento (con señal visible si no es `vigente`) y el `tema`
- [ ] Mostrar el caso `fuera_de_dominio`
- [ ] **Aviso visible** de que es una herramienta informativa y no sustituye la asesoría jurídica
- [ ] Claves y configuración en **`.env`**; solo `.env.example` en Git (RNF2)
- [ ] **Ley 1581 de 2012:** no almacenar datos personales de usuarios sin consentimiento informado (historial solo en la sesión del navegador, sin guardar preguntas en servidor ni en logs)
- [ ] Trabajar primero con datos simulados del contrato, luego con el motor real
- [ ] **Despliegue en entorno de pruebas**
- [ ] Reproducibilidad: `package.json` completo y README con instalación y ejecución (RNF4)
- [ ] Guion y grabación del **video de 5 minutos**
- [ ] Sección "Integración / frontend" del informe técnico

## 5. Cronograma de 2 semanas (10 días hábiles)

Fecha de inicio: **2026-11-09** (lunes). Cambiar la columna "Fecha" si se mueve el calendario.

| Día | Fecha | Duvan | Wilder | Santiago Castro | Santiago Bulla | Hito |
|---|---|---|---|---|---|---|
| 1 | Lun 09/11 | Cierra contrato de API; crea ramas; esqueleto de indexación | Fuentes oficiales y fecha de consulta; inicia corpus provisional | Setup spaCy/Stanza; diseña el pipeline | Estructura backend y frontend con datos simulados | **Contrato de API cerrado, ramas creadas** |
| 2 | Mar 10/11 | Justifica el modelo de embeddings; embeddings del corpus provisional | **Corpus provisional (20–30 art.) entregado** con metadatos; PR | Normalización, tokenización y lematización sobre el provisional | Backend proxy + CORS | **Corpus provisional disponible** |
| 3 | Mié 11/11 | Índice FAISS y recuperación top-k | Limpieza y segmentación regex del corpus completo | POS, NER y estadísticas | Chat con historial (simulado) | |
| 4 | Jue 12/11 | Prompt anti-alucinación (v1) | **Corpus completo con vigencia verificada**, Ley 2000 y sentencias C.C. | Frecuencias, n-gramas, colocaciones y KWIC | Panel de fuentes (simulado) | **Corpus completo (día 4)** |
| 5 | Vie 13/11 | Reindexa con corpus completo (estrategias A y B); `/query` real | Documento de origen/licencia y `segmentacion.md` | Glosario y sinónimos coloquiales | Aviso legal; `.env`; revisión Ley 1581 del diseño | **Fin de semana 1**: análisis, índice, backend y frontend con simulados |
| 6 | Lun 16/11 | Clasificador temático; ajuste del prompt | Banco de preguntas (1ª mitad, parte de las 10 del enunciado) | Informe de análisis (borrador) | Conecta frontend con el motor real | |
| 7 | Mar 17/11 | `/upload_pdf/`; mide tiempo de respuesta (< 10 s); integra glosario | Banco de preguntas completo (50+), con preguntas trampa | Entrega glosario/sinónimos al motor | Pruebas de integración; **despliegue de pruebas** | **Integración real funcionando** |
| 8 | Mié 18/11 | `run_eval.py`; métricas; **comparación A vs. B** documentada | Revisa referencias; revisión manual de exactitud/fidelidad/cita | Cierra informe de análisis | Corrige UI; README y `package.json`; revisión Ley 1581 | **Evaluación ejecutada** |
| 9 | Jue 19/11 | Congelamiento; análisis de errores, sesgos y riesgos; compila informe técnico | Informe técnico (corpus y evaluación) | Informe técnico (lingüística) | Video de 5 min; informe técnico (web) | **Congelamiento de funcionalidades** |
| 10 | Vie 20/11 | Ensayo de sustentación; merges finales; verifica ≤ 15 págs. | Ensayo de sustentación | Ensayo de sustentación | Ensayo de sustentación | **Entrega** |

**Opcional (solo si sobra tiempo):** búsqueda híbrida BM25 + FAISS (Duvan, días 7 a 8). No debe poner en riesgo la evaluación ni el congelamiento del día 9.

## 6. Dependencias y riesgos

**Qué bloquea a quién**

| Bloqueo | Afecta a | Mitigación |
|---|---|---|
| Corpus provisional (día 2) | Duvan (embeddings), Castro (análisis) | Wilder prioriza 20–30 artículos antes que la limpieza total |
| Corpus completo (día 4) | Reindexado, banco de preguntas, evaluación | Reindexar el día 5; el pipeline debe reproducirse con un comando |
| Contrato de API (día 1) | Backend y frontend | Se cierra primero; cambios por PR a `docs/api_contract.md` |
| Motor real (días 5–7) | Integración | Backend y frontend avanzan con datos simulados del contrato |
| Banco de preguntas (día 7) | Evaluación y comparación A vs. B | Wilder empieza el banco el día 6; con las 10 preguntas del enunciado Duvan puede probar antes |
| Glosario/sinónimos (día 7) | Expansión de consultas en el motor | Castro entrega una primera lista el día 5 |

**Riesgos**

- **Retraso del corpus.** Se trabaja con el provisional; si el completo no llega al día 4, se evalúa sobre el subconjunto segmentado y se documenta la limitación. Duvan decide el día 4 si se recorta el alcance.
- **Preguntas fuera de dominio.** El sistema debe decir que la información **no está en el Código** (`fuera_de_dominio: true`) y no inventar (RF3). El banco incluye preguntas trampa (tránsito, impuestos) y se mide cuántas se rechazan bien.
- **Vigencia de artículos.** Hay artículos modificados, derogados o con inexequibilidad total o condicionada (Ley 2000 de 2019; sentencias de la Corte Constitucional). Wilder los marca en `vigencia`; el motor no debe presentar texto inexequible como vigente.
- **Alucinación del LLM.** Prompt restringido al contexto y verificación de que los artículos citados estén entre los fragmentos recuperados.
- **Latencia (RNF1).** Respuesta < 10 s: limitar k, tamaño de contexto y usar modelo de embeddings ligero; medir en el entorno de pruebas el día 7.
- **Datos personales (Ley 1581 de 2012).** Las preguntas de los usuarios pueden contener datos personales; no se persisten sin consentimiento informado.
- **Dependencia de la clave del LLM.** Vive solo en `.env`; si falla, el sistema devuelve un error claro y no una respuesta inventada.
- **Duración del enunciado.** El enunciado indica 3 semanas y el plan usa 2 (9 al 20 de noviembre, decisión del equipo). Confirmar la fecha oficial de entrega con el docente; si hay más tiempo, el margen se usa en evaluación y análisis de errores.
- **Campos `vigencia` y `tema` en la API (resuelto).** El contrato ya los incluye como campos opcionales de cada elemento de `fragmentos` (`vigencia`: `vigente | modificado | inexequible | exequible_condicionado`). Los valores salen de los metadatos del corpus (Fase 1, Wilder) y el frontend (Santiago Bulla) debe mostrar la vigencia en el panel de fuentes. Las respuestas simuladas de `engine/api.py` ya usan el formato final.
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
| Corpus JSON | Texto de fuente oficial, limpio, segmentado por libro/título/capítulo/artículo/parágrafo/numeral, con metadatos (`id`, `ubicacion`, `epigrafe`, `vigencia`, `tema`), modificaciones y sentencias C.C. marcadas, y `README_corpus.md` con origen, fecha de consulta, criterios, metadatos y licencia; mergeado a `main` |
| Informe de análisis lingüístico | Incluye estadísticas (artículos, tokens, tipos, tipo/token, longitud media), frecuencias, n-gramas, colocaciones, KWIC de los cuatro términos, POS/NER y glosario con sinónimos; reproducible desde `engine/analysis/` |
| Motor RAG | Modelo de embeddings justificado; índice FAISS reproducible; comparación A vs. B documentada; `/query` cumple el contrato, cita artículos y rechaza fuera de dominio; `/upload_pdf/` no regenera embeddings; respuesta < 10 s |
| Backend y frontend | Chat con historial y panel de fuentes, aviso legal visible, CORS restringido, `.env`, desplegado en entorno de pruebas y funcionando contra el motor real |
| Banco de preguntas | 50+ preguntas con respuesta de referencia y artículos esperados, incluidas preguntas trampa fuera de dominio |
| Reporte de evaluación | `run_eval.py` ejecuta; `reporte.md` tiene Precisión@k, Recall@k, MRR, exactitud, fidelidad y corrección de la cita, más análisis de errores y mejoras |
| Informe técnico | ≤ 15 páginas, cubre todas las fases, ética, sesgos y riesgos; revisado por los cuatro |
| Video | 5 min, muestra el flujo completo y una pregunta fuera de dominio |
| Sustentación | Los cuatro pueden explicar el flujo completo de extremo a extremo |
| Repositorio | `main` con todo mergeado por PR, README con instalación y ejecución, `requirements.txt` y `package.json` completos, ningún `.env` versionado |

## 9. Requisitos del enunciado (RF y RNF)

| Código | Requisito | Cómo se cumple | Responsable |
|---|---|---|---|
| RF1 | Recibe preguntas en lenguaje natural y responde en español claro | `/query` + prompt en español | Duvan |
| RF2 | Cada respuesta cita los artículos que la sustentan | Prompt con citación obligatoria; verificación contra los fragmentos | Duvan |
| RF3 | Si no puede responderse con el corpus, lo indica y no inventa | Prompt + `fuera_de_dominio` + preguntas trampa en el banco | Duvan (banco: Wilder) |
| RF4 | `POST /upload_pdf/` sin regenerar automáticamente los embeddings | Endpoint solo recibe y guarda el archivo | Duvan |
| RF5 | La interfaz muestra los fragmentos recuperados | Panel de fuentes en el frontend | Santiago Bulla |
| RNF1 | Respuesta < 10 s por consulta en el entorno de pruebas | Medición el día 7 y ajuste de k y contexto | Duvan |
| RNF2 | Claves en variables de entorno, nunca en el repositorio | `.env` en `.gitignore`; solo `.env.example` | Santiago Bulla |
| RNF3 | El backend restringe orígenes con CORS | `ORIGENES_PERMITIDOS` | Santiago Bulla |
| RNF4 | Git, documentado y reproducible con `requirements.txt` y `package.json` | README + dependencias completas | Santiago Bulla (motor: Duvan) |

## 10. Consideraciones éticas y legales

| Punto del enunciado | Acción | Responsable | Día |
|---|---|---|---|
| Herramienta informativa y educativa; no reemplaza abogado ni a las autoridades | Aviso visible en el frontend y mención en el README | Santiago Bulla | 5 |
| Verificar vigencia y modificaciones de cada artículo antes de incluirlo | Campo `vigencia` + revisión artículo por artículo | Wilder | 4 |
| No almacenar datos personales sin consentimiento informado (Ley 1581 de 2012) | Historial solo en la sesión del navegador; sin guardar preguntas en servidor ni logs; revisión final | Santiago Bulla | 5 y 8 |
| Analizar sesgos y riesgos de respuestas incorrectas en un dominio sensible | Sección en el informe técnico con casos del análisis de errores | Duvan (con Wilder) | 9 |

## 11. Trazabilidad: requisito del enunciado → tarea → responsable → día

| Requisito del enunciado | Tarea | Responsable | Día |
|---|---|---|---|
| F1: fuentes oficiales y fecha de consulta | Obtener texto de Senado / SUIN-Juriscol / Función Pública y registrar fecha | Wilder | 1 (documentado en 5) |
| F1: modificaciones (Ley 2000 de 2019) | Identificar y marcar en `vigencia` | Wilder | 4 |
| F1: sentencias de la Corte Constitucional | Anotar inexequibilidad / exequibilidad condicionada | Wilder | 4 |
| F1: limpieza del texto | Quitar encabezados, pies, numeración, notas editoriales, caracteres corruptos | Wilder | 2 (provisional), 3 (completo) |
| F1: segmentación con regex | Libro, título, capítulo, artículo, parágrafo, numeral | Wilder | 2 (provisional), 3 (completo) |
| F1: metadatos | `id`, `ubicacion`, `epigrafe`, `vigencia`, `tema` | Wilder | 2 (esquema), 4 (completos) |
| F2: spaCy o Stanza; normalizar, tokenizar, lematizar | Pipeline de preprocesamiento | Santiago Castro | 1–2 |
| F2: POS y NER | Autoridades, lugares, montos, plazos | Santiago Castro | 3 |
| F2: estadísticas | Artículos, tokens, tipos, tipo/token, longitud media | Santiago Castro | 3 |
| F2: n-gramas, colocaciones, KWIC | «multa», «comparendo», «medida correctiva», «espacio público» | Santiago Castro | 4 |
| F2: glosario y sinónimos coloquiales | Glosario jurídico y lista de sinónimos | Santiago Castro | 5 (entrega al motor: 7) |
| F3: justificar el modelo de embeddings | Documento de decisión | Duvan | 2 |
| F3: embeddings e índice FAISS | Construcción y guardado del índice | Duvan | 3 (completo: 5) |
| F3: comparar ≥ 2 estrategias de segmentación | Artículo completo vs. tamaño fijo con solapamiento; resultados documentados | Duvan | 5 (índices), 8 (comparación) |
| F4: top-k (BM25 híbrido opcional) | Recuperación semántica; BM25 solo si sobra tiempo | Duvan | 3 (BM25: 7–8, opcional) |
| F4: prompt (solo contexto, cita, declara si no está) | Prompt anti-alucinación | Duvan | 4 (v1), 6 (ajuste) |
| F4: clasificador temático | Orienta la búsqueda al libro o título | Duvan | 6 |
| F5: historial | Chat con historial de conversación | Santiago Bulla | 3 |
| F5: visualización de fuentes | Panel de fragmentos citados | Santiago Bulla | 4 |
| F5: aviso visible | Aviso de herramienta informativa | Santiago Bulla | 5 |
| F5: `.env` | Variables de entorno y `.env.example` | Santiago Bulla | 5 |
| F5: despliegue en entorno de pruebas | Despliegue y pruebas | Santiago Bulla | 7 |
| F6: banco de 50+ preguntas | Preguntas con respuesta de referencia y artículos esperados | Wilder | 6–7 |
| F6: preguntas trampa fuera de dominio | Tránsito, impuestos, etc. (≥ 10) | Wilder | 6–7 |
| F6: Precisión@k, Recall@k, MRR | `run_eval.py` | Duvan | 8 |
| F6: exactitud, fidelidad, corrección de la cita | Métricas y revisión manual | Duvan (revisión: Wilder) | 8 |
| F6: análisis de errores y mejoras | Errores frecuentes y propuestas | Duvan y Wilder | 8–9 |
| RF1, RF2, RF3 | `/query` real con prompt y `fuera_de_dominio` | Duvan | 5–6 |
| RF4 | `/upload_pdf/` sin regenerar embeddings | Duvan | 7 |
| RF5 | Panel de fuentes | Santiago Bulla | 4 |
| RNF1 | Medir y mantener < 10 s | Duvan | 7 |
| RNF2 | `.env` fuera de Git | Santiago Bulla | 5 |
| RNF3 | CORS restringido | Santiago Bulla | 2 |
| RNF4 | README, `requirements.txt`, `package.json` | Santiago Bulla (motor: Duvan) | 8 |
| Ética: herramienta informativa | Aviso legal | Santiago Bulla | 5 |
| Ética: verificar vigencia | Campo `vigencia` | Wilder | 4 |
| Ética: Ley 1581 de 2012 | Sin datos personales sin consentimiento | Santiago Bulla | 5, 8 |
| Ética: sesgos y riesgos | Sección en el informe técnico | Duvan | 9 |
| Entregable 1: corpus JSON + documento de origen y licencia | `corpus/` + `README_corpus.md` | Wilder | 4–5 |
| Entregable 2: informe de análisis lingüístico | `docs/analisis/` | Santiago Castro | 6–8 |
| Entregable 3: repo con motor, backend, frontend y README | Integración y README | Duvan y Santiago Bulla | 8–10 |
| Entregable 4: banco y reporte de evaluación | `eval/` | Wilder (banco) y Duvan (reporte) | 7–8 |
| Entregable 5: informe técnico ≤ 15 págs. y video de 5 min | Informe compilado por Duvan; video por Santiago Bulla | Duvan y Santiago Bulla | 9 |
| Entregable 6: sustentación oral | Ensayo con los cuatro | Todos | 10 |
