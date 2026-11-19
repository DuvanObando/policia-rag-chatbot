# Demo de la entrega final (20/11)

Guion para mostrar el chatbot completo: **frontend y backend de Santiago Bulla + motor RAG**, sobre la Ley 1801 de 2016 (249 artículos, 471 fragmentos), con la carga en vivo de la Ley 769 de 2002 (Código de Tránsito). Verificado de punta a punta el 19/11 con el entorno virtual (`venv` + `uvicorn`); **Docker no se probó en el PC de Duvan** (ver la guía de traspaso, sección 9).

Instalación desde cero en otro PC: [`guia-companeros/traspaso-santiago-castro.md`](guia-companeros/traspaso-santiago-castro.md).

**Reglas de oro**

- **Deja 15 a 20 s entre preguntas** (límites gratuitos de Groq y Gemini). Si sale «El servicio está ocupado» (503), espera 30 s y repite.
- Arranca todo **unos 2 minutos antes** y no cierres las ventanas.
- No hagas otra cosa pesada en el PC durante la demo (la carga de la Ley 769 usa toda la CPU; el 19/11, con Docker Desktop abierto y poca RAM, la carga tardó 19 min en vez de 6).

## 1. Arrancar

Doble clic en [`iniciar_todo.bat`](../iniciar_todo.bat) (raíz del repo). Abre tres ventanas («Motor Chatbot RAG», «Backend Chatbot RAG», «Frontend Chatbot RAG»), espera a que el motor diga `listo` (unos 50 s en el PC de Duvan, que tiene el repo en OneDrive) y abre <http://localhost:5173>. Para apagar todo: [`detener_todo.bat`](../detener_todo.bat).

`iniciar_demo.bat` y `detener_demo.bat` siguen sirviendo para arrancar **solo el motor** (Swagger en <http://localhost:8000/docs>).

`.env` recomendado (raíz): `LLM_ORDEN=groq,gemini`, `LLM_GROQ_MODELO=openai/gpt-oss-120b,openai/gpt-oss-20b`, `BUSQUEDA_MODO=semantico`, `TEMAS_PROPUESTA=1`, `ADMIN_TOKEN` y `ADMIN_CLAVE` propios.

> **Sobre `gpt-oss-20b`:** el 12/11 la demo dejó solo el 120b porque el 20b respondía mal la pregunta del licor. El 19/11 el 120b agotó su límite gratuito después de muchas pruebas (429 con espera de 10 min) y Gemini respondió 504 por tiempo: con solo el 120b el chat devolvía 503. Con el 20b de respaldo el chat siguió respondiendo (y respondió bien las preguntas de la Ley 769). Si en la sustentación una respuesta del licor sale «No encontré…», es el 20b: espera 30 s y repite.

## 2. Guion (unos 8 minutos)

### 2.1 Como usuario: preguntas indirectas (2 min)

En la pantalla inicial, **Entrar como usuario**. Verificadas el 19/11 por la API y por el frontend:

| Pregunta | Qué sale | Qué mostrar |
|---|---|---|
| ¿Me pueden multar por tomar licor en el parque? | Art. 140, num. 7: esa parte fue declarada **inexequible** (C-253 de 2019), ya no sirve de base para una multa | En el panel, el art. 140 con la etiqueta amarilla de vigencia «vigente modificado con inexequibilidad parcial» |
| Un policía me pidió la cédula, ¿estoy obligado a mostrarla? | Art. 35, num. 3: resistirse al procedimiento de identificación es un comportamiento contrario a la convivencia | El tema detectado («Tranquilidad y relaciones respetuosas», de la propuesta de Santiago Castro). Antes del 19/11 esta pregunta salía mal (ver sección 4) |
| ¿Me pueden llevar a la estación si estoy borracho en la calle? | Art. 155 (traslado por protección), literal D | Vigencia «vigente modificado condicionado» |
| ¿Qué pasa si me cuelo en TransMilenio? | Art. 146 | — |

### 2.2 Fuera de dominio (30 s)

«**Me detuvieron por conducir mi moto borracho, ¿me pueden multar?**» → «No encontré esa información en las normas cargadas: Ley 1801 de 2016 (…)». El frontend la marca «Fuera del Código» y el panel avisa que los fragmentos no están relacionados. Explica: es **tránsito** (Ley 769), y no está cargada.

### 2.3 Cargar la Ley 769 en vivo (unos 6 a 7 minutos de espera)

Antes de la sustentación, descarga el PDF oficial: <https://www.funcionpublica.gov.co/eva/gestornormativo/norma_pdf.php?i=5557> (56 páginas).

1. **Salir** → **Administrador** con la `ADMIN_CLAVE` del `.env` → pestaña **Administración**.
2. **Agregar una norma**: el PDF, norma `Ley 769 de 2002` y la URL oficial. Botón **Agregar norma**.
3. El PDF se guarda sin tocar las consultas (RF4) y la barra avanza: extrayendo (menos de 1 s con PyMuPDF) → indexando (≈ 30 % y 60 %) → **listo**.
4. **Mientras carga, vuelve a Chat y haz una pregunta de la Ley 1801**: el chat sigue respondiendo con los índices anteriores (más lento, porque la CPU está calculando embeddings). Aprovecha la espera para explicar la arquitectura con la [página de diagramas](https://duvanobando.github.io/policia-rag-chatbot/diagramas/).
5. Al terminar, la cabecera dice «Normas cargadas: Ley 1801 de 2016 · Ley 769 de 2002». Repite la pregunta de la moto: ahora **cita la Ley 769 de 2002, Artículo 131** (multas). También funcionan «¿Qué pasa si conduzco borracho?» (arts. 131, 149 y 152) y «¿Cuánto es la multa por no portar la licencia de conducción?» (art. 131, B.1: 8 SMDLV).

**Plan B (si no hay tiempo para esperar):** cargarla antes, con el motor apagado: `engine\.venv\Scripts\python engine/indexing/reprocesar.py --json corpus/procesados/ley_769_de_2002.json`, y en vivo mostrar solo la pregunta de la moto.

**Después de la demo**, con el motor apagado, deja solo la Ley 1801: `engine\.venv\Scripts\python engine/indexing/reprocesar.py --quitar "Ley 769 de 2002"`.

### 2.4 Cierre (1 min)

Métricas de la evaluación formal ([`eval/reporte.md`](../eval/reporte.md)) y limitaciones (sección 5).

## 3. Medido el 19/11 (PC de Duvan, CPU, repo en OneDrive)

| Prueba | Resultado |
|---|---|
| 10 preguntas indirectas por la API (20 s de pausa) | 9 de 9 de la Ley 1801 responden con el artículo esperado; la de la moto, fuera de dominio. De 1,8 a 7,7 s |
| Las mismas por el backend de Bulla (la ruta del frontend) | Mismos artículos; 3 respondieron 504 porque en ese momento corría una evaluación pesada en el mismo PC (el backend corta a los 30 s). Repetidas sin carga, bien |
| Carga de la Ley 769 por la pantalla de Administración | Subida y extracción en menos de 1 s; trabajo `listo` con 167 artículos y 315 fragmentos nuevos. El chat siguió respondiendo durante la carga: 18 de 23 preguntas con HTTP 200 (de 4,8 a 28,8 s, con la CPU ocupada y poca RAM libre), más la que se hizo desde el frontend; 4 respondieron 503 (límite de Groq agotado y Gemini sin responder a tiempo) y 1 respondió 504 (más de 30 s) |
| Después de la carga | Moto → Ley 769, art. 131; licencia → art. 131, B.1; «conduzco borracho» → arts. 131, 149 y 152 |
| Volver a solo la Ley 1801 (`--quitar`) | 0,4 s; índices idénticos al respaldo (mismos vectores, ids y BM25) |

## 4. Qué cambió el 19/11 y por qué

- **Temas de Santiago Castro.** El corpus trae el mismo `tema` en los 249 artículos, así que el clasificador temático no empujaba nada. Se aplicó la propuesta de Castro (32 temas por rangos de artículos) **sin editar el corpus**, en el cargador. Con eso la pregunta de la cédula encuentra el art. 35 (antes no aparecía en los 10 primeros). Resultados: [`resultados_temas.md`](resultados_temas.md).
- **Analogías.** Con solo la Ley 1801, el modelo respondía la pregunta de la moto con el art. 146, num. 6 (comer en el transporte público). El prompt prohíbe ahora aplicar un artículo a una conducta distinta (regla 4b), sin dejar de aceptar que la gente pregunte con sus palabras («cédula» = identificación).
- **Artículos enormes.** El art. 131 de la Ley 769 tiene 28.000 caracteres; al LLM se le manda un extracto. Ahora el extracto son los trozos de ese artículo **más parecidos a la pregunta** (antes, el trozo encontrado y sus vecinos, y en la pregunta de la moto el modelo no veía la parte de embriaguez).

## 5. Limitaciones que conviene decir

- La vigencia es **por artículo** (salvo 6 expresiones inexequibles marcadas a mano); la Ley 769 queda con vigencia «no verificada».
- La extracción de la Ley 769 es básica (pendiente de Wilder): faltan los arts. 3, 18 y 128 y el art. 131 queda en un solo bloque.
- Los planes gratuitos de Groq y Gemini limitan las peticiones: con muchas pruebas seguidas aparecen 429 y 503.
- El historial de la conversación se muestra, pero el motor responde cada pregunta por separado.

## 6. Diagramas e informe

Página con los diagramas y el informe en PDF: [`docs/diagramas/index.html`](diagramas/index.html), publicada en <https://duvanobando.github.io/policia-rag-chatbot/diagramas/>. Informe: [`docs/informe_avance.md`](informe_avance.md) y [`docs/entregas/informe_avance.pdf`](entregas/informe_avance.pdf).
