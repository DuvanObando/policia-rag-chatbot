// Vista del estado del motor: lo que necesita el frontend para habilitar el chat
// y mostrar las normas cargadas (cambian sin reiniciar cuando termina un reprocesamiento).
module.exports = {
  render: (res, datos) =>
    res.json({
      listo: Boolean(datos.listo),
      error: datos.error || null,
      corpus: datos.corpus || null,
      fragmentos_en_indice: datos.fragmentos_en_indice ?? null,
      normas: datos.normas || [],
      trabajo_activo: datos.reprocesamiento?.trabajo_activo || null,
    }),
};
