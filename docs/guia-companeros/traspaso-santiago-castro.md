# Traspaso a Santiago Castro: hacer correr todo en tu PC para la sustentación

Duvan cerró su parte el jueves 19/11. Esta guía es para que **tú, solo**, tengas el chatbot completo (motor, backend y frontend) corriendo en tu PC para la sustentación del **viernes 20**, incluida la demostración de cargar la Ley 769 en vivo. Síguela en orden.

> **Qué está verificado:** la forma **principal** (entorno virtual de Python + `uvicorn`) se probó de punta a punta el 19/11 en el PC de Duvan: motor, backend y frontend de Santiago Bulla, chat, panel de fuentes, vigencia, pantalla de Administración y carga de la Ley 769. **Docker NO se probó en el PC de Duvan**: es la forma alternativa y tienes que verificarla tú (sección 9).

## Tiempo total

Unos **45 a 60 minutos** la primera vez (la mayor parte es esperar descargas e índices). Después, arrancar todo toma **menos de 1 minuto**.

| Paso | Tiempo aproximado |
|---|---|
| 1. Clonar el repo | 1 min |
| 2. Claves y `.env` | 10 min |
| 3. Entorno de Python e instalación | 5 a 10 min (descarga PyTorch) |
| 4. Índices | 10 a 15 min (la primera vez baja también el modelo de embeddings, ~1.1 GB) |
| 5. Backend y frontend (`npm install`) | 2 a 4 min |
| 6. Arrancar y probar | 2 min |

## 1. Clonar el repo FUERA de OneDrive

OneDrive bloquea archivos del entorno virtual y las rutas con tildes dan problemas con FAISS. Usa una carpeta corta, por ejemplo `C:\dev`:

```bash
git clone https://github.com/DuvanObando/policia-rag-chatbot.git C:\dev\policia-rag-chatbot
```

```bash
cd C:\dev\policia-rag-chatbot
```

Necesitas **Python 3.11 o 3.12** (`python --version`), **Node 18 o más** (`node --version`) y Git.

## 2. Claves y archivo `.env`

Copia la plantilla (en la raíz del repo):

```bash
copy .env.example .env
```

Abre `.env` con un editor y completa:

1. **`GEMINI_API_KEY`**: tu clave gratuita de Google AI Studio (<https://aistudio.google.com/>, botón «Get API key»).
2. **`GROQ_API_KEY`**: tu clave gratuita de Groq (<https://console.groq.com/keys>). Es el proveedor principal: responde en 1 a 4 s.
3. **`ADMIN_TOKEN`** y **`ADMIN_CLAVE`**: créalos **tú**, nuevos y distintos entre sí. **No reutilices los que circularon por WhatsApp.** Genera cada uno con:

   ```bash
   python -c "import secrets; print(secrets.token_urlsafe(32))"
   ```

   - `ADMIN_TOKEN`: lo usa el backend para hablar con el motor. Nadie lo escribe a mano.
   - `ADMIN_CLAVE`: es la clave que escribes en la pantalla «Administrador» del chatbot. Si prefieres una más corta para escribirla en la sustentación, usa al menos 12 caracteres (`python -c "import secrets; print(secrets.token_urlsafe(12))"`).

4. Revisa que queden así estas variables (el resto, como viene en `.env.example`):

   ```
   LLM_ORDEN=groq,gemini
   LLM_GROQ_MODELO=openai/gpt-oss-120b,openai/gpt-oss-20b
   CORPUS_RUTA=corpus/procesados/corpus_ley_1801.json
   BUSQUEDA_MODO=semantico
   TEMAS_PROPUESTA=1
   NORMA_PRINCIPAL=Ley 1801 de 2016
   ORIGENES_PERMITIDOS=http://localhost:5173,http://localhost:3000
   MOTOR_URL=http://localhost:8000
   PORT=4000
   ```

**Un solo `.env` para todo:** el motor, el backend y el Docker leen el `.env` de la **raíz**. No crees `backend/.env`. El `.env` nunca se sube a git (ya está en `.gitignore`) ni se comparte.

## 3. Entorno de Python del motor (forma PRINCIPAL)

```bash
python -m venv engine\.venv
```

```bash
engine\.venv\Scripts\python -m pip install -r engine/requirements.txt
```

Tarda 5 a 10 minutos (PyTorch es pesado). Si Windows te muestra «Control de aplicaciones bloqueó este archivo», **no desactives la protección**: avísale al grupo (el motor usa Snowball, no necesita spaCy).

## 4. Índices (no se versionan: hay que construirlos)

```bash
engine\.venv\Scripts\python engine/indexing/build_index.py --todas --sin-adicionales
```

Construye las dos estrategias (`articulo` y `fragmentos`) solo con la Ley 1801. La primera vez descarga el modelo de embeddings (~1.1 GB). Al final imprime `fragmentos: 249` para el índice `articulo` y `fragmentos: 471` para `fragmentos`, y «normas adicionales: ninguna (solo Ley 1801)».

## 5. Backend y frontend de Santiago Bulla

```bash
cd backend
npm install
cd ..\frontend
npm install
cd ..
```

## 6. Arrancar todo y probar

**Con un clic:** doble clic en **`iniciar_todo.bat`** (raíz del repo). Abre tres ventanas («Motor Chatbot RAG», «Backend Chatbot RAG» y «Frontend Chatbot RAG»), espera a que el motor esté listo y abre el navegador en <http://localhost:5173>. **No cierres esas ventanas durante la demo.** Para apagar todo: **`detener_todo.bat`**.

**A mano** (tres terminales, desde la raíz):

```bash
cd engine && .venv\Scripts\uvicorn api:app --port 8000
```

```bash
cd backend && npm run start
```

```bash
cd frontend && npm run dev
```

Comprueba:

1. <http://localhost:8000/health> dice `"listo": true` y `normas` solo con la Ley 1801 (249 artículos).
2. En <http://localhost:5173>, **Entrar como usuario** y pregunta «¿Me pueden multar por tomar licor en el parque?»: debe citar el Art. 140 y avisar que esa parte fue declarada inexequible.
3. **Salir** → **Administrador** con tu `ADMIN_CLAVE` → pestaña **Administración**: debe listar la Ley 1801 con 249 artículos.

## 7. Guion de la demo (unos 8 minutos)

Detalle y alternativas en [`docs/demo_entrega.md`](../demo_entrega.md).

1. **Qué es** (30 s): chatbot RAG sobre la Ley 1801 de 2016; responde solo con artículos del corpus y cita artículo, numeral o parágrafo.
2. **Preguntas indirectas** (2 min), como usuario. Deja unos segundos entre preguntas (límites gratuitos):
   - «¿Me pueden multar por tomar licor en el parque?» → Art. 140, num. 7, con el aviso de inexequibilidad.
   - «Un policía me pidió la cédula, ¿estoy obligado a mostrarla?» → Art. 35, num. 3.
   - «¿Me pueden llevar a la estación si estoy borracho en la calle?» → Art. 155 (traslado por protección).
   - Muestra el **panel de fragmentos** (derecha): ubicación, vigencia y tema.
3. **Fuera de dominio** (30 s): «Me detuvieron por conducir mi moto borracho, ¿me pueden multar?» → «No encontré esa información en las normas cargadas: Ley 1801…». Explica que es tránsito (Ley 769) y que **no está cargada**.
4. **Carga de la Ley 769 en vivo** (unos 7 min de espera; mientras tanto explica la arquitectura con la [página de diagramas](https://duvanobando.github.io/policia-rag-chatbot/diagramas/)):
   1. Salir → **Administrador** → pestaña **Administración**.
   2. **Agregar una norma**: PDF de la Ley 769 (descárgalo antes de la sustentación de la Función Pública: <https://www.funcionpublica.gov.co/eva/gestornormativo/norma_pdf.php?i=5557>), norma `Ley 769 de 2002`, URL oficial la misma.
   3. La barra avanza: en cola → extrayendo (menos de 1 s) → indexando (unos 6 min en CPU) → **listo**.
   4. **Mientras carga, el chat sigue respondiendo**: vuelve a la pestaña Chat y haz una pregunta de la Ley 1801.
   5. Al terminar, repite la pregunta de la moto: ahora cita la **Ley 769 de 2002, Artículo 131** (multas). También sirven «¿Qué pasa si conduzco borracho?» (arts. 131, 149 y 152) y «¿Cuánto es la multa por no portar la licencia de conducción?» (art. 131, B.1).
5. **Cierre** (1 min): métricas de la evaluación ([`eval/reporte.md`](../../eval/reporte.md)) y limitaciones (vigencia por artículo, la Ley 769 queda con vigencia «no verificada»).

**Después de la demo**, deja el corpus solo con la Ley 1801 (con el motor apagado):

```bash
engine\.venv\Scripts\python engine/indexing/reprocesar.py --quitar "Ley 769 de 2002"
```

Si no tienes tiempo para la espera de 7 minutos en la sustentación, **cárgala antes** (por la pantalla de Administración o con `engine\.venv\Scripts\python engine/indexing/reprocesar.py --json corpus/procesados/ley_769_de_2002.json`) y en vivo solo muestra la pregunta de la moto antes (en tu ensayo) y después.

## 8. Si algo falla

| Síntoma | Qué hacer |
|---|---|
| El chat responde «El servicio está ocupado» (503) | Límite gratuito de Groq o Gemini. Espera 30 a 60 s y repite. Comprueba que `GROQ_API_KEY` y `GEMINI_API_KEY` están en el `.env` y que `LLM_ORDEN=groq,gemini`. En la sustentación, deja 15 a 20 s entre preguntas |
| La respuesta tarda y sale «está tardando demasiado» (504) | El motor tardó más de 30 s: casi siempre es la CPU ocupada (otro programa pesado, o la carga de una norma). Repite la pregunta |
| `/health` dice `listo: false` | Lee el campo `error`: falta una clave en el `.env` de la raíz, o faltan los índices (paso 4) |
| El motor no arranca (la ventana se cierra o muestra un error) | Abre una terminal en `engine` y corre `.venv\Scripts\uvicorn api:app --port 8000` para ver el error. Si dice que no existe un índice o el BM25: repite el paso 4 |
| Índices incompatibles (errores de FAISS, de dimensión o de BM25 después de un `git pull`) | Reconstrúyelos: `engine\.venv\Scripts\python engine/indexing/build_index.py --todas --sin-adicionales`. Si la ruta tiene tildes, mueve el repo a `C:\dev` |
| Puerto ocupado (8000, 4000 o 5173) | Corre `detener_todo.bat`. Si sigue ocupado, cierra el programa desde el Administrador de tareas, o cambia el puerto (`--port 8010` y `MOTOR_URL`; `PORT` para el backend) |
| 401 en Administración («la clave no es válida») | La `ADMIN_CLAVE` que escribiste no es la del `.env` de la raíz. Revísala (sin espacios al final) y **reinicia el backend** después de cambiar el `.env` |
| 503 en Administración («administración deshabilitada») | Falta `ADMIN_CLAVE` (backend) o `ADMIN_TOKEN` (motor) en el `.env`. Agrégalos y reinicia motor y backend |
| La carga de la norma termina en `error` | Lee el mensaje en la pantalla. El chat sigue con el corpus anterior: no se rompe nada |
| El frontend dice «No se pudo conectar con el servidor» | El backend no está encendido (ventana «Backend Chatbot RAG») |

## 9. Docker (forma ALTERNATIVA, no probada por Duvan)

Santiago Bulla dejó el motor en Docker ([`docker/docker-compose.yml`](../../docker/docker-compose.yml)). **No se probó en el PC de Duvan**; si quieres usarlo, verifícalo **hoy** en el tuyo. Si falla en cualquier paso, **usa el entorno virtual** (pasos 3 a 6), que sí está verificado.

Lo que hace: construye una imagen con Python 3.11, PyTorch (CPU) y las dependencias; **monta** `engine/` (código e índices) y `corpus/` desde tu repo, y lee el **mismo `.env` de la raíz** (`LLM_ORDEN`, `GROQ_API_KEY`, `GEMINI_API_KEY`, `BUSQUEDA_MODO`, `CORPUS_RUTA`, `ADMIN_TOKEN`, `TEMAS_PROPUESTA`…). **Los índices no se construyen dentro del contenedor: se montan los tuyos**, así que antes haz el paso 4 con el entorno virtual. El backend y el frontend siguen corriendo con `npm` (paso 5).

### Verificar Docker en tu PC (hazlo hoy)

1. Abre **Docker Desktop** y espera a que diga «Engine running».
2. Asegúrate de que el puerto 8000 esté libre (`detener_todo.bat`).
3. Desde la raíz del repo:

   ```bash
   docker compose -f docker/docker-compose.yml up -d --build
   ```

   La primera vez tarda (descarga PyTorch y el modelo de embeddings, varios GB).
4. Espera a que <http://localhost:8000/health> diga `"listo": true` (o `docker ps` muestre `healthy`). Ver el registro: `docker logs -f policia-rag-motor`.
5. Arranca backend y frontend con `npm` (sección 6, segunda y tercera terminal) y prueba **2 preguntas**: la del licor (Art. 140) y la de la cédula (Art. 35).
6. Prueba la **pantalla de Administración** con tu `ADMIN_CLAVE`: debe listar la Ley 1801.
7. Para apagar: `docker compose -f docker/docker-compose.yml down`.

**Si falla** (no construye, no llega a `listo`, 503 en Administración, respuestas distintas): `docker compose -f docker/docker-compose.yml down` y usa el entorno virtual. Nota: la imagen instala spaCy, pero los índices se construyeron con Snowball; el motor usa el método guardado en el índice, así que es consistente mientras no reconstruyas los índices dentro de Docker.

## 10. Qué queda pendiente y de quién

| Quién | Pendiente |
|---|---|
| **Wilder** | No subió nada desde el 16/11: `procesar_pdf.py` mejorado (a la Ley 769 le faltan los art. 3, 18 y 128), `corpus/anotaciones_vigencia.json`, fecha de consulta del corpus en `corpus/README_corpus.md` y el banco oficial `eval/banco_preguntas.json` (hoy vacío: la evaluación usó su banco de `corpus/preguntas_ley_1801.json`, adaptado). Secciones «Corpus» y «Evaluación» del informe técnico |
| **Santiago Castro (tú)** | Correr el proyecto en tu PC (esta guía) y verificar Docker; abrir el PR de tu rama no hace falta: ya quedó integrada en `main` el 19/11. Tu sección del informe técnico ya está en [`docs/analisis/seccion_informe_tecnico.md`](../analisis/seccion_informe_tecnico.md) |
| **Santiago Bulla** | Sección «Integración y despliegue» del informe técnico y el video de 5 minutos |
| **Todos** | Ensayo de la sustentación: cada uno debe poder explicar el flujo completo |

Duvan dejó su parte cerrada: [duvan.md](duvan.md). Estado del motor y resultados: [`docs/informe_avance.md`](../informe_avance.md), [`eval/reporte.md`](../../eval/reporte.md) y [`docs/resultados_temas.md`](../resultados_temas.md).

## Mensaje para enviar

WhatsApp, para enviárselo a Santiago Castro:

> Santiago, hoy cerré mi parte y te dejo el proyecto para la sustentación de mañana 💪 La guía paso a paso está aquí: https://github.com/DuvanObando/policia-rag-chatbot/blob/main/docs/guia-companeros/traspaso-santiago-castro.md
> *Hoy*, para tenerlo corriendo en tu PC: clona el repo *fuera de OneDrive* (en `C:\dev`), saca tus claves gratis de Groq y Gemini y crea *tus propios* `ADMIN_TOKEN` y `ADMIN_CLAVE` (no uses los que pasaron por WhatsApp).
> Después: venv, `pip install`, construir los índices y doble clic en `iniciar_todo.bat`. Son unos 45-60 min la primera vez, casi todo esperando descargas.
> La forma verificada es el *venv*. Docker es la alternativa y *no se probó en mi PC*: si lo quieres usar, pruébalo hoy (sección 9 de la guía) y si falla, usa el venv.
> Para la demo te sugiero: preguntar lo de la moto borracho (sale fuera de dominio), cargar la *Ley 769* desde Administración (unos 6 min, el chat sigue respondiendo) y repetirla: ahí cita la Ley 769.
> Tu glosario y tus 32 temas ya están en `main` y arreglaron la pregunta de la cédula 🙌 Cualquier cosa me escribes.
