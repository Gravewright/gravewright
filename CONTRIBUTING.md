# Contributing / Como contribuir

## English

Thank you for helping Gravewright become a dependable extensible VTT. Contributions may improve the product, kernel, SDK, CLI, UI language, documentation, tests, or examples.

### Before opening a change

1. Search existing issues and discussions. For a bug, include a minimal reproduction; for a feature, describe the user problem before the API.
2. Keep changes focused. Discuss broad architecture, new manifest fields, and public SDK contracts before implementing them.
3. Never commit credentials, private module archives, personal data, generated diagnostics, or dependency directories.

### Development workflow

Requires Node.js 24 or newer.

```bash
npm ci
npm test
npm run typecheck
npm run build
npm run pack:dry
npm run smoke:packages
```

Use `npm run grave -- new module <name> --dry-run` to preview scaffolding. If a module uses `defineModule`, run `npm run grave -- module build <path>` and commit both generated `manifest.json` and `types.ts`. CI checks tests, types, builds, package contents, and consumer smoke tests.

Public SDK changes must follow the [SDK governance policy](docs/SDK-GOVERNANCE.md): prefer additive evolution, document compatibility, add tests, and provide a migration path. Add notable user-facing changes to `CHANGELOG.md`.

Pull requests should explain the problem, chosen behavior, compatibility impact, verification performed, and any security implications. By contributing, you agree that your work is distributed under the license of the package or file it modifies.

## Português

Obrigado por ajudar a tornar o Gravewright um VTT extensível e confiável. Contribuições podem melhorar o produto, kernel, SDK, CLI, UI, documentação, testes ou exemplos.

Antes de propor uma mudança, procure issues e discussões existentes. Para bugs, envie uma reprodução mínima; para funcionalidades, descreva primeiro o problema do usuário. Discuta previamente alterações arquiteturais, novos campos de manifest e contratos públicos do SDK. Nunca envie credenciais, arquivos privados, dados pessoais ou diagnósticos.

Use Node.js 24 ou superior e execute os comandos de verificação da seção em inglês. Para módulos criados com `defineModule`, execute `npm run grave -- module build <caminho>` e versione `manifest.json` e `types.ts`. Mudanças públicas devem seguir a [governança do SDK](docs/SDK-GOVERNANCE.md), incluir testes e orientações de migração quando razoável. Registre mudanças relevantes no `CHANGELOG.md`.

O pull request deve explicar o problema, o comportamento escolhido, o impacto de compatibilidade, as verificações e as implicações de segurança. A contribuição será distribuída sob a licença do pacote ou arquivo alterado.
