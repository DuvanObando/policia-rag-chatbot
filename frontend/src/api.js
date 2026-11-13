// Llamadas al backend Express. El frontend nunca habla directo con el motor.
// Toda falla se convierte en un Error con un mensaje en español listo para mostrar.
const API_URL = import.meta.env.VITE_API_URL || "http://localhost:4000";
const TIMEOUT_MS = 35000;

async function llamar(ruta, opciones = {}) {
  let r;
  try {
    r = await fetch(`${API_URL}${ruta}`, { ...opciones, signal: AbortSignal.timeout(TIMEOUT_MS) });
  } catch (e) {
    throw new Error(
      e.name === "TimeoutError"
        ? "La respuesta está tardando demasiado. Intenta de nuevo en unos minutos."
        : "No se pudo conectar con el servidor. Verifica que el backend esté encendido."
    );
  }
  const datos = await r.json().catch(() => ({}));
  if (!r.ok) throw new Error(datos.error || "Ocurrió un error inesperado. Intenta de nuevo.");
  return datos;
}

export const obtenerEstado = () => llamar("/health");

export const enviarPregunta = (pregunta, historial) =>
  llamar("/query", {
    method: "POST",
    headers: { "Content-Type": "application/json; charset=utf-8" },
    body: JSON.stringify({ pregunta, historial }),
  });

export const subirPdf = (archivo) => {
  const form = new FormData();
  form.append("file", archivo);
  return llamar("/upload_pdf", { method: "POST", body: form });
};
