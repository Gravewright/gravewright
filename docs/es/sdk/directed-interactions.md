# Interacciones dirigidas

Las interacciones dirigidas son decisiones multijugador propiedad del servidor. El requester declara destinatarios explícitos, prompt de texto, schema de respuesta acotado, deadline, visibilidad y provenance opcional. No admiten HTML arbitrario ni ejecutan acciones automáticamente.

Se admiten boolean, elección única, elección múltiple acotada, número acotado y string acotado. El servidor deriva al respondedor de la sesión autenticada. Las claves de idempotencia hacen seguros los reintentos. Las interacciones abiertas sobreviven a reload y se recuperan con `list({status: "open", recipient: "me"})`. El deadline es server-owned y desactivar el package cancela requests abiertos.

