# Modelo de autoridade

Toda chamada da SDK segue o mesmo caminho. Entender isso uma vez explica a maior
parte do comportamento que você vai encontrar, inclusive as recusas.

```
intenção do pacote
  → capability declarada
  → principal autenticado
  → autoridade atual desse principal
  → mutação no core
  → projeção filtrada para quem lê
```

O pacote expressa uma intenção. A capability que ele declarou decide se aquele tipo
de intenção está disponível para ele. A sessão decide *quem* está pedindo. As
permissões da campanha decidem se essa pessoa pode. O core aplica a mudança. O que
volta é filtrado para quem está lendo.

## Capability é permissão para pedir, não autoridade para agir

Declarar `tokens.transfer` não permite ao pacote mover qualquer token; permite pedir,
em nome de um usuário que já poderia mover aquele token. Uma capability nunca eleva um
jogador a GM, e um pacote rodando no navegador de um jogador tem exatamente a
autoridade daquele jogador.

É por isso que dois usuários rodando o mesmo pacote veem resultados diferentes da
mesma chamada, e por isso um pacote não escala declarando mais capabilities.

## A identidade vem da sessão

Toda operação deriva seu principal da sessão autenticada. Um pacote não pode agir
como outro usuário, e saber o id de alguém não muda nada — ids aparecem nos DTOs para
que um pacote possa *endereçar* alguém, nunca para que possa *virar* essa pessoa.

Concretamente: um pacote pode aprender por `TokenDTO.controllers` quem conduz um
token, e ainda assim não pode mover esse token. Pode endereçar uma interação dirigida
àquele usuário, e ainda assim não pode responder por ele.

## Visibilidade é projeção, não um filtro que você aplica

O core decide o que quem lê pode ver antes de devolver qualquer coisa. Recursos
ocultos ficam ausentes, e não marcados como ocultos, então um pacote não infere a
existência deles pela resposta. Um token que você não pode inspecionar não devolve
controladores; uma Scene que você não pode ver não é destino válido; um envio privado
simplesmente não está no payload.

Consequência prática: nunca trate um resultado vazio como prova de que algo não
existe. Significa que *você* não pode ver.

## Isolamento de campanha

Toda chamada é restrita a uma campanha. Um pacote ativado na campanha A não lê nem
escreve na campanha B, mesmo para um usuário que pertence às duas, e nenhuma API
enumera recursos entre campanhas.

## Concorrência

Mutações que podem conflitar aceitam `expectedVersion` e falham com `STALE_VERSION`
quando o recurso já mudou. Nada é aplicado pela metade: uma mutação recusada deixa o
recurso exatamente como estava. Releia, decida de novo, tente outra vez.

## O que um pacote nunca pode fazer

- agir como outro usuário, ou responder a uma decisão endereçada a ele;
- contornar as permissões da campanha declarando uma capability;
- ler um recurso oculto por ter declarado a capability que cobre aquele tipo;
- alcançar outra campanha;
- alcançar o banco, o sistema de arquivos, o renderer ou uma rota privada;
- afirmar que algo aconteceu num instante com que o core não concordou.

Se você encontrar uma operação que acredita ser possível e ela for recusada, vale
verificar se o *usuário* que age poderia executá-la diretamente. Quase sempre é essa
a resposta.
