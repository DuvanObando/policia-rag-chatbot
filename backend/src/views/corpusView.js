// Vistas del corpus: estado de un trabajo de reprocesamiento y lista de normas/documentos.
module.exports = {
  trabajo: (res, status, datos) =>
    res.status(status).json({
      trabajo_id: datos.trabajo_id,
      documento: datos.documento || null,
      norma: datos.norma || null,
      estado: datos.estado,
      progreso: datos.progreso ?? 0,
      articulos_procesados: datos.articulos_procesados ?? null,
      fragmentos_nuevos: datos.fragmentos_nuevos ?? null,
      error: datos.error || null,
      duracion_s: datos.duracion_s ?? null,
    }),

  documentos: (res, datos) =>
    res.json({
      normas: (datos.normas || []).map((n) => ({
        norma: n.norma,
        titulo: n.titulo || null,
        articulos: n.articulos,
        base: Boolean(n.base),
        fuente_url: n.fuente_url || null,
        fecha_carga: n.fecha_carga || null,
        vigencia_verificada: n.vigencia_verificada ?? null,
      })),
      documentos: (datos.documentos || []).map((d) => ({
        id: d.id,
        nombre: d.nombre,
        fecha: d.fecha || null,
        paginas: d.paginas ?? null,
        estado: d.estado,
        norma: d.norma || null,
        fuente_url: d.fuente_url || null,
        articulos: d.articulos ?? null,
      })),
    }),
};
