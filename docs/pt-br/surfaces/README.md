# Superfícies públicas

Cada página documenta uma fronteira explícita entre módulo, SDK e kernel.

## Autoria

- [`defineModule`](define-module.md) — declaração tipada do módulo.
- [`create`](create.md) — construção da instância runtime.
- [Manifest](manifest.md) — fronteira estática de validação.
- [Exports](exports.md) — lista pública de capacidades.
- [ModuleRegistry](module-registry.md) — registro de APIs no TypeScript.

## Comunicação

- [`use`](use.md) — referência revogável para uma dependência declarada.
- [`get`](get.md) — leitura de valor ou comando permitido.
- [`set`](set.md) — mutação cross-module genérica e deprecated.
- [`prop`](prop.md) — propriedade compartilhada legível e gravável.
- [Dependencies](dependencies.md) — nomes, SemVer, ordem e instalação.

## Composição

- [Routes](routes.md) — handlers finais de request.
- [Middleware](middleware.md) — handlers encadeados.
- [Slots](slots.md) — contribuições para pontos de extensão.
- [Contrato de server](server.md) — único kind obrigatório.

## Runtime

- [Diagnóstico](diagnostic.md) — eventos semânticos de auditoria opt-in.
- [Ciclo de vida e estado](lifecycle.md) — load, activate, compose, disable e dispose.
