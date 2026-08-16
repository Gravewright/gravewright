# Índice estrutural do contrato SDK 1

Identifiers canônicos não são traduzidos. A estrutura vem de `gravewright-sdk-1.json`.

## Capabilities

### `actors.data.write`

Status: `stable`
Tipos de package: `ruleset`, `addon`, `library`, `content`, `theme`, `assets`
Métodos: `sdk.actors.patchData`
Eventos: [Eventos](#eventos)
Erros: `CAPABILITY_REQUIRED`, `PERMISSION_DENIED`, `NOT_FOUND`, `VALIDATION_FAILED`, `STALE_VERSION`, `UNKNOWN_ACTION`
Autoridade: Capability declarada mais autoridade do usuário atual sobre o recurso; capabilities nunca elevam permissões.
Visibilidade: Projeção do usuário atual; recursos ocultos são indistinguíveis de inexistentes.
Concorrência: Autoritativo no servidor; `expectedVersion` é compare-and-swap atômico quando declarado.
Durabilidade: Somente recursos de servidor declarados são duráveis; registros locais terminam no unload do package.
Ciclo de vida: O package deve estar instalado, habilitado e ativo; registros retornam um disposer.
Limite de segurança: Não expõe filesystem, database, transport, renderer, internals de ACL nem override de permissão.

### `actors.items.read`

Status: `stable`
Tipos de package: `ruleset`, `addon`, `library`, `content`, `theme`, `assets`
Métodos: `sdk.actors.items.slots`, `sdk.actors.items.listCopies`
Eventos: [Eventos](#eventos)
Erros: `CAPABILITY_REQUIRED`, `PERMISSION_DENIED`, `NOT_FOUND`, `VALIDATION_FAILED`, `STALE_VERSION`, `UNKNOWN_ACTION`
Autoridade: Capability declarada mais autoridade do usuário atual sobre o recurso; capabilities nunca elevam permissões.
Visibilidade: Projeção do usuário atual; recursos ocultos são indistinguíveis de inexistentes.
Concorrência: Autoritativo no servidor; `expectedVersion` é compare-and-swap atômico quando declarado.
Durabilidade: Somente recursos de servidor declarados são duráveis; registros locais terminam no unload do package.
Ciclo de vida: O package deve estar instalado, habilitado e ativo; registros retornam um disposer.
Limite de segurança: Não expõe filesystem, database, transport, renderer, internals de ACL nem override de permissão.

### `actors.items.write`

Status: `stable`
Tipos de package: `ruleset`, `addon`, `library`, `content`, `theme`, `assets`
Métodos: `sdk.actors.items.insertCopy`, `sdk.actors.items.removeCopy`
Eventos: [Eventos](#eventos)
Erros: `CAPABILITY_REQUIRED`, `PERMISSION_DENIED`, `NOT_FOUND`, `VALIDATION_FAILED`, `STALE_VERSION`, `UNKNOWN_ACTION`
Autoridade: Capability declarada mais autoridade do usuário atual sobre o recurso; capabilities nunca elevam permissões.
Visibilidade: Projeção do usuário atual; recursos ocultos são indistinguíveis de inexistentes.
Concorrência: Autoritativo no servidor; `expectedVersion` é compare-and-swap atômico quando declarado.
Durabilidade: Somente recursos de servidor declarados são duráveis; registros locais terminam no unload do package.
Ciclo de vida: O package deve estar instalado, habilitado e ativo; registros retornam um disposer.
Limite de segurança: Não expõe filesystem, database, transport, renderer, internals de ACL nem override de permissão.

### `actors.read`

Status: `stable`
Tipos de package: `ruleset`, `addon`, `library`, `content`, `theme`, `assets`
Métodos: `sdk.actors.get`, `sdk.actors.list`, `sdk.actors.data`
Eventos: [Eventos](#eventos)
Erros: `CAPABILITY_REQUIRED`, `PERMISSION_DENIED`, `NOT_FOUND`, `VALIDATION_FAILED`, `STALE_VERSION`, `UNKNOWN_ACTION`
Autoridade: Capability declarada mais autoridade do usuário atual sobre o recurso; capabilities nunca elevam permissões.
Visibilidade: Projeção do usuário atual; recursos ocultos são indistinguíveis de inexistentes.
Concorrência: Autoritativo no servidor; `expectedVersion` é compare-and-swap atômico quando declarado.
Durabilidade: Somente recursos de servidor declarados são duráveis; registros locais terminam no unload do package.
Ciclo de vida: O package deve estar instalado, habilitado e ativo; registros retornam um disposer.
Limite de segurança: Não expõe filesystem, database, transport, renderer, internals de ACL nem override de permissão.

### `actors.register`

Status: `stable`
Tipos de package: `ruleset`, `addon`, `library`, `content`, `theme`, `assets`
Métodos: —
Eventos: [Eventos](#eventos)
Erros: `CAPABILITY_REQUIRED`, `PERMISSION_DENIED`, `NOT_FOUND`, `VALIDATION_FAILED`, `STALE_VERSION`, `UNKNOWN_ACTION`
Autoridade: Capability declarada mais autoridade do usuário atual sobre o recurso; capabilities nunca elevam permissões.
Visibilidade: Projeção do usuário atual; recursos ocultos são indistinguíveis de inexistentes.
Concorrência: Autoritativo no servidor; `expectedVersion` é compare-and-swap atômico quando declarado.
Durabilidade: Somente recursos de servidor declarados são duráveis; registros locais terminam no unload do package.
Ciclo de vida: O package deve estar instalado, habilitado e ativo; registros retornam um disposer.
Limite de segurança: Não expõe filesystem, database, transport, renderer, internals de ACL nem override de permissão.

### `actors.write`

Status: `stable`
Tipos de package: `ruleset`, `addon`, `library`, `content`, `theme`, `assets`
Métodos: `sdk.actors.create`, `sdk.actors.update`, `sdk.actors.delete`
Eventos: [Eventos](#eventos)
Erros: `CAPABILITY_REQUIRED`, `PERMISSION_DENIED`, `NOT_FOUND`, `VALIDATION_FAILED`, `STALE_VERSION`, `UNKNOWN_ACTION`
Autoridade: Capability declarada mais autoridade do usuário atual sobre o recurso; capabilities nunca elevam permissões.
Visibilidade: Projeção do usuário atual; recursos ocultos são indistinguíveis de inexistentes.
Concorrência: Autoritativo no servidor; `expectedVersion` é compare-and-swap atômico quando declarado.
Durabilidade: Somente recursos de servidor declarados são duráveis; registros locais terminam no unload do package.
Ciclo de vida: O package deve estar instalado, habilitado e ativo; registros retornam um disposer.
Limite de segurança: Não expõe filesystem, database, transport, renderer, internals de ACL nem override de permissão.

### `assets.audio`

Status: `stable`
Tipos de package: `ruleset`, `addon`, `library`, `content`, `theme`, `assets`
Métodos: —
Eventos: [Eventos](#eventos)
Erros: `CAPABILITY_REQUIRED`, `PERMISSION_DENIED`, `NOT_FOUND`, `VALIDATION_FAILED`, `STALE_VERSION`, `UNKNOWN_ACTION`
Autoridade: Capability declarada mais autoridade do usuário atual sobre o recurso; capabilities nunca elevam permissões.
Visibilidade: Projeção do usuário atual; recursos ocultos são indistinguíveis de inexistentes.
Concorrência: Autoritativo no servidor; `expectedVersion` é compare-and-swap atômico quando declarado.
Durabilidade: Somente recursos de servidor declarados são duráveis; registros locais terminam no unload do package.
Ciclo de vida: O package deve estar instalado, habilitado e ativo; registros retornam um disposer.
Limite de segurança: Não expõe filesystem, database, transport, renderer, internals de ACL nem override de permissão.

### `assets.icons`

Status: `stable`
Tipos de package: `ruleset`, `addon`, `library`, `content`, `theme`, `assets`
Métodos: —
Eventos: [Eventos](#eventos)
Erros: `CAPABILITY_REQUIRED`, `PERMISSION_DENIED`, `NOT_FOUND`, `VALIDATION_FAILED`, `STALE_VERSION`, `UNKNOWN_ACTION`
Autoridade: Capability declarada mais autoridade do usuário atual sobre o recurso; capabilities nunca elevam permissões.
Visibilidade: Projeção do usuário atual; recursos ocultos são indistinguíveis de inexistentes.
Concorrência: Autoritativo no servidor; `expectedVersion` é compare-and-swap atômico quando declarado.
Durabilidade: Somente recursos de servidor declarados são duráveis; registros locais terminam no unload do package.
Ciclo de vida: O package deve estar instalado, habilitado e ativo; registros retornam um disposer.
Limite de segurança: Não expõe filesystem, database, transport, renderer, internals de ACL nem override de permissão.

### `assets.images`

Status: `stable`
Tipos de package: `ruleset`, `addon`, `library`, `content`, `theme`, `assets`
Métodos: —
Eventos: [Eventos](#eventos)
Erros: `CAPABILITY_REQUIRED`, `PERMISSION_DENIED`, `NOT_FOUND`, `VALIDATION_FAILED`, `STALE_VERSION`, `UNKNOWN_ACTION`
Autoridade: Capability declarada mais autoridade do usuário atual sobre o recurso; capabilities nunca elevam permissões.
Visibilidade: Projeção do usuário atual; recursos ocultos são indistinguíveis de inexistentes.
Concorrência: Autoritativo no servidor; `expectedVersion` é compare-and-swap atômico quando declarado.
Durabilidade: Somente recursos de servidor declarados são duráveis; registros locais terminam no unload do package.
Ciclo de vida: O package deve estar instalado, habilitado e ativo; registros retornam um disposer.
Limite de segurança: Não expõe filesystem, database, transport, renderer, internals de ACL nem override de permissão.

### `assets.import`

Status: `stable`
Tipos de package: `ruleset`, `addon`, `library`, `content`, `theme`, `assets`
Métodos: `sdk.assets.ingest`, `sdk.assets.cancelImport`
Eventos: [Eventos](#eventos)
Erros: `CAPABILITY_REQUIRED`, `PERMISSION_DENIED`, `NOT_FOUND`, `VALIDATION_FAILED`, `STALE_VERSION`, `UNKNOWN_ACTION`
Autoridade: Capability declarada mais autoridade do usuário atual sobre o recurso; capabilities nunca elevam permissões.
Visibilidade: Projeção do usuário atual; recursos ocultos são indistinguíveis de inexistentes.
Concorrência: Autoritativo no servidor; `expectedVersion` é compare-and-swap atômico quando declarado.
Durabilidade: Somente recursos de servidor declarados são duráveis; registros locais terminam no unload do package.
Ciclo de vida: O package deve estar instalado, habilitado e ativo; registros retornam um disposer.
Limite de segurança: Não expõe filesystem, database, transport, renderer, internals de ACL nem override de permissão.

### `assets.library`

Status: `stable`
Tipos de package: `ruleset`, `addon`, `library`, `content`, `theme`, `assets`
Métodos: `sdk.assets.list`
Eventos: [Eventos](#eventos)
Erros: `CAPABILITY_REQUIRED`, `PERMISSION_DENIED`, `NOT_FOUND`, `VALIDATION_FAILED`, `STALE_VERSION`, `UNKNOWN_ACTION`
Autoridade: Capability declarada mais autoridade do usuário atual sobre o recurso; capabilities nunca elevam permissões.
Visibilidade: Projeção do usuário atual; recursos ocultos são indistinguíveis de inexistentes.
Concorrência: Autoritativo no servidor; `expectedVersion` é compare-and-swap atômico quando declarado.
Durabilidade: Somente recursos de servidor declarados são duráveis; registros locais terminam no unload do package.
Ciclo de vida: O package deve estar instalado, habilitado e ativo; registros retornam um disposer.
Limite de segurança: Não expõe filesystem, database, transport, renderer, internals de ACL nem override de permissão.

### `assets.maps`

Status: `stable`
Tipos de package: `ruleset`, `addon`, `library`, `content`, `theme`, `assets`
Métodos: —
Eventos: [Eventos](#eventos)
Erros: `CAPABILITY_REQUIRED`, `PERMISSION_DENIED`, `NOT_FOUND`, `VALIDATION_FAILED`, `STALE_VERSION`, `UNKNOWN_ACTION`
Autoridade: Capability declarada mais autoridade do usuário atual sobre o recurso; capabilities nunca elevam permissões.
Visibilidade: Projeção do usuário atual; recursos ocultos são indistinguíveis de inexistentes.
Concorrência: Autoritativo no servidor; `expectedVersion` é compare-and-swap atômico quando declarado.
Durabilidade: Somente recursos de servidor declarados são duráveis; registros locais terminam no unload do package.
Ciclo de vida: O package deve estar instalado, habilitado e ativo; registros retornam um disposer.
Limite de segurança: Não expõe filesystem, database, transport, renderer, internals de ACL nem override de permissão.

### `assets.pack`

Status: `stable`
Tipos de package: `ruleset`, `addon`, `library`, `content`, `theme`, `assets`
Métodos: —
Eventos: [Eventos](#eventos)
Erros: `CAPABILITY_REQUIRED`, `PERMISSION_DENIED`, `NOT_FOUND`, `VALIDATION_FAILED`, `STALE_VERSION`, `UNKNOWN_ACTION`
Autoridade: Capability declarada mais autoridade do usuário atual sobre o recurso; capabilities nunca elevam permissões.
Visibilidade: Projeção do usuário atual; recursos ocultos são indistinguíveis de inexistentes.
Concorrência: Autoritativo no servidor; `expectedVersion` é compare-and-swap atômico quando declarado.
Durabilidade: Somente recursos de servidor declarados são duráveis; registros locais terminam no unload do package.
Ciclo de vida: O package deve estar instalado, habilitado e ativo; registros retornam um disposer.
Limite de segurança: Não expõe filesystem, database, transport, renderer, internals de ACL nem override de permissão.

### `assets.scripts`

Status: `stable`
Tipos de package: `ruleset`, `addon`, `library`, `content`, `theme`, `assets`
Métodos: —
Eventos: [Eventos](#eventos)
Erros: `CAPABILITY_REQUIRED`, `PERMISSION_DENIED`, `NOT_FOUND`, `VALIDATION_FAILED`, `STALE_VERSION`, `UNKNOWN_ACTION`
Autoridade: Capability declarada mais autoridade do usuário atual sobre o recurso; capabilities nunca elevam permissões.
Visibilidade: Projeção do usuário atual; recursos ocultos são indistinguíveis de inexistentes.
Concorrência: Autoritativo no servidor; `expectedVersion` é compare-and-swap atômico quando declarado.
Durabilidade: Somente recursos de servidor declarados são duráveis; registros locais terminam no unload do package.
Ciclo de vida: O package deve estar instalado, habilitado e ativo; registros retornam um disposer.
Limite de segurança: Não expõe filesystem, database, transport, renderer, internals de ACL nem override de permissão.

### `assets.styles`

Status: `stable`
Tipos de package: `ruleset`, `addon`, `library`, `content`, `theme`, `assets`
Métodos: —
Eventos: [Eventos](#eventos)
Erros: `CAPABILITY_REQUIRED`, `PERMISSION_DENIED`, `NOT_FOUND`, `VALIDATION_FAILED`, `STALE_VERSION`, `UNKNOWN_ACTION`
Autoridade: Capability declarada mais autoridade do usuário atual sobre o recurso; capabilities nunca elevam permissões.
Visibilidade: Projeção do usuário atual; recursos ocultos são indistinguíveis de inexistentes.
Concorrência: Autoritativo no servidor; `expectedVersion` é compare-and-swap atômico quando declarado.
Durabilidade: Somente recursos de servidor declarados são duráveis; registros locais terminam no unload do package.
Ciclo de vida: O package deve estar instalado, habilitado e ativo; registros retornam um disposer.
Limite de segurança: Não expõe filesystem, database, transport, renderer, internals de ACL nem override de permissão.

### `assets.ui`

Status: `stable`
Tipos de package: `ruleset`, `addon`, `library`, `content`, `theme`, `assets`
Métodos: `sdk.ui.toast`, `sdk.ui.openModal`, `sdk.ui.closeModal`
Eventos: [Eventos](#eventos)
Erros: `CAPABILITY_REQUIRED`, `PERMISSION_DENIED`, `NOT_FOUND`, `VALIDATION_FAILED`, `STALE_VERSION`, `UNKNOWN_ACTION`
Autoridade: Capability declarada mais autoridade do usuário atual sobre o recurso; capabilities nunca elevam permissões.
Visibilidade: Projeção do usuário atual; recursos ocultos são indistinguíveis de inexistentes.
Concorrência: Autoritativo no servidor; `expectedVersion` é compare-and-swap atômico quando declarado.
Durabilidade: Somente recursos de servidor declarados são duráveis; registros locais terminam no unload do package.
Ciclo de vida: O package deve estar instalado, habilitado e ativo; registros retornam um disposer.
Limite de segurança: Não expõe filesystem, database, transport, renderer, internals de ACL nem override de permissão.

### `assets.video`

Status: `stable`
Tipos de package: `ruleset`, `addon`, `library`, `content`, `theme`, `assets`
Métodos: —
Eventos: [Eventos](#eventos)
Erros: `CAPABILITY_REQUIRED`, `PERMISSION_DENIED`, `NOT_FOUND`, `VALIDATION_FAILED`, `STALE_VERSION`, `UNKNOWN_ACTION`
Autoridade: Capability declarada mais autoridade do usuário atual sobre o recurso; capabilities nunca elevam permissões.
Visibilidade: Projeção do usuário atual; recursos ocultos são indistinguíveis de inexistentes.
Concorrência: Autoritativo no servidor; `expectedVersion` é compare-and-swap atômico quando declarado.
Durabilidade: Somente recursos de servidor declarados são duráveis; registros locais terminam no unload do package.
Ciclo de vida: O package deve estar instalado, habilitado e ativo; registros retornam um disposer.
Limite de segurança: Não expõe filesystem, database, transport, renderer, internals de ACL nem override de permissão.

### `automation.schedule`

Status: `stable`
Tipos de package: `ruleset`, `addon`, `library`, `content`, `theme`, `assets`
Métodos: `sdk.automation.schedule`, `sdk.automation.get`, `sdk.automation.list`, `sdk.automation.cancel`, `sdk.automation.audit`
Eventos: [Eventos](#eventos)
Erros: `CAPABILITY_REQUIRED`, `PERMISSION_DENIED`, `NOT_FOUND`, `VALIDATION_FAILED`, `STALE_VERSION`, `UNKNOWN_ACTION`
Autoridade: Capability declarada mais autoridade do usuário atual sobre o recurso; capabilities nunca elevam permissões.
Visibilidade: Projeção do usuário atual; recursos ocultos são indistinguíveis de inexistentes.
Concorrência: Autoritativo no servidor; `expectedVersion` é compare-and-swap atômico quando declarado.
Durabilidade: Somente recursos de servidor declarados são duráveis; registros locais terminam no unload do package.
Ciclo de vida: O package deve estar instalado, habilitado e ativo; registros retornam um disposer.
Limite de segurança: Não expõe filesystem, database, transport, renderer, internals de ACL nem override de permissão.

### `bus.provide`

Status: `stable`
Tipos de package: `ruleset`, `addon`, `library`, `content`, `theme`, `assets`
Métodos: `sdk.bus.provide`
Eventos: [Eventos](#eventos)
Erros: `CAPABILITY_REQUIRED`, `PERMISSION_DENIED`, `NOT_FOUND`, `VALIDATION_FAILED`, `STALE_VERSION`, `UNKNOWN_ACTION`
Autoridade: Capability declarada mais autoridade do usuário atual sobre o recurso; capabilities nunca elevam permissões.
Visibilidade: Projeção do usuário atual; recursos ocultos são indistinguíveis de inexistentes.
Concorrência: Autoritativo no servidor; `expectedVersion` é compare-and-swap atômico quando declarado.
Durabilidade: Somente recursos de servidor declarados são duráveis; registros locais terminam no unload do package.
Ciclo de vida: O package deve estar instalado, habilitado e ativo; registros retornam um disposer.
Limite de segurança: Não expõe filesystem, database, transport, renderer, internals de ACL nem override de permissão.

### `bus.publish`

Status: `stable`
Tipos de package: `ruleset`, `addon`, `library`, `content`, `theme`, `assets`
Métodos: `sdk.bus.publish`
Eventos: [Eventos](#eventos)
Erros: `CAPABILITY_REQUIRED`, `PERMISSION_DENIED`, `NOT_FOUND`, `VALIDATION_FAILED`, `STALE_VERSION`, `UNKNOWN_ACTION`
Autoridade: Capability declarada mais autoridade do usuário atual sobre o recurso; capabilities nunca elevam permissões.
Visibilidade: Projeção do usuário atual; recursos ocultos são indistinguíveis de inexistentes.
Concorrência: Autoritativo no servidor; `expectedVersion` é compare-and-swap atômico quando declarado.
Durabilidade: Somente recursos de servidor declarados são duráveis; registros locais terminam no unload do package.
Ciclo de vida: O package deve estar instalado, habilitado e ativo; registros retornam um disposer.
Limite de segurança: Não expõe filesystem, database, transport, renderer, internals de ACL nem override de permissão.

### `bus.request`

Status: `stable`
Tipos de package: `ruleset`, `addon`, `library`, `content`, `theme`, `assets`
Métodos: `sdk.bus.request`
Eventos: [Eventos](#eventos)
Erros: `CAPABILITY_REQUIRED`, `PERMISSION_DENIED`, `NOT_FOUND`, `VALIDATION_FAILED`, `STALE_VERSION`, `UNKNOWN_ACTION`
Autoridade: Capability declarada mais autoridade do usuário atual sobre o recurso; capabilities nunca elevam permissões.
Visibilidade: Projeção do usuário atual; recursos ocultos são indistinguíveis de inexistentes.
Concorrência: Autoritativo no servidor; `expectedVersion` é compare-and-swap atômico quando declarado.
Durabilidade: Somente recursos de servidor declarados são duráveis; registros locais terminam no unload do package.
Ciclo de vida: O package deve estar instalado, habilitado e ativo; registros retornam um disposer.
Limite de segurança: Não expõe filesystem, database, transport, renderer, internals de ACL nem override de permissão.

### `bus.subscribe`

Status: `stable`
Tipos de package: `ruleset`, `addon`, `library`, `content`, `theme`, `assets`
Métodos: `sdk.bus.subscribe`
Eventos: [Eventos](#eventos)
Erros: `CAPABILITY_REQUIRED`, `PERMISSION_DENIED`, `NOT_FOUND`, `VALIDATION_FAILED`, `STALE_VERSION`, `UNKNOWN_ACTION`
Autoridade: Capability declarada mais autoridade do usuário atual sobre o recurso; capabilities nunca elevam permissões.
Visibilidade: Projeção do usuário atual; recursos ocultos são indistinguíveis de inexistentes.
Concorrência: Autoritativo no servidor; `expectedVersion` é compare-and-swap atômico quando declarado.
Durabilidade: Somente recursos de servidor declarados são duráveis; registros locais terminam no unload do package.
Ciclo de vida: O package deve estar instalado, habilitado e ativo; registros retornam um disposer.
Limite de segurança: Não expõe filesystem, database, transport, renderer, internals de ACL nem override de permissão.

### `cards.manage`

Status: `stable`
Tipos de package: `ruleset`, `addon`, `library`, `content`, `theme`, `assets`
Métodos: `sdk.cards.definitions.instantiate`, `sdk.cards.shuffle`, `sdk.cards.reset`, `sdk.cards.draw`, `sdk.cards.reveal`, `sdk.cards.discard`, `sdk.cards.play`, `sdk.cards.updatePlacement`, `sdk.cards.discardPlacement`
Eventos: [Eventos](#eventos)
Erros: `CAPABILITY_REQUIRED`, `PERMISSION_DENIED`, `NOT_FOUND`, `VALIDATION_FAILED`, `STALE_VERSION`, `UNKNOWN_ACTION`
Autoridade: Capability declarada mais autoridade do usuário atual sobre o recurso; capabilities nunca elevam permissões.
Visibilidade: Projeção do usuário atual; recursos ocultos são indistinguíveis de inexistentes.
Concorrência: Autoritativo no servidor; `expectedVersion` é compare-and-swap atômico quando declarado.
Durabilidade: Somente recursos de servidor declarados são duráveis; registros locais terminam no unload do package.
Ciclo de vida: O package deve estar instalado, habilitado e ativo; registros retornam um disposer.
Limite de segurança: Não expõe filesystem, database, transport, renderer, internals de ACL nem override de permissão.

### `cards.read`

Status: `stable`
Tipos de package: `ruleset`, `addon`, `library`, `content`, `theme`, `assets`
Métodos: `sdk.cards.state`, `sdk.cards.definitions.list`, `sdk.cards.definitions.get`
Eventos: [Eventos](#eventos)
Erros: `CAPABILITY_REQUIRED`, `PERMISSION_DENIED`, `NOT_FOUND`, `VALIDATION_FAILED`, `STALE_VERSION`, `UNKNOWN_ACTION`
Autoridade: Capability declarada mais autoridade do usuário atual sobre o recurso; capabilities nunca elevam permissões.
Visibilidade: Projeção do usuário atual; recursos ocultos são indistinguíveis de inexistentes.
Concorrência: Autoritativo no servidor; `expectedVersion` é compare-and-swap atômico quando declarado.
Durabilidade: Somente recursos de servidor declarados são duráveis; registros locais terminam no unload do package.
Ciclo de vida: O package deve estar instalado, habilitado e ativo; registros retornam um disposer.
Limite de segurança: Não expõe filesystem, database, transport, renderer, internals de ACL nem override de permissão.

### `chat.cards`

Status: `stable`
Tipos de package: `ruleset`, `addon`, `library`, `content`, `theme`, `assets`
Métodos: `sdk.chat.send`
Eventos: [Eventos](#eventos)
Erros: `CAPABILITY_REQUIRED`, `PERMISSION_DENIED`, `NOT_FOUND`, `VALIDATION_FAILED`, `STALE_VERSION`, `UNKNOWN_ACTION`
Autoridade: Capability declarada mais autoridade do usuário atual sobre o recurso; capabilities nunca elevam permissões.
Visibilidade: Projeção do usuário atual; recursos ocultos são indistinguíveis de inexistentes.
Concorrência: Autoritativo no servidor; `expectedVersion` é compare-and-swap atômico quando declarado.
Durabilidade: Somente recursos de servidor declarados são duráveis; registros locais terminam no unload do package.
Ciclo de vida: O package deve estar instalado, habilitado e ativo; registros retornam um disposer.
Limite de segurança: Não expõe filesystem, database, transport, renderer, internals de ACL nem override de permissão.

### `chat.read`

Status: `stable`
Tipos de package: `ruleset`, `addon`, `library`, `content`, `theme`, `assets`
Métodos: `sdk.chat.list`, `sdk.chat.get`
Eventos: [Eventos](#eventos)
Erros: `CAPABILITY_REQUIRED`, `PERMISSION_DENIED`, `NOT_FOUND`, `VALIDATION_FAILED`, `STALE_VERSION`, `UNKNOWN_ACTION`
Autoridade: Capability declarada mais autoridade do usuário atual sobre o recurso; capabilities nunca elevam permissões.
Visibilidade: Projeção do usuário atual; recursos ocultos são indistinguíveis de inexistentes.
Concorrência: Autoritativo no servidor; `expectedVersion` é compare-and-swap atômico quando declarado.
Durabilidade: Somente recursos de servidor declarados são duráveis; registros locais terminam no unload do package.
Ciclo de vida: O package deve estar instalado, habilitado e ativo; registros retornam um disposer.
Limite de segurança: Não expõe filesystem, database, transport, renderer, internals de ACL nem override de permissão.

### `combat.config`

Status: `stable`
Tipos de package: `ruleset`, `addon`, `library`, `content`, `theme`, `assets`
Métodos: —
Eventos: [Eventos](#eventos)
Erros: `CAPABILITY_REQUIRED`, `PERMISSION_DENIED`, `NOT_FOUND`, `VALIDATION_FAILED`, `STALE_VERSION`, `UNKNOWN_ACTION`
Autoridade: Capability declarada mais autoridade do usuário atual sobre o recurso; capabilities nunca elevam permissões.
Visibilidade: Projeção do usuário atual; recursos ocultos são indistinguíveis de inexistentes.
Concorrência: Autoritativo no servidor; `expectedVersion` é compare-and-swap atômico quando declarado.
Durabilidade: Somente recursos de servidor declarados são duráveis; registros locais terminam no unload do package.
Ciclo de vida: O package deve estar instalado, habilitado e ativo; registros retornam um disposer.
Limite de segurança: Não expõe filesystem, database, transport, renderer, internals de ACL nem override de permissão.

### `combat.manage`

Status: `stable`
Tipos de package: `ruleset`, `addon`, `library`, `content`, `theme`, `assets`
Métodos: `sdk.combat.start`, `sdk.combat.end`, `sdk.combat.advance`, `sdk.combat.advanceRound`, `sdk.combat.setTurn`, `sdk.combat.add`, `sdk.combat.remove`, `sdk.combat.setFlags`, `sdk.combat.rollInitiative`, `sdk.combat.setInitiative`, `sdk.combat.moveCombatant`, `sdk.combat.setInitiativeOrder`
Eventos: [Eventos](#eventos)
Erros: `CAPABILITY_REQUIRED`, `PERMISSION_DENIED`, `NOT_FOUND`, `VALIDATION_FAILED`, `STALE_VERSION`, `UNKNOWN_ACTION`
Autoridade: Capability declarada mais autoridade do usuário atual sobre o recurso; capabilities nunca elevam permissões.
Visibilidade: Projeção do usuário atual; recursos ocultos são indistinguíveis de inexistentes.
Concorrência: Autoritativo no servidor; `expectedVersion` é compare-and-swap atômico quando declarado.
Durabilidade: Somente recursos de servidor declarados são duráveis; registros locais terminam no unload do package.
Ciclo de vida: O package deve estar instalado, habilitado e ativo; registros retornam um disposer.
Limite de segurança: Não expõe filesystem, database, transport, renderer, internals de ACL nem override de permissão.

### `combat.read`

Status: `stable`
Tipos de package: `ruleset`, `addon`, `library`, `content`, `theme`, `assets`
Métodos: `sdk.combat.current`, `sdk.combat.combatants`
Eventos: [Eventos](#eventos)
Erros: `CAPABILITY_REQUIRED`, `PERMISSION_DENIED`, `NOT_FOUND`, `VALIDATION_FAILED`, `STALE_VERSION`, `UNKNOWN_ACTION`
Autoridade: Capability declarada mais autoridade do usuário atual sobre o recurso; capabilities nunca elevam permissões.
Visibilidade: Projeção do usuário atual; recursos ocultos são indistinguíveis de inexistentes.
Concorrência: Autoritativo no servidor; `expectedVersion` é compare-and-swap atômico quando declarado.
Durabilidade: Somente recursos de servidor declarados são duráveis; registros locais terminam no unload do package.
Ciclo de vida: O package deve estar instalado, habilitado e ativo; registros retornam um disposer.
Limite de segurança: Não expõe filesystem, database, transport, renderer, internals de ACL nem override de permissão.

### `combat.runtime`

Status: `stable`
Tipos de package: `ruleset`, `addon`, `library`, `content`, `theme`, `assets`
Métodos: `sdk.combat.register`, `sdk.combat.registerPanel`, `sdk.combat.dispatch`, `sdk.combat.renderSlot`
Eventos: [Eventos](#eventos)
Erros: `CAPABILITY_REQUIRED`, `PERMISSION_DENIED`, `NOT_FOUND`, `VALIDATION_FAILED`, `STALE_VERSION`, `UNKNOWN_ACTION`
Autoridade: Capability declarada mais autoridade do usuário atual sobre o recurso; capabilities nunca elevam permissões.
Visibilidade: Projeção do usuário atual; recursos ocultos são indistinguíveis de inexistentes.
Concorrência: Autoritativo no servidor; `expectedVersion` é compare-and-swap atômico quando declarado.
Durabilidade: Somente recursos de servidor declarados são duráveis; registros locais terminam no unload do package.
Ciclo de vida: O package deve estar instalado, habilitado e ativo; registros retornam um disposer.
Limite de segurança: Não expõe filesystem, database, transport, renderer, internals de ACL nem override de permissão.

### `commands.register`

Status: `stable`
Tipos de package: `ruleset`, `addon`, `library`, `content`, `theme`, `assets`
Métodos: `sdk.commands.register`
Eventos: [Eventos](#eventos)
Erros: `CAPABILITY_REQUIRED`, `PERMISSION_DENIED`, `NOT_FOUND`, `VALIDATION_FAILED`, `STALE_VERSION`, `UNKNOWN_ACTION`
Autoridade: Capability declarada mais autoridade do usuário atual sobre o recurso; capabilities nunca elevam permissões.
Visibilidade: Projeção do usuário atual; recursos ocultos são indistinguíveis de inexistentes.
Concorrência: Autoritativo no servidor; `expectedVersion` é compare-and-swap atômico quando declarado.
Durabilidade: Somente recursos de servidor declarados são duráveis; registros locais terminam no unload do package.
Ciclo de vida: O package deve estar instalado, habilitado e ativo; registros retornam um disposer.
Limite de segurança: Não expõe filesystem, database, transport, renderer, internals de ACL nem override de permissão.

### `content.index`

Status: `stable`
Tipos de package: `ruleset`, `addon`, `library`, `content`, `theme`, `assets`
Métodos: `sdk.content.search`
Eventos: [Eventos](#eventos)
Erros: `CAPABILITY_REQUIRED`, `PERMISSION_DENIED`, `NOT_FOUND`, `VALIDATION_FAILED`, `STALE_VERSION`, `UNKNOWN_ACTION`
Autoridade: Capability declarada mais autoridade do usuário atual sobre o recurso; capabilities nunca elevam permissões.
Visibilidade: Projeção do usuário atual; recursos ocultos são indistinguíveis de inexistentes.
Concorrência: Autoritativo no servidor; `expectedVersion` é compare-and-swap atômico quando declarado.
Durabilidade: Somente recursos de servidor declarados são duráveis; registros locais terminam no unload do package.
Ciclo de vida: O package deve estar instalado, habilitado e ativo; registros retornam um disposer.
Limite de segurança: Não expõe filesystem, database, transport, renderer, internals de ACL nem override de permissão.

### `content.packs`

Status: `stable`
Tipos de package: `ruleset`, `addon`, `library`, `content`, `theme`, `assets`
Métodos: `sdk.content.packs`, `sdk.content.pack`
Eventos: [Eventos](#eventos)
Erros: `CAPABILITY_REQUIRED`, `PERMISSION_DENIED`, `NOT_FOUND`, `VALIDATION_FAILED`, `STALE_VERSION`, `UNKNOWN_ACTION`
Autoridade: Capability declarada mais autoridade do usuário atual sobre o recurso; capabilities nunca elevam permissões.
Visibilidade: Projeção do usuário atual; recursos ocultos são indistinguíveis de inexistentes.
Concorrência: Autoritativo no servidor; `expectedVersion` é compare-and-swap atômico quando declarado.
Durabilidade: Somente recursos de servidor declarados são duráveis; registros locais terminam no unload do package.
Ciclo de vida: O package deve estar instalado, habilitado e ativo; registros retornam um disposer.
Limite de segurança: Não expõe filesystem, database, transport, renderer, internals de ACL nem override de permissão.

### `content.references`

Status: `stable`
Tipos de package: `ruleset`, `addon`, `library`, `content`, `theme`, `assets`
Métodos: `sdk.content.ref`, `sdk.content.resolve`, `sdk.content.get`, `sdk.content.can`, `sdk.content.open`, `sdk.content.link`
Eventos: [Eventos](#eventos)
Erros: `CAPABILITY_REQUIRED`, `PERMISSION_DENIED`, `NOT_FOUND`, `VALIDATION_FAILED`, `STALE_VERSION`, `UNKNOWN_ACTION`
Autoridade: Capability declarada mais autoridade do usuário atual sobre o recurso; capabilities nunca elevam permissões.
Visibilidade: Projeção do usuário atual; recursos ocultos são indistinguíveis de inexistentes.
Concorrência: Autoritativo no servidor; `expectedVersion` é compare-and-swap atômico quando declarado.
Durabilidade: Somente recursos de servidor declarados são duráveis; registros locais terminam no unload do package.
Ciclo de vida: O package deve estar instalado, habilitado e ativo; registros retornam um disposer.
Limite de segurança: Não expõe filesystem, database, transport, renderer, internals de ACL nem override de permissão.

### `dice.roll`

Status: `stable`
Tipos de package: `ruleset`, `addon`, `library`, `content`, `theme`, `assets`
Métodos: `sdk.dice.roll`
Eventos: [Eventos](#eventos)
Erros: `CAPABILITY_REQUIRED`, `PERMISSION_DENIED`, `NOT_FOUND`, `VALIDATION_FAILED`, `STALE_VERSION`, `UNKNOWN_ACTION`
Autoridade: Capability declarada mais autoridade do usuário atual sobre o recurso; capabilities nunca elevam permissões.
Visibilidade: Projeção do usuário atual; recursos ocultos são indistinguíveis de inexistentes.
Concorrência: Autoritativo no servidor; `expectedVersion` é compare-and-swap atômico quando declarado.
Durabilidade: Somente recursos de servidor declarados são duráveis; registros locais terminam no unload do package.
Ciclo de vida: O package deve estar instalado, habilitado e ativo; registros retornam um disposer.
Limite de segurança: Não expõe filesystem, database, transport, renderer, internals de ACL nem override de permissão.

### `events.subscribe`

Status: `stable`
Tipos de package: `ruleset`, `addon`, `library`, `content`, `theme`, `assets`
Métodos: `sdk.events.on`, `sdk.events.once`, `sdk.events.available`
Eventos: [Eventos](#eventos)
Erros: `CAPABILITY_REQUIRED`, `PERMISSION_DENIED`, `NOT_FOUND`, `VALIDATION_FAILED`, `STALE_VERSION`, `UNKNOWN_ACTION`
Autoridade: Capability declarada mais autoridade do usuário atual sobre o recurso; capabilities nunca elevam permissões.
Visibilidade: Projeção do usuário atual; recursos ocultos são indistinguíveis de inexistentes.
Concorrência: Autoritativo no servidor; `expectedVersion` é compare-and-swap atômico quando declarado.
Durabilidade: Somente recursos de servidor declarados são duráveis; registros locais terminam no unload do package.
Ciclo de vida: O package deve estar instalado, habilitado e ativo; registros retornam um disposer.
Limite de segurança: Não expõe filesystem, database, transport, renderer, internals de ACL nem override de permissão.

### `handouts.present`

Status: `stable`
Tipos de package: `ruleset`, `addon`, `library`, `content`, `theme`, `assets`
Métodos: `sdk.handouts.present`
Eventos: [Eventos](#eventos)
Erros: `CAPABILITY_REQUIRED`, `PERMISSION_DENIED`, `NOT_FOUND`, `VALIDATION_FAILED`, `STALE_VERSION`, `UNKNOWN_ACTION`
Autoridade: Capability declarada mais autoridade do usuário atual sobre o recurso; capabilities nunca elevam permissões.
Visibilidade: Projeção do usuário atual; recursos ocultos são indistinguíveis de inexistentes.
Concorrência: Autoritativo no servidor; `expectedVersion` é compare-and-swap atômico quando declarado.
Durabilidade: Somente recursos de servidor declarados são duráveis; registros locais terminam no unload do package.
Ciclo de vida: O package deve estar instalado, habilitado e ativo; registros retornam um disposer.
Limite de segurança: Não expõe filesystem, database, transport, renderer, internals de ACL nem override de permissão.

### `items.data.write`

Status: `stable`
Tipos de package: `ruleset`, `addon`, `library`, `content`, `theme`, `assets`
Métodos: `sdk.items.patchData`
Eventos: [Eventos](#eventos)
Erros: `CAPABILITY_REQUIRED`, `PERMISSION_DENIED`, `NOT_FOUND`, `VALIDATION_FAILED`, `STALE_VERSION`, `UNKNOWN_ACTION`
Autoridade: Capability declarada mais autoridade do usuário atual sobre o recurso; capabilities nunca elevam permissões.
Visibilidade: Projeção do usuário atual; recursos ocultos são indistinguíveis de inexistentes.
Concorrência: Autoritativo no servidor; `expectedVersion` é compare-and-swap atômico quando declarado.
Durabilidade: Somente recursos de servidor declarados são duráveis; registros locais terminam no unload do package.
Ciclo de vida: O package deve estar instalado, habilitado e ativo; registros retornam um disposer.
Limite de segurança: Não expõe filesystem, database, transport, renderer, internals de ACL nem override de permissão.

### `items.read`

Status: `stable`
Tipos de package: `ruleset`, `addon`, `library`, `content`, `theme`, `assets`
Métodos: `sdk.items.get`, `sdk.items.list`
Eventos: [Eventos](#eventos)
Erros: `CAPABILITY_REQUIRED`, `PERMISSION_DENIED`, `NOT_FOUND`, `VALIDATION_FAILED`, `STALE_VERSION`, `UNKNOWN_ACTION`
Autoridade: Capability declarada mais autoridade do usuário atual sobre o recurso; capabilities nunca elevam permissões.
Visibilidade: Projeção do usuário atual; recursos ocultos são indistinguíveis de inexistentes.
Concorrência: Autoritativo no servidor; `expectedVersion` é compare-and-swap atômico quando declarado.
Durabilidade: Somente recursos de servidor declarados são duráveis; registros locais terminam no unload do package.
Ciclo de vida: O package deve estar instalado, habilitado e ativo; registros retornam um disposer.
Limite de segurança: Não expõe filesystem, database, transport, renderer, internals de ACL nem override de permissão.

### `items.register`

Status: `stable`
Tipos de package: `ruleset`, `addon`, `library`, `content`, `theme`, `assets`
Métodos: —
Eventos: [Eventos](#eventos)
Erros: `CAPABILITY_REQUIRED`, `PERMISSION_DENIED`, `NOT_FOUND`, `VALIDATION_FAILED`, `STALE_VERSION`, `UNKNOWN_ACTION`
Autoridade: Capability declarada mais autoridade do usuário atual sobre o recurso; capabilities nunca elevam permissões.
Visibilidade: Projeção do usuário atual; recursos ocultos são indistinguíveis de inexistentes.
Concorrência: Autoritativo no servidor; `expectedVersion` é compare-and-swap atômico quando declarado.
Durabilidade: Somente recursos de servidor declarados são duráveis; registros locais terminam no unload do package.
Ciclo de vida: O package deve estar instalado, habilitado e ativo; registros retornam um disposer.
Limite de segurança: Não expõe filesystem, database, transport, renderer, internals de ACL nem override de permissão.

### `items.write`

Status: `stable`
Tipos de package: `ruleset`, `addon`, `library`, `content`, `theme`, `assets`
Métodos: `sdk.items.create`, `sdk.items.update`, `sdk.items.delete`
Eventos: [Eventos](#eventos)
Erros: `CAPABILITY_REQUIRED`, `PERMISSION_DENIED`, `NOT_FOUND`, `VALIDATION_FAILED`, `STALE_VERSION`, `UNKNOWN_ACTION`
Autoridade: Capability declarada mais autoridade do usuário atual sobre o recurso; capabilities nunca elevam permissões.
Visibilidade: Projeção do usuário atual; recursos ocultos são indistinguíveis de inexistentes.
Concorrência: Autoritativo no servidor; `expectedVersion` é compare-and-swap atômico quando declarado.
Durabilidade: Somente recursos de servidor declarados são duráveis; registros locais terminam no unload do package.
Ciclo de vida: O package deve estar instalado, habilitado e ativo; registros retornam um disposer.
Limite de segurança: Não expõe filesystem, database, transport, renderer, internals de ACL nem override de permissão.

### `journals.read`

Status: `stable`
Tipos de package: `ruleset`, `addon`, `library`, `content`, `theme`, `assets`
Métodos: `sdk.journals.get`, `sdk.journals.list`
Eventos: [Eventos](#eventos)
Erros: `CAPABILITY_REQUIRED`, `PERMISSION_DENIED`, `NOT_FOUND`, `VALIDATION_FAILED`, `STALE_VERSION`, `UNKNOWN_ACTION`
Autoridade: Capability declarada mais autoridade do usuário atual sobre o recurso; capabilities nunca elevam permissões.
Visibilidade: Projeção do usuário atual; recursos ocultos são indistinguíveis de inexistentes.
Concorrência: Autoritativo no servidor; `expectedVersion` é compare-and-swap atômico quando declarado.
Durabilidade: Somente recursos de servidor declarados são duráveis; registros locais terminam no unload do package.
Ciclo de vida: O package deve estar instalado, habilitado e ativo; registros retornam um disposer.
Limite de segurança: Não expõe filesystem, database, transport, renderer, internals de ACL nem override de permissão.

### `journals.write`

Status: `stable`
Tipos de package: `ruleset`, `addon`, `library`, `content`, `theme`, `assets`
Métodos: `sdk.journals.create`, `sdk.journals.update`, `sdk.journals.delete`
Eventos: [Eventos](#eventos)
Erros: `CAPABILITY_REQUIRED`, `PERMISSION_DENIED`, `NOT_FOUND`, `VALIDATION_FAILED`, `STALE_VERSION`, `UNKNOWN_ACTION`
Autoridade: Capability declarada mais autoridade do usuário atual sobre o recurso; capabilities nunca elevam permissões.
Visibilidade: Projeção do usuário atual; recursos ocultos são indistinguíveis de inexistentes.
Concorrência: Autoritativo no servidor; `expectedVersion` é compare-and-swap atômico quando declarado.
Durabilidade: Somente recursos de servidor declarados são duráveis; registros locais terminam no unload do package.
Ciclo de vida: O package deve estar instalado, habilitado e ativo; registros retornam um disposer.
Limite de segurança: Não expõe filesystem, database, transport, renderer, internals de ACL nem override de permissão.

### `locales`

Status: `stable`
Tipos de package: `ruleset`, `addon`, `library`, `content`, `theme`, `assets`
Métodos: `sdk.i18n.t`
Eventos: [Eventos](#eventos)
Erros: `CAPABILITY_REQUIRED`, `PERMISSION_DENIED`, `NOT_FOUND`, `VALIDATION_FAILED`, `STALE_VERSION`, `UNKNOWN_ACTION`
Autoridade: Capability declarada mais autoridade do usuário atual sobre o recurso; capabilities nunca elevam permissões.
Visibilidade: Projeção do usuário atual; recursos ocultos são indistinguíveis de inexistentes.
Concorrência: Autoritativo no servidor; `expectedVersion` é compare-and-swap atômico quando declarado.
Durabilidade: Somente recursos de servidor declarados são duráveis; registros locais terminam no unload do package.
Ciclo de vida: O package deve estar instalado, habilitado e ativo; registros retornam um disposer.
Limite de segurança: Não expõe filesystem, database, transport, renderer, internals de ACL nem override de permissão.

### `packages.inspect`

Status: `stable`
Tipos de package: `ruleset`, `addon`, `library`, `content`, `theme`, `assets`
Métodos: `sdk.packages.get`, `sdk.packages.has`
Eventos: [Eventos](#eventos)
Erros: `CAPABILITY_REQUIRED`, `PERMISSION_DENIED`, `NOT_FOUND`, `VALIDATION_FAILED`, `STALE_VERSION`, `UNKNOWN_ACTION`
Autoridade: Capability declarada mais autoridade do usuário atual sobre o recurso; capabilities nunca elevam permissões.
Visibilidade: Projeção do usuário atual; recursos ocultos são indistinguíveis de inexistentes.
Concorrência: Autoritativo no servidor; `expectedVersion` é compare-and-swap atômico quando declarado.
Durabilidade: Somente recursos de servidor declarados são duráveis; registros locais terminam no unload do package.
Ciclo de vida: O package deve estar instalado, habilitado e ativo; registros retornam um disposer.
Limite de segurança: Não expõe filesystem, database, transport, renderer, internals de ACL nem override de permissão.

### `pdf.annotations.read`

Status: `stable`
Tipos de package: `ruleset`, `addon`, `library`, `content`, `theme`, `assets`
Métodos: `sdk.pdf.annotations.list`
Eventos: [Eventos](#eventos)
Erros: `CAPABILITY_REQUIRED`, `PERMISSION_DENIED`, `NOT_FOUND`, `VALIDATION_FAILED`, `STALE_VERSION`, `UNKNOWN_ACTION`
Autoridade: Capability declarada mais autoridade do usuário atual sobre o recurso; capabilities nunca elevam permissões.
Visibilidade: Projeção do usuário atual; recursos ocultos são indistinguíveis de inexistentes.
Concorrência: Autoritativo no servidor; `expectedVersion` é compare-and-swap atômico quando declarado.
Durabilidade: Somente recursos de servidor declarados são duráveis; registros locais terminam no unload do package.
Ciclo de vida: O package deve estar instalado, habilitado e ativo; registros retornam um disposer.
Limite de segurança: Não expõe filesystem, database, transport, renderer, internals de ACL nem override de permissão.

### `pdf.annotations.write`

Status: `stable`
Tipos de package: `ruleset`, `addon`, `library`, `content`, `theme`, `assets`
Métodos: `sdk.pdf.annotations.create`, `sdk.pdf.annotations.update`, `sdk.pdf.annotations.delete`
Eventos: [Eventos](#eventos)
Erros: `CAPABILITY_REQUIRED`, `PERMISSION_DENIED`, `NOT_FOUND`, `VALIDATION_FAILED`, `STALE_VERSION`, `UNKNOWN_ACTION`
Autoridade: Capability declarada mais autoridade do usuário atual sobre o recurso; capabilities nunca elevam permissões.
Visibilidade: Projeção do usuário atual; recursos ocultos são indistinguíveis de inexistentes.
Concorrência: Autoritativo no servidor; `expectedVersion` é compare-and-swap atômico quando declarado.
Durabilidade: Somente recursos de servidor declarados são duráveis; registros locais terminam no unload do package.
Ciclo de vida: O package deve estar instalado, habilitado e ativo; registros retornam um disposer.
Limite de segurança: Não expõe filesystem, database, transport, renderer, internals de ACL nem override de permissão.

### `pdf.presentation`

Status: `stable`
Tipos de package: `ruleset`, `addon`, `library`, `content`, `theme`, `assets`
Métodos: `sdk.pdf.presentation.start`, `sdk.pdf.presentation.current`, `sdk.pdf.presentation.update`, `sdk.pdf.presentation.end`
Eventos: [Eventos](#eventos)
Erros: `CAPABILITY_REQUIRED`, `PERMISSION_DENIED`, `NOT_FOUND`, `VALIDATION_FAILED`, `STALE_VERSION`, `UNKNOWN_ACTION`
Autoridade: Capability declarada mais autoridade do usuário atual sobre o recurso; capabilities nunca elevam permissões.
Visibilidade: Projeção do usuário atual; recursos ocultos são indistinguíveis de inexistentes.
Concorrência: Autoritativo no servidor; `expectedVersion` é compare-and-swap atômico quando declarado.
Durabilidade: Somente recursos de servidor declarados são duráveis; registros locais terminam no unload do package.
Ciclo de vida: O package deve estar instalado, habilitado e ativo; registros retornam um disposer.
Limite de segurança: Não expõe filesystem, database, transport, renderer, internals de ACL nem override de permissão.

### `pdf.read`

Status: `stable`
Tipos de package: `ruleset`, `addon`, `library`, `content`, `theme`, `assets`
Métodos: `sdk.pdf.get`, `sdk.pdf.metadata`
Eventos: [Eventos](#eventos)
Erros: `CAPABILITY_REQUIRED`, `PERMISSION_DENIED`, `NOT_FOUND`, `VALIDATION_FAILED`, `STALE_VERSION`, `UNKNOWN_ACTION`
Autoridade: Capability declarada mais autoridade do usuário atual sobre o recurso; capabilities nunca elevam permissões.
Visibilidade: Projeção do usuário atual; recursos ocultos são indistinguíveis de inexistentes.
Concorrência: Autoritativo no servidor; `expectedVersion` é compare-and-swap atômico quando declarado.
Durabilidade: Somente recursos de servidor declarados são duráveis; registros locais terminam no unload do package.
Ciclo de vida: O package deve estar instalado, habilitado e ativo; registros retornam um disposer.
Limite de segurança: Não expõe filesystem, database, transport, renderer, internals de ACL nem override de permissão.

### `pdf.viewer`

Status: `stable`
Tipos de package: `ruleset`, `addon`, `library`, `content`, `theme`, `assets`
Métodos: `sdk.pdf.viewer.open`, `sdk.pdf.viewer.goToPage`, `sdk.pdf.viewer.search`, `sdk.pdf.viewer.currentPage`
Eventos: [Eventos](#eventos)
Erros: `CAPABILITY_REQUIRED`, `PERMISSION_DENIED`, `NOT_FOUND`, `VALIDATION_FAILED`, `STALE_VERSION`, `UNKNOWN_ACTION`
Autoridade: Capability declarada mais autoridade do usuário atual sobre o recurso; capabilities nunca elevam permissões.
Visibilidade: Projeção do usuário atual; recursos ocultos são indistinguíveis de inexistentes.
Concorrência: Autoritativo no servidor; `expectedVersion` é compare-and-swap atômico quando declarado.
Durabilidade: Somente recursos de servidor declarados são duráveis; registros locais terminam no unload do package.
Ciclo de vida: O package deve estar instalado, habilitado e ativo; registros retornam um disposer.
Limite de segurança: Não expõe filesystem, database, transport, renderer, internals de ACL nem override de permissão.

### `permissions.inspect`

Status: `stable`
Tipos de package: `ruleset`, `addon`, `library`, `content`, `theme`, `assets`
Métodos: `sdk.permissions.can`, `sdk.permissions.check`
Eventos: [Eventos](#eventos)
Erros: `CAPABILITY_REQUIRED`, `PERMISSION_DENIED`, `NOT_FOUND`, `VALIDATION_FAILED`, `STALE_VERSION`, `UNKNOWN_ACTION`
Autoridade: Capability declarada mais autoridade do usuário atual sobre o recurso; capabilities nunca elevam permissões.
Visibilidade: Projeção do usuário atual; recursos ocultos são indistinguíveis de inexistentes.
Concorrência: Autoritativo no servidor; `expectedVersion` é compare-and-swap atômico quando declarado.
Durabilidade: Somente recursos de servidor declarados são duráveis; registros locais terminam no unload do package.
Ciclo de vida: O package deve estar instalado, habilitado e ativo; registros retornam um disposer.
Limite de segurança: Não expõe filesystem, database, transport, renderer, internals de ACL nem override de permissão.

### `rolls.intent`

Status: `stable`
Tipos de package: `ruleset`, `addon`, `library`, `content`, `theme`, `assets`
Métodos: `sdk.rolls.intent`
Eventos: [Eventos](#eventos)
Erros: `CAPABILITY_REQUIRED`, `PERMISSION_DENIED`, `NOT_FOUND`, `VALIDATION_FAILED`, `STALE_VERSION`, `UNKNOWN_ACTION`
Autoridade: Capability declarada mais autoridade do usuário atual sobre o recurso; capabilities nunca elevam permissões.
Visibilidade: Projeção do usuário atual; recursos ocultos são indistinguíveis de inexistentes.
Concorrência: Autoritativo no servidor; `expectedVersion` é compare-and-swap atômico quando declarado.
Durabilidade: Somente recursos de servidor declarados são duráveis; registros locais terminam no unload do package.
Ciclo de vida: O package deve estar instalado, habilitado e ativo; registros retornam um disposer.
Limite de segurança: Não expõe filesystem, database, transport, renderer, internals de ACL nem override de permissão.

### `rules.actions`

Status: `stable`
Tipos de package: `ruleset`, `addon`, `library`, `content`, `theme`, `assets`
Métodos: `sdk.rules.actions.list`, `sdk.rules.actions.get`, `sdk.rules.actions.resolve`, `sdk.rules.actions.execute`, `sdk.rules.actions.executeReference`
Eventos: [Eventos](#eventos)
Erros: `CAPABILITY_REQUIRED`, `PERMISSION_DENIED`, `NOT_FOUND`, `VALIDATION_FAILED`, `STALE_VERSION`, `UNKNOWN_ACTION`
Autoridade: Capability declarada mais autoridade do usuário atual sobre o recurso; capabilities nunca elevam permissões.
Visibilidade: Projeção do usuário atual; recursos ocultos são indistinguíveis de inexistentes.
Concorrência: Autoritativo no servidor; `expectedVersion` é compare-and-swap atômico quando declarado.
Durabilidade: Somente recursos de servidor declarados são duráveis; registros locais terminam no unload do package.
Ciclo de vida: O package deve estar instalado, habilitado e ativo; registros retornam um disposer.
Limite de segurança: Não expõe filesystem, database, transport, renderer, internals de ACL nem override de permissão.

### `rules.declarative`

Status: `stable`
Tipos de package: `ruleset`, `addon`, `library`, `content`, `theme`, `assets`
Métodos: —
Eventos: [Eventos](#eventos)
Erros: `CAPABILITY_REQUIRED`, `PERMISSION_DENIED`, `NOT_FOUND`, `VALIDATION_FAILED`, `STALE_VERSION`, `UNKNOWN_ACTION`
Autoridade: Capability declarada mais autoridade do usuário atual sobre o recurso; capabilities nunca elevam permissões.
Visibilidade: Projeção do usuário atual; recursos ocultos são indistinguíveis de inexistentes.
Concorrência: Autoritativo no servidor; `expectedVersion` é compare-and-swap atômico quando declarado.
Durabilidade: Somente recursos de servidor declarados são duráveis; registros locais terminam no unload do package.
Ciclo de vida: O package deve estar instalado, habilitado e ativo; registros retornam um disposer.
Limite de segurança: Não expõe filesystem, database, transport, renderer, internals de ACL nem override de permissão.

### `rules.extends`

Status: `stable`
Tipos de package: `ruleset`, `addon`, `library`, `content`, `theme`, `assets`
Métodos: —
Eventos: [Eventos](#eventos)
Erros: `CAPABILITY_REQUIRED`, `PERMISSION_DENIED`, `NOT_FOUND`, `VALIDATION_FAILED`, `STALE_VERSION`, `UNKNOWN_ACTION`
Autoridade: Capability declarada mais autoridade do usuário atual sobre o recurso; capabilities nunca elevam permissões.
Visibilidade: Projeção do usuário atual; recursos ocultos são indistinguíveis de inexistentes.
Concorrência: Autoritativo no servidor; `expectedVersion` é compare-and-swap atômico quando declarado.
Durabilidade: Somente recursos de servidor declarados são duráveis; registros locais terminam no unload do package.
Ciclo de vida: O package deve estar instalado, habilitado e ativo; registros retornam um disposer.
Limite de segurança: Não expõe filesystem, database, transport, renderer, internals de ACL nem override de permissão.

### `scene.effects.read`

Status: `stable`
Tipos de package: `ruleset`, `addon`, `library`, `content`, `theme`, `assets`
Métodos: `sdk.scene.effects.list`, `sdk.scene.effects.presets`
Eventos: [Eventos](#eventos)
Erros: `CAPABILITY_REQUIRED`, `PERMISSION_DENIED`, `NOT_FOUND`, `VALIDATION_FAILED`, `STALE_VERSION`, `UNKNOWN_ACTION`
Autoridade: Capability declarada mais autoridade do usuário atual sobre o recurso; capabilities nunca elevam permissões.
Visibilidade: Projeção do usuário atual; recursos ocultos são indistinguíveis de inexistentes.
Concorrência: Autoritativo no servidor; `expectedVersion` é compare-and-swap atômico quando declarado.
Durabilidade: Somente recursos de servidor declarados são duráveis; registros locais terminam no unload do package.
Ciclo de vida: O package deve estar instalado, habilitado e ativo; registros retornam um disposer.
Limite de segurança: Não expõe filesystem, database, transport, renderer, internals de ACL nem override de permissão.

### `scene.effects.write`

Status: `stable`
Tipos de package: `ruleset`, `addon`, `library`, `content`, `theme`, `assets`
Métodos: `sdk.scene.effects.create`, `sdk.scene.effects.update`, `sdk.scene.effects.delete`
Eventos: [Eventos](#eventos)
Erros: `CAPABILITY_REQUIRED`, `PERMISSION_DENIED`, `NOT_FOUND`, `VALIDATION_FAILED`, `STALE_VERSION`, `UNKNOWN_ACTION`
Autoridade: Capability declarada mais autoridade do usuário atual sobre o recurso; capabilities nunca elevam permissões.
Visibilidade: Projeção do usuário atual; recursos ocultos são indistinguíveis de inexistentes.
Concorrência: Autoritativo no servidor; `expectedVersion` é compare-and-swap atômico quando declarado.
Durabilidade: Somente recursos de servidor declarados são duráveis; registros locais terminam no unload do package.
Ciclo de vida: O package deve estar instalado, habilitado e ativo; registros retornam um disposer.
Limite de segurança: Não expõe filesystem, database, transport, renderer, internals de ACL nem override de permissão.

### `scene.fog.read`

Status: `stable`
Tipos de package: `ruleset`, `addon`, `library`, `content`, `theme`, `assets`
Métodos: `sdk.scene.fog.state`
Eventos: [Eventos](#eventos)
Erros: `CAPABILITY_REQUIRED`, `PERMISSION_DENIED`, `NOT_FOUND`, `VALIDATION_FAILED`, `STALE_VERSION`, `UNKNOWN_ACTION`
Autoridade: Capability declarada mais autoridade do usuário atual sobre o recurso; capabilities nunca elevam permissões.
Visibilidade: Projeção do usuário atual; recursos ocultos são indistinguíveis de inexistentes.
Concorrência: Autoritativo no servidor; `expectedVersion` é compare-and-swap atômico quando declarado.
Durabilidade: Somente recursos de servidor declarados são duráveis; registros locais terminam no unload do package.
Ciclo de vida: O package deve estar instalado, habilitado e ativo; registros retornam um disposer.
Limite de segurança: Não expõe filesystem, database, transport, renderer, internals de ACL nem override de permissão.

### `scene.fog.write`

Status: `stable`
Tipos de package: `ruleset`, `addon`, `library`, `content`, `theme`, `assets`
Métodos: `sdk.scene.fog.enable`, `sdk.scene.fog.disable`, `sdk.scene.fog.reset`, `sdk.scene.fog.paint`
Eventos: [Eventos](#eventos)
Erros: `CAPABILITY_REQUIRED`, `PERMISSION_DENIED`, `NOT_FOUND`, `VALIDATION_FAILED`, `STALE_VERSION`, `UNKNOWN_ACTION`
Autoridade: Capability declarada mais autoridade do usuário atual sobre o recurso; capabilities nunca elevam permissões.
Visibilidade: Projeção do usuário atual; recursos ocultos são indistinguíveis de inexistentes.
Concorrência: Autoritativo no servidor; `expectedVersion` é compare-and-swap atômico quando declarado.
Durabilidade: Somente recursos de servidor declarados são duráveis; registros locais terminam no unload do package.
Ciclo de vida: O package deve estar instalado, habilitado e ativo; registros retornam um disposer.
Limite de segurança: Não expõe filesystem, database, transport, renderer, internals de ACL nem override de permissão.

### `scene.geometry.read`

Status: `stable`
Tipos de package: `ruleset`, `addon`, `library`, `content`, `theme`, `assets`
Métodos: `sdk.scene.geometry.walls`, `sdk.scene.geometry.lights`
Eventos: [Eventos](#eventos)
Erros: `CAPABILITY_REQUIRED`, `PERMISSION_DENIED`, `NOT_FOUND`, `VALIDATION_FAILED`, `STALE_VERSION`, `UNKNOWN_ACTION`
Autoridade: Capability declarada mais autoridade do usuário atual sobre o recurso; capabilities nunca elevam permissões.
Visibilidade: Projeção do usuário atual; recursos ocultos são indistinguíveis de inexistentes.
Concorrência: Autoritativo no servidor; `expectedVersion` é compare-and-swap atômico quando declarado.
Durabilidade: Somente recursos de servidor declarados são duráveis; registros locais terminam no unload do package.
Ciclo de vida: O package deve estar instalado, habilitado e ativo; registros retornam um disposer.
Limite de segurança: Não expõe filesystem, database, transport, renderer, internals de ACL nem override de permissão.

### `scene.geometry.write`

Status: `stable`
Tipos de package: `ruleset`, `addon`, `library`, `content`, `theme`, `assets`
Métodos: `sdk.scene.geometry.createWall`, `sdk.scene.geometry.updateWall`, `sdk.scene.geometry.deleteWall`, `sdk.scene.geometry.splitWall`, `sdk.scene.geometry.moveWallNode`, `sdk.scene.geometry.moveWalls`, `sdk.scene.geometry.deleteWalls`, `sdk.scene.geometry.createLight`, `sdk.scene.geometry.updateLight`, `sdk.scene.geometry.deleteLight`, `sdk.scene.geometry.setDoorState`
Eventos: [Eventos](#eventos)
Erros: `CAPABILITY_REQUIRED`, `PERMISSION_DENIED`, `NOT_FOUND`, `VALIDATION_FAILED`, `STALE_VERSION`, `UNKNOWN_ACTION`
Autoridade: Capability declarada mais autoridade do usuário atual sobre o recurso; capabilities nunca elevam permissões.
Visibilidade: Projeção do usuário atual; recursos ocultos são indistinguíveis de inexistentes.
Concorrência: Autoritativo no servidor; `expectedVersion` é compare-and-swap atômico quando declarado.
Durabilidade: Somente recursos de servidor declarados são duráveis; registros locais terminam no unload do package.
Ciclo de vida: O package deve estar instalado, habilitado e ativo; registros retornam um disposer.
Limite de segurança: Não expõe filesystem, database, transport, renderer, internals de ACL nem override de permissão.

### `scene.images.read`

Status: `stable`
Tipos de package: `ruleset`, `addon`, `library`, `content`, `theme`, `assets`
Métodos: `sdk.scene.images.list`
Eventos: [Eventos](#eventos)
Erros: `CAPABILITY_REQUIRED`, `PERMISSION_DENIED`, `NOT_FOUND`, `VALIDATION_FAILED`, `STALE_VERSION`, `UNKNOWN_ACTION`
Autoridade: Capability declarada mais autoridade do usuário atual sobre o recurso; capabilities nunca elevam permissões.
Visibilidade: Projeção do usuário atual; recursos ocultos são indistinguíveis de inexistentes.
Concorrência: Autoritativo no servidor; `expectedVersion` é compare-and-swap atômico quando declarado.
Durabilidade: Somente recursos de servidor declarados são duráveis; registros locais terminam no unload do package.
Ciclo de vida: O package deve estar instalado, habilitado e ativo; registros retornam um disposer.
Limite de segurança: Não expõe filesystem, database, transport, renderer, internals de ACL nem override de permissão.

### `scene.images.write`

Status: `stable`
Tipos de package: `ruleset`, `addon`, `library`, `content`, `theme`, `assets`
Métodos: `sdk.scene.images.place`, `sdk.scene.images.update`, `sdk.scene.images.delete`
Eventos: [Eventos](#eventos)
Erros: `CAPABILITY_REQUIRED`, `PERMISSION_DENIED`, `NOT_FOUND`, `VALIDATION_FAILED`, `STALE_VERSION`, `UNKNOWN_ACTION`
Autoridade: Capability declarada mais autoridade do usuário atual sobre o recurso; capabilities nunca elevam permissões.
Visibilidade: Projeção do usuário atual; recursos ocultos são indistinguíveis de inexistentes.
Concorrência: Autoritativo no servidor; `expectedVersion` é compare-and-swap atômico quando declarado.
Durabilidade: Somente recursos de servidor declarados são duráveis; registros locais terminam no unload do package.
Ciclo de vida: O package deve estar instalado, habilitado e ativo; registros retornam um disposer.
Limite de segurança: Não expõe filesystem, database, transport, renderer, internals de ACL nem override de permissão.

### `scene.measurements.shared`

Status: `stable`
Tipos de package: `ruleset`, `addon`, `library`, `content`, `theme`, `assets`
Métodos: `sdk.scene.measurements.share`, `sdk.scene.measurements.listShared`, `sdk.scene.measurements.cancel`
Eventos: [Eventos](#eventos)
Erros: `CAPABILITY_REQUIRED`, `PERMISSION_DENIED`, `NOT_FOUND`, `VALIDATION_FAILED`, `STALE_VERSION`, `UNKNOWN_ACTION`
Autoridade: Capability declarada mais autoridade do usuário atual sobre o recurso; capabilities nunca elevam permissões.
Visibilidade: Projeção do usuário atual; recursos ocultos são indistinguíveis de inexistentes.
Concorrência: Autoritativo no servidor; `expectedVersion` é compare-and-swap atômico quando declarado.
Durabilidade: Somente recursos de servidor declarados são duráveis; registros locais terminam no unload do package.
Ciclo de vida: O package deve estar instalado, habilitado e ativo; registros retornam um disposer.
Limite de segurança: Não expõe filesystem, database, transport, renderer, internals de ACL nem override de permissão.

### `scene.overlays`

Status: `stable`
Tipos de package: `ruleset`, `addon`, `library`, `content`, `theme`, `assets`
Métodos: —
Eventos: [Eventos](#eventos)
Erros: `CAPABILITY_REQUIRED`, `PERMISSION_DENIED`, `NOT_FOUND`, `VALIDATION_FAILED`, `STALE_VERSION`, `UNKNOWN_ACTION`
Autoridade: Capability declarada mais autoridade do usuário atual sobre o recurso; capabilities nunca elevam permissões.
Visibilidade: Projeção do usuário atual; recursos ocultos são indistinguíveis de inexistentes.
Concorrência: Autoritativo no servidor; `expectedVersion` é compare-and-swap atômico quando declarado.
Durabilidade: Somente recursos de servidor declarados são duráveis; registros locais terminam no unload do package.
Ciclo de vida: O package deve estar instalado, habilitado e ativo; registros retornam um disposer.
Limite de segurança: Não expõe filesystem, database, transport, renderer, internals de ACL nem override de permissão.

### `scene.read`

Status: `stable`
Tipos de package: `ruleset`, `addon`, `library`, `content`, `theme`, `assets`
Métodos: `sdk.scene.get`, `sdk.scene.list`, `sdk.scene.active`
Eventos: [Eventos](#eventos)
Erros: `CAPABILITY_REQUIRED`, `PERMISSION_DENIED`, `NOT_FOUND`, `VALIDATION_FAILED`, `STALE_VERSION`, `UNKNOWN_ACTION`
Autoridade: Capability declarada mais autoridade do usuário atual sobre o recurso; capabilities nunca elevam permissões.
Visibilidade: Projeção do usuário atual; recursos ocultos são indistinguíveis de inexistentes.
Concorrência: Autoritativo no servidor; `expectedVersion` é compare-and-swap atômico quando declarado.
Durabilidade: Somente recursos de servidor declarados são duráveis; registros locais terminam no unload do package.
Ciclo de vida: O package deve estar instalado, habilitado e ativo; registros retornam um disposer.
Limite de segurança: Não expõe filesystem, database, transport, renderer, internals de ACL nem override de permissão.

### `scene.shaders.read`

Status: `stable`
Tipos de package: `ruleset`, `addon`, `library`, `content`, `theme`, `assets`
Métodos: `sdk.scene.shaders.presets`, `sdk.scene.shaders.getPreset`, `sdk.scene.shaders.list`
Eventos: [Eventos](#eventos)
Erros: `CAPABILITY_REQUIRED`, `PERMISSION_DENIED`, `NOT_FOUND`, `VALIDATION_FAILED`, `STALE_VERSION`, `UNKNOWN_ACTION`
Autoridade: Capability declarada mais autoridade do usuário atual sobre o recurso; capabilities nunca elevam permissões.
Visibilidade: Projeção do usuário atual; recursos ocultos são indistinguíveis de inexistentes.
Concorrência: Autoritativo no servidor; `expectedVersion` é compare-and-swap atômico quando declarado.
Durabilidade: Somente recursos de servidor declarados são duráveis; registros locais terminam no unload do package.
Ciclo de vida: O package deve estar instalado, habilitado e ativo; registros retornam um disposer.
Limite de segurança: Não expõe filesystem, database, transport, renderer, internals de ACL nem override de permissão.

### `scene.shaders.write`

Status: `stable`
Tipos de package: `ruleset`, `addon`, `library`, `content`, `theme`, `assets`
Métodos: `sdk.scene.shaders.apply`, `sdk.scene.shaders.update`, `sdk.scene.shaders.enable`, `sdk.scene.shaders.remove`
Eventos: [Eventos](#eventos)
Erros: `CAPABILITY_REQUIRED`, `PERMISSION_DENIED`, `NOT_FOUND`, `VALIDATION_FAILED`, `STALE_VERSION`, `UNKNOWN_ACTION`
Autoridade: Capability declarada mais autoridade do usuário atual sobre o recurso; capabilities nunca elevam permissões.
Visibilidade: Projeção do usuário atual; recursos ocultos são indistinguíveis de inexistentes.
Concorrência: Autoritativo no servidor; `expectedVersion` é compare-and-swap atômico quando declarado.
Durabilidade: Somente recursos de servidor declarados são duráveis; registros locais terminam no unload do package.
Ciclo de vida: O package deve estar instalado, habilitado e ativo; registros retornam um disposer.
Limite de segurança: Não expõe filesystem, database, transport, renderer, internals de ACL nem override de permissão.

### `scene.templates.read`

Status: `stable`
Tipos de package: `ruleset`, `addon`, `library`, `content`, `theme`, `assets`
Métodos: `sdk.scene.templates.list`, `sdk.scene.templates.get`
Eventos: [Eventos](#eventos)
Erros: `CAPABILITY_REQUIRED`, `PERMISSION_DENIED`, `NOT_FOUND`, `VALIDATION_FAILED`, `STALE_VERSION`, `UNKNOWN_ACTION`
Autoridade: Capability declarada mais autoridade do usuário atual sobre o recurso; capabilities nunca elevam permissões.
Visibilidade: Projeção do usuário atual; recursos ocultos são indistinguíveis de inexistentes.
Concorrência: Autoritativo no servidor; `expectedVersion` é compare-and-swap atômico quando declarado.
Durabilidade: Somente recursos de servidor declarados são duráveis; registros locais terminam no unload do package.
Ciclo de vida: O package deve estar instalado, habilitado e ativo; registros retornam um disposer.
Limite de segurança: Não expõe filesystem, database, transport, renderer, internals de ACL nem override de permissão.

### `scene.templates.write`

Status: `stable`
Tipos de package: `ruleset`, `addon`, `library`, `content`, `theme`, `assets`
Métodos: `sdk.scene.templates.create`, `sdk.scene.templates.update`, `sdk.scene.templates.delete`
Eventos: [Eventos](#eventos)
Erros: `CAPABILITY_REQUIRED`, `PERMISSION_DENIED`, `NOT_FOUND`, `VALIDATION_FAILED`, `STALE_VERSION`, `UNKNOWN_ACTION`
Autoridade: Capability declarada mais autoridade do usuário atual sobre o recurso; capabilities nunca elevam permissões.
Visibilidade: Projeção do usuário atual; recursos ocultos são indistinguíveis de inexistentes.
Concorrência: Autoritativo no servidor; `expectedVersion` é compare-and-swap atômico quando declarado.
Durabilidade: Somente recursos de servidor declarados são duráveis; registros locais terminam no unload do package.
Ciclo de vida: O package deve estar instalado, habilitado e ativo; registros retornam um disposer.
Limite de segurança: Não expõe filesystem, database, transport, renderer, internals de ACL nem override de permissão.

### `scene.tools`

Status: `stable`
Tipos de package: `ruleset`, `addon`, `library`, `content`, `theme`, `assets`
Métodos: `sdk.scene.activeCanvas`, `sdk.scene.activeCameraForScene`, `sdk.tools.activeTool`, `sdk.tools.register`, `sdk.scene.measurements.measure`
Eventos: [Eventos](#eventos)
Erros: `CAPABILITY_REQUIRED`, `PERMISSION_DENIED`, `NOT_FOUND`, `VALIDATION_FAILED`, `STALE_VERSION`, `UNKNOWN_ACTION`
Autoridade: Capability declarada mais autoridade do usuário atual sobre o recurso; capabilities nunca elevam permissões.
Visibilidade: Projeção do usuário atual; recursos ocultos são indistinguíveis de inexistentes.
Concorrência: Autoritativo no servidor; `expectedVersion` é compare-and-swap atômico quando declarado.
Durabilidade: Somente recursos de servidor declarados são duráveis; registros locais terminam no unload do package.
Ciclo de vida: O package deve estar instalado, habilitado e ativo; registros retornam um disposer.
Limite de segurança: Não expõe filesystem, database, transport, renderer, internals de ACL nem override de permissão.

### `settings`

Status: `stable`
Tipos de package: `ruleset`, `addon`, `library`, `content`, `theme`, `assets`
Métodos: `sdk.settings.definitions`, `sdk.settings.all`, `sdk.settings.get`, `sdk.settings.set`, `sdk.settings.scope`, `sdk.settings.onChange`
Eventos: [Eventos](#eventos)
Erros: `CAPABILITY_REQUIRED`, `PERMISSION_DENIED`, `NOT_FOUND`, `VALIDATION_FAILED`, `STALE_VERSION`, `UNKNOWN_ACTION`
Autoridade: Capability declarada mais autoridade do usuário atual sobre o recurso; capabilities nunca elevam permissões.
Visibilidade: Projeção do usuário atual; recursos ocultos são indistinguíveis de inexistentes.
Concorrência: Autoritativo no servidor; `expectedVersion` é compare-and-swap atômico quando declarado.
Durabilidade: Somente recursos de servidor declarados são duráveis; registros locais terminam no unload do package.
Ciclo de vida: O package deve estar instalado, habilitado e ativo; registros retornam um disposer.
Limite de segurança: Não expõe filesystem, database, transport, renderer, internals de ACL nem override de permissão.

### `sheets.components`

Status: `stable`
Tipos de package: `ruleset`, `addon`, `library`, `content`, `theme`, `assets`
Métodos: —
Eventos: [Eventos](#eventos)
Erros: `CAPABILITY_REQUIRED`, `PERMISSION_DENIED`, `NOT_FOUND`, `VALIDATION_FAILED`, `STALE_VERSION`, `UNKNOWN_ACTION`
Autoridade: Capability declarada mais autoridade do usuário atual sobre o recurso; capabilities nunca elevam permissões.
Visibilidade: Projeção do usuário atual; recursos ocultos são indistinguíveis de inexistentes.
Concorrência: Autoritativo no servidor; `expectedVersion` é compare-and-swap atômico quando declarado.
Durabilidade: Somente recursos de servidor declarados são duráveis; registros locais terminam no unload do package.
Ciclo de vida: O package deve estar instalado, habilitado e ativo; registros retornam um disposer.
Limite de segurança: Não expõe filesystem, database, transport, renderer, internals de ACL nem override de permissão.

### `sheets.controller`

Status: `stable`
Tipos de package: `ruleset`, `addon`, `library`, `content`, `theme`, `assets`
Métodos: `sdk.sheets.registerController`
Eventos: [Eventos](#eventos)
Erros: `CAPABILITY_REQUIRED`, `PERMISSION_DENIED`, `NOT_FOUND`, `VALIDATION_FAILED`, `STALE_VERSION`, `UNKNOWN_ACTION`
Autoridade: Capability declarada mais autoridade do usuário atual sobre o recurso; capabilities nunca elevam permissões.
Visibilidade: Projeção do usuário atual; recursos ocultos são indistinguíveis de inexistentes.
Concorrência: Autoritativo no servidor; `expectedVersion` é compare-and-swap atômico quando declarado.
Durabilidade: Somente recursos de servidor declarados são duráveis; registros locais terminam no unload do package.
Ciclo de vida: O package deve estar instalado, habilitado e ativo; registros retornam um disposer.
Limite de segurança: Não expõe filesystem, database, transport, renderer, internals de ACL nem override de permissão.

### `sheets.declarative`

Status: `stable`
Tipos de package: `ruleset`, `addon`, `library`, `content`, `theme`, `assets`
Métodos: —
Eventos: [Eventos](#eventos)
Erros: `CAPABILITY_REQUIRED`, `PERMISSION_DENIED`, `NOT_FOUND`, `VALIDATION_FAILED`, `STALE_VERSION`, `UNKNOWN_ACTION`
Autoridade: Capability declarada mais autoridade do usuário atual sobre o recurso; capabilities nunca elevam permissões.
Visibilidade: Projeção do usuário atual; recursos ocultos são indistinguíveis de inexistentes.
Concorrência: Autoritativo no servidor; `expectedVersion` é compare-and-swap atômico quando declarado.
Durabilidade: Somente recursos de servidor declarados são duráveis; registros locais terminam no unload do package.
Ciclo de vida: O package deve estar instalado, habilitado e ativo; registros retornam um disposer.
Limite de segurança: Não expõe filesystem, database, transport, renderer, internals de ACL nem override de permissão.

### `sheets.html`

Status: `stable`
Tipos de package: `ruleset`, `addon`, `library`, `content`, `theme`, `assets`
Métodos: —
Eventos: [Eventos](#eventos)
Erros: `CAPABILITY_REQUIRED`, `PERMISSION_DENIED`, `NOT_FOUND`, `VALIDATION_FAILED`, `STALE_VERSION`, `UNKNOWN_ACTION`
Autoridade: Capability declarada mais autoridade do usuário atual sobre o recurso; capabilities nunca elevam permissões.
Visibilidade: Projeção do usuário atual; recursos ocultos são indistinguíveis de inexistentes.
Concorrência: Autoritativo no servidor; `expectedVersion` é compare-and-swap atômico quando declarado.
Durabilidade: Somente recursos de servidor declarados são duráveis; registros locais terminam no unload do package.
Ciclo de vida: O package deve estar instalado, habilitado e ativo; registros retornam um disposer.
Limite de segurança: Não expõe filesystem, database, transport, renderer, internals de ACL nem override de permissão.

### `sheets.richText`

Status: `stable`
Tipos de package: `ruleset`, `addon`, `library`, `content`, `theme`, `assets`
Métodos: —
Eventos: [Eventos](#eventos)
Erros: `CAPABILITY_REQUIRED`, `PERMISSION_DENIED`, `NOT_FOUND`, `VALIDATION_FAILED`, `STALE_VERSION`, `UNKNOWN_ACTION`
Autoridade: Capability declarada mais autoridade do usuário atual sobre o recurso; capabilities nunca elevam permissões.
Visibilidade: Projeção do usuário atual; recursos ocultos são indistinguíveis de inexistentes.
Concorrência: Autoritativo no servidor; `expectedVersion` é compare-and-swap atômico quando declarado.
Durabilidade: Somente recursos de servidor declarados são duráveis; registros locais terminam no unload do package.
Ciclo de vida: O package deve estar instalado, habilitado e ativo; registros retornam um disposer.
Limite de segurança: Não expõe filesystem, database, transport, renderer, internals de ACL nem override de permissão.

### `sheets.runtime`

Status: `stable`
Tipos de package: `ruleset`, `addon`, `library`, `content`, `theme`, `assets`
Métodos: `sdk.sheets.helpers`, `sdk.sheets.register`
Eventos: [Eventos](#eventos)
Erros: `CAPABILITY_REQUIRED`, `PERMISSION_DENIED`, `NOT_FOUND`, `VALIDATION_FAILED`, `STALE_VERSION`, `UNKNOWN_ACTION`
Autoridade: Capability declarada mais autoridade do usuário atual sobre o recurso; capabilities nunca elevam permissões.
Visibilidade: Projeção do usuário atual; recursos ocultos são indistinguíveis de inexistentes.
Concorrência: Autoritativo no servidor; `expectedVersion` é compare-and-swap atômico quando declarado.
Durabilidade: Somente recursos de servidor declarados são duráveis; registros locais terminam no unload do package.
Ciclo de vida: O package deve estar instalado, habilitado e ativo; registros retornam um disposer.
Limite de segurança: Não expõe filesystem, database, transport, renderer, internals de ACL nem override de permissão.

### `storage.sqlite`

Status: `stable`
Tipos de package: `ruleset`, `addon`, `library`, `content`, `theme`, `assets`
Métodos: `sdk.storage.sqlite.query`, `sdk.storage.sqlite.execute`, `sdk.storage.sqlite.status`
Eventos: [Eventos](#eventos)
Erros: `CAPABILITY_REQUIRED`, `PERMISSION_DENIED`, `NOT_FOUND`, `VALIDATION_FAILED`, `STALE_VERSION`, `UNKNOWN_ACTION`
Autoridade: Capability declarada mais autoridade do usuário atual sobre o recurso; capabilities nunca elevam permissões.
Visibilidade: Projeção do usuário atual; recursos ocultos são indistinguíveis de inexistentes.
Concorrência: Autoritativo no servidor; `expectedVersion` é compare-and-swap atômico quando declarado.
Durabilidade: Somente recursos de servidor declarados são duráveis; registros locais terminam no unload do package.
Ciclo de vida: O package deve estar instalado, habilitado e ativo; registros retornam um disposer.
Limite de segurança: Não expõe filesystem, database, transport, renderer, internals de ACL nem override de permissão.

### `tokens.extends`

Status: `stable`
Tipos de package: `ruleset`, `addon`, `library`, `content`, `theme`, `assets`
Métodos: `sdk.tokens.centerOn`
Eventos: [Eventos](#eventos)
Erros: `CAPABILITY_REQUIRED`, `PERMISSION_DENIED`, `NOT_FOUND`, `VALIDATION_FAILED`, `STALE_VERSION`, `UNKNOWN_ACTION`
Autoridade: Capability declarada mais autoridade do usuário atual sobre o recurso; capabilities nunca elevam permissões.
Visibilidade: Projeção do usuário atual; recursos ocultos são indistinguíveis de inexistentes.
Concorrência: Autoritativo no servidor; `expectedVersion` é compare-and-swap atômico quando declarado.
Durabilidade: Somente recursos de servidor declarados são duráveis; registros locais terminam no unload do package.
Ciclo de vida: O package deve estar instalado, habilitado e ativo; registros retornam um disposer.
Limite de segurança: Não expõe filesystem, database, transport, renderer, internals de ACL nem override de permissão.

### `tokens.manage`

Status: `stable`
Tipos de package: `ruleset`, `addon`, `library`, `content`, `theme`, `assets`
Métodos: `sdk.tokens.create`, `sdk.tokens.update`, `sdk.tokens.delete`
Eventos: [Eventos](#eventos)
Erros: `CAPABILITY_REQUIRED`, `PERMISSION_DENIED`, `NOT_FOUND`, `VALIDATION_FAILED`, `STALE_VERSION`, `UNKNOWN_ACTION`
Autoridade: Capability declarada mais autoridade do usuário atual sobre o recurso; capabilities nunca elevam permissões.
Visibilidade: Projeção do usuário atual; recursos ocultos são indistinguíveis de inexistentes.
Concorrência: Autoritativo no servidor; `expectedVersion` é compare-and-swap atômico quando declarado.
Durabilidade: Somente recursos de servidor declarados são duráveis; registros locais terminam no unload do package.
Ciclo de vida: O package deve estar instalado, habilitado e ativo; registros retornam um disposer.
Limite de segurança: Não expõe filesystem, database, transport, renderer, internals de ACL nem override de permissão.

### `tokens.mappings`

Status: `stable`
Tipos de package: `ruleset`, `addon`, `library`, `content`, `theme`, `assets`
Métodos: —
Eventos: [Eventos](#eventos)
Erros: `CAPABILITY_REQUIRED`, `PERMISSION_DENIED`, `NOT_FOUND`, `VALIDATION_FAILED`, `STALE_VERSION`, `UNKNOWN_ACTION`
Autoridade: Capability declarada mais autoridade do usuário atual sobre o recurso; capabilities nunca elevam permissões.
Visibilidade: Projeção do usuário atual; recursos ocultos são indistinguíveis de inexistentes.
Concorrência: Autoritativo no servidor; `expectedVersion` é compare-and-swap atômico quando declarado.
Durabilidade: Somente recursos de servidor declarados são duráveis; registros locais terminam no unload do package.
Ciclo de vida: O package deve estar instalado, habilitado e ativo; registros retornam um disposer.
Limite de segurança: Não expõe filesystem, database, transport, renderer, internals de ACL nem override de permissão.

### `tokens.move`

Status: `stable`
Tipos de package: `ruleset`, `addon`, `library`, `content`, `theme`, `assets`
Métodos: `sdk.tokens.move`
Eventos: [Eventos](#eventos)
Erros: `CAPABILITY_REQUIRED`, `PERMISSION_DENIED`, `NOT_FOUND`, `VALIDATION_FAILED`, `STALE_VERSION`, `UNKNOWN_ACTION`
Autoridade: Capability declarada mais autoridade do usuário atual sobre o recurso; capabilities nunca elevam permissões.
Visibilidade: Projeção do usuário atual; recursos ocultos são indistinguíveis de inexistentes.
Concorrência: Autoritativo no servidor; `expectedVersion` é compare-and-swap atômico quando declarado.
Durabilidade: Somente recursos de servidor declarados são duráveis; registros locais terminam no unload do package.
Ciclo de vida: O package deve estar instalado, habilitado e ativo; registros retornam um disposer.
Limite de segurança: Não expõe filesystem, database, transport, renderer, internals de ACL nem override de permissão.

### `tokens.read`

Status: `stable`
Tipos de package: `ruleset`, `addon`, `library`, `content`, `theme`, `assets`
Métodos: `sdk.tokens.get`, `sdk.tokens.list`
Eventos: [Eventos](#eventos)
Erros: `CAPABILITY_REQUIRED`, `PERMISSION_DENIED`, `NOT_FOUND`, `VALIDATION_FAILED`, `STALE_VERSION`, `UNKNOWN_ACTION`
Autoridade: Capability declarada mais autoridade do usuário atual sobre o recurso; capabilities nunca elevam permissões.
Visibilidade: Projeção do usuário atual; recursos ocultos são indistinguíveis de inexistentes.
Concorrência: Autoritativo no servidor; `expectedVersion` é compare-and-swap atômico quando declarado.
Durabilidade: Somente recursos de servidor declarados são duráveis; registros locais terminam no unload do package.
Ciclo de vida: O package deve estar instalado, habilitado e ativo; registros retornam um disposer.
Limite de segurança: Não expõe filesystem, database, transport, renderer, internals de ACL nem override de permissão.

### `tokens.targets`

Status: `stable`
Tipos de package: `ruleset`, `addon`, `library`, `content`, `theme`, `assets`
Métodos: `sdk.tokens.targets.list`, `sdk.tokens.targets.set`, `sdk.tokens.targets.clear`
Eventos: [Eventos](#eventos)
Erros: `CAPABILITY_REQUIRED`, `PERMISSION_DENIED`, `NOT_FOUND`, `VALIDATION_FAILED`, `STALE_VERSION`, `UNKNOWN_ACTION`
Autoridade: Capability declarada mais autoridade do usuário atual sobre o recurso; capabilities nunca elevam permissões.
Visibilidade: Projeção do usuário atual; recursos ocultos são indistinguíveis de inexistentes.
Concorrência: Autoritativo no servidor; `expectedVersion` é compare-and-swap atômico quando declarado.
Durabilidade: Somente recursos de servidor declarados são duráveis; registros locais terminam no unload do package.
Ciclo de vida: O package deve estar instalado, habilitado e ativo; registros retornam um disposer.
Limite de segurança: Não expõe filesystem, database, transport, renderer, internals de ACL nem override de permissão.

### `ui.applications`

Status: `stable`
Tipos de package: `ruleset`, `addon`, `library`, `content`, `theme`, `assets`
Métodos: `sdk.ui.applications.register`, `sdk.ui.applications.render`, `sdk.ui.applications.close`
Eventos: [Eventos](#eventos)
Erros: `CAPABILITY_REQUIRED`, `PERMISSION_DENIED`, `NOT_FOUND`, `VALIDATION_FAILED`, `STALE_VERSION`, `UNKNOWN_ACTION`
Autoridade: Capability declarada mais autoridade do usuário atual sobre o recurso; capabilities nunca elevam permissões.
Visibilidade: Projeção do usuário atual; recursos ocultos são indistinguíveis de inexistentes.
Concorrência: Autoritativo no servidor; `expectedVersion` é compare-and-swap atômico quando declarado.
Durabilidade: Somente recursos de servidor declarados são duráveis; registros locais terminam no unload do package.
Ciclo de vida: O package deve estar instalado, habilitado e ativo; registros retornam um disposer.
Limite de segurança: Não expõe filesystem, database, transport, renderer, internals de ACL nem override de permissão.

### `ui.slots`

Status: `stable`
Tipos de package: `ruleset`, `addon`, `library`, `content`, `theme`, `assets`
Métodos: `sdk.ui.slots.available`, `sdk.ui.slots.register`
Eventos: [Eventos](#eventos)
Erros: `CAPABILITY_REQUIRED`, `PERMISSION_DENIED`, `NOT_FOUND`, `VALIDATION_FAILED`, `STALE_VERSION`, `UNKNOWN_ACTION`
Autoridade: Capability declarada mais autoridade do usuário atual sobre o recurso; capabilities nunca elevam permissões.
Visibilidade: Projeção do usuário atual; recursos ocultos são indistinguíveis de inexistentes.
Concorrência: Autoritativo no servidor; `expectedVersion` é compare-and-swap atômico quando declarado.
Durabilidade: Somente recursos de servidor declarados são duráveis; registros locais terminam no unload do package.
Ciclo de vida: O package deve estar instalado, habilitado e ativo; registros retornam um disposer.
Limite de segurança: Não expõe filesystem, database, transport, renderer, internals de ACL nem override de permissão.

## Eventos

### `actor.created`

Entrega: Evento autorizado e versionado por schema; releia o estado atual.

### `actor.data.updated`

Entrega: Evento autorizado e versionado por schema; releia o estado atual.

### `actor.deleted`

Entrega: Evento autorizado e versionado por schema; releia o estado atual.

### `actor.updated`

Entrega: Evento autorizado e versionado por schema; releia o estado atual.

### `automation.job.changed`

Entrega: Evento autorizado e versionado por schema; releia o estado atual.

### `cards.state.changed`

Entrega: Evento autorizado e versionado por schema; releia o estado atual.

### `chat.created`

Entrega: Evento autorizado e versionado por schema; releia o estado atual.

### `combat.ended`

Entrega: Evento autorizado e versionado por schema; releia o estado atual.

### `combat.started`

Entrega: Evento autorizado e versionado por schema; releia o estado atual.

### `combat.turn.changed`

Entrega: Evento autorizado e versionado por schema; releia o estado atual.

### `combat.updated`

Entrega: Evento autorizado e versionado por schema; releia o estado atual.

### `game.ready`

Entrega: Evento autorizado e versionado por schema; releia o estado atual.

### `item.created`

Entrega: Evento autorizado e versionado por schema; releia o estado atual.

### `item.deleted`

Entrega: Evento autorizado e versionado por schema; releia o estado atual.

### `item.updated`

Entrega: Evento autorizado e versionado por schema; releia o estado atual.

### `journal.created`

Entrega: Evento autorizado e versionado por schema; releia o estado atual.

### `journal.deleted`

Entrega: Evento autorizado e versionado por schema; releia o estado atual.

### `journal.updated`

Entrega: Evento autorizado e versionado por schema; releia o estado atual.

### `pdf.annotations.changed`

Entrega: Evento autorizado e versionado por schema; releia o estado atual.

### `pdf.presentation.changed`

Entrega: Evento autorizado e versionado por schema; releia o estado atual.

### `rules.action.completed`

Entrega: Evento autorizado e versionado por schema; releia o estado atual.

### `scene.changed`

Entrega: Evento autorizado e versionado por schema; releia o estado atual.

### `scene.effects.changed`

Entrega: Evento autorizado e versionado por schema; releia o estado atual.

### `scene.fog.changed`

Entrega: Evento autorizado e versionado por schema; releia o estado atual.

### `scene.geometry.changed`

Entrega: Evento autorizado e versionado por schema; releia o estado atual.

### `scene.images.changed`

Entrega: Evento autorizado e versionado por schema; releia o estado atual.

### `scene.measurements.changed`

Entrega: Evento autorizado e versionado por schema; releia o estado atual.

### `scene.shaders.changed`

Entrega: Evento autorizado e versionado por schema; releia o estado atual.

### `scene.templates.changed`

Entrega: Evento autorizado e versionado por schema; releia o estado atual.

### `setting.changed`

Entrega: Evento autorizado e versionado por schema; releia o estado atual.

### `token.created`

Entrega: Evento autorizado e versionado por schema; releia o estado atual.

### `token.deleted`

Entrega: Evento autorizado e versionado por schema; releia o estado atual.

### `token.moved`

Entrega: Evento autorizado e versionado por schema; releia o estado atual.

### `token.targets.changed`

Entrega: Evento autorizado e versionado por schema; releia o estado atual.

### `token.updated`

Entrega: Evento autorizado e versionado por schema; releia o estado atual.

## Erros

- `CAPABILITY_REQUIRED`
- `PERMISSION_DENIED`
- `NOT_FOUND`
- `VALIDATION_FAILED`
- `STALE_VERSION`
- `UNKNOWN_ACTION`
