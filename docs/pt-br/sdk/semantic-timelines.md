# Linhas do tempo semânticas

Uma linha do tempo semântica diz *o que deve acontecer, e quanto tempo depois do
início*. É a forma de compor uma sequência de efeitos semânticos já existentes — um
som, um letreiro, uma luz, um shader, um emissor de partículas — em um momento
autoral único.

O core é dono do relógio. O pacote declara offsets; ele não roda timer, e não pode
afirmar que algo aconteceu num instante com que o core não concordou.

## Timeline não é workflow

Elas parecem semelhantes e resolvem problemas opostos.

| | Timeline | Workflow durável |
|---|---|---|
| Espera por | um relógio | uma decisão ou um prazo |
| Ramifica | nunca | sobre o contexto, inclusive a resposta de um jogador |
| Uso típico | entrada cinematográfica, sequência de alarme, transição de ambiente | aprovação, negociação, procedimento de vários passos |

Se a sequência muda de forma conforme a escolha de alguém, é um workflow.

## Definição e instância

Uma **definição** é um id, uma versão de schema e uma lista de cues. Cada cue tem um
`cueId`, um `offsetMs` a partir do início, um tipo e os parâmetros desse tipo. O core
deriva `durationMs` do último cue; o pacote não o afirma.

```js
await sdk.timelines.register({
  id: "alarm-cascade",
  schemaVersion: 1,
  cues: [
    { cueId: "siren", offsetMs: 0, type: "AUDIO_PLAY", parameters: {
        asset: { kind: "library-asset", id: alarmAssetId }, channel: "sfx",
        gain: 0.9, audience: { kind: "campaign" }, sceneId } },
    { cueId: "warning", offsetMs: 0, type: "PRESENTATION_SHOW", parameters: {
        mode: "title-card", content: { title: "Alarme", text: "A segurança está respondendo." },
        audience: { kind: "campaign" } } },
    { cueId: "flare", offsetMs: 400, type: "LIGHT_CREATE", parameters: {
        x: 700, y: 350, bright_radius: 120, dim_radius: 320, color: "#ff2f3a" } },
    { cueId: "haze", offsetMs: 900, type: "PARTICLE_CREATE", parameters: {
        x: 700, y: 350, kind: "ember", density: 0.6, scale: 4 } },
  ],
});

await sdk.timelines.start({
  definitionId: "alarm-cascade",
  sceneId,
  audience: { kind: "campaign" },
  idempotencyKey: `alarm-cascade:${sceneId}`,
});
```

Uma **instância** é uma execução. Leia com `sdk.timelines.get` ou
`sdk.timelines.list`, e interrompa com `sdk.timelines.cancel`.

## Tipos de cue

`ACTION`, `AUDIO_PLAY`, `PRESENTATION_SHOW`, `LIGHT_CREATE`, `SHADER_PRESET`,
`PARTICLE_CREATE` e `NAVIGATION`. Cada um delega ao mesmo serviço autoritativo que a
chamada direta equivalente usaria, então uma timeline nunca faz algo que o pacote não
poderia ter feito sozinho.

Um cue `ACTION` só referencia ações registradas do próprio pacote em execução. Um cue
pode declarar `cleanupAction`, também própria, que o core executa para os cues já
disparados quando a timeline é cancelada.

## Início autoritativo e entrada tardia

A instância registra o momento em que começou. Um cliente que conecta depois é
projetado para o ponto correto: cues já vencidos são tratados como executados, em vez
de reproduzidos desde o início. É por isso que a unidade são offsets, e não timers
locais — quem chega tarde vê uma cena coerente, não uma sequência reiniciada.

Iniciar é idempotente via `idempotencyKey`, então uma repetição ou um segundo cliente
tentando a mesma cascata devolve a instância existente.

## Autoridade

A audiência segue a mesma regra de sempre: um GM pode endereçar a campanha ou
usuários nomeados, e um jogador só a si mesmo. Os parâmetros de cue são validados
pelo domínio dono, então um preset de shader inválido ou uma partícula fora de faixa
é recusado em vez de aplicado pela metade.

## Ciclo de vida

A execução de cues é receitada, então a recuperação após reinício não redispara um
cue já executado. Cancelar roda a limpeza declarada para os cues disparados.
Descarregar o pacote provedor encerra suas timelines em execução.

## Erros comuns

| Código | Causa |
|---|---|
| `VALIDATION_FAILED` | Tipo de cue desconhecido, `cueId` duplicado, offset fora do limite, referência de ação alheia ou parâmetros inválidos. |
| `NOT_FOUND` | Definição desconhecida, ou instância que o chamador não pode ver. |
| `PERMISSION_DENIED` | A audiência é maior do que quem chama pode endereçar. |

## O que esta API não expõe

Sem chamadas cruas ao renderer, sem GLSL, sem timers do pacote e sem agendar ações de
outro pacote.
