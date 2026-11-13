# Backend (Express · MVC)

Intermediario entre el frontend React y el motor RAG (FastAPI). El frontend nunca llama al motor directamente.

## Estructura

```
backend/src/
├── server.js                      Arranque: .env, CORS, log sin datos personales, manejo de errores
├── routes/rutas.js                Endpoints → controlador (y límite de 10 MB del PDF con multer)
├── controllers/
│   ├── chatController.js          POST /query: valida la pregunta y el historial
│   ├── estadoController.js        GET /health: estado del motor
│   └── documentoController.js     POST /upload_pdf: valida y reenvía el PDF
├── models/motorModel.js           Modelo: llamadas HTTP al motor (MOTOR_URL), con tiempo máximo
└── views/
    ├── chatView.js                JSON de la respuesta del chat (sin score)
    ├── estadoView.js              JSON del estado (listo, error)
    ├── documentoView.js           JSON de la subida de PDF
    └── errorView.js               { "error": "mensaje en español" }
```

## Endpoints

| Método | Ruta | Qué hace |
|---|---|---|
| GET | `/health` | `{ listo, error, corpus, fragmentos_en_indice }`. Siempre 200; si el motor está apagado, `listo: false` |
| POST | `/query` | `{ pregunta, historial }` → `{ respuesta, fuera_de_dominio, tema_detectado, articulos_citados, citas, fragmentos }` |
| POST | `/upload_pdf` | `multipart/form-data`, campo `file` (PDF ≤ 10 MB). Lo guarda pendiente de indexar (RF4) |

Errores, siempre `{ "error": "..." }`: 400 JSON inválido · 403 origen no permitido (CORS) · 413 PDF > 10 MB · 422 entrada inválida · 502 motor apagado · 503 motor ocupado · 504 el motor tardó más de `MOTOR_TIMEOUT_MS`.

## Variables (`.env` de la raíz del repo)

| Variable | Por defecto | Uso |
|---|---|---|
| `PORT` | `4000` | Puerto del backend |
| `MOTOR_URL` | `http://localhost:8000` | URL del motor FastAPI |
| `ORIGENES_PERMITIDOS` | (vacío) | Orígenes aceptados por CORS, separados por coma. Debe incluir `http://localhost:5173` |
| `MOTOR_TIMEOUT_MS` | `30000` | Tiempo máximo de espera al motor |

## Ejecutar

```bash
cd backend
npm install
npm run dev
```

## Privacidad (Ley 1581 de 2012)

El log solo registra método, ruta, código y tiempo. Nunca el texto de preguntas, respuestas, historial ni PDFs.
