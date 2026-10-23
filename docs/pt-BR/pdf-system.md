# Gravewright PDF System

[Documentação](../README.pt-BR.md) · [English](../en/pdf-system.md) · [Gestão de campanha](campaign-management.md) · [Referência da API](api.md)

O PDF System incluído usa um PDF enviado ou um modelo incluído como ficha de
personagem. Campos nativos do PDF e campos desenhados manualmente compartilham
valores, barras de tokens e ações de rolagem salvas. As mesmas fichas dos atores
estão disponíveis na mesa e em **Gerenciar campanha → Personagens**.

## Mapear um PDF sem campos editáveis

1. Abra a ficha do ator como mestre da campanha e selecione seu PDF.
2. Escolha **Mapear campos** e o tipo: texto, número, checkbox ou texto multilinha.
3. Desenhe um retângulo sobre a área desejada da página. **Adicionar campo**
   também cria um retângulo sem arrastar.
4. Nomeie o campo e ajuste seus limites. Arraste para mover ou use a alça no canto
   inferior direito para redimensionar. As setas movem um pixel exibido; Shift
   move dez.
5. Escolha **Concluir mapeamento** para preencher os campos. As alterações são
   salvas pelo fluxo normal da ficha.

Os retângulos usam coordenadas relativas à página e acompanham zoom e navegação.
O mestre configura o layout; participantes com permissão de edição preenchem os
valores. Os campos nativos do PDF continuam disponíveis. Remover um retângulo
preserva seu valor armazenado. O PDF original permanece intacto.

Use Shift/Ctrl-clique ou um retângulo de seleção para selecionar vários campos.
**Ferramentas de disposição** oferece copiar/colar, duplicação, alinhamento,
distribuição e encaixe opcional em uma grade de cinco pontos. Ctrl+C/V/D e
Ctrl+Z/Shift+Z oferecem atalhos de área de transferência e histórico. O histórico
mantém 50 etapas do layout do PDF ativo e preserva os valores atuais ao desfazer.
Trocar de documento limpa esse histórico de layout.

## Ações dos campos, barras e fórmulas

Como mestre, dê dois cliques em um campo nativo ou manual, ou foque-o e pressione
F2, para abrir **Ações do campo**. Selecione um valor de token, configure rótulo e
fórmula de rolagem ou escolha um preset. Os seis presets são d20, maior ou menor
de dois d20, 2d6, d6 explosivo e 4dF. Campos de número e texto de uma linha podem
alimentar barras dos tokens. Alterar um vínculo preserva seu valor atual.

| Fórmula | Significado |
| --- | --- |
| `1d20 + @value` | Rolar usando o valor numérico atual deste campo |
| `2d6` | Rolar sem ler o valor do campo |
| `1d20 + @{field-key}` | Ler o valor numérico de outro campo mapeado |

Use **Campo de referência** para inserir a chave exata de um campo existente.
Chaves manuais permanecem estáveis ao renomear campos. Nomes nativos com chaves
ou barras invertidas são escapados pelo seletor. Valores vazios equivalem a zero;
checkboxes equivalem a zero ou um. Outros valores não numéricos impedem a
rolagem. Consulte a [notação de dados](../../gravewright/dice/grammar/notation/GRAMMAR.pt-BR.md)
para as expressões de rolagem aceitas.

Salvar uma ação valida sua fórmula sem rolar dados. Editores autorizados executam
ações salvas pelos botões acima do PDF ou com Alt+Enter em um campo focado.
Jogadores também podem dar dois cliques em campos configurados. Para o mestre,
dois cliques abrem a configuração; **Rolar ação salva** executa a ação já salva.
Resultados usam visibilidade, contexto de cena e recibos de repetição nativos de
dados/chat.

**Fórmula do valor calculado** usa aritmética determinística, comparações e funções
numéricas com referências `@{field-key}`. Campos calculados são somente leitura.
O servidor os recalcula na ordem de dependências ao salvar e rejeita ciclos,
inclusive por aliases das barras. Se um cálculo falhar temporariamente, o último
resultado canônico fica disponível e o diagnóstico explica o problema. Limpe a
fórmula para voltar à edição comum do campo.

## Reutilizar mapeamentos

**Biblioteca de mapeamentos** permite aos mestres salvar ou substituir um modelo,
aplicá-lo à ficha atual ou a atores selecionados e importar/exportar JSON
versionado. Mapeamentos contêm retângulos, ações, cálculos, vínculos de campos e
barras e metadados opcionais do documento. Não contêm o PDF, valores de personagens
ou mídia.

Aplique um modelo ao mesmo layout de PDF. Os valores são preservados pela
identidade do campo e pelas barras canônicas, sem mesclar por rótulos visíveis.
A aplicação em lote valida as revisões de todos os destinos antes de confirmar
qualquer mudança. Atualizar um modelo não altera automaticamente as fichas que
usaram a definição anterior.

Fichas de atores e cópias independentes dos tokens têm estado separado. Aplicar
um modelo ao ator não reescreve suas cópias independentes; uma cópia aberta deve
ser selecionada explicitamente. O JSON de mapeamento não autoriza redistribuir o
PDF de origem ou seu conteúdo. Arquivos de campanha preservam a biblioteca.

## Diagnosticar e exportar

**Diagnóstico do mapeamento de PDF** aponta campos/referências ausentes, problemas
de cálculo, páginas ausentes e diferenças em relação a dimensões, rotação ou
impressão do documento salvas. Ele permite navegar até campos ainda presentes.
O painel de preparação também informa PDFs não selecionados e problemas de
cálculo salvos; a geometria real das páginas é conferida ao abrir a ficha.

**PDF preenchido** renderiza todas as páginas e seus valores atuais em uma cópia
PDF achatada a 144 dpi. Inclui campos manuais e campos nativos repetidos, sem
campos editáveis ou conteúdo PDF executável. O download do original continua
disponível separadamente. A exportação falha em vez de cortar texto excedente ou
entregar um documento incompleto. Fechar a ficha ou trocar seu PDF cancela a
operação.

## Limites e integração

| Recurso | Limite |
| --- | --- |
| Campos manuais / ações de rolagem / campos calculados | 256 de cada por ficha, somando as origens PDF |
| Vínculos de campos | 1.024 por ficha |
| Fórmula de rolagem / rótulo | 512 / 48 caracteres |
| Modelos de mapeamento | 128 por campanha |
| Importação JSON / aplicação em lote | 1 MB / 100 atores |
| PDF preenchido | 100 páginas, 16 milhões de pixels por página, 128 milhões por operação, saída de 100 MB |

Toda escrita revalida participação, permissões da ficha, identidade da origem e
revisões. Após um conflito, confira o estado atual antes de salvar; reutilize o
UUID da operação somente ao repetir a mesma operação. Layouts e modelos exigem
um mestre. Streamers continuam somente leitura. Textos dos controles do host
passam pelo Translator; nomes, fórmulas e conteúdo autorais mantêm sua redação.

Integrações de navegador descobrem o sistema com `await api.system.state()` e
chamam suas operações `pdf.*` por `api.system.call()`. Integrações Python usam
a fachada pública `api.pdf_system` ou o dispatcher `api.systems`. Veja os payloads, contextos de
token, revisões, modelos e diagnósticos no [guia da API](api.md). Inspeção do PDF,
renderização achatada e histórico de layout executam no navegador; diagnósticos
do servidor inspecionam mapeamentos armazenados e um descritor observado opcional,
sem analisar os bytes do PDF. Os pontos de implementação e verificação estão em
[Arquitetura do frontend](frontend.md) e [Testes](testing.md).
