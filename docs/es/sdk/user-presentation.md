# Presentación de usuario

La presentación de usuario es la pequeña proyección visual server-authoritative que los packages pueden usar para representar coherentemente a un participante. SDK 1 expone solamente un color canónico en minúsculas con formato `#rrggbb` y el ID ya visible del participante. No expone settings del core, preferencias arbitrarias, perfil, email, locale, permisos ni metadatos de autenticación.

El package debe declarar `users.presentation.read`. La capability y la autoridad del usuario son verificaciones distintas: `list()` contiene solamente miembros de la campaña activa y `get(userId)` funciona solo para un miembro visible en esa campaña. Una campaña inaccesible se rechaza; un objetivo desconocido o de otra campaña es indistinguible de un recurso ausente.

```js
const participantes = await sdk.users.presentation.list();
const presentacion = await sdk.users.presentation.get(userId);

const dispose = sdk.events.on("user.presentation.changed", async event => {
  const actual = await sdk.users.presentation.get(event.resourceId);
  actualizarColor(actual.userId, actual.color);
});
```

El evento sigue el lifecycle normal de eventos de la SDK y solo se entrega por las rooms de campaña. Su shape limitado identifica al participante mediante `resourceId`; los consumidores vuelven a leer la proyección autoritativa. Elimine la suscripción durante el teardown del package.

Por ejemplo, un addon de dados 3D puede tomar el user ID del autor desde un DTO de roll autorizado, llamar a `presentation.get(authorUserId)` y renderizar ese color. Esto no requiere acceso a settings del core ni amplía la visibilidad del roll.
