// Pestaña de administración (solo rol admin): nutre el corpus con PDF de normas.
// Flujo: subir PDF (con su norma) -> reprocesar -> consultar el estado cada 4 s hasta listo o error.
// Si el backend rechaza la clave (401), se cierra la sesión de administrador.
import { useEffect, useState } from "react";
import { listarCorpus, reprocesar, estadoTrabajo } from "../api.js";
import FormNorma from "./FormNorma.jsx";
import ProgresoTrabajo from "./ProgresoTrabajo.jsx";
import ListaCorpus from "./ListaCorpus.jsx";

const INTERVALO_MS = 4000;

export default function Administracion({ clave, trabajoActivo, onCorpusActualizado, onClaveInvalida }) {
  const [aviso, setAviso] = useState(null);
  const [corpus, setCorpus] = useState({ normas: [], documentos: [] });
  const [trabajo, setTrabajo] = useState(null);

  function manejarError(e) {
    if (e.status === 401) return onClaveInvalida(e.message);
    setAviso({ error: true, texto: e.message });
  }

  const cargarCorpus = () => listarCorpus(clave).then(setCorpus).catch(manejarError);

  useEffect(() => {
    cargarCorpus();
  }, [clave]);

  async function incorporar(id) {
    setAviso(null);
    try {
      setTrabajo(await reprocesar(clave, id));
    } catch (e) {
      // 409: ya hay un trabajo en curso; se sigue ese en vez de lanzar otro
      if (e.status === 409 && e.datos.trabajo_activo) {
        setAviso({ error: false, texto: "Ya hay un reprocesamiento en curso; se muestra su avance." });
        setTrabajo({ trabajo_id: e.datos.trabajo_activo, estado: "en_cola", progreso: 0 });
      } else manejarError(e);
      cargarCorpus();
    }
  }

  // Si ya hay un trabajo corriendo en el motor, se muestra su avance
  useEffect(() => {
    if (trabajoActivo && !trabajo) setTrabajo({ trabajo_id: trabajoActivo, estado: "en_cola", progreso: 0 });
  }, [trabajoActivo, trabajo]);

  // Consulta el estado del trabajo mientras no termine
  const enCurso = trabajo && !["listo", "error"].includes(trabajo.estado);
  useEffect(() => {
    if (!enCurso) return;
    const id = setTimeout(async () => {
      try {
        const t = await estadoTrabajo(clave, trabajo.trabajo_id);
        setTrabajo(t);
        if (t.estado === "listo" || t.estado === "error") {
          cargarCorpus();
          onCorpusActualizado();
        }
      } catch (e) {
        if (e.status === 401) return manejarError(e);
        setTrabajo((t) => ({ ...t, estado: "error", error: e.message }));
      }
    }, INTERVALO_MS);
    return () => clearTimeout(id);
  }, [clave, trabajo]);

  return (
    <main className="admin">
      <h2>Administración del corpus</h2>
      {aviso && <p className={`aviso ${aviso.error ? "error" : ""}`}>{aviso.texto}</p>}

      <FormNorma clave={clave} ocupado={enCurso} onSubido={incorporar} onError={manejarError} />
      {trabajo && <ProgresoTrabajo trabajo={trabajo} onCerrar={enCurso ? null : () => setTrabajo(null)} />}
      <ListaCorpus corpus={corpus} ocupado={enCurso} onIncorporar={incorporar} onActualizar={cargarCorpus} />
    </main>
  );
}
