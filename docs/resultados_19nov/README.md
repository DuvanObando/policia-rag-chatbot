# Comparaciones repetidas el 19/11 (glosario y temas de Santiago Castro)

Salidas completas de los scripts de `eval/`, corridos el 19/11/2026 con el corpus real (Ley 1801: 249 artículos, 471 fragmentos), el **glosario de 49 términos** de Santiago Castro (`engine/glossary/sinonimos.json`) y los **32 temas** de su propuesta aplicados en el clasificador (`TEMAS_PROPUESTA=1`, empuje semántico 0,02). Solo recuperación: no llaman al LLM.

| Script | Salida | Resultado principal |
|---|---|---|
| `eval/comparar_expansion.py` | [comparar_expansion.txt](comparar_expansion.txt) | Modo híbrido, 19 preguntas: MRR 0,613 sin expansión → **0,625** con el glosario de Castro. En las 3 muy coloquiales 0,317 → **0,556**; en las 16 originales baja de 0,669 a 0,637 (p12, «perro suelto en el parque», pasa del 1 al 2). Mismo patrón que con el glosario semilla el 12/11. La expansión solo actúa en `lexico` e `hibrido`: **en el modo de la demo (`semantico`) no cambia nada** |
| `eval/comparar_modos.py` | [comparar_modos.txt](comparar_modos.txt) | 16 preguntas, con clasificador: **semántico 0,721**, híbrido 0,669, léxico 0,635 (MRR). Se mantiene `semantico` por defecto |
| `eval/comparar_segmentacion.py` | [comparar_segmentacion.txt](comparar_segmentacion.txt) | **fragmentos 0,708** frente a artículo 0,403 (MRR). Igual que el 12/11 (no depende del glosario ni de los temas) |
| `eval/comparar_clasificador.py` | [comparar_clasificador.txt](comparar_clasificador.txt) | 13 preguntas: MRR 0,622 sin clasificador → **0,718** con los temas de Castro (el 12/11, con el clasificador anterior: 0,699, y toda la mejora venía del «artículo 163») |
| `eval/comparar_temas.py` | [../resultados_temas.md](../resultados_temas.md) | 68 preguntas: MRR 0,791 sin clasificador, 0,805 con el anterior, **0,863** con los temas de Castro |

Evaluación formal con el LLM (Precisión@k, Recall@k, MRR, fuera de dominio y cita): [`eval/reporte.md`](../../eval/reporte.md).
