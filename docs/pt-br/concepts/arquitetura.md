# Arquitetura

## Visão do runtime

```text
descoberta de manifests
          │
          ▼
validação estática ──► plano de ativação ──► factories dos módulos
                                                   │
                                                   ▼
                                      middleware · routes · slots
                                                   │
                                                   ▼
                                          server ativo inicia
```

O planejamento ocorre antes de qualquer factory. Ele valida dependências,
SemVer, providers de capabilities, routes, slots, protocolo de room e regras de
singleton. Erros de configuração falham antes da aquisição de recursos.

## Responsabilidades

O host descobre módulos e solicita estados. O kernel valida e coordena. O SDK
define tipos e helpers para autores. Cada módulo possui sua implementação e suas
dependências npm.

```text
host             módulos instalados e estados desejados
kernel           validade da composição e ordem de ativação
SDK              contratos estáveis para autores
módulo            domínio, pacotes externos, recursos e cleanup
```

### Princípio de ownership do módulo

O Gravewright coordena módulos e seus contratos declarados. Cada módulo é dono
dos detalhes de implementação: framework frontend, DOM e rendering, estado no
cliente, protocolos HTTP/WebSocket/WebRTC, bibliotecas de persistência,
integrações externas, cache e comunicação entre suas próprias partes client e
server. React, Vue, Svelte, Web Components, Canvas, Three.js e Pixi são escolhas
válidas do módulo e permanecem invisíveis para o kernel.

Módulos se comunicam por dependências declaradas e `ctx.use()`, capabilities
declaradas e `ctx.capability()`, e valores obtidos com `ModuleRef.get()`. Esse é
o contrato Gravewright independentemente de onde o host executa o módulo. Ele
não é uma API apenas de server e não existe uma API browser paralela.

### Princípio de minimização de surfaces

Uma nova surface do kernel ou SDK só se justifica quando módulos não conseguem
resolver o problema de forma razoável com os contratos existentes. Ausência de
padronização muitas vezes é uma fronteira deliberada, não uma feature faltando.
Depender explicitamente de uma implementação concreta é permitido quando
portabilidade não é objetivo do módulo.

Novas surfaces públicas exigem evidência: um problema real compartilhado por
vários módulos, sem encapsulamento razoável no próprio módulo, e friction
demonstrada nos contratos existentes. A arquitetura legacy cresceu para dezenas
de capabilities e extension points; o runtime atual resiste deliberadamente a
esse padrão. Gravewright prefere uma abstração ausente a uma especulativa.

### Longevidade do kernel

A simplicidade do kernel é uma estratégia de longevidade. Responsabilidades e
APIs permanecem pequenas, previsíveis e protegidas de ecossistemas voláteis.
Dependencies devem ser poucas e servir diretamente ao trabalho do kernel.
React pode mudar, Express pode ser substituído e storage ou rendering podem
evoluir sem alterar o kernel, pois essas tecnologias vivem nos módulos.

## Non-goals

Gravewright não é framework frontend ou full-stack, transporte universal,
framework de RPC ou messaging, ORM, renderer, gerenciador de estado, sistema de
autenticação ou API de persistência. Ele não padroniza como um módulo implementa
UI, transporte, storage, rendering ou seu protocolo client/server.

## Modelo de segurança

O manifest impede acesso não declarado entre módulos e permite rejeitar um grafo
inválido antes do import. `ctx.use("nome")` é limitado às `dependencies` do
chamador; nomes exportados são verificados novamente em runtime.

Isso controla capabilities dentro do grafo, mas não isola processos. Não instale
módulos não confiáveis num host privilegiado. Hashes garantem integridade do
release em trânsito; não tornam o código confiável.

## Modelo de falha

Factories registram recursos imediatamente com `ctx.onDispose()`. Uma ativação
que falha desfaz recursos na ordem inversa. No shutdown normal, o server para
primeiro; composição e módulos são liberados na ordem topológica inversa.

Uma desativação é confirmada assim que o teardown começa. Todos os disposers são
tentados em ordem inversa e erros de cleanup são reportados, mas um módulo já
parcialmente desmontado nunca volta a aparecer como ativo nem é limpo novamente
no shutdown.

## Fronteira da composição visual

O SDK compartilhado inclui tipos DOM e o helper `composeRoomSlots` para que rooms
e addons usem o mesmo contrato visual. Importar o SDK no Node não acessa
`document` nem executa trabalho DOM; isso só ocorre quando uma room no browser
chama o helper explicitamente. Slots padronizam um ponto estreito de composição;
eles não tornam o kernel responsável pelo framework, arquitetura DOM, rendering
ou transporte da room.
