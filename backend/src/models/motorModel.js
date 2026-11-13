// Modelo: acceso a los datos del motor RAG (FastAPI en MOTOR_URL).
// Cada función devuelve { status, datos } con la respuesta tal cual del motor.
// Si el motor está apagado lanza un error con status 502; si tarda demasiado, 504.
const MOTOR_URL = process.env.MOTOR_URL || "http://localhost:8000";
const TIMEOUT_MS = Number(process.env.MOTOR_TIMEOUT_MS) || 30000;

async function pedir(ruta, opciones = {}) {
  try {
    const r = await fetch(`${MOTOR_URL}${ruta}`, { ...opciones, signal: AbortSignal.timeout(TIMEOUT_MS) });
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

  subirPdf: (archivo) => {
    const form = new FormData();
    form.append("file", new Blob([archivo.buffer], { type: "application/pdf" }), archivo.originalname);
    return pedir("/upload_pdf/", { method: "POST", body: form });
  },
};
