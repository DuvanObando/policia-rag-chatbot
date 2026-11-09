# Guía de Wilder: corpus (Fase 1) y banco de preguntas

> Antes de esta guía, lee el [README de la carpeta](README.md): explica el proyecto, el estado del motor, cómo levantarlo y las reglas comunes (repo fuera de OneDrive, clave de Gemini propia, rama por persona, etc.).

## Tu rol

Eres el responsable del **corpus**: el texto de la Ley 1801 de 2016, limpio, dividido en unidades y con metadatos. **Todo el chatbot se apoya en tu trabajo**: lo que tú guardes es lo que el buscador encuentra y lo que el modelo cita. Después construyes el **banco de 50+ preguntas** con el que se evalúa el sistema. Pesos en la nota: corpus 20 %, evaluación 15 %.

## Prioridad ALTA: vigencia por numeral, no por artículo

Hoy el corpus de muestra guarda **una sola vigencia por artículo**, pero la ley cambia por numeral y por parágrafo. Consecuencia real: el chatbot responde que beber alcohol en un parque está prohibido citando **art. 140, num. 7**, y en la fuente oficial esos apartes del numeral están **tachados como inexequibles**. En otras palabras, hoy cita texto que la Corte anuló. El motor no puede evitarlo: solo conoce lo que dice el corpus.

**Qué hacer:**

- Guardar la **vigencia de cada numeral y de cada parágrafo**, no solo la del artículo.
- Marcar los **apartes inexequibles** (texto tachado). Ejemplo: art. 140, num. 7.
- Marcar los **parágrafos condicionalmente exequibles**. Ejemplo: art. 163, par. 1.
- Marcar también lo **modificado** (p. ej. art. 180, modificado por la Ley 2450 de 2025; art. 163, num. 7 agregado por la Ley 2455 de 2025).

**Cómo la fuente marca el texto tachado.** En el HTML de la fuente (Secretaría del Senado) los apartes inexequibles van dentro de etiquetas `<S>...</S>`. Por ejemplo, en `ley_1801_2016_pr003.html`, el num. 7 del art. 140 es:

```html
<p>7. &lt;Apartes tachados INEXEQUIBLES&gt; Consumir <S><span class="b_aj">bebidas alcohólicas</span></S>,
sustancias <S><span class="b_aj">psicoactivas o</span></S> prohibidas en estadios, ...
```

El script de referencia (`engine/preprocess/extraer_senado.py`) **elimina todas las etiquetas**, así que pierde el tachado y solo conserva la nota «Apartes tachados INEXEQUIBLES». **Hay que leer las etiquetas `<S>` antes de quitarlas.** Las notas entre `< >` («Parágrafo CONDICIONALMENTE exequible», «Numeral adicionado por…») también dicen la vigencia por numeral; el script las deja en un archivo aparte (`marcas.json`) como punto de partida.

**Propuesta de formato** (a acordar con Duvan antes de fijarla; la idea es **agregar** campos sin quitar los actuales, para no romper el motor):

```json
{
  "id": "art-140",
  "ubicacion": {"libro": "...", "titulo": "...", "capitulo": "...", "articulo": "Artículo 140"},
  "epigrafe": "COMPORTAMIENTOS CONTRARIOS AL CUIDADO E INTEGRIDAD DEL ESPACIO PÚBLICO",
  "texto": "texto completo del artículo",
  "vigencia": "modificado",
  "tema": "...",
  "unidades": [
    {"id": "art-140-num-7", "tipo": "numeral", "numero": "7", "texto": "...",
     "vigencia": "inexequible_parcial",
     "apartes_inexequibles": ["bebidas alcohólicas", "psicoactivas o"],
     "nota": "Apartes tachados INEXEQUIBLES (fuente: Senado)"},
    {"id": "art-163-par-1", "tipo": "parágrafo", "numero": "1", "texto": "...",
     "vigencia": "exequible_condicionado"}
  ]
}
```

Las vigencias que hoy reconoce el contrato son `vigente`, `modificado`, `inexequible`, `exequible_condicionado` y `no_verificada`. **`inexequible_parcial` es nueva**: cuando la definan, Duvan actualiza `docs/api_contract.md`, `build_index.py`, el prompt y el frontend. No cambies los nombres de los campos que ya existen sin avisar.

## Segmentar parágrafos y numerales como unidades separadas

Para que el chatbot cite con precisión (p. ej. «Art. 180, par.»), el corpus debe poder dar cada **numeral** y cada **parágrafo** como unidad con su número. La jerarquía completa es: libro → título → capítulo → artículo → parágrafo / numeral, con expresiones regulares. Cuida los casos borde: parágrafos sin número («PARÁGRAFO.»), «PARÁGRAFO TRANSITORIO», numerales cuyo texto es solo «INEXEQUIBLE», y las **tablas** de medidas correctivas dentro de los parágrafos (art. 124, 140 y otros).

## Tareas (fechas según el cronograma del plan, día 1 = lunes 9/11)

- [ ] **Día 1 · Lun 09/11:** elegir y registrar la fuente oficial con la **fecha de consulta**; arrancar el corpus provisional de **20 a 30 artículos**.
- [ ] **Día 2 · Mar 10/11:** entregar el **corpus provisional** (20–30 artículos) con todos los metadatos, ya con la vigencia por numeral para esos artículos (PR). Desbloquea a Santiago Castro y a Duvan. Puedes seguir usando `corpus/muestra/codigo_muestra.json` hasta entonces.
- [ ] **Día 3 · Mié 11/11:** limpieza y segmentación con regex del **corpus completo** (los 243 artículos: libro, título, capítulo, artículo, parágrafo, numeral).
- [ ] **Día 4 · Jue 12/11:** **corpus completo con la vigencia verificada**: modificaciones (Ley 2000 de 2019 y las demás que aparecen en el texto consolidado: Leyes 2197/2022, 2318/2023, 2450/2025, 2455/2025…) y **sentencias de la Corte Constitucional** (inexequibilidad y exequibilidad condicionada). **Avisa a Duvan en cuanto lo subas.**
- [ ] **Día 5 · Vie 13/11:** completar `corpus/README_corpus.md` (origen, fecha de consulta, criterios de segmentación, metadatos, licencia de uso) y la **sección 1 de `docs/segmentacion.md`** (regex, criterios y casos borde).
- [ ] **Día 6 · Lun 16/11:** banco de preguntas, primera mitad (incluye las 10 preguntas de ejemplo del enunciado).
- [ ] **Día 7 · Mar 17/11:** banco completo de **50+ preguntas** (ver abajo).
- [ ] **Día 8 · Mié 18/11:** revisar las respuestas de referencia; revisión manual de exactitud, fidelidad y corrección de la cita junto con Duvan.
- [ ] **Día 9 · Jue 19/11:** secciones «Corpus» y «Evaluación» del informe técnico (el informe completo es de máximo 15 páginas y lo compila Duvan).
- [ ] **Día 10 · Vie 20/11:** ensayo de la sustentación (todos explican el flujo completo).

## Archivos que te pertenecen

- `corpus/` (incluidos tus scripts de limpieza y segmentación), `corpus/README_corpus.md`
- `docs/segmentacion.md` (la sección 1)
- `eval/banco_preguntas.json`

## Lo que ya dejé listo para ti

- **Un script de partida:** `engine/preprocess/extraer_senado.py`. Lee las 6 páginas HTML del Senado, quita las notas editoriales, detecta libro, título, capítulo y artículos (los 243) y calcula una vigencia aproximada por artículo. Ojo: **no descarga** las páginas (hay que bajarlas antes a una carpeta `senado/`; las 6 URLs están en `corpus/muestra/README.md`), y al final solo guarda 10 artículos fijos (`SEL`). Es una **base de referencia, no el pipeline oficial**: tú decides si lo amplías o lo rehaces. Uso: `python engine/preprocess/extraer_senado.py <carpeta> <salida.json> <marcas.json>`.
- **El esquema de referencia:** `corpus/muestra/codigo_muestra.json` (10 artículos) y su `corpus/muestra/README.md` (fuente, criterio de vigencia y notas).
- **Reglas del esquema actual** (mantenlas): `id` = `art-N`; `ubicacion` como **objeto** con `libro`, `titulo`, `capitulo`, `articulo`; `epigrafe` tal cual la fuente; `texto` sin notas editoriales; `vigencia`; `tema`.
- **Un motor que usa tu corpus sin cambios de código:** `python engine/indexing/build_index.py --corpus RUTA --estrategia fragmentos` (y `articulo`).
- **Un ejemplo del formato del banco:** `eval/ejemplo_formato.json`.

## Banco de preguntas (50+)

Formato (de `eval/ejemplo_formato.json`): `pregunta`, `respuesta_referencia`, `articulos_esperados` (lista) y `fuera_de_dominio` (true/false). Puedes agregar un campo `tipo` para poder analizar por categoría. Incluye:

- Las **10 preguntas de ejemplo del enunciado**, ampliadas hasta 50 o más.
- **Preguntas trampa fuera de dominio** (tránsito, impuestos, trámites de otras entidades…) en cantidad suficiente, **al menos 15** (cerca de un tercio). El motor no usa un umbral numérico de relevancia: la decisión «no está en el Código» la toma el modelo con el prompt, y estas preguntas sirven para medirla en el modo **híbrido** (que siempre trae resultados, aunque no tengan nada que ver) y decidir si hace falta algo más.
- **Preguntas que piden un artículo por número** («¿Qué dice el artículo 163?»).
- **Preguntas ambiguas entre dos temas** (p. ej. un perro suelto en el parque: animales y espacio público).
- **Preguntas muy coloquiales** (jerga: «guaro», «boleta», «tombos»…).
- Preguntas con **términos exactos** (siglas, plazos, nombres de leyes).
- Que cada `articulos_esperados` sea verificable en el texto del corpus, y la `respuesta_referencia` esté escrita con tus palabras (no copiada del artículo).

## Cómo entregar

1. `git checkout main && git pull`, luego `git checkout -b feature/wilder-corpus`.
2. Trabaja y haz commits pequeños. Sube con `git push -u origin feature/wilder-corpus`.
3. Abre un **pull request a `main`**; lo revisa Duvan. **No subas** `.env`, PDFs de `docs/` ni archivos grandes de descarga.
4. **Avísale a Duvan por WhatsApp** al entregar (provisional y completo): él reconstruye los índices y repite las comparaciones con tu corpus.
5. Corpus y banco entran en PR separados.

## Avisos y peticiones

- **El campo `tema` de cada fragmento tiene que coincidir con los nombres de `engine/retrieval/temas.json`**, que el clasificador usa para orientar la búsqueda. Si defines tu propia taxonomía de temas, **coordínala con Santiago Castro**, que reorganiza ese archivo con tu corpus.
- Si cambias nombres de campos del corpus, avisa antes: el motor, `build_index.py` y el clasificador los leen.
- El corpus de muestra tiene vigencias aproximadas (una por artículo, con un criterio documentado en `corpus/muestra/README.md`). Es provisional: no lo trates como respuesta correcta.

## Mensaje para enviar

> Wilder, ya dejé listo el motor del chatbot en `main` (busca, responde con citas y todo). Lo que más depende de ti ahora es el corpus: guarda la **vigencia por numeral**, no por artículo, porque hoy el bot cita texto que la Corte ya anuló (art. 140, num. 7; en el HTML del Senado viene tachado con `<S>`).
> Tu guía con fechas, el esquema y lo que ya dejé listo: `docs/guia-companeros/wilder.md`. Lee primero el README de esa carpeta.
> Necesito el **corpus provisional (20–30 artículos) el martes 10** y el **completo el jueves 12**. Avísame apenas lo subas para reconstruir los índices.
> Y saca tu propia clave gratis de Gemini y trabaja el repo fuera de OneDrive 🙏
