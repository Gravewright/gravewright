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

Como mestre da campanha, abra **Nova cena**. Escolha o fluxo conforme sua origem:

| Origem e objetivo | Ação | Resultado |
| --- | --- | --- |
| Uma imagem para usar diretamente como cena | **Enviar mapa** | Cena nativa com grade e visibilidade configuradas |
| Um mapa para construir ou continuar editando como projeto | **Map Builder** | Projeto editável; gerar a cena é uma ação separada |
| Uma imagem pronta para receber paredes, objetos ou comportamentos | **Map Builder → Biblioteca → Importar → Importar mapa pronto** | Fundo do projeto com elementos editáveis sobre ele |
| Um arquivo `.uvtt`, `.dd2vtt` ou `.df2vtt` | **Importar Universal VTT** | Nova cena nativa exclusiva do mestre, com paredes, portas e luzes suportadas |

Importar uma imagem não detecta paredes nem reconstrói suas camadas originais.
A importação Universal VTT não cria um projeto do Builder. O
[guia do importador/exportador](universal-vtt.md) explica os campos aceitos e avisos.

Para criar o primeiro projeto no Builder:

1. Escolha **Nova cena → Map Builder** e nomeie o projeto no cabeçalho.
   Entrar no Builder preserva a cena atual dos jogadores.
2. Use **Painéis → Configurações** para dimensões e tamanho da célula. O cabeçalho
   escolhe **Tiles** ou **Pintura**; **Painéis → Ferramentas** reúne as opções do pincel.
3. Importe suas imagens em **Biblioteca → Importar** ou escolha um fundo de mapa
   pronto. Ajuste as dimensões da grade para corresponder à imagem.
4. Pinte pisos e adicione paredes, portas, objetos, luzes ou efeitos. **Painéis → Camadas**
   controla camada ativa, visibilidade, bloqueios e conteúdo. Selecione um elemento
   e use **Painéis → Seleção** para editar suas propriedades.
5. Aguarde o cabeçalho indicar que o projeto foi salvo. As edições salvam
   automaticamente; o botão de estado e **Ctrl+S** sincronizam imediatamente.
   Reabra o trabalho salvo por **Painéis → Projetos**.
6. Use **Prévia** para conferir o mapa. Use **Testar comportamento** para um grafo
   de Objeto Inteligente disponível; o ensaio apresenta previsões sem confirmar
   efeitos na partida. Veja os objetos suportados no [guia do Map Builder](map-builder.md).
7. Escolha **Gerar cena** para criar uma cena nativa privada. Depois do vínculo,
   a ação do cabeçalho passa a **Atualizar cena**, aplicando novas edições à mesma
   cena. Um conflito de revisão interrompe a atualização para recuperação explícita.
8. Em **Cenas**, use **Ativar para jogadores** quando quiser compartilhar a cena.

Essas ações têm efeitos diferentes:

| Ação | O que altera |
| --- | --- |
| Salvamento automático / **Ctrl+S** | O projeto editável |
| **Gerar cena** / **Atualizar cena** | Imagem e recursos gerados da cena nativa |
| **Ativar para jogadores** | Visibilidade da cena e transmissão aos jogadores |

Se o salvamento falhar, mantenha a aba aberta e use os controles de recuperação.
**Recarregar projeto salvo** adota a versão do servidor; **Salvar uma cópia**
preserva o documento local com uma nova identidade de projeto. O rascunho do
navegador serve à recuperação, não substitui um backup. O
[guia do Map Builder](map-builder.md) cobre modos de desenho, remoção de assets,
camadas, Objetos Inteligentes, atalhos, limites e solução de problemas.

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

- Os catálogos do host incluem inglês, português do Brasil e espanhol. Inglês é o padrão quando não há preferência salva. Mudar o idioma da interface não traduz nomes, textos ou assets criados pelo usuário; sistemas instalados fornecem suas próprias traduções.
- O sistema PDF nativo não fornece tipos de itens; o backend genérico de itens não representa um editor/catálogo nativo completo.
- O carregador de extensões executa JavaScript na página principal. Instale código confiável; assinaturas não fornecem isolamento.
- O marketplace online exige catálogo e chaves confiáveis. Hosts gerenciados instalam atualizações pela Administração mediante solicitação do proprietário. Apps Django da biblioteca de módulos são ativados para todo o servidor e exigem reinício automático; módulos de navegador continuam vinculados às mesas.

Para desenvolvimento ou integrações, continue nos guias de [API](api.md) e [módulos](modules.md).
