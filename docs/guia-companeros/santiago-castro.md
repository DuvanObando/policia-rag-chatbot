# Guía de Santiago Castro: análisis lingüístico (Fase 2)

> Antes de esta guía, lee el [README de la carpeta](README.md): explica el proyecto, el estado del motor, cómo levantarlo y las reglas comunes (repo fuera de OneDrive, clave de Gemini propia, rama por persona, etc.).

## Tu rol

Eres el responsable del **análisis lingüístico del corpus**: preprocesamiento, estadísticas, n-gramas, KWIC, glosario y sinónimos coloquiales, y el **informe de análisis** (entregable 2 del proyecto). Pesa 15 % de la nota. Además, tu glosario alimenta directamente al buscador: hoy el motor trae uno provisional que tú reemplazas.

## URGENTE HOY: comprueba que spaCy cargue en tu equipo

En el equipo de Duvan (Windows 11) **spaCy no se pudo importar**: Windows bloqueó una de sus librerías nativas (`preshed/maps.pyd`) con el mensaje «Una directiva de Control de aplicaciones bloqueó este archivo» (puede ser el *Control inteligente de aplicaciones* u otra política de Windows). Si te pasa a ti, el análisis lingüístico se queda sin herramienta. Pruébalo **hoy**, con el entorno virtual activado:

```bash
pip install -r engine/requirements.txt
python -m spacy download es_core_news_sm
python -c "import spacy; nlp = spacy.load('es_core_news_sm'); print([t.lemma_ for t in nlp('Los comandantes multaron a las personas')])"
```

- **Si carga:** perfecto, sigue con spaCy (el enunciado pide `es_core_news` o Stanza).
- **Si falla con ese error: usa Stanza** (el enunciado lo permite). Usa PyTorch, que sí funciona en estos equipos.
- **NO desactives la protección de Windows para forzarlo.** En Windows 11, el Control inteligente de aplicaciones **no se puede volver a activar sin reinstalar Windows**. No lo arregles tocando la configuración de seguridad.
- Avísale a Duvan **el resultado hoy mismo** (carga o no carga, y qué usarás).

## Tareas (fechas según el cronograma del plan, día 1 = lunes 9/11)

- [ ] **Día 1 · Lun 09/11 (hoy):** probar spaCy (arriba); si falla, preparar Stanza. Diseñar el pipeline.
- [ ] **Día 2 · Mar 10/11:** normalización, tokenización y lematización sobre el corpus provisional (mientras tanto, usa `corpus/muestra/codigo_muestra.json`).
- [ ] **Día 3 · Mié 11/11:** etiquetado gramatical (POS), reconocimiento de entidades (NER: autoridades, lugares, montos, plazos) y estadísticas (número de artículos, tokens, tipos, relación tipo/token, longitud media por fragmento).
- [ ] **Día 4 · Jue 12/11:** frecuencias, n-gramas, colocaciones y KWIC de «multa», «comparendo», «medida correctiva» y «espacio público». Cuando llegue el **corpus completo** (Wilder, día 4), repite el análisis con él.
- [ ] **Día 5 · Vie 13/11:** **glosario y sinónimos coloquiales reales** (ver abajo).
- [ ] **Día 6 · Lun 16/11:** borrador del informe de análisis. Reorganizar `engine/retrieval/temas.json` con la estructura real de la ley (ver abajo).
- [ ] **Día 7 · Mar 17/11:** **entregar el glosario al motor** (PR que reemplaza `engine/glossary/sinonimos.json`). Revisar `engine/preprocess/texto_bm25.py` y, si cambia el método de preparación del texto, reconstruir los índices.
- [ ] **Día 8 · Mié 18/11:** cerrar el informe de análisis lingüístico (en `docs/analisis/`).
- [ ] **Día 9 · Jue 19/11:** sección «Análisis lingüístico» del informe técnico (máximo 15 páginas en total; lo compila Duvan).
- [ ] **Día 10 · Vie 20/11:** ensayo de la sustentación (todos explican el flujo completo).

## Archivos que te pertenecen

- `engine/preprocess/` (incluido `texto_bm25.py`; `extraer_senado.py` es la base de Wilder), `engine/analysis/`, `engine/glossary/`, `docs/analisis/`

## Lo que ya dejé listo para ti

- **Un glosario provisional** en `engine/glossary/sinonimos.json` (18 entradas semilla, sacadas de 10 artículos). **Es tuyo para reemplazar.**
- **El mecanismo que lo usa:** `engine/retrieval/expansion.py`. Si la pregunta del usuario contiene un coloquial («guaro»), se agregan a la consulta de **BM25** las palabras del término legal («bebidas alcohólicas»). Solo afecta a la búsqueda léxica, nunca a la semántica. Se desactiva con `BUSQUEDA_EXPANSION=0` en el `.env`.
- **Una función de preparación de texto** para BM25: `engine/preprocess/texto_bm25.py` (`tokens_bm25`). Hace minúsculas, tokenización, quita stopwords, lematiza (spaCy si carga, y si no un *stemmer* Snowball) y quita tildes. Está documentada como **punto de conexión con tu preprocesamiento**.
- **Un clasificador temático** por palabras clave: `engine/retrieval/temas.json` (`clasificador.py` lo lee).
- **Las evaluaciones**, para comprobar que no rompes nada: `python eval/comparar_expansion.py` (tarda un par de minutos y no usa Gemini ni necesita clave), y los documentos `docs/busqueda_hibrida.md` y `docs/clasificador.md`.

## Glosario de sinónimos: formato y reglas

Formato (el mismo que el provisional):

```json
{
  "bebidas alcohólicas": ["trago", "tragos", "licor", "guaro", "alcohol", "cerveza", "cervezas"],
  "orden de comparendo": ["comparendo", "boleta", "papeleta", "multa de la policía"]
}
```

- La **clave** es el término legal **tal como aparece en el Código** (así lo encuentra BM25); la lista son los coloquiales. Las claves que empiezan con `_` se ignoran (el archivo trae notas ahí).
- La detección es por **palabras completas, sin tildes ni mayúsculas, no por raíces**. Por eso hay que **listar plurales y variantes de género** (`perro` y `perros`; `uniformado` y `uniformados`). Un coloquial de varias palabras debe ir completo y en orden.
- **Evita términos genéricos** que salen en casi cualquier pregunta: `agente`, `policía`, y `casa` suelta si genera ruido (mejor en frase: «mi casa»). Se quitó `agente` del glosario semilla por eso: una versión anterior empeoraba una pregunta porque «caso» activaba «casa» y «agente» agregaba ruido.
- Un coloquial debe señalar **una sola cosa** del Código.

## Reorganizar `temas.json`

`engine/retrieval/temas.json` define los temas, sus palabras clave y el libro y título al que pertenecen. Hoy tiene 10 temas inventados para los 10 artículos de muestra. Cuando llegue el corpus completo, reorganízalo **por libro y título de la ley real** y amplíalo con tu glosario. Dos requisitos:

- El `tema` de cada entrada **debe coincidir con el campo `tema` de los fragmentos del corpus** (así se sabe qué artículos reciben el empuje). Coordina con **Wilder** los nombres de los temas.
- Se edita sin tocar Python; el motor lee el archivo al arrancar. El archivo trae instrucciones en `_ayuda`.

## `texto_bm25.py`: revisarlo y probar la rama de spaCy

- Revísalo para que sea **coherente con tu preprocesamiento** (misma normalización, mismas stopwords).
- La rama de **spaCy nunca se ha ejecutado** (en el equipo donde se escribió spaCy estaba bloqueado). Si en tu equipo carga, pruébala: `tokens_bm25("texto", metodo="spacy")`. Si usas Stanza, agrégalo como tercer método en ese archivo (`tokens_bm25_lote` y `descripcion_metodo`).
- El índice BM25 guarda con qué método se construyó. Si el método disponible cambia, **el motor arranca con `listo: false`** y pide reconstruir el índice: ejecuta los dos `build_index.py` (ver README de la carpeta). Después repite `python eval/comparar_expansion.py` y deja anotado en `docs/busqueda_hibrida.md` si los resultados cambian.

## Para el informe

BM25 usa **stemming Snowball** (o spaCy donde carga), **no lematización**, y hay que explicar por qué: spaCy está bloqueado por Windows en el equipo del líder. El análisis lingüístico del informe es independiente de ese detalle: ahí sí debes usar lematización (spaCy o Stanza).

## Cómo entregar

1. `git checkout main && git pull`, luego `git checkout -b feature/santiago-castro-linguistica`.
2. Haz commits pequeños y sube con `git push -u origin feature/santiago-castro-linguistica`.
3. Abre un **pull request a `main`**; lo revisa Duvan. Entrega el glosario (`sinonimos.json`) en un PR **separado y pronto** (día 7), porque el motor lo usa.
4. Avísale a Duvan por WhatsApp cuando el PR esté listo, para reconstruir índices y repetir las comparaciones.

## Avisos y peticiones

- Dime **hoy** si spaCy carga o no, y qué vas a usar.
- No toques `engine/retrieval/` ni `engine/indexing/` sin avisar: son del motor. Para cambios allí, pídelos o hazlos en un PR aparte.
- No subas el entorno virtual, los índices ni modelos descargados.

## Mensaje para enviar

> Santiago, ya dejé el motor del chatbot listo en `main`. Lo urgente **hoy**: prueba que spaCy te cargue (en mi PC Windows lo bloqueó el control de aplicaciones). Si te falla usa **Stanza**, y por favor **NO desactives esa protección de Windows**: no se puede volver a activar sin reinstalar el sistema.
> Tu guía con fechas y todo lo que dejé armado está en `docs/guia-companeros/santiago-castro.md` (lee primero el README de esa carpeta).
> Después necesito tu **glosario real** para reemplazar el provisional (`engine/glossary/sinonimos.json`) hacia el martes 17.
> Avísame hoy qué te funcionó y saca tu clave gratis de Gemini 🙏
