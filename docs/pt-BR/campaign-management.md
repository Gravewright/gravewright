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
| Personagens e fichas PDF | Atores da campanha e fichas do sistema; no PDF System, seleção de PDF, campos manuais, rolagens salvas, cálculos e mapeamentos reutilizáveis |
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
