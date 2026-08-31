# Documentação do Gravewright

[English](../en/README.md) · [README do projeto](../../README.pt-BR.md)

Gravewright é um microkernel TypeScript para compor um virtual tabletop com
módulos independentes e versionados. Este manual é organizado por tarefa:
entender o modelo, construir um módulo funcional, explorar um subsistema ou
consultar um contrato exato.

## Escolha seu caminho

| Se você quer… | Comece aqui |
| --- | --- |
| Entender o que é o Gravewright | [Introdução](about/introducao.md) |
| Executar o repositório pela primeira vez | [Primeiros passos](getting-started/README.md) |
| Criar seu primeiro módulo | [Seu primeiro módulo](getting-started/primeiro-modulo.md) |
| Entender a arquitetura | [Conceitos fundamentais](concepts/README.md) |
| Resolver uma tarefa específica | [Guias](guides/README.md) |
| Consultar uma fronteira do SDK ou kernel | [Referência](reference/README.md) |
| Diagnosticar uma falha | [Solução de problemas](solucao-de-problemas.md) |

## Seções da documentação

- **Primeiros passos** é sequencial: do checkout até um módulo validado.
- **Conceitos fundamentais** explica módulos, kinds, manifests, capabilities,
  composição e lifecycle.
- **Guias** são orientados a tarefas e podem ser lidos separadamente.
- **Referência** descreve comandos, schemas e superfícies do runtime.
- **Exemplos e templates** contêm código para executar, copiar e modificar.

## Invariantes importantes

- Um projeto em execução possui exatamente um `server` ativo.
- Módulos `room`, `ruleset`, `addon` e `system` têm cardinalidade `0..n`.
- Todo módulo exporta ao menos os comandos `read`, `write` e `stat`.
- Um módulo só pode usar outro módulo concreto se declarar a dependência.
- Manifests estáticos são validados antes da importação do código.
- Instalar nunca ativa um módulo implicitamente.

## Recursos de código

- [Templates mínimos](../minimal-templates/README.md)
- [Exemplos completos](../examples/README.md)
- [Guia completo de autoria](criando-um-modulo.md)

Se a documentação e o runtime divergirem, isso é um bug. Abra uma issue com a
página, o comando executado e a saída observada.
