// Componente raíz: sesión por rol (usuario: chat; admin: chat + administración), historial,
// estado del motor y normas cargadas. Sesión e historial viven solo en el navegador (Ley 1581).
import { useEffect, useState } from "react";
import { obtenerEstado, enviarPregunta } from "./api.js";
import AvisoLegal from "./components/AvisoLegal.jsx";
import EstadoMotor from "./components/EstadoMotor.jsx";
import Ingreso from "./components/Ingreso.jsx";
import Chat from "./components/Chat.jsx";
import PanelFuentes from "./components/PanelFuentes.jsx";
import Administracion from "./components/Administracion.jsx";

const CLAVE_HISTORIAL = "chat_ley1801_historial";
const CLAVE_SESION = "chat_ley1801_sesion"; // { rol: "usuario" | "admin", clave? }

const leer = (clave, porDefecto) => {
  try {
    return JSON.parse(sessionStorage.getItem(clave)) || porDefecto;
  } catch {
    return porDefecto;
  }
};

export default function App() {
  const [sesion, setSesion] = useState(() => leer(CLAVE_SESION, null));
  const [avisoIngreso, setAvisoIngreso] = useState(null);
  const [mensajes, setMensajes] = useState(() => leer(CLAVE_HISTORIAL, []));
  const [estado, setEstado] = useState({ listo: false, error: null, cargando: true, normas: [] });
  const [enviando, setEnviando] = useState(false);
  const [seleccionado, setSeleccionado] = useState(null);
  const [pestana, setPestana] = useState("chat");

  // Sesión e historial en sessionStorage: se borran al cerrar la pestaña del navegador
  useEffect(() => {
    try {
      sessionStorage.setItem(CLAVE_HISTORIAL, JSON.stringify(mensajes));
      sesion ? sessionStorage.setItem(CLAVE_SESION, JSON.stringify(sesion)) : sessionStorage.removeItem(CLAVE_SESION);
    } catch {
      /* sin sessionStorage todo sigue funcionando en memoria */
    }
  }, [mensajes, sesion]);

  // /health al abrir, cada 10 s y al terminar un reprocesamiento: habilita el chat y trae las normas
  const revisarEstado = () =>
    obtenerEstado()
      .then((d) => setEstado({ ...d, cargando: false }))
      .catch((e) => setEstado({ listo: false, error: e.message, cargando: false, normas: [] }));

  useEffect(() => {
    revisarEstado();
    const id = setInterval(revisarEstado, 10000);
    return () => clearInterval(id);
  }, []);

  function entrar(rol, clave) {
    setSesion(rol === "admin" ? { rol, clave } : { rol });
    setAvisoIngreso(null);
    setPestana("chat");
  }

  // Al salir se borra también la conversación, por si el equipo es compartido
  function salir(aviso = null) {
    setSesion(null);
    setAvisoIngreso(aviso);
    setMensajes([]);
    setSeleccionado(null);
  }

  async function preguntar(pregunta) {
    // El motor acepta máximo 50 mensajes de historial; los de error no se envían
    const historial = mensajes
      .filter((m) => m.rol !== "error")
      .slice(-50)
      .map((m) => ({ rol: m.rol, contenido: m.contenido }));
    setMensajes((prev) => [...prev, { rol: "usuario", contenido: pregunta }]);
    setEnviando(true);
    try {
      const datos = await enviarPregunta(pregunta, historial);
      setMensajes((prev) => [...prev, { rol: "asistente", contenido: datos.respuesta, datos }]);
      setSeleccionado(null);
    } catch (e) {
      setMensajes((prev) => [...prev, { rol: "error", contenido: e.message }]);
    } finally {
      setEnviando(false);
    }
  }

  // Si no hay uno elegido, el panel muestra las fuentes de la última respuesta
  const indiceFuentes = seleccionado ?? mensajes.findLastIndex((m) => m.rol === "asistente");
  const mensajeFuentes = indiceFuentes >= 0 ? mensajes[indiceFuentes] : null;

  // Con una sola norma se mantiene el nombre del Código; con varias, se listan las cargadas
  const nombresNormas = estado.normas.map((n) => n.norma);
  const variasNormas = nombresNormas.length > 1;
  const esAdmin = sesion?.rol === "admin";

  return (
    <div className="app">
      <header className="cabecera">
        <div>
          <h1>{variasNormas ? "Asistente de consultas normativas" : "Asistente del Código Nacional de Policía"}</h1>
          <p>
            {variasNormas
              ? `Normas cargadas: ${nombresNormas.join(" · ")}`
              : "Consultas sobre la Ley 1801 de 2016 · Código Nacional de Seguridad y Convivencia Ciudadana"}
          </p>
        </div>
        <div className="cabecera-acciones">
          {esAdmin && (
            <nav className="pestanas">
              <button className={pestana === "chat" ? "activa" : ""} onClick={() => setPestana("chat")}>Chat</button>
              <button className={pestana === "admin" ? "activa" : ""} onClick={() => setPestana("admin")}>Administración</button>
            </nav>
          )}
          <EstadoMotor estado={estado} />
          {sesion && (
            <div className="sesion">
              <span>{esAdmin ? "Administrador" : "Usuario"}</span>
              <button onClick={() => salir()}>Salir</button>
            </div>
          )}
        </div>
      </header>

      <AvisoLegal />

      {!sesion && <Ingreso aviso={avisoIngreso} onEntrar={entrar} />}

      {sesion && (!esAdmin || pestana === "chat") && (
        <main className="contenido">
          <Chat
            mensajes={mensajes}
            habilitado={estado.listo && !enviando}
            enviando={enviando}
            estado={estado}
            normas={nombresNormas}
            indiceFuentes={indiceFuentes}
            onPreguntar={preguntar}
            onVerFuentes={setSeleccionado}
            onNuevaConversacion={() => { setMensajes([]); setSeleccionado(null); }}
          />
          <PanelFuentes mensaje={mensajeFuentes} />
        </main>
      )}

      {esAdmin && pestana === "admin" && (
        <Administracion
          clave={sesion.clave}
          trabajoActivo={estado.trabajo_activo}
          onCorpusActualizado={revisarEstado}
          onClaveInvalida={salir}
        />
      )}
    </div>
  );
}
