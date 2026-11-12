# Notas del glosario de sinónimos coloquiales (borrador 1)

Responsable: Santiago Castro (Fase 2). Archivo del glosario: `engine/glossary/sinonimos.json`. Estas notas explican cómo se armó, qué se dejó fuera y por qué, y cómo revisarlo.

## Qué contiene el borrador

1. 49 términos legales y 339 coloquiales, en el formato que ya usa el motor (`{"termino_legal": ["coloquial1", ...]}`), sin cambiar el contrato.
2. Los términos legales son expresiones tal como aparecen en el texto de la Ley 1801 (se verificó que las 49 claves existen en el corpus). Dos se corrigieron al revisar: el Código dice «habitantes de y en calle» y «necesidades fisiológicas».
3. Los coloquiales son propuestas de uso común en Colombia, pendientes de revisión humana. Lo ideal es que Santiago agregue y quite según cómo habla la gente de verdad.
4. Cubre: sanciones y trámite (multa, comparendo, decomiso, descuento, apelación, mora), actuación policial (requisa, traslado, allanamiento, uso de la fuerza), alcohol y drogas, espacio público y vendedores ambulantes, ruido, basura, mascotas y perros peligrosos, armas y pólvora, menores, transporte masivo, protestas, eventos, negocios, domicilio, invasiones, habitantes de calle y prostitución.

## Cómo funciona el mecanismo (para entender las decisiones)

1. Si la pregunta contiene un coloquial, se agregan a la consulta de BM25 las palabras del término legal. Solo afecta a la búsqueda léxica: la búsqueda semántica y el modelo de lenguaje ven la pregunta original. Por eso un coloquial ambiguo mete ruido en BM25, pero por sí solo no produce una respuesta equivocada.
2. Los coloquiales se comparan por palabras completas, sin tildes ni mayúsculas. Hay que listar plurales, género y conjugaciones («requisa», «requisan», «me requisaron»).
3. No existe una lista de exclusiones. Si una palabra activa el término equivocado, la única salida es quitarla o convertirla en una frase.
4. Los términos se evalúan por separado: una pregunta puede activar varios términos legales a la vez.

## Palabras ambiguas que NO se incluyeron sueltas

| Palabra | Otros significados | Decisión |
|---|---|---|
| perico | café con leche, ave, droga | Fuera (estaba en la semilla) |
| vicio | genérico | Fuera (estaba en la semilla) |
| boleta | entrada a un concierto, persona que queda en ridículo («hacer boleta») | Solo en frases: «me ponen boleta», «me pusieron una boleta» |
| rumba | fiesta (ruido), reunión (aglomeraciones), consumo de licor | Fuera |
| calle | espacio público, habitantes de calle, «me sacaron a la calle» (desalojo) | Solo la frase «en la calle» |
| plaza | plaza de mercado, plaza de toros (espectáculos taurinos) | Fuera |
| estación | estación de policía o estación de TransMilenio | Solo la frase «estación de policía» |
| vaca | animal, «hacer una vaca» (colecta de plata) | Fuera |
| mula | animal, persona que transporta droga | Fuera |
| reclamar | apelar, reclamar un bien | Fuera |
| casa | domicilio u otras casas | Solo en frases con «mi casa» |
| me pegaron, me golpearon | riña entre personas o abuso policial | Fuera |
| pelado, pelao | niño, sin plata | Fuera |
| partido | partido deportivo, partido político | Fuera |
| bomba | pólvora, globo, bomba de agua | Fuera |
| paro | protesta, paro cardíaco | Fuera |
| fierro | arma o metal | Fuera |

## Qué se tomó de las dos listas de expresiones bogotanas

1. Las listas traen unas 60 expresiones de uso general (chévere, tusa, sapo, gomelo, piloso, ñapa...). Casi todas no tienen relación con la Ley 1801 y no se incluyeron: el glosario no es un diccionario de bogotanismos, es un puente entre cómo pregunta la gente y cómo escribe la ley.
2. Se agregaron las que sí aplican: «polita», «politas» (cerveza), «chicha», «chichas» (bebida fermentada de maíz) en «bebidas alcohólicas», y «borrachera», «borracheras» en «estado de embriaguez».
3. Las listas confirman varias ambigüedades que ya se habían detectado: «boleta» tiene un tercer significado (persona que queda en ridículo, «hacer boleta»), «perico» es tinto con leche, «vaca» es reunir plata entre amigos, y «amarga» es cerveza pero también un adjetivo.
4. Quedaron fuera por ambiguas: «amarga» (cerveza o adjetivo), «jartera» (aburrimiento o borrachera), «foforro» y «jolgorio» (fiesta, igual que «rumba»).
5. Pendiente de decidir: «chino» y «china» (niño o niña en Bogotá) para «niños, niñas y adolescentes». Riesgo: también se usa para la persona de nacionalidad china y «china» para la naranja. Decide Santiago.

## Palabras incluidas pero con riesgo (revisar)

1. «pelea» y «peleas»: activan «confrontaciones violentas» (riñas entre personas). Pero «pelea de perros» es otra cosa en el Código (peleas caninas, art. 125). Se agregó una entrada propia para «pelea de perros», pero la palabra «pelea» sola también se activa y mete ruido. Es la limitación sin exclusiones.
2. «me quitan» y «me quitaron» (decomiso): también se dirían de «me quitaron el trabajo». En preguntas de policía suele ser decomiso.
3. «bronca», «mota» (también pelusa o mancha), «curso» (también un curso cualquiera), «tienda», «bar», «deuda», «descuento», «rebaja».
4. Conjugaciones que faltan: la semilla tenía «resolver ahí mismo», pero la pregunta «el policía resuelve el problema ahí mismo» no la activa. Conviene listar más formas.

## Cómo revisar un término

1. Prueba liviana, sin índices ni claves de API: `python engine/analysis/probar_glosario.py` (usa las preguntas de `eval/`) o con tus propias frases: `python engine/analysis/probar_glosario.py "me cogieron con un porro"`.
2. Para cada palabra dudosa, escribir 3 preguntas reales con ese sentido y 1 con el otro sentido, y ver qué activa.
3. Evaluación completa: `python eval/comparar_expansion.py`. Necesita los índices de fragmentos ya construidos (con BM25), así que se coordina con Duvan. Ojo: las 3 preguntas coloquiales de `eval/` fueron escritas junto con la semilla (usan «boleta», «guaro», «pitbull»), así que la evaluación es parcialmente circular. Conviene agregar preguntas nuevas con coloquiales distintos.
4. Si una palabra empeora el resultado, se quita o se convierte en frase.

## Si el significado de una palabra cambia con el tiempo

1. Se anota aquí con fecha y motivo (por ejemplo: «2026-11-12, perico fuera por ambigua»).
2. Se cambia el glosario por PR con revisión, así queda historial y se puede deshacer.
3. Si se quiere guardar metadatos por palabra (fecha, fuente, ambigüedad), mejor hacerlo en este archivo de notas y no dentro de `sinonimos.json`, porque cambiar el formato del JSON cambia el contrato con el motor y hay que hablarlo con Duvan.

## Idea: agregar y quitar palabras solo desde una cuenta de administrador

1. Hoy no existe nada de administración ni autenticación en el repositorio, y la guía no lo pide.
2. Haría falta tocar tres partes: el archivo del glosario (esta parte es de Santiago Castro), un endpoint protegido en el motor o el backend que lea, agregue y quite palabras y llame a `recargar()` (el motor lee el glosario una sola vez y lo guarda en memoria; hoy nadie llama a `recargar()`, así que un cambio exige reiniciar), y una pantalla de administración con inicio de sesión en `frontend/` y `backend/`.
3. Esas dos últimas partes no son del rol de lingüística. Si el equipo la quiere, se decide con Duvan (motor) y con quien lleve integración, y suma riesgo: autenticación, registro de quién cambió qué y validación de cada cambio, porque una palabra mal puesta altera las búsquedas de todos.
4. Propuesta por ahora: mantener el glosario como archivo versionado que se cambia por PR, y mencionar el panel de administración como mejora futura en el informe técnico.
