// Punto de entrada del backend: configura Express y monta las rutas.
// Lee el .env de la raíz del repo (PORT, MOTOR_URL, ORIGENES_PERMITIDOS).
require("dotenv").config({ path: require("path").join(__dirname, "..", "..", ".env") });
const express = require("express");
const cors = require("cors");
const rutas = require("./routes/rutas");
const errorView = require("./views/errorView");

const PORT = process.env.PORT || 4000;
const origenes = (process.env.ORIGENES_PERMITIDOS || "")
  .split(",")
  .map((o) => o.trim())
  .filter(Boolean);

const app = express();

// Ley 1581: el log solo guarda método, ruta, estado y tiempo; nunca el cuerpo
app.use((req, res, next) => {
  const inicio = Date.now();
  res.on("finish", () => console.log(`${req.method} ${req.path} ${res.statusCode} ${Date.now() - inicio}ms`));
  next();
});

// RNF3: solo los orígenes de ORIGENES_PERMITIDOS pueden llamar al backend
app.use(
  cors({
    origin: (origin, cb) => {
      if (!origin || origenes.includes(origin)) return cb(null, true);
      const error = new Error("Origen no permitido por CORS.");
      error.status = 403;
      cb(error);
    },
  })
);
app.use(express.json({ limit: "200kb" }));

app.use("/", rutas);

app.use((req, res) => errorView.render(res, 404, "Ruta no encontrada."));

// Errores de CORS, JSON mal formado, tamaño del PDF (multer) y cualquier otro inesperado
app.use((err, req, res, next) => {
  if (err.code === "LIMIT_FILE_SIZE") return errorView.render(res, 413, "El archivo supera el máximo permitido de 10 MB.");
  if (err.name === "MulterError") return errorView.render(res, 422, "Envía un único PDF en el campo 'file'.");
  if (err.type === "entity.parse.failed") return errorView.render(res, 400, "El cuerpo de la petición debe ser un JSON válido.");
  if (err.type === "entity.too.large") return errorView.render(res, 413, "La petición es demasiado grande.");
  if (err.status) return errorView.render(res, err.status, err.message);
  console.error(`Error interno en ${req.path}: ${err.name}`);
  errorView.render(res, 500, "Ocurrió un error interno. Intenta de nuevo en unos minutos.");
});

app
  .listen(PORT, () => console.log(`Backend en http://localhost:${PORT} | orígenes permitidos: ${origenes.join(", ")}`))
  .on("error", (e) => {
    // Puerto ocupado: mensaje claro en vez del stack trace de Node
    console.error(e.code === "EADDRINUSE" ? `El puerto ${PORT} ya está en uso. Cierra el otro proceso o cambia PORT en el .env.` : e.message);
    process.exit(1);
  });
