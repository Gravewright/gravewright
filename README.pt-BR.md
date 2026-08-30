# Gravewright

**Construa um virtual tabletop a partir de módulos, não de premissas.**

Gravewright é uma plataforma open source para criar Virtual Tabletops com módulos independentes e substituíveis. Ela oferece um pequeno microkernel TypeScript e deixa cada distribuição decidir como campanhas, salas, regras, renderização, assets, interface e descoberta devem funcionar.

[English](README.md) · [Documentação](docs/README.md) · [Criar um módulo](docs/pt-br/criando-um-modulo.md)

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
          ┌─────────────┬───────────┼───────────┬─────────────┐
          │             │           │           │             │
      Campaign         Room       Ruleset   Marketplace       UI
                        │                       │
                    Renderer                Módulos e
                        │                    Recipes
                      Assets
```

Use os módulos oficiais, substitua apenas uma parte da stack ou publique uma experiência completamente diferente. O kernel coordena o sistema sem controlar suas decisões de produto.

## O que o Gravewright oferece

- Um microkernel pequeno para validação, composição e ciclo de vida.
- Manifests estáticos, inspecionados antes da execução do código do módulo.
- APIs tipadas através de `@gravewright/sdk` e `ctx.use()`.
- Routes, middleware e slots sem acoplar módulos a um framework web.
- Scaffold, diagnóstico, verificação de ambiente e tooling pela CLI `grave`.
- Marketplace baseado em releases verificadas e recipes reproduzíveis.

O único requisito estrutural é exatamente um módulo `server` ativo. Gravewright define o contrato mínimo, não a implementação: Express, Fastify ou outro transporte pode satisfazê-lo.

## Início rápido

```bash
npm install
npm test
npm run typecheck
npm run grave -- doctor
npm run grave -- run
```

O marketplace padrão fica disponível em `http://127.0.0.1:3000/marketplace`.

## Crie um módulo

```bash
npm run grave -- new addon fog-of-war
npm run grave -- module build modules/fog-of-war
npm run grave -- doctor
```

Comece pelo [guia de autoria](docs/pt-br/criando-um-modulo.md), copie um [template mínimo](docs/minimal-templates/) ou estude os [exemplos completos](docs/examples/).

## Princípios

- **Kernel pequeno:** mecanismos pertencem ao núcleo; políticas de produto não.
- **Implementações substituíveis:** nenhum renderer, ruleset ou storage é universal.
- **Contratos explícitos:** dependências e capacidades públicas são declaradas e validadas.
- **Composição em vez de acoplamento:** um VTT é um conjunto de módulos compatíveis.
- **Evolução independente:** módulos podem ser mantidos e publicados separadamente.
- **Liberdade de distribuição:** Gravewright é uma fundação, não um VTT prescrito.

## Workspace

```text
gravewright/
├── bin/                 executável `grave`
├── docs/                documentação, templates e exemplos
├── modules/             módulos instalados
│   ├── server/          implementação mínima de server
│   └── marketplace/     catálogos, instalação e recipes
├── packages/
│   ├── kernel/          runtime do microkernel (Apache-2.0)
│   └── sdk/             contratos públicos (MIT)
├── scripts/             tooling de desenvolvimento
├── src/                 host e CLI
└── tests/               testes do kernel, CLI e tooling
```

## Licença

`@gravewright/sdk` usa MIT. `@gravewright/kernel` usa Apache-2.0. Módulos de terceiros permanecem sujeitos às suas próprias licenças.
