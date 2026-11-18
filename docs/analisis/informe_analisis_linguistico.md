# Informe de análisis lingüístico (Fase 2)

Chatbot RAG sobre la Ley 1801 de 2016 (Código Nacional de Seguridad y Convivencia Ciudadana).
Responsable: Santiago Castro. Corte del 18 de noviembre de 2026.

Este informe describe cómo se analizó el corpus, qué se encontró y cómo ese análisis alimenta al buscador del chatbot. Todas las cifras salen de los archivos de esta misma carpeta y se pueden regenerar con los scripts de `engine/analysis/` (sección 10).

## 1. Datos y alcance

El corpus es `corpus/procesados/corpus_ley_1801.json`, entregado por la Fase 1. Tiene 290 registros: 249 son artículos del texto base de la ley y 41 son disposiciones de normas que la modifican, adicionan o corrigen: Decreto 555 de 2017 (16 registros), Ley 2197 de 2022 (8), Ley 2220 de 2022 (6), Ley 2318 de 2023 (4), Ley 2030 de 2020 (3), Ley 2000 de 2019 (2), Ley 1955 de 2019 (1) y Ley 2054 de 2020 (1).

Cada análisis se corrió dos veces: sobre la **ley base** y sobre **todo el corpus**. Se separan porque las normas modificatorias repiten tablas completas de sanciones. Por ejemplo, los primeros ejemplos de concordancia del corpus completo vienen del Decreto 555 y repiten los mismos artículos de la ley base. Mezclarlos infla las frecuencias sin que haya más lenguaje nuevo.

## 2. Herramientas y método

Se usó spaCy con el modelo `es_core_news_sm` 3.8.0. Se probó el 11 de noviembre y carga sin problemas en el equipo de análisis, así que no hizo falta recurrir a Stanza (el enunciado permite cualquiera de los dos). La lematización funciona bien en frases simples: «Los comandantes multaron a las personas» da `el, comandante, multar, a, el, persona`.

Pasos aplicados a cada registro:

1. Tokenización con spaCy. Se descartan espacios y signos de puntuación; lo que queda se cuenta como palabra.
2. Lematización y normalización (minúsculas y, para las frecuencias, sin tildes).
3. Etiquetado gramatical (POS) y reconocimiento de entidades (NER) con el modelo.
4. Montos y plazos con expresiones regulares, porque el modelo no los etiqueta.
5. Autoridades y lugares con un diccionario de formas (`entidades_reglas.py`), por las razones de la sección 4.
6. Frecuencias de lemas, n-gramas de lemas (sin palabras vacías en los extremos), colocaciones con ventana de 4 palabras a cada lado, frecuencia conjunta mínima de 5 y medida PMI, y concordancias (KWIC) con 8 palabras de contexto y hasta 30 ejemplos por término.

**Diferencia con el buscador.** El análisis usa lematización, pero el índice BM25 del motor usa *stemming* Snowball. La razón es práctica: cuando se construyó el motor, spaCy estaba bloqueado por Windows en el equipo del líder del proyecto, y el índice guarda con qué método se preparó el texto para no mezclar métodos. La diferencia se ve en una misma pregunta, «¿Cuántos smdlv cuesta una multa tipo 4?»: spaCy da `smdlv, costar, multa, tipo, 4` y Snowball da `smdlv, cuest, mult, tip, 4`. El *stemming* es más burdo, pero consistente entre el índice y la consulta, que es lo que importa para BM25.

## 3. Estadísticas del corpus

|  | Solo ley base | Todo el corpus |
|---|---|---|
| Registros | 249 | 290 |
| Tokens (palabras) | 53.443 | 68.654 |
| Tipos (formas) | 4.884 | 4.942 |
| Tipos (lemas) | 3.701 | 3.756 |
| Relación tipo/token (formas) | 0,0914 | 0,072 |
| Relación tipo/token (lemas) | 0,0693 | 0,0547 |
| Longitud media por registro (tokens) | 214,6 | 236,7 |
| Mediana | 130 | 143,5 |
| Mínimo y máximo | 22 y 1.347 | 22 y 1.352 |

Tres lecturas de la tabla:

- **La relación tipo/token es baja** (0,0914 en la ley base) y cae a 0,072 al sumar las reformas. Es lo esperable en un texto normativo, que repite fórmulas y tablas, y el efecto se acentúa porque las modificatorias reproducen artículos ya existentes.
- **La media de longitud (214,6 tokens) es mucho mayor que la mediana (130).** Pocos artículos muy largos, que llegan a 1.347 tokens, elevan el promedio. Esto tiene consecuencias para la segmentación del motor, que parte los artículos largos en fragmentos.
- **Los 53.443 tokens de la ley base se reducen a 3.701 lemas distintos.** Es un vocabulario pequeño y muy especializado.

## 4. POS y entidades

**Categorías gramaticales.** El texto es muy nominal:

| Etiqueta | Categoría | Ley base | % base | Todo | % todo |
|---|---|---|---|---|---|
| NOUN | sustantivo | 13.188 | 24,7 % | 16.904 | 24,6 % |
| ADP | preposición | 10.008 | 18,7 % | 12.779 | 18,6 % |
| DET | determinante | 6.972 | 13,0 % | 8.864 | 12,9 % |
| ADJ | adjetivo | 5.559 | 10,4 % | 7.061 | 10,3 % |
| PROPN | nombre propio | 4.560 | 8,5 % | 5.859 | 8,5 % |
| VERB | verbo | 3.692 | 6,9 % | 4.762 | 6,9 % |
| CCONJ | conjunción | 3.001 | 5,6 % | 3.859 | 5,6 % |
| NUM | numeral | 2.182 | 4,1 % | 2.989 | 4,4 % |
| PRON | pronombre | 1.950 | 3,6 % | 2.544 | 3,7 % |

Hay 3,6 sustantivos por cada verbo en la ley base. Es un estilo de enumeraciones («Numeral 1 ... Numeral 2 ...») más que de oraciones con acción. Los nombres propios (8,5 %) son una proporción alta para un texto legal. Es probable que buena parte sean encabezados en mayúscula y cabeceras de tabla que el modelo toma por nombres, aunque este informe no lo comprobó token por token.

**NER del modelo.** Estas son las entidades que devuelve `es_core_news_sm`:

| Etiqueta | Ley base | Todo | Entidades más frecuentes en la ley base (y cuántas veces) |
|---|---|---|---|
| PER | 587 | 744 | «policía» (230), «destrucción» (38), «suspensión» (35), «participación» (18) |
| LOC | 754 | 1.059 | «numeral» (129), «la ley» (86), «suspensión» (76), «gobierno nacional» (21) |
| ORG | 334 | 449 | «parágrafo» (49), «comportamientos» (22), «destrucción» (17), «corregido por el art» (15) |
| MISC | 1.832 | 2.294 | «multa general» (117), «parágrafo 1» (62), «código» (61), «sentencia de la corte constitucional» (57) |

El resultado confirma que el modelo no sirve tal cual para este dominio. Etiqueta «numeral» y «la ley» como lugares, y «destrucción» y «suspensión» (medidas correctivas) como personas. Fue entrenado con noticias y la prosa jurídica no se parece. Por eso se extraen con reglas las cuatro clases que pide el enunciado.

**Autoridades, lugares, montos y plazos por reglas** (`engine/analysis/entidades_reglas.py`):

| Autoridad o institución | Ocurrencias base | Registros base | Ocurrencias todo |
|---|---|---|---|
| Corte Constitucional | 113 | 73 | 113 |
| autoridad de policía | 82 | 61 | 100 |
| Policía Nacional | 74 | 47 | 92 |
| alcalde | 60 | 41 | 72 |
| personal uniformado de la Policía | 36 | 21 | 49 |
| gobernador | 21 | 16 | 22 |
| concejo municipal o distrital | 16 | 11 | 17 |
| inspector de policía | 10 | 8 | 14 |
| comandante de estación | 9 | 8 | 13 |
| autoridad ambiental | 8 | 6 | 9 |
| Presidente de la República | 7 | 7 | 8 |
| Ministerio Público | 6 | 5 | 9 |
| corregidor | 5 | 4 | 7 |
| Ministerio del Interior | 4 | 2 | 5 |

Las menciones a la «Corte Constitucional» no son parte del texto original de la ley: vienen de las notas de jurisprudencia que el corpus conserva junto a cada artículo.

| Lugar | Ocurrencias base | Registros base | Ocurrencias todo |
|---|---|---|---|
| espacio público | 66 | 36 | 94 |
| transporte público | 25 | 10 | 25 |
| domicilio | 15 | 11 | 17 |
| lugar abierto al público | 13 | 9 | 20 |
| parque | 13 | 7 | 16 |
| área protegida | 11 | 7 | 12 |
| vía pública | 8 | 8 | 9 |
| establecimiento educativo | 4 | 2 | 10 |
| establecimiento de comercio | 4 | 3 | 4 |
| estadio o escenario deportivo | 2 | 2 | 3 |
| zona de recreo | 1 | 1 | 1 |

| Monto | Ley base | Todo el corpus |
|---|---|---|
| tipo 1 | 33 | 43 |
| tipo 2 | 37 | 58 |
| tipo 3 | 40 | 56 |
| tipo 4 | 123 | 165 |
| Multa especial | 45 | 58 |
| Referencias a salarios mínimos, SMDLV o UVT | 18 | 34 |

La ley casi no expresa montos en salarios mínimos. Fija las sanciones por categorías, y la «multa general tipo 4» (la más severa) es la más repetida, con 123 de las 233 menciones de multa general por tipo en la ley base. Las referencias a salarios mínimos suben de 18 a 34 al sumar las reformas, que introducen más lenguaje de montos.

| Unidad del plazo | Ley base | Todo el corpus |
|---|---|---|
| días | 31 | 45 |
| meses | 14 | 17 |
| años | 14 | 19 |
| horas | 10 | 11 |
| minutos | 3 | 3 |

Los plazos aparecen escritos con el número en letras y en paréntesis («tres (3) meses», «cuarenta y ocho (48) horas»). Los días son la unidad más frecuente en ambos alcances.

## 5. Frecuencias y n-gramas

**Lemas más frecuentes de la ley base** (sin palabras vacías): actividad (490), publico (450), policia (389), numeral (361), multa (353), autoridad (302), medida (296), comportamiento (290), general (284), paragrafo (280), tipo (264), 2 (249).

**Bigramas más frecuentes:** «multa general» (237), «general tipo» (228), «medida correctivo» (137), «tipo 4» (123), «suspension temporal» (115), «corte constitucional» (114), «involucrar aglomeracion» (98), «publico complejo» (93), «actividad numeral» (84), «policia nacional» (75).

**Trigramas más frecuentes:** «multa general tipo» (228), «autoridad de policia» (133), «aglomeracion de publico» (128), «general tipo 4» (121), «temporal de actividad» (106), «actividad que involucrar» (95).

Lo que dicen los n-gramas es el esqueleto de la ley: la escala de sanciones («multa general tipo N»), las medidas correctivas, la suspensión de actividades, las aglomeraciones de público y los nombres de las autoridades. «Corte constitucional» aparece como bigrama por las notas de jurisprudencia mencionadas arriba.

## 6. Los cuatro términos del enunciado

| Término | Ocurrencias base | Registros base | Ocurrencias todo | Registros todo |
|---|---|---|---|---|
| multa | 353 | 56 | 510 | 75 |
| comparendo | 22 | 7 | 40 | 11 |
| medida correctiva | 137 | 76 | 177 | 97 |
| espacio publico | 66 | 36 | 94 | 45 |

**Multa.** Es el término dominante. Sus colocaciones en la ley base son: numeral (309; PMI 7,02), tipo (293; PMI 7,39), general (242; PMI 7,01), actividad (72; PMI 4,48), suspension (56; PMI 5,38), especial (51; PMI 5,88), destruccion (36; PMI 6,15). Las tres primeras («numeral», «tipo» y «general») no salen de frases corridas sino de las tablas de sanciones («Numeral 1 Multa General tipo 2»). Los 30 ejemplos de concordancia que guarda el análisis caen todos en las tablas de los artículos 27 a 35, por eso el KWIC de «multa» muestra tablas y no prosa.

**Comparendo.** Es el término menos frecuente: 22 ocurrencias en 7 registros de la ley base, frente a 353 de «multa». Su único compañero frecuente es «orden», porque el Código habla de «orden de comparendo». Al sumar las reformas sube a 40 ocurrencias y aparecen «expedición» e «imponer». Algunas concordancias del artículo 219, con 8 palabras de contexto:

- «Procedimiento para la imposición de [comparendo] Cuando el personal uniformado de la Policía tenga»
- «Término perentorio para objetar la orden de [comparendo] Vencidos los 3 días hábiles posteriores a la» (art. 223A)
- «Definición de orden de [comparendo] Entiéndase por esta la acción del personal uniformado» (art. 218)

**Medida correctiva.** 137 ocurrencias en 76 registros. Colocaciones: aplicacion (31; PMI 7,17), siguiente (22; PMI 5,92), imponer (20; PMI 7,5), aplicar (19; PMI 6,73), medida (15; PMI 4,31), correctiir (15; PMI 7,47). Es un término de procedimiento: se «impone», se «aplica» y se habla de su «incumplimiento».

**Espacio público.** 66 ocurrencias en 36 registros. Colocaciones: lugar (13; PMI 5,85), abierto (12; PMI 7,96), publico (10; PMI 4,17), comun (7; PMI 8,88), zona (6; PMI 7,29), area (5; PMI 6,49). Aparece junto a «lugares abiertos al público» y a «común», y en artículos tan distintos como el cuidado del espacio público (art. 50), las manifestaciones (arts. 53 y 54) y el consumo de bebidas alcohólicas (art. 34).

## 7. Glosario de términos jurídicos y sinónimos coloquiales

La gente pregunta «¿me ponen boleta si me cogen tomando guaro?» y la ley dice «orden de comparendo» y «bebidas alcohólicas». BM25 solo compara palabras, así que no une las dos formas. El glosario es el puente.

**Contenido.** 49 términos legales y 374 coloquiales, en el formato que ya usa el motor (`{"termino_legal": ["coloquial1", ...]}`), en `engine/glossary/sinonimos.json`. Cada término legal está escrito tal como aparece en el texto de la ley, y se verificó que las 49 claves existen en el corpus. Los coloquiales cubren sanciones y trámite, actuación policial, alcohol y drogas, espacio público y vendedores ambulantes, ruido, basura, mascotas y perros peligrosos, armas y pólvora, menores, transporte masivo, protestas, eventos, negocios, domicilio, invasiones, habitantes de calle y prostitución.

**Cómo funciona.** Si la pregunta contiene un coloquial, se agregan a la consulta de BM25 las palabras del término legal. Solo afecta a la búsqueda léxica: la búsqueda semántica y el modelo de lenguaje ven siempre la pregunta original. Los coloquiales se comparan por palabras completas, sin tildes ni mayúsculas, no por raíces, así que hay que listar plurales y conjugaciones («requisa», «me requisó», «me requisaron»).

**Criterios de construcción.**

- El glosario no es un diccionario de bogotanismos: de dos listas de expresiones bogotanas revisadas, casi todas eran jerga general sin relación con el Código y solo se tomaron las que aplican («polita», «chicha», «borrachera»).
- Las palabras con varios sentidos se dejan fuera o solo entran dentro de frases. «Boleta» significa comparendo, entrada a un evento o persona que queda en ridículo, y solo entra como «me ponen boleta». «Perico», «vaca», «mula», «rumba», «plaza» y «estación» se dejaron fuera, y «calle» y «casa» solo entran como «en la calle» y «mi casa». Los motivos de cada decisión están en `docs/analisis/glosario_notas.md`.
- De los 374 coloquiales, 323 no aparecen en el texto de la ley base. Esos son los que de verdad traducen jerga a lenguaje legal; los demás («perro», «niños», «uniformado») ya están en el Código.

**Pruebas.** `engine/analysis/probar_glosario.py` muestra qué coloquiales se activan en cada pregunta sin necesitar índices ni claves de API. Con las 20 preguntas distintas de `eval/`, 11 activan al menos un coloquial. Con frases de prueba se comprobó, por ejemplo, que «me requisó» activa «registro a persona» y que «el curso de inglés es obligatorio» no activa nada.

**Limitaciones conocidas.**

1. El mecanismo no tiene lista de exclusiones. Si una palabra activa el término equivocado, la única salida es quitarla o convertirla en frase. «Pelea de perros» activa «peleas caninas» pero también «confrontaciones violentas», porque «pelea» sola está en el glosario. «Moroso» se activa también con una deuda bancaria.
2. La evaluación de la expansión que trae el repositorio es parcialmente circular: sus tres preguntas coloquiales usan palabras de la semilla («boleta», «guaro», «pitbull»). Hacen falta preguntas nuevas con otros coloquiales.
3. Si la pregunta ya contiene todas las palabras del término legal, la expansión no agrega nada. Es el comportamiento diseñado, pero significa que la pregunta «Pagué la multa pronto, ¿me hacen descuento?» no registra ninguna expansión, porque ya trae «descuento», «pronto» y «pagar».
4. Los coloquiales son propuestas de uso común en Colombia. Siguen necesitando revisión por hablantes distintos al autor.

**Mantenimiento.** El glosario es un archivo versionado y se cambia por *pull request*, así queda historial y se puede deshacer un cambio que empeore los resultados. Un panel de administración con inicio de sesión sería una mejora futura: obligaría a tocar el motor, el backend y el frontend, y a agregar autenticación y registro de cambios, porque una palabra mal puesta altera las búsquedas de todos.

## 8. Relación con el clasificador temático

El clasificador del motor orienta la búsqueda hacia el tema de la pregunta, pero compara el nombre del tema con el campo `tema` de cada fragmento del corpus. En el corpus actual los 249 artículos de la ley base tienen el mismo valor, «texto fuente Ley 1801», y no coincide con ninguno de los temas de `engine/retrieval/temas.json`. Por eso el clasificador hoy no empuja a ningún fragmento.

Como parte del análisis se propone una estructura de 32 temas derivada de los capítulos y epígrafes reales de la ley (por ejemplo, «Tipos de multa» para los artículos 180 y 181, «Comparendo» para el 218, el 219 y el 223A, o «Caninos potencialmente peligrosos» para los artículos 126 a 134). Las 41 normas modificatorias heredan el tema del artículo de la Ley 1801 que modifican. La propuesta está en `propuesta_temas.json` y falta que quien es dueño del corpus decida si la adopta.

## 9. Limitaciones del análisis

- **Errores del lematizador.** `es_core_news_sm` lematiza mal algunas formas: «correctivo» aparece a veces como «correctiir».
- **Errores de extracción del PDF.** Hay palabras pegadas o duplicadas que vienen de las cabeceras de tabla, como «aaplicar» («AAPLICAR») o «comportamientosmedida». Contaminan las colocaciones por PMI, porque una palabra rara que siempre aparece junto al término sube artificialmente. Antes de lematizar convendría limpiar esas cabeceras.
- **Las tablas dominan algunos resultados.** Colocaciones y concordancias de «multa» salen de las tablas de sanciones, no de frases. Un análisis aparte del texto de las tablas separaría el lenguaje corrido del esquemático.
- **Notas editoriales.** Las referencias a la Corte Constitucional y a «Modificado por el Art. ...» se cuentan como texto del artículo. No se separaron.
- **KWIC limitado.** Se guardan solo los primeros 30 ejemplos de cada término.

## 10. Cómo reproducir los resultados

Desde la raíz del repositorio y con el entorno virtual activo:

```bash
python -m spacy download es_core_news_sm
python engine/analysis/estadisticas.py            # estadisticas_base.json
python engine/analysis/estadisticas.py --todo     # estadisticas_todo.json
python engine/analysis/frecuencias.py             # frecuencias_base.json y kwic_base.txt
python engine/analysis/frecuencias.py --todo      # frecuencias_todo.json y kwic_todo.txt
python engine/analysis/entidades_reglas.py        # entidades_reglas_base.json
python engine/analysis/entidades_reglas.py --todo # entidades_reglas_todo.json
python engine/analysis/probar_glosario.py "me cogieron con un porro"
```

Archivos de esta carpeta: `estadisticas_*.json`, `frecuencias_*.json`, `kwic_*.txt`, `entidades_reglas_*.json`, `glosario_notas.md` y `registro_trabajo.md`.
