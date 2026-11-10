# Segmentación del corpus

Este documento tiene dos partes:

1. **Segmentación jerárquica del texto** (documento y artículo): pipeline inicial en `corpus/extraer.py`, `corpus/limpiar.py` y `corpus/segmentar.py`. La segmentación de numerales y parágrafos y la consolidación jurídica siguen pendientes.
2. **Segmentación para indexación** (cómo se parten los artículos antes de vectorizarlos): Fase 3, responsable Duvan. *Primera comparación hecha sobre el corpus de muestra.*

---

## 1. Segmentación jerárquica del corpus

El pipeline de `corpus/construir_corpus.py` extrae el texto página por página y
separa los artículos de la Ley 1801. En las otras normas selecciona artículos
con numeración consecutiva y añade al corpus únicamente los que contienen una
referencia detectable a la Ley 1801. Cada disposición mantiene la norma y el
artículo de origen, el archivo PDF y la lista de páginas físicas donde aparece
el texto; las reformas no se fusionan con el texto de 2016 ni se marcan como
vigentes sin verificación. Los documentos sin referencia detectada
se listan en `corpus/procesados/corpus_ley_1801_revision.json`.

La detección de encabezados y de referencias es heurística. Esta etapa todavía
no descompone numerales o parágrafos, ni establece la vigencia por aparte, ni
produce una versión consolidada oficial. Revisar las fuentes y los casos del
archivo de revisión antes de indexar o presentar respuestas jurídicas.

---

## 2. Segmentación para indexación (Fase 3)

> **Aviso:** todos los resultados de esta sección son sobre el **corpus de muestra de 10 artículos** (`corpus/muestra/codigo_muestra.json`) y 10 preguntas. Son una primera señal, no una conclusión. **Se repetirán con el corpus completo** y el banco de 50+ preguntas.

### Modelo de embeddings: `intfloat/multilingual-e5-base`

| Criterio | Por qué este modelo |
|---|---|
| Español | Es multilingüe y rinde bien en español; el texto de la ley y las preguntas están en español. |
| Gratis | Modelo abierto (Hugging Face) vía `sentence-transformers`; no requiere clave ni pago por uso. |
| Local | Corre en el equipo: ni el texto ni las preguntas de los usuarios salen a un servicio externo (relevante para la Ley 1581 de 2012). Peso: unos 1.1 GB. |
| 512 tokens | Admite hasta 512 tokens por texto, más que otros modelos multilingües ligeros (p. ej. `paraphrase-multilingual-MiniLM`, que se queda en 128). |

Detalles de uso: vectores de 768 dimensiones, normalizados (el producto punto equivale a la similitud coseno); prefijo `passage: ` para los fragmentos y `query: ` para las preguntas, como pide el modelo.

**Alternativa descartada por ahora:** los embeddings de la API de OpenAI (de pago, requieren clave y enviar el texto fuera del equipo). Podría reconsiderarse si E5 no alcanza en la evaluación completa.

### Tokens por artículo (artículo completo, con prefijo `passage: `)

Límite del modelo: 512 tokens; lo que pasa de ahí **se corta** y no entra en el vector.

| Artículo | Tokens | ¿Se corta? | Trozos de 250 (estrategia `fragmentos`) |
|---|---|---|---|
| 124 | 717 | **Sí** | 4 |
| 139 | 550 | **Sí** | 3 |
| 140 | 1416 | **Sí** | 7 |
| 163 | 453 | no | 2 |
| 173 | 271 | no | 2 |
| 180 | 885 | **Sí** | 5 |
| 183 | 335 | no | 2 |
| 198 | 388 | no | 2 |
| 218 | 59 | no | 1 |
| 222 | 459 | no | 2 |

Cuatro de diez artículos se cortan. El 140 pierde unos dos tercios: justo los numerales 13 y 14 (sustancias psicoactivas en parques y zonas) y la tabla de medidas correctivas.

### Las dos estrategias

| | `articulo` | `fragmentos` |
|---|---|---|
| Qué se vectoriza | Epígrafe + texto del artículo completo | Trozos de **250 tokens con 50 de solapamiento**, medidos con el tokenizer del modelo |
| Contexto | Todo el artículo, pero solo los primeros 512 tokens | Cada trozo lleva el epígrafe antepuesto; hereda ubicación, vigencia y tema del artículo |
| Ids | `art-140` | `art-140-f1`, `art-140-f2`, … |
| Vectores (muestra) | 10 | 30 |
| Resultado de la búsqueda | Artículos | Trozos agrupados por artículo: se conserva el de mayor score y se devuelven k artículos distintos |

Los trozos se cortan sobre el texto original (posiciones del tokenizer), así que son texto literal del artículo. Un trozo puede empezar a mitad de una frase.

### Cómo se evaluó

- Preguntas: `eval/preguntas_segmentacion.json` — 10 preguntas en lenguaje ciudadano, escritas **antes** de ejecutar la evaluación y sin ajustarlas después. Cada una tiene un artículo esperado.
  - 4 apuntan a contenido que queda **después del token 512** (artículos 140, 124, 180 y 139).
  - 6 apuntan a contenido que sí entra en 512 tokens.
- Script: `eval/comparar_segmentacion.py` (a nivel de artículo, con k = 10).
- Métricas: **Acierto@1** (el artículo esperado es el primero), **Acierto@3** (está entre los 3 primeros) y **MRR** (promedio de 1/posición).

### Resultados

Posición del artículo esperado (1 = primero):

| # | Esperado | ¿Después de 512? | `articulo` | `fragmentos` |
|---|---|---|---|---|
| p01 | 140 | sí | 1 | 1 |
| p02 | 124 | sí | 1 | 1 |
| p03 | 180 | sí | **4** | **1** |
| p04 | 139 | sí | 1 | 1 |
| p05 | 163 | no | 1 | 1 |
| p06 | 173 | no | 3 | 4 |
| p07 | 183 | no | 1 | 1 |
| p08 | 198 | no | 1 | 1 |
| p09 | 218 | no | 3 | 4 |
| p10 | 222 | no | 1 | 1 |

Resumen:

| Estrategia | Vectores | Acierto@1 | Acierto@3 | MRR | ms por búsqueda |
|---|---|---|---|---|---|
| `articulo` | 10 | 0.70 | **0.90** | 0.792 | 211 |
| `fragmentos` | 30 | **0.80** | 0.80 | **0.850** | 273 |

Por tipo de pregunta:

| Preguntas | Estrategia | Acierto@1 | Acierto@3 | MRR |
|---|---|---|---|---|
| 4 con respuesta después del token 512 | `articulo` | 0.75 | 0.75 | 0.812 |
| | `fragmentos` | **1.00** | **1.00** | **1.000** |
| 6 con respuesta dentro de 512 tokens | `articulo` | 0.67 | **1.00** | 0.778 |
| | `fragmentos` | 0.67 | 0.67 | 0.750 |

El tiempo por búsqueda es sobre todo el costo de codificar la pregunta con el modelo (la búsqueda en FAISS con 10 o 30 vectores es instantánea); la diferencia entre estrategias está dentro del ruido de medición. La carga inicial del modelo ronda los 8 s y se hace una sola vez.

### Lectura de los resultados

- **Dónde ayuda `fragmentos`:** en p03 (el descuento por pronto pago del artículo 180, que queda fuera de los 512 tokens), el artículo completo ni siquiera aparecía entre los 3 primeros (posición 4); con trozos pasó al primer lugar. Es el caso que la teoría predecía.
- **Dónde no hace falta:** p01, p02 y p04 también apuntaban a texto cortado, pero `articulo` los acertó igual. En una muestra de 10 artículos, cada tema aparece en un solo artículo, así que el vector del artículo cortado alcanza para encontrarlo. Con el corpus completo (más artículos sobre temas parecidos) esto probablemente cambie.
- **Dónde pierde `fragmentos`:** en p06 y p09 (artículos cortos y genéricos: lista de medidas correctivas y definición del comparendo) cayó del puesto 3 al 4. Un trozo suelto de un artículo largo con vocabulario parecido les ganó. Por eso su Acierto@3 es menor.
- **Cuidado con las cifras:** con 10 preguntas, una sola pregunta mueve 10 puntos. La diferencia entre estrategias es de 1 o 2 preguntas. No es estadísticamente concluyente.
- **Costo de `fragmentos`:** 3 veces más vectores (30 contra 10) y la respuesta llega como un trozo, no como el artículo entero. Para generar la respuesta convendrá darle al LLM el artículo completo (o sus trozos vecinos) a partir del trozo encontrado; eso aún no está implementado.

### Conclusión provisional: usar `fragmentos` por defecto

Se elige `fragmentos` (250 tokens, 50 de solapamiento) como estrategia por defecto, **de forma provisional**:

1. Es la única que no pierde contenido: en el artículo 140 el artículo completo deja fuera dos tercios del texto, incluidos numerales y la tabla de medidas, que son justo lo que un ciudadano pregunta (multas y consecuencias).
2. Ganó en las preguntas que dependen del texto cortado (4 de 4 contra 3 de 4), y en MRR y Acierto@1 en general.
3. Su debilidad (artículos cortos y genéricos) se puede mitigar más adelante con búsqueda híbrida (BM25), con el clasificador temático o dando el artículo completo al LLM.

Esta decisión **se revisará** con el corpus completo y el banco de 50+ preguntas, probando también otros tamaños de trozo (por ejemplo 200 y 350 tokens) y de solapamiento.

### Cómo reproducir

```bash
python engine/indexing/build_index.py --estrategia articulo
python engine/indexing/build_index.py --estrategia fragmentos --tamano 250 --solape 50
python eval/comparar_segmentacion.py
```
