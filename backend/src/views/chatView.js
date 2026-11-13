// Vista del chat: arma el JSON que consume el frontend a partir de la respuesta del motor.
// El score no se envía: su escala cambia según el modo de búsqueda (ver docs/api_contract.md).
module.exports = {
  render: (res, datos) =>
    res.json({
      respuesta: datos.respuesta,
      fuera_de_dominio: datos.fuera_de_dominio,
      tema_detectado: datos.tema_detectado || null,
      articulos_citados: datos.articulos_citados || [],
      citas: (datos.citas || []).map((c) => c.texto),
      fragmentos: (datos.fragmentos || []).map((f) => ({
        id: f.id,
        ubicacion: f.ubicacion,
        epigrafe: f.epigrafe,
        texto: f.texto,
        vigencia: f.vigencia || null,
        tema: f.tema || null,
        archivo_fuente: f.archivo_fuente || f.fuente || null,
        paginas: f.paginas || [],
      })),
    }),
};
