# Corpus documental de la Ley 1801 de 2016

## Estructura de entrada

Guarda los PDF en `documentos/leyes/` o `documentos/decretos/`. Los nombres deben
identificar la norma, por ejemplo:

- `Ley_1801_de_2016.pdf`: PDF base de trabajo.
- `Mod_Ley_2000_de_2019.pdf`: norma modificatoria.
- `Adi_Ley_2030_de_2020.pdf`: norma aditiva.
- `Mod_Decreto_555_de_2017.pdf`: decreto relacionado.

El nombre `Mod_` o `Adi_` se conserva como clasificación del archivo, no como
conclusión jurídica sobre la vigencia actual de sus disposiciones.

## Construcción

Desde la raíz del repositorio, instala las dependencias del motor en su entorno:

```powershell
.\engine\.venv\Scripts\python.exe -m pip install -r engine\requirements.txt
```

Después ejecuta:

```powershell
.\engine\.venv\Scripts\python.exe corpus\construir_corpus.py
```

El proceso genera:

- `procesados/texto_extraido/`: JSON por documento, con metadatos, hash SHA-256 y
  texto separado por página.
- `procesados/corpus_ley_1801.json`: registros segmentados con los campos que
  consume el indexador (`id`, `ubicacion`, `epigrafe`, `texto`, `vigencia` y
  `tema`), además de metadatos de procedencia.
- `procesados/corpus_ley_1801_revision.json`: documentos sin referencia explícita
  detectada, registros duplicados fusionados y archivos legados que requieren
  revisión manual.

También se pueden ejecutar por separado:

```powershell
.\engine\.venv\Scripts\python.exe corpus\extraer.py
.\engine\.venv\Scripts\python.exe corpus\segmentar.py
```

`extraer.py` guarda texto por página; `segmentar.py` construye los registros RAG
a partir de esos JSON. Si el PDF es una imagen escaneada sin texto seleccionable,
la extracción se detiene con un error: primero debe aplicarse OCR.

## Tratamiento de la norma base y sus reformas

- Los artículos se conservan tal como aparecen en el PDF de la Ley 1801. El script no
  determina si ese PDF contiene el texto promulgado originalmente o una versión
  consolidada; por eso se etiquetan `no_verificada`.
- Las disposiciones de otras leyes o decretos se guardan por separado y su
  `ubicacion` indica tanto el artículo de la fuente como los artículos de la Ley
  1801 a los que hacen referencia.
- Las reformas se etiquetan `no_verificada`; el script no supone que una
  modificación sigue vigente, no resuelve decisiones judiciales y no combina
  automáticamente textos de distintas fechas.
- Solo se agregan al corpus RAG disposiciones con referencias explícitas
  detectables a la Ley 1801. Las demás permanecen en `texto_extraido` y aparecen
  en el archivo de revisión. Una referencia no detectada no demuestra que la
  norma sea jurídicamente irrelevante.

La segmentación de las normas sigue la numeración consecutiva de sus artículos y
la detección de referencias es heurística. Antes de usar el
resultado para responder consultas jurídicas, revisa el archivo de revisión y
contrasta los textos, las relaciones y la vigencia con una fuente oficial.
Este proceso genera un corpus de fuentes, **no una versión consolidada oficial**
de la Ley 1801.

El motor actual está orientado a citar artículos de la Ley 1801. Para indexar
estas disposiciones de varias normas en ese motor, primero se debe ampliar su
manejo de citas para incluir la norma y el artículo fuente; este JSON conserva
esa procedencia, pero no cambia por sí solo el comportamiento de citación de la
API.

## Formato de cada registro

| Campo | Descripción |
|---|---|
| `id` | Identificador único del artículo o de la disposición fuente. |
| `ubicacion` | Norma y artículo fuente; para reformas, incluye los artículos objetivo detectados. |
| `epigrafe` | Encabezado descriptivo para recuperación. |
| `texto` | Texto extraído, limpiando encabezados repetidos y cortes de palabra de página. |
| `vigencia` | `no_verificada`; no es un dictamen jurídico. |
| `tema` | Clasificación básica por tipo de disposición. |
| `fuente`, `fuentes` (si se fusionaron duplicados), `norma`, `articulo_fuente`, `articulos_ley_1801`, `tipo_disposicion` | Trazabilidad adicional. |
