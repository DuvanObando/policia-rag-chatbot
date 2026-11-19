# Clasificador temático: con y sin la propuesta de temas de Santiago Castro

Generado por `eval/comparar_temas.py`. Solo recuperación (sin LLM), modo semántico, fragmentos, k=10. Posición = lugar del primer artículo esperado (0 = no aparece en los 10).

- **A**: sin clasificador. **B**: clasificador anterior (10 temas del corpus de muestra; con el corpus real todos los artículos tienen el mismo tema, así que solo actúa la regla del artículo por número). **C**: propuesta de Castro (32 temas por rangos de artículos) con el empuje de temas.json (0.02 desde el 19/11).

| Grupo | n | A Acierto@1 | A Acierto@3 | A MRR | B Acierto@1 | B Acierto@3 | B MRR | C Acierto@1 | C Acierto@3 | C MRR |
|---|---|---|---|---|---|---|---|---|---|---|
| todas | 68 | 0.69 | 0.87 | 0.791 | 0.71 | 0.88 | 0.805 | 0.79 | 0.91 | 0.863 |
| evaluaciones anteriores | 19 | 0.53 | 0.68 | 0.633 | 0.58 | 0.74 | 0.686 | 0.63 | 0.79 | 0.725 |
| indirectas (19/11) | 9 | 0.44 | 0.89 | 0.648 | 0.44 | 0.89 | 0.648 | 0.89 | 1.00 | 0.944 |
| banco de Wilder | 40 | 0.82 | 0.95 | 0.897 | 0.82 | 0.95 | 0.897 | 0.85 | 0.95 | 0.909 |

Sensibilidad de C al empuje (todas las preguntas):

| empuje | Acierto@1 | Acierto@3 | MRR |
|---|---|---|---|
| 0.01 | 0.76 | 0.90 | 0.843 |
| 0.02 | 0.79 | 0.91 | 0.863 |
| 0.03 | 0.75 | 0.91 | 0.833 |
| 0.05 | 0.69 | 0.87 | 0.782 |

## Preguntas que cambian entre B y C

| id | pregunta | esperado | B | C | tema detectado (C) | primero en C |
|---|---|---|---|---|---|---|
| segmentacion-p06 | ¿Qué otras sanciones, además de la multa, me puede imponer la policía? | art-173 | 4 | 3 | Medidas correctivas | art-180 |
| segmentacion-p10 | ¿Cómo es el trámite cuando el policía resuelve el problema ahí mismo e | art-222 | 3 | 2 | Espacio público | art-223 |
| coloquiales-p17 | ¿Me ponen boleta si me cogen tomando guaro en el parque? | art-140 | 2 | 1 | Espacio público | art-140 |
| i01 | ¿Me pueden multar por tomar licor en el parque? | art-140 | 2 | 1 | Espacio público | art-140 |
| i03 | ¿Puedo vender comida en la calle sin permiso? | art-140, art-92 | 2 | 1 | Actividad económica | art-92 |
| i04 | Un policía me pidió la cédula, ¿estoy obligado a mostrarla? | art-35 | 0 | 1 | Tranquilidad y relaciones respetuosas | art-35 |
| i07 | ¿Me pueden llevar a la estación si estoy borracho en la calle? | art-155 | 3 | 1 | Traslado, registro e incautación | art-155 |
| pregunta_02 | ¿Puedo llevar un cuchillo en la calle si lo uso como herramienta de mi | art-27 | 2 | 1 | Seguridad e integridad de las personas | art-27 |
| pregunta_33 | ¿Puedo hacer el programa comunitario de convivencia en un municipio di | art-223A | 7 | 8 | Medidas correctivas | art-175 |
