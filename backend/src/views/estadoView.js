// Vista del estado del motor: solo lo que necesita el frontend para habilitar el chat.
module.exports = {
  render: (res, datos) =>
    res.json({
      listo: Boolean(datos.listo),
      error: datos.error || null,
      corpus: datos.corpus || null,
      fragmentos_en_indice: datos.fragmentos_en_indice ?? null,
    }),
};
