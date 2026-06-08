# APIs Públicas do Gravewright

Esta seção documenta as superfícies públicas de integração para autores de sistemas, módulos, integrações e content packs. Materiais de API são licenciados sob MIT; a implementação do core permanece Apache-2.0.

> [!WARNING]
> **API em Alpha.** Gravewright ainda é pré-1.0. As APIs públicas são documentadas para permitir experimentação, mas garantias de compatibilidade ainda estão sendo finalizadas. Breaking changes devem atualizar documentação, schemas e testes no mesmo change.

## Superfícies de API

| Documento | Público | Cobre |
|---|---|---|
| [`extensoes.md`](extensoes.md) | autores de módulos/sistemas | globals de navegador, API escopada de módulo, hooks de ficha e combate |
| [`http.md`](http.md) | integrações | grupos de rotas HTTP e convenções de request |
| [`realtime.md`](realtime.md) | clientes realtime | `/game/ws`, comandos, eventos e replay |
| [`../modulos.md`](../modulos.md) | autores de módulos | Module API v1, manifest, capabilities, settings e empacotamento |
| [`../modulos/criando-um-modulo.md`](../modulos/criando-um-modulo.md) | autores de módulos | guia passo a passo detalhado |
| [`../sistemas/criando-um-sistema.md`](../sistemas/criando-um-sistema.md) | autores de sistemas | System API v1, estrutura, manifest, schemas, fichas e regras |
| [`../sistemas/manifest.md`](../sistemas/manifest.md) | autores de sistemas | referência do manifest de sistema |

## Escolhendo entre sistema e módulo

| Necessidade | Use |
|---|---|
| definir tipos de ator/item | sistema |
| definir schemas e layouts de ficha | sistema |
| definir rolagens base e combate | sistema |
| adicionar comportamento visual opcional | módulo |
| adicionar automação habilitável por campanha | módulo |
| adicionar settings de usuário/campanha | módulo |
| distribuir conteúdo opcional | módulo ou sistema, dependendo do dono do conteúdo |

Regra prática: se a campanha não funciona sem isso, provavelmente é sistema. Se o GM deve poder ligar/desligar por campanha, é módulo.

## Estabilidade

Durante Alpha:

- manifests devem declarar `apiVersion: "1"`;
- pacotes devem declarar `compatibility.minimum`, `compatibility.verified` e `compatibility.maximum`;
- autores devem testar contra a versão exata marcada como `verified`;
- APIs documentadas são o contrato público;
- globals internos, DOM interno e detalhes de implementação podem mudar sem migração.
