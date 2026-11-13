// Un mensaje del chat. Las respuestas del asistente muestran citas, tema y botón de fuentes.
export default function Mensaje({ mensaje, activo, onVerFuentes }) {
  const { rol, contenido, datos } = mensaje;

  if (rol !== "asistente") return <div className={`mensaje ${rol}`}>{contenido}</div>;

  // RF2: se muestran las citas detalladas; si no vienen, la lista corta de artículos
  const citas = datos.citas.length ? datos.citas : datos.articulos_citados;

  return (
    <div className={`mensaje asistente ${activo ? "activo" : ""}`}>
      {datos.fuera_de_dominio && <div className="etiqueta fuera">Fuera del Código</div>}
      <div className="texto">{contenido}</div>

      {citas.length > 0 && (
        <div className="citas">
          <span>Fuentes citadas:</span>
          {citas.map((c) => (
            <span key={c} className="cita">{c}</span>
          ))}
        </div>
      )}

      <div className="pie-mensaje">
        {datos.tema_detectado && datos.tema_detectado !== "general" && (
          <span className="etiqueta tema">Tema: {datos.tema_detectado}</span>
        )}
        {datos.fragmentos.length > 0 && (
          <button className="enlace" onClick={onVerFuentes}>
            {activo ? "Fragmentos en el panel" : `Ver fragmentos recuperados (${datos.fragmentos.length})`}
          </button>
        )}
      </div>
    </div>
  );
}
