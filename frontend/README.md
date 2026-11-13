# Frontend (React + Vite)

Interfaz de chat del chatbot RAG sobre la Ley 1801 de 2016. Solo habla con el backend Express.

## Estructura

```
frontend/src/
├── main.jsx                   Monta la app
├── App.jsx                    Estado global: historial (sessionStorage), /health cada 10 s, fuentes elegidas
├── api.js                     Llamadas al backend (/health, /query, /upload_pdf) con mensajes en español
├── styles.css                 Estilos (colores en variables :root)
└── components/
    ├── AvisoLegal.jsx         Aviso siempre visible: herramienta informativa, no asesoría jurídica
    ├── EstadoMotor.jsx        Indicador "Motor listo / no disponible"
    ├── Chat.jsx               Mensajes, caja de pregunta (máx. 500 caracteres), sugerencias
    ├── Mensaje.jsx            Burbuja con citas (RF2), tema y botón de fragmentos
    ├── PanelFuentes.jsx       Fragmentos recuperados con vigencia e inexequibles tachados (RF5)
    └── SubirPdf.jsx           Subida de PDF (RF4) y aviso de que queda pendiente de indexar
```

## Comportamiento

- El chat se habilita solo cuando `/health` responde `listo: true`.
- El historial vive en `sessionStorage` (se borra al cerrar la pestaña) y se envía al backend (máx. 50 mensajes).
- El `score` no se muestra. Toda vigencia distinta de `vigente` lleva señal ⚠.
- Si `fuera_de_dominio` es `true`, los fragmentos se marcan como no relacionados.

## Ejecutar

```bash
cd frontend
npm install
npm run dev
```

Abre `http://localhost:5173`. Si el backend no corre en `http://localhost:4000`, copia `.env.example` a `.env` y cambia `VITE_API_URL`.
