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
      "score": 0.0
    }
  ],
  "fuera_de_dominio": false
}
```

- `fuera_de_dominio`: `true` si la pregunta no corresponde a la Ley 1801 de 2016.

## `POST /upload_pdf/`

Recibe un PDF (multipart, campo `file`). No regenera embeddings ni índices.
