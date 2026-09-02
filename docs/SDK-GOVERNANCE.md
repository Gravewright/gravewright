# Gravewright SDK governance / Governança do SDK Gravewright

## English

### Status and intent

The Gravewright SDK is evolving toward a stable public contract. Gravewright is currently pre-1.0, and its public architecture is still being refined. During the `0.x` series, public APIs may receive breaking changes when they materially improve the product, simplify the architecture, correct an unsuitable contract, or address security.

Evolution should be deliberate rather than disruptive by default. Additive changes are preferred when they preserve a clear design, but compatibility must not prevent important architectural simplification before `1.0`.

### Public API and internals

The public API consists of:

- documented exports of `@gravewright/sdk`;
- the public module manifest schema;
- contracts explicitly identified as public in the documentation;
- observable behavior described in the SDK reference as public behavior.

Internals include kernel data structures, loader implementation, private lifecycle details, unexported helpers, and modules not documented as public API. Internals may change at any time without backward-compatibility guarantees. Importing files outside a package's declared `exports` does not make them public API.

### Policy for `0.x` releases

- Public APIs may change incompatibly.
- Every known breaking change must be clearly identified in `CHANGELOG.md`.
- Release notes must explain the affected contract and the replacement behavior.
- Migration guidance and examples should be provided when reasonably possible.
- Deprecation is preferred when it provides useful transition time, but it is not mandatory during `0.x` when maintaining both designs would add disproportionate complexity or risk.
- Generated manifests and types affected by a change must have clear regeneration instructions.
- Security fixes may immediately reject previously accepted unsafe behavior.

Versioning follows SemVer for the current maturity level: patch releases contain compatible fixes and documentation updates where practical; minor `0.x` releases may contain additive features and documented breaking changes. Consumers should review the changelog before every `0.x` upgrade and test their complete composition.

### Change review

A public API change should state:

1. the user or architectural problem;
2. the public surfaces affected;
3. whether the change is compatible or breaking;
4. migration guidance, when reasonable;
5. test, documentation, and security impact.

The implementation, public types, English and Portuguese documentation, manifest schema when applicable, tests, and changelog should remain aligned in the same change. Experimental APIs must be explicitly marked and opt-in; they carry no stability guarantee until promoted to public stable status.

### Path to `1.0`

Stronger compatibility guarantees will be adopted as the SDK approaches `1.0`. Before the first stable release, maintainers will identify the supported public surface, document a formal deprecation window, define major-version migration expectations, and verify the contract with compatibility tests. Until then, the changelog and release documentation are the source of truth for upgrade impact.

### Security

No stability expectation requires preserving a vulnerability. Maintainers may tighten validation, constrain unsafe access, or disable exploitable behavior with the smallest practical impact. See [SECURITY.md](../SECURITY.md).

---

## Português

### Estado e intenção

O SDK Gravewright está evoluindo em direção a um contrato público estável. O Gravewright ainda está em fase pré-1.0 e sua arquitetura pública continua sendo refinada. Durante a série `0.x`, APIs públicas podem receber mudanças incompatíveis quando isso melhorar materialmente o produto, simplificar a arquitetura, corrigir um contrato inadequado ou resolver um problema de segurança.

A evolução deve ser deliberada, sem causar ruptura por padrão. Mudanças aditivas são preferíveis quando preservam um design claro, mas a compatibilidade não deve impedir simplificações arquiteturais importantes antes da versão `1.0`.

### API pública e internals

A API pública é composta por:

- exports documentados de `@gravewright/sdk`;
- schema público do manifest de módulo;
- contratos explicitamente identificados como públicos na documentação;
- comportamento observável descrito como público na referência do SDK.

Internals incluem estruturas internas do kernel, implementação do loader, detalhes privados de lifecycle, helpers não exportados e módulos não documentados como API pública. Internals podem mudar a qualquer momento, sem garantia de compatibilidade retroativa. Importar arquivos fora de `exports` declarados por um pacote não os transforma em API pública.

### Política para versões `0.x`

- APIs públicas podem sofrer mudanças incompatíveis.
- Toda breaking change conhecida deve ser identificada claramente no `CHANGELOG.md`.
- As notas da versão devem explicar o contrato afetado e o comportamento substituto.
- Orientações e exemplos de migração devem ser fornecidos quando for razoavelmente possível.
- Depreciação é preferível quando oferece uma transição útil, mas não é obrigatória em `0.x` quando manter os dois designs causar complexidade ou risco desproporcional.
- Mudanças que afetem manifests e tipos gerados devem ter instruções claras de regeneração.
- Correções de segurança podem rejeitar imediatamente comportamentos inseguros antes aceitos.

O versionamento segue a intenção do SemVer adequada à maturidade atual: versões patch contêm correções compatíveis e atualizações de documentação quando possível; versões minor `0.x` podem conter funcionalidades aditivas e breaking changes documentadas. Consumidores devem revisar o changelog antes de cada atualização `0.x` e testar sua composição completa.

### Revisão de mudanças

Uma mudança de API pública deve informar:

1. o problema de usuário ou arquitetura;
2. as superfícies públicas afetadas;
3. se a mudança é compatível ou incompatível;
4. orientações de migração, quando razoável;
5. impacto em testes, documentação e segurança.

Implementação, tipos públicos, documentação em inglês e português, schema do manifest quando aplicável, testes e changelog devem permanecer alinhados na mesma mudança. APIs experimentais devem ser explicitamente marcadas e opt-in; elas não possuem garantia de estabilidade até serem promovidas ao estado público estável.

### Caminho até `1.0`

Garantias de compatibilidade mais fortes serão adotadas conforme o SDK se aproximar da versão `1.0`. Antes da primeira versão estável, os mantenedores identificarão a superfície pública suportada, documentarão uma janela formal de depreciação, definirão expectativas de migração entre versões major e verificarão o contrato com testes de compatibilidade. Até lá, o changelog e a documentação de cada release são as fontes de verdade sobre o impacto de atualização.

### Segurança

Nenhuma expectativa de estabilidade exige preservar uma vulnerabilidade. Os mantenedores podem tornar validações mais estritas, restringir acessos inseguros ou desativar comportamentos exploráveis com o menor impacto prático. Consulte [SECURITY.md](../SECURITY.md).

