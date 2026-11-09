# Búsqueda híbrida: semántica + BM25 (Fase 4, opcional)

El motor tiene tres modos de búsqueda. El modo se elige con `BUSQUEDA_MODO` en el `.env`:

| Modo | Qué hace | Cuándo falla |
|---|---|---|
| `semantico` | Compara el significado de la pregunta con el de cada fragmento (embeddings + FAISS). | Pierde términos exactos: siglas, números, nombres de leyes. |
| `lexico` | BM25: compara las palabras de la pregunta con las del fragmento. Solo devuelve fragmentos que comparten alguna palabra. | No entiende sinónimos ni paráfrasis; con una pregunta sin palabras en común no devuelve nada. |
| `hibrido` | Combina las dos listas con **Reciprocal Rank Fusion (RRF)**. | — (ver «Límites») |

**Recomendado y por defecto: `hibrido`.**

> **Aviso:** todos los resultados son sobre el **corpus de muestra de 10 artículos (30 fragmentos)** y 16 preguntas. Son una primera señal, **no una conclusión**, y se repetirán con el corpus completo y el banco de 50+ preguntas.

## Cómo funciona

### Preparación del texto (BM25)

Función `tokens_bm25()` en [`engine/preprocess/texto_bm25.py`](../engine/preprocess/texto_bm25.py): minúsculas → tokenización → sin stopwords en español → lematización → sin tildes. Los números se conservan (`24`, `1566`, `tipo 4`). Se usa para los fragmentos al construir el índice y para la pregunta al buscar, así que ambos quedan en la misma forma.

Es el **punto de conexión con el preprocesamiento de la Fase 2** (Santiago Castro): cuando su pipeline esté listo, basta con reemplazar el cuerpo de esa función.

Dos métodos, y el índice guarda cuál usó:

- **`spacy`**: lematiza con `es_core_news_sm` (`python -m spacy download es_core_news_sm`).
- **`snowball`**: stemmer Snowball en español, en Python puro. Es el **respaldo**.

> **En el equipo donde se escribió esto, spaCy no carga:** Windows («Control de aplicaciones») bloquea una de sus extensiones nativas (`preshed/maps.pyd`). Por eso **todos los resultados de este documento son con `snowball`**. La rama `spacy` del código **no se ha ejecutado** y debe probarse en un equipo donde spaCy funcione. Snowball es *stemming*, no lematización: recorta la palabra a su raíz (`multas`, `multar` → `mult`), es más burdo y a veces junta palabras distintas.

### Índice

`build_index.py` guarda junto a `index.faiss` un `bm25_tokens.json` con los fragmentos ya preparados y el método usado. Se arma para cada estrategia (`articulo` y `fragmentos`), con los mismos fragmentos y las mismas posiciones. Hay que **reconstruir los índices** para que existan:

```bash
python engine/indexing/build_index.py --estrategia articulo
python engine/indexing/build_index.py --estrategia fragmentos
```

### Reciprocal Rank Fusion

Cada fragmento suma `1 / (k + posición)` por cada lista en la que aparece (la semántica y la léxica); gana el de mayor suma. `k = 60` por defecto (`BUSQUEDA_RRF_K` en el `.env`). Solo cuenta la **posición**, no el valor del score, así que no hay que normalizar nada entre los dos métodos. Un fragmento que sale bien en las dos listas queda arriba; uno que sale muy bien en una sola también puede quedar arriba.

### Clasificador y artículo por número: igual en los tres modos

- **Artículo por número** («¿Qué dice el artículo 163?»): va primero en cualquier modo. Si el modo no trajo ese artículo (p. ej. léxico sin coincidencias), entra su primer fragmento con score 0.
- **Empuje por tema**: el score tiene otra escala en cada modo, así que sumar el mismo `0.03` a los tres no empujaría lo mismo. El empuje de cada modo se calculó para que sea el **mismo «empujón relativo»** que el del modo semántico (`eval/calibrar_empuje.py`): `empuje = 0.03 × dispersión del modo ÷ dispersión semántica`, donde la dispersión es la diferencia de score entre la posición 1 y la 10. El cálculo usa solo los scores de las preguntas, nunca el artículo esperado ni si acertó, y se hizo **antes** de evaluar.

| Modo | Escala del score | Dispersión mediana | Empuje máximo |
|---|---|---|---|
| `semantico` | coseno (0 a 1) | 0.0463 | **0.03** |
| `lexico` | BM25 ÷ mejor BM25 (0 a 1) | 0.7808 | **0.5** |
| `hibrido` | RRF (~0.01 a 0.03) | 0.0046 | **0.003** |

Los valores están en `engine/retrieval/temas.json` (`configuracion.empuje_por_modo`). **El `score` que devuelve la API cambia de escala con el modo**: no se pueden comparar scores de modos distintos.

## Evaluación

`eval/comparar_modos.py`. **16 preguntas**: las 10 de la segmentación, las 3 del clasificador y **3 nuevas con términos exactos**, escritas antes de implementar BM25 y sin ajustarlas después (el artículo esperado de cada una se comprobó en el texto):

| # | Tipo | Pregunta | Esperado |
|---|---|---|---|
| p14 | Sigla o término técnico | ¿Cuántos smdlv cuesta una multa tipo 4? | 180 |
| p15 | Plazo | ¿Qué debe ocurrir en 24 horas con una apelación contra la orden de policía? | 222 |
| p16 | Término legal específico | ¿Qué tiene que ver la Ley 1566 de 2012 con las medidas correctivas? | 140 |

Todos los modos con clasificador, estrategia `fragmentos`, k = 10.

### Resultados

| Preguntas | Modo | Acierto@1 | Acierto@3 | MRR |
|---|---|---|---|---|
| **16 (todas)** | semantico | 0.75 | 0.94 | 0.859 |
| | lexico | **0.88** | 0.94 | 0.906 |
| | **hibrido** | **0.88** | **1.00** | **0.927** |
| 13 de la evaluación anterior | semantico | 0.77 | 0.92 | 0.865 |
| | lexico | 0.85 | 0.92 | 0.885 |
| | hibrido | 0.85 | 1.00 | 0.910 |
| 3 con términos exactos (p14–p16) | semantico | 0.67 | 1.00 | 0.833 |
| | lexico | 1.00 | 1.00 | 1.000 |
| | hibrido | 1.00 | 1.00 | 1.000 |
| *Informativo: 16 sin clasificador* | semantico | 0.69 | 0.88 | 0.812 |
| | lexico | 0.75 | 0.88 | 0.810 |
| | hibrido | 0.81 | 0.88 | 0.865 |

Posición del artículo esperado (1 = primero), con clasificador:

| # | Esperado | semantico | lexico | hibrido |
|---|---|---|---|---|
| p01–p05, p07, p08, p10, p11, p12, p14, p15 | — | 1 | 1 | 1 |
| p06 | 173 | **2** | 6 | 3 |
| p09 | 218 | 4 | **1** | 2 |
| p13 | 222 | 2 | 3 | **1** |
| p16 | 140 | 2 | **1** | **1** |

### En qué preguntas cambió el resultado y por qué

12 de las 16 dieron lo mismo en los tres modos. Cambiaron cuatro:

- **p16 (Ley 1566 de 2012): semántico 2 → léxico y híbrido 1.** La pregunta pide una ley concreta. El semántico se fue al artículo 173 («Medidas correctivas»), ayudado por el clasificador, que detectó ese tema por «medidas correctivas» y lo empujó; BM25 encontró `1566` y `2012`, que solo están en el artículo 140. Es exactamente el caso para el que sirve el léxico.
- **p09 (el documento que me entrega el policía): semántico 4 → léxico 1, híbrido 2.** La pregunta no dice «comparendo», pero comparte palabras sueltas con el artículo 218 (`documento`, `entregar`). El semántico no la ve; el léxico sí. En el híbrido el 222 quedó apenas por delante del 218 (0.0320 contra 0.0318).
- **p13 (no hago caso a un agente): híbrido 1, semántico 2, léxico 3.** Ningún método solo la acierta; la suma sí: el 222 salió segundo en la lista semántica y tercero en la léxica, y la fusión lo subió al primer puesto. El único término en común con el artículo era `caso`, una coincidencia casi de azar.
- **p06 (otras sanciones además de la multa): semántico 2 → híbrido 3 → léxico 6.** Es la pregunta donde el léxico estorba. Pide el artículo 173 (lista de medidas) pero solo comparte `multa` y `policía` con él, palabras muy comunes en el corpus; BM25 puso arriba los artículos 198 y 222 (probablemente porque nombran más veces a la Policía; no lo verifiqué). El híbrido amortiguó el daño (3), pero el semántico solo (2) fue mejor.

### Tiempo de búsqueda

Medido con las 16 preguntas, 5 pasadas con el orden de los modos rotado (80 búsquedas por modo, k = 3, con clasificador):

| Modo | Mediana | p90 |
|---|---|---|
| semantico | 140.6 ms | 155.7 ms |
| lexico | **1.6 ms** | 2.2 ms |
| hibrido | 142.4 ms | 159.9 ms |

Casi todo el tiempo es codificar la pregunta con el modelo de embeddings; BM25 cuesta apenas unos milisegundos, así que el híbrido cuesta lo mismo que el semántico. (La primera corrida de `comparar_modos.py` dio 362 ms para el semántico y 216 ms para el híbrido, una diferencia sin sentido causada por correr los modos uno tras otro con la carga del equipo cambiando; por eso se repitió con el orden rotado.) Todos están muy por debajo del límite de 10 s de la respuesta completa (RNF1).

### Preguntas fuera de dominio, con el LLM real y modo híbrido

Con `BUSQUEDA_MODO=hibrido`:

| Pregunta | Fragmentos recuperados | `fuera_de_dominio` | Tiempo |
|---|---|---|---|
| ¿Cuánto cuesta renovar el pase de conducción? | 183, 139, 180 | **True** («No encontré esa información en el Código…») | 3.54 s |
| ¿Cuál es la tarifa del impuesto predial en Bogotá? | 180, 140, 139 | **True** | 1.30 s |
| *(control en dominio)* ¿Hay descuento si pago la multa rápido? | 180, 183, 140 | False, cita `Art. 180` | 1.22 s |

El modo híbrido siempre devuelve fragmentos (la parte semántica trae los más parecidos aunque no tengan nada que ver), así que lo que evita que se invente una respuesta es el prompt, no la búsqueda; en estas pruebas funcionó.

## Recomendación: `hibrido` por defecto

1. **Mejor resultado global** en esta muestra: único con Acierto@3 = 1.00 y el MRR más alto (0.927), y empata con el léxico en Acierto@1 (0.88). También es el mejor sin clasificador (MRR 0.865).
2. **No depende de acertar con el tipo de pregunta.** El semántico falla con términos exactos (p16); el léxico falla con paráfrasis (p06) y no devuelve nada si no hay palabras en común. El híbrido acertó las dos clases o se quedó cerca (p06: puesto 3).
3. **Cuesta lo mismo que el semántico** (unos 142 ms; BM25 son 1.6 ms).
4. **Mantiene un respaldo:** si la pregunta no comparte palabras con el corpus, el híbrido sigue funcionando con la parte semántica; el léxico puro devolvería una lista vacía.

Es **configurable** sin tocar código: `BUSQUEDA_MODO=semantico|lexico|hibrido` en el `.env` (el `/health` muestra el modo activo). Si el valor no existe, o falta el índice BM25, el motor arranca con `listo: false` y un mensaje claro en `error`.

## Límites de esta evaluación

1. **Muestra mínima.** 16 preguntas y 10 artículos: una pregunta mueve 6 puntos de Acierto@1, y el híbrido acierta en primer lugar solo 2 preguntas más que el semántico (p13 y p16). **No es estadísticamente concluyente.** Con 10 artículos de temas muy distintos, casi cualquier método acierta.
2. **Las tres preguntas nuevas favorecen al léxico por construcción**: se pidieron con términos exactos. Que el léxico y el híbrido las acierten no dice mucho sobre preguntas ciudadanas reales, que casi nunca traen «Ley 1566» o «smdlv».
3. **Stemming, no lematización**, por el bloqueo de spaCy. La rama de spaCy no se ejecutó. Los resultados con spaCy podrían ser distintos (probablemente mejores para el léxico).
4. **El empuje del clasificador en modo léxico es muy grande (0.5)** porque se calibró por equivalencia relativa; con un tema detectado casi decide el orden entre los candidatos que comparten palabras. Con el corpus completo hay que revisarlo.
5. **El `score` no es comparable entre modos** (coseno, BM25 normalizado, RRF).
6. **RRF con `k = 60` no se ajustó.** Es el valor habitual; con 30 fragmentos conviene probar otros.

## Cómo reproducir

```bash
python engine/indexing/build_index.py --estrategia articulo
python engine/indexing/build_index.py --estrategia fragmentos
python eval/calibrar_empuje.py          # empuje equivalente por modo
python eval/comparar_modos.py           # resultados de este documento
python engine/retrieval/search.py --modo lexico "¿Cuántos smdlv cuesta una multa tipo 4?"
```
