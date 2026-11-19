// Pantalla de ingreso: el usuario entra directo al chat (sin datos personales, Ley 1581);
// el administrador escribe su clave, que el backend valida antes de dejarlo entrar.
import { useState } from "react";
import { listarCorpus } from "../api.js";

export default function Ingreso({ aviso, onEntrar }) {
  const [clave, setClave] = useState("");
  const [validando, setValidando] = useState(false);
  const [error, setError] = useState(aviso);

  async function entrarAdmin(e) {
    e.preventDefault();
    setValidando(true);
    setError(null);
    try {
      await listarCorpus(clave); // 200 = clave correcta
      onEntrar("admin", clave);
    } catch (err) {
      setError(err.message);
    } finally {
      setValidando(false);
    }
  }

  return (
    <main className="ingreso">
      <section className="tarjeta rol">
        <h2>Usuario</h2>
        <p>Haz preguntas en lenguaje natural y revisa los artículos que sustentan cada respuesta. No necesitas registrarte.</p>
        <button className="boton-primario" onClick={() => onEntrar("usuario")}>Entrar como usuario</button>
      </section>

      <form className="tarjeta rol" onSubmit={entrarAdmin}>
        <h2>Administrador</h2>
        <p>Agrega normas y actualiza el corpus del chatbot a partir de PDF oficiales.</p>
        <input
          type="password"
          placeholder="Clave de administrador"
          value={clave}
          autoComplete="current-password"
          onChange={(e) => setClave(e.target.value)}
        />
        <button className="boton-secundario" disabled={!clave.trim() || validando}>
          {validando ? "Validando…" : "Entrar como administrador"}
        </button>
        {error && <p className="aviso error">{error}</p>}
      </form>
    </main>
  );
}
