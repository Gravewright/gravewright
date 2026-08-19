# Quadro de membros e controle de Token

Existem duas leituras para que um pacote consiga *endereçar* a pessoa certa: quem
está nesta mesa, e quem conduz este token.

## `sdk.campaign.members()`

Devolve o quadro de membros da campanha — a mesma associação que a mesa nativa já
mostra a quem chama.

```js
const roster = await sdk.campaign.members();
// [{ userId, role, name }, ...]
const players = roster.filter((member) => member.role === "player");
```

Cada entrada traz um id de usuário, o papel do membro nesta campanha e um nome de
exibição. Só isso: sem e-mail, sem metadados de conta, sem credenciais.

O quadro é associação, **não presença**. Diz quem pertence à campanha, não quem está
conectado agora; não há status online aqui nem feed de presença por trás. Releia
quando precisar da associação atual — um membro removido some da próxima leitura
autoritativa.

A chamada é restrita à campanha e só responde a quem já é membro. Não há diretório
entre campanhas nem enumeração global de usuários.

Requer `campaign.members.read`.

## `TokenDTO.controllers`

Todo token que você consegue ler traz os usuários que podem controlá-lo.

```js
const token = await sdk.tokens.get(tokenId, { sceneId });
// token.controllers -> ["gm-user-id", "player-user-id"]
```

São as relações canônicas de controle, derivadas da mesma autoridade que decide se um
movimento é permitido. Um token com dois donos lista os dois, mais o GM; a lista nunca
é reduzida a um único usuário "principal", porque o pacote deve escolher sua própria
política de destinatário em vez de herdar a nossa.

**A projeção é filtrada.** Ver um token no tabuleiro não é autoridade para saber quem
o conduz: controladores só são devolvidos para tokens que quem chama poderia
controlar. Um jogador vê controladores no próprio token e lista vazia no token de
outro, que é o que impede um tabuleiro compartilhado de virar canal lateral de
enumeração. Um token oculto está ausente por completo, controladores incluídos.

## Endereçar, não delegar

Um id de controlador é uma referência de endereçamento. Não concede nada.

Saber que um usuário controla um token não permite ao pacote mover esse token,
responder como esse usuário ou executar algo em nome dele. Toda operação seguinte
continua derivando seu principal da sessão autenticada.

## Fluxo típico

Reagir a alguém entrando numa região e pedir *àquela* pessoa que decida:

```js
sdk.events.on("zone.entered", async (event) => {
  const zone = await sdk.scene.zones.get(event.zone_id);
  if (zone?.type !== "my-package.restricted") return;

  const token = await sdk.tokens.get(event.token_id, { sceneId: event.scene_id });
  const roster = await sdk.campaign.members();
  const players = new Set(roster.filter((m) => m.role === "player").map((m) => m.userId));
  const recipient = (token?.controllers || []).find((userId) => players.has(userId));
  if (!recipient) return;

  await sdk.interactions.request({
    recipients: [recipient],
    title: "Área restrita",
    text: "Você cruzou a linha. Continuar?",
    responseSchema: { type: "boolean" },
    deadline: Math.floor(Date.now() / 1000) + 300,
  });
});
```

O evento de zona fornece um id de token; o token resolve a pessoa; o quadro de membros
diz qual delas é jogador em vez de GM. A decisão então pertence apenas ao
destinatário autenticado.

## Erros comuns

| Código | Causa |
|---|---|
| `CAPABILITY_REQUIRED` | `campaign.members.read` não foi declarada. |
| `PERMISSION_DENIED` | Quem chama não é membro da campanha solicitada. |

## O que estas APIs não expõem

Sem presença, sem identidade de conta além do nome de exibição, sem consulta entre
campanhas e sem informação de controlador para tokens que quem chama não poderia
controlar.
