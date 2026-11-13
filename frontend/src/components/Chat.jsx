// Ventana de conversación: lista de mensajes, caja de pregunta y subida de PDF.
import { useEffect, useRef, useState } from "react";
import Mensaje from "./Mensaje.jsx";
import SubirPdf from "./SubirPdf.jsx";

const MAX_PREGUNTA = 500;
const SUGERENCIAS = [
  "¿Qué es una medida correctiva y cuáles contempla el Código?",
  "¿Puede la policía ingresar a un domicilio sin orden escrita?",
  "¿Está permitido el consumo de sustancias psicoactivas en parques?",
  "¿Qué consecuencias tiene no pagar una multa?",
];

export default function Chat({ mensajes, habilitado, enviando, estado, indiceFuentes, onPreguntar, onVerFuentes, onNuevaConversacion }) {
  const [texto, setTexto] = useState("");
  const listaRef = useRef(null);

  // Baja al último mensaje sin mover el resto de la página
  useEffect(() => {
    listaRef.current?.scrollTo({ top: listaRef.current.scrollHeight, behavior: "smooth" });
  }, [mensajes, enviando]);

  function enviar(e) {
    e.preventDefault();
    if (!habilitado || !texto.trim()) return;
    onPreguntar(texto.trim());
    setTexto("");
  }

  return (
    <section className="chat">
      <div className="chat-barra">
        <h2>Conversación</h2>
        <button className="boton-secundario" onClick={onNuevaConversacion} disabled={enviando || !mensajes.length}>
          Nueva conversación
        </button>
      </div>

      <div className="mensajes" ref={listaRef}>
        {!mensajes.length && (
          <div className="bienvenida">
            <p>Pregunta en lenguaje natural sobre multas, comportamientos contrarios a la convivencia, medidas correctivas o procedimientos de policía. Cada respuesta cita los artículos que la sustentan.</p>
            <div className="sugerencias">
              {SUGERENCIAS.map((s) => (
                <button key={s} onClick={() => onPreguntar(s)} disabled={!habilitado}>
                  {s}
                </button>
              ))}
            </div>
          </div>
        )}

        {mensajes.map((m, i) => (
          <Mensaje key={i} mensaje={m} activo={i === indiceFuentes} onVerFuentes={() => onVerFuentes(i)} />
        ))}

        {enviando && (
          <div className="mensaje asistente pensando">
            <span /> <span /> <span /> Buscando en el Código…
          </div>
        )}
      </div>

      {!estado.listo && !estado.cargando && (
        <div className="alerta">
          El chat está deshabilitado porque el motor no está listo. {estado.error}
        </div>
      )}

      <form className="caja-pregunta" onSubmit={enviar}>
        <textarea
          value={texto}
          maxLength={MAX_PREGUNTA}
          rows={2}
          placeholder={habilitado ? "Escribe tu pregunta sobre el Código Nacional de Policía…" : "Esperando al motor…"}
          disabled={!habilitado}
          onChange={(e) => setTexto(e.target.value)}
          onKeyDown={(e) => e.key === "Enter" && !e.shiftKey && enviar(e)}
        />
        <div className="caja-acciones">
          <SubirPdf habilitado={!enviando} />
          <span className="contador">{texto.length}/{MAX_PREGUNTA}</span>
          <button type="submit" className="boton-primario" disabled={!habilitado || !texto.trim()}>
            Enviar
          </button>
        </div>
      </form>
    </section>
  );
}
