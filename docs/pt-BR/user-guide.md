# Usando o Gravewright

[Documentação](../README.pt-BR.md) · [English](../en/user-guide.md)

## Contas e campanhas

Crie o primeiro proprietário em `/setup` e entre por `/login`. Outros usuários se cadastram em `/register`. O proprietário administra a instância e cria campanhas em `/inside`. A campanha também aparece como `container` nas rotas HTTP e `table` nas interfaces do navegador/tempo real.

O sistema nativo é **Gravewright PDF System**, com atores `character`. Convide jogadores usando o código da campanha; o mestre da campanha configura validade e máximo de usos e pode revogar códigos. Entradas bem-sucedidas de novos membros incrementam automaticamente o contador de usos. O vínculo permite acessar a campanha, enquanto permissões de documentos e cenas definem o que pode ser visto ou alterado. Um link de transmissão oferece acesso restrito de leitura e não equivale a uma conta de jogador.

## Preparar a mesa

1. Crie uma campanha e abra sua mesa.
2. Crie/importe uma cena de mapa e configure grade, visão inicial e visibilidade. A cena precisa estar visível aos jogadores e em transmissão ativa para que eles a acessem.
3. Crie atores, anexe fichas PDF quando necessário e coloque seus tokens na cena. Dados do ator e estado do token são relacionados, mas distintos; o token representa o ator em um mapa específico.
4. Prepare diários, materiais e recursos, concedendo acesso intencionalmente. Confira em uma sessão separada de jogador antes de compartilhar.
5. Convide os jogadores, use controles de lobby/prontidão quando habilitados e transmita a cena desejada.

As ferramentas incluem seleção, movimento, desenho, medição, paredes, neblina, iluminação, pings e efeitos. Permissões e ferramenta ativa determinam as ações disponíveis. O mestre pode preparar material oculto sem transmiti-lo. A renderização depende do WebGL do navegador e da complexidade da cena.

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
- Marketplace online e descoberta de releases precisam de configuração do operador. Descoberta de atualização do núcleo não instala versões automaticamente.

Para desenvolvimento ou integrações, continue nos guias de [API](api.md) e [módulos](modules.md).
