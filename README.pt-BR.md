# Gravewright

**Construa um virtual tabletop a partir de módulos, não de premissas.**

Gravewright é uma plataforma open source para criar Virtual Tabletops com módulos independentes e substituíveis. Ela oferece um pequeno microkernel TypeScript e deixa cada distribuição decidir como sua mesa, regras, backend, extensões e transporte devem funcionar.

[English](README.md) · [Documentação](docs/README.md) · [Criar um módulo](docs/pt-br/criando-um-modulo.md) · [Prontidão de release](docs/pt-br/reference/prontidao-de-release.md)

## Um kernel, muitos VTTs

```text
                         ┌─────────────────────┐
                         │ Gravewright Kernel  │
                         │ valida · compõe     │
                         │ ciclo de vida       │
                         └──────────┬──────────┘
                                    │
                            um server ativo
                                    │
                ┌───────────┬───────┴───────┬───────────┐
                │           │               │           │
              Room       Ruleset          Addon       Backend
          campanha/mesa  regras         extensões     backend
```

Use os módulos oficiais, substitua apenas uma parte da stack ou publique uma experiência completamente diferente. O kernel coordena o sistema sem controlar suas decisões de produto.

## O que o Gravewright oferece

- Um microkernel pequeno para validação, composição e ciclo de vida.
- Manifests estáticos, inspecionados antes da execução do código do módulo.
- Resolução concreta, estrutural e semântica tipada por `ctx.use()`, `ctx.kind()` e `ctx.capability()`.
- Routes, middleware e slots sem acoplar módulos a um framework web.
- Scaffold, diagnóstico, verificação de ambiente e tooling pela CLI `grave`.
- Marketplace baseado em releases verificadas e recipes reproduzíveis.

Todo projeto em execução possui exatamente um `server`, uma `room` e um `ruleset`
ativos. `chat`, `dice-engine`, `assets` e `storage` são singletons opcionais;
`backend` e `addon` são plurais.

## Início rápido

```bash
npm install
npm test
npm run typecheck
npm run grave -- doctor
npm run grave -- run
```

O `gravewright.modules.json` versionado é a composição padrão deste repositório.
A instalação pelo marketplace nunca altera o estado de ativação automaticamente.

O marketplace padrão fica disponível em `http://127.0.0.1:3000/marketplace`.

## Crie um módulo

```bash
npm run grave -- new addon fog-of-war
npm run grave -- module build modules/fog-of-war
npm run grave -- doctor
```

Comece pelos [primeiros passos para autores](docs/pt-br/getting-started/README.md), use o [guia completo](docs/pt-br/criando-um-modulo.md), copie um [template mínimo](docs/minimal-templates/) ou estude os [exemplos completos](docs/examples/).

## Princípios

- **Kernel pequeno:** mecanismos pertencem ao núcleo; políticas de produto não.
- **Implementações substituíveis:** nenhum renderer, ruleset ou storage é universal.
- **Contratos explícitos:** dependências e capacidades públicas são declaradas e validadas.
- **Lifecycle transacional:** a ativação é planejada; recursos fazem rollback e shutdown em ordem inversa.
- **Capabilities substituíveis:** consumidores exigem contratos versionados e recipes escolhem providers.
- **Composição em vez de acoplamento:** um VTT é um conjunto de módulos compatíveis.
- **Evolução independente:** módulos podem ser mantidos e publicados separadamente.
- **Liberdade de distribuição:** Gravewright é uma fundação, não um VTT prescrito.

## Workspace

```text
gravewright/
├── bin/                 executável `grave`
├── docs/                documentação, templates e exemplos
├── modules/             módulos instalados
│   ├── gravewright-server/       implementação mínima de server
│   └── gravewright-marketplace/  catálogos, instalação e recipes
├── packages/
│   ├── kernel/          runtime do microkernel (Apache-2.0)
│   └── sdk/             contratos públicos (MIT)
├── scripts/             tooling de desenvolvimento
├── src/                 host e CLI
└── tests/               testes do kernel, CLI e tooling
```

## Licença

`@gravewright/sdk` usa MIT. `@gravewright/kernel` usa Apache-2.0. Módulos de terceiros permanecem sujeitos às suas próprias licenças.

Consulte [CONTRIBUTING.md](CONTRIBUTING.md) antes de enviar mudanças e
[SECURITY.md](SECURITY.md) para relatar vulnerabilidades de forma privada.
