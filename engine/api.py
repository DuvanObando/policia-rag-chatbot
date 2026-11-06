"""API mínima del motor RAG (respuestas simuladas).

Contrato: ver docs/api_contract.md
"""
from typing import List, Optional

from fastapi import FastAPI, File, UploadFile
from pydantic import BaseModel

app = FastAPI(title="Motor RAG - Ley 1801 de 2016")


class Query(BaseModel):
    pregunta: str
    historial: Optional[List[dict]] = None


@app.post("/query")
def query(q: Query):
    # TODO(C): reemplazar por recuperación + generación reales
    return {
        "respuesta": "Respuesta simulada.",
        "articulos_citados": ["Artículo 1"],
        "fragmentos": [
            {
                "id": "art-1",
                "ubicacion": "Título I, Capítulo único",
                "epigrafe": "Objeto",
                "texto": "Texto simulado del fragmento.",
                "score": 0.0,
            }
        ],
        "fuera_de_dominio": False,
    }


@app.post("/upload_pdf/")
async def upload_pdf(file: UploadFile = File(...)):
    # Solo recibe el archivo. NO regenera embeddings ni índices.
    contenido = await file.read()
    return {
        "mensaje": "PDF recibido (simulado). No se regeneraron embeddings.",
        "archivo": file.filename,
        "bytes": len(contenido),
    }
