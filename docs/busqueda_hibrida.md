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

---

# Expansión de consultas con glosario

## Para qué sirve

El usuario dice «guaro», «boleta», «tombos»; la ley dice «bebidas alcohólicas», «orden de comparendo», «autoridades de policía». BM25 solo compara palabras, así que no los une. La expansión detecta los términos coloquiales de un glosario y **le agrega a la consulta de BM25** las palabras del término legal.

## Cómo funciona

[`engine/retrieval/expansion.py`](../engine/retrieval/expansion.py), `expandir(pregunta)`:

1. **Detecta** los coloquiales del glosario comparando **palabras completas normalizadas** (minúsculas y sin tildes, con la función `sin_tildes` de `texto_bm25.py`). Un coloquial de varias palabras (`multa de la policía`) debe aparecer completo y en ese orden. **No se comparan raíces del stemmer.**
2. **Agrega** a la consulta las palabras del término legal, **preparadas con `tokens_bm25`** (igual que el texto del índice, para que coincidan con él), y solo las que la pregunta todavía no tiene (no se duplican).

Ejemplo: «¿Me ponen boleta si me cogen tomando guaro en el parque?» agrega `beb alcohol` (bebidas alcohólicas), `orden comparend` (orden de comparendo) y `espaci public` (espacio público).

Reglas:

- **Solo BM25.** Se aplica a la consulta léxica de los modos `lexico` e `hibrido`, **nunca a la consulta semántica**: el modelo de embeddings ya entiende «guaro», y agregarle palabras solo desviaría su significado.
- **Activable:** `BUSQUEDA_EXPANSION` en el `.env` (`1` activa por defecto; `0`, `false`, `no` u `off` la desactivan). `/health` → `busqueda_expansion` muestra si está activa y cuántas entradas tiene el glosario.
- **Consecuencia de comparar palabras completas:** las variantes (plural, género) hay que listarlas en el glosario (`perro` y `perros`). Es el precio de no confundir palabras.

### Corrección: por qué no se comparan raíces

La primera versión detectaba los coloquiales con la misma preparación de texto de BM25 (stemming), para que «drogas» encontrara «droga» sin listar plurales. El stemmer Snowball reduce **«caso» y «casa» a la misma raíz, `cas`**: la pregunta «¿Qué pasa si no hago *caso* cuando un agente me da una indicación?» activó el coloquial `casa` (→ «domicilio») y la pregunta p13 **empeoró** (puesto 1 → 2). También `castigue` se tomaba por `castigo`, y `agente` agregaba «autoridades de policía». Por eso:

- La detección pasó a **palabras completas** (arriba).
- Se quitó **`agente`** (y su plural `agentes`) del glosario semilla: es un término demasiado genérico. El archivo ahora dice que se eviten términos así (`agente`, `policía`, y `casa` suelta si genera ruido).

## El glosario (`engine/glossary/sinonimos.json`)

```json
{
  "_provisional": "...",
  "_evitar": "...",
  "bebidas alcohólicas": ["trago", "tragos", "licor", "guaro", "alcohol", "cerveza"],
  "orden de comparendo": ["comparendo", "boleta", "papeleta", "multa de la policía"]
}
```

- Formato: `{"termino_legal": ["coloquial1", "coloquial2", ...]}`. El término legal va **como aparece en el Código** (así lo encuentra BM25). Las claves que empiezan con `_` se ignoran.
- Hoy tiene **18 entradas semilla** sacadas del corpus de muestra.
- **Es PROVISIONAL**: lo escribió el motor RAG solo para probar el mecanismo. **Santiago Castro lo reemplaza con el glosario de la Fase 2** (mismo formato); el archivo lo dice en su primera clave.
- Evitar términos genéricos (clave `_evitar`): `agente` y `policía` aparecen en casi cualquier pregunta; un coloquial debe señalar una sola cosa del Código.

## Verificación de consistencia del índice

El índice BM25 guarda con qué método se prepararon sus textos (`snowball:spanish` o `spacy:es_core_news_sm-<versión>`). Si el método disponible cambia (por ejemplo, se instala spaCy después de construir el índice), las palabras de las preguntas dejarían de coincidir con las del índice y BM25 fallaría **en silencio**. Por eso, **al arrancar** y en los modos que usan BM25, el motor compara los dos métodos; si no coinciden, arranca con `listo: false` y un error como:

> El índice BM25 de 'fragmentos' se construyó con la preparación de texto 'spacy:es_core_news_sm-3.8.0', pero ahora está disponible 'snowball:spanish'. Hay que reconstruir el índice: python engine/indexing/build_index.py --estrategia fragmentos

Se probó modificando una copia del archivo del índice para simular el desajuste (después se restauró): el servidor arrancó con `listo: false` y `/query` respondió 503.

## Evaluación: híbrido con y sin expansión

`eval/comparar_expansion.py`. **19 preguntas** (no se modificaron al corregir): las 16 de la evaluación anterior más **3 muy coloquiales**, escritas antes de evaluar:

| # | Pregunta | Esperado |
|---|---|---|
| p17 | ¿Me ponen boleta si me cogen tomando guaro en el parque? | 140 |
| p18 | Mi perro es un pitbull y se me escapó a la calle, ¿me cobran mucho? | 124 |
| p19 | Los tombos se metieron a mi apartamento sin papel, ¿eso se puede? | 163 |

Modo híbrido, con clasificador. Se muestran la primera versión (por raíces, con `agente`) y la **versión corregida** (palabras completas, sin `agente`):

| Preguntas | Expansión | Acierto@1 | Acierto@3 | MRR |
|---|---|---|---|---|
| **19 (todas)** | sin | 0.84 | 1.00 | 0.912 |
| | con, primera versión | 0.84 | 1.00 | 0.921 |
| | **con, corregida** | **0.89** | 1.00 | **0.947** |
| 16 de la evaluación anterior | sin | 0.88 | 1.00 | 0.927 |
| | con, primera versión | 0.81 | 1.00 | 0.906 |
| | **con, corregida** | 0.88 | 1.00 | **0.938** |
| 3 muy coloquiales (p17–p19) | sin | 0.67 | 1.00 | 0.833 |
| | con, primera versión | 1.00 | 1.00 | 1.000 |
| | **con, corregida** | **1.00** | 1.00 | **1.000** |
| *Informativo: modo léxico, 19* | sin | 0.79 | 0.89 | 0.855 |
| | con, primera versión | 0.89 | 0.89 | 0.912 |
| | **con, corregida** | **0.89** | **0.95** | **0.921** |

### Posición del artículo esperado (híbrido): solo las que cambian

| # | Esperado | Sin expansión | Primera versión | **Corregida** |
|---|---|---|---|---|
| p06 | 173 | 3 | 2 | **2** |
| p13 | 222 | 1 | 2 (empeoró) | **1** (recuperada) |
| p17 | 140 | 2 | 1 | **1** |

Las otras 16 preguntas dan igual en las tres columnas. **Ninguna pregunta empeora frente a «sin expansión» con la versión corregida.**

- **p17 (boleta + guaro + parque): 2 → 1.** La expansión agrega `bebidas alcohólicas`, `orden de comparendo` y `espacio público`; el artículo 140 pasa adelante del 124.
- **p06 (otras sanciones además de la multa): 3 → 2.** `sanciones` → `medidas correctivas` agrega `med correct` y sube el 173.
- **p13: de vuelta al puesto 1.** Ya no se activa `casa` por `caso`, ni `agente`; la expansión no agrega nada a esa pregunta.

Qué coincidencias dejaron de ocurrir con la corrección (ninguna cambiaba una posición): `castigue` → `castigo` (p02, que era una coincidencia por raíz), `sin permiso de un juez` ≠ `sin permiso del juez` (p05: la frase del glosario no coincide palabra por palabra), `agente` (p08, p13) y `casa` (p13). En p05 sigue activándose `apartamento` → `domicilio`.

### Preguntas fuera de dominio (LLM real, híbrido)

Se comprobaron con el LLM real con la primera versión: «pase de conducción» e «impuesto predial» siguieron en `fuera_de_dominio: True`, sin ninguna palabra agregada. Con la versión corregida la expansión tampoco agrega ninguna palabra a esas dos preguntas (se comprobó la expansión; lo recuperado es idéntico), así que no se repitió la llamada al LLM.

## Conclusión sobre la expansión

- **Con la corrección, la expansión es una mejora pequeña pero sin regresiones en esta muestra:** Acierto@1 de 0.84 a 0.89 y MRR de 0.912 a 0.947 en 19 preguntas; ninguna pregunta empeora. Ayuda sobre todo con jerga (p17; en modo léxico puro, las tres coloquiales pasan de 0.33 a 1.00).
- Sigue **activa por defecto**; se desactiva con `BUSQUEDA_EXPANSION=0`.

### Límites de esta evaluación

1. **Muestra mínima y parcialmente circular.** Las tres preguntas coloquiales usan jerga que está en el glosario semilla (`guaro`, `boleta`, `tombos`, `pitbull`), y el glosario salió de los mismos 10 artículos: es una prueba de que **el mecanismo funciona**, no de que cubra la jerga real. («sin papel», en p19, quedó fuera a propósito y no se detecta.) En híbrido, solo p17 cambia el Acierto@1: **+1 pregunta de 19** (5 puntos), no concluyente.
2. **La corrección se hizo mirando una pregunta de la evaluación (p13)**, así que esa pregunta ya no es una prueba independiente. La corrección en sí es de diseño (palabras completas) y no depende de p13, pero los números de la versión corregida están algo favorecidos.
3. **Con palabras completas se pierden variantes no listadas** (`calles`, `uniformados`, `patrulleros`): el glosario de la Fase 2 debe incluirlas.
4. **El glosario es provisional**: las conclusiones cambian cuando Santiago Castro entregue el definitivo.
5. **Las palabras agregadas pesan igual que las de la pregunta** (no hay peso menor para lo expandido).
6. Todo se midió con **stemming (Snowball), no lematización**, porque spaCy está bloqueado en este equipo.

### Cómo reproducir

```bash
python eval/comparar_expansion.py
```
