// Controlador del estado: el frontend solo habilita el chat cuando el motor está listo.
// Si el motor está apagado responde 200 con listo=false y el motivo, igual que /health del motor.
const motor = require("../models/motorModel");
const estadoView = require("../views/estadoView");

async function consultarEstado(req, res) {
  try {
    const { datos } = await motor.estado();
    estadoView.render(res, datos);
  } catch (e) {
    estadoView.render(res, { listo: false, error: e.message });
  }
}

module.exports = { consultarEstado };
