# Workflows duráveis

Um workflow durável coordena um processo autoritativo de vários passos que pode
precisar esperar — pela decisão de um jogador ou por um prazo — e ainda assim
continuar correto depois de recarregar o navegador, recarregar o pacote ou reiniciar
o servidor.

Ele não é um script, de propósito. Um workflow é *dado*: cada passo executável vem de
um conjunto fechado, e todo o estado de suspensão vive no core. O pacote descreve o
processo uma vez e nunca guarda o estado pendente.

## Definição e instância

Uma **definição** é o formato do processo: um id, uma versão de schema, uma lista
ordenada de passos e os limites que aceita (`maxDuration`, `maxSteps`). Registre com
`sdk.workflows.register`.

Uma **instância** é uma execução daquela definição, iniciada com
`sdk.workflows.start`. Iniciar é idempotente via `idempotencyKey`: a mesma chave
devolve a mesma instância em vez de começar outra. A instância congela a definição
com que começou, então registrar uma definição alterada nunca reescreve uma execução
em andamento.

Leia instâncias com `sdk.workflows.get` e `sdk.workflows.list`; encerre uma antes do
fim com `sdk.workflows.cancel`.

## Passos

| Passo | Significado |
|---|---|
| `ACTION` | Executa uma das suas ações registradas. |
| `INTERACTION` | Pede uma decisão a um usuário e suspende até a resposta. |
| `WAIT_UNTIL` | Suspende até um instante absoluto ou por N segundos. |
| `BRANCH` | Compara uma chave do contexto e salta para um de dois passos. |
| `SET` | Escreve um literal no contexto do workflow. |
| `COMPLETE` | Termina com sucesso. |
| `FAIL` | Termina sem sucesso, com um motivo. |

`BRANCH` só salta para frente, então uma definição não pode formar laço.

## Decidir pela resposta de um jogador

Um passo `INTERACTION` pode declarar um `resultKey` opcional. Quando a interação
termina, o core grava o *valor* da resposta do destinatário — nunca o objeto da
interação — em `context[resultKey]`, e o passo `BRANCH` comum lê essa chave como
qualquer outra.

```js
await sdk.workflows.register({
  id: "breach-response",
  schemaVersion: 1,
  maxDuration: 3600,
  steps: [
    { type: "ACTION", action: "my-package:alarm.raise@1", input: { actorId } },
    {
      type: "INTERACTION",
      resultKey: "response",
      request: {
        recipients: [operativeUserId],
        title: "Resposta de segurança",
        text: "Suprimir o alarme?",
        responseSchema: { type: "single-choice", choices: [
          { id: "SUPPRESS", label: "Suprimir" },
          { id: "IGNORE", label: "Deixar tocar" },
        ] },
        deadline: Math.floor(Date.now() / 1000) + 900,
      },
    },
    { type: "BRANCH", key: "response", equals: "SUPPRESS", then: 3, else: 4 },
    { type: "ACTION", action: "my-package:alarm.suppress@1", input: { actorId } },
    { type: "COMPLETE", reason: "resolved" },
  ],
});

await sdk.workflows.start({
  definitionId: "breach-response",
  sceneId,
  idempotencyKey: `breach:${sceneId}`,
});
```

Como um branch escalar não representa divergência, `resultKey` só vale em uma
requisição com exatamente um destinatário. A chave deve ser um identificador local do
workflow e não pode ocupar os slots do runtime `input`, `lastResult` ou
`interaction`.

## Autoridade

O workflow age como o usuário que o iniciou, nunca como o destinatário da pergunta.
Saber quem foi perguntado não concede nada: a resposta só é aceita do destinatário
autenticado, e cada passo `ACTION` é autorizado contra a autoridade atual do usuário
que iniciou, no momento em que roda. Um workflow é visível para seu dono e para o GM.

## Ciclo de vida e recuperação

A suspensão é persistida, então um workflow em espera não é uma promessa guardada no
navegador. Quem recarrega continua vendo a decisão pendente; um servidor que
reinicia retoma do passo onde parou. Cada passo registra um recibo, então uma
conclusão repetida avança a execução uma única vez e nenhuma ação executa duas vezes.

Cancelamento, expiração e falha do provider nunca inventam uma resposta: `resultKey`
apenas fica ausente, e uma definição que precise tratar recusa faz o branch sobre a
chave ausente. Se o pacote provedor for descarregado, suas instâncias em execução são
encerradas em vez de ficarem órfãs.

## Erros comuns

| Código | Causa |
|---|---|
| `VALIDATION_FAILED` | Passo fora do conjunto fechado, branch para trás, `resultKey` inválido ou limite excedido. |
| `NOT_FOUND` | Definição desconhecida, ou instância que o chamador não pode ver. |
| `PERMISSION_DENIED` | Pacote ou usuário sem autoridade para a operação. |
| `STALE_VERSION` | `expectedVersion` não confere mais no cancelamento. |

## O que esta API não expõe

Sem callbacks, sem código arbitrário, sem timers do pacote e sem forma de observar ou
alterar os workflows de outro pacote.
