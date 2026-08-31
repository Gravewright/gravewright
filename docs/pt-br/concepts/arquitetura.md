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
