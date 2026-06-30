# Politica de Estabilidade da SDK

Este documento define quais superficies publicas fazem parte do contrato da SDK
1.x e quais permanecem fora do LTS.

## Regra Guia

Estabilizar apenas comportamento intencional. Um package valido para
`sdkVersion: "1"` deve continuar instalando, ativando e executando em releases
`1.x`, salvo quando depender de capabilities `forbidden`.

Autores de pacote devem mirar a linha final da SDK com `compatibility.minimum`
e `compatibility.verified` definidos como `"1"`; valores pre-release como
`1.0.0-rc.1` sao historicos e validam como unverified contra a SDK 1 final.

## Niveis de Estabilidade

| Status | Significado |
|---|---|
| `stable` | API publica. Nao deve quebrar em `sdkVersion: "1"`. |
| `forbidden` | Capability bloqueada para packages (superficie insegura). |

## Classificacao Atual

| Superficie | Status | Notas |
|---|---|---|
| Campos do `manifest` v1 | `stable` | Contrato publico do pacote. |
| `settings.*` | `stable` | Definicoes e coercao validadas. |
| `content.*` | `stable` | Content packs e leitura de conteudo. |
| `i18n.*` | `stable` | Locales e traducao. |
| Lifecycle frontend (`GravewrightSDK.register`, `setup`, `ready`) | `stable` | Ownership e inicializacao testados. |
| `storage.sqlite` / `sdk.storage.sqlite.*` | `stable` | SQLite gerenciado pelo Gravewright. |
| `sdk.bus.*` | `stable` | Comunicação entre pacotes. |
| `sheets.html` / `sheets.controller` / `sheets.richText` | `stable` | Sheets HTML com controller declarado. |

## Requisitos

1. Toda API publica deve ter status no registro canonico de capabilities.
2. Metodos frontend publicos com permissao devem mapear para uma capability.
3. O doctor deve reportar uso de capabilities legadas, proibidas ou em conflito.
4. Mudancas incompativeis no contrato do manifest exigem novo `sdkVersion` ou
   migracao formal.

## Release Gates

> Histórico: estes foram os gates internos do sprint de estabilidade. Seu
> conteúdo foi entregue em conjunto como **Gravewright Alpha 2.0.0 — SDK Freeze**
> (`v2.0.0-alpha.0`), que congelou a superfície da SDK 1. Os nomes de versão
> abaixo são os do plano do sprint, não a tag publicada.

| Release | Tema |
|---|---|
| `v1.0.0-alpha.4` | Storage runtime, lifecycle frontend e sync de capabilities. |
| `v1.0.0-alpha.5` | Interop `sdk.bus.*`. |
| `v1.0.0-beta.1` | Consolidacao LTS: storage, bus e HTML sheets estaveis. |
| `v1.0.0-rc.1` | Apenas bugfixes, docs e testes. |
