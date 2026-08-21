# Marketplace, canales y provenance

Marketplace v2 es el registro remoto para descubrir e instalar el Core y
packages. Las entradas publican canales `stable`, `testing` o `dev`, artefactos
inmutables, checksum y provenance `core`, `community` o `partner`. El lector
acepta v1 para migración; el authoring nuevo debe producir v2.

Un canal solo está disponible si el registro remoto lo publica para esa
entrada. La interfaz muestra únicamente esos canales. Elegir un canal no crea
una release y no provoca downgrade o instalación automática.

La resolución nunca sube silenciosamente a un canal más riesgoso. `stable`
recibe stable; `testing` puede resolver testing o stable; `dev` puede resolver
dev, testing o stable según lo publicado. Un canal sin candidato compatible
informa indisponibilidad.

La actualización local relee metadatos instalados. La actualización remota
descarga el artefacto del registro, verifica integridad y compatibilidad y
preserva la provenance registrada. `core` y `partner` requieren la asociación
confiable definida por el registro; un manifest no puede autoproclamarlas.
