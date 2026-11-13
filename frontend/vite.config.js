import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

// Puerto 5173: debe estar en ORIGENES_PERMITIDOS del .env para que el backend acepte las peticiones
export default defineConfig({
  plugins: [react()],
  server: { port: 5173, strictPort: true },
});
