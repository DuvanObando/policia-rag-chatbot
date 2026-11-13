// Controlador del chat: valida la pregunta, consulta el motor y entrega la vista.
const motor = require("../models/motorModel");
const chatView = require("../views/chatView");
const errorView = require("../views/errorView");

const MAX_PREGUNTA = 500;
const MAX_HISTORIAL = 50;

async function preguntar(req, res, next) {
  const { pregunta, historial = [] } = req.body || {};

  if (typeof pregunta !== "string" || !pregunta.trim())
    return errorView.render(res, 422, "La pregunta no puede estar vacía.");
  if (pregunta.trim().length > MAX_PREGUNTA)
    return errorView.render(res, 422, `La pregunta es demasiado larga: máximo ${MAX_PREGUNTA} caracteres.`);
  if (!Array.isArray(historial) || historial.length > MAX_HISTORIAL)
    return errorView.render(res, 422, `El historial debe ser una lista de máximo ${MAX_HISTORIAL} mensajes.`);

  try {
    const { status, datos } = await motor.consultar(pregunta.trim(), historial);
    if (status !== 200) return errorView.render(res, status, datos.error || "El motor no pudo responder.");
    chatView.render(res, datos);
  } catch (e) {
    next(e);
  }
}

module.exports = { preguntar };
