# Seguridad y autoridad de SDK 1

La SDK aplica dos controles independientes: la capability declarada por el
package y la autoridad actual del usuario sobre el recurso. La primera nunca
eleva la segunda.

Las lecturas son proyecciones filtradas. Un recurso oculto no se distingue de
uno inexistente. Las mutaciones compartidas son autoritativas en el servidor;
cuando se declara `expectedVersion`, el cambio usa compare-and-swap atómico.
Errores públicos usan únicamente los códigos del
[índice estructural](contract-index.md#errores).

La SDK no expone filesystem, database internals, transport, DOM events crudos,
renderer objects, ACL internals ni un dispatcher universal. Los registros
locales devuelven un disposer y deben liberarse en `unload`.
