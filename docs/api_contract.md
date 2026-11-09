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
      "vigencia": "vigente",
      "tema": "string"
    }
  ],
  "fuera_de_dominio": false,
  "citas": [
    { "articulo": "Artículo 163", "numeral": "2", "paragrafo": null, "texto": "Art. 163, num. 2" }
  ]
}
```

- `fuera_de_dominio`: `true` si la pregunta no corresponde a la Ley 1801 de 2016.
- `citas` (**opcional**): detalle de cada cita de la respuesta. `articulos_citados` sigue igual (solo artículos), así que quien no use `citas` no se ve afectado.
  - `articulo`: como en `articulos_citados` (`"Artículo 163"`).
  - `numeral`: número del numeral citado, o `null`.
  - `paragrafo`: número del parágrafo (`"1"`), `"único"` (parágrafo sin número), `"transitorio"`, o `null`.
  - `texto`: forma legible para mostrar (`"Art. 163, num. 2"`, `"Art. 183, par."`, `"Art. 180"`).
  - Solo incluye citas de artículos que estaban en el contexto y cuyo numeral o parágrafo existe en el texto del artículo. Si `fuera_de_dominio` es `true`, va vacío.

### Campos de cada elemento de `fragmentos`

| Campo | Tipo | Obligatorio | Descripción |
|---|---|---|---|
| `id` | string | sí | Identificador del fragmento en el corpus |
| `ubicacion` | string | sí | Ubicación jerárquica (libro, título, capítulo, artículo) |
| `epigrafe` | string | sí | Epígrafe del artículo |
| `texto` | string | sí | Texto del fragmento |
| `score` | number | sí | Puntaje de relevancia de la recuperación |
| `vigencia` | string | no | Estado de vigencia: `vigente`, `modificado`, `inexequible` o `exequible_condicionado` |
| `tema` | string | no | Tema asignado al fragmento en el corpus |

### Origen y uso de `vigencia` y `tema`

- Ambos campos son **opcionales**: si el corpus no los tiene para un fragmento, se omiten y el frontend no debe fallar.
- Sus valores **salen de los metadatos del corpus** (Fase 1); el motor los copia tal cual, sin calcularlos.
- **El frontend debe mostrar la `vigencia` en el panel de fuentes** junto a cada fragmento, con una señal visible cuando no sea `vigente` (`modificado`, `inexequible` o `exequible_condicionado`).
- El frontend puede mostrar el `tema` como etiqueta del fragmento.

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
  "fragmentos_en_indice": 30,
  "llm_proveedor": "gemini",
  "llm_principal": "gemini-3.5-flash-lite",
  "llm_respaldo": "gemini-3.6-flash",
  "tiempos_de_carga_s": { "embeddings_e_indice_s": 8.1, "cliente_llm_s": 0.4, "total_s": 8.5 }
}
```

El modelo de embeddings, el índice y el cliente del LLM se cargan **al arrancar el servidor**, no en la primera pregunta. Si falta la clave del LLM, `listo` es `false`, `error` explica por qué y `POST /query` responde 503.

## Privacidad (Ley 1581 de 2012)

El motor **no registra el texto de las preguntas, de las respuestas ni del historial** en logs, y no guarda nada en disco ni en base de datos. Los logs solo contienen estado, tiempos, modelo usado y conteos. El historial de conversación debe vivir en el navegador del usuario (sesión), no en el servidor. Quien agregue logs al backend o al motor debe respetar esta regla.

## `POST /upload_pdf/`

Recibe un PDF (multipart, campo `file`). No regenera embeddings ni índices.
