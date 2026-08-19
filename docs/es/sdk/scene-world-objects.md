# Scene world objects

Los scene world objects son recursos persistentes de campaign cuyo tipo semántico procede de un package activo; authority, persistencia, audience, rendering, hit-test, selección y mutations pertenecen al core. No son acceso al renderer, Tokens ni Zones.

`sdk.scene.objectTypes.register()` registra definiciones JSON-safe con namespace. `sdk.scene.objects.list/get/create/update/delete` administra instancias versionadas en coordenadas del mundo y usa CAS con `expectedVersion`. El core admite `point`, `rect`, `circle`, `polygon` y `polyline`, deriva bounds/hit-test y nunca proyecta objetos ocultos.

Las interacciones son intents semánticos declarados, no callbacks. Desactivar el provider conserva los datos como placeholder; reactivarlo restaura la proyección. No se ejecutan migraciones arbitrarias en el cliente.
