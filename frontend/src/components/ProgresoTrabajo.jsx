// Barra de progreso del reprocesamiento con el estado del trabajo en español.
const ESTADOS = {
  en_cola: "En cola",
  extrayendo: "Extrayendo los artículos del PDF",
  indexando: "Calculando embeddings e indexando",
  listo: "Norma incorporada al corpus",
  error: "El reprocesamiento falló",
};

export default function ProgresoTrabajo({ trabajo, onCerrar }) {
  const { estado, progreso, norma, error } = trabajo;

  return (
    <section className={`tarjeta progreso ${estado}`} role="status">
      <div className="progreso-cabecera">
        <h3>{norma ? `Reprocesamiento: ${norma}` : "Reprocesamiento"}</h3>
        {onCerrar && <button className="enlace" onClick={onCerrar}>Cerrar</button>}
      </div>
      <p>
        {ESTADOS[estado] || estado} · {progreso}%
      </p>
      <div className="barra">
        <div style={{ width: `${progreso}%` }} />
      </div>

      {estado === "listo" && (
        <p className="aviso">
          {trabajo.articulos_procesados} artículos y {trabajo.fragmentos_nuevos} fragmentos nuevos
          {trabajo.duracion_s != null && ` en ${Math.round(trabajo.duracion_s)} s`}. Ya está disponible en el chat.
        </p>
      )}
      {estado === "error" && <p className="aviso error">{error}. El chat sigue con el corpus anterior.</p>}
    </section>
  );
}
