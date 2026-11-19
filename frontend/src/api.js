// Llamadas al backend Express. El frontend nunca habla directo con el motor.
// Toda falla se convierte en un Error con mensaje en español; trae `status` y `datos` del backend.
const API_URL = import.meta.env.VITE_API_URL || "http://localhost:4000";

async function llamar(ruta, opciones = {}, timeout = 35000) {
  let r;
  try {
    r = await fetch(`${API_URL}${ruta}`, { ...opciones, signal: AbortSignal.timeout(timeout) });
  } catch (e) {
    throw new Error(
      e.name === "TimeoutError"
        ? "La respuesta está tardando demasiado. Intenta de nuevo en unos minutos."
        : "No se pudo conectar con el servidor. Verifica que el backend esté encendido."
    );
  }
  const datos = await r.json().catch(() => ({}));
  if (!r.ok) throw Object.assign(new Error(datos.error || "Ocurrió un error inesperado. Intenta de nuevo."), { status: r.status, datos });
  return datos;
}

export const obtenerEstado = () => llamar("/health");

export const enviarPregunta = (pregunta, historial) =>
  llamar("/query", {
    method: "POST",
    headers: { "Content-Type": "application/json; charset=utf-8" },
    body: JSON.stringify({ pregunta, historial }),
  });

// Administración: la clave viaja en X-Admin-Clave; el token del motor solo lo conoce el backend
export const listarCorpus = (clave) => llamar("/corpus/documentos", { headers: { "X-Admin-Clave": clave } });

export const subirPdf = (clave, archivo, norma, fuenteUrl) => {
  const form = new FormData();
  form.append("file", archivo);
  form.append("norma", norma);
  if (fuenteUrl) form.append("fuente_url", fuenteUrl);
  return llamar("/upload_pdf", { method: "POST", headers: { "X-Admin-Clave": clave }, body: form }, 65000);
};

export const reprocesar = (clave, id) =>
  llamar("/corpus/reprocesar", {
    method: "POST",
    headers: { "Content-Type": "application/json; charset=utf-8", "X-Admin-Clave": clave },
    body: JSON.stringify({ id }),
  });

export const estadoTrabajo = (clave, trabajoId) =>
  llamar(`/corpus/reprocesar/${encodeURIComponent(trabajoId)}`, { headers: { "X-Admin-Clave": clave } });
