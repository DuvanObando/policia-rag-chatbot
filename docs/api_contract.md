# Contrato de la API — `POST /query`

Referencia compartida del equipo (frontend ↔ backend ↔ motor).

## Entrada

```json
{
  "pregunta": "string",
  "historial": [{ "rol": "usuario | asistente", "contenido": "string" }]
}
```

- `pregunta` (string, obligatorio)
- `historial` (arreglo, opcional)

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
  "fuera_de_dominio": false
}
```

- `fuera_de_dominio`: `true` si la pregunta no corresponde a la Ley 1801 de 2016.

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

## `POST /upload_pdf/`

Recibe un PDF (multipart, campo `file`). No regenera embeddings ni índices.
