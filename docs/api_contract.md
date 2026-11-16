# Contrato de la API — `POST /query`

Referencia compartida del equipo (frontend ↔ backend ↔ motor).

## Entrada

```json
{
  "pregunta": "string",
  "historial": [{ "rol": "usuario | asistente", "contenido": "string" }]
}
```

- `pregunta` (string, obligatorio): no puede estar vacía (se ignoran los espacios al inicio y al final) ni pasar de **500 caracteres**.
- `historial` (arreglo, opcional): de máximo **50** mensajes. **Por ahora el motor lo acepta pero NO lo usa**: la respuesta depende solo de `pregunta`. El frontend ya puede enviarlo; cuando el motor lo use, este contrato avisará.

## Salida

```json
{
  "respuesta": "string",
  "articulos_citados": ["Artículo 1"],
  "fragmentos": [
    {
      "id": "string",
      "ubicacion": "string",
      "epigrafe": "string",
      "texto": "string",
      "score": 0.0,
      "norma": "Ley 1801 de 2016",
      "vigencia": "vigente",
      "tema": "string",
      "fuente": "Ley_1801_de_2016.pdf",
      "archivo_fuente": "documentos/leyes/Ley_1801_de_2016.pdf",
      "pagina_inicio": 1,
      "pagina_fin": 2,
      "paginas": [1, 2],
      "ubicaciones_fuente": [
        {
          "archivo": "documentos/leyes/Ley_1801_de_2016.pdf",
          "pagina_inicio": 1,
          "pagina_fin": 2,
          "paginas": [1, 2]
        }
      ]
    }
  ],
  "fuera_de_dominio": false,
  "citas": [
    { "articulo": "Artículo 163", "numeral": "2", "paragrafo": null, "texto": "Art. 163, num. 2", "norma": "Ley 1801 de 2016" }
  ],
  "tema_detectado": "Ingreso a domicilio"
}
```

- `fuera_de_dominio`: `true` si la pregunta no corresponde a **ninguna de las normas cargadas** en el corpus (hoy la Ley 1801 de 2016; ver `normas` en `/health`). La respuesta es entonces «No encontré esa información en las normas cargadas: …».
- **Varias normas** (desde el 16/11, ver [reprocesamiento.md](reprocesamiento.md)): los artículos de la Ley 1801 se citan como siempre (`"Artículo 163"`, `"Art. 163, num. 2"`). Los de otra norma llevan la norma: en `articulos_citados`, `"Ley 769 de 2002, Artículo 131"`; en `citas[].texto`, `"Ley 769, Art. 131, num. 2"`; y `citas[].norma` y `fragmentos[].norma` dicen la norma completa.
- `citas` (**opcional**): detalle de cada cita de la respuesta. `articulos_citados` sigue igual (solo artículos), así que quien no use `citas` no se ve afectado.
  - `articulo`: como en `articulos_citados` (`"Artículo 163"`).
  - `numeral`: número del numeral citado, o `null`.
  - `paragrafo`: número del parágrafo (`"1"`), `"único"` (parágrafo sin número), `"transitorio"`, o `null`.
  - `texto`: forma legible para mostrar (`"Art. 163, num. 2"`, `"Art. 183, par."`, `"Art. 180"`).
  - Solo incluye citas de artículos que estaban en el contexto y cuyo numeral o parágrafo existe en el texto del artículo. Si `fuera_de_dominio` es `true`, va vacío.

- `tema_detectado` (**opcional**): tema que detectó el clasificador temático al leer la pregunta (por ejemplo `"Ingreso a domicilio"`), o `"general"` si no detectó ninguno. Es informativo: el motor lo usa para empujar el orden de la búsqueda hacia ese tema (nunca como filtro), y el frontend puede mostrarlo como etiqueta. Ver [clasificador.md](clasificador.md).
  - Si la pregunta pide un artículo por su número («¿Qué dice el artículo 163?») y ese artículo existe, sus fragmentos van primero en `fragmentos`, aunque su `score` no sea el más alto.
  - Con un empate entre varios temas el nombre es poco informativo; el clasificador interno tiene una confianza que la API no expone.

### Campos de cada elemento de `fragmentos`

| Campo | Tipo | Obligatorio | Descripción |
|---|---|---|---|
| `id` | string | sí | Identificador del fragmento en el corpus |
| `ubicacion` | string | sí | Ubicación jerárquica (libro, título, capítulo, artículo) |
| `epigrafe` | string | sí | Epígrafe del artículo |
| `texto` | string | sí | Texto del fragmento |
| `norma` | string | no | Norma a la que pertenece el fragmento (`"Ley 1801 de 2016"`, `"Ley 769 de 2002"`) |
| `score` | number | sí | Puntaje de relevancia de la recuperación, incluido el empuje del clasificador. **Su escala depende del modo de búsqueda** (`/health` → `busqueda_modo`): coseno en `semantico` (0 a 1), BM25 normalizado en `lexico` (0 a 1) y Reciprocal Rank Fusion en `hibrido` (~0.01 a 0.04). No se pueden comparar scores de modos distintos |
| `vigencia` | string | no | Estado de vigencia. Con la muestra: `vigente`, `modificado`, `inexequible`, `exequible_condicionado`; documentos subidos: `no_verificada`. **Con el corpus de la Fase 1** también: `vigente_modificado`, `vigente_condicionado`, `vigente_modificado_condicionado`, `vigente_con_inexequibilidad_parcial`, `vigente_modificado_con_inexequibilidad_parcial`. Regla para el frontend: **todo lo que no sea `vigente` lleva señal visible** |
| `tema` | string | no | Tema asignado al fragmento en el corpus |
| `fuente` | string | no | Nombre del archivo PDF fuente |
| `archivo_fuente` | string | no | Ruta del PDF relativa a `corpus/` |
| `pagina_inicio`, `pagina_fin` | integer | no | Primera y última página física del PDF que contienen el texto |
| `paginas` | array de integer | no | Páginas físicas exactas que contienen el texto, numeradas desde 1 |
| `ubicaciones_fuente` | array de objetos | no | Ruta y páginas de origen; puede haber varias ubicaciones cuando se fusionaron copias idénticas |
| `fuentes` | array de string | no | Nombres de los PDF con texto idéntico fusionado |

### Origen y uso de `vigencia` y `tema`

- Ambos campos son **opcionales**: si el corpus no los tiene para un fragmento, se omiten y el frontend no debe fallar.
- Sus valores **salen de los metadatos del corpus** (Fase 1); el motor los copia tal cual, sin calcularlos.
- **El frontend debe mostrar la `vigencia` en el panel de fuentes** junto a cada fragmento, con una señal visible cuando no sea `vigente` (`modificado`, `inexequible` o `exequible_condicionado`).
- El frontend puede mostrar el `tema` como etiqueta del fragmento.
- En `texto`, las expresiones declaradas inexequibles aparecen marcadas como `[INEXEQUIBLE: expresión]` (salen de `corpus/anotaciones_vigencia.json`). El frontend puede resaltarlas o tacharlas.
- El frontend puede mostrar `archivo_fuente` y `paginas` para permitir localizar el texto en el PDF. Las páginas son la numeración física del archivo, no necesariamente la numeración impresa en el documento.
- Los campos de fuente y página se copian del corpus; en documentos subidos por `/upload_pdf/` pueden faltar.

## Errores de `POST /query`

Todos devuelven JSON `{ "error": "mensaje en español" }`.

| Código | Cuándo | Ejemplo de `error` |
|---|---|---|
| 422 | Entrada inválida | `"La pregunta no puede estar vacía."` · `"La pregunta es demasiado larga: máximo 500 caracteres."` · `"Falta el campo obligatorio 'pregunta'."` |
| 503 | Ningún modelo de lenguaje pudo responder, o el motor no está listo | `"El servicio está ocupado, intenta de nuevo en unos minutos."` |
| 500 | Error interno inesperado | `"Ocurrió un error interno. Intenta de nuevo en unos minutos."` |

El frontend puede mostrar el campo `error` tal cual al usuario. El mensaje de un 422 no repite el texto enviado.

## `GET /health`

Estado del motor. Siempre responde 200 (la propiedad `listo` indica si puede atender preguntas).

```json
{
  "listo": true,
  "error": null,
  "modelo_embeddings": "intfloat/multilingual-e5-base",
  "estrategia_busqueda": "fragmentos",
  "busqueda_modo": "hibrido",
  "busqueda_expansion": { "activa": true, "entradas": 18 },
  "rrf_k": 60,
  "fragmentos_en_indice": 30,
  "llm_proveedor": "gemini",
  "llm_principal": "gemini-3.5-flash-lite",
  "llm_respaldo": "gemini-3.6-flash",
  "llm_orden": ["gemini", "groq"],
  "llm_respaldo_externo": { "proveedor": "groq", "modelo": "openai/gpt-oss-120b,openai/gpt-oss-20b" },
  "corpus": "corpus_ley_1801.json",
  "normas": [{ "norma": "Ley 1801 de 2016", "articulos": 249 }],
  "reprocesamiento": { "trabajo_activo": null },
  "tiempos_de_carga_s": { "embeddings_e_indice_s": 8.1, "cliente_llm_s": 0.4, "total_s": 8.5 }
}
```

`normas` son las normas cargadas en el índice vigente, con su número de artículos; cambia sin reiniciar cuando termina un reprocesamiento. `reprocesamiento.trabajo_activo` es el id del trabajo en curso, o `null`.

El modelo de embeddings, el índice y el cliente del LLM se cargan **al arrancar el servidor**, no en la primera pregunta. `busqueda_modo` es el modo activo (`semantico`, `lexico` o `hibrido`, según `BUSQUEDA_MODO` en el `.env`), `rrf_k` la constante de la fusión (solo en `hibrido`; `null` en los otros) y `busqueda_expansion` indica si la expansión de consultas con glosario está activa (`BUSQUEDA_EXPANSION`) y cuántas entradas tiene el glosario. `llm_orden` es el orden en que se prueban los proveedores (`LLM_ORDEN` del `.env`; si no está, el de `LLM_PROVEEDOR` primero y Groq después). `llm_respaldo_externo` es el proveedor de otra empresa que responde si los dos modelos de Gemini fallan (Groq, si hay `GROQ_API_KEY` en el `.env`; `null` si no). Si falta la clave del LLM, si `BUSQUEDA_MODO` no existe, si falta el índice BM25 o si se construyó con otro método de preparación de texto que el disponible ahora, `listo` es `false`, `error` explica por qué y `POST /query` responde 503.

## Privacidad (Ley 1581 de 2012)

El motor **no registra el texto de las preguntas, de las respuestas ni del historial** en logs, y no guarda nada en disco ni en base de datos. Los logs solo contienen estado, tiempos, modelo usado y conteos. El historial de conversación debe vivir en el navegador del usuario (sesión), no en el servidor. Quien agregue logs al backend o al motor debe respetar esta regla.

## `POST /upload_pdf/`

Sube un documento PDF **sin regenerar los embeddings** (RF4). Es el primer paso de un flujo de dos pasos. El segundo paso depende del documento:

- **Si es una norma** (p. ej. la Ley 769 de 2002) y se sube con el campo `norma`: un administrador lanza `POST /corpus/reprocesar` (ver «Corpus: reprocesamiento», abajo).
- **Si es un documento complementario sin norma**: reconstruyendo el índice a mano (abajo).

### Por qué dos pasos (RF4)

Generar embeddings es lento y reconstruye el índice con el que responde el buscador. Si cada subida lo hiciera automáticamente, cualquier usuario podría degradar o cambiar el motor sin revisión, y un PDF malo contaminaría las respuestas. Por eso:

1. **Subir** (`POST /upload_pdf/`): la API valida el archivo, lo guarda, extrae su texto y lo registra como `pendiente_de_indexar`. **No toca los índices:** el buscador sigue igual y el documento todavía no aparece en las respuestas.
2. **Indexar** (una persona del equipo, cuando decida): con `POST /corpus/reprocesar` si el documento es una norma; si es un documento complementario, reconstruyendo el índice con los documentos subidos:

   ```bash
   python engine/indexing/build_index.py --estrategia fragmentos --incluir-uploads
   ```

   Por defecto `build_index.py` **no** incluye los documentos subidos. Hay que repetir `--incluir-uploads` en cada reconstrucción (el índice se arma desde cero), y reiniciar el motor para que cargue el índice nuevo. Los documentos pasan a `indexado` en el registro.

Los documentos indexados entran como fragmentos con `tema: "documento complementario"` y `vigencia: "no_verificada"` (nadie ha revisado su texto; el motor avisa de ello en la respuesta). Su `ubicacion` es `"Documento complementario: <nombre guardado>"`.

### Petición

`multipart/form-data` con:

| Campo | Obligatorio | Descripción |
|---|---|---|
| `file` | sí | El PDF |
| `norma` | no | Norma del documento, con tipo, número y año: `"Ley 769 de 2002"`. Necesaria después para `POST /corpus/reprocesar` (también se puede dar ahí) |
| `fuente_url` | no | URL oficial de donde se descargó (`http(s)://…`, máximo 500 caracteres) |

### Respuesta 200

```json
{
  "id": "Ley_769_de_2002_20261116-160512",
  "nombre_guardado": "Ley_769_de_2002_20261116-160512.pdf",
  "paginas": 56,
  "caracteres": 245310,
  "estado": "pendiente_de_indexar",
  "norma": "Ley 769 de 2002",
  "fuente_url": "https://www.funcionpublica.gov.co/eva/gestornormativo/norma_pdf.php?i=5557",
  "mensaje": "Documento guardado como Ley 769 de 2002. Todavía NO está disponible en las consultas (...): para incorporarlo, un administrador debe lanzar POST /corpus/reprocesar con id «...»."
}
```

`id` es lo que hay que mandar a `POST /corpus/reprocesar`. `norma` y `fuente_url` son `null` si no se enviaron.

### Validaciones y errores

Todos devuelven `{ "error": "mensaje en español" }`.

| Código | Cuándo |
|---|---|
| 413 | El archivo pesa más de **10 MB** |
| 422 | No es un PDF real (la cabecera `%PDF-` debe estar en los primeros 1024 bytes, como permite el formato; no basta con la extensión), está dañado, tiene contraseña, no contiene texto extraíble (p. ej. escaneado), falta el campo `file`, la `norma` no tiene la forma «Ley 769 de 2002» o la `fuente_url` no es una URL http(s) |

### Qué se guarda y dónde

En `corpus/uploads/` (ignorada por git):

- `<nombre>_<AAAAMMDD-HHMMSS>.pdf` y `.txt` (texto extraído). El nombre original se limpia: sin carpetas ni `../`, solo letras, números, `_` y `-`; la fecha y hora evitan sobrescribir.
- `pendientes.json`: registro con `id`, `nombre`, `texto`, `fecha`, `paginas`, `caracteres`, `estado` (`pendiente_de_indexar`, `indexado` o `procesado`) y, si se enviaron, `norma` y `fuente_url`. `procesado` = incorporado como norma con `POST /corpus/reprocesar`.

Por privacidad, los logs no registran el nombre ni el contenido de los documentos, solo tamaño, páginas y caracteres.

## Corpus: reprocesamiento

Incorporar una norma nueva a las consultas **sin reconstruir todo el índice ni apagar el motor**. Detalle, diagrama, tiempos y limitaciones: [reprocesamiento.md](reprocesamiento.md).

| Endpoint | Qué hace | Respuestas |
|---|---|---|
| `POST /corpus/reprocesar` | Lanza en segundo plano la incorporación de un PDF ya subido. **Requiere la cabecera `X-Admin-Token`** con el `ADMIN_TOKEN` del `.env` del motor. Cuerpo JSON: `{"id": "<id del PDF subido>", "norma": "Ley 769 de 2002" (opcional si se dio al subirlo), "fuente_url": "…" (opcional)}` | **202** `{trabajo_id, estado: "en_cola", consultar}` · **401** sin token o token inválido · **404** no existe un documento con ese id · **409** ya hay un trabajo en curso (`trabajo_activo`) · **422** falta la norma o no tiene la forma «Ley 769 de 2002», o es la Ley 1801 · **503** el motor no tiene `ADMIN_TOKEN` configurado |
| `GET /corpus/reprocesar/{trabajo_id}` | Estado del trabajo | **200** `{trabajo_id, documento, norma, estado, progreso, articulos_procesados, fragmentos_nuevos, error, creado, inicio, fin, duracion_s, tiempos_s}` · **404** no existe (o el motor se reinició: los trabajos viven en memoria) |
| `GET /corpus/documentos` | Normas cargadas y documentos subidos | **200** `{normas: [{norma, titulo, articulos, base, archivo, fuente_url, fecha_carga, vigencia_verificada}], documentos: [{id, nombre, fecha, paginas, caracteres, estado, norma, fuente_url, articulos, fecha_procesado}]}` |

`estado` de un trabajo: `en_cola` → `extrayendo` → `indexando` → `listo` (o `error`, con el motivo en `error`). `progreso` va de 0 a 100. Solo hay un trabajo a la vez. Mientras corre, `POST /query` sigue respondiendo con los índices anteriores; al terminar bien, el motor pasa a los nuevos sin reiniciarse. Si falla, se queda con los anteriores.
