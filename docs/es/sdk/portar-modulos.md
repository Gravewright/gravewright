# Portar módulos a Gravewright

Esta guía explica cómo adaptar a Gravewright un módulo creado para otra plataforma
de mesa virtual. **Módulo original** es el proyecto de referencia, **plataforma de
origen** es su entorno original y **port** es el nuevo package de Gravewright SDK.

Un port no consiste en renombrar APIs mecánicamente. Hay modelos diferentes de
datos, autoridad, permisos, lifecycle e interfaz. Preserve el comportamiento útil y
reimplemente la integración mediante contratos públicos de Gravewright.

> [!IMPORTANT]
> Use solamente código y materiales que tenga derecho a estudiar, modificar y
> redistribuir. Esta guía es técnica y no reemplaza asesoramiento jurídico.

## 1. Introducción

Elija el [`kind`](package-authoring.md) por el resultado en Gravewright: `addon` para
comportamiento opcional, `ruleset` para reglas base, `theme` para presentación,
`content` para contenido importable, `assets` para medios reutilizables y `library`
para una dependencia pasiva. No copie la clasificación de la plataforma de origen.

Lea el [inicio rápido](quick-start.md), las [capabilities](capabilities.md) y el
[manifest](manifest.md).

## 2. Evaluar el módulo antes de empezar

Registre repositorio, versión y commit; licencias del código y assets; autores y
avisos; funciones esenciales y opcionales; dependencias; APIs, eventos, datos, UI y
permisos de origen; alternativas declarativas; necesidades de runtime; dependencias
de internals privados; y riesgos de seguridad, rendimiento y multijugador.

Clasifique el resultado como **portable**, **portable con alcance reducido**,
**bloqueado por un SDK GAP** o **no redistribuible**. Pruebe primero la integración
mínima mediante la SDK pública.

## 3. Licencia

Que el código sea visible no autoriza su reutilización. Lea la licencia completa,
confirme modificación y redistribución, identifique atribución, entrega de código,
avisos y marcado de cambios, audite dependencias/assets y preserve todos los avisos.

### Licencias que normalmente permiten un port

Gravewright no impone una lista cerrada: `license` acepta un string. Use un
[identificador SPDX](https://spdx.org/licenses/) preciso. La aceptación técnica no
demuestra compatibilidad jurídica.

| Licencia | Valor del manifest | Obligación principal al distribuir |
|---|---|---|
| MIT | `MIT` | Conservar licencia y copyrights. |
| Apache 2.0 | `Apache-2.0` | Conservar licencia/notices, marcar cambios y cumplir sus términos de patentes. |
| BSD 2-Clause | `BSD-2-Clause` | Conservar copyright, condiciones y disclaimer. |
| BSD 3-Clause | `BSD-3-Clause` | Lo anterior y no usar nombres para aval sin permiso. |
| Mozilla Public License 2.0 | `MPL-2.0` | Publicar bajo MPL el source de archivos cubiertos modificados. |
| GNU LGPL 2.1 | `LGPL-2.1-only` o `LGPL-2.1-or-later` | Cumplir LGPL para la biblioteca cubierta y su modificación/sustitución. |
| GNU LGPL 3.0 | `LGPL-3.0-only` o `LGPL-3.0-or-later` | Cumplir LGPL para la biblioteca cubierta. |
| GNU GPL 2.0 | `GPL-2.0-only` o `GPL-2.0-or-later` | Distribuir derivados cubiertos de forma compatible y entregar source correspondiente. |
| GNU GPL 3.0 | `GPL-3.0-only` o `GPL-3.0-or-later` | Distribuir derivados cubiertos de forma compatible y entregar source correspondiente. |
| GNU Affero GPL 3.0 | `AGPL-3.0-only` o `AGPL-3.0-or-later` | Cumplir GPL y ofrecer source correspondiente a usuarios de red de una versión modificada. |
| Unlicense | `Unlicense` | Conservar el texto aplicable y revisar su adecuación jurídica. |

El port de dados 3D deriva de código GNU Affero GPL 3.0. Su valor exacto debe ser
`AGPL-3.0-only` o `AGPL-3.0-or-later`, según la concesión original. “GNU” no basta:
GPL, LGPL, AGPL, `only` y `or-later` tienen efectos distintos.

Para contenido/assets son comunes `CC0-1.0`, `CC-BY-4.0`, `CC-BY-SA-4.0` y
`OFL-1.1`. Creative Commons normalmente no se recomienda para código. `CC-BY-NC-*`
restringe uso comercial; `CC-BY-ND-*` impide distribuir una adaptación.

No redistribuya material sin licencia, `All Rights Reserved`, limitado a uso
personal, que prohíba derivados, adquirido sin permiso de redistribución o sujeto a
términos incompatibles. Acceso al source no equivale a permiso.

### Cómo declarar la licencia

Use identificadores o expresiones SPDX exactas:

```json
{ "license": "MIT" }
```

```json
{ "license": "AGPL-3.0-only" }
```

```json
{ "license": "MIT OR Apache-2.0" }
```

Use `OR` solamente para una elección alternativa real. Use `AND` únicamente cuando
el mismo trabajo esté sujeto simultáneamente a todas las licencias indicadas; no lo
use para resumir archivos independientes con licencias diferentes. Declare en el
manifest la licencia del código principal y mapee código, fuentes y assets de terceros
individualmente en `THIRD_PARTY_NOTICES.md`, sin sugerir que fueron relicenciados.
Incluya el texto principal en `LICENSE`, conserve headers, registre
proyecto/versión/commit/licencia en `UPSTREAM.md`, explique la cobertura en
`README.md` y entregue source correspondiente cuando el copyleft lo requiera.

## 4. Propiedad intelectual y assets

La licencia de código no cubre automáticamente marcas, nombres, arte, modelos 3D,
mapas, texto, publicaciones de juego, audio o fuentes. Inventaríe cada material con
origen, autor, licencia, cambios y destino. Evite sugerir afiliación; reemplace assets
ambiguos; conserve atribución; no incluya campañas, credenciales, bases ni archivos
personales.

## 5. Definir el alcance

Divida el módulo en comportamientos observables y marque cada uno como **portar**,
**reimplementar**, **sustituir** o **excluir**, con motivo e implementación. Documente
explícitamente lo que la primera versión no hace.

## 6. Mapear la arquitectura

| Necesidad | Contrato Gravewright |
|---|---|
| Lifecycle | `window.GravewrightSDK.register` |
| Metadata/compatibilidad | `manifest.json` |
| Permiso de API | `capabilities` |
| Estado de mesa | `sdk.context()` y `sdk.game.*` |
| Eventos | `sdk.bus.*` |
| Chat/rolls | `sdk.chat.*` y DTOs públicos |
| Configuración | settings declarados y `sdk.settings.*` |
| Sheets/combate | `sdk.sheets.*` / `sdk.combat.*` |
| Escena/tokens | `sdk.scene.*`, `sdk.tokens.*`, `sdk.tools.*` |
| UI/i18n | slots documentados de `sdk.ui.*` y `sdk.i18n.*` |
| Contenido/medios | packs y paths relativos declarados |

Sin method, event, DTO, capability o slot documentado, la superficie es privada.
Para cada acción defina iniciador, autoridad, audiencia, durabilidad, reconexión y
concurrencia. Nunca eluda autoridad mediante DOM, HTTP, WebSocket, base de datos,
filesystem o renderer privados. Consulte [seguridad](security.md).

## 7. Estructura del package

```bash
grave addon new mi-port --name "Mi Port" --js --settings
```

Incluya `manifest.json`, `README.md`, archivos de licencia/procedencia y solamente
los directorios de runtime necesarios. Declare capabilities usadas y prefiera datos
declarativos.

```js
window.GravewrightSDK.register({
  id: "mi-port",
  setup(sdk) {
    // Registrar listeners, commands e integraciones.
  },
  ready(sdk) {
    // Montar comportamiento que necesita el juego listo.
  },
});
```

La inicialización debe ser idempotente y el teardown completo. Fije dependencias,
preserve avisos, elimine adapters de origen, documente builds reproducibles y no
publique `node_modules`, caches, secrets ni archivos de desarrollo innecesarios.

## 8. Implementar mediante la SDK

Implemente verticalmente: registro, input/evento público, adapter interno, efecto
mínimo, permisos/multijugador, settings, accesibilidad/errores y teardown.

```text
evento/DTO público → adapter del port → motor independiente → UI/efecto
```

Pase solamente campos públicos necesarios y maneje versiones, opcionales y ausencia
de recursos.

## 9. Usar IA para automatizar el port

La IA puede inventariar, crear adapters, convertir formatos, generar tests y explicar
diagnósticos. No concede derechos ni justifica eludir la SDK. Limite la edición al
package, proporcione solo material licenciado y documentación pública, prohíba
inventar APIs/internals y exija patches pequeños con procedencia y tests.

```text
Edita solamente data/packages/addons/mi-port.
Usa únicamente APIs documentadas de Gravewright SDK 1.
No inventes capabilities ni accedas a DOM, base, filesystem, red, WebSocket,
stores o globals privados. Preserva licencias y añade tests de GM/jugadores.
Ejecuta:
grave package validate data/packages/addons/mi-port
grave package doctor mi-port
```

Nunca envíe `.env`, bases, saves, campañas privadas, credenciales o packages
comerciales a una IA externa. Consulte [authoring con IA](authoring-with-ai.md).

## 10. Validar, probar y depurar

Ejecute `grave package validate` y `grave package doctor`. Pruebe instalación,
activación/desactivación, reload, GM y jugadores simultáneos, permisos, lifecycle de
recursos, sync/reconexión/duplicados, concurrencia, campañas viejas/nuevas, settings,
dependencias ausentes, teardown, rendimiento, accesibilidad y errores seguros. Use
unit tests para adapters y E2E con browsers reales para UI, autoridad y multijugador.
Instale el artefacto final en un entorno limpio.

## 11. Informar un SDK GAP

Existe una GAP cuando un comportamiento legítimo y general no puede componerse con
APIs públicas, no porque la API original tuviera otro nombre. Revise capabilities,
methods y DTOs; reduzca el bloqueo a un package mínimo; evalúe autoridad y privacidad.

El informe debe incluir título orientado al objetivo, caso de uso, comportamiento y
audiencia esperados, APIs evaluadas, reproducción mínima, restricción exacta, mínima
capacidad general propuesta, seguridad/autoridad y alternativas. No publique contra
internals mientras espera: reduzca alcance o mantenga la función experimental.

## 12. Documentar autoría, origen y cambios

El README debe explicar función, partes reutilizadas/reimplementadas/excluidas,
no-afiliación, instalación, capabilities y motivos, compatibilidad, build,
limitaciones, licencia y enlaces a `UPSTREAM.md`/`THIRD_PARTY_NOTICES.md`. Mantenga un
changelog que distinga fixes del port, sync de origen y cambios de SDK.

## 13. Publicar

Valide y pruebe; instale el artefacto limpio; revise manifest, versiones,
dependencias, derechos y assets; publique SHA-256 y release notes; elija `dev`,
`testing` o `stable`; y siga el [Marketplace](marketplace.md). Excluya secrets, bases,
campañas, caches, dependencias de desarrollo, material sin licencia y archivos de
origen sin uso.

## 14. Mantener el port

Fije la versión original por release. Compare nuevos commits, aplique solo cambios de
alcance, conserve el adapter Gravewright, actualice avisos/assets, repita tests
multijugador y de artefacto limpio, documente divergencias y pruebe el contrato del
adapter.

## 15. Checklist final

- [ ] Todas las licencias permiten modificación y redistribución.
- [ ] `LICENSE`, `UPSTREAM.md` y `THIRD_PARTY_NOTICES.md` están completos.
- [ ] El alcance portado, sustituido y excluido está documentado.
- [ ] Todas las integraciones son SDK pública y cada capability está justificada.
- [ ] Autoridad, visibilidad, durabilidad, reconexión y concurrencia están definidas.
- [ ] `grave package validate` y `grave package doctor` pasan.
- [ ] Adapters tienen unit tests y flujos GM/jugador aplicables tienen E2E.
- [ ] Teardown, dependencias ausentes, accesibilidad y rendimiento fueron probados.
- [ ] El artefacto limpio se instala y solo contiene archivos necesarios.
- [ ] Manifest, compatibilidad, canal, hash, README y release notes son correctos.
- [ ] Existe un proceso no destructivo para actualizar desde el origen.
