# Corpus de muestra (PROVISIONAL)

> **Corpus PROVISIONAL, solo para desarrollo del motor** (embeddings, índice FAISS, recuperación y prompt).
> **No es el corpus del proyecto.** Será reemplazado por el corpus oficial que construye Wilder en la Fase 1 (`corpus/`, ver `corpus/README_corpus.md`). No debe usarse para evaluar ni para el informe.

## Fuente

Secretaría del Senado de la República de Colombia, base documental, **Ley 1801 de 2016** (texto consolidado con sus notas de vigencia). El texto está repartido en seis páginas:

- <http://www.secretariasenado.gov.co/senado/basedoc/ley_1801_2016.html>
- <http://www.secretariasenado.gov.co/senado/basedoc/ley_1801_2016_pr001.html>
- <http://www.secretariasenado.gov.co/senado/basedoc/ley_1801_2016_pr002.html>
- <http://www.secretariasenado.gov.co/senado/basedoc/ley_1801_2016_pr003.html>
- <http://www.secretariasenado.gov.co/senado/basedoc/ley_1801_2016_pr004.html>
- <http://www.secretariasenado.gov.co/senado/basedoc/ley_1801_2016_pr005.html>

**Fecha de consulta:** 2026-11-09.

Las páginas están en codificación ISO-8859-1. En ellas se identificaron 243 artículos; de ellos se extrajeron los 10 de esta muestra.

## Contenido

`codigo_muestra.json`: arreglo de 10 artículos, de temas distintos, ordenados por número.

| Campo | Descripción |
|---|---|
| `id` | `art-<número>` |
| `ubicacion` | Objeto con `libro`, `titulo`, `capitulo` y `articulo`, tomados de los encabezados de la fuente |
| `epigrafe` | Epígrafe del artículo, tal cual aparece en la fuente (en mayúsculas) |
| `texto` | Texto del artículo, tal cual aparece en la fuente (numerales, parágrafos y tablas incluidos) |
| `vigencia` | `vigente`, `modificado`, `inexequible` o `exequible_condicionado` (ver criterio abajo) |
| `tema` | Etiqueta temática **asignada por nosotros** para probar el buscador; no viene de la fuente |

### Cómo se limpió el texto

Solo se quitaron las notas editoriales y los espacios sobrantes:

- Líneas de enlaces de la página: «Notas de Vigencia», «Jurisprudencia Vigencia», «Legislación Anterior», «Notas del Editor».
- Marcas entre `<...>` (por ejemplo `<Artículo modificado por el artículo 19 de la Ley 2450 de 2025. El nuevo texto es el siguiente:>`).
- Las tablas de la fuente se dejaron como texto, con las celdas separadas por ` | `.

El texto de la ley no se reescribió ni se completó.

### Criterio de `vigencia`

El esquema admite un solo valor por artículo, pero la fuente marca la vigencia por numeral o parágrafo. Para esta muestra se aplicó el siguiente orden, mirando las marcas de la fuente:

1. Marca de artículo completo «INEXEQUIBLE» → `inexequible`.
2. Marca de artículo completo «CONDICIONALMENTE exequible» → `exequible_condicionado`.
3. Artículo, numeral, parágrafo o inciso «modificado» o «adicionado» por otra norma → `modificado`.
4. Sin marcas de ese tipo → `vigente`.

Las correcciones de texto por decreto (p. ej. «corregido por el Decreto 555 de 2017») no se consideraron modificaciones.

**Limitación:** un artículo `modificado` puede además tener numerales inexequibles o condicionalmente exequibles. Ese detalle no cabe en un solo campo y está en la tabla siguiente. El corpus de Wilder deberá resolverlo (p. ej. con vigencia por numeral).

| Artículo | `vigencia` | Marcas de la fuente que lo justifican |
|---|---|---|
| 124 | vigente | Sin marcas |
| 139 | vigente | Sin marcas |
| 140 | modificado | Corregido por el Decreto 555 de 2017; numerales 13 y 14 adicionados por el art. 3 de la Ley 2000 de 2019; inciso del parágrafo 2 modificado por la misma ley; numeral 7 con «apartes tachados INEXEQUIBLES»; numerales 6, 13 y 14 y partes del parágrafo 2 «CONDICIONALMENTE exequibles»; parágrafo «CONDICIONALMENTE exequible» |
| 163 | modificado | Numeral 7 adicionado por el art. 22 de la Ley 2455 de 2025; parágrafo 1 «CONDICIONALMENTE exequible» |
| 173 | vigente | Solo «corregido por el art. 12 del Decreto 555 de 2017» |
| 180 | modificado | Modificado por el art. 19 de la Ley 2450 de 2025 |
| 183 | modificado | Numerales 7 a 10 adicionados por el art. 43 de la Ley 2197 de 2022 (el 10 corregido por el Decreto 207 de 2022); numeral 6 «INEXEQUIBLE» (la fuente no trae su texto, por eso en `texto` queda «6.» vacío) |
| 198 | vigente | Sin marca de vigencia (solo una llamada de nota al pie `<1>` en el numeral 4, que se quitó) |
| 218 | vigente | Sin marcas |
| 222 | vigente | Sin marcas |

## Notas para quien use la muestra

- **`ubicacion` es un objeto aquí, pero una cadena en la API** (`docs/api_contract.md`). El motor debe armar la cadena, por ejemplo `"Libro Tercero. … > Título I. … > Capítulo II. … > Artículo 173"`.
- La fuente es una versión consolidada que ya incluye reformas recientes (Ley 2318 de 2023, Ley 2450 y Ley 2455 de 2025). Algunos artículos pueden diferir de la versión original de 2016.
- Los encabezados de `ubicacion` están en minúsculas con inicial mayúscula (no tal cual) para facilitar su lectura.
- El script de extracción no está versionado.
