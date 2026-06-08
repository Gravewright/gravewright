# System API v1: Rolls

Rolagens sao declaradas em `rules/actions.gw.json`. A API separa a intencao da rolagem da apresentacao visual: `intent` diz o que a rolagem significa, enquanto `chatCard`, `rollToast` e CSS dizem como ela aparece.

Exemplo:

```json
{
  "actions": {
    "roll.initiative": {
      "type": "roll",
      "label": "Iniciativa",
      "intent": "initiative",
      "formula": "1d20 + @sheet.combat.initiative",
      "visibility": "public",
      "chatCard": "initiative"
    }
  }
}
```

Intents v1:

- `check`: teste de atributo ou pericia.
- `save`: salvaguarda.
- `attack`: ataque.
- `damage`: dano.
- `initiative`: iniciativa.
- `skill`: pericia.
- `tool`: ferramenta.
- `custom`: tipo especifico do sistema.

O `dialog.intent` pode sobrescrever o `intent` da action quando a mesma action abre modos diferentes de rolagem. Transformacoes continuam declarativas: `replaceFirstDie`, `append`, `appendEach` e expressoes `when` usam os dados de `sheet` e `input`.
