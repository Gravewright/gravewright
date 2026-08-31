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

## Fronteira do browser

O SDK compartilhado inclui tipos DOM e o helper `composeRoomSlots` para que rooms
e addons usem o mesmo contrato visual. Importar o SDK no Node não acessa
`document` nem executa trabalho DOM; isso só ocorre quando uma room no browser
chama o helper explicitamente. Se essa superfície crescer, um futuro pacote
`@gravewright/room` ou subpath do SDK pode tornar a fronteira física.
