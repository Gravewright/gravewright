# Gravewright PDF System

Usa um PDF como ficha de personagem. Inspirado no módulo **PDF Sheets** do Foundry
VTT, mas com uma diferença central de arquitetura.

## O modelo: o PDF é a aparência, não o depósito

O módulo do Foundry salva o **PDF binário preenchido** por ator (`ficha.pdf` vira
`ficha-ActorID.pdf`). Aqui não.

Aqui cada campo do PDF é ligado a um **caminho de dado** pelo mapeamento, e o valor
vive em `scoped-json-v1` (SQLite) como qualquer outra ficha:

```text
campo "HP" do PDF  →  mappings/pdf-fields.gw.json  →  sheet.hp.value
                                                          │
                                    mappings/token.gw.json ┘
                                                          ▼
                                              barra de HP do token
```

Três motivos para isso, nesta ordem:

1. **Pacotes SDK não escrevem binário.** O modelo de storage é JSON; a rota que o
   Foundry usa (`FilePicker.upload`) não existe na Gravewright.
2. **Dado dentro de PDF é opaco.** Ninguém além do visualizador lê um campo. Com
   caminhos, rolagem, barra de token e combate leem o mesmo valor.
3. **Um template serve todos.** Sem cópia por ator, e atualizar o template não
   invalida as fichas existentes.

O preço: quem preencher o PDF por fora e subir o arquivo não vê os dados migrarem
sozinhos. Os valores são da ficha, não do arquivo.

## Arquivos

| Arquivo | Responsabilidade |
|---|---|
| `manifest.json` | Identidade, capabilities e **toda** a lista de arquivos servíveis. |
| `mappings/pdf-fields.gw.json` | Campo do PDF → caminho de dado. O coração do sistema. |
| `mappings/token.gw.json` | Onde a barra do token lê. Aponta para os mesmos caminhos. |
| `schemas/actors/character.schema.json` | Forma do dado. Caminho fora daqui é descartado na escrita. |
| `sheets/character.html` | Barra de controles + palco do PDF + camada de campos. |
| `scripts/pdf-sheet.js` | Cria os campos a partir do mapeamento, já com `data-bind`. Não grava: quem grava é o host. |
| `scripts/pdf-viewer.js` | Desenha a página com pdf.js e diz onde cada campo está na tela. |
| `vendor/pdf.mjs`, `vendor/pdf.worker.mjs` | Runtime do pdf.js, build **legacy**. Asset, não entrypoint. |
| `assets/sheets/blank-a4.pdf` | Página de aviso: explica como enviar a sua própria ficha. Sem campos, de propósito. |

## Como se encaixa no SDK

A ficha é `mode: "html"`. O host carrega `sheets/character.html`, chama o
controlador registrado por `sdk.sheets.registerController` e **depois** liga os
atributos que conhece: `data-bind` (valor ↔ caminho), `data-action` (botão) e
`data-text` (caminho de dado — *não* chave de tradução; rótulo se traduz no
controlador, via `sdk.i18n.t`).

PDFs enviados para a biblioteca são resolvidos por `sdk.pdf.get` e abertos por
`sdk.pdf.viewer.open`. Assim, o ruleset não contorna os gates de capability e de
visibilidade do SDK 1. Apenas o template PDF empacotado usa diretamente o
adaptador local, pois ele é um asset imutável do próprio pacote e não um
documento da campanha.

O controlador não grava. Ele cria os campos a partir do mapeamento já com
`data-bind`, e o host persiste pelo mesmo caminho de qualquer outra ficha. Um
segundo caminho de escrita só produziria divergência.

Dois vocabulários de caminho convivem, e é bom saber por quê:

| Onde | Forma | Exemplo |
|---|---|---|
| Mapeamento e `token.gw.json` | canônica do servidor | `sheet.hp.value`, `core.name` |
| `data-bind` no DOM | a que `ctx.data` expõe | `system.hp.value`, `actor.name` |

O mapeamento guarda a canônica porque o token lê dela. A conversão para a forma
de binding mora numa função só (`bindingPath`), e o host reconverte na escrita.

`data-action` tem duas saídas: o controlador do pacote e, se ele não reivindicar,
a ação server-side do ruleset. **Devolver `true` reivindica.** Todos os botões
daqui são de cliente puro — virar página não é regra de sistema —, então todos
devolvem `true`; `default` devolve `false` para não engolir o que é do servidor.

Como o controlador precisa buscar o mapeamento e o pdf.js antes de existir campo
algum, e o host não espera por `mount`, o trabalho assíncrono termina chamando
`GravewrightHTMLSheets.update(root, ctx.data)` — que devolve a ligação dos campos
recém-criados ao host.

## As três abas

| Aba | O que tem |
|---|---|
| **Ficha** | O PDF com os campos por cima. |
| **Token** | Imagem do token e qual campo alimenta cada barra. |
| **Notas** | Biografia, história e anotações. |

O host liga as abas sozinho — `[role="tablist"]` com filhos `[data-tab]` e painéis
irmãos `[data-tab-panel]` de mesmo nome. O pacote só declara a forma.

### Imagem do token

O slot `data-actor-image="token"` recebe **o mesmo quadro de upload da ficha
nativa**. Upload de imagem carrega CSRF, transmissão para a sala e recálculo dos
tokens da cena; um pacote reimplementando isso erraria algum dos três. Uma ficha
HTML substitui a raiz inteira e por isso não herda o cabeçalho onde esse quadro
vive — o slot é a ponte.

### Qual campo alimenta a barra

`token.gw.json` resolve caminhos **fixos** (`sheet.hp.value`), e é do sistema, não
do ator. Então a escolha por personagem não muda o mapeamento: muda **para onde o
campo do PDF grava**. Escolher "Vigor" como PV faz o input de Vigor gravar direto
em `sheet.hp.value`.

Um valor, um lugar. Espelhar de `sheet.fields.Vigor` para `sheet.hp.value` seria
uma segunda escrita, e duas escritas divergem.

O preço: trocar a escolha depois deixa o valor antigo no caminho antigo. A escolha
mora em `sheet.token.bars.<slot>` e guarda o **nome** do campo.

## Usando o seu próprio PDF (sem editar nada)

1. Envie o PDF para a **biblioteca de assets** da campanha, do mesmo jeito que uma
   imagem.
2. Abra a ficha e clique no botão PDF. Seu arquivo aparece na lista, junto dos
   templates do pacote.
3. Pronto. Os campos aparecem sobre a página e já gravam.

**Por que funciona sem mapeamento:** os nomes de campo vêm do próprio PDF
(`getAnnotations`), e cada um cai em `sheet.fields.<nome>` — que o schema deixa
aberto de propósito. Nome conhecido (`HP`, `AC`, `CharacterName`…) reaproveita o
caminho canônico do template `generic`, e é só por isso que a barra do token
funciona num PDF que ninguém mapeou.

Nome de campo vira segmento de caminho, então caracteres fora de `[A-Za-z0-9_-]`
viram `_`. Sem isso, um campo `Ataque.Bônus` abriria um objeto aninhado por
acidente e o valor sumiria do lugar esperado.

O que ganha ao mapear à mão (fluxo de "Usando o seu PDF", abaixo): endereçar o
campo por regra, rolagem e barra de token com um caminho estável.

### Duas origens, exclusivas

`sheet.pdf.asset` (envio do GM) ganha de `sheet.pdf.template` (template do pacote).
Escolher um limpa o outro — senão um envio antigo continuaria ganhando do template
recém-escolhido. Se o arquivo for apagado da biblioteca, a ficha cai de volta no
template em vez de abrir vazia.

## Usando o seu PDF

1. Coloque o arquivo em `assets/sheets/`.
2. **Declare em `provides.assets.sheets`** no manifest. Sem isso o servidor devolve
   404 — o manifest é quem autoriza servir, não o mapeamento.
3. Adicione uma entrada em `templates` no mapeamento, ligando cada campo a um
   caminho.
4. Caminho em `sheet.*` precisa existir no schema. Campo sem entrada no mapeamento
   cai em `sheet.fields.<nome>` e funciona — só não é endereçável por regra.

`tests/unit/test_gravewright_pdf_system_package.py` verifica os quatro passos.

## A renderização

O pdf.js vive em `vendor/`, dentro do pacote. `scripts/pdf-viewer.js`
desenha a página e, para cada campo, devolve onde ele está na tela.

**As coordenadas vêm do PDF, não do mapeamento.** O visualizador lê
`page.getAnnotations()` e usa `convertToViewportRectangle` para converter o
retângulo do campo (origem embaixo à esquerda, no PDF) para a tela. Por isso o
mapeamento fala só de *nomes* — trocar o template não obriga a medir nada com
régua, e um teste recusa mapeamento que carregue coordenadas.

### Por que o build `legacy` do pdf.js

O `vendor/` traz o build **legacy**, não o moderno. O moderno usa APIs que nem
todo navegador tem:

| API | Onde o pdf.js usa | Disponibilidade |
|---|---|---|
| `Map.prototype.getOrInsertComputed` | resolve recursos de **formulário** | Firefox sim, Chrome ainda não |
| `Uint8Array.prototype.toHex` | **descriptografia** | Chrome 140+ |
| `Uint8Array.fromBase64` | assinaturas, fontes embutidas | Chrome 140+ |

Repare onde ficam: formulário e descriptografia — exatamente por onde passa uma
ficha de RPG preenchível, que ainda por cima costuma vir protegida por senha de
dono. Com o build moderno o documento **nem abre** num navegador um pouco atrás:
`getDocument` rejeita com um TypeError sobre uma função inexistente, e a ficha só
diz "não foi possível abrir o PDF", sem indicar que o problema é o navegador.

O legacy carrega os próprios polyfills (core-js), inclusive dentro do worker, que
roda em contexto separado. Por isso não há nada de nosso nesse caminho.

Trocar de volta pelo moderno é uma regressão silenciosa: passa em qualquer máquina
de desenvolvimento atual e quebra na mão de quem joga.
`tests/js/pdf_compat_harness.js` roda o pdf.js vendorizado num Node que não tem
nenhuma das três APIs — espelho de um navegador atrasado — e falha na hora se o
build errado entrar.

Dois cuidados que valem lembrar antes de mexer:

- **O runtime é asset, não entrypoint.** `pdf.mjs` + worker somam 3 MB. Como
  entrypoint entrariam no carregamento da página de jogo de todo mundo, inclusive
  de quem nunca abre uma ficha. São importados por `import()` na primeira ficha
  aberta, uma vez por sessão.
- **`workerSrc` precisa ser explícito.** O padrão do pdf.js é procurar um irmão
  `./pdf.worker.mjs` relativo à página, que aqui não existe. O caminho é resolvido
  por `sdk.package.assetUrl`, o mesmo resolvedor que serve o template — o
  visualizador o recebe no `open()` em vez de remontar a URL por conta própria.

O adaptador continua opcional: sem `window.GravewrightPdfViewer` a ficha abre com
os campos empilhados numa coluna legível e **grava normalmente**, só sem a página
desenhada atrás. É o que garante que o sistema seja de dados, não de arquivo.

`tests/js/pdf_viewer_harness.js` roda o visualizador contra um pdf.js falso e
confere o que quebra calado: inversão do eixo Y, escala no zoom, campo de outra
página escondido, e o deslocamento vertical em página dupla.
