# Documentacao do Gravewright

Esta e a documentacao em portugues do Gravewright para o publico brasileiro.

> [!WARNING]
> **ALPHA — NÃO RODE CAMPANHAS.**
> O Gravewright está em fase Alpha. Mudanças estruturais (especialmente de schema)
> podem ocorrer entre versões e **não há garantia de caminho de upgrade** — uma
> atualização pode tornar uma mesa existente irrecuperável.
>
> **Use para one-shots.** Teste, quebre, e relate problemas e sugestões em [issues](https://github.com/ricardoporfirio/grave/issues).
> O que você perde numa one-shot é uma sessão. Numa campanha, são meses.

## Guias Do Projeto

- `inicio.md` explica instalacao local e primeira execucao.
- `configuracao.md` documenta variaveis de ambiente e modos de runtime.
- `arquitetura.md` descreve backend, frontend, persistencia, realtime e extensoes.
- `desenvolvimento.md` descreve fluxo de desenvolvimento e contribuicao.
- `testes.md` documenta testes unitarios, integracao, Docker e performance.
- `docker-testes.md` documenta a estrutura de Docker Compose em `tests/`.
- `deploy.md` documenta requisitos para producao.
- `operacao.md` documenta backup, migracoes, diagnosticos e storage.
- `seguranca.md` documenta modelo de seguranca e checklist.
- `licenciamento.md` explica core Apache-2.0 e materiais de API MIT.
- `storage.md` documenta uploads, pacotes e limpeza em cascata.
- `banco-de-dados.md` documenta SQLite local/teste e PostgreSQL em producao.

## APIs Publicas

- `api/README.md` e a entrada da documentacao de APIs publicas.
- `api/http.md` resume grupos de rotas HTTP e limites de autorizacao.
- `api/realtime.md` documenta WebSocket, comandos, eventos e replay.
- `api/extensoes.md` documenta APIs de navegador para sistemas e modulos.
- `modulos.md` documenta Module API v1.
- `sistemas/README.md` e a entrada da System API v1.

## Relacao Com A Documentacao Em Ingles

A documentacao em ingles continua sendo a referencia principal para revisoes tecnicas de API. Esta arvore em portugues deve acompanhar os mesmos conceitos, comandos e alertas operacionais.
