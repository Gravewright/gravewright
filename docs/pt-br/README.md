# Documentação do Gravewright

Esta é a documentação em português do Gravewright para o público brasileiro.

> [!WARNING]
> **ALPHA — FAÇA BACKUP ANTES DE ATUALIZAR. NÃO RODE CAMPANHAS LONGAS AINDA.**
>
> O Gravewright está em fase Alpha. Mudanças estruturais, especialmente em schema, SDK, storage e ciclo de vida de pacotes, podem ocorrer entre versões e **não há garantia de caminho de upgrade**.
>
> Uma atualização pode tornar uma mesa existente irrecuperável.
>
> Use para one-shots, mesas de teste e arcos curtos de Alpha. Antes de atualizar, faça backup e preserve a versão usada.
>
> **Uso recomendado em Alpha:** one-shots e campanhas curtas de poucas sessões.
>
> **Ainda não recomendado:** campanhas longas, hospedagem pública de produção ou dados irrecuperáveis.

## Guias do Projeto

- `inicio.md` explica instalação local e primeira execução com o CLI `grave`.
- `alpha.md` explica risco de Alpha, backups e política de upgrade.
- `configuracao.md` documenta variáveis de ambiente e modos de runtime.
- `arquitetura.md` descreve backend, frontend, persistência, realtime e pacotes SDK.
- `desenvolvimento.md` descreve fluxo de desenvolvimento e contribuição.
- `testes.md` documenta testes unitários, CLI, E2E, Docker e performance.
- `deploy.md` documenta requisitos para produção.
- `operacao.md` documenta backup, restore, diagnósticos e storage.
- `seguranca.md` documenta modelo de segurança e checklist.
- `licenciamento.md` explica core Apache-2.0 e materiais de API MIT.
- `storage.md` documenta uploads, pacotes e limpeza em cascata.
- `banco-de-dados.md` documenta SQLite local/teste e PostgreSQL em produção.

## APIs Públicas

- `api/README.md` é a entrada da documentação de APIs públicas.
- `api/http.md` resume grupos de rotas HTTP e limites de autorização.
- `api/realtime.md` documenta WebSocket, comandos, eventos e replay.

## SDK

A documentação principal do SDK fica em inglês em `../sdk/`.

O SDK é o único modelo de extensão. Todo extensível é um pacote Gravewright descrito por um único manifest: ruleset, addon, library, theme, content ou assets.

## Relação com a documentação em inglês

A documentação em inglês continua sendo a referência principal para revisões técnicas de API. Esta árvore em português deve acompanhar os mesmos conceitos, comandos e alertas operacionais.
