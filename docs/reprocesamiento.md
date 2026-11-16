# Reprocesamiento del corpus: agregar normas nuevas desde un PDF

Desde el 16/11 el motor puede **incorporar una norma nueva** (por ejemplo la Ley 769 de 2002, Código Nacional de Tránsito Terrestre) a partir de su PDF oficial, **sin reconstruir todo el índice, sin reiniciarse y sin dejar de responder** mientras trabaja. La Ley 1801 de 2016 sigue siendo la norma base y no cambia.

Contrato de los endpoints: [api_contract.md](api_contract.md), secciones «POST /upload_pdf/» y «Corpus: reprocesamiento».

## Flujo

```mermaid
sequenceDiagram
    autonumber
    actor Admin as Administrador (frontend → backend)
    participant API as Motor (FastAPI)
    participant Up as corpus/uploads
    participant Job as Trabajo en segundo plano
    participant Pipe as procesar_pdf.py (Wilder)
    participant Idx as Índices (FAISS + BM25)

    Admin->>API: POST /upload_pdf/ (file, norma, fuente_url)
    API->>Up: guarda PDF + texto, estado pendiente_de_indexar
    API-->>Admin: 200 {id} — RF4: no se tocan los índices
    Admin->>API: POST /corpus/reprocesar {id} + X-Admin-Token
    API->>Job: lanza (uno a la vez; si hay otro: 409)
    API-->>Admin: 202 {trabajo_id}
    Job->>Pipe: procesar_pdf(ruta, norma, fuente_url) [extrayendo]
    Pipe-->>Job: lista de artículos (10 claves)
    Job->>Job: valida la salida
    Job->>Idx: embeddings SOLO de los artículos nuevos;<br/>copia de FAISS + BM25 de las dos estrategias [indexando]
    Job->>Idx: guarda en indexes/<e>.nuevo y cambia carpetas
    Job->>API: instala la versión nueva en memoria (cambio atómico)
    loop cada 3-5 s
        Admin->>API: GET /corpus/reprocesar/{trabajo_id}
        API-->>Admin: estado, progreso, articulos_procesados, error
    end
    Note over API,Idx: Mientras tanto POST /query responde con los índices anteriores
```

Estados del trabajo: `en_cola` → `extrayendo` (5 %) → `indexando` (30 % estrategia `articulo`, 60 % estrategia `fragmentos`, 92 % cambio de carpetas) → `listo` (100 %), o `error` con el motivo.

## Qué pasa por dentro

| Pieza | Archivo | Qué hace |
|---|---|---|
| Normas | [`engine/indexing/normas.py`](../engine/indexing/normas.py) | Normaliza `"ley 769 de 2002"` → `"Ley 769 de 2002"`, arma los ids (`ley769-art-131`; la Ley 1801 sigue con `art-140`), nombres de archivo y títulos |
| Extracción | [`corpus/pipeline/procesar_pdf.py`](../corpus/pipeline/procesar_pdf.py) | PDF → lista de artículos. Versión básica (pypdf, parte por «ARTÍCULO N», vigencia `no_verificada`); **Wilder reemplaza el interior** sin cambiar la firma ni la salida ([su guía](guia-companeros/wilder.md)) |
| Reprocesamiento | [`engine/indexing/reprocesar.py`](../engine/indexing/reprocesar.py) | Valida la salida, calcula embeddings solo de lo nuevo, arma la versión nueva de cada estrategia, la guarda y hace el cambio. También la línea de comandos |
| Búsqueda | [`engine/retrieval/search.py`](../engine/retrieval/search.py) | Índice versionado en memoria (`Version`): cada consulta usa una sola versión; `instalar_version` la cambia de una vez |
| Generación | [`engine/generation/prompt.py`](../engine/generation/prompt.py), [`citas.py`](../engine/generation/citas.py), [`responder.py`](../engine/generation/responder.py) | El dominio del prompt son las normas cargadas; las citas de otras normas llevan la norma: `(Ley 769, Art. 131, num. 2)` |

Detalles importantes:

- **Incremental:** solo se calculan embeddings de los artículos (y trozos) nuevos. El índice FAISS existente se copia y se le agregan los vectores; si la norma ya estaba cargada, sus vectores se quitan antes (`remove_ids`), así que volver a procesarla **reemplaza** la versión anterior. BM25 se recalcula con los tokens guardados más los nuevos, usando el **mismo método de tokenización con que se construyó el índice** (aunque el entorno tenga otro disponible, p. ej. spaCy en Docker).
- **Todo o nada:** se preparan las dos estrategias (`articulo` y `fragmentos`) en `indexes/<e>.nuevo/`. Solo si las dos salen bien se guarda el JSON de la norma, se cambian las carpetas (`<e>` → `<e>.anterior`, `<e>.nuevo` → `<e>`) y se instala la versión nueva en memoria. Si algo falla, el motor sigue con la versión anterior y las carpetas vuelven como estaban.
- **Persistente:** los índices nuevos quedan en disco; si el motor se reinicia, arranca con la norma ya cargada. La lista de normas adicionales va en `metadatos.json` (`corpus_adicionales`).
- **El corpus base no se toca:** cada norma nueva se guarda aparte en `corpus/procesados/<norma>.json` (p. ej. `ley_769_de_2002.json`). `corpus_ley_1801.json` nunca se edita.
- **Artículos muy largos:** el small-to-big manda al LLM el artículo completo, salvo los de más de 12.000 caracteres (el art. 131 de la Ley 769 tiene 28.000): de esos va el trozo encontrado con sus vecinos y una nota `[EXTRACTO…]`. El artículo más largo de la Ley 1801 tiene unos 9.000, así que la Ley 1801 no cambia.

## Endpoints

| Endpoint | Protección | Respuesta |
|---|---|---|
| `POST /upload_pdf/` (`file`, `norma`, `fuente_url` opcionales) | — | 200 `{id, …}`; no reindexa (RF4) |
| `POST /corpus/reprocesar` `{"id": "...", "norma": "...", "fuente_url": "..."}` | Cabecera `X-Admin-Token` = `ADMIN_TOKEN` del `.env` | 202 `{trabajo_id}` · 401 · 404 · 409 · 422 · 503 |
| `GET /corpus/reprocesar/{trabajo_id}` | — | 200 estado · 404 |
| `GET /corpus/documentos` | — | 200 normas cargadas y documentos subidos |
| `GET /health` | — | ahora incluye `normas` (con número de artículos) y `reprocesamiento.trabajo_activo` |

El `ADMIN_TOKEN` se genera con `python -c "import secrets; print(secrets.token_urlsafe(32))"` y va solo en el `.env` del motor (y del backend, que lo reenvía). **Nunca en el frontend.** Se compara en tiempo constante (`hmac.compare_digest`).

## Prueba de punta a punta con la Ley 769 de 2002 (16/11)

PDF oficial: Función Pública, <https://www.funcionpublica.gov.co/eva/gestornormativo/norma_pdf.php?i=5557> (56 páginas). Equipo: portátil del equipo, CPU, sin GPU; LLM Groq `openai/gpt-oss-120b`.

| Paso | Resultado |
|---|---|
| Antes: «¿Cuánto es la multa por no portar la licencia de conducción?» | `fuera_de_dominio: true` («No encontré esa información en las normas cargadas: Ley 1801 de 2016…») |
| Sin token / token incorrecto | **401** / **401** |
| Reprocesar un documento que no existe / consultar un trabajo que no existe | **404** / **404** |
| `POST /upload_pdf/` con `norma="Ley 769 de 2002"` | **200 en 63,3 s** (pypdf es lento con este PDF) |
| `/health` después de subir | igual que antes: solo Ley 1801, 471 fragmentos (**RF4**) |
| `POST /corpus/reprocesar` | **202 en 0,02 s** |
| Un segundo `POST /corpus/reprocesar` mientras corre el primero | **409** con `trabajo_activo` |
| Trabajo completo | **`listo` en 582 s (9 min 42 s)**: extracción 76,9 s (167 artículos); indexado `articulo` 214,7 s (167 vectores nuevos); `fragmentos` 290,5 s (316 trozos nuevos) |
| Consultas durante el trabajo | **23 de 23 respondieron 200**: 11,6-15,2 s durante la extracción (la CPU está ocupada con pypdf), 1,3-12,2 s durante el indexado |
| `/health` después | Ley 1801 (249 artículos) + Ley 769 (167); 787 fragmentos |
| Después: la misma pregunta de la licencia | Responde con la multa del literal B.1 y cita **Ley 769 de 2002, Artículo 131** |
| Guion: licor en el parque / domicilio sin orden / «¿Qué dice el artículo 163?» | Art. 140, num. 7 / Art. 163, num. 1-7 / Art. 163 de la Ley 1801 **y** Art. 163 de la Ley 769 (la pregunta no dice de qué norma: el motor muestra las dos) |
| Reinicio del motor | Arranca con las dos normas desde disco (persistencia) |
| Quitar la Ley 769 (`reprocesar.py --quitar`) | 0,4 s; índices **idénticos** al respaldo previo (249 y 471 vectores, mismos ids y en el mismo orden, diferencia máxima 0,0, BM25 igual) |

Al terminar se dejó el corpus como estaba (solo Ley 1801). El JSON de tránsito quedó en [`corpus/procesados/ley_769_de_2002.json`](../corpus/procesados/ley_769_de_2002.json) como ejemplo.

## Comandos

Desde la raíz del repo, con el motor **apagado** (si está encendido, reinícialo después; por la API no hace falta reiniciar):

```bash
# Volver a cargar la Ley 769 desde el JSON de ejemplo (no vuelve a leer el PDF; unos 8 min en CPU)
engine/.venv/Scripts/python engine/indexing/reprocesar.py --json corpus/procesados/ley_769_de_2002.json

# Procesar un PDF directamente (sin la API)
engine/.venv/Scripts/python engine/indexing/reprocesar.py --pdf Ley_769_de_2002.pdf --norma "Ley 769 de 2002" --url https://...

# Quitar una norma de los índices (el JSON de corpus/procesados/ se conserva)
engine/.venv/Scripts/python engine/indexing/reprocesar.py --quitar "Ley 769 de 2002"

# Reconstruir TODO desde cero (las dos estrategias, con las normas adicionales que ya tenga el índice)
engine/.venv/Scripts/python engine/indexing/build_index.py --todas

# ... desde cero y solo con la Ley 1801
engine/.venv/Scripts/python engine/indexing/build_index.py --todas --sin-adicionales

# ... desde cero con una norma adicional concreta
engine/.venv/Scripts/python engine/indexing/build_index.py --todas --adicional corpus/procesados/ley_769_de_2002.json
```

Por la API (motor encendido): subir el PDF con `norma` y lanzar `POST /corpus/reprocesar` con el `id`, como en el diagrama.

## Cumplimiento de RF4

RF4 pide subir documentos **sin regenerar los embeddings**. Se cumple en dos pasos separados:

1. `POST /upload_pdf/` solo guarda el archivo y su texto. Comprobado: `/health` no cambia después de subir.
2. La incorporación es una acción **explícita de un administrador** (`POST /corpus/reprocesar` con token) y es **incremental**: no se regeneran los embeddings del corpus existente, solo se calculan los de los artículos nuevos (comprobado: los 249/471 vectores de la Ley 1801 quedan idénticos).

## Limitaciones

- **Vigencia no verificada:** los artículos de normas nuevas quedan con `vigencia: "no_verificada"`. El PDF de la Función Pública trae las notas de modificación pegadas al texto, pero nadie las ha revisado. El frontend debería mostrarlo.
- **Extracción básica:** a la Ley 769 le faltan los art. 3, 18 y 128, el art. 131 sale en un solo bloque de 28.000 caracteres y el libro no se detecta. Lo mejora Wilder en `procesar_pdf.py`.
- **Lentitud de pypdf:** con este PDF, subir tarda unos 60 s y extraer unos 77 s; durante la extracción las consultas se vuelven lentas (11-15 s) porque comparten la CPU. PyMuPDF (ya declarado en `engine/requirements.txt`) es mucho más rápido, pero no está instalado en el entorno de prueba. El backend de Santiago tiene timeout de 30 s: la ruta de subida necesita más.
- **Trabajos en memoria:** si el motor se reinicia, se pierde el estado de los trabajos (`404`); los índices ya cambiados sí persisten.
- **Un trabajo a la vez** (409 si hay otro), y un solo proceso del motor (`uvicorn` sin `--workers`): con varios procesos, solo el que corrió el trabajo vería la versión nueva hasta reiniciar.
- **Docker:** la imagen del motor instala spaCy, mientras que los índices del repo se construyeron con Snowball. El reprocesamiento usa el método guardado en el índice, así que es consistente; pero si se reconstruye desde cero dentro de Docker, los tokens BM25 cambian de método.
- **OneDrive/Windows:** a veces bloquean el borrado de carpetas. El cambio de carpetas renombra lo viejo a `*.borrar-*` y lo limpia después; esas carpetas están ignoradas por git.
- El registro `corpus/uploads/pendientes.json` (local, ignorado por git) puede quedar con un documento en estado `procesado` aunque su norma se haya quitado con `--quitar`.
