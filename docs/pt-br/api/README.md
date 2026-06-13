# APIs Públicas do Gravewright

Esta seção documenta as superfícies públicas de integração para autores de sistemas, módulos, integrações e pacotes de conteúdo.

Os materiais de API são licenciados sob MIT. A implementação do core permanece Apache-2.0.

> [!WARNING]
> **Superfície de API em Alpha.**
>
> Gravewright ainda é pré-1.0. As APIs públicas são documentadas para permitir experimentação por autores de sistemas, módulos, integrações e pacotes de conteúdo, mas as garantias de compatibilidade ainda estão sendo finalizadas.
>
> Breaking changes de API devem atualizar documentação, schemas e testes no mesmo change.

## Superfícies de API

| Documento                                                                | Público                       | Cobre                                                                                                              |
| ------------------------------------------------------------------------ | ----------------------------- | ------------------------------------------------------------------------------------------------------------------ |
| [`extensoes.md`](extensoes.md)                                           | Autores de módulos e sistemas | Globals de navegador, API escopada de módulo, hooks de ficha, labels de ficha, hooks de combate e slots de combate |
| [`http.md`](http.md)                                                     | Autores de integrações        | Grupos de rotas HTTP e convenções de request                                                                       |
| [`realtime.md`](realtime.md)                                             | Clientes realtime             | `/game/ws`, comandos, eventos e comportamento de replay                                                            |
| [`../modulos.md`](../modulos.md)                                         | Autores de módulos            | Visão geral da Module API v1 e quick start                                                                         |
| [`../modulos/criando-um-modulo.md`](../modulos/criando-um-modulo.md)     | Autores de módulos            | Manifest, entrypoints, capabilities, hooks, settings, empacotamento e validação                                    |
| [`../sistemas/criando-um-sistema.md`](../sistemas/criando-um-sistema.md) | Autores de sistemas           | System API v1, estrutura de pacote, manifest, schemas, fichas, regras, labels, assets e configuração de combate    |
| [`../sistemas/manifest.md`](../sistemas/manifest.md)                     | Autores de sistemas           | Referência do manifest de sistema                                                                                  |

## Escolhendo o Tipo Certo de Extensão

| Necessidade                                                  | Use                                                |
| ------------------------------------------------------------ | -------------------------------------------------- |
| Definir tipos de ator                                        | Sistema                                            |
| Definir tipos de item                                        | Sistema                                            |
| Definir schemas e layouts de ficha                           | Sistema                                            |
| Definir rolagens centrais e configuração de combate          | Sistema                                            |
| Fornecer vocabulário de ruleset, labels e arquivos de locale | Sistema                                            |
| Adicionar comportamento opcional de UI                       | Módulo                                             |
| Adicionar automação habilitável por campanha                 | Módulo                                             |
| Adicionar settings de usuário ou campanha                    | Módulo                                             |
| Distribuir conteúdo opcional                                 | Módulo ou sistema, dependendo da posse do conteúdo |

Regra prática: se a campanha não funciona sem isso, provavelmente pertence a um sistema.

Se o GM deve poder ligar ou desligar por campanha, deve ser um módulo.

## Expectativas de Estabilidade

Durante Alpha:

* manifests devem declarar `apiVersion: "1"`;
* pacotes devem declarar `compatibility.minimum`, `compatibility.verified` e `compatibility.maximum`;
* autores de extensão devem testar contra a versão exata do Gravewright marcada como `verified`;
* APIs documentadas são o único contrato público;
* globals não documentados, estrutura DOM, internals de renderer, comportamento de fallback, stores privados e detalhes de implementação podem mudar sem suporte de migração;
* mudanças em API pública devem refletir em documentação e testes no mesmo change.

## API Pública vs Implementação Privada

APIs públicas são documentadas neste diretório e nos guias relacionados de sistemas e módulos.

Os itens abaixo não são contratos públicos, exceto quando forem explicitamente documentados:

* globals internos de JavaScript;
* estado local de renderer;
* stores privados;
* estrutura DOM;
* classes CSS que não foram documentadas como hooks de extensão;
* labels de fallback;
* substituição completa do renderer de ficha;
* substituição completa do renderer de combate;
* formatos internos de eventos WebSocket que não estejam documentados em `api/realtime.md`.

Sistemas e módulos devem usar APIs documentadas, manifests declarativos, schemas, regras, hooks, slots, labels, locales e assets em vez de depender de detalhes de implementação.

## Licença dos Materiais de API

Os materiais de API são licenciados sob MIT para permitir que autores copiem livremente contratos de API, schemas, exemplos, formatos de manifest e estruturas iniciais de pacote.
