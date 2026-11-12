# Diagramas del proyecto

Generados con [Archify](https://github.com/tt-a1i/archify) a partir del código del repo (commit `1259b13`), con cada nodo ligado a su archivo y líneas. Los HTML son interactivos y autónomos (ábrelos en el navegador); los PNG salen del menú Exportar del propio visor.

| Diagrama | HTML | PNG | Fuente editable |
|---|---|---|---|
| Arquitectura en ejecución (cliente → API → búsqueda → LLM → citas) | [html](arquitectura-ejecucion.html) | [png](arquitectura-ejecucion.png) | [json](fuentes/arquitectura-ejecucion.json) |
| Estructura del monorepo (motor, corpus, análisis, integración) | [html](estructura-monorepo.html) | [png](estructura-monorepo.png) | [json](fuentes/estructura-monorepo.json) |
| Flujo de una consulta a `/query`, con tiempos medidos el 12/11 | [html](flujo-consulta.html) | [png](flujo-consulta.png) | [json](fuentes/flujo-consulta.json) |

## Regenerarlos

Los JSON de `fuentes/` son la fuente. Con Archify instalado (`npx -y skills@latest add https://archify.si --skill archify --agent claude-code --global --copy --yes`), desde la **raíz del repo**:

```bash
node ~/.claude/skills/archify/bin/archify.mjs finalize architecture docs/diagramas/fuentes/arquitectura-ejecucion.json docs/diagramas/arquitectura-ejecucion.html --repo-root . --quality showcase
```

(`tree` para la estructura y `sequence` para el flujo.) Las referencias a código se verifican contra el commit fijado en `meta.repository.revision`: si cambia el código, actualiza ese commit y las líneas citadas. Los tiempos del flujo son de una prueba del 12/11 en el PC de desarrollo; no son un compromiso de rendimiento.
