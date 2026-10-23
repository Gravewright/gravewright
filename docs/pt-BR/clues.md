# Pistas

[Documentação](../README.pt-BR.md) · [English](../en/clues.md) · [Relógios de progresso](clocks.md)

Pistas acompanham descobertas com os mesmos escopos de campanha e cena dos
relógios de progresso. O mestre pode preparar uma descoberta, registrar notas
privadas e revelá-la imediatamente ou após várias etapas. A mesa e o gerenciador
usam as mesmas pistas salvas, independentemente do sistema da campanha.

## Preparar uma pista

Abra **Pistas** na barra de menus da mesa ou selecione **Pistas** em
**Gerenciar campanha**. Um mestre da campanha pode criar e editar estes campos:

| Campo | Significado |
| --- | --- |
| Nome | Título autoral, com até 120 caracteres |
| Conteúdo | Descoberta exibida após a revelação, com até 4.000 caracteres |
| Notas do mestre | Preparação privada, com até 4.000 caracteres |
| Segmentos | Progresso necessário, inteiro de 1 a 24; o padrão é 4 |
| Progresso | Valor atual entre zero e o número de segmentos |
| Cor | Cor de exibição da pista |
| Visibilidade | Revelar ao descobrir ou apenas mestre |
| Escopo | Toda a campanha ou a cena selecionada |
| Fixada | Exibir a pista permitida na área fixada da mesa |

Use um segmento para uma descoberta que deve aparecer em uma única etapa. Use
vários para uma investigação que exige múltiplas descobertas. Uma campanha pode
conter até 128 pistas. Notas do mestre
são separadas do Conteúdo: continuam privadas mesmo após a revelação da pista.
Nomes, conteúdo e notas autorais preservam sua redação ao trocar o idioma da
interface.

Selecionar uma cena no gerenciamento prepara essa cena sem mudar a transmissão
da mesa, a navegação privada ou a presença. Uma pista de cena só fica disponível
nessa cena. Excluir a cena também remove as pistas vinculadas a ela.

## Descoberta e visibilidade

Jogadores e espectadores recebem uma pista apenas quando as duas condições são
atendidas: seu progresso está completo e sua visibilidade é **Revelar ao descobrir**.
Antes disso, o servidor omite o registro, incluindo nome, conteúdo, identificador
e progresso incompleto. Não envia espaços reservados nem uma contagem de pistas
desconhecidas. Notas do mestre são omitidas de toda projeção para jogadores e
espectadores.

Apenas mestres da campanha podem configurar pistas ou mudar seu progresso
diretamente. Jogadores e espectadores podem abrir descobertas permitidas em modo
somente leitura. A fixação segue as mesmas verificações de descoberta e
visibilidade da lista completa.

| Operação do mestre | Resultado |
| --- | --- |
| Avançar ou recuar | Mudar o progresso dentro dos limites de segmentos |
| Revelar | Completar o progresso e tornar a descoberta visível aos jogadores |
| Ocultar | Tornar a pista exclusiva do mestre, preservando o progresso |
| Reiniciar | Voltar o progresso a zero, preservando a visibilidade |
| Excluir | Remover a pista |

Reduzir uma pista completa para menos que o progresso necessário remove sua
exibição para jogadores até que ela esteja completa novamente. Ocultar remove
sua apresentação atual; participantes podem lembrar conteúdo já descoberto.
Fechar uma janela não exclui pistas salvas. Recarregar restaura a configuração e
o progresso persistidos.

## Mecanismos do MapBuilder

Use **Controlar pista** no Blueprint de um Objeto Inteligente para ligar uma
interação do mapa a avançar, recuar, definir, reiniciar, revelar ou ocultar. Uma
conexão numérica em **Quantidade** substitui a quantidade configurada para
avançar, recuar e definir. Reiniciar, revelar e ocultar ignoram Quantidade.

Um vínculo criado pelo mestre autoriza essa operação específica quando um
participante interage com o mecanismo. Ele não concede controles gerais de pistas
nem expõe conteúdo desconhecido ou notas do mestre. A execução exige um mestre
ativo na campanha e preserva as restrições de campanha e cena da pista.

**Simular** descreve a ação planejada sem alterar pistas salvas. **Testar
comportamento** usa o motor do servidor, apresenta os valores antes e depois e
reverte pistas e recibos junto com o ensaio. Durante o jogo, operações confirmadas
atualizam as mesmas pistas salvas e suas exibições permitidas na mesa.

Consulte [Controlar pistas no MapBuilder](map-builder.md#controlar-pistas) para
conexões, limites de quantidade e a diferença entre gerar e atualizar uma cena.

## Sincronização, backups e atualização

A mesa recebe alterações confirmadas pela conexão de tempo real existente.
O gerenciamento atualiza sua projeção por HTTP sem entrar na mesa nem criar
presença. Edições concorrentes exigem a revisão inteira atual; após um conflito,
revise a pista atualizada antes de enviar outra operação. Novas tentativas da
mesma operação reutilizam seu UUID de requisição para aplicar o progresso uma vez.

Exportações, snapshots, restaurações e clones da campanha preservam configuração,
conteúdo, notas do mestre, progresso e escopo das pistas. Opções de clone podem
omitir pistas com `clues: false`. Omitir cenas com `scenes: false` também omite
pistas dessas cenas, preservando as pistas da campanha incluídas. Vínculos de
Blueprint incluídos passam a apontar para as pistas copiadas; alvos omitidos
ficam indisponíveis em vez de controlar a pista da campanha original.

Este recurso adiciona a migração `0004_progress_clue` de `gravewright_table`.
Aplique migrações pendentes antes de reiniciar uma instalação existente:

```bash
uv run --locked python manage.py migrate
```

Extensões podem usar o domínio `clues` da [API pública](api.md). A API aplica as
mesmas verificações de descoberta, privacidade, escopo e função da interface nativa.
