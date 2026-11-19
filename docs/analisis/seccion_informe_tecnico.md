# Análisis lingüístico

*(Sección del informe técnico. Responsable: Santiago Castro. El detalle completo está en `docs/analisis/informe_analisis_linguistico.md`.)*

## Qué se hizo y con qué

El corpus de la Fase 1 tiene 290 registros: 249 artículos de la Ley 1801 y 41 disposiciones de normas que la modifican. Se analizó por separado el texto base y el corpus completo, porque las normas modificatorias repiten tablas enteras de sanciones y mezclarlas infla las frecuencias.

El análisis usa spaCy (`es_core_news_sm` 3.8.0) para tokenizar, lematizar y etiquetar. Se eligió spaCy y no Stanza porque carga sin problemas en el equipo de análisis y el enunciado permite cualquiera de los dos. Los montos y plazos se extraen con expresiones regulares, y las autoridades y lugares con un diccionario de formas, porque el reconocedor de entidades del modelo falla en este dominio: etiqueta «numeral» como lugar y «destrucción» como persona.

## Resultados principales

| | Ley base | Todo el corpus |
|---|---|---|
| Tokens | 53.443 | 68.654 |
| Tipos (lemas) | 3.701 | 3.756 |
| Relación tipo/token (formas) | 0,0914 | 0,072 |
| Longitud media y mediana por registro | 214,6 y 130 | 236,7 y 143,5 |

- **Es un texto nominal y repetitivo.** Hay 3,6 sustantivos por cada verbo y una relación tipo/token baja. El esqueleto de la ley se ve en los n-gramas: «multa general tipo» (228 veces), «autoridad de policía» (133) y «aglomeración de público» (128).
- **La ley expresa las sanciones por categorías, no por montos.** Hay 233 menciones de «multa general tipo N», de las cuales 123 son de tipo 4, y solo 18 referencias a salarios mínimos. Los plazos se escriben con el número en letras y en paréntesis, y los días son la unidad más usada.
- **Los cuatro términos del enunciado.** «Multa» aparece 353 veces en 56 artículos, «medida correctiva» 137 veces en 76, «espacio público» 66 en 36 y «comparendo» solo 22 en 7. Esa diferencia importa para el buscador: los usuarios dicen «comparendo» y el Código dice sobre todo «multa» y «orden de comparendo».
- **Las colocaciones de «multa»** («numeral», «tipo», «general») salen de las tablas de sanciones y no de frases corridas. Es una característica del corpus, y la tratamos como tal al interpretar los resultados.

## Aporte al motor: glosario de sinónimos coloquiales

Para cerrar la distancia entre cómo pregunta la gente y cómo escribe la ley se construyó un glosario de 49 términos jurídicos y 374 coloquiales (`engine/glossary/sinonimos.json`). Si la pregunta contiene un coloquial («guaro», «me ponen boleta», «tombos»), se agregan a la consulta léxica BM25 las palabras del término legal («bebidas alcohólicas», «orden de comparendo», «autoridades de policía»). La búsqueda semántica y el modelo de lenguaje ven siempre la pregunta original.

Dos decisiones de diseño merecen mencionarse. Las palabras con varios sentidos («boleta», «perico», «vaca», «rumba») se dejaron fuera o solo entran dentro de frases, y el glosario es un archivo versionado que se cambia por *pull request*, no un panel de administración.

## Limitaciones

- El mecanismo del glosario no tiene lista de exclusiones: «pelea de perros» activa también «confrontaciones violentas».
- La evaluación de la expansión que trae el repositorio es parcialmente circular, porque sus preguntas coloquiales usan palabras de la semilla original del glosario.
- BM25 usa *stemming* Snowball y no lematización, porque spaCy estaba bloqueado en el equipo donde se construyó el motor. El análisis lingüístico sí usa lematización.
- El lematizador y la extracción del PDF dejan errores («correctiir», «aaplicar») que contaminan las colocaciones por PMI.
- El clasificador temático hoy no tiene efecto, porque los 249 artículos comparten el mismo valor en el campo `tema`. Se propuso una estructura de 32 temas derivada de los capítulos reales de la ley; falta decidir si se adopta.
