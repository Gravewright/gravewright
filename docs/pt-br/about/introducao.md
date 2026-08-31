# Introdução

[Início da documentação](../README.md) · [English](../../en/about/introduction.md)

Gravewright é uma fundação open source para construir virtual tabletops. Ele não
é uma mesa pronta, um renderer ou um motor de regras. É o pequeno runtime que
valida e compõe essas partes.

## Qual problema ele resolve?

Implementações de VTT frequentemente acoplam transporte, estado de campanha,
regras, storage e apresentação numa aplicação. Substituir uma parte passa a
exigir um fork ou a reescrita da stack. O Gravewright dá a cada parte uma
fronteira explícita, permitindo trocar uma implementação sem alterar o kernel.

```text
projeto
├── exatamente um server      transporte e integração com o host
├── zero ou mais rooms        experiências de campanha/mesa
├── zero ou mais rulesets     mecânicas do jogo
├── zero ou mais addons       extensões opcionais
└── zero ou mais backends      serviços de backend
```

O kernel conhece esses cinco papéis e seus contratos mínimos. Ele não conhece
Express, SQLite, PixiJS, um jogo específico ou um marketplace específico.

## As duas fronteiras

Um módulo possui uma fronteira estática e outra de runtime:

1. `manifest.json` permite inspecionar identidade, dependências, capabilities,
   pontos de composição e nomes públicos antes de importar código.
2. `create(ctx)` constrói a instância somente depois que o plano é validado.

O manifest é uma fronteira de validação e composição, não um sandbox de
segurança. O JavaScript instalado executa com as permissões do processo host.

## O que ler agora

- Novo no repositório: [Primeiros passos](../getting-started/README.md).
- Avaliando o design: [Arquitetura](../concepts/arquitetura.md).
- Pronto para codar: [Seu primeiro módulo](../getting-started/primeiro-modulo.md).
- Procurando uma API exata: [Referência](../reference/README.md).
