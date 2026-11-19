# Reporte de evaluación formal (Fase 6)

Generado por `eval/run_eval.py` el 19/11/2026 08:49 (25.2 min).

- **Banco:** corpus/preguntas_ley_1801.json (banco de Wilder, adaptado: eval/banco_preguntas.json está vacío) + eval/preguntas_indirectas.json. Preguntas: 60 (0 sin respuesta del LLM).
- **Configuración:** modo de búsqueda `semantico`, LLM en orden ['groq', 'gemini'], temas de Castro activos (TEMAS_PROPUESTA).
- **k = 3** artículos distintos entregados al LLM (small-to-big).

## Métricas

| Métrica | Valor | n |
|---|---|---|
| Precisión@3 | 0.333 | 49 |
| Recall@3 | 0.942 | 49 |
| MRR | 0.908 | 49 |
| Exactitud de fuera de dominio | 0.933 | 60 |
| Fuera de dominio: precisión (de las marcadas, cuántas lo eran) | 0.769 | 13 |
| Fuera de dominio: recall (de las trampas, cuántas detectó) | 0.909 | 11 |
| Corrección de la cita (al menos un artículo citado es esperado) | 0.935 | 46 |
| Cita exacta (todos los citados son esperados) | 0.783 | 46 |
| Tiempo por pregunta (mediana / máximo) | 1.4 s / 10.2 s | 60 |

Modelos que respondieron: openai/gpt-oss-120b (2), openai/gpt-oss-20b (46), gemini-3.5-flash-lite (12)

## Por tipo de pregunta

| Tipo | n | MRR | Exactitud fuera de dominio | Cita correcta |
|---|---|---|---|---|
| fuera_de_dominio | 10 | nan | 0.900 | nan |
| indirecta | 9 | 0.944 | 0.778 | 1.000 |
| norma_modificatoria | 40 | 0.900 | 0.975 | 0.923 |
| transito | 1 | nan | 1.000 | nan |

## Análisis de errores

### Fuera de dominio equivocado: era trampa y el motor respondió (1)

- **pregunta_50** «¿Quién tiene prioridad en una intersección sin semáforo?» — esperados —; recuperados ['art-141', 'art-140', 'art-146']; citados ['art-141']; fuera_de_dominio False

### Fuera de dominio equivocado: estaba en la ley y el motor dijo que no (3)

- **pregunta_19** «¿La Policía puede llevar a una persona a una estación para hacer un traslado por protección?» — esperados ['art-155']; recuperados ['art-155', 'art-157', 'art-159']; citados []; fuera_de_dominio True
- **i01** «¿Me pueden multar por tomar licor en el parque?» — esperados ['art-140']; recuperados ['art-140', 'art-103', 'art-180']; citados []; fuera_de_dominio True
- **i03** «¿Puedo vender comida en la calle sin permiso?» — esperados ['art-140', 'art-92']; recuperados ['art-92', 'art-110', 'art-93']; citados []; fuera_de_dominio True

### El artículo esperado no llegó al LLM (recuperación) (2)

- **pregunta_31** «¿Si me ponen una multa de convivencia, puedo cambiar algunas multas pequeñas por participar en una actividad comunitaria?» — esperados ['art-223A']; recuperados ['art-180', 'art-212', 'art-175']; citados ['art-180', 'art-175']; fuera_de_dominio False
- **pregunta_33** «¿Puedo hacer el programa comunitario de convivencia en un municipio diferente al lugar donde ocurrió el problema?» — esperados ['art-223A']; recuperados ['art-175', 'art-180', 'art-111']; citados ['art-175', 'art-111']; fuera_de_dominio False

### Llegó el artículo pero la cita no es la esperada (1)

- **pregunta_10** «¿Un alcalde puede definir zonas específicas del espacio público donde se restringe el consumo de sustancias psicoactivas?» — esperados ['art-140']; recuperados ['art-140', 'art-34', 'art-49']; citados ['art-34']; fuera_de_dominio False

### Sin respuesta del LLM (límites del plan gratuito) (0)

- Ninguna.

## Análisis (escrito a mano el 19/11; si se vuelve a correr `run_eval.py`, esta sección se reemplaza)

**Lectura de las métricas.**

- **Recuperación muy buena:** Recall@3 0,942 y MRR 0,908. En 46 de 49 preguntas el artículo esperado llegó al LLM, casi siempre en el primer puesto.
- **Precisión@3 = 0,333 es el techo, no un mal resultado:** casi todas las preguntas tienen un solo artículo esperado y el motor siempre entrega 3, así que la precisión máxima posible es 1/3.
- **Fuera de dominio:** exactitud 0,933 (56 de 60). Detectó 10 de 11 trampas.
- **Cita:** el artículo citado es el esperado en el 93,5 % de las respuestas. En el 78,3 %, todos los citados son esperados; el resto agrega un artículo vecino, como el 150 junto al 35.

**Los errores se concentran en los modelos de respaldo.** Groq agotó el límite gratuito de `gpt-oss-120b` después de un día de pruebas, así que respondieron:

| Modelo | Preguntas | Correctas |
|---|---|---|
| `gpt-oss-120b` | 2 | 2 |
| `gpt-oss-20b` | 46 | 40 |
| `gemini-3.5-flash-lite` | 12 | 11 |

Las 3 abstenciones equivocadas («No encontré…» con el artículo correcto en el contexto) son de esos modelos: licor en el parque (20b), vender comida en la calle (Gemini) y traslado por protección (20b). Las dos primeras las respondió bien el `gpt-oss-120b` en la prueba de las preguntas indirectas del mismo día. Es la misma debilidad del 20b documentada el 12/11 en `docs/demo_entrega.md`. **Con el 120b disponible, el resultado esperado es mejor que el medido aquí.**

**Errores por tipo:**

1. **Trampa respondida (1).** pregunta_50, «¿Quién tiene prioridad en una intersección sin semáforo?» (tránsito). El 20b respondió con el art. 141 de la Ley 1801 (movilidad) y afirmó una regla de prioridad que ese artículo no establece. Es una analogía que la regla 4b del prompt debía evitar; el 20b la cumple peor.
2. **Recuperación (2).** pregunta_31 y pregunta_33 piden el art. 223A (programa comunitario en lugar de la multa, agregado por la Ley 2197 de 2022). La búsqueda trae los arts. 175 y 180, que hablan del mismo tema con más texto. Mejoraría con el empuje por tema si el art. 223A estuviera en el mismo tema que el 175 (hoy está en «Comparendo» y el 175 en «Medidas correctivas»).
3. **Cita distinta (1).** pregunta_10, sobre las zonas donde el alcalde restringe el consumo: citó el art. 34 (perímetros de restricción cerca de colegios), que también trata de perímetros, en vez del art. 140. Es defendible, pero no es la referencia de Wilder.

**Límites de esta evaluación:**

- **Banco:** es el anterior de Wilder adaptado, porque `eval/banco_preguntas.json` está vacío. 40 de sus preguntas son sobre artículos modificados por otras normas, y las 10 trampas son todas de tránsito: con la Ley 769 cargada dejarían de ser trampas.
- **Fidelidad:** no se mide automáticamente (requiere revisión humana de cada respuesta); el detalle por pregunta está en `eval/resultados_eval.json`.
- **Muestra pequeña:** con 60 preguntas, una sola pregunta mueve casi 2 puntos.
