# Guía de Santiago Bulla: backend, frontend e integración

> Antes de esta guía, lee el [README de la carpeta](README.md): explica el proyecto, el estado del motor, cómo levantarlo y las reglas comunes (repo fuera de OneDrive, clave de Gemini propia, rama por persona, etc.).

## Tu rol

Eres el responsable de lo que ve el usuario: el **backend Node.js/Express** (proxy hacia el motor Python), el **frontend de chat** (con historial y panel de fuentes), el **aviso legal**, el `.env`, el **despliegue en entorno de pruebas**, el **README de instalación** y el **video de 5 minutos**. Pesa 15 % de la nota (integración y funcionalidad), y los requisitos RF5, RNF2, RNF3 y RNF4 del enunciado son tuyos.

## Buena noticia: el motor real ya funciona

El plan marca «trabajar con datos simulados» hasta el día 6, pero **el motor real ya está en `main` y responde**. Puedes conectarte a él desde hoy (levántalo con la sección [«Motor RAG (engine/)» del README raíz](../../README.md#motor-rag-engine)). Necesitas tu propia clave gratuita de Gemini en tu `.env` (ver reglas comunes).

## El contrato (resumen; el completo está en [`docs/api_contract.md`](../api_contract.md))

El motor corre en `http://localhost:8000`. Tu backend lo llama; el frontend solo habla con tu backend.

`POST /query` con `{"pregunta": "...", "historial": [...]}` devuelve:

```json
{
  "respuesta": "texto con las citas y los avisos de vigencia",
  "articulos_citados": ["Artículo 163"],
  "citas": [{"articulo": "Artículo 163", "numeral": "2", "paragrafo": null, "texto": "Art. 163, num. 2"}],
  "fragmentos": [{
    "id": "art-163-f1",
    "ubicacion": "Libro III, Título I, Capítulo I, Artículo 163",
    "epigrafe": "INGRESO A INMUEBLE SIN ORDEN ESCRITA",
    "texto": "...", "score": 0.036,
    "vigencia": "modificado", "tema": "Ingreso a domicilio"
  }],
  "fuera_de_dominio": false,
  "tema_detectado": "Ingreso a domicilio"
}
```

- **Opcionales** (pueden faltar): `vigencia` y `tema` en cada fragmento, `citas`, `tema_detectado`. El frontend no debe fallar si no vienen.
- `vigencia`: `vigente`, `modificado`, `inexequible`, `exequible_condicionado` o `no_verificada`.
- `historial` se acepta (máximo 50 mensajes) pero **el motor todavía no lo usa**.
- La pregunta no puede estar vacía ni superar **500 caracteres**.
- **Errores**, siempre `{"error": "mensaje en español"}`: **422** entrada inválida, **413** PDF de más de 10 MB, **503** el motor no está listo o Gemini está saturado («El servicio está ocupado, intenta de nuevo en unos minutos»), **500** error interno. El mensaje se puede mostrar tal cual.
- `GET /health` → `{"listo": true|false, "error": ..., ...}`.
- `POST /upload_pdf/` (multipart, campo `file`) → `{nombre_guardado, paginas, caracteres, estado, mensaje}`. El documento **no está disponible en las consultas** hasta que Duvan reconstruya el índice: el `mensaje` ya lo explica; muéstraselo al usuario.

## Tareas (fechas según el cronograma del plan, día 1 = lunes 9/11)

- [ ] **Día 1 · Lun 09/11:** estructura del backend y del frontend (el motor real ya está disponible para probar).
- [ ] **Día 2 · Mar 10/11:** backend como proxy hacia el motor: `/query`, **`/health`** y `/upload_pdf` + **CORS** restringido.
- [ ] **Día 3 · Mié 11/11:** chat con **historial** de conversación.
- [ ] **Día 4 · Jue 12/11:** **panel de fuentes** (ver reglas abajo).
- [ ] **Día 5 · Vie 13/11:** **aviso legal** visible, configuración con `.env`, revisión de la Ley 1581 del diseño.
- [ ] **Día 6 · Lun 16/11:** frontend conectado al motor real de punta a punta (si ya lo hiciste antes, mejor).
- [ ] **Día 7 · Mar 17/11:** pruebas de integración y **despliegue de pruebas**.
- [ ] **Día 8 · Mié 18/11:** corregir la interfaz; `README` y `package.json` completos (reproducible); revisión final de la Ley 1581.
- [ ] **Día 9 · Jue 19/11:** guion y grabación del **video de 5 minutos** (con una pregunta fuera de dominio); sección «Integración / frontend» del informe técnico.
- [ ] **Día 10 · Vie 20/11:** ensayo de la sustentación (todos explican el flujo completo).

## Archivos que te pertenecen

- `backend/` (hoy `backend/src/server.js` y `package.json`), `frontend/` (hoy solo un placeholder: el framework lo eliges tú), `.env.example`, `README.md`

## Lo que ya dejé listo para ti

- **El motor real** con `/health`, `/query` y `/upload_pdf/`, y el contrato documentado.
- **Un backend mínimo** (`backend/src/server.js`): proxy de `/query` y `/upload_pdf`, CORS restringido a `ORIGENES_PERMITIDOS` y puerto/URL del motor por `.env`. **Le faltan** las cosas de abajo.
- **El `.env.example`** con `ORIGENES_PERMITIDOS`, `MOTOR_URL` y `PORT`. El backend lee el `.env` de la **raíz** del repo.
- **Mensajes de error amables ya en español** que puedes mostrar directamente.

## Qué debe hacer el backend y el frontend

**Chat y estado del motor**

- Llama a `GET /health` y **habilita el chat solo cuando `listo` sea `true`**. Si es `false`, muestra el `error` de forma amable. (El backend actual no expone `/health`: agrégalo como proxy.)
- Envía las preguntas **en UTF-8** (en `fetch`/Express ya lo es; cuidado con probar con `curl` o PowerShell en Windows, que rompen los acentos: usa Postman o un script en Node).
- Hoy, si el motor está apagado, tu backend devuelve **502** `{"error": "Motor no disponible"}`: tradúcelo en la interfaz con el mismo tono amable.
- Si el motor responde **503** o tarda, muestra un **mensaje amable** («El servicio está ocupado…») en lugar de quedarte cargando. Una respuesta normal tarda 1 a 4 s; en el peor caso, unos 21 s. Pon un indicador de «pensando…» y un tiempo máximo de unos 30 s.
- El **historial** puedes enviarlo, pero el motor aún no lo usa; guárdalo solo en el navegador (sesión), no en el servidor.

**Panel de fuentes (RF5)**

- Muestra los `fragmentos` con `ubicacion`, `epigrafe` y `texto`.
- **Muestra la `vigencia` con una señal visible cuando no sea `vigente`** (`modificado`, `inexequible`, `exequible_condicionado`, `no_verificada`).
- Muestra las **`citas`** (artículo + numeral o parágrafo, usando el campo `texto`, p. ej. «Art. 180, par.»). `articulos_citados` es la lista corta de artículos.
- **NO muestres el `score` como porcentaje** ni como «relevancia 93 %». En el modo por defecto (híbrido) es un puntaje de fusión de ~0.01 a 0.04 y cambia de escala según el modo. Si lo muestras, que no sea como porcentaje (o mejor, no lo muestres).
- **Si `fuera_de_dominio` es `true`**, el motor igual devuelve `fragmentos`, pero son los *más parecidos*, no fuentes relevantes. No los presentes como fuente de la respuesta (ocúltalos o márcalos «no relacionados»); `articulos_citados` y `citas` vienen vacíos.

**Aviso legal (RF y ética)**

- Visible siempre: es una herramienta **informativa**, no sustituye la asesoría jurídica.

**Subida de PDFs**

- **Limita las subidas a 10 MB en el backend antes de reenviarlas** a `/upload_pdf/` (en `multer`, `limits: { fileSize: 10 * 1024 * 1024 }`). Hoy el backend las acepta sin límite. Convierte el error de tamaño en un 413 con mensaje en español.
- Muestra el `mensaje` de la respuesta: explica que el documento todavía no está disponible en las consultas.

**Seguridad y privacidad**

- **CORS** restringido a los orígenes de `ORIGENES_PERMITIDOS` del `.env` (ya está; mantenlo y pruébalo con un origen no permitido).
- **Ley 1581 de 2012:** el backend **tampoco debe registrar** preguntas ni respuestas en logs (cuidado con `console.log(req.body)`, morgan con cuerpo, etc.). Solo estado, tiempos y errores.
- Las claves van en el `.env` (RNF2). Nunca en el repositorio ni en el frontend.

## Cómo entregar

1. `git checkout main && git pull`, luego `git checkout -b feature/santiago-bulla-web`.
2. Haz commits pequeños y sube con `git push -u origin feature/santiago-bulla-web`.
3. Abre un **pull request a `main`**; lo revisa Duvan. Separa backend y frontend en PRs distintos si puedes.
4. Si necesitas un campo nuevo en la API, o algo del motor cambia, **avísale a Duvan**: el contrato (`docs/api_contract.md`) se cambia por PR.
5. El `README` de instalación y ejecución es tuyo: debe permitir que alguien levante todo desde cero.

## Avisos y peticiones

- **El motor puede estar caído o saturado**: tu interfaz tiene que seguir funcionando y explicar qué pasa.
- La **primera vez** que se levanta el motor tarda en cargar (unos 10 a 15 s); por eso `/health`.
- Si el puerto 8000 está ocupado, cambia el del motor y `MOTOR_URL`.
- Pregúntame lo que no esté claro; pero primero revisa `docs/api_contract.md`.

## Mensaje para enviar

> Santiago, el motor del chatbot ya está listo en `main` y funcionando (`/health`, `/query` y `/upload_pdf/`): puedes conectar tu backend y tu frontend al motor real desde hoy, no hace falta esperar al día 6.
> Tu guía con fechas, el contrato y lo que debe mostrar el panel de fuentes está en `docs/guia-companeros/santiago-bulla.md` (lee primero el README de esa carpeta).
> Ojo con tres cosas: **no muestres el score como porcentaje**, habilita el chat solo cuando `/health` diga `listo: true`, y limita las subidas a **10 MB** en el backend.
> Saca tu clave gratis de Gemini en AI Studio y trabaja el repo fuera de OneDrive 🙏
