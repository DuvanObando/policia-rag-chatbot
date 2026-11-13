// Vista de error: todas las fallas salen como { error: "mensaje en español" }.
module.exports = {
  render: (res, status, mensaje) => res.status(status).json({ error: mensaje }),
};
