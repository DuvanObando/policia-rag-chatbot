# Frontend (React + Vite)

Interfaz de chat del chatbot RAG. Solo habla con el backend Express.

## Estructura

```
frontend/src/
├── main.jsx                   Monta la app
├── App.jsx                    Sesión por rol, pestañas, historial (sessionStorage), /health cada 10 s
├── api.js                     Llamadas al backend con mensajes en español
├── styles.css                 Estilos (colores en variables :root)
└── components/
    ├── AvisoLegal.jsx         Aviso siempre visible: herramienta informativa, no asesoría jurídica
    ├── EstadoMotor.jsx        Indicador "Motor listo / no disponible"
    ├── Ingreso.jsx            Pantalla inicial: entrar como usuario o como administrador
    ├── Chat.jsx               Mensajes, caja de pregunta (máx. 500 caracteres), sugerencias
    ├── Mensaje.jsx            Burbuja con citas (RF2), tema y botón de fragmentos
    ├── PanelFuentes.jsx       Fragmentos con vigencia, norma e inexequibles tachados (RF5)
    ├── Administracion.jsx     Reprocesamiento y consulta del estado cada 4 s (solo admin)
    ├── FormNorma.jsx          Subir el PDF de una norma (RF4) y lanzar su incorporación
    ├── ProgresoTrabajo.jsx    Barra de progreso del reprocesamiento
    └── ListaCorpus.jsx        Normas cargadas y documentos subidos
```

## Roles

| Rol | Cómo entra | Qué ve |
|---|---|---|
| Usuario | Botón «Entrar como usuario», sin clave ni datos personales | Solo el chat y el panel de fuentes |
| Administrador | Clave `ADMIN_CLAVE` del `.env` del backend (el backend la valida) | Pestañas Chat y Administración |

- La sesión (rol y, para el administrador, su clave) se guarda en `sessionStorage`: se mantiene al recargar y se borra al cerrar la pestaña.
- **Salir** cierra la sesión y borra la conversación, por si el equipo es compartido.
- Si el backend rechaza la clave (401), la sesión de administrador se cierra y vuelve la pantalla de ingreso.
- Las rutas de administración las protege el backend, no solo la interfaz: sin la clave responden 401.

## Comportamiento

- El chat se habilita solo cuando `/health` responde `listo: true`.
- El historial vive en `sessionStorage` (se borra al cerrar la pestaña) y se envía al backend (máx. 50 mensajes).
- El `score` no se muestra. Toda vigencia distinta de `vigente` lleva señal ⚠.
- Si `fuera_de_dominio` es `true`, los fragmentos se marcan como no relacionados.
- Con más de una norma cargada, la cabecera y los textos del chat las nombran (campo `normas` de `/health`).

## Administración (agregar normas)

Solo el administrador nutre el corpus, desde la pestaña **Administración**.

1. **Agregar una norma**: PDF oficial, norma («Ley 769 de 2002») y URL oficial opcional. El PDF se sube sin cambiar las consultas.
2. La interfaz lanza el reprocesamiento y muestra el avance (en cola → extrayendo → indexando → listo).
3. Al terminar, la norma aparece en la lista y en la cabecera, y el chat ya la usa. Si falla, el chat sigue con el corpus anterior.

Un documento pendiente se puede incorporar después con el botón **Incorporar** de la lista.

## Ejecutar

```bash
cd frontend
npm install
npm run dev
```

Abre `http://localhost:5173`. Si el backend no corre en `http://localhost:4000`, copia `.env.example` a `.env` y cambia `VITE_API_URL`.
