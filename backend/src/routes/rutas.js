// Rutas del backend: cada endpoint apunta a su controlador.
const express = require("express");
const multer = require("multer");
const chatController = require("../controllers/chatController");
const estadoController = require("../controllers/estadoController");
const documentoController = require("../controllers/documentoController");

const router = express.Router();
const upload = multer({ storage: multer.memoryStorage(), limits: { fileSize: 10 * 1024 * 1024, files: 1 } });

router.get("/health", estadoController.consultarEstado);
router.post("/query", chatController.preguntar);
router.post("/upload_pdf", upload.single("file"), documentoController.subirPdf);

module.exports = router;
