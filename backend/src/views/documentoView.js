// Vista de la subida de PDF: el id es el que se manda a /corpus/reprocesar (paso 2).
// El mensaje explica que el documento aún no entra a las consultas (RF4).
module.exports = {
  render: (res, datos) =>
    res.json({
      id: datos.id,
      nombre_guardado: datos.nombre_guardado,
      paginas: datos.paginas,
      caracteres: datos.caracteres,
      estado: datos.estado,
      norma: datos.norma || null,
      fuente_url: datos.fuente_url || null,
      mensaje: datos.mensaje,
    }),
};
