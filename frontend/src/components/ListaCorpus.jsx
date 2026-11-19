// Normas cargadas en el corpus y documentos subidos (GET /corpus/documentos).
// Un documento pendiente con norma se puede incorporar desde aquí (p. ej. si falló antes).
const ESTADOS_DOC = {
  pendiente_de_indexar: "Pendiente",
  indexado: "Indexado (complementario)",
  procesado: "Incorporado",
};

export default function ListaCorpus({ corpus, ocupado, onIncorporar, onActualizar }) {
  return (
    <section className="tarjeta lista-corpus">
      <div className="progreso-cabecera">
        <h3>Normas cargadas</h3>
        <button className="enlace" onClick={onActualizar}>Actualizar</button>
      </div>
      <table>
        <thead>
          <tr><th>Norma</th><th>Artículos</th><th>Origen</th><th>Vigencia</th></tr>
        </thead>
        <tbody>
          {corpus.normas.map((n) => (
            <tr key={n.norma}>
              <td>
                <strong>{n.norma}</strong>
                {n.titulo && <div className="detalle">{n.titulo}</div>}
              </td>
              <td>{n.articulos}</td>
              <td>
                {n.base ? "Corpus base" : "Agregada"}
                {n.fuente_url && <div><a href={n.fuente_url} target="_blank" rel="noreferrer">Fuente oficial</a></div>}
              </td>
              <td>
                {n.vigencia_verificada === false ? <span className="vigencia aviso">⚠ No verificada</span> : <span className="vigencia ok">Verificada</span>}
              </td>
            </tr>
          ))}
        </tbody>
      </table>

      <h3>Documentos subidos</h3>
      {!corpus.documentos.length && <p className="detalle">Todavía no se ha subido ningún PDF.</p>}
      {corpus.documentos.length > 0 && (
        <table>
          <thead>
            <tr><th>Documento</th><th>Norma</th><th>Estado</th><th /></tr>
          </thead>
          <tbody>
            {corpus.documentos.map((d) => (
              <tr key={d.id}>
                <td>
                  {d.nombre}
                  <div className="detalle">{[d.fecha, d.paginas && `${d.paginas} págs.`].filter(Boolean).join(" · ")}</div>
                </td>
                <td>{d.norma || <span className="detalle">Sin norma</span>}</td>
                <td>{ESTADOS_DOC[d.estado] || d.estado}</td>
                <td>
                  {d.estado === "pendiente_de_indexar" && d.norma && (
                    <button className="boton-secundario" disabled={ocupado} onClick={() => onIncorporar(d.id)}>
                      Incorporar
                    </button>
                  )}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      )}
    </section>
  );
}
