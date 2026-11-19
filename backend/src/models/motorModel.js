// Modelo: acceso a los datos del motor RAG (FastAPI en MOTOR_URL).
// Cada función devuelve { status, datos } con la respuesta tal cual del motor.
// Si el motor está apagado lanza un error con status 502; si tarda demasiado, 504.
const MOTOR_URL = process.env.MOTOR_URL || "http://localhost:8000";
const TIMEOUT_MS = Number(process.env.MOTOR_TIMEOUT_MS) || 30000;
const TIMEOUT_SUBIDA_MS = 60000; // la subida extrae el texto del PDF: sin PyMuPDF puede pasar de 30 s

async function pedir(ruta, opciones = {}, timeout = TIMEOUT_MS) {
  try {
    const r = await fetch(`${MOTOR_URL}${ruta}`, { ...opciones, signal: AbortSignal.timeout(timeout) });
    return { status: r.status, datos: await r.json() };
  } catch (e) {
    const error = new Error(
      e.name === "TimeoutError"
        ? "El motor tardó demasiado en responder. Intenta de nuevo en unos minutos."
        : "El motor no está disponible en este momento. Intenta de nuevo en unos minutos."
    );
    error.status = e.name === "TimeoutError" ? 504 : 502;
    throw error;
  }
}

module.exports = {
  estado: () => pedir("/health"),

  consultar: (pregunta, historial) =>
    pedir("/query", {
      method: "POST",
      headers: { "Content-Type": "application/json; charset=utf-8" },
      body: JSON.stringify({ pregunta, historial }),
    }),

  subirPdf: (archivo, norma, fuenteUrl) => {
    const form = new FormData();
    form.append("file", new Blob([archivo.buffer], { type: "application/pdf" }), archivo.originalname);
    if (norma) form.append("norma", norma);
    if (fuenteUrl) form.append("fuente_url", fuenteUrl);
    return pedir("/upload_pdf/", { method: "POST", body: form }, TIMEOUT_SUBIDA_MS);
  },

  // El token de administrador del motor sale del .env del backend; el frontend nunca lo ve
  reprocesar: (id, norma, fuenteUrl) =>
    pedir("/corpus/reprocesar", {
      method: "POST",
      headers: { "Content-Type": "application/json; charset=utf-8", "X-Admin-Token": process.env.ADMIN_TOKEN || "" },
      body: JSON.stringify({ id, norma: norma || null, fuente_url: fuenteUrl || null }),
    }),

  estadoTrabajo: (trabajoId) => pedir(`/corpus/reprocesar/${encodeURIComponent(trabajoId)}`),

  documentos: () => pedir("/corpus/documentos"),
};
