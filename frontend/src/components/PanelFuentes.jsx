// Panel de fuentes (RF5): fragmentos recuperados para verificar la respuesta.
// Todo lo que no sea "vigente" lleva señal visible y las expresiones [INEXEQUIBLE: ...] se tachan.
export default function PanelFuentes({ mensaje }) {
  const datos = mensaje?.datos;

  return (
    <aside className="panel-fuentes">
      <h2>Fragmentos recuperados</h2>

      {!datos && <p className="vacio">Aquí aparecerán los fragmentos del Código que sustentan cada respuesta.</p>}

      {datos?.fuera_de_dominio && (
        <p className="alerta">
          La pregunta no corresponde al Código. Estos fragmentos son solo los más parecidos y <strong>no están relacionados</strong> con la respuesta.
        </p>
      )}

      {datos?.fragmentos.map((f) => (
        <article key={f.id} className={`fragmento ${datos.fuera_de_dominio ? "no-relacionado" : ""}`}>
          <header>
            <h3>{f.epigrafe || f.id}</h3>
            {f.vigencia && (
              <span className={`vigencia ${f.vigencia === "vigente" ? "ok" : "aviso"}`}>
                {f.vigencia === "vigente" ? "Vigente" : `⚠ ${f.vigencia.replaceAll("_", " ")}`}
              </span>
            )}
          </header>
          <p className="ubicacion">{f.ubicacion}</p>
          {f.tema && <span className="etiqueta tema">{f.tema}</span>}

          <p className="texto-fragmento">
            {f.texto.split(/(\[INEXEQUIBLE: [^\]]*\])/).map((parte, i) =>
              parte.startsWith("[INEXEQUIBLE: ") ? (
                <del key={i} title="Expresión declarada inexequible por la Corte Constitucional">
                  {parte.slice(14, -1)}
                </del>
              ) : (
                parte
              )
            )}
          </p>

          {f.archivo_fuente && (
            <p className="origen">
              Fuente: {f.archivo_fuente.split("/").pop()}
              {f.paginas.length > 0 && ` · pág. ${f.paginas.join(", ")}`}
            </p>
          )}
        </article>
      ))}
    </aside>
  );
}
