// Vista de la subida de PDF: el mensaje explica que el documento aún no entra a las consultas (RF4).
module.exports = {
  render: (res, datos) =>
    res.json({
      nombre_guardado: datos.nombre_guardado,
      paginas: datos.paginas,
      caracteres: datos.caracteres,
      estado: datos.estado,
      mensaje: datos.mensaje,
    }),
};
