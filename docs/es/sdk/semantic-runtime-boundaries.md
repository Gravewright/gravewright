# Límites del runtime semántico

El SDK expone intención, no maquinaria. Cada dominio de abajo acepta una descripción
tipada de lo que debe ocurrir y deja que el core decida si puede, cuándo ocurre y
quién lo observa. Saber dónde caen esas líneas suele bastar para prever lo que una
API dará y lo que no.

## Drag y drop es un protocolo, no un evento del DOM

`sdk.ui.dragDrop` describe qué se llevaba y dónde aterrizó, como referencias de
contenido y una posición en el mundo. No es `DragEvent`, `DataTransfer`, un selector
ni ningún otro handle del DOM. El core vuelve a resolver la referencia y el destino
justo antes de ejecutar la acción registrada vinculada a ese destino, de modo que un
gesto nunca puede afirmar un resultado que el usuario no habría podido realizar
directamente.

## El audio es un dominio del core, no un elemento

El core es dueño del estado de reproducción, la audiencia, el ciclo de vida y la
proyección de reconexión. `sdk.audio` nunca devuelve `HTMLAudioElement`, un nodo de
WebAudio, una URL de medios ni autoridad sobre el volumen personal de quien escucha.

## La navegación cambia un punto de vista, nada más

`sdk.navigation.scene` cambia qué Scene está mirando un usuario. No mueve, crea ni
modifica un Token, y no es una presentación.

## Input separa el significado del vínculo

Un paquete declara qué significa un comando; el usuario es dueño de qué tecla lo
invoca. El core conserva los listeners crudos de teclado y puntero, los atajos
protegidos, la supresión durante la escritura, el umbral de pulsación larga, la
cancelación de puntero y la resolución de conflictos multipuntero.

## Dominios vecinos deliberadamente distintos

| Esto | no es | porque |
|---|---|---|
| Presentation | Navigation | una muestra contenido, la otra cambia el contexto de Scene |
| Directed Interaction | Presentation | una pide una decisión y espera la respuesta |
| Durable Workflow | Semantic Timeline | uno espera decisiones, la otra corre por un reloj |
| Token Transfer | Scene Navigation | uno mueve un Token, la otra mueve una vista |
| Scene Zone | World Object | una es una región, el otro es una cosa direccionable |
| Sound | Playback | uno es contenido reutilizable, el otro una instancia en ejecución |

Los Scene World Objects siguen siendo recursos semánticos con datos e interacciones.
No son objetos del renderer, y ninguna API devuelve un handle de dibujo para ellos.
