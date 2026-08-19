# SDK 1 RC 1 — política de compatibilidad

El SDK **1** de Gravewright está en **Release Candidate 1**. El contrato público está
congelado: lo publicado en `gravewright-sdk-1.json`, `gravewright-sdk-1.d.ts` y la
documentación del SDK es lo que un paquete puede usar como base, y no se espera que
cambie de nuevo antes de que el SDK 1 sea estable.

El estado RC habla de estabilidad, no de versión. `sdkVersion` es `1`, los paquetes
declaran `"sdkVersion": "1"`, y la promoción de RC 1 a SDK 1 Estable no cambia ese
campo ni obliga a republicar ningún paquete.

## Qué es público

Solo lo que el contrato declara:

- los métodos, parámetros y tipos de retorno en `gravewright-sdk-1.json`;
- los tipos en `gravewright-sdk-1.d.ts`;
- las capabilities, eventos y códigos de error de esos mismos registros;
- la semántica de runtime que esos documentos describen — autoridad, visibilidad,
  concurrencia y durabilidad.

## Qué no es público

Todo lo demás, incluyendo:

- campos de respuesta que el DTO no declara;
- formas internas de servicios y repositorios;
- el DOM, el renderer y cualquier cosa en `window` fuera del punto de entrada
  documentado;
- rutas HTTP privadas y frames WebSocket crudos;
- el esquema de base de datos y la disposición del sistema de archivos;
- eventos internos y campos de DTO exclusivos de la implementación.

Un paquete que dependa de cualquiera de ellos **no tiene garantía de compatibilidad**,
y una release puede cambiarlos sin aviso. Esto no restringe lo que puedes hacer con el
código — Gravewright es abierto, y bifurcarlo o parchearlo es legítimo. Es una
declaración sobre lo que el SDK promete mantener funcionando.

Antes del RC 1 la lectura de Token dejaba pasar campos internos no declarados, entre
ellos `token_id` y un `controlled_by_user_ids` sin filtrar. Nunca formaron parte del
contrato; la lectura ahora devuelve el `TokenDTO` declarado, cuyo campo de identidad
es `id` y cuya lista `controllers` se filtra según la autoridad de quien llama para
inspeccionar el control. No se proporciona ningún alias para los internos eliminados.

## Ruptura frente a compatible

**Ruptura** — no permitido durante el RC sin revisión explícita:

- eliminar o renombrar un método, capability, evento o código de error;
- eliminar un campo público de DTO, o estrechar un tipo público;
- volver obligatorio un parámetro opcional, o eliminar un parámetro;
- cambiar lo que devuelve un método;
- cambiar la semántica de autoridad para quien ya era un llamador válido;
- mover un método a otro namespace.

**Compatible** — permitido durante el RC:

- correcciones de fallos, seguridad y rendimiento;
- reemplazar una implementación tras un contrato sin cambios;
- correcciones de documentación y nuevas pruebas;
- eliminar campos internos filtrados o no declarados, que nunca se prometieron;
- añadir un campo o parámetro opcional, tras revisión explícita de RC.

Métodos y capabilities nuevos son estructuralmente compatibles, pero el RC 1 es un
congelamiento de funcionalidades: requieren revisión explícita, y el clasificador de
diff los reporta como `POTENTIALLY_BREAKING` para que no entren en silencio.

## Cómo se aplica el congelamiento

`docs/sdk/_data/gravewright-sdk-1.rc1-snapshot.json` es una huella semántica del
contrato certificado — identidad de métodos, obligatoriedad y tipos de parámetros,
tipos de retorno, ids de capabilities, eventos y errores, y campos de DTO. El formato,
el orden y la prosa quedan fuera a propósito, así que la documentación puede
reescribirse libremente.

```
python scripts/sdk1_contract_snapshot.py --diff    # clasifica cada diferencia
python scripts/sdk1_contract_snapshot.py --check   # falla ante un cambio que rompe
python scripts/sdk1_contract_snapshot.py --write   # recongela tras un cambio aprobado
```

La suite de pruebas ejecuta `--check`, así que una ruptura accidental falla en CI en
lugar de llegar a un paquete publicado.

## Reportar una carencia

Si tu addon necesita algo que el SDK público no expresa:

1. confirma que ninguna composición pública existente lo resuelve;
2. repórtalo como carencia pública del SDK, indicando la operación bloqueada;
3. no publiques contra internos privados esperando que se mantengan.

El SDK **2** queda reservado exclusivamente para un cambio incompatible intencional de
este contrato público. No es el número de release del producto, y la versión del
producto avanza de forma independiente.
