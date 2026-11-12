# Registro de trabajo: análisis lingüístico (Fase 2)

Responsable: Santiago Castro. Es una lista simple, en orden, de lo que se va haciendo. Se completa y se ordena mejor más adelante.

## Hecho

1. (mié 11/11) Se leyó la guía personal `docs/guia-companeros/santiago-castro.md` y el README de la carpeta. Rol: análisis lingüístico (preprocesamiento, estadísticas, n-gramas, KWIC, glosario, informe). Pesa 15 % de la nota.
2. (mié 11/11) Se creó el entorno virtual `engine/.venv` y se instaló `engine/requirements.txt`.
3. (mié 11/11) Prueba urgente de spaCy: **carga bien** con `es_core_news_sm` 3.8.0. Lematiza «Los comandantes multaron a las personas» como `['el', 'comandante', 'multar', 'a', 'el', 'persona']`. Decisión: se usa spaCy, no hace falta Stanza.
4. (mié 11/11) Se probó la rama de spaCy de `engine/preprocess/texto_bm25.py`, que nunca se había ejecutado. Resultado con «¿Cuántos smdlv cuesta una multa tipo 4?»:
   - spaCy: `['smdlv', 'costar', 'multa', 'tipo', '4']`
   - Snowball: `['smdlv', 'cuest', 'mult', 'tip', '4']`
5. (mié 11/11) Se creó `engine/analysis/estadisticas.py` (tokens, tipos, relación tipo/token, longitud, POS, NER, montos y plazos). Guarda `docs/analisis/estadisticas_base.json` (solo ley base) y `docs/analisis/estadisticas_todo.json` (con `--todo`, incluye modificatorias).
6. (mié 11/11) Resultados de las estadísticas:

   | | Solo ley base | Todo el corpus |
   |---|---|---|
   | Registros | 249 | 290 |
   | Tokens | 53.443 | 68.654 |
   | Tipos (formas) | 4.884 | 4.942 |
   | Tipos (lemas) | 3.701 | 3.756 |
   | Tipo/token (formas) | 0,0914 | 0,072 |
   | Longitud media por registro | 214,6 | 236,7 |
   | Mediana | 130 | 143,5 |
   | Montos (regex) | 251 | 356 |
   | Plazos (regex) | 72 | 95 |

   Longitud mínima 22 y máxima 1.347 tokens en la ley base.

7. (mié 11/11) Se ajustó `estadisticas.py` para que no sobrescriba resultados (`estadisticas_base.json` y `estadisticas_todo.json`) y se verificó en el equipo: las cifras coinciden con la tabla de arriba.
8. (mié 11/11) Se creó `engine/analysis/frecuencias.py` (adelanto del día 4): lemas más frecuentes, bigramas, trigramas, colocaciones (por frecuencia y por PMI) y KWIC de «multa», «comparendo», «medida correctiva» y «espacio público». Guarda `docs/analisis/frecuencias_<base|todo>.json` y `docs/analisis/kwic_<base|todo>.txt`. Los términos se buscan por lema, así «medidas correctivas» cuenta como «medida correctiva». Resultados en la ley base:

   | Término | Ocurrencias | Registros |
   |---|---|---|
   | multa | 353 | 56 |
   | comparendo | 22 | 7 |
   | medida correctiva | 137 | 76 |
   | espacio público | 66 | 36 |

   Bigramas más frecuentes: «multa general» (237), «general tipo» (228), «medida correctivo» (137), «tipo 4» (123), «suspensión temporal» (115), «corte constitucional» (114), «espacio público» (66). Trigrama principal: «multa general tipo» (228).

9. (mié 11/11) Se corrió `frecuencias.py` en el equipo, con la ley base y con `--todo`. Las cifras de la ley base coinciden con las de arriba. Resultados con todo el corpus (290 registros, 68.654 palabras):

   | Término | Ocurrencias | Registros |
   |---|---|---|
   | multa | 510 | 75 |
   | comparendo | 40 | 11 |
   | medida correctiva | 177 | 97 |
   | espacio público | 94 | 45 |

   Bigramas principales: «multa general» (327), «general tipo» (307), «medida correctivo» (177), «tipo 4» (165), «suspensión temporal» (151), «espacio público» (94).

10. (jue 12/11) Borrador 1 del glosario de sinónimos coloquiales en `engine/glossary/sinonimos.json`: 49 términos legales y 339 coloquiales, mismo formato que el motor (no cambia el contrato). Se verificó que las 49 claves existen en el texto del corpus (se corrigieron «habitantes de y en calle» y «necesidades fisiológicas») y se probó con el mismo código de expansión del motor. Pendiente de revisión humana de los coloquiales.
11. (jue 12/11) Se creó `docs/analisis/glosario_notas.md` (decisiones, palabras ambiguas excluidas y por qué, palabras con riesgo, cómo revisar) y `engine/analysis/probar_glosario.py`, una prueba liviana que no necesita índices ni claves de API: muestra qué coloquiales se activan en cada pregunta. Con las 19 preguntas del repo, 11 activan al menos un coloquial.
12. (jue 12/11) Se analizó la idea de que solo administradores puedan agregar o quitar palabras del glosario. Conclusión: hoy no hay administración ni autenticación en el repo y la guía no lo pide; tocaría el motor (endpoint más `recargar()`, que hoy nadie llama) y el frontend, que no son del rol de lingüística. Propuesta: glosario como archivo versionado con cambios por PR y panel de administración como mejora futura en el informe.

13. (jue 12/11) Se verificó en el equipo: `probar_glosario.py` carga `entradas: 49` y 11 de las 19 preguntas del repo activan al menos un coloquial (igual que en la prueba previa). Se revisaron dos listas de expresiones bogotanas aportadas por Santiago: casi todas son jerga general sin relación con el Código; se agregaron «polita», «chicha» y «borrachera» (ahora 345 coloquiales) y se anotaron las ambiguas en `glosario_notas.md`. Pendiente decidir «chino» y «china» (niño).

## Hallazgos para el informe

1. El NER genérico de spaCy (`es_core_news_sm`) es ruidoso en texto jurídico: etiqueta «numeral» como lugar y «destrucción» o «suspensión» como persona. Se justifica usar reglas propias para autoridades, plazos y montos.
2. La Ley 1801 casi no expresa montos en SMDLV. Usa «Multa General tipo N» (unas 233 veces) y plazos escritos como «tres (3) meses» o «cuarenta y ocho (48) horas».
3. La media de longitud (214) es mucho mayor que la mediana (130): pocos artículos muy largos elevan el promedio.
4. BM25 del motor usa stemming Snowball, no lematización, porque spaCy está bloqueado por Windows en el equipo del líder. El análisis lingüístico del informe sí usa lematización con spaCy.
5. `main` ya trae el corpus completo de Wilder (`corpus/procesados/corpus_ley_1801.json`, 290 registros: 249 de la ley base y 41 de normas que la modifican, adicionan o corrigen) y eliminó `corpus/muestra/`. El motor todavía apunta al corpus de muestra por defecto en `engine/indexing/embeddings.py`; para reconstruir índices hay que pasar `--corpus corpus/procesados/corpus_ley_1801.json`. Pendiente avisar a Duvan.

6. Las colocaciones de «multa» (numeral, tipo, general) salen de las tablas de sanciones («Numeral 1 Multa General tipo 2»), no de frases corridas. Conviene explicarlo en el informe y, si se quiere, analizar aparte el texto de las tablas.
7. Hay pequeños errores del lematizador y del texto fuente que se ven en los resultados: «correctivo» aparece a veces como «correctiir», y hay palabras pegadas como «aaplicar». Para el informe, anotarlos como limitaciones del modelo `es_core_news_sm` y de la extracción del PDF.
8. «Comparendo» aparece solo 22 veces (7 registros): es un término poco frecuente en la ley frente a «multa». Útil para el glosario: la gente dice «comparendo» y el Código dice sobre todo «multa» y «orden de comparendo».
9. Al sumar las normas que modifican la ley, «comparendo» sube de 22 a 40 ocurrencias y aparece junto a «expedición» e «imponer»; y «SMDLV» aparece como colocación de «multa» (en la ley base casi no estaba). Es decir, las reformas introducen más lenguaje de comparendo y de montos en salarios mínimos. Útil para el glosario y para explicar por qué se analizan los dos alcances por separado.
10. Siguen apareciendo errores de extracción o lematización («admitar», «comunitarioo», «correctiir»). Anotarlos como limitaciones; si se quiere, limpiar el texto antes de lematizar.
11. Palabras de la calle que cambian de significado (polisemia): «boleta» (comparendo o entrada a un evento), «estación» (de policía o de TransMilenio), «perico», «vaca», «mula», «rumba». «Boleta» tiene tres sentidos (comparendo, entrada a evento, persona que queda en ridículo). Se resuelve poniéndolas solo en frases («me ponen boleta») o dejándolas fuera. El mecanismo no tiene exclusiones: «pelea de perros» activa tanto riñas como peleas caninas. Buen ejemplo para el informe.
12. La evaluación de expansión del repo es parcialmente circular: las 3 preguntas coloquiales usan palabras de la semilla («boleta», «guaro», «pitbull»). Conviene agregar preguntas nuevas con otros coloquiales.

## Pendiente

1. Avisarle a Duvan que spaCy carga y que se usa spaCy (la guía lo pedía el día 1).
2. Revisar los archivos `kwic_base.txt` y `kwic_todo.txt` para elegir ejemplos del informe (día 4).
3. Revisar el borrador del glosario: agregar y quitar coloquiales según cómo habla la gente, probar con `python engine/analysis/probar_glosario.py` y revisar las palabras de riesgo en `glosario_notas.md` (día 5). Evaluar con `python eval/comparar_expansion.py` (necesita índices, coordinar con Duvan) y entregar al motor en un PR separado que reemplaza `engine/glossary/sinonimos.json` (día 7).
4. Reorganizar `engine/retrieval/temas.json` por libro y título reales de la ley, coordinando los nombres de los temas con Wilder (día 6).
5. Revisar `engine/preprocess/texto_bm25.py` para que sea coherente con el preprocesamiento; si cambia el método, reconstruir índices y repetir `python eval/comparar_expansion.py` (día 7).
6. Borrador y cierre del informe de análisis en `docs/analisis/` (días 6 a 8) y sección «Análisis lingüístico» del informe técnico (día 9).
7. Pasar el trabajo a un repositorio con git (hoy está en un ZIP descargado), crear la rama `feature/santiago-castro-linguistica` y abrir PR a `main`.
8. Ensayo de la sustentación (día 10).
