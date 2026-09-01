# Kinds de módulo

Kinds definem papéis arquiteturais e contratos mínimos. Módulos implementam esses papéis; seus detalhes internos são opacos para o Gravewright.

| Kind | Contrato mínimo | Cardinalidade ativa |
| --- | --- | --- |
| `server` | `start`, `stop`, `http`, `route`, `middleware`; `realtime` opcional | exatamente 1 |
| `room` | `mount`, `unmount`, `slots` e os slots canônicos | 0..1 |
| `ruleset` | nenhuma API universal de jogo | 0..1 |
| `chat` | `send`, `erase` | 0..1 |
| `dice-engine` | `roll` | 0..1 |
| `assets` | `store`, `resolve`, `mimeTypeAllowed`, `remove` | 0..1 |
| `storage` | `create`, `find`, `where`, `update`, `delete` | 0..1 |
| `backend` | exports livres | 0..N |
| `addon` | exports livres | 0..N |

Use `dependencies` com `ctx.use()` quando a identidade da implementação importa, `uses` com `ctx.kind()` para um papel arquitetural substituível e `requires`/`provides` com `ctx.capability()` para um protocolo semântico opcional que não justifica um kind.

O `server` controla transporte, routes e middleware. A `room` controla o ciclo visual e os slots. O `ruleset` deliberadamente não possui API universal de personagem, combate, iniciativa ou dados.

Somente `server` é obrigatório para o kernel. Uma recipe de VTT pode exigir
`room` e `ruleset`, enquanto um servidor usado apenas para administração ou
marketplace pode iniciar sem ambos.
