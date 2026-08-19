# Comandos de entrada

El Registro de Entrada es el dueño de la entrada física. El teclado, el puntero y los gestos los lee el runtime de entrada del núcleo y nadie más: un paquete nunca instala un listener en el documento anfitrión, nunca recibe un `KeyboardEvent` y nunca ve un nodo del DOM que no haya creado. Lo que un paquete registra es un *comando semántico*: una intención con nombre, su etiqueta, los contextos a los que pertenece y los atajos con los que empieza. Lo que controla la persona usuaria es qué tecla lo invoca.

Registrar e invocar requieren `input.commands`.

## Dos tipos de comando

Un comando puede atenderse localmente, ejecutarse en el servidor, o ambas cosas.

Un **comando semántico local** se atiende en el navegador. Úsalo cuando la intención es sobre la interfaz — abrir un panel, enfocar una aplicación, cambiar de vista. Pasa un handler como segundo argumento de `register`:

```js
await sdk.input.commands.register({
  id: "open-console",
  label: "Abrir consola",
  contexts: ["global", "text-input-excluded"],
  defaultBindings: ["Alt+U"]
}, async (invocation) => {
  await sdk.ui.applications.render("console", host);
});
```

El handler recibe un `InputCommandInvocationDTO` — `commandId`, `packageId`, `source`, `binding`, `context` — y nada más. Son metadatos ya resueltos, no un evento.

Un **comando de acción registrada** lo ejecuta el servidor. Úsalo cuando la intención cambia estado autoritativo. Nombra una acción registrada y pre-vincula la entrada que esa acción necesita:

```js
const actor = await sdk.actors.get(actorId);

await sdk.input.commands.register({
  id: "engage-scanner",
  label: "Activar escáner",
  contexts: ["global", "text-input-excluded"],
  defaultBindings: ["Alt+S"],
  registeredAction: "my-package:scanner.engage@1",
  actionInput: { actorId: actor.id }
});
```

Ambos se pueden combinar: entrega un handler *y* un `registeredAction`, y el handler corre localmente mientras el servidor ejecuta la acción.

## Los metadatos de invocación no son entrada de la acción

Los metadatos que describen *cómo* se invocó un comando — qué atajo, qué contexto — nunca se pasan a la acción registrada. Una acción recibe solo `actionInput`, exactamente como quedó registrado.

Esto importa porque `actionInput` es dato de definición del paquete, no carga útil de runtime. Se valida y se canoniza al registrar el comando, lo guarda el runtime del núcleo y se usa literalmente en cada invocación. Quien llama no puede sustituirlo: una invocación que envía entrada de acción para un comando que ya pre-vinculó la suya se rechaza, no se combina. Los comandos sin `actionInput` siguen aceptando entrada de quien llama, validada por el esquema de la propia acción.

La entrada pre-vinculada es JSON simple y acotado. No hay lenguaje de expresiones, ni interpolación, ni sintaxis de rutas — si un comando necesita apuntar a un recurso cuyo ID solo existe en runtime, registra el comando una vez que ese ID exista. Registrar de nuevo el mismo id de comando reemplaza la definición, incluida su entrada pre-vinculada, así que un paquete puede volver a registrar cuando cambie el recurso al que apunta.

## Autoridad

Un comando no concede autoridad alguna. Un handler local corre con los privilegios del código de paquete normal: cada llamada SDK que hace deriva su principal de la sesión autenticada y se comprueba contra capacidades y autoridad de campaña exactamente como si la persona hubiera pulsado un botón. Un comando de acción registrada se comprueba igual — quien llama debe tener permiso para la acción, diga lo que diga la definición del comando.

Nada en una definición de comando puede falsificar usuario, campaña, rol de dirección, audiencia ni contexto de permisos. Los comandos pertenecen a la campaña en la que se registraron y son invisibles desde cualquier otra.

## Atajos

`defaultBindings` es aquello con lo que empieza el comando. Un atajo propio de la persona usuaria, fijado con `sdk.input.bindings.set`, reemplaza al predeterminado en vez de sumarse a él, y surte efecto de inmediato — sin recargar, y la tecla anterior deja de funcionar en ese mismo momento.

```js
const bound = await sdk.input.bindings.set("engage-scanner", "Alt+K");
```

Un atajo es una tecla con prefijo de modificadores, como `Alt+K`, `Ctrl+Shift+P` o `F7`. El núcleo impone dos reglas:

- **Los atajos reservados se rechazan.** Combinaciones que el navegador o la aplicación ya usan — `Ctrl+L`, `Ctrl+T`, `Ctrl+W`, `Ctrl+N`, `Ctrl+R`, `Ctrl+Shift+T`, `Alt+F4`, `F5`, `F12` — no se pueden reclamar.
- **Los conflictos se rechazan.** Un atajo que ya tiene otro comando, de cualquier paquete, se rechaza en vez de quedar silenciosamente tapado.

Los atajos pertenecen a la persona usuaria, no a la campaña ni al paquete: la elección de una es invisible para las demás. Un cambio con éxito emite `input.binding.changed` a esa persona, para que otras superficies vuelvan a leer. Un cambio rechazado no emite nada.

Lee el conjunto actual con `sdk.input.bindings.get()` y lista los comandos disponibles al paquete con `sdk.input.commands.list()`.

## Contextos y supresión al escribir

`contexts` declara dónde vale un comando: `global`, `scene`, `actor-sheet`, `package-application`, `combat`.

Dos contextos gobiernan la escritura. Con el foco en un campo de texto, un textarea, un select o una región contenteditable, un comando solo corre si declara `text-input`. Declarar `text-input-excluded` rechaza la invocación al escribir incluso entonces, y siempre gana cuando ambos están presentes. Un comando que no declara ninguno queda suprimido al escribir.

La supresión es del núcleo. Un paquete nunca debe filtrar teclas por su cuenta — no tiene acceso a los eventos necesarios, y cualquier filtro del lado del paquete discreparía de las reglas del núcleo que la persona usuaria ve en todo lo demás.

## Exactamente una vez

Una pulsación física invoca como mucho un comando. Cuando varios comandos comparten un atajo, el primero que coincide se queda la pulsación y el resto se omite; una tecla mantenida en repetición no vuelve a invocar. Un comando suprimido, sin atajo o desechado no produce invocación alguna, en vez de producir una que falla.

## Gestos

`sdk.input.gestures.register` vincula un gesto de puntero — `tap`, `double-tap`, `long-press`, `drag`, `pan`, `cancel` — a un id de comando, y acepta el mismo handler opcional. La invocación lleva `source: "gesture"` y el nombre del gesto. Como con las teclas, el núcleo es dueño de todo listener de puntero.

## Ciclo de vida

El registro devuelve un disposer. Llamarlo retira el comando de inmediato: el atajo deja de resolver, el handler se descarta y no queda ningún listener atrás — el núcleo es dueño de los únicos listeners que existen, así que un paquete no puede filtrar uno.

Los disposers también se ejecutan al descargar el paquete. Un paquete desactivado no tiene comandos registrados, así que sus atajos no resuelven nada; reactivarlo los vuelve a registrar por el ciclo de vida normal.
