// Indicador del estado del motor según GET /health del backend.
export default function EstadoMotor({ estado }) {
  const clase = estado.cargando ? "pendiente" : estado.listo ? "listo" : "caido";
  const texto = estado.cargando ? "Conectando…" : estado.listo ? "Motor listo" : "Motor no disponible";

  return (
    <div className={`estado-motor ${clase}`} title={estado.error || ""}>
      <span className="punto" />
      {texto}
    </div>
  );
}
