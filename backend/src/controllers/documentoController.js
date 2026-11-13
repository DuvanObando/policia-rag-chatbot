// Controlador de documentos: reenvía el PDF al motor, que lo guarda sin regenerar embeddings (RF4).
// El límite de 10 MB lo aplica multer en las rutas antes de llegar aquí.
const motor = require("../models/motorModel");
const documentoView = require("../views/documentoView");
const errorView = require("../views/errorView");

async function subirPdf(req, res, next) {
  if (!req.file) return errorView.render(res, 422, "Falta el archivo PDF en el campo 'file'.");
  if (!req.file.originalname.toLowerCase().endsWith(".pdf"))
    return errorView.render(res, 422, "Solo se aceptan archivos PDF.");

  try {
    const { status, datos } = await motor.subirPdf(req.file);
    if (status !== 200) return errorView.render(res, status, datos.error || "El motor no pudo guardar el documento.");
    documentoView.render(res, datos);
  } catch (e) {
    next(e);
  }
}

module.exports = { subirPdf };
