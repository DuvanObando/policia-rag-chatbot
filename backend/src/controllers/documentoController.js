// Controlador de documentos: reenvía el PDF (y su norma y URL oficial) al motor, que lo guarda
// sin regenerar embeddings (RF4). El límite de 10 MB lo aplica multer en las rutas.
const motor = require("../models/motorModel");
const documentoView = require("../views/documentoView");
const errorView = require("../views/errorView");

async function subirPdf(req, res, next) {
  if (!req.file) return errorView.render(res, 422, "Falta el archivo PDF en el campo 'file'.");
  if (!req.file.originalname.toLowerCase().endsWith(".pdf"))
    return errorView.render(res, 422, "Solo se aceptan archivos PDF.");

  const norma = (req.body.norma || "").trim();
  const fuenteUrl = (req.body.fuente_url || "").trim();

  try {
    const { status, datos } = await motor.subirPdf(req.file, norma, fuenteUrl);
    if (status !== 200) return errorView.render(res, status, datos.error || "El motor no pudo guardar el documento.");
    documentoView.render(res, datos);
  } catch (e) {
    next(e);
  }
}

module.exports = { subirPdf };
