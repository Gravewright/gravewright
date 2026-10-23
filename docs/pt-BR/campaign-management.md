# Gerenciar uma campanha

[Documentação](../README.pt-BR.md) · [English](../en/campaign-management.md) · [Guia de uso](user-guide.md)

Use **Gerenciar campanha** no cartão de uma campanha ou na prévia de sua capa
para preparar o conteúdo antes de entrar na mesa. O link abre
`/campaigns/<uuid-da-campanha>/manage` para a campanha selecionada.

O acesso segue o vínculo atual com a campanha. Todo mestre pode usar a área,
inclusive um comestre cuja conta tenha o papel de participante. Um proprietário
do servidor que seja apenas jogador daquela campanha não recebe acesso de
gerenciamento. Jogadores, espectadores de transmissão e pessoas sem vínculo
não podem usar essa área do mestre. Alterar ou revogar o vínculo passa a valer
nas requisições autorizadas seguintes.

## Ferramentas de conteúdo

A área de gerenciamento usa os documentos existentes e os editores nativos da
campanha. Não há uma segunda cópia da campanha para mesclar depois com a mesa.

| Área | O que preparar |
| --- | --- |
| Diários e missões | Diários, páginas, missões, quadros de missões e tabelas de rolagem nos editores nativos, com seus anexos e regras de acesso |
| [Relógios](clocks.md) | Relógios de progresso da campanha ou cena selecionada, com visibilidade, controles dos jogadores e fixação compartilhados com a mesa |
| [Pistas](clues.md) | Descobertas por etapas compartilhadas com a mesa; jogadores recebem o conteúdo somente após conclusão e visibilidade pública |
| [Mapas mentais](mindmaps.md) | Grafos de tópicos com notas, ramificações e vínculos nativos; o mestre configura leitores e jogadores editores, que usam os mesmos grafos na mesa |
| Personagens e [fichas PDF](pdf-system.md) | Atores da campanha e fichas do sistema; no PDF System, seleção de PDF, campos manuais, rolagens salvas, cálculos e mapeamentos reutilizáveis |
| Itens | Documentos e formulários de itens fornecidos pelo sistema instalado na campanha |
| Cenas e MapBuilder | Cenas da campanha, projetos editáveis de mapa e cenas existentes compatíveis; gerar ou atualizar uma cena continua sendo uma operação explícita |
| Biblioteca de arquivos | Imagens, PDFs e áudio da campanha pelas ferramentas nativas de upload, pastas e arquivos |
| Áudio | Faixas, playlists e a configuração de áudio compatível com a campanha |
| Cartas | Baralhos nativos, imagens de cartas e operações permitidas sobre os baralhos |
| Compêndios | Conteúdo autorizado da campanha e dos pacotes instalados, usando os catálogos e as ferramentas de documentos existentes |
| Membros e permissões | Convites, participantes atuais e editores nativos de acesso a documentos, pastas e páginas |

Em **Participantes**, **Convidar jogadores** cria um convite válido por 24 horas
com limite de 10 usos. O modal nativo mostra o código em um campo somente de
leitura; **Copiar código** o copia para a área de transferência quando acionado.

**Remover participante** abre um modal nativo de confirmação que identifica a
pessoa antes de enviar a remoção. O serviço da campanha verifica novamente o
vínculo de mestre de quem solicita e recusa remover outro mestre ou o próprio
vínculo do solicitante.

Diários e missões usam os mesmos modelos de documento e editores do jogo.
O gerenciamento não introduz outro formato de notas nem outro sistema de missões.
Páginas de diário exclusivas do mestre e documentos privados mantêm suas regras
de audiência. Abrir um documento ou vinculá-lo a uma missão não concede aos
jogadores acesso ao seu conteúdo privado.

Fichas abertas pelo diretório de atores editam o ator da campanha. Snapshots
independentes de tokens mantêm seus próprios estados e as regras nativas de
sincronização. Alterar o layout PDF continua sendo uma operação do mestre;
os valores dos personagens continuam seguindo as permissões da ficha. Tipos de
item e regras de jogo pertencem ao sistema instalado; um sistema sem tipos de
item não ganha um catálogo de itens nessa área.

Consulte o [guia do MapBuilder](map-builder.md) para adoção, fontes vinculadas e
atualização de cenas, e [Universal VTT](universal-vtt.md) para limites e avisos
de importação.

## Ferramentas de preparação

Estas ferramentas são exclusivas dos mestres da campanha. Planos de sessão,
eventos da cronologia, notas privadas e as escolhas do painel ficam guardados
na campanha, e os jogadores nunca os recebem. Cada mestre tem o próprio painel.
Os outros mestres veem as alterações nos registros compartilhados na próxima
atualização da página, que acontece automaticamente a cada 15 segundos.

| Área | O que faz |
| --- | --- |
| Painel da visão geral | Documentos fixados, a próxima sessão planejada, pendências, diagnóstico das fichas e eventos futuros. **Personalizar painel** mostra, oculta e reordena esses painéis para você |
| Missões | Colunas para cada estado de missão. Arraste um cartão para outra coluna ou use **Mover missão para** pelo teclado. Os cartões mostram personagens responsáveis, o progresso dos objetivos (que podem ser marcados no próprio cartão) e pré-requisitos. Uma missão ativa antes de seus pré-requisitos serem concluídos mostra um aviso |
| Planejador de sessões | Uma sequência ordenada de cenas, encontros, missões, diários, personagens, itens, áudio e notas, com checklist e notas privadas. **Encerrar sessão** registra um resumo e as pendências; etapas e itens do checklist ainda abertos são sugeridos como pendências. Essas pendências aparecem depois no painel |
| Cronologia | Eventos com uma data no mundo em texto livre, uma data opcional no calendário, a marcação "futuro" e vínculos com documentos da campanha. Os eventos aparecem na ordem que você definir. A visualização de calendário mostra os eventos e as sessões planejadas que têm data no calendário |
| Conexões | O que um personagem, item, diário ou cena vincula e onde é usado: referências no texto de diários, responsáveis e pré-requisitos de missões, quadros de missões, marcadores de cena, tokens, planos de sessão e vínculos da cronologia |
| Ver como jogador | Escolha um jogador para ver os diários, páginas, personagens, itens e cenas que o servidor envia a ele. Os diários abrem numa prévia somente leitura da versão do jogador, sem os blocos exclusivos do mestre |
| Histórico e lixeira | Versões anteriores de cada diário, comparadas linha a linha com a versão atual. Um mestre pode restaurar qualquer uma delas. Diários excluídos vão para a lixeira, e restaurar um deles traz de volta identificador, páginas, acessos, vínculos com quadros de missões e arquivos, sem restaurar o resto da campanha |

Digite **@** no texto editável do diário para abrir o seletor de referências no
gestor. A busca consulta os recursos da campanha pela API HTTP autorizada sem
entrar na mesa. Cada destino mantém seus controles de acesso. No
gerenciador, uma referência de cena seleciona essa cena para preparação; na
mesa, ela abre o diretório de cenas.

Os pré-requisitos de missões ficam guardados na missão e só os mestres os veem.
Eles não podem formar um ciclo. Editores que não enviam pré-requisitos mantêm
os já guardados.

Uma versão é registrada antes de cada alteração num diário. Salvamentos da
mesma pessoa em até cinco minutos viram uma única versão, e cada diário guarda
suas 50 versões mais recentes. Restaurar uma versão registra o conteúdo
substituído como nova versão, então uma restauração também pode ser desfeita.
Não é possível restaurar uma versão que use arquivos removidos depois do
documento. A lixeira guarda até 200 diários excluídos. Os arquivos de um diário
na lixeira só são apagados quando ele é excluído permanentemente. Marcadores de
mapa removidos junto com um diário não são recriados ao restaurá-lo.

O diagnóstico das fichas vem do sistema da campanha pela operação opcional de
sistema `preparation.diagnostics`. O PDF System aponta fichas sem PDF
selecionado e cálculos salvos que não podem ser avaliados; a geometria das
páginas continua sendo verificada quando a ficha é aberta. Sistemas que não
oferecem essa operação não mostram o painel.

Exportações, cópias e snapshots incluem planos de sessão, eventos da cronologia,
painéis e histórico de diários, com os arquivos mantidos pela lixeira. Selecione
**Preparação** ao copiar para incluir planos, eventos e opções do painel; o
histórico acompanha **Diários**. As cópias incluem os arquivos físicos.
Importações portáteis atribuem um painel ao mestre que importa (o seu painel
correspondente ou o primeiro painel da origem, com preferência pelo proprietário),
sem adicionar participantes ou permissões de usuários. Snapshots restauram o
painel de cada mestre atual. Arquivos antigos que não armazenavam a preparação
preservam a preparação e o histórico existentes ao restaurar uma campanha.

Selecione **Mapas mentais** separadamente para copiar os grafos colaborativos.
Vínculos tipados apontam aos recursos copiados; destinos omitidos ficam
indisponíveis sem vincular à campanha de origem. Cópias portáteis limpam concessões
de edição; snapshots as preservam na mesma campanha. Mapas com escopo de cena
acompanham a seleção das cenas. Veja colaboração e permissões em
[Mapas mentais](mindmaps.md).

Restaurar uma versão revalida a visibilidade, os pré-requisitos e os arquivos
antes de salvar. A versão esperada é aquela exibida na comparação; se outro mestre
editar o documento, abra uma nova comparação antes de restaurar. Arquivos ausentes
mantêm o registro na lixeira e geram um erro. Rascunhos de sessão são preservados
ao selecionar a sessão atual, e os campos ficam desativados durante o salvamento.

A preparação aceita 200 planos de sessão e 1.000 eventos por campanha. Cada
sessão tem até 64 etapas e 64 itens de checklist, com até 32 pendências registradas
ao concluir. Cada mestre pode fixar 24 documentos; cada evento pode vincular 24.
Datas do calendário usam `YYYY-MM-DD`; a data do mundo é texto autoral e o núcleo
não interpreta o calendário de um jogo.

Arquivos completos de campanha contêm preparação privada, notas do mestre e
histórico. Compartilhe-os somente com o público pretendido. Uma importação
portátil remove permissões específicas, mas não transforma segredos autorais em
material público. Exportações de recursos para compêndios omitem preparação e
histórico. Mantenha os arquivos físicos ao arquivar anexos da lixeira; exportar
esse arquivo sem os anexos é rejeitado.

## Preparar conteúdo e entrar no jogo

Abrir o gerenciamento não inicia o canvas da mesa, o renderizador Pixi, a conexão
WebSocket do jogo nem a presença na mesa. É possível organizar o conteúdo sem
entrar na cena em andamento. **Entrar na mesa** continua sendo uma ação separada.

Os salvamentos alteram os registros compartilhados da campanha. Comandos
explícitos como reproduzir áudio, transmitir uma cena ou comprar cartas mantêm
seus efeitos e permissões nativos; use-os quando quiser alterar aquele estado
da campanha. Apenas abrir o gerenciamento não executa esses comandos.

Mantenha o fluxo normal de salvamento e conflitos. Cada nova alteração lógica
usa um UUID de requisição novo; uma repetição da mesma operação reutiliza seu
UUID. As revisões detectam edições concorrentes. Se o documento mudou em outra
janela, recarregue o estado atual e revise a alteração, sem substituir a revisão
esperada silenciosamente. Editores nativos preservam seu comportamento de
salvamentos pendentes, fechamento e descarte.

## Autorização e integração

O servidor verifica novamente o vínculo com a campanha, o acesso do mestre e
a titularidade dos recursos. Ocultar botões não é a barreira de autorização.
Uma URL de gerenciamento ou um ID de arquivo conhecido não permite acessar
outra campanha. O conteúdo entregue a jogadores e espectadores continua
filtrado pelos respectivos serviços nativos.

A página Inside acrescenta `can_manage` às linhas da apresentação usando os
vínculos atuais; o formato JSON público das campanhas permanece igual. As
ferramentas de gerenciamento reutilizam a API pública do navegador e os serviços
nativos dos domínios, sem escrever documentos diretamente nem criar depósitos
separados. Veja a [referência da API](api.md) para revisões, recibos,
transferências de arquivos e capacidades fornecidas pelo sistema.
