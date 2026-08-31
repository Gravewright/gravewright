# Status da API pública

Este inventário reflete o contrato atual e sua cobertura de integração
automatizada. “Candidata a estável” não declara congelamento.

## `@gravewright/sdk`

| Contrato | Status | Evidência ou risco |
| --- | --- | --- |
| Kinds, providers e `ModuleManifest` | candidata a estável | Os cinco papéis e o grafo estático foram exercitados. |
| `defineModule`, registries, `Context`, `ModuleRef`, `Dispose` | candidata a estável | Dependências concretas, capabilities e lifecycle foram exercitados. |
| `DynamicContext` | candidata a estável | Agora possui a mesma surface de `use`, `capability`, lifecycle e diagnóstico de `Context`, com nomes dinâmicos. |
| Request, response, routes e middleware | candidata a estável | Surface neutra deliberadamente pequena; recursos HTTP especializados pertencem à API de um server concreto. |
| Slots de room e `composeRoomSlots` | candidata a estável | Contrato visual estreito; framework, rendering e transporte client/server pertencem à room ou ao módulo. |

## `@gravewright/kernel`

`Kernel`, suas opções, `ActivationPlan` e os métodos públicos `load`, `plan`,
`initialize`, `activate`, `disable`, `use` e `shutdown` são candidatos a
estáveis. Planner interno, validador e registros de runtime não fazem parte da
raiz pública do pacote.

O schema JSON ajuda editores e ferramentas. A validação de runtime continua
sendo a autoridade semântica.

## Auditoria de minimização

| Surface | Finalidade no core | Detalhe que fica no módulo | Decisão |
| --- | --- | --- | --- |
| Manifest e constantes | Identidade, grafo, permissões e composição | Comportamento e bibliotecas | Manter |
| `defineModule` e inferência | Autoria e tipo da factory declarada | Implementação da factory | Manter |
| `use`, `capability` e `get` | Resolver e autorizar comunicação entre módulos | Implementação dos valores | Manter; linguagem central |
| `onDispose` | Ligar recursos a rollback e shutdown | Implementação do recurso | Manter |
| Diagnóstico | Auditoria semântica opt-in já existente | Backend de logs e telemetria da aplicação | Manter estreita |
| Routes e middleware neutros | Compor handlers básicos portáveis | HTTP completo e framework do server | Manter pequena |
| Protocolo de room e slots | Compor contribuições visuais independentes | UI, rendering, estado e transporte | Manter estreita |
| `DynamicContext` | Fallback não tipado explícito | Descoberta e implementação | Manter; agora coerente |
| Kernel e plano | Validar e executar a composição | Política do host e implementação | Manter |

Cada surface atual sustenta declaração, composição, autorização, lifecycle ou
uma integração estreita já existente. Os contratos HTTP e DOM são pontos de
interoperabilidade, não tentativas de modelar essas tecnologias por inteiro.
Não é necessária uma surface de transporte, RPC, eventos, frontend,
persistência ou autenticação. Nada deve ser adicionado por completude teórica.

Os exports específicos `http` e `ws` do `gravewright-server` são a saída
explícita: um módulo pode depender desse provider quando precisar de algo além
do contrato neutro. Portabilidade é uma escolha, não uma obrigação universal.
