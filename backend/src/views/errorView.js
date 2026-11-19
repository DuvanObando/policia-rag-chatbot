// Vista de error: todas las fallas salen como { error: "mensaje en español" }.
// `extra` agrega campos útiles para el frontend (p. ej. trabajo_activo en un 409).
module.exports = {
  render: (res, status, mensaje, extra = {}) => res.status(status).json({ error: mensaje, ...extra }),
};
