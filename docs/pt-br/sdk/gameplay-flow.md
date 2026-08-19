# Fluxo de jogo

Um fluxo de jogo responde *quem age, e quando*. Ele ordena participantes por fases
nomeadas e registra o que cada um comprometeu, sem supor nada sobre o jogo em
andamento.

Não é um rastreador de combate. Um fluxo não tem dados, nem d20, nem iniciativa, nem
pontos de vida; nunca lê um ruleset. Uma campanha systemless roda uma sessão inteira
sobre ele, e um ruleset que queira iniciativa constrói isso por cima.

## Definição e instância

Uma **definição** nomeia as fases e o modelo de turno. Registre com
`sdk.gameplay.flows.register`.

```js
await sdk.gameplay.flows.register({
  id: "infiltration",
  schemaVersion: 1,
  turnModel: "SIMULTANEOUS",
  phases: [
    { id: "BRIEFING", label: "Briefing", submissionPolicy: "all" },
    { id: "PLANNING", label: "Planejamento", submissionPolicy: "all" },
    { id: "RESOLUTION", label: "Resolução", submissionPolicy: "all" },
  ],
});
```

Uma **instância** é uma execução, iniciada por um GM com
`sdk.gameplay.flows.start` e uma lista explícita de participantes. Leia com
`sdk.gameplay.flows.get` ou `sdk.gameplay.flows.list`.

## Modelos de turno

- **`SIMULTANEOUS`** — todos comprometem, e a fase revela quando o último terminar.
  É o modelo de compromisso secreto.
- **`SEQUENTIAL`** — um participante ativo por vez, na ordem dos participantes.
- **`PHASED`** — participantes agem dentro da fase sem um assento ativo por turno.

## Compromisso secreto e revelação

No `SIMULTANEOUS`, `sdk.gameplay.flows.submit` registra a escolha do participante e o
fluxo a mantém privada. Enquanto nem todos tiverem enviado, cada um vê apenas a
própria entrada em `submissions`, e `revealed` é `false`. Quando o último envio
chega, o fluxo revela e todos passam a ver o conjunto completo de uma vez.

O GM vê os envios o tempo todo, que é o que permite narrar.

Um envio é um compromisso: enviar duas vezes na mesma fase é recusado, e
`expectedVersion` torna envios concorrentes seguros. Avançar de fase com
`sdk.gameplay.flows.advance` limpa os envios e inicia a próxima rodada de
compromisso.

## Autoridade

Só um GM inicia um fluxo ou avança a fase. Só um participante listado pode enviar, e
apenas por si mesmo. Quem não é participante não consegue nem ler o fluxo.

## Ciclo de vida

O estado do fluxo é persistido, não guardado num cliente. Quem recarrega vê a fase
atual e o próprio compromisso vigente; quem entra depois vê a fase como ela está
agora. Uma fase pode ter `deadlineSeconds`, e nesse caso o core avança o fluxo quando
o prazo passa, em vez de esperar para sempre.

As fases são cíclicas: avançar além da última volta à primeira e incrementa os
contadores de rodada e ciclo. Um fluxo expressa conclusão ao chegar a uma fase que
significa conclusão no seu desenho — normalmente uma fase final chamada `COMPLETE`.

## Erros comuns

| Código | Causa |
|---|---|
| `VALIDATION_FAILED` | Definição malformada, participante desconhecido ou valor que não é JSON seguro. |
| `NOT_FOUND` | O fluxo não existe, ou quem chama não é participante nem GM. |
| `ALREADY_SUBMITTED` | Este participante já comprometeu nesta fase. |
| `NOT_ACTIVE_PARTICIPANT` | Modelo sequencial, e não é a vez deste participante. |
| `STALE_VERSION` | `expectedVersion` não confere mais. |

## O que esta API não expõe

Sem iniciativa, sem timers de turno controlados pelo pacote, sem enviar por outro
usuário e sem acesso ao compromisso alheio antes da revelação.
