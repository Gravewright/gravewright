# Rolagens Autoritativas

Rolagens no Gravewright sao avaliadas no servidor. Um pacote envia uma formula
ou uma intencao de action; o engine avalia os dados, monta os grupos de rolagem,
renderiza o card de chat, transmite o resultado e devolve a mesma resposta
autoritativa ao chamador.

Use este guia para qualquer estilo de ruleset. O motor de formulas e neutro:
dado de passo, vantagem/desvantagem, pools de sucesso, dados variaveis, Fate,
draw de cartas e helpers usam o mesmo caminho.

## Sintaxe de Formula

| Recurso | Sintaxe | Notas |
|---|---|---|
| Aritmetica | `+ - * /`, parenteses, `-` unario | Precedencia padrao. |
| Comparacao e logica | `== != < <= > >=`, `&&`, `||` | Retorna `1` ou `0`. |
| Paths do ator | `@core.name`, `@sheet.strength`, `@sheet.rank` | `@sheet` e o bloco de dados de sistema/ficha do ator. Paths ausentes valem `0`. |
| Escopo de input | `input.amount` | Usado por actions declarativas com inputs de runtime. |
| Notacao de dados | `1d20`, `2d6`, `2d20kh1`, `2d20kl1` | `kh1` mantem o maior; `kl1` mantem o menor. |
| Dados dinamicos | `die(sides)`, `die(count, sides)` | Lados e quantidade podem vir de `@paths`. |
| Dado explosivo | `explode(sides, threshold)` | Rola `1d{sides}` ate sair abaixo do limiar. |
| Pool de sucesso | `successes(count, sides, target)` | Conta dados iguais ou acima do alvo. |
| Roll under | `under(count, sides, target)` | Conta dados iguais ou abaixo do alvo. |
| Fate | `fate()` | Rola quatro dados Fate/Fudge como `4dF`. |
| Carta | `draw(n)` | Sorteia um indice de carta em um baralho de tamanho `n`. |
| Builtins | `floor`, `ceil`, `round`, `abs`, `min`, `max`, `clamp`, `if` | `if(cond, a, b)` retorna `a` quando `cond != 0`. |
| Helpers | `abilityMod(@sheet.str.score)` | Helpers ficam em `rules/formulas.gw.json`. |

## Limites de Seguranca

Formulas sao parseadas por um avaliador proprio. Elas nao executam JavaScript,
Python, SQL ou codigo do pacote.

| Limite | Valor |
|---|---:|
| Tamanho maximo da expressao | `200` caracteres |
| Quantidade maxima por grupo de dados | `100` |
| Maior numero de lados | `1000` |
| Profundidade maxima de helpers | `16` |

Formulas invalidas, dados fora dos limites, helpers ruins e divisao por zero
falham no servidor.

## Padroes de Sistema

| Padrao | Formula |
|---|---|
| Dado de passo com explosao | `explode(@sheet.traitDie, @sheet.traitDie)` |
| Vantagem | `2d20kh1` ou `max(1d20, 1d20)` |
| Desvantagem | `2d20kl1` ou `min(1d20, 1d20)` |
| Pool de sucesso | `successes(@sheet.pool, 10, 8)` |
| Pool roll-under | `under(@sheet.pool, 20, @sheet.target)` |
| Dado de atributo variavel | `die(@sheet.attributeDie)` |
| Varios dados variaveis | `die(@sheet.count, @sheet.sides)` |
| Fate com modificador | `fate() + @sheet.approach` |
| Checagem com limite | `clamp(1d20 + @sheet.bonus, 1, 30)` |

Cada expressao de dado contribui uma entrada em `groups`:

```json
{
  "notation": "2d20kh1",
  "results": [4, 17],
  "subtotal": 17
}
```

## API de Runtime

### `sdk.dice.roll({ formula, label?, actorId? })`

Requer `dice.roll`.

Envia `POST /game/actor/roll`. Use quando o pacote ja conhece a formula e so
precisa de uma rolagem autoritativa com card de chat.

```js
await sdk.dice.roll({
  actorId: ctx.actor.id,
  label: "Strength",
  formula: "explode(die(@sheet.strengthDie), @sheet.strengthDie)"
});
```

### `sdk.rolls.intent({ actorId, actionId, inputs?, rollOptions?, target? })`

Requer `rolls.intent`.

Envia `POST /game/actor/action`. Use para actions declarativas de Sheet IR,
targets, dano aplicado, iniciativa ou qualquer action definida em
`rules/actions.gw.json`.

```js
await sdk.rolls.intent({
  actorId: ctx.actor.id,
  actionId: "attack.primary",
  inputs: { calledShot: false },
  rollOptions: { visibility: "public" },
  target: { actorId: targetActorId, tokenId: targetTokenId }
});
```

Os dois metodos retornam a resposta do servidor:

```json
{
  "actor_id": "actor-id",
  "type": "roll",
  "label": "Strength",
  "expression": "1d20 + @sheet.bonus",
  "groups": [],
  "modifier": 0,
  "total": 12,
  "visibility": "public",
  "metadata": { "rendered": {} },
  "applied": []
}
```

## Fichas HTML

Fichas HTML sem controller podem rolar:

```html
<button
  type="button"
  data-roll="2d20kh1 + @sheet.attackBonus"
  data-roll-label="Attack">
  Attack
</button>
```

O pacote precisa declarar `dice.roll`. O runtime le o actor id do contexto da
ficha montada e chama `sdk.dice.roll` pelo mesmo gate de capability.

Use controller quando a formula for escolhida dinamicamente:

```js
sdk.sheets.registerController("character", {
  async onAction(action, ctx) {
    if (action.name !== "roll-attribute") return;
    await sdk.dice.roll({
      actorId: ctx.actor.id,
      label: action.element.dataset.label,
      formula: action.element.dataset.formula
    });
  }
});
```

Prefira actions de Sheet IR e `sdk.rolls.intent` quando a rolagem tambem aplica
dano, atualiza estado, usa target de ator/token ou participa de iniciativa.
