# Documentação do Gravewright

[English](../en/README.md) · [README do projeto](../../README.pt-BR.md)

## Autores de módulos

- [Criando um módulo](criando-um-modulo.md): fluxo completo, manifest, SDK, tipos, dependências, composição, diagnóstico, testes e releases.
- [Superfícies públicas](surfaces/README.md): uma página detalhada para cada fronteira do SDK e kernel.
- [Templates mínimos](../minimal-templates/README.md): bases pequenas feitas para copiar.
- [Exemplos completos](../examples/README.md): módulos funcionais e documentados.

## Conceitos fundamentais

- Um módulo é uma capacidade versionada independentemente.
- Seu `manifest.json` estático é a fronteira de segurança e composição.
- Seu export default é criado com `defineModule()`.
- Sua API TypeScript pública amplia `ModuleRegistry` em `types.ts`.
- Módulos ficam desabilitados até serem marcados como `active` em `gravewright.modules.json`.
- Exatamente um módulo ativo deve implementar o kind `server`.
