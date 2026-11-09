# Clasificador temático (Fase 4)

El clasificador orienta la búsqueda hacia el tema (y el libro o título) al que parece pertenecer la pregunta. Es **por palabras clave**, determinista y sin costo: no llama a ningún modelo.

> **Aviso:** todos los resultados de este documento son sobre el **corpus de muestra de 10 artículos** y 13 preguntas. Son una primera señal, **no una conclusión**, y se repetirán con el corpus completo (ver «Límites de esta evaluación»).

## Cómo funciona

1. **Normaliza** la pregunta: minúsculas, sin tildes ni signos.
2. **Detecta temas** con las palabras clave de [`engine/retrieval/temas.json`](../engine/retrieval/temas.json). Una palabra suma 1; una frase suma una unidad por palabra. Cada palabra clave cuenta una sola vez.
3. **Elige el tema** de mayor puntaje. `confianza` = puntaje del ganador ÷ puntaje de todos los temas que coincidieron (1.0 si solo coincidió uno; 0.5 si dos empatan; 0.33 si tres empatan). Si ninguna palabra coincide, el tema es `"general"` y la confianza 0.
4. **Empuja** (nunca filtra): suma `empuje × confianza` al score de los fragmentos del tema detectado, para cada tema con puntaje de al menos la mitad del mejor. Con un tema claro el empuje es completo (0.03); con dos temas parejos, cada uno recibe la mitad.
5. **Artículo por número:** si la pregunta dice «artículo 163» o «art. 163» y ese artículo existe en el índice, va **primero** (varios, en el orden en que se piden). Si no existe, se ignora.

`buscar(pregunta, k, estrategia, modo, clasificador=True)`: la firma no cambió salvo el parámetro opcional `clasificador`. Con `clasificador=False` el orden es solo por similitud semántica.

Detalles a tener en cuenta:

- El `score` devuelto **incluye el empuje** (es el que decide el orden). Cuando se pide un artículo por número, la lista puede no quedar ordenada por score.
- Si dos temas empatan, `tema` es el primero que aparece en `temas.json`; con `confianza` baja (0.33 o 0.5) ese nombre es poco informativo. Los temas con empate sí reciben empuje (repartido).
- La API devuelve `tema_detectado` (campo opcional; ver [api_contract.md](api_contract.md)).

## Cómo ampliarlo sin tocar Python

Todo está en `engine/retrieval/temas.json`:

- `tema`: debe ser **igual** al campo `tema` de los fragmentos del corpus; así se sabe qué artículos reciben el empuje.
- `libro` y `titulo`: a qué parte del Código corresponde el tema (se devuelven al clasificar).
- `palabras_clave`: con formas coloquiales (`trago`, `licor`, `rumba`, `perro`, `comparendo`...). Un `*` al final coincide con cualquier terminación (`multa*` → multa, multas, multar, multado). No hace falta poner tildes. Evita palabras que salen en casi todas las preguntas (policía, ley, código) y palabras que se solapan (`multa*` y `multar*` contarían dos veces).
- `configuracion.empuje` (0 lo desactiva) y `configuracion.umbral_relativo`.

Los cambios se ven al reiniciar el motor.

## Evaluación

Script: `eval/comparar_clasificador.py` (estrategia `fragmentos`). Preguntas: las 10 de `eval/preguntas_segmentacion.json` más 3 nuevas de `eval/preguntas_clasificador.json`:

| # | Tipo | Pregunta | Esperado |
|---|---|---|---|
| p11 | Artículo por número | ¿Qué dice el artículo 163? | 163 |
| p12 | Ambigua entre dos temas | ¿Cuánto me cobran si dejo a mi perro suelto en el parque? | 124 |
| p13 | Sin tema claro | ¿Qué pasa si no hago caso cuando un agente me da una indicación? | 222 |

Las 3 preguntas nuevas se escribieron **antes** de redactar las palabras clave, y las palabras clave no se ajustaron después de ver los resultados. El empuje por defecto (0.03) se fijó antes de evaluar.

### Resultados

| Preguntas | Configuración | Acierto@1 | Acierto@3 | MRR |
|---|---|---|---|---|
| 13 | sin clasificador | 0.69 | 0.85 | 0.808 |
| 13 | **con clasificador** | **0.77** | **0.92** | **0.865** |
| 10 originales | sin clasificador | 0.80 | 0.80 | 0.850 |
| 10 originales | con clasificador | 0.80 | 0.90 | 0.875 |

Posición del artículo esperado y tema detectado:

| # | Esperado | Sin | Con | Tema detectado | Confianza |
|---|---|---|---|---|---|
| p01 | 140 | 1 | 1 | Consumo de sustancias en espacio público | 0.50 |
| p02 | 124 | 1 | 1 | Animales potencialmente peligrosos | 1.00 |
| p03 | 180 | 1 | 1 | Tipos de multa | 0.50 |
| p04 | 139 | 1 | 1 | Espacio público | 1.00 |
| p05 | 163 | 1 | 1 | Ingreso a domicilio | 1.00 |
| p06 | 173 | 4 | **2** | Medidas correctivas | 0.50 |
| p07 | 183 | 1 | 1 | No pago de multas | 0.50 |
| p08 | 198 | 1 | 1 | Autoridades de policía | 1.00 |
| p09 | 218 | 4 | 4 | general | 0.00 |
| p10 | 222 | 1 | 1 | Proceso verbal inmediato | 0.80 |
| p11 | 163 | 2 | **1** | general | 0.00 |
| p12 | 124 | 1 | 1 | Tipos de multa | 0.33 |
| p13 | 222 | 2 | 2 | general | 0.00 |

### Qué cambió y por qué

- **p06 (173: «otras sanciones, además de la multa»), posición 4 → 2.** Detectó dos temas empatados: «Medidas correctivas» (por `sancion*`) y «Tipos de multa» (por `multa*`), y cada uno recibió medio empuje (+0.015). El artículo 173 pasó de 0.824 a 0.839 y superó a dos artículos sin empuje, pero **no al primero**: el 180 (Tipos de multa) recibió el mismo empuje, así que sigue delante. El clasificador ayudó, pero no resolvió esta pregunta, que justamente es ambigua.
- **p11 (artículo por número), posición 2 → 1.** No intervino el tema (no detectó ninguno); fue la regla del artículo: el 163 pasó al primer lugar aunque su score (0.785) quedó por debajo de otro fragmento (0.789). Es la mejora más clara, y es una regla determinista.
- **No empeoró ninguna pregunta.** Las otras 11 quedaron igual.

### Dónde no funcionó o no se puede juzgar

- **p09 (comparendo), p11 y p13: tema `general`.** p09 no dice «comparendo» («el documento que me entrega el policía»); p13 («indicación de un agente») no usa palabras del tema. Los sinónimos coloquiales sirven solo si están en la lista. Se evitó a propósito poner `policia` o `agente` como palabra clave porque salen en casi toda pregunta. p13 quedó en la posición 2 con o sin clasificador.
- **p12 (ambigua): tema `Tipos de multa` con confianza 0.33.** Hubo un empate de tres temas (multa, perro, parque) y el nombre que se reporta es solo el primero de la lista; no es informativo. Aun así el artículo esperado ya era el primero sin clasificador, así que no se puede decir que el clasificador ayudó ni estorbó.
- **p01, p03 y p07 detectan un tema razonable con confianza 0.5**, porque otros temas también coincidieron (en p01 empató con «Autoridades de policía» por «quién decide»). En las tres el artículo esperado ya iba primero sin clasificador.

### Sensibilidad al empuje (solo informativa)

| Empuje | Acierto@1 | Acierto@3 | MRR |
|---|---|---|---|
| 0.00 | 0.77 | 0.85 | 0.846 |
| 0.01 | 0.77 | 0.92 | 0.853 |
| 0.02 a 0.12 | 0.77 | 0.92 | 0.865 |

Con empuje 0 el resultado ya es 0.77 porque la regla del artículo por número sigue activa. A partir de 0.02 el resultado se estabiliza: en esta muestra ningún empuje hace que p06 llegue al primer lugar ni que otra pregunta empeore. No se eligió el 0.03 mirando esta tabla.

## Límites de esta evaluación

1. **Muestra mínima y casi circular.** El corpus tiene 10 artículos y cada uno es su propio tema, así que empujar un tema equivale a empujar un artículo. Los nombres de tema los asigné yo, y las palabras clave las escribí con las preguntas a la vista del autor (se congelaron antes de evaluar, pero esto no es una evaluación independiente). Con el corpus completo, un tema agrupará muchos artículos y el empuje será menos preciso.
2. **13 preguntas.** Una pregunta mueve 8 puntos de Acierto@1. Las diferencias (+0.08 Acierto@1, +0.08 Acierto@3, +0.057 MRR) son de una o dos preguntas y no son estadísticamente concluyentes. Casi toda la mejora de Acierto@1 es de p11, una regla determinista.
3. **Hay que rehacer `temas.json` con la taxonomía de temas del corpus de Wilder** (Fase 1) y volver a evaluar con el banco de 50+ preguntas, incluyendo preguntas fuera de dominio, para confirmar que el empuje no hace pasar preguntas ajenas como si fueran del Código. En las pruebas con el servidor, una pregunta fuera de dominio («impuesto predial») salió con tema `general` y sin empuje.

## Cómo reproducir

```bash
python engine/indexing/build_index.py --estrategia fragmentos
python eval/comparar_clasificador.py
python engine/retrieval/search.py "¿Qué dice el artículo 163?"                    # con clasificador
python engine/retrieval/search.py --sin-clasificador "¿Qué dice el artículo 163?" # sin clasificador
```
