# Kinds y lifecycle de packages

Use `ruleset` para modelos y reglas de juego; `addon` para extensiones;
`library` para código compartido; `content` para documentos importables;
`theme` para presentación; y `assets` para medios reutilizables. No declare una
capability para ocultar una operación que pertenece a otro kind.

El flujo recomendado es:

1. crear con `grave KIND new` o `--wizard`;
2. completar el manifest y los archivos provistos;
3. validar con `grave package validate RUTA --json`;
4. instalar y habilitar;
5. diagnosticar con Package Doctor y `grave doctor`;
6. publicar metadata y artefactos inmutables en el Marketplace.

El manifest usa `schemaVersion: 1`, `sdkVersion: "1"`, un kind válido,
`compatibility.verified: "1"`, capabilities conocidas, activation,
entrypoints y `provides`. La lista canónica está en [capabilities](capabilities.md)
y la estructura completa en [manifest](manifest.md).
