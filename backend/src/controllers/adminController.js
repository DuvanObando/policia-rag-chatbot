// Controlador de administración: solo quien conoce ADMIN_CLAVE (del .env) puede nutrir el corpus.
// El frontend envía la clave en la cabecera X-Admin-Clave; se compara en tiempo constante.
const crypto = require("crypto");
const errorView = require("../views/errorView");

function verificarClave(req, res, next) {
  const esperada = (process.env.ADMIN_CLAVE || "").trim();
  if (!esperada) return errorView.render(res, 503, "La administración está deshabilitada: falta ADMIN_CLAVE en el .env del backend.");

  // Se comparan los hash para que ambos tengan la misma longitud
  const hash = (t) => crypto.createHash("sha256").update(t).digest();
  const recibida = (req.get("X-Admin-Clave") || "").trim();
  if (!recibida || !crypto.timingSafeEqual(hash(recibida), hash(esperada)))
    return errorView.render(res, 401, "No tienes permiso de administrador: la clave no es válida.");
  next();
}

module.exports = { verificarClave };
