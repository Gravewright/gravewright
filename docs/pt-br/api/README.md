# APIs Públicas do Gravewright

Esta seção documenta as superfícies públicas de integração para autores de pacotes SDK e integrações.

Os materiais de API são licenciados sob MIT. A implementação do core permanece Apache-2.0.

> [!WARNING]
> **Superfície de API em Alpha.**
>
> Gravewright ainda é pré-1.0. As APIs públicas são documentadas para permitir experimentação por autores de pacotes SDK e integrações, mas as garantias de compatibilidade ainda estão sendo finalizadas.
>
> Breaking changes de API devem atualizar documentação, schemas e testes no mesmo change.

## Superfícies de API

| Documento                                                                | Público                       | Cobre                                                                                                              |
| ------------------------------------------------------------------------ | ----------------------------- | ------------------------------------------------------------------------------------------------------------------ |
| [`http.md`](http.md)                                                     | Autores de integrações        | Grupos de rotas HTTP e convenções de request                                                                       |
| [`realtime.md`](realtime.md)                                             | Clientes realtime             | `/game/ws`, comandos, eventos e comportamento de replay                                                            |
| [`../../sdk/README.md`](../../sdk/README.md)                             | Autores de pacotes            | Gravewright SDK — o único modelo de extensão                                                                       |
| [`../../sdk/manifest.md`](../../sdk/manifest.md)                         | Autores de pacotes            | Referência do manifest de pacote (v1)                                                                              |
| [`../../sdk/runtime.md`](../../sdk/runtime.md)                           | Autores de pacotes            | Runtime de navegador `window.GravewrightSDK`                                                                       |

## Escolhendo o Tipo Certo de Pacote

| Necessidade | Kind |
| --- | --- |
| Definir tipos de ator/item, fichas, regras e combate | `ruleset` |
| Fornecer vocabulario de ruleset, labels e arquivos de locale | `ruleset` |
| Adicionar comportamento opcional de UI ou automacao por campanha | `addon` |
| Adicionar tema visual | `theme` |
| Fornecer midia reutilizavel, como tokens, mapas e audio | `assets` |
| Distribuir pacotes de conteudo importavel | `content` |
| Compartilhar codigo/estilos passivos entre pacotes | `library` |

Regra pratica: se a campanha nao funciona sem isso, pertence a um `ruleset`.

Se o GM deve poder ligar ou desligar por campanha, use `addon`, `theme`, `assets`
ou `content`. Veja [`../../sdk/kinds.md`](../../sdk/kinds.md).

## Expectativas de Estabilidade

Durante Alpha:

* manifests devem declarar `schemaVersion: 1` e `sdkVersion: "1"`;
* pacotes devem declarar `compatibility.minimum`, `compatibility.verified` e `compatibility.maximum`;
* autores de pacotes devem testar contra a versão exata do Gravewright marcada como `verified`;
* APIs documentadas são o único contrato público;
* globals não documentados, estrutura DOM, internals de renderer, comportamento de fallback, stores privados e detalhes de implementação podem mudar sem suporte de migração;
* mudanças em API pública devem refletir em documentação e testes no mesmo change.

## API Pública vs Implementação Privada

APIs públicas são documentadas neste diretório e nos guias do SDK.

Os itens abaixo não são contratos públicos, exceto quando forem explicitamente documentados:

* globals internos de JavaScript;
* estado local de renderer;
* stores privados;
* estrutura DOM;
* classes CSS que não foram documentadas como hooks de extensão;
* labels de fallback;
* formatos internos de eventos WebSocket que não estejam documentados em `api/realtime.md`.

Pacotes devem usar a SDK documentada: manifests declarativos, schemas, regras,
hooks, slots, labels, locales, assets e `window.GravewrightSDK`.

## Licença dos Materiais de API

Os materiais de API são licenciados sob MIT para permitir que autores copiem livremente contratos de API, schemas, exemplos, formatos de manifest e estruturas iniciais de pacote.
