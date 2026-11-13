// Subida de PDF (RF4): el documento queda pendiente de indexar; no entra a las consultas aún.
import { useRef, useState } from "react";
import { subirPdf } from "../api.js";

const MAX_BYTES = 10 * 1024 * 1024;

export default function SubirPdf({ habilitado }) {
  const inputRef = useRef(null);
  const [subiendo, setSubiendo] = useState(false);
  const [aviso, setAviso] = useState(null);

  async function elegir(e) {
    const archivo = e.target.files[0];
    e.target.value = "";
    if (!archivo) return;
    if (archivo.size > MAX_BYTES) return setAviso({ error: true, texto: "El archivo supera el máximo permitido de 10 MB." });

    setSubiendo(true);
    setAviso(null);
    try {
      const datos = await subirPdf(archivo);
      setAviso({ error: false, texto: `${datos.nombre_guardado} (${datos.paginas} pág.): ${datos.mensaje}` });
    } catch (err) {
      setAviso({ error: true, texto: err.message });
    } finally {
      setSubiendo(false);
    }
  }

  return (
    <div className="subir-pdf">
      <input ref={inputRef} type="file" accept="application/pdf,.pdf" hidden onChange={elegir} />
      <button type="button" className="boton-secundario" disabled={!habilitado || subiendo} onClick={() => inputRef.current.click()}>
        {subiendo ? "Subiendo…" : "Subir PDF"}
      </button>
      {aviso && (
        <div className={`aviso-subida ${aviso.error ? "error" : ""}`} role="status">
          {aviso.texto}
          <button type="button" className="cerrar" aria-label="Cerrar aviso" onClick={() => setAviso(null)}>×</button>
        </div>
      )}
    </div>
  );
}
