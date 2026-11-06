require("dotenv").config({ path: require("path").join(__dirname, "..", "..", ".env") });
const express = require("express");
const cors = require("cors");
const multer = require("multer");

const PORT = process.env.PORT || 4000;
const MOTOR_URL = process.env.MOTOR_URL || "http://localhost:8000";
const origenes = (process.env.ORIGENES_PERMITIDOS || "")
  .split(",")
  .map((o) => o.trim())
  .filter(Boolean);

const app = express();
const upload = multer({ storage: multer.memoryStorage() });

// CORS restringido a los orígenes definidos en ORIGENES_PERMITIDOS
app.use(
  cors({
    origin: (origin, cb) => {
      if (!origin || origenes.includes(origin)) return cb(null, true);
      cb(new Error("Origen no permitido por CORS"));
    },
  })
);
app.use(express.json());

app.post("/query", async (req, res) => {
  try {
    const r = await fetch(`${MOTOR_URL}/query`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(req.body),
    });
    res.status(r.status).json(await r.json());
  } catch (e) {
    res.status(502).json({ error: "Motor no disponible" });
  }
});

app.post("/upload_pdf", upload.single("file"), async (req, res) => {
  try {
    if (!req.file) return res.status(400).json({ error: "Falta el archivo" });
    const form = new FormData();
    form.append("file", new Blob([req.file.buffer]), req.file.originalname);
    const r = await fetch(`${MOTOR_URL}/upload_pdf/`, { method: "POST", body: form });
    res.status(r.status).json(await r.json());
  } catch (e) {
    res.status(502).json({ error: "Motor no disponible" });
  }
});

app.listen(PORT, () => console.log(`Backend en http://localhost:${PORT}`));
