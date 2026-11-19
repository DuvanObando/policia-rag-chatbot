// Formulario para agregar una norma: sube el PDF con su norma y URL oficial (paso 1)
// y, si sale bien, pide incorporarla al corpus (paso 2) con el id que devuelve el backend.
import { useState } from "react";
import { subirPdf } from "../api.js";

const MAX_BYTES = 10 * 1024 * 1024;

export default function FormNorma({ clave, ocupado, onSubido, onError }) {
  const [archivo, setArchivo] = useState(null);
  const [norma, setNorma] = useState("");
  const [fuenteUrl, setFuenteUrl] = useState("");
  const [subiendo, setSubiendo] = useState(false);
  const [aviso, setAviso] = useState(null);

  async function enviar(e) {
    e.preventDefault();
    if (archivo.size > MAX_BYTES) return setAviso("El archivo supera el máximo permitido de 10 MB.");

    setSubiendo(true);
    setAviso(null);
    try {
      const datos = await subirPdf(clave, archivo, norma.trim(), fuenteUrl.trim());
      setAviso(`PDF guardado (${datos.paginas} páginas): ${datos.norma}. Su avance se muestra abajo.`);
      setArchivo(null);
      setNorma("");
      setFuenteUrl("");
      e.target.reset();
      onSubido(datos.id);
    } catch (err) {
      setAviso(null);
      onError(err);
    } finally {
      setSubiendo(false);
    }
  }

  return (
    <form className="tarjeta form-norma" onSubmit={enviar}>
      <h3>Agregar una norma</h3>
      <p className="ayuda">
        El PDF se guarda sin tocar las consultas (RF4) y luego se incorpora al corpus en segundo plano. El chat sigue
        respondiendo mientras tanto. Si la norma ya estaba cargada, se reemplaza.
      </p>

      <label>
        PDF oficial de la norma (máx. 10 MB)
        <input type="file" accept="application/pdf,.pdf" required onChange={(e) => setArchivo(e.target.files[0] || null)} />
      </label>
      <label>
        Norma (tipo, número y año)
        <input type="text" placeholder="Ley 769 de 2002" value={norma} required onChange={(e) => setNorma(e.target.value)} />
      </label>
      <label>
        URL oficial de la fuente (opcional)
        <input type="url" placeholder="https://www.funcionpublica.gov.co/…" value={fuenteUrl} onChange={(e) => setFuenteUrl(e.target.value)} />
      </label>

      <button className="boton-primario" disabled={subiendo || ocupado || !archivo || !norma.trim()}>
        {subiendo ? "Subiendo…" : ocupado ? "Hay un reprocesamiento en curso" : "Agregar norma"}
      </button>
      {aviso && <p className="aviso">{aviso}</p>}
    </form>
  );
}
