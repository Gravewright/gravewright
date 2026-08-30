// Conteúdo da wiki em português brasileiro.
import { releaseGuides } from "./release-guides.mjs";

export const guides = [
  {
    slug: "inicio", section: "Comece aqui", title: "Bem-vindo ao Gravewright",
    summary: "Entenda o que é o Gravewright e escolha seu próximo passo.",
    body: `# Bem-vindo ao Gravewright

O Gravewright é uma mesa virtual para jogar RPG pelo navegador. Uma pessoa executa o aplicativo e assume o papel de **GM**; os demais entram como jogadores por um link ou código de convite.

Você não precisa conhecer programação para jogar. O fluxo normal é:

1. instalar e iniciar o Gravewright;
2. criar uma mesa;
3. escolher um ruleset ou usar fichas PDF;
4. preparar uma cena e os personagens;
5. convidar o grupo;
6. abrir a mesa e jogar.

## Escolha sua jornada

- **Quero mestrar:** siga para *Instalação* e depois *Sua primeira mesa*.
- **Sou jogador:** leia *Entrando como jogador* e *Conhecendo a interface*.
- **Quero publicar um servidor:** leia *Servidor e produção* depois de testar localmente.
- **Quero criar um sistema:** comece em *Pacotes e rulesets*.

## Conceitos essenciais

**Mesa** é a campanha compartilhada. **Cena** é o mapa atual. **Ator** representa personagem, criatura ou NPC. **Item** representa equipamento, habilidade ou recurso definido pelo ruleset. **Diário** guarda textos, missões e quadros de missão. **Ruleset** ensina ao Gravewright as regras e fichas de um jogo.

> [!NOTE]
> Gravewright Beta ainda está evoluindo. Faça backups antes de atualizações e antes de mudanças grandes na campanha.

## O que você deve ver ao terminar

Depois do guia inicial, você terá uma mesa aberta no navegador, uma conta de GM e um caminho claro para preparar sua primeira sessão.`
  },
  {
    slug: "instalacao", section: "Comece aqui", title: "Instalação e primeiro início",
    summary: "Instale o ZIP desktop no Windows ou execute um checkout do código-fonte.",
    body: `# Instalação e primeiro início

## Windows: pacote desktop recomendado

Este é o caminho para quem baixou **Gravewright-<versão>-win64.zip**. Ele já contém Python e dependências: não instale Python, Git ou \`uv\`.

1. No Explorador de Arquivos, clique com o botão direito no ZIP e escolha **Extrair Tudo**.
2. Mova a pasta extraída para um local permanente. Não execute o programa dentro do ZIP.
3. Abra a pasta **Gravewright** e execute **Gravewright.exe**. O arquivo precisa permanecer ao lado da pasta **_internal**.
4. Se o SmartScreen aparecer, confirme que o arquivo veio da release oficial e use **Mais informações → Executar assim mesmo**.
5. Na janela **Gravewright Launcher**, clique em **Start Gravewright**.
6. Aguarde o estado mudar de **Server stopped** para **Running at** seguido de um endereço local, como \`http://127.0.0.1:54321/\`. A porta é escolhida automaticamente e pode não ser 8000.
7. O navegador abre sozinho. Se não abrir, clique em **Open in browser**.

Mantenha o launcher aberto durante a sessão. **Stop Gravewright** encerra o servidor; fechar o launcher também o encerra.

### Onde os dados ficam

No primeiro início é criada a pasta **GravewrightData** ao lado do executável. Ela contém banco SQLite, uploads e pacotes instalados. O botão **Open data folder** abre exatamente essa pasta. Para atualizar o app, substitua a pasta do programa, mas preserve **GravewrightData**.

### Manutenção pelo launcher

- **Doctor** verifica banco, diretórios e pacotes; o resultado aparece no painel de logs.
- **Backup** cria um ZIP verificado com banco, assets e pacotes.
- **Restore** só funciona com o servidor parado e pede confirmação antes de substituir dados.
- **Packages** executa list, install, enable, disable, update, doctor e remove por ID.
- **Logs** mostra ou oculta o log do servidor.

Se o launcher normal não iniciar, execute **Gravewright-debug.exe** na mesma pasta e copie o erro exibido no console.

## Windows: checkout do código-fonte

Use este caminho somente se você baixou ou clonou o repositório e enxerga arquivos como **install-windows.bat**, **pyproject.toml** e **uv.lock**.

1. Extraia ou clone o repositório inteiro.
2. Dê duplo clique em **install-windows.bat**.
3. O script instala \`uv\` para o usuário atual, executa \`uv sync --frozen\`, cria a configuração local e um \`SESSION_SECRET\`, roda o diagnóstico e inicia o servidor.
4. Aguarde a mensagem **Starting Gravewright**; o navegador abrirá em \`http://127.0.0.1:8000\`.
5. Mantenha a janela do terminal aberta. Fechá-la ou pressionar \`Ctrl+C\` encerra o servidor.

Nas próximas vezes, dê duplo clique no mesmo **install-windows.bat**. Ele reaproveita o ambiente já preparado.

Para manutenção manual, abra PowerShell na raiz do projeto:

\`\`\`powershell
.\\grave.bat doctor
.\\grave.bat run --open
\`\`\`

## Primeiro acesso

1. Na tela **Login**, clique em **Criar conta**.
2. Preencha nome, e-mail e uma senha com pelo menos 8 caracteres.
3. A primeira conta registrada recebe o papel global **OWNER**; isso é diferente de ser GM de uma campanha.
4. Após entrar, confirme que aparecem as abas **Campanhas**, **Sistemas de regras** e **Add-ons**. **Configurações** e **Privacidade** aparecem somente para o owner.

## Diagnóstico por sintoma

**O desktop não encontra os dados:** não mova apenas o EXE; mova a pasta Gravewright completa e mantenha **GravewrightData** ao lado dela.

**O botão Start falha:** clique em **Doctor**, abra **Logs** e, se necessário, use **Gravewright-debug.exe**.

**O checkout informa que uv não existe:** feche a janela, abra novamente e rode **install-windows.bat**; a primeira instalação pode exigir uma nova sessão para atualizar o PATH.

**A página não abre:** no desktop use **Open in browser** e o endereço/porta mostrados no launcher. No checkout use \`http://127.0.0.1:8000\`.

**A tela aparece sem estilos:** você abriu um HTML pelo Explorador. Gravewright deve ser acessado pelo endereço HTTP aberto pelo launcher.`
  },
  {
    slug: "primeira-mesa", section: "Comece aqui", title: "Sua primeira mesa",
    summary: "Crie uma campanha, escolha o sistema e entre no espaço de jogo.",
    body: `# Sua primeira mesa

## Criar a campanha

1. Entre com sua conta e permaneça na aba **Campanhas** do painel interno.
2. Clique em **Criar campanha**.
3. Preencha **Título** (obrigatório, até 120 caracteres) e **Descrição** (opcional).
4. Clique novamente em **Criar campanha**. O novo cartão aparece na lista.
5. No cartão, clique em **Abrir** para entrar na mesa ou em **Gerenciar mesa** para sistema, pacotes, membros, códigos e snapshots.

## Escolher o sistema

Se o cartão mostra **Sem sistema de regras anexado**, faça uma destas opções:

1. abra **Sistemas de regras** no painel interno;
2. instale e **Ative** um ruleset disponível, ou use **Enviar um ruleset** para um ZIP válido;
3. em **Atribuir à campanha**, escolha a campanha;
4. volte a **Campanhas** e confirme **Sistema de regras: <nome>**.

Também é possível abrir a mesa sem sistema: o modal **Vincular sistema de regras** explicará que atores e itens só serão liberados depois do vínculo. O sistema determina tipos de ator/item, fichas, rolagens e combate. Para fichas preenchíveis, use **Gravewright PDF System**.

## Preparação mínima para um teste

Ao abrir a mesa como GM, use **Primeiros passos do GM**. O checklist acompanha quatro ações reais:

1. vincular um sistema;
2. criar um personagem pelo diretório **Atores**;
3. criar uma cena pelo painel **GM → Cenas**;
4. gerar um código pelo painel **GM → Jogadores**.

Para testar o tabuleiro, envie um mapa em **Cenas → Enviar mapa**, marque **Ativar após enviar** e aguarde as etapas *Enviando*, *Preparando*, *Fatiando tiles* e *Gravando blocos*. Depois arraste o ator do diretório para o mapa para criar o token.

Abra uma segunda janela anônima com uma conta de jogador. Isso revela imediatamente diferenças de permissão e visibilidade.

## Checklist antes de convidar o grupo

- a cena correta está ativa;
- o mapa abre sem erro;
- o jogador enxerga apenas o que deveria;
- o ator pertence ao jogador;
- fichas e itens abrem;
- o chat envia mensagens e rolagens;
- existe um backup recente.

> [!TIP]
> Prepare primeiro uma sala de teste. Quando o fluxo estiver confortável, crie ou importe a campanha definitiva.`
  },
  {
    slug: "jogador", section: "Jogadores", title: "Entrando como jogador",
    summary: "Aceite um convite, entre na mesa e configure sua experiência.",
    body: `# Entrando como jogador

## Entrar por convite

Há dois fluxos diferentes:

- **Código de entrada:** no painel **Campanhas**, clique em **Entrar em uma mesa**, digite o código no formato mostrado e pressione **Entrar na mesa**. Você entra como Player.
- **Link com código:** faça login, abra o link e confirme em **Continuar e entrar**.
- **Convite nominal:** aparece em **Convites pendentes**. Confira quem convidou e a função oferecida, depois use **Aceitar** ou **Recusar**.

Depois da confirmação, o cartão da campanha aparece em **Campanhas** com sua função. Clique em **Abrir**.

## Primeira entrada

Na primeira vez em cada mesa, o Gravewright abre **Modo de interface**. Antes de fechar, escolha:

- **Classic Mode:** painéis tradicionais e acesso direto às ferramentas;
- **Gravewright Mode:** apresentação reorganizada para a experiência do Gravewright;
- **Visão clássica:** menos efeitos visuais;
- **Visão cinematográfica:** efeitos e apresentação mais ricos.

- a cor em **Cor do seu ping**;
- **Classic Mode** ou **Gravewright Mode**;
- visão **Clássica** ou **Cinematográfica**;
- se **Shaders da mesa** ficam ligados.

Essas escolhas são salvas para seu usuário naquela campanha. Alterá-las não muda a tela dos outros jogadores; depois você pode reabrir a configuração pelo ícone de engrenagem.

## Antes da sessão

1. confirme se seu nome aparece online;
2. abra o ator concedido pelo GM;
3. teste a ficha e uma rolagem;
4. confirme que o mapa e o token estão visíveis;
5. informe ao GM se algum diário ou item esperado não aparece.

## Se você perder acesso

Atualize a página e volte à lista de mesas. Se a campanha desapareceu, o convite pode ter sido revogado ou sua associação removida. Um jogador banido é expulso imediatamente e não consegue reutilizar o convite antigo.`
  },
  {
    slug: "interface", section: "Jogadores", title: "Conhecendo a interface",
    summary: "Aprenda a navegar entre mapa, diretórios, ferramentas e janelas.",
    body: `# Conhecendo a interface

O centro da tela é o tabuleiro. Os diretórios ficam na lateral e abrem cenas, atores, itens, diários, combate e configurações.

## Janelas

Fichas, permissões, criação e configurações abrem em janelas. A barra superior oferece arrastar, minimizar, maximizar/tela cheia e fechar. As janelas **Novo ator**, **Novo item**, **Criar Entrada** e **Permissões** abrem próximas da aba lateral que as originou.

## Navegação do mapa

- use a roda do mouse para aproximar e afastar;
- arraste o tabuleiro com a ferramenta apropriada;
- selecione tokens com clique;
- use ping para indicar um ponto ao grupo;
- medições ajudam a conferir distâncias.

## Diretórios e ferramentas

Na coluna direita ficam Busca, Chat, Atores, Itens, Diário, Combate e configurações. Na mesa ficam as ferramentas com atalhos: **Selecionar (S)**, **Alvo (T)**, **HP (H)**, **Régua (R)**, **Desenho (D)**, **Notas (N)**, **Marcadores (M)**, **Paredes (W)**, **Névoa (F)** e **Iluminação (L)**.

Pastas apenas organizam atores, itens e diários; não concedem acesso. Clique com o botão direito em uma entrada para **Abrir**, **Permissões** ou excluir. Para mover conteúdo, arraste a entrada para a pasta e confira o contador da pasta.

## Atalhos seguros para aprender

Passe o cursor pelos botões antes de clicar. Os nomes das ferramentas aparecem em tooltip. Teste movimento, zoom, seleção e abertura de fichas antes de usar ferramentas de parede ou exclusão.

## Recuperação

Se uma janela ficar fora de posição, feche e abra novamente. Se a interface parar de responder, recarregue a página; alterações persistidas no servidor continuam salvas.`
  },
  {
    slug: "jogadores-permissoes", section: "Mestrando", title: "Jogadores, convites e permissões",
    summary: "Convide o grupo e controle leitura, propriedade e acesso.",
    body: `# Jogadores, convites e permissões

## Convidar

Dentro da mesa, abra **GM → Jogadores** e use **Gerar código de entrada**. Copie o código ou link exibido e envie ao grupo. Códigos colocam a pessoa como Player; para outra função, use o convite nominal disponível no gerenciamento da campanha.

## Papéis da campanha

- **GM:** administra campanha, membros, cenas e todo o conteúdo;
- **Assistant GM:** função administrativa delegada, sem transformar o usuário em owner global;
- **Player:** usa o tabuleiro e apenas recursos concedidos;
- **Streamer:** sessão de leitura gerada por link, sem chat nem controles da mesa.

## Permissões de atores, itens e diários

Nos diretórios **Atores**, **Itens** ou **Diário**, clique com o botão direito na entrada e escolha **Permissões**. O modal segue o mesmo modelo nos três recursos. Para **Players**, selecione:

- **Nenhuma:** o recurso não é exibido;
- **Apenas leitura:** pode abrir, mas não alterar;
- **Dono:** pode editar dentro dos limites do ruleset.

Finalize em **Salvar permissões**. Use **Dono** para a ficha do personagem; **Apenas leitura** para NPCs visíveis, itens de referência e handouts. Pastas não propagam permissões automaticamente.

## Remover ou banir

Remover encerra a associação atual. Banir também impede a reutilização de convites aceitos anteriormente e expulsa imediatamente a pessoa conectada.

> [!WARNING]
> Teste permissões com uma conta real de jogador. A visão do GM mostra conteúdo que pode estar corretamente oculto para o grupo.`
  },
  {
    slug: "cenas", section: "Mestrando", title: "Cenas, mapas, paredes e visão",
    summary: "Monte um mapa jogável e controle o que cada personagem enxerga.",
    body: `# Cenas, mapas, paredes e visão

## Criar uma cena

1. abra **GM → Cenas**;
2. em **Enviar mapa**, preencha **Nome da cena** e escolha **Imagem do mapa**;
3. escolha um **Grupo** ou deixe **Sem grupo**;
4. defina **Visibilidade**: Jogadores, Apenas GM ou Oculta;
5. configure **Mostrar grid**, cor, opacidade e **Tamanho do grid**. O grid é independente da resolução da imagem;
6. mantenha o tile raster e chunk nos padrões se não souber por que alterá-los;
7. marque **Ativar após enviar** e envie.

Aguarde a sequência **Enviando arquivo → Preparando mapa → Fatiando tiles → Gravando blocos → Concluído**. Fechar durante esse processo pode interromper a criação.

Depois, o cartão da cena oferece **Navegar sem carregar para a mesa**, **Ativar** e **Configurar**. Navegar muda apenas sua visão; ativar muda a cena compartilhada. Em **Configurar**, ajuste a cena ou use **Usar visão atual como início**.

## Paredes e portas

Pressione **W** ou escolha **Paredes** e selecione **Parede**, **Porta**, **Janela** ou **Passagem secreta** antes de desenhar. Clique nos pontos do contorno e conecte as extremidades; frestas permitem visão. Volte a **Selecionar (S)** para editar ou apagar segmentos. Teste portas como GM e depois em **Alternar visão GM/jogador**.

## Iluminação e visão dinâmica

Selecione o token e abra **Visão do token** para configurar alcance e quem enxerga por ele. Pressione **L** para adicionar luz e ajuste alcance, cor e intensidade no editor. O jogador precisa ser dono do ator/token para usar sua visão. Use **Alternar visão GM/jogador**; olhar apenas como GM não valida o resultado.

## Névoa e revelação

Fog of war controla áreas conhecidas. Revele somente o necessário e use reset com cuidado, pois ele altera o estado compartilhado.

## Diagnóstico

Se um jogador vê através de uma parede, procure extremidades desconectadas. Se tudo está escuro, confirme visão do token, luz ambiente e ownership do ator. Se o mapa está lento, reduza efeitos e teste o modo clássico.`
  },
  {
    slug: "atores-tokens", section: "Mestrando", title: "Atores e tokens",
    summary: "Crie personagens, conceda propriedade e coloque-os no mapa.",
    body: `# Atores e tokens

## Criar um ator

1. abra a aba **Atores** na lateral direita;
2. clique em **Criar Ator**;
3. informe o nome e escolha um tipo fornecido pelo ruleset;
4. confirme; a entrada aparece no diretório;
5. clique para abrir a ficha e preencha os campos do sistema.

Se não houver tipos ou a criação disser que o sistema não está ativado, volte ao painel, ative um ruleset e vincule-o à campanha.

## Dar o personagem ao jogador

Clique com o botão direito no ator, escolha **Permissões**, marque o jogador como **Dono** e salve. **Apenas leitura** permite consultar, mas não controlar como personagem. Depois entre com a conta do jogador e confirme que a ficha abre e salva.

## Colocar no mapa

Com uma cena ativa, arraste a entrada do ator para um ponto do mapa. Isso cria uma instância de token vinculada ao ator. Arrastar novamente cria outra instância; não duplica o ator do diretório.

## Configurar o token

Selecione o token e revise imagem, tamanho, nome, disposição, barras e visão. As barras vêm dos mapeamentos do ruleset. Se HP não aparecer, confirme que a ficha possui o valor esperado e que o ruleset declarou o mapeamento. A ferramenta **HP (H)** aplica Dano, Cura ou Define valor ao token controlado; GMs controlam todos.

## Movimento

Jogadores movem apenas tokens autorizados. Paredes e portas podem limitar o caminho. O GM pode reposicionar e corrigir tokens bloqueados.

## Boas práticas

Use pastas para separar personagens, aliados e criaturas. Dê nomes únicos e mantenha uma imagem de tamanho moderado para cada ator.`
  },
  {
    slug: "itens-fichas-pdf", section: "Mestrando", title: "Itens, fichas e PDFs",
    summary: "Use fichas do ruleset, equipamentos e documentos PDF preenchíveis.",
    body: `# Itens, fichas e PDFs

## Itens

1. abra **Itens** e clique em **Criar Item**;
2. informe o nome e escolha um tipo fornecido pelo ruleset;
3. abra o item e preencha sua ficha;
4. para compartilhar o item solto, use botão direito → **Permissões**;
5. para incorporá-lo a um ator, arraste-o para uma zona da ficha que aceite aquele tipo.

Se o drop for rejeitado, a zona pode não aceitar o tipo, o item pode pertencer a outro ruleset ou o sistema pode não ter uma ação de drop definida. Criar uma pasta não altera nenhum desses comportamentos.

## Fichas HTML e declarativas

O ruleset controla os campos e ações disponíveis. Alterações são salvas pelo servidor; aguarde o indicador de salvamento antes de fechar.

## Gravewright PDF System

Use este ruleset quando o jogo possui uma ficha PDF preenchível:

1. no painel interno, abra **Sistemas de regras**;
2. localize **Gravewright PDF System**, use **Instalar** se aparecer como Disponível e depois **Ativar**;
3. em **Atribuir à campanha**, selecione sua mesa;
4. abra a campanha e crie um ator do tipo disponibilizado pelo pacote;
5. abra a ficha e carregue o PDF pelo controle da própria ficha;
6. altere alguns campos, feche e reabra o ator para testar persistência;
7. arraste o ator para a cena e confira nome/barras definidos pelo mapeamento do pacote.

O PDF enviado e os valores de formulário são armazenados pelo Gravewright; abrir o arquivo fora do aplicativo não substitui o dado salvo. Apenas campos AcroForm reais são editáveis. Um PDF escaneado ou "achatado" pode ser visualizado, mas não oferece campos.

## Segurança e direitos autorais

Envie somente PDFs que você tem direito de usar. PDFs enviados por usuários ficam no armazenamento da campanha e não devem ser adicionados ao repositório do core.

## Quando um campo não funciona

Confirme se o PDF realmente possui campos de formulário. PDFs apenas escaneados não oferecem campos editáveis. Verifique também os mapeamentos do ruleset e o console de diagnóstico.`
  },
  {
    slug: "diarios-missoes", section: "Mestrando", title: "Diários, missões e quadros",
    summary: "Organize textos de campanha e publique missões para os jogadores.",
    body: `# Diários, missões e quadros

## Diários

Abra a aba **Diário** e use **Criar Entrada**. Digite o título, escolha **Diário** em **Tipo** e clique em **Criar diário**. Dentro do editor:

- digite \`/\` para inserir Texto, Títulos, listas, citação, separador, imagem, **Nota do GM** ou **Segredo**;
- use **Nova seção** para Página, Capítulo, Seção ou Subseção;
- em **Audiência**, escolha **Mesa** ou **Só mestre** por seção;
- acompanhe o estado **Alterado → Salvando… → Salvo** antes de fechar;
- use botão direito → **Permissões** no diretório para definir Nenhuma, Apenas leitura ou Dono.

**Criar Pasta** e subpastas organizam as entradas, mas não tornam seu conteúdo público.

## Criar uma missão

1. no diretório de diários, escolha **Criar Entrada**;
2. selecione **Missão**;
3. informe o título;
4. abra a missão e clique em **Editar**;
5. preencha local, contratante, resumo, descrição pública e tags;
6. adicione objetivos e recompensas;
7. marque apenas os elementos que devem ser visíveis;
8. altere o status para **Disponível**.

Na edição, a navegação lateral separa **Conteúdo**, **Objetivos**, **Recompensas** e **Área exclusiva do GM**. Em cada objetivo ou recompensa, marque **visível** somente quando o jogador puder vê-lo. Objetivos também podem ser marcados como opcionais e concluídos.

Missões em rascunho ou arquivadas não aparecem na ficha pública nem no quadro.

## Quadro de missão

Crie uma entrada do tipo **Quadro de missão** e abra **Editar**. Em **Missões vinculadas**, escolha uma missão e use **Adicionar missão**. Para cada linha você pode alterar o status, fixar/desafixar, ordenar pelas setas ou remover do quadro. O filtro de status nessa mesma área reduz a lista administrativa; ele não muda o status sozinho.

Na visualização pública, apenas missões vinculadas que não estejam em **Rascunho** nem **Arquivada** geram cards. Se nenhuma for publicável, o mural vazio fica centralizado.

## Status

Use **Disponível**, **Em andamento**, **Concluída** ou **Fracassou** conforme a narrativa. A mudança é transmitida aos jogadores conectados.

## Visibilidade

Objetivos e recompensas ocultos continuam disponíveis para o GM, mas não aparecem na ficha dos jogadores. Isso permite revelar consequências e metas no momento certo.`
  },
  {
    slug: "chat-combate", section: "Jogando", title: "Chat, dados e combate",
    summary: "Conduza rolagens, iniciativa, turnos e comunicação durante a sessão.",
    body: `# Chat, dados e combate

## Chat

Abra **Chat**, escreva no campo **Mensagem... (/ para ver comandos)** e envie. Os comandos disponíveis incluem:

- \`/roll 2d6+3\` para uma rolagem pública;
- \`/gmroll 1d20\` para resultado visível só a você e ao GM;
- \`/whisper nome mensagem\` para outro jogador;
- \`/gm mensagem\` para falar com o GM;
- \`/me ação\` para emote em terceira pessoa.

O GM pode apagar uma mensagem ou **Apagar todas as mensagens**. Rolagens e chat são validados pelo servidor; editar o HTML local não altera resultados.

## Rolagens

Na **Bandeja de dados**, clique nos dados ou escreva uma **Fórmula**, por exemplo \`2d20L1+3\`. Ajuste quantidade, modificador, descartar menores/maiores, explosão e dado extra quando aplicável. Preencha **Nome da rolagem** e escolha **Rolar** ou **Para o GM**. Fórmulas que o servidor não reconhece são recusadas.

## Iniciar combate

1. com **Selecionar (S)**, selecione os tokens envolvidos;
2. abra **Combate** e clique em **Adicionar tokens selecionados**;
3. use **Rolar iniciativa**, **Rolar dos NPCs**, **Rolar quem falta** ou defina um valor individual;
4. clique em **Iniciar combate**;
5. avance em **Próximo turno** ou **Próxima rodada**;
6. no menu do combatente, centralize token, abra ficha, passe o turno, oculte/revele ou marque como derrotado.

O ruleset pode alterar iniciativa, desempates e apresentação dos cartões.

## Durante o turno

Atualize condições e recursos pela ficha ou ações oferecidas. Confirme que o combatente ativo corresponde ao destaque no rastreador.

## Encerrar

Use **Encerrar combate** somente quando o encontro terminou. Isso limpa o estado ativo; registros narrativos importantes devem ser anotados no diário.`
  },
  {
    slug: "cartas-efeitos", section: "Jogando", title: "Cartas, luzes e efeitos",
    summary: "Use baralhos e atmosfera visual sem comprometer a sessão.",
    body: `# Cartas, luzes e efeitos

## Cartas

Cartas só aparecem quando o ruleset ou add-on ativo declara esse recurso. Nesse caso, abra o painel fornecido pelo pacote para criar/usar baralhos, comprar, revelar e descartar. Se não existir uma aba ou ação de cartas, não há um baralho genérico para configurar no core: primeiro ative um pacote que ofereça a interface.

Antes da sessão, teste compra, descarte e visibilidade com uma conta de jogador.

## Luzes

Pressione **L**, escolha a ferramenta de iluminação, clique na cena e configure a luz no editor. Use **Camada de jogo** para algo visível na mesa e **Camada GM** para preparação oculta. Depois selecione **Alternar visão GM/jogador** para validar paredes, alcance e token que fornece visão.

## Partículas e shaders

O GM edita partículas e shaders pelos controles da cena. Cada efeito possui configuração própria e é transmitido à mesa. O botão pessoal **Shaders da mesa**, em **Modo de interface**, permite ao jogador desligar shaders localmente sem apagar a configuração do GM.

## Regra prática de desempenho

Se a mesa perder fluidez:

1. desative shaders;
2. reduza partículas;
3. diminua luzes animadas;
4. teste em modo clássico;
5. verifique o tamanho do mapa e das imagens.

Atmosfera deve apoiar a sessão, não impedir interação com fichas e tokens.`
  },
  {
    slug: "administracao", section: "Administração", title: "Campanhas, snapshots e backups",
    summary: "Proteja os dados da mesa e recupere alterações indesejadas.",
    body: `# Campanhas, snapshots e backups

## Snapshot e backup não são a mesma coisa

**Snapshot** pertence a uma campanha e fica no mesmo banco. Ele inclui atores, itens, diários, cenas, tokens, combate, chat, permissões e arquivos da campanha; não inclui contas globais, sessões, auditoria nem o histórico de snapshots. **Backup** é um ZIP externo da instalação SQLite e pode incluir assets e pacotes.

## Rotina recomendada

No painel **Campanhas**, abra **Gerenciar mesa → Snapshots**. Informe nome e descrição e clique em **Criar snapshot**. Para voltar, escolha **Restaurar esta versão**; o Gravewright cria primeiro um snapshot automático de segurança. **Excluir** remove apenas aquele ponto, não a campanha.

Use snapshots antes de importar conteúdo ou alterar a campanha. Use backup antes de atualizar o Gravewright ou trocar pacotes e guarde o ZIP fora da instalação.

## Pela CLI

\`\`\`powershell
.\\grave.bat doctor
.\\grave.bat db status
.\\grave.bat backup -o gravewright-backup.zip --include-assets --include-packages --verify
\`\`\`

No desktop, **Backup** já inclui assets, pacotes e verificação. Para restaurar, pare o servidor, clique em **Restore**, escolha o ZIP e confirme. No checkout, teste primeiro com \`.\\grave.bat restore arquivo.zip --dry-run\` e só depois use \`--yes\`.

## Clonar e exportar

Clonagem é útil para testar alterações sem afetar a mesa original. Exportação transfere uma campanha conforme os recursos habilitados. Sempre confira permissões e pacotes necessários após importar.

## Antes de atualizar

Pare novas edições, faça backup verificado, anote a versão atual e execute a migração. Depois teste login, abertura da campanha, cenas, fichas e arquivos enviados.`
  },
  {
    slug: "servidor", section: "Administração", title: "Servidor, produção e segurança",
    summary: "Publique uma mesa com HTTPS, segredos próprios e banco protegido.",
    body: `# Servidor, produção e segurança

Comece localmente. Publique somente depois que GM e jogador conseguirem completar uma sessão de teste.

## Requisitos de produção

- domínio e HTTPS;
- \`SESSION_SECRET\` longo e exclusivo;
- cookies seguros;
- hosts e origens WebSocket permitidos;
- PostgreSQL para instalações multiusuário persistentes;
- armazenamento com backup;
- proxy reverso configurado para WebSocket.

O launcher desktop escuta apenas em loopback e serve para uso local. Ele não publica a mesa para jogadores externos. Para internet, execute o servidor por Docker ou processo gerenciado atrás de proxy HTTPS.

## Variáveis

Parta de \`.env.production\`, mas não publique segredos no Git. Configure \`APP_ENV=production\`, \`DATABASE_URL\`, \`SESSION_SECRET\`, \`ALLOWED_HOSTS\`, \`WS_ALLOWED_ORIGINS\` e cookies seguros. O proxy precisa encaminhar upgrade de WebSocket para \`/game/ws\`.

## Checklist de publicação

1. execute migrações;
2. execute \`grave doctor\`;
3. acesse por HTTPS;
4. teste login em outro dispositivo;
5. confirme conexão em tempo real;
6. envie e recupere um arquivo;
7. teste backup e restauração;
8. monitore logs sem expor dados pessoais.

> [!WARNING]
> Não exponha diretamente um servidor de desenvolvimento à internet. Use proxy HTTPS, firewall e segredos próprios.

Consulte \`SECURITY.md\` para relatar vulnerabilidades de forma responsável.`
  },
  {
    slug: "solucao-problemas", section: "Administração", title: "Diagnóstico e solução de problemas",
    summary: "Investigue falhas sem colocar campanhas em risco.",
    body: `# Diagnóstico e solução de problemas

## Comece pelo doctor

\`\`\`powershell
.\\grave.bat doctor
.\\grave.bat db status
\`\`\`

No desktop, clique em **Doctor** e depois em **Logs**. No checkout, use os comandos acima. Registre versão, sistema operacional, horário, código de saída e a primeira mensagem de erro.

## Tela não carrega

No desktop, confirme **Running at ...** e use **Open in browser**; a porta é dinâmica. No checkout, confirme que o terminal segue aberto e use \`http://127.0.0.1:8000\`. Uma página aberta por \`file:///\` não é o aplicativo. Depois teste janela anônima, console do navegador e logs.

## Tempo real não funciona

Se chat, presença ou atualizações não chegam, confira a origem WebSocket, proxy e HTTPS. A página HTTPS deve usar WebSocket seguro.

## Arquivo ou mapa falha

Confira formato, tamanho, espaço em disco e permissões do diretório de armazenamento. Não renomeie arquivos internos manualmente.

## Banco atrasado

Não altere tabelas à mão. Faça backup e execute a migração oficial. Se a migração falhar, preserve o banco e os logs antes de tentar novamente.

## Ao pedir ajuda

Envie passos reproduzíveis e mensagens de erro, mas remova emails, tokens, segredos, conteúdo privado e arquivos da campanha.`
  },
  {
    slug: "cli", section: "Criadores", title: "CLI do Gravewright",
    summary: "Use a linha de comando para executar, validar e manter o projeto.",
    body: `# CLI do Gravewright

O comando principal é \`grave\` no macOS/Linux e \`grave.bat\` no Windows.

## Comandos essenciais

\`\`\`text
grave doctor
grave run --open
grave backup -o backup.zip --verify
grave restore backup.zip
grave db status
grave db upgrade
grave package list
grave package validate caminho/do/pacote
grave package doctor id-do-pacote
\`\`\`

No Windows use o prefixo \`.\\grave.bat\`; no macOS/Linux, \`./grave\`. Os launchers chamam \`uv run python -m app.cli\` e devem ser executados na raiz do repositório. Use \`--help\` em qualquer nível:

\`\`\`powershell
.\\grave.bat --help
.\\grave.bat package --help
.\\grave.bat ruleset new --help
\`\`\`

## Saída para automação

Comandos de pacote oferecem \`--json\` quando indicado. Use essa saída em CI em vez de interpretar tabelas coloridas.

## Fluxo para validar um pacote

1. gere a estrutura com \`.\\grave.bat ruleset new meu-sistema --name "Meu Sistema" --sheets --rolls --combat --content\`;
2. valide com \`.\\grave.bat package validate data/packages/rulesets/meu-sistema\`;
3. instale com \`.\\grave.bat package install meu-sistema --yes --enable\`;
4. rode \`.\\grave.bat package doctor meu-sistema\`;
5. vincule a uma campanha descartável e teste como GM e Player;
6. gere \`grave.lock.json\` com \`.\\grave.bat lock -o grave.lock.json\` para registrar o conjunto instalado.

Um código de saída diferente de zero significa que a automação deve parar.`
  },
  {
    slug: "pacotes-rulesets", section: "Criadores", title: "Pacotes, SDK e rulesets",
    summary: "Crie extensões usando capabilities públicas sem depender do core interno.",
    body: `# Pacotes, SDK e rulesets

Todo conteúdo instalável é um pacote. Os tipos principais são **ruleset**, **addon**, **library**, **theme**, **content** e **assets**.

## Criar um ruleset

\`\`\`powershell
.\\grave.bat ruleset new meu-rpg --name "Meu RPG" --sheets --rolls --combat --content
\`\`\`

O pacote é criado em \`data/packages/rulesets/meu-rpg\`. O \`manifest.json\` identifica kind, versão, SDK, capabilities e entradas declarativas. Schemas definem dados; layouts definem fichas; arquivos de rolls, combat e mappings definem comportamento autorizado.

## Manifest

Declare apenas capabilities realmente usadas. Informe compatibilidade com SDK 1, dependências e arquivos por caminhos relativos. \`package validate\` verifica schema, referências e capabilities; \`package doctor\` também verifica instalação, integridade e dependências.

## Runtime público

Scripts acessam o SDK pelo objeto entregue em \`setup(sdk)\`. Não use imports do core, rotas privadas, banco, filesystem ou WebSocket bruto. Para persistência use \`storage.sqlite\`; para mensagens, assets e fichas declare a capability pública correspondente. O servidor continua validando papel, campanha e ownership.

## Ciclo de desenvolvimento

1. gere o pacote;
2. valide pela CLI;
3. instale e habilite;
4. ative em uma campanha de teste;
5. abra como GM e jogador;
6. execute o doctor;
7. empacote apenas arquivos declarados.

## Compatibilidade

SDK 1 RC 1 é o candidato público congelado; packages continuam declarando \`sdkVersion: "1"\`. Prefira adições compatíveis e teste versões mínima e verificada declaradas no manifest.`
  },
  {
    slug: "sdk-manifest", section: "SDK em profundidade", title: "Manifesto e ciclo de um pacote",
    summary: "Entenda cada bloco do manifest, ativação, validação e publicação.",
    body: `# Manifesto e ciclo de um pacote

O \`manifest.json\` não é metadado decorativo: é o contrato que o core valida antes de carregar qualquer arquivo. Ele responde **quem é o pacote**, **onde pode ser ativado**, **o que fornece** e **a quais APIs pede acesso**.

## Pacote mínimo explicado

\`\`\`json
{
  "$schema": "https://raw.githubusercontent.com/Gravewright/gravewright/main/schemas/gravewright-package-v1.schema.json",
  "schemaVersion": 1,
  "sdkVersion": "1",
  "kind": "addon",
  "id": "minha-condicao",
  "name": "Minha Condição",
  "version": "0.1.0",
  "compatibility": { "minimum": "1", "verified": "1", "maximum": "1.x" },
  "capabilities": ["assets.scripts", "assets.ui"],
  "activation": { "scope": "campaign", "mode": "multiple" },
  "entrypoints": { "game": { "scripts": ["scripts/main.js"] } },
  "settings": [], "dependencies": [], "conflicts": [], "provides": {}
}
\`\`\`

- \`schemaVersion\` seleciona o formato do JSON; na SDK 1 é número \`1\`.
- \`sdkVersion\` seleciona a linha da API, não a versão comercial do Gravewright.
- \`kind\` define o papel: ruleset é base exclusiva; addon e theme são extensões; library é dependência passiva; content e assets entregam conteúdo.
- \`id\` é identidade permanente. Ele deve coincidir com a pasta e com \`GravewrightSDK.register({ id })\`.
- \`version\` deve subir quando você publica assets novos; isso também evita cache antigo.
- \`activation\` controla onde carregar. Ruleset normalmente usa \`exclusive\`; addon, \`multiple\`; library, \`passive\`.
- \`entrypoints\` manda carregar JS/CSS. Declarar um arquivo em outro bloco não o executa automaticamente.

## provides: o que o core realmente consome

Use \`actorTypes\` e \`itemTypes\` para tipos e suas fichas; \`rules.formulas\` para regras; \`mappings.tokens\` para projeção no token; \`contentPacks\`, \`assets\`, \`locales\` e \`areaMarkers\` quando necessários. Não invente \`provides.sheets\`, \`provides.rolls\` ou \`provides.combat\`: essas chaves de topo não são contratos canônicos ativos.

## Validar, instalar e ativar

\`\`\`powershell
.\\grave.bat package validate data/packages/addons/minha-condicao --json
.\\grave.bat package install minha-condicao --yes --enable
.\\grave.bat campaign package activate ID_DA_CAMPANHA minha-condicao
.\\grave.bat package doctor minha-condicao
\`\`\`

Validação verifica o arquivo no disco. Instalação registra um snapshot. Enable torna o pacote globalmente disponível. Activate carrega-o em uma campanha. Confundir essas etapas é a causa mais comum de “o script existe, mas não roda”. Ao editar um pacote instalado, use \`package update\`, incremente a versão e recarregue a mesa.

## Não faça

- não use caminhos absolutos, \`..\` ou arquivos fora do pacote;
- não declare uma capability “por garantia”;
- não mude o \`id\` depois de publicar: isso cria outro pacote;
- não coloque código inline em HTML ou no manifest;
- não marque dependência opcional como obrigatória; degrade graciosamente quando possível.`
  },
  {
    slug: "sdk-capabilities-runtime", section: "SDK em profundidade", title: "Capabilities e runtime JavaScript",
    summary: "Registre scripts, use APIs autorizadas e trate o ciclo de vida corretamente.",
    body: `# Capabilities e runtime JavaScript

Capability é uma permissão técnica e auditável. O método continua sujeito às permissões do usuário: declarar \`actors.write\` não permite que um Player altere um ator que não controla.

## Registro completo

\`\`\`js
window.GravewrightSDK.register({
  id: "minha-condicao",
  setup(sdk, { package: manifest, context }) {
    console.log("configurando", manifest.id, context.campaignId);
  },
  ready(sdk, { context }) {
    sdk.ui.toast("Addon carregado nesta campanha");
  }
});
\`\`\`

\`setup\` roda quando o manifesto ativo é conhecido; use-o para registrar controllers, comandos e subscriptions. \`ready\` roda quando a mesa está pronta; use-o para ações que dependem do runtime completo. O \`sdk\` recebido já está filtrado para aquele pacote.

Para o exemplo, o manifest precisa de \`assets.scripts\` para carregar o arquivo e \`assets.ui\` para \`sdk.ui.toast\`. Sem a segunda, o runtime lança uma mensagem indicando pacote, método e capability ausente.

## Leitura e escrita não são a mesma permissão

\`actors.read\` libera \`sdk.actors.list/get\`; \`actors.write\` libera create/update/delete; \`actors.data.write\` libera patch validado de dados da ficha. A mesma divisão existe para items. Para rolar use \`dice.roll\`; para uma intent declarada em regras use \`rolls.intent\`.

\`\`\`js
const actors = await sdk.actors.list();
const hero = actors.find((actor) => actor.type === "character");
if (hero) {
  await sdk.dice.roll({ formula: "1d20+3", label: "Teste de " + hero.name });
}
\`\`\`

Esse código exige \`actors.read\` e \`dice.roll\`. O servidor filtra a lista pelo usuário atual e calcula a rolagem; não use \`Math.random\` para uma rolagem de jogo.

## Comunicação entre pacotes

Publique eventos versionados e assine nomes com namespace:

\`\`\`js
sdk.bus.publish("minha-condicao.aplicada", { version: 1, actorId, condition: "cego" });
const unsubscribe = sdk.bus.subscribe("outro-pacote.atualizado", (payload) => {
  if (payload?.version !== 1) return;
  console.log(payload);
});
\`\`\`

Declare \`bus.publish\` e/ou \`bus.subscribe\`. Guarde \`unsubscribe\` e chame-o ao desmontar. Não use eventos genéricos como \`updated\`; eles colidem e não têm proprietário.

## APIs proibidas

\`backend.execute\`, \`database.raw\`, \`filesystem.raw\`, \`network.raw\` e \`permissions.override\` são rejeitadas. Não contorne isso chamando \`fetch\` para rotas internas, acessando globals do renderer ou alterando o DOM do core. Essas superfícies não são API e podem quebrar ou vazar dados.`
  },
  {
    slug: "sdk-fichas-html", section: "SDK em profundidade", title: "Fichas HTML, bindings e controllers",
    summary: "Construa uma ficha editável, persistente e segura do início ao fim.",
    body: `# Fichas HTML, bindings e controllers

Uma ficha HTML tem quatro peças: schema dos dados, template, CSS e controller opcional. O tipo liga tudo no manifest.

## Tipo no manifest

\`\`\`json
{
  "id": "character",
  "label": "Personagem",
  "schema": "schemas/actors/character.schema.json",
  "sheet": {
    "mode": "html",
    "template": "sheets/character.html",
    "controller": "scripts/character-sheet.js",
    "style": "styles/character-sheet.css"
  }
}
\`\`\`

O manifest também precisa de \`sheets.html\`, \`sheets.controller\`, \`assets.scripts\` e \`assets.styles\`; JS e CSS precisam aparecer em \`entrypoints.game\`. \`sheet.style\` sozinho não injeta CSS, e \`sheet.controller\` sozinho não executa JS.

## Template que salva

\`\`\`html
<form class="meu-rpg-sheet">
  <input data-bind="actor.name" aria-label="Nome">
  <label>Força <input type="number" data-bind="system.forca"></label>
  <p>Tipo: <span data-text="actor.type"></span></p>
  <button type="button" data-roll="1d20 + @sheet.forca" data-roll-label="Teste de Força">Rolar</button>
  <button type="button" data-action="mostrar-resumo">Resumo</button>
</form>
\`\`\`

\`actor.*\` é identidade; em item use \`item.*\`; \`system.*\` é o dado validado pelo schema. \`data-bind\` lê e persiste; number vira número; outros inputs normalmente produzem string. \`data-text\` usa textContent seguro. \`data-rich-text\` exige \`sheets.richText\` e passa por sanitizer. \`data-roll\` exige \`dice.roll\`.

Não escreva \`system.sheet.forca\` nem índices/wildcards: essas raízes não fazem parte do contrato. Checkbox não possui coerção booleana especial; trate-o num controller se precisa de boolean real.

## Controller e limpeza

\`\`\`js
window.GravewrightSDK.register({
  id: "meu-rpg",
  setup(sdk) {
    sdk.sheets.registerController("character", {
      mount(ctx) {
        ctx.root.classList.toggle("is-readonly", !ctx.data.canEdit);
      },
      async onAction(action, ctx) {
        if (action.name !== "mostrar-resumo") return;
        sdk.ui.toast(ctx.actor.name + ": Força " + ctx.data.system.forca);
      },
      unmount(ctx) {
        // remova timers, observers e listeners externos aqui
      }
    });
  }
});
\`\`\`

Pesquise sempre dentro de \`ctx.root\`; várias fichas podem estar abertas. \`canEdit\` serve para UX, não segurança, o servidor ainda decide. Não substitua \`root.innerHTML\` no update, pois destruirá bindings. Não use \`onclick\`, \`<script>\` no template ou seletores CSS globais.

## Diagnóstico

HTML sem estilo: CSS não está em entrypoints. Botão morto: script não carregou, IDs não coincidem ou capability falta. Campo volta ao valor antigo: schema rejeitou ou usuário não pode editar. Veja Console e Network; assets devem responder 200 em \`/sdk/packages/<id>/asset/...\`.`
  },
  {
    slug: "sdk-storage-settings", section: "SDK em profundidade", title: "Storage SQLite e settings",
    summary: "Persista dados próprios sem banco bruto e escolha o escopo correto.",
    body: `# Storage SQLite e settings

Use **settings** para configuração declarada e pequena. Use **storage.sqlite** para tabelas próprias, consultas e estado estruturado. Não use storage para duplicar atores, itens ou dados que já pertencem ao core.

## Storage gerenciado

No manifest, declare \`storage.sqlite\`, scopes, migrations, queries e limite. Migrations criam tabelas; \`queries.json\` contém operações nomeadas. O pacote nunca recebe caminho do banco nem SQL arbitrário.

\`\`\`json
{
  "queries": {
    "getState": { "type": "read", "params": { "key": "string" }, "sql": "SELECT value_json FROM addon_state WHERE key=:key LIMIT 1" },
    "saveState": { "type": "write", "params": { "key": "string", "value_json": "json-string" }, "sql": "INSERT INTO addon_state(key,value_json) VALUES(:key,:value_json) ON CONFLICT(key) DO UPDATE SET value_json=:value_json" }
  }
}
\`\`\`

\`\`\`js
await sdk.storage.sqlite.execute("campaign", "saveState", {
  key: "painel", value_json: JSON.stringify({ collapsed: true })
});
const rows = await sdk.storage.sqlite.query("campaign", "getState", { key: "painel" });
const state = rows[0] ? JSON.parse(rows[0].value_json) : {};
\`\`\`

Parâmetros ausentes, extras ou de tipo errado são rejeitados. Um named query contém um statement; ATTACH, PRAGMA, VACUUM e múltiplos statements são proibidos. Nunca monte SQL com concatenação: declare parâmetros.

## Settings por escopo

\`client\` fica naquele navegador; \`user\` acompanha o usuário e é global entre campanhas; \`campaign\` é compartilhado pela mesa; \`package\` é configuração geral. A precedência efetiva é default → campaign → user.

\`\`\`json
"settings": [{
  "key": "dificuldade", "type": "enum", "scope": "campaign",
  "default": "normal", "options": ["facil", "normal", "dificil"],
  "label": "Dificuldade", "description": "Altera os modificadores desta mesa."
}]
\`\`\`

\`\`\`js
const value = sdk.settings.get("dificuldade");
const off = sdk.settings.onChange("dificuldade", ({ value }) => atualizarUI(value));
await sdk.settings.set("dificuldade", "dificil");
\`\`\`

Declare \`settings\`. Não renomeie keys publicadas sem migração, não salve segredo em client setting e não use user scope para uma regra que precisa ser igual para todos. Valores são coeridos estritamente; enum fora de options e número inválido geram \`sdk.settings.invalid_value\`.`
  },
  {
    slug: "sdk-tutorial-addon", section: "SDK em profundidade", title: "Tutorial: addon funcional do zero",
    summary: "Crie, instale, teste e depure um addon real sem modificar o core.",
    body: `# Tutorial: addon funcional do zero

Vamos criar um addon que registra o comando namespaced \`saudacao-mesa.mostrar\`, lê uma setting de campanha e mostra um toast. O resultado será carregado somente nas campanhas em que o pacote estiver ativo.

## 1. Gerar a estrutura

Na raiz do Gravewright:

\`\`\`powershell
.\\grave.bat addon new saudacao-mesa --name "Saudação da Mesa" --js --settings
\`\`\`

Confirme a pasta \`data/packages/addons/saudacao-mesa\`. Não mova o pacote para \`static/\` nem para \`app/\`.

## 2. Manifesto

Use estas partes essenciais:

\`\`\`json
{
  "schemaVersion": 1,
  "sdkVersion": "1",
  "kind": "addon",
  "id": "saudacao-mesa",
  "name": "Saudação da Mesa",
  "version": "0.1.0",
  "compatibility": { "minimum": "1", "verified": "1", "maximum": "1.x" },
  "capabilities": ["assets.scripts", "assets.ui", "commands.register", "settings"],
  "activation": { "scope": "campaign", "mode": "multiple" },
  "entrypoints": { "game": { "scripts": ["scripts/main.js"] } },
  "settings": [{
    "key": "mensagem", "type": "string", "scope": "campaign",
    "default": "Bem-vindos à aventura!", "label": "Mensagem de saudação",
    "description": "Texto mostrado pelo comando /saudacao."
  }],
  "dependencies": [], "conflicts": [], "provides": {}
}
\`\`\`

Cada método usado tem uma capability: carregar JS → \`assets.scripts\`; registrar comando → \`commands.register\`; ler configuração → \`settings\`; toast → \`assets.ui\`.

## 3. Script

Crie \`scripts/main.js\`:

\`\`\`js
window.GravewrightSDK.register({
  id: "saudacao-mesa",
  setup(sdk) {
    sdk.commands.register("saudacao-mesa.mostrar", () => {
      const mensagem = sdk.settings.get("mensagem");
      sdk.ui.toast(mensagem || "Bem-vindos!");
    });
  }
});
\`\`\`

O ID precisa ser idêntico ao manifest. O comando é registrado em \`setup\`, pois isso é configuração do runtime. O nome recebe o namespace do pacote para não colidir. A mensagem é lida dentro do handler, assim mudanças posteriores na setting são respeitadas. \`sdk.commands.register\` registra um comando de cliente; ele não cria automaticamente um slash command do chat.

## 4. Validar e carregar

\`\`\`powershell
.\\grave.bat package validate data/packages/addons/saudacao-mesa --json
.\\grave.bat package install saudacao-mesa --yes --enable
.\\grave.bat campaign package activate ID_DA_CAMPANHA saudacao-mesa
.\\grave.bat package doctor saudacao-mesa
\`\`\`

Abra ou recarregue a campanha e confirme no Console que não houve recusa de registro. Dispare \`saudacao-mesa.mostrar\` por uma integração de comandos do host/pacote consumidor; o toast deve mostrar o default. Se você quer especificamente \`/saudacao\` no chat, precisa implementar a integração documentada do chat: registrar um comando de cliente não altera o parser do chat.

## 5. Alterar durante o desenvolvimento

Depois de editar, mude \`version\` para \`0.1.1\`, execute \`.\\grave.bat package update saudacao-mesa\` e recarregue completamente a página. Não reinstale por cima, não edite o snapshot no banco e não copie manualmente o JS para static.

## 6. Quando falhar

- pacote não aparece: valide kind, pasta e instalação;
- aparece, mas não carrega: confirme enabled global e active na campanha;
- register recusado: compare os dois IDs;
- comando não existe: confira Network para o JS e \`commands.register\`;
- capability error: declare exatamente a capability citada e atualize o pacote;
- código antigo: incremente version, update e recarregue sem cache.`
  },
  {
    slug: "ruleset-pdf", section: "Criadores", title: "Gravewright PDF System",
    summary: "Entenda o ruleset PDF incluído no core e como adaptá-lo.",
    body: `# Gravewright PDF System

O **Gravewright PDF System** faz parte do core e oferece uma base para jogos cuja ficha oficial é um PDF preenchível.

## O que ele fornece

- ator do tipo personagem;
- visualizador PDF;
- leitura e gravação de campos;
- mapeamentos para dados da ficha e token;
- integração com combate;
- suporte a anotações;
- interface em inglês e português.

## Usar em uma campanha

1. em **Sistemas de regras**, instale e ative **Gravewright PDF System**;
2. atribua-o à campanha pelo seletor **Atribuir à campanha**;
3. abra a mesa e crie um ator do tipo oferecido pelo ruleset;
4. abra a ficha e envie um PDF AcroForm preenchível;
5. edite campos, feche e reabra para confirmar persistência;
6. crie um token e confira os campos mapeados no tabuleiro e combate.

## Adaptar para um jogo

O pacote versionado fica em \`data/packages/rulesets/gravewright-pdf-system\`. Estude \`manifest.json\`, schemas/layouts declarados, \`pdf-fields.gw.json\`, \`token.gw.json\`, scripts e regras de combate referenciados pelo manifest. Para um jogo específico, crie outro ID de ruleset; não personalize o pacote do core, pois uma atualização substituirá suas mudanças.

## Assets do core e arquivos do usuário

O PDF A4 vazio, scripts e runtime pdf.js fazem parte do core e devem entrar no Git. PDFs enviados por usuários vão para o armazenamento da campanha/\`GravewrightData\`, não para a pasta do ruleset. Nunca adicione fichas comerciais nem dados de campanha ao repositório.

## Validar

\`\`\`powershell
.\\grave.bat package validate data/packages/rulesets/gravewright-pdf-system
\`\`\`

O resultado esperado é um pacote aprovado, compatível e sem warnings.`
  },
  ...releaseGuides["pt-br"],
];
