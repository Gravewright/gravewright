# Actions declarativas

Pacotes declaram actions registradas por `provides.rules.actionRegistry`. Cada definição tem ID estável local ao pacote, versão positiva explícita do contrato, schema tipado de input object, classe de idempotência e no máximo 16 operações semânticas allow-listed.

Use `sdk.rules.actions.list()` e `sdk.rules.actions.get(id)` para descoberta e `sdk.rules.actions.execute(id, input, {version})` para execução. O caller não envia um grafo de operações. As definições são validadas no carregamento do pacote; uma definição inválida é omitida sem tornar código arbitrário executável.

A execução revalida ativação do pacote, membership na campanha, authority do usuário atual, visibilidade do recurso e a capability exigida por cada operação. O resultado contém identidade, versão, execution ID opaco, resultado semântico e pequenas referências aos recursos alterados. `rules.action.completed` não contém estado do recurso; listeners fazem nova leitura autorizada.

`REQUIRES_IDEMPOTENCY_KEY` é crash-safe quando o core deriva `durability: supported`: hoje, exatamente um `actor.data.patch`. Mutation e receipt compartilham o replace do envelope do Actor. Definições multi-step e cross-resource não são duráveis. A semântica é at-least-once com execução idempotente, não exactly-once cross-domain.

`resolve({provider:"active-ruleset", semantic})` descobre semânticas tipadas; `executeReference` usa a autoridade normal do provider sem expor paths privados.
