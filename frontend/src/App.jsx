// Componente raíz: guarda el historial (sessionStorage), el estado del motor y el mensaje
// cuyas fuentes se muestran. El historial vive solo en el navegador (Ley 1581 de 2012).
import { useEffect, useState } from "react";
import { obtenerEstado, enviarPregunta } from "./api.js";
import AvisoLegal from "./components/AvisoLegal.jsx";
import EstadoMotor from "./components/EstadoMotor.jsx";
import Chat from "./components/Chat.jsx";
import PanelFuentes from "./components/PanelFuentes.jsx";

const CLAVE_HISTORIAL = "chat_ley1801_historial";

export default function App() {
  const [mensajes, setMensajes] = useState(() => {
    try {
      return JSON.parse(sessionStorage.getItem(CLAVE_HISTORIAL)) || [];
    } catch {
      return [];
    }
  });
  const [estado, setEstado] = useState({ listo: false, error: null, cargando: true });
  const [enviando, setEnviando] = useState(false);
  const [seleccionado, setSeleccionado] = useState(null);

  useEffect(() => {
    try {
      sessionStorage.setItem(CLAVE_HISTORIAL, JSON.stringify(mensajes));
    } catch {
      /* sin sessionStorage el chat sigue funcionando en memoria */
    }
  }, [mensajes]);

  // Consulta /health al abrir y cada 10 s: el chat solo se habilita con listo=true
  useEffect(() => {
    const revisar = () =>
      obtenerEstado()
        .then((d) => setEstado({ ...d, cargando: false }))
        .catch((e) => setEstado({ listo: false, error: e.message, cargando: false }));
    revisar();
    const id = setInterval(revisar, 10000);
    return () => clearInterval(id);
  }, []);

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

  function nuevaConversacion() {
    setMensajes([]);
    setSeleccionado(null);
  }

  // Si no hay uno elegido, el panel muestra las fuentes de la última respuesta
  const indiceFuentes = seleccionado ?? mensajes.findLastIndex((m) => m.rol === "asistente");
  const mensajeFuentes = indiceFuentes >= 0 ? mensajes[indiceFuentes] : null;

  return (
    <div className="app">
      <header className="cabecera">
        <div>
          <h1>Asistente del Código Nacional de Policía</h1>
          <p>Consultas sobre la Ley 1801 de 2016 · Código Nacional de Seguridad y Convivencia Ciudadana</p>
        </div>
        <EstadoMotor estado={estado} />
      </header>

      <AvisoLegal />

      <main className="contenido">
        <Chat
          mensajes={mensajes}
          habilitado={estado.listo && !enviando}
          enviando={enviando}
          estado={estado}
          indiceFuentes={indiceFuentes}
          onPreguntar={preguntar}
          onVerFuentes={setSeleccionado}
          onNuevaConversacion={nuevaConversacion}
        />
        <PanelFuentes mensaje={mensajeFuentes} />
      </main>
    </div>
  );
}
