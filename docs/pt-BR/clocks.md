# Relógios de progresso

[Documentação](../README.pt-BR.md) · [English](../en/clocks.md) · [Gerenciamento de campanha](campaign-management.md)

Relógios de progresso acompanham tarefas, ameaças, contagens regressivas e outros
objetivos da campanha por meio de segmentos preenchidos. Pertencem à campanha
e funcionam com qualquer sistema de jogo. A mesa e o gerenciador do mestre
editam os mesmos registros salvos.

## Criar e configurar

Na mesa, abra **Relógios** na barra de menus. Antes de entrar no jogo, abra
**Gerenciar campanha** e selecione **Relógios**. Um mestre da campanha pode criar
um relógio, escolher seu nome e cor e definir o progresso atual.

Escolha um modelo com 4, 6, 8, 10 ou 12 segmentos ou **Personalizado** para um
número inteiro entre 2 e 24. O progresso permanece entre zero e o número de
segmentos.
Uma campanha pode conter até 128 relógios.

Escolha o escopo do relógio:

| Escopo | Onde aparece |
| --- | --- |
| Campanha | Naquela campanha, entre as cenas |
| Cena atual | Somente ao visualizar a cena vinculada |

Selecionar um contexto de cena no gerenciador prepara os relógios daquela cena.
A seleção preserva a transmissão da mesa, a cena privada de cada participante
e a presença na mesa. Entrar na mesa continua sendo uma ação separada.
Excluir uma cena também remove os relógios vinculados a ela.

## Público e controles

| Configuração ou papel | Comportamento |
| --- | --- |
| Apenas mestre | O servidor entrega o relógio somente aos mestres da campanha |
| Jogadores | Participantes que visualizam seu escopo podem ver o relógio |
| Jogadores podem avançar este relógio | Jogadores podem avançar ou reduzir o progresso desse relógio público |
| Mestre | Pode configurar, avançar, reiniciar e excluir relógios |
| Espectador | Pode visualizar os relógios permitidos, com controles somente de leitura |
| Fixado | Mostra o relógio permitido na área de relógios fixados da mesa |

A edição por jogadores altera o progresso. Configuração, visibilidade, escopo
de cena, reinício e exclusão continuam sendo operações do mestre. Ocultar um
controle é uma escolha de apresentação; o servidor verifica o vínculo atual e
a permissão do participante em cada requisição. Relógios privados e relógios
de outra cena visualizada são filtrados antes da entrega.

Use os controles de aumentar e diminuir para alterar o progresso, **Reiniciar**
para voltar a zero ou o editor do mestre para revisar a configuração. Fechar a
janela mantém os relógios salvos. Recarregar a página restaura o progresso salvo.
Os relógios fixados usam os mesmos registros autorizados da lista completa.

## Sincronização e integração

A mesa recebe alterações confirmadas pela conexão de tempo real existente.
O gerenciamento de campanha usa HTTP, atualizando ao recuperar o foco e pelo
seu ciclo normal de atualização. **Atualizar campanha** busca o estado atual
imediatamente.

Edições concorrentes usam a versão salva. Se um relógio mudar enquanto uma
operação estiver pendente, atualize o estado e revise a ação. Cada alteração
lógica usa um UUID de requisição novo; repetir exatamente a mesma operação
reutiliza seu UUID para que ela seja aplicada uma única vez.

Integrações de navegador usam o domínio `clocks` da
[API pública](api.md): `state`, `create`, `update`, `advance`, `reset` e `delete`.
Alterações em um relógio existente informam seu `id` e sua `version` inteira;
avançar também informa `delta`. Criar e atualizar aceitam os campos nativos
`name`, `segments`, `value`, `color`, `visibility`, `playersCanEdit`, `pinned`
e `scopeSceneId`. A visibilidade é `gm` ou `players`; `scopeSceneId: null`
seleciona o escopo da campanha. O `sceneId` da requisição informa o contexto
atual de visualização. Os relógios retornados mostram seu escopo salvo em
`clock.sceneId`. As integrações mantêm as mesmas verificações de campanha,
cena e papel da interface nativa.

Os mostradores usam arte SVG nativa. O recurso dispensa módulos de outros VTTs
ou pacotes de sistemas de jogo.

## Mecanismos do MapBuilder

O nó **Controlar relógio** dos Objetos Inteligentes conecta um evento do
mecanismo a uma operação de avançar, reduzir, definir ou reiniciar. Aceita uma
quantidade configurada ou uma entrada numérica conectada. As alterações usam o
mesmo relógio salvo e atualizam janelas e exibições fixadas autorizadas após a
confirmação.

Um nó autorado pelo mestre autoriza aquela operação específica quando um
participante interage com o mecanismo. Isso inclui relógios privados e relógios
cuja edição direta por jogadores está desativada. Não concede acesso geral nem
expõe nomes e valores privados. O motor exige um mestre ativo na campanha.
O escopo do relógio continua limitando qual cena pode executar o vínculo.

Consulte [Controlar relógios de progresso no MapBuilder](map-builder.md#controlar-relógios-de-progresso)
para conexões, limites de quantidade e fluxos seguros de simulação e ensaio.

## Backups e atualização

Exportações de campanha, snapshots, restaurações e clones preservam a
configuração, o progresso e o escopo de campanha ou cena dos relógios. As opções
de clonagem podem omitir todos os relógios com `clocks: false`. Omitir as cenas
com `scenes: false` também omite os relógios vinculados a cenas, preservando os
relógios da campanha quando os relógios forem incluídos.

O recurso acrescenta a migração `0003_progress_clock` de `gravewright_table`.
Aplique as migrações pendentes antes de reiniciar uma instalação existente:

```bash
uv run --locked python manage.py migrate
```
