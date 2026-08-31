# Referência

- [Status da API pública](status-da-api-publica.md)
- [Compatibilidade e versionamento](compatibilidade.md)
- [Prontidão de release](prontidao-de-release.md)
- [Guia de atualização](guia-de-atualizacao.md)

Estas páginas descrevem o contrato atual com precisão. São feitas para consulta,
não para leitura sequencial.

## Tooling

- [Referência da CLI](cli.md)
- [Manifest](../surfaces/manifest.md)
- [`defineModule`](../surfaces/define-module.md)
- [`ModuleRegistry`](../surfaces/module-registry.md)

## Superfícies de runtime

- [Índice completo](../surfaces/README.md)
- [`use`](../surfaces/use.md) e [`get`](../surfaces/get.md)
- [Routes](../surfaces/routes.md), [middleware](../surfaces/middleware.md) e [slots](../surfaces/slots.md)
- [Contrato do server](../surfaces/server.md)
- [ABI de slots da room](../surfaces/room-slots.md)
- [Lifecycle](../surfaces/lifecycle.md)

Contratos públicos são definidos por `@gravewright/sdk`; a garantia de runtime
vive em `@gravewright/kernel`. Um tipo TypeScript sozinho não concede permissão.
