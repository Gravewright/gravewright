# Politica de Estabilidade da SDK

Este documento define quais superficies publicas fazem parte do contrato da SDK
1.x e quais permanecem fora do LTS.

## Regra Guia

Estabilizar apenas comportamento intencional. A SDK 1 está em RC 1. Um package
válido para `sdkVersion: "1"` deve continuar instalando, ativando e executando
em releases compatíveis, salvo quando depender de capabilities `forbidden`.

Autores devem usar `compatibility.minimum` e `compatibility.verified` como
`"1"`. Versões do produto ou labels de RC, como `1.0.0-beta.3` e
`1.0.0-rc.1`, não pertencem nesses campos de compatibilidade da SDK.

## Niveis de Estabilidade

| Status | Significado |
|---|---|
| `stable` | API pública incluída no candidato RC 1 congelado. Não deve quebrar em `sdkVersion: "1"`. |
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

## Enforcement do RC 1

O fingerprint semântico é
`docs/sdk/_data/gravewright-sdk-1.rc1-snapshot.json`. A CI regenera o contrato
público e rejeita drift incompatível. Consulte
[`rc1-compatibility-policy.md`](rc1-compatibility-policy.md) e
[`rc1-certification.md`](rc1-certification.md); gates históricos pertencem ao
histórico de releases, não ao contrato atual de autoria.
