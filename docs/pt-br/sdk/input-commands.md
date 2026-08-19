# Comandos de entrada

O Registro de Entrada é o dono da entrada física. Teclado, ponteiro e gestos são lidos pelo runtime de entrada do núcleo e por mais ninguém: um pacote nunca instala um listener no documento hospedeiro, nunca recebe um `KeyboardEvent` e nunca vê um nó do DOM que não tenha criado. O que um pacote registra é um *comando semântico*: uma intenção nomeada, com rótulo, os contextos a que pertence e os atalhos com que começa. O que a pessoa usuária controla é qual tecla o invoca.

Registrar e invocar exigem `input.commands`.

## Dois tipos de comando

Um comando pode ser tratado localmente, executado no servidor, ou ambos.

Um **comando semântico local** é tratado no navegador. Use-o quando a intenção é sobre a interface — abrir um painel, focar uma aplicação, trocar de visão. Passe um handler como segundo argumento de `register`:

```js
await sdk.input.commands.register({
  id: "open-console",
  label: "Abrir console",
  contexts: ["global", "text-input-excluded"],
  defaultBindings: ["Alt+U"]
}, async (invocation) => {
  await sdk.ui.applications.render("console", host);
});
```

O handler recebe um `InputCommandInvocationDTO` — `commandId`, `packageId`, `source`, `binding`, `context` — e nada mais. São metadados já resolvidos, não um evento.

Um **comando de ação registrada** é executado pelo servidor. Use-o quando a intenção altera estado autoritativo. Nomeie uma ação registrada e pré-vincule a entrada que essa ação exige:

```js
const actor = await sdk.actors.get(actorId);

await sdk.input.commands.register({
  id: "engage-scanner",
  label: "Acionar scanner",
  contexts: ["global", "text-input-excluded"],
  defaultBindings: ["Alt+S"],
  registeredAction: "my-package:scanner.engage@1",
  actionInput: { actorId: actor.id }
});
```

Os dois podem ser combinados: forneça um handler *e* um `registeredAction`, e o handler roda localmente enquanto o servidor executa a ação.

## Metadados de invocação não são entrada da ação

Os metadados que descrevem *como* um comando foi invocado — qual atalho, qual contexto — nunca são repassados à ação registrada. Uma ação recebe apenas `actionInput`, exatamente como foi gravado no registro.

Isso importa porque `actionInput` é dado de definição do pacote, não payload de runtime. Ele é validado e canonicalizado quando o comando é registrado, guardado pelo runtime do núcleo e usado literalmente em toda invocação. Quem chama não pode substituí-lo: uma invocação que envia entrada de ação para um comando que já pré-vinculou a sua é recusada, não mesclada. Comandos sem `actionInput` continuam aceitando entrada de quem chama, validada pelo schema da própria ação.

Entrada pré-vinculada é JSON simples e limitado. Não há linguagem de expressão, interpolação nem sintaxe de caminho — se um comando precisa mirar um recurso cujo ID só existe em runtime, registre o comando depois que esse ID existir. Registrar o mesmo id de comando de novo substitui a definição, inclusive a entrada pré-vinculada, então um pacote pode re-registrar sempre que o recurso alvo mudar.

## Autoridade

Um comando não concede autoridade nenhuma. Um handler local roda com os privilégios de código de pacote comum: toda chamada SDK que ele faz deriva o principal da sessão autenticada e é conferida contra capacidades e autoridade da campanha exatamente como se a pessoa tivesse clicado num botão. Um comando de ação registrada é conferido do mesmo jeito — quem chama precisa ter permissão para a ação, diga o que disser a definição do comando.

Nada numa definição de comando forja usuário, campanha, papel de mestre, audiência ou contexto de permissão. Comandos pertencem à campanha em que foram registrados e são invisíveis de qualquer outra.

## Atalhos

`defaultBindings` é com o que o comando começa. Um atalho próprio da pessoa usuária, definido por `sdk.input.bindings.set`, substitui o padrão em vez de somar a ele, e vale imediatamente — sem recarregar, e a tecla anterior para de funcionar no mesmo instante.

```js
const bound = await sdk.input.bindings.set("engage-scanner", "Alt+K");
```

Um atalho é uma tecla com prefixo de modificadores, como `Alt+K`, `Ctrl+Shift+P` ou `F7`. Duas regras são impostas pelo núcleo:

- **Atalhos reservados são recusados.** Combinações que o navegador ou a aplicação já usam — `Ctrl+L`, `Ctrl+T`, `Ctrl+W`, `Ctrl+N`, `Ctrl+R`, `Ctrl+Shift+T`, `Alt+F4`, `F5`, `F12` — não podem ser tomadas.
- **Conflitos são recusados.** Um atalho já usado por outro comando, de qualquer pacote, é rejeitado em vez de silenciosamente sobreposto.

Atalhos pertencem à pessoa usuária, não à campanha nem ao pacote: a escolha de uma é invisível para as demais. Uma alteração bem-sucedida emite `input.binding.changed` para essa pessoa, para que outras superfícies releiam. Uma alteração recusada não emite nada.

Leia o conjunto atual com `sdk.input.bindings.get()` e liste os comandos disponíveis ao pacote com `sdk.input.commands.list()`.

## Contextos e supressão durante digitação

`contexts` declara onde um comando vale: `global`, `scene`, `actor-sheet`, `package-application`, `combat`.

Dois contextos governam a digitação. Com o foco num campo de texto, textarea, select ou região contenteditable, um comando só roda se declarar `text-input`. Declarar `text-input-excluded` recusa a invocação durante a digitação mesmo assim, e sempre vence quando os dois estão presentes. Um comando que não declara nenhum dos dois fica suprimido durante a digitação.

A supressão é do núcleo. Um pacote nunca deve filtrar teclas por conta própria — não tem acesso aos eventos necessários para isso, e qualquer filtro do lado do pacote discordaria das regras do núcleo que a pessoa usuária vê em todo o resto.

## Exatamente uma vez

Um toque físico invoca no máximo um comando. Quando vários comandos compartilham um atalho, o primeiro que casar toma o toque e os demais são ignorados; tecla segurada em repetição não reinvoca. Um comando suprimido, sem atalho ou descartado não produz invocação alguma, em vez de produzir uma que falha.

## Gestos

`sdk.input.gestures.register` vincula um gesto de ponteiro — `tap`, `double-tap`, `long-press`, `drag`, `pan`, `cancel` — a um id de comando, e aceita o mesmo handler opcional. A invocação carrega `source: "gesture"` e o nome do gesto. Como nas teclas, o núcleo é dono de todo listener de ponteiro.

## Ciclo de vida

O registro devolve um disposer. Chamá-lo remove o comando imediatamente: o atalho para de resolver, o handler é descartado e nenhum listener fica para trás — o núcleo é dono dos únicos listeners que existem, então um pacote não tem como vazar um.

Os disposers também rodam quando o pacote é descarregado. Um pacote desativado não tem comando registrado, então seus atalhos não resolvem nada; reativá-lo os registra de novo pelo ciclo de vida normal.
