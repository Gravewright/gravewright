# Diários e referências da campanha

[Documentação](../README.pt-BR.md) · [English](../en/journals.md)

Abra **Diários** na mesa ou no [gestor de campanha](campaign-management.md).
O gestor edita os documentos existentes da campanha sem entrar na mesa.
Diários, páginas, missões, quadros de missões e tabelas de rolagem mantêm seus
editores nativos, anexos e controles de acesso.

Em telas estreitas, use **Recolher páginas** para deixar mais espaço para o
documento. **Mostrar páginas** restaura o índice.

## Renomear uma página pelo cabeçalho

Ao editar uma página de sua propriedade, clique no nome dela no cabeçalho do
documento ou foque o nome e pressione **Enter** ou **Espaço**. Digite um nome de
até 120 caracteres. **Enter** ou sair do campo confirma e salva; **Escape** cancela.
Um nome vazio mantém o título anterior. Renomear preserva o conteúdo e os vínculos
da página. Páginas somente de leitura e o modo de leitura não oferecem esse controle.

## Capítulos e subcapítulos

Capítulos organizam um diário independentemente das páginas. Um capítulo pode
ficar vazio, conter várias páginas e conter subcapítulos. Cada página pertence
a no máximo um capítulo; também pode ficar fora de todos eles.

Escolha **Novo capítulo** para criar um capítulo vazio. O formulário permite
definir seu nome e escolher um capítulo pai. As ações de um capítulo também
oferecem **Novo subcapítulo**, **Editar capítulo**, ordenação entre irmãos e
**Excluir capítulo**. A edição pode mudar o nome ou o pai sem alterar a identidade
do capítulo nem suas páginas. O seletor de pai exclui relações que tornariam a
hierarquia circular.

Use **Mover para capítulo** nas ações de uma página para escolher seu capítulo
ou **Sem capítulo**. Excluir um capítulo mantém suas páginas fora de qualquer
capítulo e move seus subcapítulos imediatos para o pai do capítulo excluído.
Excluir uma página continua sendo uma operação separada. Grupos de categorias
existentes tornam-se capítulos ao abrir um diário antigo; as páginas e seus
vínculos permanecem no lugar.

A hierarquia segue os controles de acesso existentes do diário. Jogadores veem
os capítulos necessários às páginas autorizadas, seus ancestrais e ramos realmente
vazios. Ramos que contêm apenas páginas ocultas são omitidos. Salvar uma página
pública editável preserva as páginas privadas e a estrutura de capítulos que o
jogador não pode ver. Acesso de leitura ou de streamer não oferece controles de
edição de capítulos.

Um diário comporta até 128 capítulos, oito níveis de capítulos e 64 páginas.
Não é possível excluir um capítulo ainda necessário a páginas protegidas;
as permissões existentes das páginas continuam valendo ao reorganizar o diário.

## Inserir uma referência da campanha

1. Abra um diário ou página que você possa editar e posicione o cursor no texto rico.
2. Digite **@** no início de um parágrafo ou depois de um espaço. Busque pelo nome
   e use **Tipo de recurso** para filtrar o catálogo da campanha.
3. Selecione um recurso e escolha **Adicionar link**. A referência é inserida
   no cursor e salva junto com as outras alterações do diário.
4. Abra a referência. Personagens, itens, diários, páginas individuais, cenas e
   mapas mentais abrem na ficha, documento ou editor nativo após verificar o acesso.
   Outros tipos mostram uma prévia atual com controles nativos quando disponíveis.

O editor vazio mostra **Digite / para inserir blocos ou @ para inserir referências**.
**/** continua abrindo o menu de blocos. Confirmar uma referência substitui o
**@** digitado; cancelar o seletor mantém esse caractere como texto comum.
Um **@** dentro de um endereço de e-mail não abre o seletor.

O catálogo reúne os recursos da campanha disponíveis à sua conta, incluindo
personagens, itens, diários e páginas individuais, cenas e seus recursos,
relógios, pistas, mapas mentais, arquivos, áudio, cartas, compêndios e ferramentas
de preparação. Alguns recursos só existem quando sua funcionalidade ou pacote
de sistema está disponível. Missões e outros tipos de diário aparecem entre os
recursos de diários. Selecionar uma página individual preserva seu destino.

As referências apontam para recursos existentes. Elas não copiam uma ficha nem
concedem acesso ao seu conteúdo. O texto autoral do diário e os nomes dos recursos
mantêm seu idioma original. Os hyperlinks existentes para diários e páginas
individuais continuam funcionando junto com o seletor de referências da campanha.

## Acesso e recursos indisponíveis

Um diário compartilhado pode conter uma referência a um recurso que apenas o
mestre pode ler. Cada destinatário recebe a referência conforme as permissões do
próprio destino. Um destino indisponível aparece como **Recurso indisponível**;
seu nome privado e sua identidade são omitidos da projeção do destinatário.

Alterar a visibilidade ou excluir um recurso pode tornar uma referência existente
indisponível. A abertura verifica novamente o acesso. Salvar um diário que possa
ser editado preserva suas referências indisponíveis existentes, permitindo que
um jogador atualize as notas sem remover as conexões ocultas do mestre. Isso não
permite inserir um destino privado adivinhado nem alterar suas permissões.

A propriedade do diário continua determinando quem pode editar seu texto rico.
Ler um diário não concede edição, e o acesso de streamer permanece somente para
leitura. Notas do mestre, páginas privadas e conteúdo oculto mantêm suas
restrições de público existentes.

## Salvamento e recuperação

As alterações usam o salvamento e o tratamento de conflitos existentes. Mantenha
a janela aberta se o salvamento falhar, confira o erro exibido e resolva conflitos
de versão antes de substituir o documento salvo. Atualizar a página recarrega o
estado autorizado do servidor.

Arquivos de campanha e snapshots mantêm as referências junto com o texto
estruturado do diário. Os destinos incluídos são remapeados para os recursos da
campanha copiada, inclusive os destinos de páginas individuais. Os recursos
vinculados também precisam ser incluídos ao transferir conteúdo para outra
campanha; destinos omitidos permanecem indisponíveis em vez de apontar para um
recurso sem relação. Consulte [implantação e recuperação](deployment.md)
para backups da instalação.
