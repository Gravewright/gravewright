# Rolagens

Rolagens sao configuradas em arquivos de regras, normalmente `rules/actions.gw.json`.

## Contrato

Uma acao de rolagem declara intent, formula, contexto e apresentacao. O servidor avalia a formula e publica resultado para chat, toast ou outros destinos suportados.

## Boas Praticas

- Use intents estaveis.
- Evite formulas que dependam de estado nao declarado.
- Teste rolagens com atores e itens reais do sistema.
