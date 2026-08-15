# Política de Governança da SDK do Gravewright

> [English version](../../GRAVEWRIGHT_SDK_GOVERNANCE_POLICY.md)

**Status:** Política de projeto proposta  
**Aplica-se a:** SDK do Gravewright, manifests de pacotes, registro de capabilities, runtime público de pacotes, contratos entre pacotes, comportamento da CLI voltado a pacotes e todos os pacotes oficiais do Gravewright  
**Linguagem normativa:** **DEVE**, **NÃO DEVE**, **DEVERIA**, **NÃO DEVERIA** e **PODE** correspondem, respectivamente, a **MUST**, **MUST NOT**, **SHOULD**, **SHOULD NOT** e **MAY** e são termos normativos.

---

## 1. Propósito

A SDK do Gravewright existe para permitir que um ecossistema de extensões cresça sem tornar o core permanentemente dependente de sua implementação atual. Ela não é apenas um conjunto de APIs convenientes: é uma fronteira de compatibilidade duradoura entre o core, rulesets, addons, bibliotecas, pacotes de conteúdo, temas, assets e futuras classes de extensão.

> **Preservar a liberdade de substituir a implementação interna do Gravewright sem quebrar desnecessariamente pacotes que dependem apenas de contratos públicos intencionais.**

Esta política governa como essa fronteira é projetada, ampliada, estabilizada, descontinuada, protegida, documentada, testada e versionada. O projeto DEVE preferir a qualidade duradoura do contrato à conveniência imediata.

## 2. Princípios centrais

### 2.1 Estabilize intenção, não implementação

> **Não estabilize comportamento acidental. Estabilize apenas contratos intencionais.**

Internals do renderer, globals privados, estrutura do DOM, classes CSS, rotas privadas, layout do banco, ordenação de WebSocket, stores, identidade de objetos, classes de framework, layout interno de arquivos, texto incidental de erros e timing incidental NÃO DEVEM virar contrato apenas por serem observáveis. Dependência de terceiros não promove automaticamente um internal a API. O projeto DEVE criar um contrato semântico, oferecer migração ou rejeitar expressamente o caso de uso.

### 2.2 A SDK é uma fronteira semântica

Contratos públicos DEVERIAM descrever o objetivo, não o mecanismo atual.

```js
await sdk.combat.setInitiative(combatantId, value);
await sdk.tokens.move(tokenId, { x, y });
await sdk.cards.draw({ deckId, count: 1 });
```

Chamadas a rotas internas, globals privados ou seletores do DOM são desencorajadas. Detalhes de implementação só podem ser expostos quando forem deliberadamente parte do modelo durável.

### 2.3 Declarativo primeiro

Quando a intenção puder ser expressa como dados, a SDK DEVERIA preferir contratos declarativos: tipos de atores e itens, fichas, regras, condições, mappings de token, settings, locales, content packs e contratos entre pacotes. APIs imperativas DEVERIAM existir apenas para comportamento genuinamente dinâmico.

### 2.4 Menor privilégio

Cada pacote DEVE solicitar o menor conjunto de capabilities suficiente. Toda operação protegida DEVE mapear para uma capability canônica. Fronteiras operacionalmente distintas não DEVEM ser agrupadas apenas para reduzir o registro; prefira `cards.read`, `cards.play` e `cards.manage` a `cards.any`.

### 2.5 Nenhuma capability de escape universal

O Gravewright NÃO DEVE introduzir autoridade equivalente a `any`, `all`, `unrestricted`, `raw`, `superuser` ou `unsafe`. Isso destruiria menor privilégio, auditoria, encapsulamento e substituibilidade do core. Uma necessidade não atendida indica uma capability semântica ausente, design inadequado do pacote ou caso de uso deliberadamente não suportado: nunca justificativa para `any`.

### 2.6 Autoridade do servidor

O browser NÃO DEVE ser autoridade de persistência, permissões, campanha, combate, ownership, storage ou segurança. Mutações públicas DEVEM passar por validação e autorização no servidor. Capability expressa intenção do pacote; não substitui a permissão do usuário.

### 2.7 Substituibilidade do core

Revisores DEVERIAM perguntar se renderer, framework, persistência, servidor ou transporte poderiam ser trocados preservando o contrato. A SDK NÃO DEVE exigir PixiJS, WebGL, WebGPU, Python, banco, framework, rotas ou modelo interno específicos, salvo se promovidos deliberadamente a contrato público.

## 3. Escopo do contrato público

Somente superfícies explicitamente declaradas públicas fazem parte do contrato: schema de `manifest.json`, `sdkVersion`, capabilities estáveis, métodos `sdk.*`, lifecycle, fichas/controllers, schemas declarativos, storage gerenciado, `sdk.bus.*`, eventos, comportamento estável da CLI, códigos estruturados de erro e formatos declarados públicos. Todo o restante é privado. Acessibilidade não é garantia de estabilidade.

## 4. Versionamento da SDK

`sdkVersion` é independente da versão do aplicativo. Reescritas internas podem continuar implementando SDK 1. Um pacote válido que usa apenas contratos estáveis, documentados e permitidos DEVERIA continuar instalando e executando em releases compatíveis. Bugs, vulnerabilidades e comportamento indefinido não viram garantias.

Uma quebra de contrato estável exige nova major da SDK, adapter formal ou processo excepcional de segurança. A major do aplicativo, sozinha, NÃO justifica quebra silenciosa.

## 5. Governança do registro de capabilities

O registro canônico é a autoridade. Cada capability DEVE definir nome, status, propósito, autoridade, métodos ou declarações, natureza runtime/declarativa, segurança, kinds permitidos quando aplicável e documentação. Allowlists independentes NÃO DEVEM ser mantidas em paralelo; mirrors DEVEM ser gerados ou testados contra a fonte canônica, e o CI DEVE falhar em caso de drift.

## 6. Ciclo de vida de capabilities

Os estados públicos da SDK 1 são `stable` e `forbidden`. Estados de governança não públicos podem existir antes do registro.

- **Proposed:** conceito de RFC, recusado em manifests de produção. DEVE documentar problema, casos reais, insuficiência atual, autoridade, abuso, API, autorização, lifecycle, schemas/eventos, migração e testes.
- **Incubating:** pode existir em builds de desenvolvimento, flags, protótipos oficiais ou harnesses, sem garantia de compatibilidade.
- **Stable:** exige todos os gates da seção 10 e não pode ser quebrada dentro da SDK 1 salvo emergência de segurança.
- **Deprecated:** continua suportada durante a major e DEVE indicar substituição, motivo, migração, diagnósticos e major-alvo.
- **Removed:** normalmente apenas na SDK 2 ou posterior, com guia de migração.
- **Forbidden:** autoridade deliberadamente recusada.

Permanecem proibidas:

```text
backend.execute
database.raw
filesystem.raw
network.raw
permissions.override
```

Aliases equivalentes também DEVEM ser recusados; renomear a mesma autoridade não contorna a proibição.

## 7. Regras de design

Toda capability DEVE ser semanticamente coerente, conceder autoridade mínima, ser independente da implementação, definir falhas e lifecycle e limitar consumo significativo de recursos. Leitura, escrita e administração DEVERIAM ser separadas quando tiverem riscos diferentes. Registros e subscriptions DEVEM ser removíveis ao desabilitar, descarregar, trocar campanha ou atualizar durante desenvolvimento; quando apropriado, a API DEVERIA retornar um disposer. Limites podem incluir payload, timeout, linhas, quota, taxa de eventos e orçamento de render.

## 8. Pacotes oficiais não usam internals privados

Pacotes oficiais são referências da SDK e NÃO DEVEM chamar rotas `/game/...` não documentadas, acessar globals `window.Gravewright*`, alterar prototypes, depender do DOM fora de sua raiz, observar o DOM global, ler stores, acessar renderer, usar CSS privado ou reconstruir URLs internas. Uma necessidade legítima abre revisão de gap: criar API semântica, redesenhar, rejeitar ou incubar. “Usar internal por enquanto” não pode virar solução permanente.

O CI DEVERIA sinalizar padrões como `window.Gravewright`, `fetch("/game/`, `XMLHttpRequest`, `document.querySelector(` e `MutationObserver(document.body`. Um match exige revisão, embora não prove violação sozinho.

## 9. Superfícies públicas não podem virar escapes

Helpers amplos e contexts merecem a mesma revisão das capabilities. Primitivas arbitrárias como `postJSON(url, body)` NÃO DEVERIAM substituir operações tipadas. Prefira `ctx.actor.patch`, `ctx.item.patch` e `ctx.refresh`. Contexts de ficha DEVERIAM expor somente dados e mutações do recurso controlado, evitando autoridade global.

## 10. Gates de estabilidade

Uma capability NÃO DEVE virar `stable` antes de cumprir os gates aplicáveis:

- **A: Necessidade demonstrada:** ao menos um caso concreto; prefira casos independentes ou pacote oficial.
- **B: Revisão da API existente:** explique por que contratos atuais não resolvem o problema.
- **C: Segurança:** documente autoridade, limites, enforcement, confiança, validação, recursos, exposição e abuso.
- **D: Encapsulamento:** não exponha rotas, DOM, renderer, persistência, frameworks ou transporte.
- **E: Cross-system:** abstrações genéricas de regras devem ser avaliadas em famílias distintas, como d20, roll-under, dice pool, PbtA, FitD, Fate/Fudge, Year Zero, cartas, step dice e percentil.
- **F: Runtime:** implementação completa em todas as camadas, inclusive autoridade no servidor.
- **G: Testes:** validação, gating, caminhos permitido/negado, permissão, input, disposal, inatividade, dependências, serialização, schemas, fixtures e browser. Inspeção estática não substitui testes executáveis importantes.
- **H: Documentação:** propósito, manifest, assinaturas, schemas, exemplos, falhas, segurança e lifecycle.
- **I: Pacote de referência:** quando viável, ao menos um pacote real.
- **J: Migração e futuro:** responda “o que lamentaríamos prometer para sempre?”.

## 11. Processo de RFC

RFC é OBRIGATÓRIA para adicionar ou ampliar capability, criar runtime público estável, alterar manifest, lifecycle, storage ou interoperabilidade, adicionar rede ou backend, descontinuar contrato, criar major ou excepcionar a política de internals.

O RFC DEVERIA conter status, problema, casos reais, não objetivos, limitações atuais, contrato, capabilities, autoridade, autorização, schemas, lifecycle, segurança, encapsulamento, alternativas, compatibilidade, migração, testes, documentação e questões abertas.

Decida nesta ordem: pertinência ao ecossistema; possibilidade declarativa; reutilização da API; autoridade mínima; sobrevivência a reescrita; autoridade do servidor; testabilidade; e disposição de sustentar a promessa durante toda a major. Conveniência não basta.

## 12. Papéis de governança

O mantenedor responde finalmente por compatibilidade, segurança, registro, majors e emergências, mesmo delegando revisões. Revisores DEVERIAM dominar design de API, autoria, segurança, runtime, backend ou modelagem de RPG; ao menos um deveria revisar como autor de pacote. Expansões de autoridade exigem revisão de segurança. Autores devem pedir apenas capabilities necessárias, evitar internals, documentar uso, tratar peers opcionais, versionar payloads, limpar lifecycle e relatar gaps.

## 13. Transparência

RFCs aceitas e rejeitadas DEVERIAM permanecer públicas. Decisões importantes devem registrar a justificativa, especialmente recusas, divisão de capability, proibição de autoridade ou escape. O projeto DEVERIA manter um log leve de decisões.

## 14. Interoperabilidade entre pacotes

Integração DEVE usar `sdk.bus.*` ou sucessor documentado, nunca globals, arquivos privados, DOM ou ordem implícita. Namespaces devem pertencer ao publicador; um pacote NÃO DEVE impersonar outro. Payloads DEVERIAM ser serializáveis, versionados, validáveis, limitados e independentes de classes internas. Ausência de peer opcional é estado normal.

## 15. Eventos

O catálogo DEVE ser pequeno e semântico (`actor.updated`, `token.moved`, `scene.activated`, `combat.updated`, `chat.created`), não coreografia de implementação. Payloads DEVEM ser documentados e versionáveis; objetos internos mutáveis NÃO DEVEM ser entregues por conveniência.

## 16. Extensões de UI

O projeto DEVERIA oferecer slots semânticos, como `scene.toolbar`, `actor.header.actions`, `item.header.actions`, `chat.message.actions` e `combat.combatant.actions`. Slot é local semântico, não seletor DOM. Pacotes DEVERIAM renderizar em roots fornecidas, preservando a liberdade de trocar DOM e framework.

## 17. Dados e storage

Storage DEVE ser escopado e gerenciado; pacotes NÃO recebem paths arbitrários. `database.raw` permanece proibida. Necessidades maiores devem ampliar storage semântico. Migrations são input privilegiado e DEVEM ser restringidas; não podem conceder autoridade proibida. Settings e storage NÃO DEVEM ser anunciados como cofre de segredos sem implementação explícita.

## 18. Rede

`network.raw` permanece proibida. Rede futura exige RFC e capability restrita com allowlist de origins, bloqueio padrão de localhost/LAN, timeout, limite de resposta, redirects seguros, remoção de credenciais ambientes, origins visíveis ao operador e defesa contra SSRF.

## 19. Código de backend

`backend.execute` permanece proibida na SDK 1. Necessidade futura deve primeiro avaliar regras declarativas, intents tipadas, expressões determinísticas, WASM restrito ou sandbox com CPU, memória, host calls e persistência limitados. Isso exige revisão de segurança no nível de major, salvo prova de compatibilidade com o modelo atual.

## 20. Pacotes oficiais

Pacotes oficiais entregam funcionalidade e testam a suficiência da SDK como terceiros a usariam. NÃO recebem APIs privadas por serem oficiais. Integração privilegiada deve permanecer claramente no core ou passar pela governança antes de virar contrato.

## 21. Revisão de capabilities na instalação

Ferramentas DEVERIAM distinguir autoridade declarativa, JavaScript confiável, mutação, storage, interop, administração e integrações futuras. Pacotes DEVERIAM justificar cada capability. CLI e UI PODEM exibir descrições geradas do registro canônico.

## 22. Fixtures de compatibilidade

O projeto DEVE manter fixtures representativas da SDK 1: manifest mínimo, cada kind, combinações estáveis, storage, lifecycle, interop, fichas, conteúdo e rulesets. Uma reescrita que alegue compatibilidade DEVE aprová-las.

## 23. Testes de fitness arquitetural

O projeto DEVERIA verificar: sincronização do registro; todo método público protegido mapeado; proibições aplicadas em manifest, doctor, instalação, ativação e runtime; pacotes oficiais sem internals; fixtures antigas válidas; identidade escopada; e capability incapaz de contornar permissão do usuário.

## 24. Descontinuação

Deprecação DEVE ser previsível: marcar docs, indicar substituição, fornecer migração e diagnósticos, manter durante a major e remover apenas na próxima, salvo segurança. Preferência de estilo não justifica churn.

## 25. Mudanças emergenciais de segurança

Uma quebra emergencial só é permitida diante de risco crível sem mitigação compatível. O projeto DEVE documentar contrato e classe do risco, limitar a quebra, fornecer migração e diagnósticos e registrar a exceção. “Segurança” NÃO pode encobrir limpeza de API.

## 26. Nova major da SDK

Uma major é cara e DEVERIA ser rara, reservada a mudanças intencionais impossíveis de preservar. SDKs podem coexistir; adapters DEVERIAM ficar centralizados; autores devem receber ferramentas e diagnósticos; migrações não relacionadas não deveriam ser forçadas juntas. A major da SDK não acompanha automaticamente a do aplicativo.

## 27. Crescimento do ecossistema

O projeto DEVERIA favorecer contratos semânticos pequenos, dados versionados, capabilities e slots explícitos, autoridade do servidor, declarações, storage escopado, interop estável e tooling forte. DEVERIA evitar monkey patching, objetos do renderer, contratos DOM, rotas arbitrárias, globals privados, load order implícito e escapes “temporários”.

## 28. Gaps da SDK

Um gap deve ser classificado como: necessidade semântica comum (nova capability via RFC), necessidade escopada (API de context), interop (bus), posicionamento de UI (slot), detalhe do core (não expor) ou autoridade insegura (rejeitar/restringir). Essa classificação substitui a tentação de adicionar `any`.

## 29. Checklist do mantenedor

Antes do merge, responda: o caso é real? É o contrato mais estreito? É semântico? Sobrevive a reescrita? Preserva autoridade do servidor? Escopo, erros, cleanup, limites e schemas estão definidos? Há testes executáveis, documentação, revisão de segurança e pacote real? Sustentaremos isso pela major inteira? Se a última resposta for incerta, ainda não está pronto.

## 30. Pacto com autores

Autores podem esperar contratos intencionais, deprecação explícita, disciplina de compatibilidade, capabilities documentadas e responsabilidade da plataforma. Em troca, devem respeitar fronteiras, menor privilégio, interop, portabilidade e migrações futuras.

## 31. Filosofia

O Gravewright deve evitar uma SDK restritiva demais e outra tão permissiva que congele cada internal. O objetivo é:

> **Extensão semântica poderosa, autoridade estreita e encapsulamento forte.**

Isso permite dezenas de rulesets, centenas de addons, anos de conteúdo e campanhas duradouras enquanto renderer, UI, persistência, rede e arquitetura continuam substituíveis. Essa liberdade é uma funcionalidade do produto e a promessa central da SDK.

## 32. Política final

1. **Segurança acima da conveniência.**
2. **Contrato intencional acima de comportamento acidental.**
3. **API semântica acima de exposição da implementação.**
4. **Menor privilégio acima de autoridade ampla.**
5. **Contratos declarativos acima de acoplamento runtime desnecessário.**
6. **Compatibilidade acima da conveniência interna quando a API é estável.**
7. **Substituibilidade do core acima da dependência do ecossistema em internals atuais.**
8. **Casos reais acima de crescimento especulativo da API.**
9. **Decisões explícitas em RFC acima de exceções não documentadas.**
10. **Nenhuma capability de escape universal.**

O projeto não promete que os internals do Gravewright permanecerão iguais. Promete tratar contratos estáveis da SDK como contratos reais. Essa distinção é a base da plataforma.
