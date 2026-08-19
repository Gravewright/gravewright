# Limites do runtime semântico

A SDK expõe intenção, não maquinaria. Cada domínio abaixo aceita uma descrição
tipada do que deve acontecer e deixa o core decidir se pode, quando acontece e quem
observa. Saber onde ficam essas fronteiras costuma bastar para prever o que uma API
vai e não vai entregar.

## Drag e drop é um protocolo, não um evento do DOM

`sdk.ui.dragDrop` descreve o que foi carregado e onde caiu, como referências de
conteúdo e uma posição no mundo. Não é `DragEvent`, `DataTransfer`, seletor nem
qualquer outro handle de DOM. O core resolve novamente a referência e o destino
imediatamente antes de executar a ação registrada vinculada àquele destino, então um
gesto nunca afirma um resultado que o usuário não poderia ter feito diretamente.

## Áudio é um domínio do core, não um elemento

O core é dono do estado de reprodução, da audiência, do ciclo de vida e da projeção
de reconexão. `sdk.audio` nunca devolve `HTMLAudioElement`, nó do WebAudio, URL de
mídia nem autoridade sobre o volume pessoal de quem escuta.

## Navegação muda o ponto de vista, e nada além disso

`sdk.navigation.scene` muda qual Scene o usuário está vendo. Não move, cria nem
altera Token, e não é uma apresentação.

## Input separa significado de vínculo

O pacote declara o que um comando significa; o usuário é dono de qual tecla o
invoca. O core mantém os listeners crus de teclado e ponteiro, os atalhos
protegidos, a supressão durante digitação, o limiar de long press, o cancelamento de
ponteiro e a resolução de conflito multipointer.

## Domínios vizinhos que são deliberadamente distintos

| Isto | não é | porque |
|---|---|---|
| Presentation | Navigation | uma mostra conteúdo, a outra muda o contexto de Scene |
| Directed Interaction | Presentation | uma pede uma decisão e espera a resposta |
| Durable Workflow | Semantic Timeline | um espera decisões, a outra corre por um relógio |
| Token Transfer | Scene Navigation | um move um Token, a outra move uma visão |
| Scene Zone | World Object | uma é uma região, o outro é uma coisa endereçável |
| Sound | Playback | um é conteúdo reutilizável, o outro é uma instância em execução |

Scene World Objects continuam sendo recursos semânticos com dados e interações. Não
são objetos do renderer, e nenhuma API devolve um handle de desenho para eles.
