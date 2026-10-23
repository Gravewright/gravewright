# Mapas mentais

[Documentação](../README.pt-BR.md) · [English](../en/mindmaps.md) · [Gestão de campanha](campaign-management.md)

Abra **Mapas mentais** pelo ícone no dock inferior da mesa ou no gestor de
campanha. As duas telas usam os mesmos grafos salvos na campanha. A referência visual é o
[MindMeister](https://www.mindmeister.com/pt): tópico central, ramificações,
tópicos móveis e conexões. A implementação funciona dentro do Gravewright,
sem conta ou serviço externo.

## Criar e organizar

O mestre cria um mapa com nome, escolhe escopo de campanha ou cena e configura
visibilidade e editores. Novos mapas são privados do mestre. Abra um mapa para
adicionar tópicos raiz, filhos ou irmãos. Selecione um tópico para editar título,
notas, cor, conclusão e recolhimento das ramificações. A troca de tópico pai
rejeita ciclos. Conexões adicionais com legenda relacionam tópicos fora da árvore.

Arraste tópicos para posicioná-los. Arraste uma área vazia para navegar, use os
controles de zoom ou a roda e escolha **Ajustar mapa** para enquadrar o grafo.
Desfazer/refazer operam sobre o rascunho local. **Salvar mapa mental** envia o
grafo com a versão esperada. Fechar um grafo alterado pergunta se deseja descartar
o rascunho usando a modal nativa. Conflitos preservam o rascunho e oferecem uma
recarga explícita do mapa salvo, sem sobrescrever a versão de outro editor.

O diretório é compartilhado entre as telas; navegação e zoom pertencem ao editor
aberto. O gestor de campanha continua exclusivo dos mestres; jogadores
autorizados usam o editor da mesa.

## Vínculos com recursos

**Vincular recurso da campanha** pesquisa recursos nativos autorizados. Vínculos
guardam identidades tipadas, sem copiar documentos ou conceder acesso.
O catálogo contempla estes 37 tipos:

| Domínio | Destinos dos vínculos |
| --- | --- |
| Personagens | Atores, arquivos acessíveis incluindo fontes PDF e pastas de personagens |
| Itens | Itens e pastas |
| Diários | Diários, missões, quadros de missões, tabelas de rolagem, páginas legíveis, anexos, pastas e entradas dos quadros |
| Cenas | Cenas, pastas, objetos nativos, blocos de imagem, desenhos, tokens e encontros |
| Biblioteca | Imagens de mapas e pastas de arquivos |
| Progresso | Relógios e pistas descobertas, conforme a visibilidade nativa |
| Áudio | Faixas e listas de reprodução |
| Cartas | Baralhos, cartas individuais, definições e imagens de cartas |
| Compêndios | Pacotes e entradas de campanha/instalados, além de anexos nativos das entradas |
| Preparação | Planos de sessão e eventos da linha do tempo |
| Autoria | Projetos do MapBuilder, modelos de comportamento e modelos de mapeamento PDF |
| Outros | Mensagens visíveis do chat e outros mapas mentais |

Objetos de cena incluem paredes/portas, luzes, imagens e controladores,
partículas, shaders, marcadores, pinos de diário, sons espaciais e zonas. Cada
tipo segue sua projeção nativa: camadas do mestre, barreiras secretas, páginas
privadas, pistas não reveladas e cartas indisponíveis para o leitor não passam
a aparecer no catálogo. Arquivos internos de pacotes sem entidade nativa da
campanha não são destinos separados. A busca do chat segue a janela recente
nativa; um vínculo existente ainda resolve mensagens antigas se houver acesso.

Abrir um vínculo verifica novamente a permissão atual. Destinos ausentes e
negados usam o mesmo estado neutro; IDs, nomes e URLs ocultos não chegam ao
jogador. Editar outro tópico preserva esse vínculo por um marcador opaco.
Remover o vínculo o retira do grafo. O texto autoral dos tópicos pertence ao
público do mapa inteiro: escreva notas privadas em um mapa privado.

## Colaboração e permissões

Somente mestres da campanha criam/excluem mapas, alteram seu escopo, configuram
visibilidade e concedem edição. **Visível para jogadores** permite leitura;
jogadores selecionados como editores também podem ler e alterar um mapa privado.
Todos os mestres podem editar. Um jogador autorizado renomeia o mapa e altera
seu grafo, mas não muda a lista de acesso. Streamers sempre têm somente leitura.
Escopo de cena também exige acesso nativo àquela cena, mesmo para um editor.

Clientes da mesa recebem invalidações após a confirmação e releem sua própria
projeção. O gestor atualiza por seu ciclo HTTP existente. Alterações de permissão
são verificadas nas leituras, gravações e repetições de recibos. Um editor
revogado não continua gravando nem recupera dados privados por um recibo antigo.

## MapBuilder

Objetos inteligentes oferecem dois nós:

| Nó | Comportamento |
| --- | --- |
| **Abrir mapa mental** (`openMindMap`) | Abre um mapa autorizado, opcionalmente focado em um tópico, para quem acionou, jogadores ou usuários selecionados |
| **Controlar tópico do mapa mental** (`mindMapNode`) | Conclui, reinicia ou alterna a conclusão do tópico configurado |

Os vínculos devem pertencer à campanha, com escopo global ou da cena atual.
Um controle escrito pelo mestre delega apenas aquele efeito pelo serviço nativo
e exige um mestre ativo na campanha; não concede edição geral ao jogador.
Abrir não ignora permissões dos destinatários. Destinos excluídos continuam
como vínculos reparáveis. A simulação descreve o efeito; o ensaio no servidor
reverte dados, recibos e notificações. Execuções adiadas verificam os destinos.

## Armazenamento, limites e APIs

Uma campanha comporta 64 mapas. Cada grafo admite 500 tópicos, 1.000 conexões
adicionais, 16 vínculos por tópico, 2.048 vínculos no total e 1 MiB de JSON.
Títulos e legendas têm até 240 caracteres; notas, 8.000; coordenadas, ±100.000.
IDs são UUIDs; referências também aceitam identidades numéricas e compostas
nativas por meio do tipo registrado.

Cópias/exportações de campanha selecionam **Mapas mentais** separadamente.
Omitir cenas também omite mapas com escopo de cena. Vínculos tipados apontam
para os recursos copiados; destinos excluídos ficam inertes e texto autoral/IDs
locais de tópicos permanecem exatos. Arquivos portáteis limpam concessões de
edição da origem; snapshots restauram concessões na mesma campanha. Um arquivo
de campanha não substitui um backup da instalação.

Python expõe `api.mindmaps.state`, `read`, `resources`, `resolve` e `command`.
O navegador expõe as mesmas leituras, além de `create`, `update`, `node`, `delete`,
`list`, `get` e `mindmaps.changed`. Veja a [API](api.md) para payloads,
UUIDs de operação e versões obrigatórias. Aplique a migração
[`0005_mind_maps`](../../gravewright/table/migrations/0005_mind_maps.py) antes de
iniciar este código em uma instalação existente.
