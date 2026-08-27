# Apresentação de usuário

Apresentação de usuário é a pequena projeção visual server-authoritative que packages podem usar para representar um participante de forma consistente. A SDK 1 expõe somente uma cor canônica minúscula em `#rrggbb` e o ID já visível do participante. Ela não expõe settings do core, preferências arbitrárias, perfil, email, locale, permissões ou metadados de autenticação.

O package deve declarar `users.presentation.read`. Capability e autoridade do usuário são verificações distintas: `list()` contém somente membros da campanha ativa, e `get(userId)` só funciona para um membro visível nessa campanha. Campanha inacessível é rejeitada; um alvo desconhecido ou de outra campanha é indistinguível de um recurso ausente.

```js
const participantes = await sdk.users.presentation.list();
const apresentacao = await sdk.users.presentation.get(userId);

const dispose = sdk.events.on("user.presentation.changed", async event => {
  const atual = await sdk.users.presentation.get(event.resourceId);
  atualizarCor(atual.userId, atual.color);
});
```

O evento segue o lifecycle normal de eventos da SDK e só é entregue pelas rooms da campanha. Seu shape limitado identifica o participante alterado em `resourceId`; consumidores relêem a projeção autoritativa. Desfaça a subscription no teardown do package.

Por exemplo, um addon de dados 3D pode obter o user ID do autor em um DTO de roll autorizado, chamar `presentation.get(authorUserId)` e renderizar essa cor. Isso não exige acesso a settings do core nem amplia a visibilidade do roll.
