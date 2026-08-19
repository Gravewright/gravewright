# Transferência de token

A transferência de token move um token de uma Scene para outra preservando o que
importa: continua sendo o mesmo token, pertencendo às mesmas pessoas, com a mesma
identidade que todo o resto já referencia.

## Transferência não é navegação

Mover um token e mover um ponto de vista são atos separados, e a SDK os mantém
separados de propósito.

- `sdk.tokens.transfer` / `sdk.tokens.transferMany` movem um token entre Scenes.
- `sdk.navigation.scene.go` muda qual Scene um usuário está vendo.

Uma transferência sozinha não move a visão de ninguém. Um GM pode realocar os tokens
do grupo enquanto os jogadores continuam olhando o que olhavam, e um jogador pode
acompanhar a ação sem que seu token saia do lugar. Se quiser os dois, faça os dois — a
transferência aceita um `navigateAudience` opcional exatamente para isso, e ainda
assim é auditada como uma navegação própria.

## Transferência individual e em grupo

```js
// Um token.
await sdk.tokens.transfer(tokenId, { sceneId: innerVaultId, x: 12, y: 8 });

// O grupo inteiro, atomicamente.
await sdk.tokens.transferMany([
  { tokenId: tokenA, sceneId: innerVaultId, x: 12, y: 8 },
  { tokenId: tokenB, sceneId: innerVaultId, x: 13, y: 8 },
]);
```

`transferMany` é tudo ou nada. Se qualquer token do lote falhar — `expectedVersion`
desatualizado, token que quem chama não controla, destino que não pode ver — nada se
move. O grupo não pode ser dividido por uma falha parcial, que é justamente a razão
de a operação em lote existir.

## Identidade, propriedade e coordenadas

O token mantém id, vínculo com o ator, propriedade e overrides. As coordenadas de
destino são coordenadas de grid na Scene de destino; a elevação é preservada, a menos
que você a defina. Origem e destino devem diferir, e ambas pertencer à campanha de
quem chama.

## Pertencimento a zonas

O pertencimento a zonas é recalculado pelo core nas duas pontas do movimento: o token
sai das zonas que ocupava na origem e entra nas que contêm seu ponto de destino.
Pacotes que escutam `zone.entered` e `zone.left` recebem os eventos resultantes; nada
precisa consultar geometria em laço.

## Autoridade

Quem chama precisa poder controlar o token, pela mesma regra que rege movê-lo
normalmente, e precisa poder ver a Scene de destino. Um jogador não transfere o token
de outro, e uma Scene oculta para quem chama não é destino válido — uma Scene oculta
nunca se torna descobrível por tentar transferir para ela.

Navegar outros usuários continua sendo autoridade separada: um jogador só navega a si
mesmo.

## Ciclo de vida

Transferências são persistidas imediatamente. Quem recarrega encontra seu token na
Scene de destino; um cliente desconectado durante o movimento reconcilia na reconexão
a partir do estado do servidor, em vez de reproduzir o evento.

## Erros comuns

| Código | Causa |
|---|---|
| `VALIDATION_FAILED` | Origem e destino iguais, coordenadas não finitas ou lote fora dos limites. |
| `NOT_FOUND` | Token ou Scene desconhecidos, token que não pode controlar ou destino que não pode ver. |
| `STALE_VERSION` | `expectedVersion` não confere mais para ao menos um token do lote. |

## O que esta API não expõe

Sem movimento entre campanhas, sem mover token que quem chama não moveria diretamente
e sem navegação implícita de usuários não endereçados.
