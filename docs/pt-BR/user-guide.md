# Usando o Gravewright

[Documentação](../README.pt-BR.md) · [English](../en/user-guide.md)

## Contas e campanhas

Crie o primeiro proprietário em `/setup` e entre por `/login`. Outros usuários se cadastram em `/register`. O proprietário administra a instância e cria campanhas em `/inside`. A campanha também aparece como `container` nas rotas HTTP e `table` nas interfaces do navegador/tempo real.

O sistema nativo é **Gravewright PDF System**, com atores `character`. Convide jogadores usando o código da campanha; o mestre da campanha configura validade e máximo de usos e pode revogar códigos. Entradas bem-sucedidas de novos membros incrementam automaticamente o contador de usos. O vínculo permite acessar a campanha, enquanto permissões de documentos e cenas definem o que pode ser visto ou alterado. Um link de transmissão oferece acesso restrito de leitura e não equivale a uma conta de jogador.

Em **Sistemas** e **Módulos**, **Instalar** lista a versão mais recente, compatível e não revogada de cada pacote. Busca, categorias e paginação usam essa seleção.

## Alertas de atualização do VTT

O proprietário da instalação tem um sino ao lado do nome no cabeçalho da biblioteca. Um marcador dourado aparece quando existe uma release mais recente e verificada do VTT. Abra-o para comparar as versões instalada e disponível; **Ver atualização** abre a Administração diretamente na aba de atualizações. A instalação continua exigindo uma ação explícita do proprietário nessa aba.

A consulta não bloqueia a biblioteca. A página visível atualiza o indicador a cada cinco minutos, reaproveitando o cache de releases do servidor por 24 horas. **Verificar atualizações** na Administração força uma consulta nova e atualiza o sino imediatamente. Contas de jogadores não recebem alertas de administração da instância.

A aba de atualizações destaca o nome completo da versão instalada e carrega imediatamente suas notas incluídas no pacote, inclusive sem internet. Ela não possui seletor de canal. Quando há uma versão nova, seu nome e suas notas aparecem junto dos controles de instalação. As notas apresentam títulos, listas, código e links seguros; a interface em português usa a seção em português quando disponível.

## Preparar a mesa

1. Crie uma campanha e abra sua mesa.
2. Crie/importe uma cena de mapa e configure grade e visão inicial. **Ativar para jogadores** torna a cena visível e a transmite. Abrir uma cena em particular não a compartilha.
3. Crie atores, anexe fichas PDF quando necessário e coloque seus tokens na cena. Dados do ator e estado do token são relacionados, mas distintos; o token representa o ator em um mapa específico.
4. Prepare diários, materiais e recursos, concedendo acesso intencionalmente. Confira em uma sessão separada de jogador antes de compartilhar.
5. Convide os jogadores, use controles de lobby/prontidão quando habilitados e transmita a cena desejada.

As ferramentas incluem seleção, movimento, desenho, medição, paredes, neblina, iluminação, pings e efeitos. Permissões e ferramenta ativa determinam as ações disponíveis. O mestre pode preparar material oculto sem transmiti-lo. A renderização depende do WebGL do navegador e da complexidade da cena.

### Entrar no Map Builder

Para o mestre da campanha, **Nova cena** abre a escolha entre **Enviar mapa** e
**Map Builder**. Enviar mapa mantém o fluxo de importação de imagem. Map Builder
abre uma área própria em tela inteira, na mesma aba, preservando a pasta de
cenas escolhida. **Voltar ao jogo** retorna à cena selecionada da campanha;
entrar no builder mantém a transmissão dos jogadores.

O Estúdio possui uma barra de ferramentas esquerda, opções contextuais do pincel
acima do mapa e uma **Biblioteca** horizontal abaixo dele. O cabeçalho reúne o botão
de estado do salvamento, **Prévia** e geração de cena; controles de zoom e dimensões em células
ficam na parte inferior da área de desenho. A biblioteca oferece busca, **Importar**
e categorias por tipo; sua seta recolhe os cards, mantendo a barra acessível.
Ao entrar, **Chão** aparece destacado e mostra as imagens disponíveis da campanha
de todos os tipos; clicar numa categoria filtra as imagens sem mudar a ferramenta
de desenho selecionada. **Camadas**, no canto superior direito do mapa, abre um painel
auxiliar com **Camadas**, **Seleção**, **Configurações**, **Projetos** e **Revisão**.
Fechá-lo mantém a biblioteca acessível. Esse painel começa fechado e só abre
quando solicitado; selecionar ou pintar objetos não o abre. **Componentes** permanece planejado.

**Importar** abre uma modal para escolher suas imagens e o tipo: **Chão**,
**Parede**, **Porta** ou **Objeto**. Opcionalmente, escolha uma família de assets
existente ou digite um novo nome para agrupar variações do mesmo tipo. Escolha uma
família na biblioteca ou no seletor superior de material para pintar com todas
as suas imagens; as imagens individuais continuam disponíveis. Dê dois cliques
no card de uma imagem para editar seu tipo ou família; uma imagem já usada no
mapa mantém seu tipo.

Com **Chão**, escolha **Forma** na barra contextual: arraste livremente com o
pincel, trace um retângulo entre cantos ou arraste um círculo a partir do centro
para definir o raio. Para um polígono, clique em pelo menos três vértices e
pressione **Enter** ou dê dois cliques para concluir; **Escape** cancela. Uma
família de chão sorteia uma imagem por célula e mantém as escolhas na prévia,
em desfazer/refazer, no salvamento e na geração de cena. Cada traço ou forma
concluída ocupa uma etapa do histórico de desfazer. Trace paredes e portas entre
dois pontos. As portas funcionam independentemente
e substituem os trechos de parede que sobrepõem na mesma direção. Selecione objetos
para mover ou editar em **Seleção**; desfazer/refazer acompanha as edições. Clique
no botão de estado do salvamento no cabeçalho ou pressione **Ctrl+S**, e use
**Camadas → Projetos** para reabrir o trabalho salvo, inclusive depois de reiniciar o VTT.
Camadas nomeadas organizam objetos com visibilidade e bloqueio salvos; novos objetos
entram na camada ativa. A barra contextual configura materiais, pincéis, encaixe
na grade e rotação de chão/objetos. Shift e clique ou seleção retangular formam um
grupo para mover, duplicar, girar ou mudar de camada. **Objeto** e **Luz**, na barra
esquerda, posicionam imagens decorativas e luzes nativas. **Revisão** mostra o resumo
do projeto e a ação de gerar cena.

**Prévia** oculta as guias de edição e pausa a pintura; mover a vista e ajustar
o zoom continuam disponíveis. Ela mostra temporariamente todas as camadas e
restaura a visibilidade anterior ao retomar a edição. **Camadas** controla a
visibilidade somente no editor; camadas ocultas continuam presentes na cena gerada.

**Gerar cena** salva o projeto, prepara o mapa fatiado e as paredes e portas
nativas, depois abre a nova cena reservada ao mestre. O vão da porta pode substituir
parte da parede: abrir a porta nativa libera movimento e visão nesse vão. As
imagens das portas acompanham seu estado durante o jogo. A transmissão dos
jogadores é preservada; use **Ativar para jogadores** no menu de contexto da cena
quando quiser compartilhar. Cada nova geração cria uma cena separada.
**Camadas → Revisão → Atualizar cena** substitui o mapa e os recursos gerados pelo projeto na cena
vinculada, preservando tokens e conteúdo manual, configurações da cena e estado
das portas durante o jogo. Edições conflitantes interrompem a atualização;
cenas com conteúdo manual conservam dimensões e tamanho da célula. Consulte o
[guia do Map Builder](map-builder.md) para o fluxo, limites e plano de entregas.

## Durante a partida

| Área | Finalidade |
| --- | --- |
| Atores e tokens | Dados de personagem, mapeamento PDF, posicionamento, movimento e estado visual |
| Chat e dados | Mensagens, projeções privadas/do mestre suportadas, rolagens e presets |
| Diários | Diários, missões, quadros de missões, tabelas ponderadas e anexos de imagem/PDF |
| Áudio | Faixas, playlists, reprodução sincronizada e controles de som posicional |
| Cartas | Recursos de baralho, compra, mãos e estado das cartas na mesa |
| Combate | Turnos de encontro, iniciativa e efeitos |
| Compêndios | Pacotes reutilizáveis, controle de acesso e importações |
| Módulos | Extensões do navegador e superfícies sobrepostas/substituídas |

Consulte a [referência de notação de dados](../../gravewright/dice/grammar/notation/GRAMMAR.pt-BR.md) para expressões aceitas. O texto rico dos diários é armazenado como documento estruturado; o servidor filtra acesso a seções do mestre e materiais compartilhados. Exportações e capturas podem ter público diferente da mesa ao vivo, então selecione o conteúdo que compartilha.

Áudio no navegador pode exigir uma interação antes de tocar. Se a mesa parar de atualizar, confira a conexão e reconecte; atualizar a página recarrega o estado autorizado. Mudanças nos módulos ativos podem exigir que clientes carreguem o novo conjunto antes de chamar extensões.

## Preservar conteúdo

Exportação/importação, clonagem e snapshots dependem das opções da instância e das permissões. Exportações priorizam conteúdo portável e podem omitir histórico privado ou redefinir propriedade; não são backups completos da instância. Antes de restaurar snapshot ou substituir conteúdo, siga os procedimentos de [implantação](deployment.md).

Mapas, músicas, PDFs e outros uploads mantêm suas próprias licenças e titularidade. A licença do projeto não autoriza redistribuir livros ou mídias que não sejam seus. Módulos podem usar licenças diferentes; veja [licenciamento](../../LICENSING.pt-BR.md).

## Limitações atuais

- A preferência de idioma da aplicação oferece `en`; existe documentação em português, mas estas alterações não implementam interface traduzida.
- O sistema PDF nativo não fornece tipos de itens; o backend genérico de itens não representa um editor/catálogo nativo completo.
- O carregador de extensões executa JavaScript na página principal. Instale código confiável; assinaturas não fornecem isolamento.
- O marketplace online exige catálogo e chaves confiáveis. Hosts gerenciados instalam atualizações pela Administração mediante solicitação do proprietário. Apps Django da biblioteca de módulos são ativados para todo o servidor e exigem reinício automático; módulos de navegador continuam vinculados às mesas.

Para desenvolvimento ou integrações, continue nos guias de [API](api.md) e [módulos](modules.md).
