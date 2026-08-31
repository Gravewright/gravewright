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
- [Dependencies](dependencies.md) — nomes, SemVer, ordem e instalação.
- [Recipes](recipes.md) — composições reproduzíveis e escolha de providers.

## Composição

- [Routes](routes.md) — handlers finais de request.
- [Middleware](middleware.md) — handlers encadeados.
- [Slots](slots.md) — contribuições para pontos de extensão.
- [Slots de room](room-slots.md) — regiões DOM garantidas e contribuições visuais isoladas.
- [Contrato de server](server.md) — contrato obrigatório de transporte.
- [`read`, `write`, `stat`](read-write-stat.md) — hooks opcionais de tooling administrativo.

## Runtime

- [Diagnóstico](diagnostic.md) — eventos semânticos de auditoria opt-in.
- [Ciclo de vida e estado](lifecycle.md) — load, activate, compose, disable e dispose.
