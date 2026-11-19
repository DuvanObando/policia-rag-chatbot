// Rutas del backend: cada endpoint apunta a su controlador.
// Las rutas de administración (nutrir el corpus) exigen la clave de administrador.
const express = require("express");
const multer = require("multer");
const chatController = require("../controllers/chatController");
const estadoController = require("../controllers/estadoController");
const documentoController = require("../controllers/documentoController");
const corpusController = require("../controllers/corpusController");
const { verificarClave } = require("../controllers/adminController");

const router = express.Router();
const upload = multer({ storage: multer.memoryStorage(), limits: { fileSize: 10 * 1024 * 1024, files: 1 } });

// Públicas: chat
router.get("/health", estadoController.consultarEstado);
router.post("/query", chatController.preguntar);

// Administración: subir PDF -> reprocesar -> consultar estado
router.post("/upload_pdf", verificarClave, upload.single("file"), documentoController.subirPdf);
router.post("/corpus/reprocesar", verificarClave, corpusController.reprocesar);
router.get("/corpus/reprocesar/:trabajoId", verificarClave, corpusController.estadoTrabajo);
router.get("/corpus/documentos", verificarClave, corpusController.documentos);

module.exports = router;
