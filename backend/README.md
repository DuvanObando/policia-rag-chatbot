# Backend (Express · MVC)

Intermediario entre el frontend React y el motor RAG (FastAPI). El frontend nunca llama al motor directamente.

## Estructura

```
backend/src/
├── server.js                      Arranque: .env, CORS, log sin datos personales, manejo de errores
├── routes/rutas.js                Endpoints → controlador (y límite de 10 MB del PDF con multer)
├── controllers/
│   ├── chatController.js          POST /query: valida la pregunta y el historial
│   ├── estadoController.js        GET /health: estado del motor y normas cargadas
│   ├── adminController.js         Verifica la clave de administrador (cabecera X-Admin-Clave)
│   ├── documentoController.js     POST /upload_pdf: valida y reenvía el PDF con norma y URL
│   └── corpusController.js        Reprocesar una norma, estado del trabajo, lista del corpus
├── models/motorModel.js           Modelo: llamadas HTTP al motor (MOTOR_URL), con tiempo máximo
└── views/
    ├── chatView.js                JSON de la respuesta del chat (sin score, con norma)
    ├── estadoView.js              JSON del estado (listo, error, normas, trabajo_activo)
    ├── documentoView.js           JSON de la subida de PDF (con el id para reprocesar)
    ├── corpusView.js              JSON del trabajo de reprocesamiento y de la lista del corpus
    └── errorView.js               { "error": "mensaje en español" }
```

## Endpoints

| Método | Ruta | Acceso | Qué hace |
|---|---|---|---|
| GET | `/health` | público | `{ listo, error, corpus, fragmentos_en_indice, normas, trabajo_activo }`. Siempre 200; con el motor apagado, `listo: false` |
| POST | `/query` | público | `{ pregunta, historial }` → `{ respuesta, fuera_de_dominio, tema_detectado, articulos_citados, citas, fragmentos }` |
| POST | `/upload_pdf` | admin | `multipart/form-data`: `file` (PDF ≤ 10 MB), `norma` («Ley 769 de 2002») y `fuente_url` opcional. Devuelve `id`; no toca las consultas (RF4). Espera hasta 60 s |
| POST | `/corpus/reprocesar` | admin | `{ id }` → 202 `{ trabajo_id, estado, progreso, ... }`. El backend agrega `X-Admin-Token` |
| GET | `/corpus/reprocesar/:trabajoId` | admin | Estado del trabajo: `en_cola`, `extrayendo`, `indexando`, `listo` o `error`, con `progreso` 0-100 |
| GET | `/corpus/documentos` | admin | `{ normas, documentos }`: normas cargadas y PDF subidos |

Las rutas **admin** exigen la cabecera `X-Admin-Clave` con el valor de `ADMIN_CLAVE`. El token del motor (`ADMIN_TOKEN`) solo lo conoce el backend; nunca llega al navegador.

Errores, siempre `{ "error": "..." }`: 400 JSON inválido · 401 clave de administrador inválida · 403 origen no permitido (CORS) · 404 documento o trabajo inexistente · 409 ya hay un reprocesamiento en curso (incluye `trabajo_activo`) · 413 PDF > 10 MB · 422 entrada inválida · 502 motor apagado · 503 motor ocupado o administración deshabilitada · 504 el motor tardó demasiado.

## Variables (`.env` de la raíz del repo)

| Variable | Por defecto | Uso |
|---|---|---|
| `PORT` | `4000` | Puerto del backend |
| `MOTOR_URL` | `http://localhost:8000` | URL del motor FastAPI |
| `ORIGENES_PERMITIDOS` | (vacío) | Orígenes aceptados por CORS, separados por coma. Debe incluir `http://localhost:5173` |
| `MOTOR_TIMEOUT_MS` | `30000` | Tiempo máximo de espera al motor (la subida de PDF usa 60 s) |
| `ADMIN_CLAVE` | (vacío) | Clave que escribe el administrador en la pestaña Administración. Sin ella, las rutas admin responden 503 |
| `ADMIN_TOKEN` | (vacío) | Token del motor para `/corpus/reprocesar`. Es el mismo `ADMIN_TOKEN` que lee el motor del `.env` |

Generar valores largos y aleatorios:

```bash
node -e "console.log(require('crypto').randomBytes(32).toString('base64url'))"
```

## Ejecutar

```bash
cd backend
npm install
npm run dev
```

## Privacidad (Ley 1581 de 2012)

El log solo registra método, ruta, código y tiempo. Nunca el texto de preguntas, respuestas, historial ni PDFs.
