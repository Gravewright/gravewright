# Arquitetura do frontend

[Índice da documentação](../README.pt-BR.md) · [English](../en/frontend.md) · [Referência da API](api.md)

A aplicação renderiza HTML Jinja2 no servidor, usa Datastar para sinais reativos e atualizações de fragmentos e executa controladores JavaScript nos espaços interativos. O tabuleiro usa PixiJS e possui pipeline próprio de fontes/build. Não existe um build único de SPA para toda a aplicação.

## Acompanhe a página pelo template

[`base.html`](../../gravewright/web/jinja2/gravewright_web/base.html) carrega CSS compartilhado, Datastar distribuído localmente e `gravewright_modules/frontend-api.js`, que cria `window.gravewright`. O ambiente `/inside` e a mesa de jogo estendem essa estrutura. [`table/page.html`](../../gravewright/table/jinja2/gravewright_table/page.html) compõe templates e carrega controladores de mesa, mapa, documentos, atores, dados e módulos.

Áreas úteis para começar:

| Local | Finalidade |
| --- | --- |
| `gravewright/web/jinja2/` | Estrutura compartilhada, páginas Inside e HTML reutilizável |
| `gravewright/accounts/jinja2/` | Templates de autenticação e configuração inicial da conta |
| `gravewright/web/static/gravewright_web/css/` | Variáveis visuais, estilos base e componentes |
| `gravewright/web/static/gravewright_web/inside/` | Controladores/estilos de contas, campanhas e administração |
| `gravewright/web/static/gravewright_web/windows.js` | Janelas móveis e redimensionáveis |
| `gravewright/table/static/gravewright_table/realtime.js` | Socket, assinaturas, fragmentos autenticados e eventos |
| `gravewright/modules/static/gravewright_modules/` | API pública de navegador, runtime de módulos, transporte e ciclo de vida |
| `gravewright/maps/frontend/` | Fontes editáveis de tabuleiro, paredes, tokens, iluminação, seleção e ferramentas |
| `gravewright/maps/static/gravewright_maps/workspace.js` | Integração do espaço de mapas |
| `gravewright/pdf_system/frontend/` | Fontes editáveis de mapeamento/controlador PDF |
| `jinja2/`, `static/` e `messages.json` de cada app | Interface, estilos e textos do domínio |

IDs e atributos `data-*` dos templates conectam controladores nativos e superfícies de extensão. Alterá-los pode afetar o controlador, sinais Datastar e montagem de módulos. Confira os três ao renomear seletores ou substituir painéis inteiros.

`modules/static/gravewright_modules/domain-api.js` expõe o contrato gerado às
páginas e aos módulos com montagem autorizada. `file-api.js` mantém bytes em
requisições multipart e retorna blobs autenticados; `global-api.js` reúne os
adaptadores de conta, campanha, administração e pacotes no ciclo de vida da página.
Cancelamento e permissões nativas são preservados. A [API pública ampliada](api.md)
documenta MapBuilder, blueprints, permissões, biblioteca e operações dos sistemas.

### Campos manuais no PDF

Veja o fluxo completo de jogadores e mestres no [guia do PDF System](pdf-system.md).
Esta seção identifica a implementação e seus limites de validação.

Na ficha do Gravewright PDF System, o mestre pode abrir um PDF e escolher
**Mapear campos**. Selecione texto, número, checkbox ou texto de várias linhas e
arraste um retângulo sobre a área da página. **Adicionar campo** cria um retângulo
pelo teclado. Selecione um retângulo para renomeá-lo, alterar seus limites em
porcentagens, arrastá-lo ou redimensionar seu canto inferior direito. As setas
movem a seleção um pixel de exibição (Shift: dez); Delete remove o campo e Esc
cancela um gesto. **Concluir mapeamento** retorna ao preenchimento. As alterações
são salvas automaticamente.

O mapeamento pertence ao personagem ou à cópia independente do token, à origem
do PDF e à página. Os campos acompanham o zoom e a exibição de páginas duplas e
convivem com os formulários nativos do PDF. Jogadores autorizados podem preencher
os campos; somente o mestre pode alterar suas definições. A sobreposição mantém
o arquivo PDF original intacto, inclusive ao baixá-lo. Excluir um retângulo
preserva seu valor armazenado. Campos de número e texto de uma linha também
podem ser escolhidos para as barras do token.

`pdf_system/frontend/manual-fields.js` contém identidades estáveis e geometria
normalizada da página exibida; `frontend/controller.js` combina as definições
manuais com os campos nativos. `static/gravewright_pdf_system/manual-editor.js`
cuida dos gestos, seleção e descarte. `pdf_system/manual_fields.py` valida até
256 definições entre as origens, limites, nomes, tipos e valores e restringe a
edição do mapeamento ao mestre pelo serviço normal de salvamento da ficha.
Mapeamentos omitidos são preservados para clientes anteriores. O controlador
gerado segue o pipeline existente de build dos assets de mapas.

O mestre pode dar dois cliques em um campo nativo ou mapeado manualmente, ou
focá-lo e pressionar F2, para abrir **Ações do campo** na modal existente da
aplicação. Escolha um valor do token, informe a fórmula e o nome da rolagem ou
use um dos seis modelos: d20, maior ou menor de dois d20, 2d6, d6 explosivo e
4dF. `@value` referencia o valor numérico atual do campo; um valor vazio vale
zero e caixas de seleção usam zero ou um. Fórmulas sem `@value` também funcionam
em campos de texto. Limpe a fórmula para remover a ação de rolagem. Vincular ou
desvincular uma barra do token preserva o valor atual do campo. Salvar valida o
candidato completo antes de atualizar a ficha exibida; Cancelar e Esc descartam
o rascunho.

As ações salvas aparecem como botões acima do PDF para editores autorizados.
Jogadores também podem dar dois cliques em um campo configurado; Alt+Enter
rola o campo focado. Para o mestre, o duplo clique continua abrindo a configuração,
onde **Rolar ação salva** executa a fórmula salva sem aplicar o rascunho. As
rolagens usam a [notação de dados](../../gravewright/dice/grammar/notation/GRAMMAR.pt-BR.md)
nativa, publicam no chat no contexto da cena atual e mantêm os recibos e as
tentativas de reconexão normais. Configurar uma ação não consome aleatoriedade.

`pdf.fieldActions` é opcional e contém até 256 definições de rolagem vinculadas à
origem e ao campo, com fórmula de 512 caracteres e nome de 48 caracteres. O
servidor compila as fórmulas pelo parser e compilador de dados, preserva ações
omitidas e rejeita alterações de quem não é mestre. `frontend/field-actions.js`
monta candidatos isolados para salvamento, preserva valores canônicos das barras
e expande a referência numérica limitada `@value`.
`static/gravewright_pdf_system/field-actions-editor.js` cuida do rascunho e do
descarte da modal.

**Campo de referência** insere `@{chave-do-campo}` em uma fórmula de rolagem ou
cálculo. O seletor mostra nomes legíveis; chaves manuais permanecem estáveis ao
renomear campos, e referências nativas mantêm o nome exato do formulário PDF.
O seletor escapa chaves e barras invertidas nesses nomes. Os valores das
referências são numéricos e seguem o limite existente de ±1.000.000.
**Fórmula do valor calculado** aceita aritmética determinística, comparações e
funções numéricas nativas com referências a outros campos. Limpe-a para voltar
à edição normal. Campos calculados são somente leitura e atualizam na ordem de
dependência. O servidor recalcula resultados a cada salvamento, rejeita ciclos,
inclusive por aliases das barras, e mantém o resultado canônico anterior quando
uma entrada fica temporariamente não numérica ou o cálculo falha.

`pdf.fieldBindings` registra endereços originais validados para as referências;
as substituições por barras usam o mapeamento atual do token. Somente o mestre
altera os vínculos ou `pdf.calculatedFields`. `formulas.py` e
`calculated_fields.py` validam e calculam no servidor; `frontend/formulas.js`
espelha o subconjunto determinístico para resposta imediata. Valores e vínculos
arquivados continuam disponíveis após remover um retângulo; o diagnóstico
identifica referências cujo campo visível desapareceu.

Durante o mapeamento, Shift/Ctrl+clique ou arraste um retângulo de seleção para
selecionar vários campos na página. A barra de ferramentas permite copiar,
colar, duplicar, usar seis alinhamentos, distribuir horizontal/verticalmente e
ativar encaixe em grade de cinco pontos. Ctrl+C/V/D e Ctrl+Z/Shift+Z oferecem as
mesmas operações. A barra fica em **Ferramentas de disposição**, inicialmente
recolhida em fichas estreitas e expansível por teclado ou toque.
Cada gesto é uma etapa do histórico, limitado a 50 etapas no
PDF atual. Desfazer restaura definições e mantém os valores atuais do personagem;
trocar de documento limpa o histórico. Cópias recebem novos UUIDs e remapeiam
fórmulas internas da seleção. `frontend/layout-editor.js` contém a geometria;
`layout-history.js` contém os estados das definições e identidades das cópias.

**Biblioteca de mapeamentos** abre os modelos da campanha para mestres. Salve ou
substitua o mapeamento atual, aplique um modelo à ficha aberta ou a atores
selecionados e importe ou exporte JSON versionado. Modelos contêm retângulos,
ações, cálculos, vínculos e geometria opcional do documento, sem PDFs, valores,
nomes de personagens ou mídia. Valores existentes são mantidos pela identidade
do campo e pelas barras canônicas; modelos não mesclam campos distintos pelo
nome visível. Snapshots independentes de tokens mantêm o próprio mapeamento,
exceto ao aplicar explicitamente um modelo àquela ficha aberta. A aplicação em
lote valida as revisões de todos os atores antes de gravar qualquer alteração.
IDs manuais já usados por outro PDF da mesma ficha geram erro de validação,
preservando os campos daquele PDF.

`MappingTemplate` e sua migração inicial pertencem ao `pdf_system`. As rotas
`/api/containers/<id>/pdf-mappings` verificam mestre, campanha, revisões e recibos
de operações. Os limites são 128 modelos por campanha, 100 atores por lote e
1 MB por importação JSON, além dos limites da ficha. Arquivos de campanha
incluem os modelos e validam seus pacotes portáteis na restauração. Alterar um
modelo exige nova aplicação para atualizar o personagem.

**PDF preenchido** baixa uma cópia separada e achatada de todas as páginas com
os valores atuais, incluindo campos nativos repetidos entre páginas. Usa o
PDF.js distribuído para renderizar a 144 dpi e grava
imagens JPEG em um contêiner PDF mínimo, preservando texto Unicode conforme
exibido pelo navegador. O original continua disponível separadamente. A cópia
não contém widgets editáveis nem conteúdo executável do PDF. A exportação
rejeita texto que não cabe no retângulo, complexidade excessiva ou resultado
acima de 100 MB e baixa somente após concluir todas as páginas. Aceita até
100 páginas, 16 milhões de pixels por página e 128 milhões por operação.
Fechar ou trocar o documento cancela o trabalho. O contêiner segue a estrutura
de imagens XObject e endereços em bytes do [ISO 32000-1](https://opensource.adobe.com/dc-acrobat-sdk-docs/pdfstandards/PDF32000_2008.pdf).

O botão **Diagnóstico do mapeamento PDF** verifica campos ou referências
ausentes, erros de cálculo, páginas inexistentes e diferenças de tamanho,
rotação ou identificação do documento. `pdf.sourceMetadata` mantém o descritor
esperado ao aplicar um modelo; abrir o PDF não o substitui silenciosamente.
O diagnóstico exibe rótulos autorais como texto e permite navegar até campos
ainda presentes. Exportar e diagnosticar não modificam o PDF original.

`node --test gravewright/pdf_system/frontend/*.test.js` cobre o modelo dos
campos; `manage.py test gravewright.pdf_system.test_manual_fields` cobre
persistência e autorização. O cenário isolado
`tests/e2e/pdf_manual_fields.py` exercita desenho, preenchimento, navegação,
campos nativos, cópias de tokens, papéis e Translator em inglês, português e
espanhol.
`manage.py test gravewright.pdf_system.test_field_actions` e
`tests/e2e/pdf_field_actions.py` cobrem configuração de rolagens, preservação de
valores das barras, entrega ao chat, rascunhos cancelados ou inválidos, permissões
e modais responsivas e traduzidas.
`manage.py test gravewright.pdf_system` também cobre modelos, cálculos,
metadados e restauração de arquivos de campanha. `tests/e2e/pdf_workbench.py`
exercita o fluxo combinado e abre/renderiza o PDF gerado pelo próprio PDF.js.

### Área do Map Builder

`GET /game/<campaign_id>/map-builder` renderiza
[`maps/builder.html`](../../gravewright/maps/jinja2/gravewright_maps/builder.html)
por `maps/builder.py`. A rota confere o vínculo atual de mestre e valida a
consulta opcional `folder` contra a campanha. O seletor de nova cena usa
navegação normal na mesma aba; o builder usa a estrutura base com controladores
próprios em `static/gravewright_maps/builder/`, sem montar o runtime da mesa,
assinaturas de cena ou a área de jogo da mesa. Os efeitos nativos usam a prévia
dedicada descrita abaixo.

O diretório de cenas da mesa lê o campo opcional `builderProjectId` da projeção
de mestre em `maps.services.state()`. Uma consulta de IDs limitada à campanha
resolve o vínculo atual do projeto com a cena; projeções de outros papéis não
incluem esse campo. A cena vinculada mantém a linha compacta e o mesmo ícone de
mapa, colorido com `--danger`, e acrescenta **Editar com MapBuilder** junto da
edição normal no menu de contexto. Shift+F10 ou a tecla de menu de contexto abre
o menu da cena focada. O menu usa o documento do diretório, inclusive em janelas
destacadas; a ação abre o editor na aba principal do jogo. O endpoint do projeto
confere novamente o papel de mestre e a campanha
ao carregar.

A entrada é uma operação de leitura. O `workspace.js` do Estúdio compõe os
controladores do editor, a navegação e os gestos de desenho. Seus módulos
vizinhos, servidos diretamente, possuem estas responsabilidades:

| Módulo em `static/gravewright_maps/builder/` | Responsabilidade |
| --- | --- |
| `project-persistence.js` | Recuperação/armazenamento de rascunhos, HTTP/CSRF, identidade dos recibos e fila de salvamento |
| `workspace-library.js` | Catálogo de assets da campanha, escolha de pincéis e controles de material |
| `workspace-import.js` | Modais de importação/edição de assets e ciclo de vida dos listeners |
| `inspector-controller.js` | Campos compartilhados da seleção, modais por seção e configuração de regiões/tochas |
| `object-menu.js` | Menu de contexto dos objetos, navegação por teclado e submenu de modelos |
| `interactive-presets.js` | Blueprints genéricos configuráveis e modal do catálogo de objetos |
| `shader-control.js` | Propriedades tipadas de shaders para edição, simulação e registros de Blueprints |
| `layer-controller.js` | Controles, conteúdo e seleção de camadas e listeners de arraste |
| `productivity.js`, `productivity-model.js` | Agrupamento, alinhamento atômico, modelos da campanha, áreas e pincel de objetos |
| `player-test.js`, `player-test-model.js` | Ensaio separado como jogador, passagem por áreas e solicitações de teste com rollback |
| `canvas-renderer.js` | Arte SVG, marcações de seleção e caches descartáveis de terreno/parede |

Os controladores recebem estado e callbacks explícitos, sem importar o workspace
nem compartilhar globais. Os testes de persistência importam sua factory pública,
sem extrair texto de funções do `workspace.js`. Um salvamento cujo dono foi
descartado não sobrescreve um rascunho recuperado ao receber confirmação tardia.
`model.js` possui a geometria em células e o histórico de desfazer, e
`viewport.js` possui a câmera SVG independente.
Listeners, captura de ponteiro, requisições e observação de tamanho terminam em
`pagehide`; a restauração pelo histórico remonta o editor. `builder_services.py`
possui as revisões de projeto por campanha, recibos de repetição, validação e
geração e atualização de cenas. Consulte [Map Builder](map-builder.md) para o formato do
projeto, a geometria nativa e os limites da imagem.

`newDocument()` cria uma camada genérica vazia com um UUID novo; o controlador
traduz seu nome inicial **Camada 1**. Não cria camadas por tipo de objeto.
A normalização da versão 3 preserva as camadas originais, inclusive uma lista
vazia após remover a última camada vazia. O servidor aceita essa lista apenas
sem objetos, e a geração do mapa vazio renderiza somente o fundo. Projetos de
versões 1/2 mantêm a conversão existente para a camada Base.

O seletor de modo no cabeçalho respeita `editingMode: "tiles" | "paint"`
opcional; a ausência usa Tiles sem mudar o projeto. Tiles e Pintura de terreno
compartilham camadas, objetos nativos, câmera e histórico. Cor/opacidade
existentes em `floor.paint` continuam renderizadas independentemente pelo SVG
e pelo raster, multiplicando cobertura da forma, transparência da textura e
opacidade. Escolher o novo pincel de terreno não reinterpreta esses estilos
anteriores nem converte a geometria existente. O chão mantém seus contratos de
camada e transformação.
SVG e Pillow usam antialiasing diferente em bordas coincidentes de contorno e
recorte; comparações de pixels mantêm o interior exato e isolam essa faixa da borda.

`floor-painter.js` controla gestos temporários de chão e aplica uma edição
completa por vez. `model.js` fornece a área percorrida pelo pincel, preenchimento
por família, captura de material e recorte atômico do chão. Fragmentos da prévia
mantêm UUIDs estáveis; gestos sem alteração não ocupam etapas de desfazer.
`floor-geometry.js` fornece contornos contínuos e recortes com o encaixe desligado,
seleção pela forma real e limites de complexidade do projeto e do raster.
O servidor valida o mesmo contrato opcional de forma do chão e gera a máscara
da união dos contornos menos os recortes, com antialiasing limitado.
`layer-model.js` conta o conteúdo das camadas e o move ou mescla preservando
identidades dos objetos e ordem de pintura.
Duplicar uma camada reutiliza a duplicação atômica de objetos com deslocamento
exato de uma célula em cada eixo, novos IDs e referências internas de Objetos
Inteligentes remapeadas. Limites do mapa, sobreposição global de portas e limites
do projeto podem recusar a cópia inteira. O isolamento é um filtro do editor;
a visibilidade do projeto e a geração nativa mantêm sua semântica existente.
Os controles de desenho ficam na aba **Ferramentas** do painel auxiliar,
deixando o espaço do canvas disponível quando o painel está fechado.

Todos os tipos de elemento aceitam `name` autoral de até 120 caracteres. Nomes
opcionais continuam ausentes nos elementos antigos sem nome; regiões e shaders
mantêm nomes obrigatórios. O inspetor usa o rótulo Objeto vazio nos controladores
antigos sem nome. `element_names.py` valida tipo,
espaços, tamanho e NUL no servidor. Edições nativas, geração e atualização
vinculada preservam os rótulos sem trocar UUIDs ou alvos do Blueprint. Chão
estático continua na imagem rasterizada; superfícies dinâmicas levam o nome da
origem para a imagem nativa. O inspetor de Seleção possui um campo de nome por
elemento selecionado, e camadas, catálogos de comportamento e escolhas de
luz/porta priorizam os nomes definidos pelo autor.

A faixa persistente de ferramentas da biblioteca usa `data-builder-dock-tool`
nos controles adicionais; os seletores das ferramentas do painel continuam
distintos. Trocar de ferramenta aplica a propriedade em foco antes de devolver
o foco ao canvas. A faixa tem rolagem própria em telas estreitas e mantém seu
layout ao substituir os cards de imagens pelos de luzes/efeitos nativos.

O botão **Painéis** abre as seis abas vinculadas do painel em uma grade de três
colunas. Cada aba mantém sua posição de rolagem; o cabeçalho e as abas permanecem
visíveis acima do conteúdo rolável. Setas, Home e End navegam pelas abas, e fechar
o painel devolve o foco a quem o abriu. Os ajustes do pincel ativo vêm antes da
paleta compacta de ferramentas, com a ajuda detalhada em uma seção expansível.
Navegar ou rolar os painéis não altera o projeto salvo nem seu histórico.

A repintura Tiles compara o material de chão visível por cima antes de substituir
a cobertura. Uma célula igual ou um traço livre inteiramente igual preserva os
registros de origem, sem sortear novamente variações válidas da família nem
adicionar histórico. A cobertura considera a união de vários pisos e seus
recortes; outro material acima deles impede a correspondência. Gestos com
encaixe filtram cada célula igual individualmente. Gestos livres mistos
substituem toda sua área, preservando a geometria fora dela. A prova de cobertura
tem um orçamento limitado de trabalho geométrico e recusa a operação inteira
quando ele é excedido. A Pintura de terreno usa sua própria representação de
pincel radial em vez da composição uniforme anterior de `floor.paint`.

### Pintura de terreno no Map Builder

`terrain-painter.js` controla um gesto circular temporário, carimbos espaçados
por distância e acúmulo parado a cada 50 ms. Aplica uma entrada `floor.brush` por
gesto concluído e encerra o timer ao cancelar, concluir ou descartar. O workspace
possui a captura de ponteiro, tamanho compartilhado, controles de modo,
histórico e renderização; trocar de ferramenta ou modo cancela o traço ativo.
Tiles continua usando `floor-painter.js` e sua semântica de substituição e
gestos sem alteração.

`terrain-brush.js` e `maps/terrain_brush.py` calculam o mesmo kernel radial nos
centros absolutos dos pixels. A dureza define um centro uniforme com queda
linear até o raio; a transparência dos carimbos acumula com arredondamento
inteiro limitado na composição. A origem guarda pontos normalizados locais,
raios horizontal/vertical, dureza e operação paint/erase na caixa do chão.
A textura mantém a fase e a rotação existentes no espaço do mapa; o pincel
fornece a cobertura.

Uma entrada de borracha aplica destination-out somente aos pisos anteriores da
mesma camada. O SVG envolve a camada acumulada na máscara; o Pillow mantém uma
superfície RGBA separada para a camada. Pintura posterior fica fora do alcance
da borracha anterior. Mesclar uma camada superior com borrachas sobre outra
inferior com pisos é recusado, mantendo esse isolamento.
`terrain-render.js` guarda imagens temporárias de máscara
pela assinatura da origem e libera o cache na limpeza/descarte; elas não são
assets de imagem da campanha. Limites restringem carimbos por traço/projeto e o
trabalho real de pixels por carimbo antes da alocação do raster, recusando
operações grandes demais de forma atômica.

As referências oficiais [TerrainBrush do Dungeondraft](https://megasploot.github.io/DungeondraftModdingAPI/reference/TerrainBrush/)
e [Terrain](https://megasploot.github.io/DungeondraftModdingAPI/reference/Terrain/)
orientaram a separação entre tamanho/intensidade do pincel e superfície de
terreno. O Gravewright implementa e salva seu próprio contrato de pincel radial.

Shift e arrastar com o botão esquerdo redimensionam o pincel de chão usando a
distância horizontal na tela (40 pixels por célula). A guia ancorada acompanha
o encaixe Tiles ou o raio contínuo do terreno. Concluir atualiza apenas
preferências do editor; Escape restaura o tamanho anterior sem gravar origem
ou histórico.

`native-effects.js` adapta o builder aos mesmos catálogos de luz, partículas e
shaders da mesa. O bundle pequeno `builder-catalog.js` fornece predefinições sem
iniciar WebGL; `builder-native.js` é carregado quando há fontes visíveis. As
entradas editáveis são `frontend/native/builder-catalog.js` e
`frontend/native/builder-preview.js`. A última reutiliza `PixiBoardRenderer` e
`SceneLayers` numa camada transparente sincronizada com a câmera SVG e a
geometria das paredes. Camadas ocultas/vazias, página oculta e descarte liberam
recursos de renderização e animação. Os efeitos nativos ficam separados do raster
gerado.

`frontend/native/builder-editors.js` hospeda os mesmos widgets `LightEditor` e
`EffectEditor` usados no jogo sobre um rascunho separado do builder. Seu
adaptador `builder-editor-model.js` converte os nomes dos raios de luz e resolve
referências compactas de presets para editar GLSL sem expandir uma origem
inalterada. Os rodapés transacionais dos widgets ficam ativos somente nesse
host; o salvamento automático do jogo continua disponível em seu host normal.
Validação e prévia do rascunho nunca chamam comandos de cena. Salvar devolve um
candidato ao `workspace.js`, que verifica se o objeto permite edição e aplica
uma etapa ao histórico do projeto. Cancelar/fechar libera timers da prévia,
validação de shader e qualquer prompt interno, preservando projeto e cena ativa.

`static/gravewright_maps/wall-editor.js` e o template `wall_editor.html`
compartilham a janela de configuração com o controlador de paredes da mesa.
Seu host no builder grava os ajustes nativos opcionais de
aparência, canais, elevação e descoberta na parede/porta de origem. As janelas
de comportamento de Objetos Inteligentes de portas e alavancas continuam
separadas da configuração da barreira física.

`builder/torch-model.js` vincula uma decoração às luzes e efeitos nativos do
projeto. Mecanismo e chama são independentes; a prévia aplica o quarto de volta
e controla os componentes ativos sem reescrever coordenadas de autoria.
`model.js` expande a seleção composta uma vez nas transformações e cópias;
`object-removal.js` concilia vínculos e referências de luz dos Blueprints de
forma atômica. Botões de componente reutilizam `builder-editors.js` e conservam
a seleção da tocha. Na mesa, `lever-controls.js` atende alavancas e tochas;
`image-components.js` projeta os objetos vinculados nas prévias de imagem e
seleção sem recriar recursos da GPU. O domínio `torches.py` valida propriedade
na cena, aplica transformações e estado da chama e mantém as operações do
conjunto nas transações dos comandos de mapa.

Os nós V2 `all`/`any` são valores booleanos puros com entradas `a`–`d` e saída
`result`. Entradas conectadas são avaliadas em ordem fixa sem interrupção
antecipada; menos de duas retorna Falso. Valores compartilhados são memorizados
somente no evento atual. Python e JavaScript validam tipos booleanos, uma origem
por entrada e limites de ciclo/tamanho. O catálogo agrupa os nós em Lógica e o
cartão mostra a quantidade de conexões; simulação e registro do mestre mostram
os resultados avaliados.

`builder/region-model.js` cria retângulos nomeados em células e a predefinição
explícita de placa ligada à porta. Regiões participam da seleção, camadas,
cópias e histórico do projeto, mas não da imagem ou prévia do jogador.
`regions.py` deriva a ocupação privada dos comandos validados de token na mesma
transação; `zones.py` estabelece a ocupação sem eventos durante edição. A modal
nativa em `features/regions` mostra estado/quantidade ao mestre e edita a zona.

`blueprint-editor.js` edita um rascunho privado de porta, alavanca, tocha ou região por meio do helper
compartilhado `mountModal`; `blueprint-model.js` valida conexões e simula o evento
selecionado localmente. O editor usa DOM/SVG nativos, sem biblioteca de grafos:
os nós continuam elementos focáveis sobre um plano deslocado e escalado, e a
rolagem nativa causada pelo foco é incorporada a essa câmera. Seu histórico de
desfazer próprio cobre somente o rascunho aberto e termina com a modal. Salvar
aplica uma operação de desfazer ao projeto. Portas
geradas mantêm o `door_state` nativo, e imagens de alavanca mantêm `lever.state`;
`blueprint_runtime.py` executa efeitos dentro
da transação e do recibo do comando de mapa existente, que também registra uma
execução só para o mestre exibida por `automation-log.js`, a janela Automação da mesa. Luzes e sons usam seus
domínios e transporte em tempo real atuais. A projeção do público inclui somente
a aparência ativa, mantendo grafos e imagens inativas privados para o mestre.

`blueprint-templates.js` captura modelos reutilizáveis da campanha, substituindo
somente campos de recursos tipados por vínculos e expondo parâmetros escalares
permitidos. Aplicar uma cópia resolvida é uma operação no histórico do rascunho,
sem dependência futura do modelo. `scene-network.js` deriva relações dos mesmos
grafos de cada elemento, mostra até 40 cartões por página e abre o editor já
existente. `blueprint_network.py` salva regras nativas com revisões de objeto e
projeto e recibo vinculado ao conteúdo, traduzindo referências para a fonte do
Builder na mesma transação. A visão da rede não executa regras.

`builder_dynamic.py` promove pisos/paredes marcados explicitamente a planos de
imagem nativos com máscaras; mapas comuns continuam incorporados à imagem.
Grupos ordenados de pintura/borracha preservam o alfa do piso;
`surface-material.js` amostra materiais substitutos no referencial original da
textura e `surface-group.js` compõe os planos quando mudam, fora do loop de
quadros. As imagens geradas pertencem à cena e ficam fora da biblioteca.
Visibilidade e material mudam o estado durante o jogo sem criar arquivos.
Limites controlam superfícies promovidas, pixels, bytes e trabalho de cache.
A preparação serializa o trabalho dos rasters dinâmicos/base e libera cada
buffer PNG após gravar o artefato da operação, antes de abrir a transação de escrita.
Ações repetidas de material de parede compartilham um cache limitado por comando.
A importação valida os novos metadados, o orçamento agregado de buffers e a
propriedade da cena sobre arte/máscaras geradas. A entrega de arquivos revalida
essa propriedade para quem não é mestre; o renderer calcula o orçamento de todos
os grupos antes de alocar buffers.

`blueprint_world.py` valida públicos de apresentação e transporte na mesma cena
dentro da transação do comando existente. Eventos `automation.presentation`
filtrados por destinatário são enviados após o commit e revalidados na entrega.
`automation-presentation.js` exibe texto autorado com `textContent`, abre a janela
nativa de diário e elimina repetições de IDs recentes. O foco de câmera só atua
na cena visualizada e exige uma preferência por perfil/dispositivo, desativada
inicialmente. O teleporte usa o token original do gatilho autenticado, valida
espaço livre para toda sua área na região de destino e processa a presença de
chegada depois de persistir os objetos da ação atual. Uma trava de chegada
persistente impede voltas até o token sair da região; navegação de cenas e
composição do grupo permanecem as mesmas.

Imagens enviadas como **Objeto** podem virar Smart Objects diretamente: escolha
**Editar nós** no menu de contexto ou **Objeto inteligente** nas propriedades de
Comportamento. Dois cliques com o botão esquerdo também abrem o editor, tanto em
Seleção quanto em Objetos, sem colocar outro objeto. Arrastar continua usando a
ferramenta ativa.
A primeira abertura cria um Blueprint vazio que herda a imagem, preservando a
identidade, a imagem, a camada e a geometria do objeto. Estados e nós podem ser
configurados livremente, com os fluxos existentes de salvamento automático e
geração da cena. Reabrir um Smart Object mantém seu comportamento autoral.
Os modelos prontos continuam opcionais.

O **Catálogo de objetos interativos** na seleção do Builder, **Modelos prontos**
no menu de contexto do objeto e o **Catálogo de objetos** do editor de nós
compartilham 14 Blueprints editáveis de mecanismos genéricos. Os modelos cobrem
interruptores, baús, passagens secretas, livros, altares, armadilhas de aviso,
sinos, placas de pressão, pedidos de dados, ativação/conclusão de missões,
placas de entrada, interruptores temporizados e botões de porta. A modal de
configuração oferece som/volume e imagem do estado ativo opcionais; opções
desmarcadas não geram nós de som nem substituição de imagem. As imagens de estado
vêm apenas de assets de Objeto e o estado inativo restaura a imagem original.
Aplicar um modelo preserva a identidade e a geometria; substituir um
comportamento autorado exige confirmação na modal da aplicação e pode ser
desfeito. A armadilha avisa na entrada enquanto armada, sem aplicar dano
específico de um sistema de RPG. As opções de Comportamento no inspetor abrem a
mesma configuração. As modais de propriedades reutilizam os controles do
inspetor e salvam pelas operações e pelo histórico existentes.

O nó `requestRoll` do Blueprint V2 armazena uma `expression` de dados validada
(até 512 caracteres), `label` (até 48), `visibility` (`public` ou `gm`) e
`audience`. O público pode ser quem interagiu, todos os jogadores, um jogador ou
usuários escolhidos. Um jogador usa o escopo compatível `users` com um UUID.
Os destinatários autorizados recebem uma modal nativa e escolhem **Rolar**;
o serviço normal de dados valida e publica o resultado no chat. O UUID do evento
identifica a mesma rolagem por usuário entre tentativas e abas, mantendo a cena
de origem. Streamers não recebem pedidos de rolagem. A ação continua
imediatamente: ela não cria ramificações com base no resultado.

**Abrir diário** usa o contrato existente `showHandout` para diários, missões e
quadros de missões, sem conceder acesso de leitura. `setQuestStatus` armazena o
`journalId` de uma missão e um dos estados `draft`, `available`, `active`,
`completed`, `failed` ou `archived`. O servidor valida campanha e tipo e aplica
a ação fixa autorada pelo mestre pelo serviço de diários, dentro da transação
do mapa; os jogadores não recebem permissão de edição do diário. Ensaios mostram
alterações de missão e pedidos de dados sem persistir diários nem abrir janelas
para jogadores. Modelos, referências adiadas e arquivos de exportação preservam
esses vínculos e os rótulos de rolagem autorados.

Blueprint V2 `elementGroup` é um conjunto puro tipado e ordenado: `name` (1–80
caracteres), `memberType` (`element`, `light`, `sound`) e de 1 a 32 UUIDs únicos
em `targetIds`. A saída `targets` se torna `elementset`, `lightset` ou `soundset`.
`lightReference.targetId` produz `light: light`; `soundReference.trackId` produz
`sound: sound`. O `reference` legado conserva o ID de saída `door: element` e
também alcança imagens nativas comuns, cujo estado é null. Paredes/chão
incorporados à imagem ficam fora do contrato. `acceptsDataType(port, type)` usa
`acceptedTypes` nas portas Alvo: ações de elemento aceitam elemento/conjunto,
ações de luz/som aceitam o recurso/conjunto correspondente, e transformações
aceitam elemento/luz ou seus conjuntos. Ler propriedade continua individual.
Um Alvo conectado substitui o vínculo de recurso legado ou o próprio elemento;
UUIDs ausentes ficam conectados e são ignorados/registrados, sem redirecionamento.
A ordem é explícita e cada ação expandida conta no limite de ações existente.

`move` guarda `dx`/`dy` finitos em células, limitados a ±1.000; `rotate` guarda
`degrees` relativo finito de até ±36.000. `blueprint_actions.py` usa validadores
nativos de imagem, porta, luz e região dentro da transação do comando. O giro
usa o centro de cada alvo, e retângulos de presença exigem múltiplos de 90 graus.
Componentes de tocha acompanham a imagem. Transformações autorizadas reconhecem
a geometria pertencente ao projeto sem mudar a fonte; atualizar a cena reaplica
transformações autoradas e mantém conflitos de outras edições manuais.
`setInteraction.enabled` e `setRegion.enabled` são booleanos estritos. O primeiro
controla requisições diretas e controles de ponteiro/teclado/chama de jogadores,
conservando a operação manual pelo mestre, sem bloquear automações autoradas.
A projeção pública nativa inclui `interactionEnabled`; omitir a configuração
autorada mantém o padrão habilitado. Interação durante o jogo sobrevive à
atualização quando seu padrão autorado não muda; uma alteração explícita
de autoria vence. A ativação de região é conservada enquanto ativação/camada
autoradas não mudam; mudanças de autoria vencem e recalculam a base de ocupação
silenciosamente. Cópias nativas e arquivos de campanha conservam a configuração;
o remapeamento toca referências/membros tipados, sem alterar textos escalares.
Excluir uma ação de recurso legada conecta somente seus fios de execução;
fios de dados nunca se tornam execução, e novas referências/grupos ausentes
permanecem inertes.

A importação usa `remap_omitted_bindings` para novas referências/grupos de som
e IDs de atores/tokens dos filtros quando seus registros são omitidos. Uma
tabela por modelo/UUID cria um UUID inerte novo para cada identidade ausente e
o reutiliza nos documentos do projeto, dados nativos e manifestos de geração.
Vínculos importados ficam inertes até escolher recursos substitutos; nomes, rótulos
de evento/grupo e textos escalares autorados são preservados, inclusive textos
que se parecem com UUIDs.

`eventContext.property` seleciona um `value` tipado de leitura. Propriedades de
texto são `event`, `sourceId`, `userId`, `userName`, `tokenId`, `actorId` e
`presence`; `count` é um inteiro de 0 a 1.000.000, `hasToken` é booleano e
`state`/`previous` transportam Estado. `blueprint_context.py` monta os dados
originais com usuários autenticados e regiões/tokens validados. Sinais e tarefas
persistentes os conservam. Evento/estado/anterior sempre vêm do avaliador para
o retrato do grafo atual; Delay conserva o retrato salvo, enquanto Temporizador
lê estado novo com a identidade original. Sem token/ator, IDs são vazios, a
contagem começa em zero e hasToken deriva da presença do token. Campos
arbitrários de dados/papel são recusados. A fixture opcional
`context.eventContext` da simulação é privada e não grava identidade no servidor
nem dispara efeitos.

Filtros de presença ficam em `region.filters` opcional na fonte e
`zone.region.filters` nativo: `tokenIds`/`actorIds` (até 64 UUIDs únicos por lista),
`dispositions` (`friendly`, `neutral`, `hostile`, `unknown`) e `visibility`
(`any`, `visible`, `hidden`). Listas usam OU e critérios usam E; listas vazias
não restringem. A visibilidade é a configuração de token oculto, independente
de controle ou visão. O modelo puro compartilhado
`static/gravewright_maps/region-filters.js` é reexportado pelos modelos nativo e
do Builder. `normalizeRegionFilters` completa padrões de edição sem mudar a
fonte; documentos antigos conservam a ausência de filtros. `regions.py` valida
propriedade das identidades e calcula ocupação/eventos pelos comandos de token
aceitos. Configurar ou habilitar/transformar uma região durante o jogo estabelece
uma base silenciosa, sem presença artificial. Desabilitar presença não cancela
sinais nomeados ou tarefas agendadas independentes. O editor nativo usa o
catálogo atual de tokens e uma requisição cancelável de atores do mestre,
descartando resultados posteriores ao fechamento. Filtros e identidades dos
ocupantes continuam privados.
Objetos podem usar uma área de ativação circular nas propriedades de
Comportamento do Builder. `decoration.presenceRadius` é o raio em células
(0,05–200), convertido em pixels no `presenceRadius` da imagem nativa. O círculo
acompanha o centro do objeto independentemente do tamanho e da rotação da arte.
O círculo e sua alça aparecem no editor quando o objeto está selecionado; o raio
é privado dos mestres e não é incorporado à imagem do mapa. Conecte
`presence:enter` ou `presence:exit` para executar efeitos nas travessias
confirmadas de tokens sem clicar. Sem raio, permanece a caixa orientada da arte;
alterar a área recalcula a ocupação silenciosamente.

Blueprint V2 também implementa `getVariable`, `setVariable`, `compareValue` e
`emitEvent`. Nós de variável guardam `scope` (`element`/`scene`), `name`,
`valueType` (`boolean`/`number`/`text`) e `default` ou `value` tipado; comparações
guardam `valueType`, `operator` e `expected`. `dataInputs`/`dataOutputs` derivam
o tipo da porta Value do nó. Mudar o tipo remove conexões incompatíveis em uma
etapa de desfazer. Chaves de grafo `signal:<name>` são eventos receptores nomeados;
emissores os enfileiram para o próprio elemento, um Alvo Elemento ou receptores
da mesma cena. Sinais não carregam dados personalizados. Os grafos continuam na
versão 2, sem declarações de variável nem memória de execução no nível superior.

`blueprint_variables.py` valida nomes, tipos, definições e memória privada:
64 entradas por escopo, nomes ASCII de até 64 caracteres começando com letra,
números finitos entre ±1.000.000, textos de até 256 caracteres e 16 grafos
receptores por blueprint. Elementos usam `SceneObject.data.automationVariables`;
cenas usam `Scene.settings.automationVariables`, ambos `{name: {type, value}}`.
Conflitos de tipo recusam o comando, sem converter valores salvos. Cada evento
lê seu retrato inicial; atribuições enfileiradas ficam visíveis ao próximo evento,
inclusive receptores de sinais. Falhas revertem memória e demais efeitos juntos.

`simulateGraph` aceita um sexto argumento opcional
`{variables: {element: {...}, scene: {...}}}`. Ele valida a memória privada de
prévia e retorna atribuições/emissões como ações sem gravá-la nem executar
receptores. Os controles Variáveis da simulação configuram somente essa prévia.
A resposta de automação exclusiva do mestre inclui `variables`; a visão Variáveis
envia `automation/reset-variable` pelo serviço de comandos existente com escopo,
nome, `elementId` quando aplicável e o `{type, value}` exibido como `expected`.
Redefinir compara aquela entrada, remove somente ela e não dispara grafos;
conflitos exigem atualização. Projeções normais de cena, jogador e streamer
omitem a memória privada. Atualizações vinculadas e arquivos de campanha
preservam a memória; duplicar um elemento nativo limpa só sua própria memória,
sem limpar os valores compartilhados da cena.

Blueprint V2 `switch` e `random` são controles de execução com portas dinâmicas,
sem `automationMemory` por nó. Escolher caminho guarda `valueType`, `value`
tipado de reserva e de um a quatro casos exatos `{id, value}`. IDs dos casos são
únicos entre `case1`–`case4`, e seus valores são únicos dentro do tipo escolhido
booleano/número/texto; booleanos permitem no máximo dois. Os limites dos valores
são os mesmos das variáveis. O tipo da entrada Value deriva de `valueType`.
Igualdade estrita seleciona o ID de um caso configurado ou `default`, usando a
reserva somente sem conexão em Value. Leituras conectadas usam o retrato inicial
do evento. Mudar o tipo redefine os valores e remove fios de Value incompatíveis
e casos descartados em uma etapa de desfazer; remover um caso conserva os IDs
e fios dos restantes.

Aleatório guarda de dois a quatro `weights`: inteiros de 0 a 1.000 com soma
positiva. Suas portas são `branch1` até a quantidade configurada. O sorteio usa
o peso total de todas as saídas configuradas, inclusive desconectadas. Peso zero
nunca é escolhido; um caminho escolhido sem conexão encerra o ramo sem novo
sorteio. `executionOutputs(node)` retorna descritores dinâmicos e
`nodeOutputs(node)` deriva seus IDs. Nós de escolha executam uma vez por percurso
do grafo, e `decisions` registra strings das portas escolhidas junto às decisões
booleanas existentes. O registro do mestre mostra tipo/valor lido/saída de
Escolher caminho e saída/peso escolhido/soma de Aleatório. Projeções de público
não expõem escolhas privadas.

O runtime deriva cada sorteio usando HMAC sob a chave privada do servidor da
instalação, com UUID da requisição, posição do evento raiz, posição do sorteio na cadeia, elemento,
evento e ID do nó; depois usa um gerador isolado para o peso total configurado.
Não consome nem reinicia o estado global de RNG do processo. Repetir um recibo
não executa de novo; repetir um comando lógico revertido usa a mesma identidade
de sorteio. Continuações de Delay preservam saídas escolhidas e nós já visitados;
Delay e Temporizador carregam as posições privadas `budget.randomRoot` e
`budget.randomDraws` entre trechos; tarefas antigas usam zero para ambos.
Movimento de tokens e exclusão de personagem/pasta conservam o contexto do
comando original, distinguindo eventos raiz de presença sem reiniciar a sequência
em chamadas aninhadas. Estado privado inválido
é recusado, e permissões, reversão de transação e limites da cadeia continuam
valendo. Os valores autorados de reserva/casos de Escolher caminho sobrevivem
à geração, cópia nativa e reescrita de referências de arquivo como conteúdo,
inclusive textos semelhantes a UUIDs.

O `simulateGraph` local aceita `context.randomDraw(nodeId, total)`, retornando
um inteiro em `[0, total)`, ou usa `Math.random` para essa prévia. Somente nós
Aleatório alcançados sorteiam; resultados convertidos ou fora do intervalo são
recusados. Escolhas da prévia não consomem a sequência do servidor nem gravam
memória de execução; também não executam receptores de sinais ou retomam tarefas
agendadas.

Blueprint V2 `counter`, `once` e `cooldown` são controles de execução com uma
Entrada e ramos `true`/`false`, sem portas de valor. O `target` inteiro do Contador
vai de 1 a 1.000.000; a contagem incrementa antes da comparação e para em
1.000.000. Uma vez guarda somente `true` depois da primeira visita. O `seconds`
finito de Recarga vai de 0,1 a 86.400; uma visita permitida guarda milissegundos
UTC inteiros `now + ceil(seconds * 1000)`, e uma visita bloqueada conserva o prazo.
O runtime fornece a hora do servidor; a avaliação pura usa zero por padrão.
A passagem do tempo não inicia um evento; a continuação agendada usa o nó Delay
separado.

`blueprint_memory.py` valida e reconcilia a memória privada em
`SceneObject.data.automationMemory`, no formato
`{event: {nodeId: {type, value}}}` e com até 128 entradas. Essa memória é distinta
das variáveis tipadas e pertence a um elemento. Remover evento/nó ou mudar seu
tipo descarta o progresso; editar parâmetros, posição e conexões o conserva.
Uma nova duração de Recarga vale na próxima ativação permitida, mantendo o prazo
atual. O progresso participa da transação e do recibo: falhas o revertem e
repetições não o duplicam. Atualizações vinculadas e arquivos de campanha o
preservam; cópias nativas o limpam. Projeções de público omitem a memória para
todos os papéis fora da resposta de automação exclusiva do mestre.

`validateBlueprintMemory` e `reconcileBlueprintMemory` espelham essas regras no
modelo puro. `simulateGraph` também aceita `{memory, now}` no sexto argumento,
copia/reconcilia essa memória e retorna `memory` e `decisions` dos ramos nos
grafos de controle. Os campos Prévia dos nós persistentes da modal fornecem valores iniciais
temporários para cada simulação. `memory.elements` na resposta de automação
alimenta a visão Memória dos nós do mestre; `automation/reset-memory` recebe
`elementId`, `event`, `nodeId` e o `{type, value}` exibido em `expected`.
A redefinição compara e remove a entrada sem emitir eventos; conflitos exigem
atualização antes de tentar novamente.

Blueprint V2 `delay` é um controle de execução com Entrada e Próximo, `seconds`
finito de 0,1 a 86.400 e sem portas de valor ou entrada em `automationMemory`.
`simulateGraph` retorna `delay: {nodeId, seconds}` na primeira espera alcançada
e interrompe todo o restante do evento, incluindo ramos posteriores de
Sequência. A trilha inclui Delay e as ações incluem somente efeitos anteriores;
o navegador não agenda trabalho nem simula uma continuação.

O servidor guarda uma continuação privada em `AutomationDelay` na transação que
grava os efeitos anteriores. Pilha de execução em profundidade, nós já visitados,
valores puros já calculados e retratos originais do evento sobrevivem a reinícios,
preservando a ordem de Sequência e evitando repetir nós convergentes. Estado,
estado anterior, estados referenciados e variáveis tipadas conservam os valores
do início do evento mesmo na primeira leitura após uma espera; a memória dos
controles é consultada no momento da retomada. Tomada da tarefa, efeitos,
conclusão e recibo da continuação são gravados juntos. Os limites atravessam
todos os trechos: 32 operações de elemento, 256 entregas de sinal de cena,
quatro operações por elemento,
1.024 ações e 32 retomadas temporizadas. Delay e Temporizador compartilham 64
tarefas pendentes por cena e 256 por campanha.
Retomar uma continuação não consome outra operação de elemento.

`blueprint_delays.py` valida a identidade do comportamento e os alvos/recursos
referenciados, confere a participação e o acesso atual sem promover o papel
original e registra
cancelamentos/falhas. Elementos alvo ausentes usados pela continuação cancelam a
espera; referências ausentes de luz, som ou imagem em qualquer parte do blueprint
também cancelam, mesmo quando usadas somente antes da suspensão. Mudar o
comportamento do blueprint
cancela o trabalho pendente; mover cartões em x/y não cancela. Pausar a cena conserva esperas
vencidas até retomar. Um executor em segundo plano no servidor processa as
entradas vencidas sem depender de HTTP ou atividade do navegador; nenhuma
transação fica aberta durante a espera. Continuações não entram em arquivos de
conteúdo ou cópias de campanha nem nas projeções de público.
A fila conserva no máximo 50 entradas encerradas por cena para diagnóstico
privado.

A lista `delays` da resposta de automação exclusiva do mestre alimenta a visão
Aguardando. O comando normal `automation/cancel-delay` envia `delayId` e o
`expectedDueAt` exibido, compara a entrada pendente e cancela sem mudar o estado
do jogo nem disparar um grafo. Conflitos exigem atualização.

Blueprint V2 `timer` é um controle de execução com Entrada/Próximo, sem portas
de valor nem entrada em `automationMemory`. Seus campos autorados exatos são
`name` e `action` (`start`, `stop` ou `restart`), com `seconds` finito de 0,1 a
86.400 obrigatório somente em start/restart e ausente em stop. Nomes usam o
formato ASCII dos sinais/variáveis, com distinção entre maiúsculas e minúsculas.
`simulateGraph` enfileira uma cópia da ação e segue imediatamente por Próximo;
não avança uma contagem nem executa seu receptor. Temporizadores alcançados
antes de Delay continuam enfileirados; os posteriores aguardam a continuação
no servidor. A modal oculta a duração em Parar e avisa quando não há grafo
receptor `signal:nome` no blueprint proprietário, sem recusar essa configuração.

`AutomationDelay` também guarda temporizadores com `kind="timer"` e `name`.
Uma restrição de banco permite um temporizador pendente por elemento/nome;
nós e grafos distintos desse elemento controlam a mesma tarefa nomeada.
`control_timer` aplica as ações na ordem autorada dentro da transação do comando.
Iniciar conserva identidade, prazo, autor e limites de uma entrada existente;
Parar cancela sem emitir; Reiniciar cria uma substituta sob o autor e os limites
do evento atual. Cada ação continua o grafo imediatamente. Falhas de capacidade
ou de ações posteriores revertem as operações de temporizador com os demais
efeitos.

O mesmo executor persistente entrega o vencimento como um novo `signal:nome`
no proprietário, lendo estado, referências e variáveis atuais em vez do retrato
de um evento salvo. Sem receptor, conclui sem efeitos. Acesso/autor, cancelamento
por edição de comportamento ou recursos ausentes, pausa/retomada, projeções
privadas e exclusão de arquivos/cópias seguem a política de Delay. Efeitos,
conclusão e recibo são gravados juntos, conservando os limites da cadeia entre
execuções do servidor. Vencer um Temporizador consome uma operação de elemento;
retomar uma continuação de Delay não. Ambos consomem o limite compartilhado de
32 retomadas temporizadas, e os limites por elemento restringem grafos que
reiniciam a contagem. Não existe modo recorrente/global.

A projeção `delays` do mestre identifica temporizadores com `kind: "timer"` e
`name`. Aguardando mostra linhas com nome e vencimento e os controles Parar
temporizador e Reiniciar temporizador. Parar usa `automation/cancel-delay`;
`automation/restart-timer` recebe `delayId` e `expectedDueAt`, confere a entrada
pendente exibida e cria uma substituta com prazo após sua duração salva. Esse
reinício pelo mestre conserva autor original, limite do papel e limites da
cadeia. Ambos exigem atualização diante de trabalho desatualizado e não emitem
um evento imediato de jogo.

Decorações de alavanca compartilham o registro de adaptadores e referências
tipadas de elemento. `features/images/ui/lever-controls.js` trata os dois
cliques nativos antes da seleção mista, com verificações de papel, ferramenta e
camada, bloqueio de comandos simultâneos e descarte de listeners. Edições de
geometria/configuração não executam seus grafos.

`floor-painter.js` coordena gestos de pincel livre, retângulo, círculo e polígono
sem registrar eventos. Ele captura o documento e as opções do pincel no início,
mantendo a imagem e o ID do objeto de cada célula entre prévias. `model.js` enumera
as células da forma e aplica a substituição do chão de forma atômica;
`workspace.js` trata a entrada e registra cada gesto concluído uma vez no histórico
de desfazer. Cancelamento ou falha por limite de objetos preserva o documento original.

O Estúdio possui um canvas em toda a largura e uma biblioteca horizontal abaixo
dele. A aba **Ferramentas** do painel auxiliar existente reúne botões das
ferramentas, material, opções do pincel, camada ativa e encaixe na grade. Esses
controles mantêm os hooks `data-builder-*` e listeners existentes, sem duplicação
no DOM. O cabeçalho reúne o campo rápido de nome do mapa, atalhos Selecionar,
Pintar e Apagar e tamanho do pincel; depois, desfazer/refazer antes do botão de
estado do salvamento, prévia e geração de cena. Os controles rápidos usam hooks
próprios e compartilham o estado existente de ferramenta e pincel com
Ferramentas. Pintar restaura o pincel livre de chão e a operação de pintura e
seleciona a categoria Chão na biblioteca. Apagar mantém a exclusão
do objeto inteiro. O tamanho espelha Ferramentas e fica ativo para o pincel livre
de chão, inclusive borracha por área. Mantém os limites de 1–20 células com encaixe
e 0,05–20 sem encaixe e os atalhos de colchetes. A seleção mantém Shift-clique e
seleção por caixa. Prévia e
requisições pendentes desativam esses controles de edição. O nome rápido espelha
Configurações: Enter ou sair do campo aplica uma operação de histórico, Escape
cancela o rascunho e Ctrl+S aplica o nome atual antes de salvar. Os atalhos do
histórico continuam Ctrl+Z, Ctrl+Shift+Z e Ctrl+Y.
Busca, importação, coleção e categorias por tipo continuam
acessíveis ao recolher os cards da biblioteca. O destaque inicial de Chão mostra
todas as imagens disponíveis da campanha; escolher a categoria Chão, Parede,
Porta ou Objeto também ativa sua ferramenta de desenho. Escolher um preset de
luz/efeito nativo ativa sua ferramenta de posicionamento. O seletor em
Ferramentas acompanha o pincel ativo e inclui imagens individuais, famílias de assets e sua aparência
padrão. Cards de famílias também aparecem na biblioteca. A importação usa a modal
padrão da aplicação para escolher arquivos, tipo de imagem e família opcional;
dois cliques no card de uma imagem abrem seu editor de tipo e família. Luzes mostram instruções de
posicionamento sem se tornarem uma classificação de asset de imagem. Painéis, no
canto superior direito da área de desenho, abre o mesmo painel auxiliar com
ferramentas, camadas, seleção, configurações, projetos e revisão. O painel começa fechado; selecionar
ou pintar não o abre. Fechá-lo mantém a biblioteca acessível. Os formulários
existentes de propriedades e configuração permanecem nesses painéis, e os hooks
antigos ocultos no DOM preservam a compatibilidade do controlador. As propriedades
dos objetos ficam em Seleção; esta interface não acrescenta uma modal de propriedades.
Componentes permanece planejado. Revisão mostra resumo, geração e atualização da
cena vinculada. Controles de visualização e dimensões em células ficam na parte inferior da
área de desenho. O estado do painel, da biblioteca e da visualização pertence ao
editor e não ao documento do projeto; esses controles não devem alterar a cena
gerada. Camadas nomeadas do projeto são
distintas: ordem, nomes, visibilidade e bloqueio persistem na versão 3 do formato,
junto com orientação do chão, decorações, luzes e metadados locais dos assets.
Alças permitem reordenar camadas por arraste, além das setas. Listas de conteúdo
expansíveis selecionam objetos individuais sem alterar o layout da área de desenho.
O campo opcional `family` do asset permanece na versão 3; seus membros compartilham
um tipo de imagem. A pintura de chão salva um `assetId` específico por célula de
1 × 1, mantendo as variações escolhidas na prévia, em desfazer/refazer, na reabertura
e na geração.
Visibilidade e bloqueio controlam seleção e edição; a geração inclui todas as
camadas do projeto. `model.js` aplica movimentos de grupo, duplicação e rotação
de forma atômica, preservando giros exatos de 90 graus e pontos de portas antigas.
A prévia desativa a edição, oculta suas
guias e mostra temporariamente todas as camadas, restaurando a visibilidade
anterior ao sair. Ela não altera a câmera ou o documento do projeto; salvar e
gerar cena continuam disponíveis. A imagem contém chão e faixas de parede;
imagens nativas, luzes e aparência de portas permanecem objetos durante o jogo.
A ordem das camadas mantém as etapas existentes do raster: todo o chão é
desenhado antes das faixas de parede. Objetos nativos mantêm seus contratos de
renderização do VTT.
A geração registra a propriedade dos recursos no projeto. Atualizar a cena
vinculada substitui apenas esses recursos e as fatias, preservando conteúdo manual
e estado das portas durante o jogo. Revisões do projeto/cena e os dados originais
dos objetos são conferidos novamente na transação; edições conflitantes no VTT
interrompem a atualização.
A mesa recarrega o documento restaurado do cache de histórico em
`pageshow.persisted`, pois o renderizador e os ciclos dos módulos já foram
encerrados.

### Redes de paredes no Map Builder

`builder/wall-edit.js` controla movimentos atômicos de nós, divisões,
prolongamentos e conexões de pontas nos eixos de parede da versão três do
projeto. Nós compartilhados são derivados de pontas coincidentes em uma mesma
camada editável, independentemente de material ou espessura. Adicionar ou
prolongar uma parede sobre uma borda editável divide essa borda e forma um nó em
T. Portas continuam sendo objetos independentes. Falhas de limites do mapa,
comprimento mínimo ou recursos deixam o documento e os IDs de fragmentos intactos.

`builder/wall-controls.js` controla os gestos de ponteiro e teclado da parede
selecionada. A área de trabalho confirma cada operação concluída uma única vez;
cancelar restaura o documento anterior ao gesto. Controles SVG de ponta, meio e
prolongamento mantêm seu tamanho na tela ao mudar o zoom. O foco é restaurado
após renderizações; Prévia, estado ocupado e permissões da camada desativam a
edição. O prolongamento armado usa um marcador próprio e devolve o foco ao canvas.

`builder/wall-joins.js` e `maps/wall_joins.py` derivam a mesma malha visual após
remover os intervalos ocupados por portas. Cantos usam uma junta limitada a
quatro vezes a maior meia-espessura, com chanfro como alternativa. Trechos
colineares contíguos compatíveis compartilham um referencial canônico; paredes
isoladas mantêm seu referencial autoral. Trechos antigos colineares compatíveis são
deduplicados na renderização. Os polígonos de cada parede formam uma única
máscara de cobertura, preservando o alfa sem aplicá-lo duas vezes em seus próprios
encontros. Camadas permanecem separadas, e encontros não fecham aberturas de
portas. A malha pertence à apresentação: coordenadas, IDs e eixos de colisão
nativos mantêm seu contrato de persistência.

## Dimensões compartilhadas e tokens visuais

[`tokens.css`](../../gravewright/web/static/gravewright_web/css/tokens.css) define os valores visuais compartilhados. Tokens dimensionais fixos usam valores simples em `px`. Reutilize os tokens existentes quando forem adequados ao componente e introduza um novo valor compartilhado somente quando ele for necessário entre componentes. A escala Fibonacci e seu script de auditoria foram retirados; o CSS do núcleo usa as regras de espaçamento, raio e tipografia abaixo em vez de `--fib-*` ou `--step-*`.

Use `--space-*` para padding, margens e gaps, incluindo suas formas abreviadas, lógicas e de linha/coluna. Ao migrar uma dimensão fixa, escolha o valor mais próximo desta escala; em caso de empate, escolha o menor. Preserve o sinal de margens negativas. O sufixo do token conta passos de quatro pixels, com nomes separados para zero, um e dois pixels:

| Token | Valor |
| --- | --- |
| `--space-0` | `0` |
| `--space-px` | `1px` |
| `--space-half` | `2px` |
| `--space-1` | `4px` |
| `--space-2` | `8px` |
| `--space-3` | `12px` |
| `--space-4` | `16px` |
| `--space-5` | `20px` |
| `--space-6` | `24px` |
| `--space-7` | `28px` |
| `--space-8` | `32px` |
| `--space-10` | `40px` |
| `--space-12` | `48px` |
| `--space-14` | `56px` |
| `--space-16` | `64px` |

O antigo valor de 34px de `--space-9` é substituído por `--space-8` com 32px. Os raios de borda usam estes nomes compartilhados:

| Token | Valor |
| --- | --- |
| `--radius-sm` | `4px` |
| `--radius-md` | `8px` |
| `--radius-lg` | `12px` |
| `--radius-xl` | `16px` |
| `--radius-pill` | `999px` |
| `--radius-circle` | `50%` |

O CSS da interface do host deve renderizar textos com **12px ou mais**. Confira os tamanhos efetivos vindos de estilos herdados, unidades relativas e formas abreviadas de fonte, além de `font-size` explícito. Os nomes existentes `--text-3xs`, `--text-2xs` e `--text-xs` continuam disponíveis com 12px. Textos de PDFs e desenhos, assim como rótulos de cena escalados pela câmera, preservam os tamanhos definidos pelo autor.

Larguras, alturas e demais geometrias dos componentes mantêm as dimensões necessárias. Um valor específico de um único componente pode usar um literal local em `px`; reserve tokens `--size-*` compartilhados para valores reutilizados entre componentes. A geometria responsiva ainda pode usar unidades relativas e expressões de layout como `calc()` e `clamp()` quando necessário.

### Controles de formulário

O `base.css` compartilhado fornece padrões escuros com baixa especificidade para
campos e botões nativos, botões de seleção de arquivos, caixas de seleção, sliders e
amostras de cor, incluindo formulários montados após o carregamento. Use `gw-field`
para rótulo, controle e ajuda; caixas de seleção, opções, sliders e cores mantêm
suas dimensões próprias em vez de herdar as de campos de texto. Campos nativos
inválidos e `aria-invalid="true"` usam o tratamento de erro do campo. Associe ajudas
e erros com `aria-describedby`.

Seletores de escolha única herdam sua seta dos estilos base. Altere a superfície
com `background-color`, pois o atalho `background` remove essa imagem, e reserve
espaço no final para a seta. Seletores múltiplos ou com lista visível não usam seta.
Áreas personalizadas de upload devem manter o campo de arquivo acessível pelo
teclado, exibir seu foco e impedir o arraste da janela pelo alvo de upload.
Verifique os estados vazio, selecionado, desabilitado e de erro em telas estreitas
com dados sintéticos; a escolha de arquivos do sistema operacional continua nativa.

## Estado nativo e tempo real

O frontend nativo usa a API de domínio compartilhada onde implementada e mantém adaptadores HTTP/socket especializados para uploads, assinaturas do tabuleiro e fragmentos renderizados. A API pública não substitui todos os transportes nativos.

O controlador de tempo real conecta o WebSocket autenticado da mesa atual, gerencia assinaturas/reconexão e dispara eventos `gravewright:*`. O servidor envia projeções autorizadas por usuário e HTML renderizado; dados privados, audiência do chat e visibilidade da cena são filtrados antes do envio. Insira texto de usuário com `textContent`. A inserção de fragmentos HTML existente destina-se ao HTML dos templates confiáveis do servidor, não a texto arbitrário de chat ou módulo.

`gravewright:api-event` é o evento interno consumido pela API de domínio; notificações `api.changed` provocam novas leituras autorizadas. Integrações públicas devem usar `api.events.on(...)`, conforme [eventos da API](api.md#eventos-de-domínio), em vez de copiar comandos internos de socket. Assinaturas não são um fluxo durável: reconecte e releia o estado. Criar `gravewright.forTable(...)` não abre um socket.

Os diretórios nativos de itens e compêndios ordenam cópias das entradas visíveis
pelo nome exibido, usando o idioma ativo; a ordem armazenada e os IDs dos
documentos permanecem intactos. Pacotes, filtros e prévias de compêndios usam
linhas compactas e janelas com tamanho inicial ajustado ao conteúdo, com rolagem
interna para conteúdos longos. O usuário mantém os controles compartilhados de
mover, redimensionar, minimizar e redefinir janelas. Mestres podem criar o
primeiro compêndio no diretório vazio; acesso de leitura não exibe controles de
importação ou permissões. Os editores de itens de cada sistema permanecem em
seus pacotes e usam os contratos existentes do host. Projeções de itens repetidas
preservam menus de ações abertos e foco; alterações de documento ou permissão
invalidam esses menus.

## Fontes e arquivos gerados

A maioria dos JavaScripts de cada app em `static/` é fonte servida diretamente. Alguns arquivos são resultados de build versionados. [`maps/scripts/build.cjs`](../../gravewright/maps/scripts/build.cjs) gera:

| Entrada/fonte editável | Destino gerado |
| --- | --- |
| `maps/frontend/widgets/game-board/ui/board.js` | `maps/static/gravewright_maps/vendor/board.js` e módulos nomeados em `runtime/` |
| `maps/frontend/shared/rendering/render-profile.js` | `maps/static/gravewright_maps/render-profile.js` |
| `maps/frontend/native/tools.js` | `maps/static/gravewright_maps/tools.js` |
| `maps/frontend/native/builder-catalog.js`, `builder-preview.js` | `maps/static/gravewright_maps/builder-catalog.js`, `builder-native.js` |
| `maps/frontend/native/builder-editors.js` | `maps/static/gravewright_maps/builder-editors.js` |
| `maps/frontend/native/table-modules.js` | `table/static/gravewright_table/media-workspace.js` |
| `maps/frontend/features/walls/{ui,model}/walls.js` | `maps/static/gravewright_maps/walls/` |
| Fontes de camadas e perfis de iluminação | `maps/static/gravewright_maps/sources/` |
| `maps/frontend/calibration.js`, `directory.js` | Modelos/controladores estáticos correspondentes |
| `maps/frontend/shared/lib/dom/tree-drag.js` | `actors/static/gravewright_actors/tree-drag.js` |
| `maps/frontend/features/tokens/ui/controller.js` | `tokens/static/gravewright_tokens/controller.js` |
| `pdf_system/frontend/controller.js` | `pdf_system/static/gravewright_pdf_system/controller.js` |

Os caminhos da tabela são relativos a `gravewright/`. Edite fontes e reconstrua os destinos. Evite correções isoladas em chunks minificados ou bibliotecas de terceiros.

Ferramentas, tabuleiro, catálogos, editores e prévia do Builder mantêm suas URLs
públicas de entrada e importam módulos ES nomeados de `gravewright_maps/runtime/`,
seguindo os caminhos de cada recurso nas fontes. Módulos compartilhados têm uma
única identidade no navegador; PixiJS e seu adaptador unsafe-eval são emitidos
uma vez em `vendor/pixi.js`. Prévia e editores continuam com imports sob demanda,
e o worker de visibilidade mantém a URL relativa do recurso e sua entrada pública
existente. O manifesto do Runner inclui cada módulo e aviso de licença emitido.
Distribua o grafo gerado completo. Essa organização usa mais requisições pequenas
e evita cópias repetidas nos bundles; tamanhos de arquivos, sozinhos, não demonstram
melhora de desempenho no navegador.

Na raiz do repositório:

```sh
npm ci --include=dev --prefix gravewright/maps/frontend
npm run build --prefix gravewright/maps/frontend
npm test --prefix gravewright/maps/frontend
```

O build usa PixiJS/esbuild fixados em [`maps/frontend/package-lock.json`](../../gravewright/maps/frontend/package-lock.json), gera ES2022 e mantém imports `/static/*` externos. O módulo compartilhado de perfil de renderização permanece externo para todos os recursos usarem a mesma instância. O build também copia licenças/avisos das dependências e escreve `vendor/packages.json`; preserve esses arquivos na redistribuição. Ele rejeita a inclusão de pacotes Vue.

### Preparação pelo executor Windows

O [Gravewright Runner](windows-runner.md) reutiliza Node.js/npm verificados dentro de `data/runner/` ou baixa sua cópia gerenciada nessa instalação quando necessário. Seu arquivo em lote CMD chama [`scripts/prepare_frontend.py`](../../scripts/prepare_frontend.py) no modo `--plan` para conferir versões dos pacotes, impressões dos arquivos e uma operação real do esbuild. Uma instalação correspondente e funcional das dependências pode ser reaproveitada já na primeira execução. O próprio arquivo em lote executa `npm ci --include=dev --include=optional` quando é necessário instalar dependências e o `npm run build` existente na primeira preparação ou em um build invalidado. Depois chama o helper no modo `--record` para verificar e salvar o estado das saídas concluídas. O esbuild é necessário durante a preparação, embora as dependências Python de desenvolvimento sejam omitidas da instalação normal do executor.

O plano retorna código de saída `0` para recursos atuais, `10` para instalação npm e build, ou `11` para somente build. O launcher em lote trata essas decisões explicitamente. Ambos os modos do helper aceitam `--node`, `--npm-cli` e `--state-dir`; o modo padrão do helper continua disponível para realizar a preparação completa em scripts de desenvolvimento e testes de regressão.

O projeto npm permanece em `gravewright/maps/frontend`; seu `node_modules/` ignorado é instalado ali e os recursos estáticos gerados são gravados nos destinos acima. Essas saídas são recursos versionados da aplicação; portanto, uma alteração nos fontes seguida da preparação pelo executor pode produzir um diff no controle de versão. Revise e inclua as saídas geradas e os avisos apropriados ao contribuir alterações de frontend.

O estado da preparação fica dentro da pasta descompactada em `data/runner/frontend/<hash-local-do-código>/state.json`. Ferramentas gerenciadas e caches do npm/uv também ficam nesta instalação. A verificação das dependências inclui arquivos de pacotes e versões Node/npm selecionadas. A verificação do build inclui fontes editáveis, script de build e hashes das saídas geradas. O arquivo em lote solicita ao `build.cjs` um manifesto das saídas, incluindo avisos de terceiros, pela variável de processo opcional `GRAVEWRIGHT_BUILD_MANIFEST`. Uma próxima execução pula um build válido e inalterado; entradas modificadas ou saídas ausentes/modificadas provocam nova preparação. Um build com falha impede a inicialização, em vez de servir um frontend não verificado. Depois, `collectstatic` copia os recursos públicos preparados para o diretório `data/staticfiles/` dentro do projeto.

O registro de métodos de domínio possui geração própria:

```sh
uv run --locked python scripts/generate_frontend_api.py
```

O script gera somente `modules/static/gravewright_modules/frontend-contract.js` a partir de `contracts/frontend.json`. `generated.js` e schemas do SDK original são artefatos separados, não gerados por esse script. `collectstatic` reúne arquivos para implantação, mas não executa builds JavaScript.

## Camadas do tabuleiro e ciclo dos recursos

O seletor **Nova cena** inclui **Mapa Vazio**. O formulário pede o nome da cena,
a cor de fundo, a largura e a altura em pixels, se deve exibir o grid e se deve
ativar a cena ao criar. A criação usa a pasta atual. Com a ativação desmarcada,
somente o criador visualiza a nova cena; os jogadores continuam na cena ativa.
O servidor gera tiles comuns sem
perda de qualidade, respeitando os limites configurados de imagem e quantidade
de tiles. Renderização, permissões, ferramentas e arquivos de campanha seguem
os fluxos existentes.

A lista de cenas do mestre mostra bolinhas com a cor de identificação salva de
cada jogador e a marca **GM** na cena visualizada. As dicas das bolinhas identificam
os jogadores, incluindo participantes desconectados com destino persistido.
**Ativar para jogadores selecionados**, no menu de contexto, abre uma lista para
selecionar um ou mais jogadores. **Ativar para jogadores** continua ativando para
todos e remove destinos individuais. Alterar a cor atualiza as bolinhas sem recarregar.
A marca **GM** também identifica a visualização privada, sem o texto adicional
**Preparando**. Os ponteiros dos outros participantes aparecem como bolinhas
translúcidas com seus nomes, usando a cor de ping salva de cada remetente. O próprio
mouse mantém o cursor nativo. O movimento remoto é interpolado em coordenadas da
cena e projetado pela câmera de quem vê, com tamanho constante no pan e no zoom.
As posições são transitórias, enviadas no máximo dez vezes por segundo e removidas
ao sair, desconectar ou trocar de cena. Um ponteiro parado permanece visível
mesmo com atualizações atrasadas; o silêncio sozinho não indica saída. As camadas
das ferramentas da cena também transmitem posições, exceto controles da interface.
Trocar de janela ou aba pausa a transmissão e preserva a última posição
compartilhada. A remoção ocorre ao sair da cena, desconectar ou receber uma ordem
explícita para ocultar; perder o foco da janela não representa uma saída.
Preferências → Ponteiros do mouse oferece controles independentes para ver os
ponteiros dos participantes e compartilhar o próprio. Ambos começam habilitados,
são salvos por perfil neste dispositivo e sincronizados entre abas. Ocultar os
ponteiros recebidos mantém suas posições disponíveis para reexibição imediata,
sem renderizá-los. Desabilitar o compartilhamento oculta imediatamente o ponteiro
para os demais e interrompe a transmissão; não afeta pings nem preferências alheias.

O mesmo menu possui o tópico **Atalhos do teclado** para ferramentas e janelas
executáveis do dock, incluindo a busca da campanha. `table/shortcuts.js` obtém
os padrões do dock renderizado, grava combinações nos campos em foco, atualiza
atalhos acessíveis/dicas e aciona os botões existentes. As configurações são
salvas por perfil/dispositivo em `gravewright.shortcuts.<profile>` e sincronizadas
entre abas. Cada camada possui seu escopo de ferramentas; atalhos de janelas
conflitam em todas as camadas. A precedência dos padrões existentes é preservada.
É possível remover atalhos ou restaurar todos os padrões. Escape cancela a
gravação; edição de texto, composição, navegação em modais e combinações
reservadas ao navegador/edição mantêm seu comportamento nativo. Gestos
específicos das ferramentas não são remapeados neste tópico.

Esses recursos usam o contrato de chaves-fonte em inglês do Translator instalado:
`tr(...)` no Jinja, o adaptador nativo `gwText(...)` e `createTranslator().t(...)`
nos controles do navegador. Complementos revisados do host para pt-BR/es cobrem
as novas chaves sem alterar arquivos assinados de idiomas já instalados. Sem um
pacote de idioma ativo, o host usa inglês e preserva o idioma escolhido no perfil.
Nomes de jogadores, cenas e títulos autorais de medições usam `translate="no"`;
combinações de teclas e IDs de ações também permanecem iguais.
O cenário `tests/e2e/table_translator.py` aceita
`GRAVEWRIGHT_TRANSLATOR_CATALOG_ROOT` com catálogos reais `en.json`, `pt-BR.json`
e `es.json`. Ele instala um pacote descartável e verifica os novos controles,
Smart Objects enviados pelo usuário, áreas circulares, valores autorais e fallback.
Somente destinatários autorizados na mesma cena recebem as posições. Streamers
apenas recebem ponteiros, e a camada GM não transmite o movimento do mouse.

O dock da mesa oferece desenho pelo Mini Paint (`Desenhar`, atalho `B`).
Retângulos e elipses pertencem a esse editor; não há ferramenta Formas separada
nem atalho `T`. Os marcadores de área compartilhados existentes continuam
visíveis, com os dados salvos e as APIs públicas compatíveis. `Medir` continua
oferecendo medidas locais da cena. Ative **Título** para editar um rótulo na
própria marcação, acima das dimensões. Cada título acompanha a medição ao mover
e ampliar o mapa e permanece visível ao fechar a ferramenta. Títulos seguem o
mesmo ciclo local das medições: não são transmitidos nem salvos na campanha.

`maps/frontend/` separa modelos de entidades, modelos/UI de funcionalidades, utilitários e widget do tabuleiro. O widget coordena renderização, entrada, agendamento/cache/pré-carregamento de tiles, camadas nativas, polígonos de visão, luzes e shaders. As funcionalidades incluem paredes, tokens, desenhos, medidas, efeitos e seleção. Testes de algoritmos ficam ao lado dos modelos e são empacotados por `maps/scripts/test_models.cjs` para o executor de testes do Node.

Mantenha um sistema de coordenadas consistente: pixels lógicos da cena, origem superior esquerda e centro dos tokens como âncora. Pan/zoom convertem posições em coordenadas CSS da área visível; a densidade de pixels altera a resolução de renderização. Misturar unidades desalinha seleção, tokens e luzes. A API de sobreposição oferece conversão explícita em vez de expor o renderer PixiJS.

Operações assíncronas pertencem a uma página, tabuleiro, ativação ou montagem. [`Lifetime`](../../gravewright/modules/static/gravewright_modules/lifetime.js) cancela chamadas e remove assinaturas; os fontes de mapas possuem utilitários próprios. Adicione/remova listeners e observers com seu proprietário. Libere recursos gráficos e tarefas pendentes ao encerrar o tabuleiro ou trocar de cena. Listener ou API que sobrevive ao contexto pode atualizar a próxima cena com dados antigos.

Atualizações da cena atual preservam posição/zoom da câmera, imagens dos tokens
e camadas montadas, inclusive revisões causadas por automações de teleporte.
Somente a troca de cena redefine a câmera. Revisões do mapa atualizam os tiles
existentes pela URL e mantêm os tiles anteriores decodificados visíveis até os
substitutos estarem prontos; requisições superadas não podem desenhar uma revisão
antiga. Uma falha na substituição mantém a imagem atual durante as tentativas
limitadas de recuperação. Ocupação e geometria das regiões atualizam sua própria
sobreposição, mantendo montados os recursos de piso, luz e shader não afetados.

Nomes de tokens, iniciais sem imagem e indicadores de condições são rasterizados
com densidade ajustada ao zoom da câmera e à resolução do renderizador. Faixas de
densidade em potências de dois, limitadas a oito, mantêm o texto ampliado nítido
sem recriar texturas ao mover a câmera ou dentro da mesma faixa de zoom. Os textos
externos usam fonte sem serifa, alinhamento central, contorno fino e espaçamento
entre linhas para as condições abaixo do nome. O cenário
`tests/e2e/token_text_resolution.py` verifica zoom, telas comuns e de alta densidade,
alterações de nomes e descarte do renderizador.

**Configurar token** permite ao mestre escolher a cor e o público de cada barra:
todos, dono e mestre ou somente mestre. O servidor omite as barras restritas do
estado enviado a cada participante. As opções de exibição da ficha continuam
como padrão até serem substituídas. Essas configurações pertencem ao token da
cena, são preservadas ao duplicar e não alteram o esquema da ficha do sistema.
As barras mantêm distância de 5px acima/abaixo do token; nome e indicadores de
condições reservam espaço para elas. Não são adicionados valores numéricos às barras.
O nome pode aparecer sempre, somente ao selecionar, somente ao passar o mouse ou
ao selecionar/passar o mouse (padrão de compatibilidade). Uma opção por token controla
o indicador de turno: contorno verde estático no turno atual e contorno tracejado
discreto no próximo. `tests/e2e/token_appearance.py` verifica salvamento pela interface,
permissões por destinatário, cores, indicadores e a janela em telas grandes/pequenas.

Confirmações de tokens e estados em tempo real podem conter metadados nativos
`teleports: [{id, version}]`, filtrados pelos tokens visíveis ao destinatário e
suas revisões exatas. A área de tokens conserva cada revisão de teleporte aceita
nas leituras normais. O movimento não é interpolado e somente o objeto Pixi
daquele token é recriado no destino; entregas repetidas mantêm a mesma recriação.
Identidade lógica, seleção e dados da ficha são preservados, e cargas de imagens
antigas não podem restaurar um objeto anterior.

Comandos de tokens bem-sucedidos aplicam o estado autorizado recebido na
confirmação. Eles não repetem o GET de tokens nem solicitam novamente as camadas;
mudanças confirmadas da cena chegam pela assinatura existente em tempo real.
Falhas e conflitos de versão continuam recarregando o estado autorizado. Um
movimento sem deslocamento e sem caminho percorrido não grava nem entra no
estado ocupado. Caminhos que saem e retornam à mesma posição continuam sendo
operações reais para preservar a automação de entrada/saída de regiões.

A área de tokens salva silenciosamente, inclusive quando a confirmação demora.
Comandos pendentes mantêm a proteção de interação para edições concorrentes.
Erros e instruções de rota continuam imediatos; não há aviso nem temporizador de
salvamento. Textos de estado que não mudaram não são reescritos a cada renderização.

Prévias locais de tokens reutilizam a chave da cena estática e a atualização de
imagens enquanto suas entradas imutáveis continuam iguais. Elas não percorrem
todas as transformações das imagens nativas nem reconstroem o índice de origens
dos componentes a cada quadro. Um novo estado de imagens continua atualizando
suas transformações e arte; mudanças de paredes, efeitos, identidade da cena e
papel continuam invalidando os recursos correspondentes.

Notificações de movimento atualizam camadas e tokens sem reconstruir o diretório
de atores ou painel de combate que não mudaram. Edições de atores/combate e outros
comandos de tokens mantêm as notificações correspondentes. Notificações pareadas
de camadas/tokens entregam o áudio espacial uma vez pela atualização de tokens;
edições independentes de camadas continuam atualizando o áudio. Autorização atual
e eventos de mudança para extensões são preservados.

O teleporte na mesma cena avança a revisão do token, não a dos metadados da cena
ou do raster. Suas notificações de camadas/tokens entregam mudanças de região e
aparência sem solicitar outro manifesto nem alterar as URLs dos tiles existentes.
Portais repetidos preservam os pisos decodificados e as texturas do mapa já carregadas.

### Atualizações de imagens nativas

`SceneImageArt` atualiza texturas de imagens comuns independentemente da chave
estática da cena. Uma troca de origem mantém o sprite e sua imagem anterior até
decodificar a nova textura; resultados atrasados não substituem estados mais
novos nem uma cena encerrada. A imagem atual sobrevive à reconstrução de
luzes/geometria na mesma cena. Superfícies compostas e pisos agrupados usam um
cache separado com o mesmo ciclo de vida. Composições inalteradas são vinculadas
de forma síncrona durante reconstruções de efeitos; trocas de material mantêm a
imagem atual até terminar a decodificação. Mudanças de máscara, geometria,
componentes do grupo ou visibilidade revogam imediatamente a cobertura antiga.
A composição fecha todos os bitmaps de entrada, inclusive em falhas e
cancelamentos, e não publica pisos parciais. Cada cache de imagens conserva no
máximo oito texturas ociosas e 16 MiB de dados RGBA decodificados ociosos,
removendo as entradas usadas há mais tempo. Trocar de cena/papel ou encerrar o tabuleiro
cancela tarefas pendentes e libera texturas/bitmaps. Apenas imagens da projeção
autorizada são solicitadas; aparências inativas não são pré-carregadas.

Referências de imagens de tokens aguardam o descarregamento pendente da mesma
URL antes de carregar novamente. Caso contrário, o loader do Pixi pode devolver
a textura antiga do cache enquanto o descarregamento está prestes a destruí-la.
URLs diferentes continuam concorrentes. Descarte aplicações com as opções
explícitas `removeView: true, releaseGlobalResources: false`: o booleano `true`
também libera pools globais ainda usados por outros tabuleiros e prévias.
Texturas da cena e recursos do renderizador continuam sendo liberados pelo dono.

Imagens privadas do GM e marcadores de Objetos vazios continuam visíveis com 55%
de opacidade em todas as abas; seleção e interação ficam restritas a GM. Desenhos
privados multiplicam sua opacidade original pelo mesmo fator. As projeções do
servidor continuam excluindo elementos privados de jogadores/streamers.

A entrega em tempo real envia `maps.layers` e `tokens.state` confirmados antes
das atualizações dependentes de áudio/combate. Cada entrega mantém sua própria
verificação de autorização. Mudanças disparadas por tokens podem compartilhar
a revisão da cena; não descarte estados apenas porque essa revisão é igual.

### Trabalho de iluminação e visão

`SceneLayers` calcula a oclusão das luzes uma vez por chave estática da cena e
reutiliza os polígonos nas máscaras, no atlas de luz e na penumbra do mestre.
`createVisibilityContext` compartilha os índices de paredes e mantém no máximo
oito subconjuntos para alcance finito ou elevação. Preserve a aritmética dos
raios e a composição das paredes: trocar a BVH pode mudar o arredondamento em
extremidades coincidentes.

Quadros de tocha e pulso atualizam sprites aditivos do Pixi sobre texturas de
atenuação imutáveis. Shaders recebem uma textura renderizada na GPU; apenas
partículas que reagem à luz pedem amostras na CPU, limitadas a oito por segundo.
Os perfis mantêm suas taxas de animação. A cena possui o pool de texturas e o
libera depois dos vínculos dos shaders, do atlas e das camadas de sprites.

Mudanças de visão são agrupadas uma vez por quadro de animação. Cenas com pelo
menos 128 segmentos de parede usam o worker de módulo da mesma origem gerado em
`vendor/visibility-worker.js`; cenas menores ou sem worker usam a mesma geometria
de forma síncrona. O worker mantém uma tarefa ativa e o último estado pendente,
transferindo buffers de coordenadas. Observadores nativos levam um `sourceId`
para que o movimento preserve a última visão concluída enquanto calcula a
seguinte. Trocas de seleção, alcance, elevação, cone ou prévia revogam essa visão
imediatamente; mudanças de paredes ou cena encerram o worker anterior. Não
reutilize a visão entre esses limites nem arredonde o alcance configurado ou as
posições dos tokens para células.
Movimento pendente preserva a textura do véu até o resultado chegar; a visão do
mestre sem prévia reutiliza o véu estático sem repintar ao mover tokens.

Ao medir, compare quadros completos e tarefas de worker concluídas. Enfileirar
não equivale a concluir, e WebGL por software em navegador headless não comprova
desempenho de uma GPU física. Gere as entradas do tabuleiro e do worker juntas
pelo build normal de arquivos.

## Estendendo a interface

O [`SurfaceRegistry`](../../gravewright/modules/static/gravewright_modules/surface-registry.js) do host aceita `gravewright.ui.register(domain, declaration)` e retorna função de cancelamento. Suporta superfícies da mesa, `app.shell` e `inside.content`. Uma montagem recebe `{root, context, api, signal, onDispose}`, ciclo de vida e raiz próprios. Falhas geram limpeza e restauram a visibilidade anterior dos elementos nativos substituídos. Esse registro global permite uma substituição por domínio.

Pacotes assinados usam `ModuleRuntime`: registro síncrono durante ativação, chamadas com identidade/lease/revisão e seleção de substituições pelas preferências da mesa. Use o callback `register` do módulo para pacotes instalados; o registro global é destinado a integrações da página do host e tem outras regras de propriedade/seleção. Veja exemplos e nomes em [módulos](modules.md).

## Verificação do frontend

Execute as verificações afetadas pela alteração:

```sh
node --test tests/modules/*.test.mjs tests/effects/*.test.mjs
npm test --prefix gravewright/maps/frontend
uv run --locked python tests/e2e/frontend_api.py
```

Para renderização/interação, use cenários relevantes de `tests/e2e/`, incluindo `mixed_selection.py`, `token_routes.py`, `light_rendering.py`, `effect_geometry.py`, `effect_pixels.py`, `map_prefetch.py` e `realtime.py`. O ambiente de navegador está descrito em [testes](testing.md). Verifique sessões de mestre e jogador quando houver permissões distintas e valide limpeza/reconexão de assinaturas novas. Mantenha textos e catálogos alinhados aos idiomas suportados pela aplicação.
