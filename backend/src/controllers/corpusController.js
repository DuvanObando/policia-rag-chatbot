// Controlador del corpus: lanza el reprocesamiento de una norma subida, consulta su estado
// y lista las normas y documentos. Los mensajes de error del motor se muestran tal cual.
const motor = require("../models/motorModel");
const corpusView = require("../views/corpusView");
const errorView = require("../views/errorView");

async function reprocesar(req, res, next) {
  const { id, norma, fuente_url } = req.body || {};
  if (typeof id !== "string" || !id.trim()) return errorView.render(res, 422, "Falta el id del documento subido.");

  try {
    const { status, datos } = await motor.reprocesar(id.trim(), norma, fuente_url);
    // 409: ya hay un trabajo en curso; se devuelve su id para que el frontend lo siga
    if (status === 409) return errorView.render(res, 409, datos.error, { trabajo_activo: datos.trabajo_activo });
    if (status !== 202) return errorView.render(res, status, datos.error || datos.detail || "El motor no pudo reprocesar.");
    corpusView.trabajo(res, 202, datos);
  } catch (e) {
    next(e);
  }
}

async function estadoTrabajo(req, res, next) {
  try {
    const { status, datos } = await motor.estadoTrabajo(req.params.trabajoId);
    if (status !== 200) return errorView.render(res, status, datos.error || "No se encontró el trabajo.");
    corpusView.trabajo(res, 200, datos);
  } catch (e) {
    next(e);
  }
}

async function documentos(req, res, next) {
  try {
    const { status, datos } = await motor.documentos();
    if (status !== 200) return errorView.render(res, status, datos.error || "No se pudo leer el corpus.");
    corpusView.documentos(res, datos);
  } catch (e) {
    next(e);
  }
}

module.exports = { reprocesar, estadoTrabajo, documentos };
