# Fichas HTML

> **Status: estável.** `sheets.html`, `sheets.controller` e
> `sheets.richText` fazem parte do contrato da SDK 1.

Fichas HTML permitem que um ruleset forneça uma interface personalizada para
atores ou itens, mantendo armazenamento, permissões, assets e identidade do
pacote sob controle do Gravewright. Uma ficha HTML substitui a Sheet IR
declarativa daquele tipo.

Este guia segue o loader, o runtime do navegador, os renderers de ator/item e as
regras de validação atuais. Ele começa com uma ficha sem JavaScript e avança até
controllers e comportamento complexo.

## Comece aqui: o modelo mental

Uma ficha HTML não é uma página web independente. Ela é uma parte de um pacote
Gravewright instalado e ativo. O Gravewright controla a janela, carrega os
arquivos, entrega os dados do ator/item ao template e decide se uma escrita é
permitida.

```text
manifest.json
    │ declara o tipo e todos os arquivos permitidos
    ▼
Gravewright abre um ator ou item
    │ lê o id do tipo correspondente, por exemplo "character"
    ▼
sheets/character.html
    │ é inserido dentro do modal de ficha do Gravewright
    ▼
data-text / data-bind / data-rich-text
    │ leem ou atualizam os dados da ficha
    ▼
Persistência e verificação de permissões do Gravewright
```

JavaScript é opcional. Adicione um controller somente quando bindings simples
não forem suficientes, por exemplo quando um botão precisar mostrar um toast ou
coordenar estado visual.

### Termos usados neste guia

| Termo | Significado em linguagem simples |
|---|---|
| Pacote | O diretório completo da extensão, com manifesto e arquivos. |
| Ruleset | O pacote que define o sistema de jogo de uma campanha. |
| Manifesto | `manifest.json`, o inventário e a declaração de permissões do pacote. |
| Ator | Uma entidade como personagem, criatura ou NPC. |
| Item | Uma entidade como arma, magia ou equipamento. |
| Tipo de ator/item | Id estável como `character` ou `weapon`, usado para escolher schema e ficha. |
| Schema | JSON Schema que descreve os campos permitidos nos dados do tipo. |
| Template | Arquivo `.html` inserido pelo Gravewright no modal da ficha. |
| Binding | Atributo `data-*` que conecta um elemento HTML aos dados da ficha. |
| Controller | JavaScript opcional que trata ciclo de vida e botões `data-action`. |
| Capability | Permissão no manifesto que declara o que o pacote pode usar. |
| Entrypoint | Lista de CSS/JS do pacote carregada na página do jogo. |

### O que você precisa antes de começar

Você precisa de um diretório de ruleset em `data/packages/rulesets/`, um
`manifest.json` válido e uma campanha onde ele possa ser ativado. Ao criar um
pacote novo, comece pelo scaffold:

```bash
grave ruleset new meu-ruleset --name "Meu Ruleset" --sheets
```

O scaffold pode criar inicialmente um arquivo Sheet IR declarativo. Este guia
substitui o valor `sheet` daquele tipo por um objeto descriptor HTML.

## 1. Estrutura do pacote

```text
data/packages/rulesets/meu-ruleset/
├── manifest.json
├── schemas/
│   └── actors/character.schema.json
├── sheets/
│   └── character.html
├── scripts/
│   └── character-sheet.js
└── styles/
    └── character-sheet.css
```

Todos os caminhos são relativos ao pacote. Caminhos que escapam do diretório,
como `../character.html`, são rejeitados.

### Responsabilidade de cada arquivo

| Arquivo | Obrigatório? | Responsabilidade |
|---|---|---|
| `manifest.json` | Sim | Declara identidade, capabilities, ids de tipo e cada arquivo que pode ser carregado. |
| `schemas/actors/character.schema.json` | Sim quando referenciado | Define formato e defaults dos dados. Não define o visual. |
| `sheets/character.html` | Sim | Define marcação, labels, inputs e botões. Não pode conter scripts. |
| `styles/character-sheet.css` | Opcional | Estiliza o template. Também precisa estar em `entrypoints.game.styles`. |
| `scripts/character-sheet.js` | Opcional | Registra pacote e controller. Também precisa estar em `entrypoints.game.scripts`. |

Crie os diretórios ausentes com:

```bash
mkdir -p data/packages/rulesets/meu-ruleset/{schemas/actors,sheets,scripts,styles}
```

### Um schema pequeno de personagem

Schema e template devem descrever os mesmos dados. Se o template usa
`system.forca`, defina `forca` no schema:

```json
{
  "$schema": "https://json-schema.org/draft/2020-12/schema",
  "type": "object",
  "title": "Personagem",
  "properties": {
    "forca": {
      "type": "integer",
      "default": 10
    },
    "biografia": {
      "type": "string",
      "default": ""
    },
    "biografiaHtml": {
      "type": "string",
      "default": ""
    }
  },
  "additionalProperties": false
}
```

## 2. Ficha mínima sem controller

O controller é opcional. Uma ficha apenas com template já pode exibir e salvar
campos por meio de `data-text`, `data-bind` e `data-rich-text`.

```json
{
  "$schema": "https://raw.githubusercontent.com/Gravewright/gravewright/main/schemas/gravewright-package-v1.schema.json",
  "schemaVersion": 1,
  "sdkVersion": "1",
  "kind": "ruleset",
  "id": "meu-ruleset",
  "name": "Meu Ruleset",
  "version": "0.1.0",
  "compatibility": {
    "minimum": "1",
    "verified": "1"
  },
  "capabilities": ["actors.register", "sheets.html", "sheets.richText", "assets.styles"],
  "activation": {
    "scope": "campaign",
    "mode": "exclusive"
  },
  "entrypoints": {
    "game": {
      "styles": ["styles/character-sheet.css"]
    }
  },
  "provides": {
    "storage": {
      "model": "scoped-json-v1"
    },
    "actorTypes": [
      {
        "id": "character",
        "label": "Personagem",
        "schema": "schemas/actors/character.schema.json",
        "sheet": {
          "mode": "html",
          "template": "sheets/character.html",
          "style": "styles/character-sheet.css"
        }
      }
    ]
  },
  "settings": [],
  "dependencies": [],
  "conflicts": []
}
```

### Campo por campo do manifesto

| Campo | Por que existe |
|---|---|
| `$schema` | Permite validação e autocomplete no editor. |
| `schemaVersion` | Seleciona o formato do manifesto. A SDK 1 usa `1`. |
| `sdkVersion` | Seleciona a linha de API usada pelo pacote. |
| `kind` | `ruleset` indica o sistema-base da campanha. |
| `id` | Id permanente. Deve combinar com diretório e registro do controller. |
| `name` | Nome legível por pessoas. |
| `version` | Versão do pacote/assets. Incremente ao publicar alterações. |
| `compatibility` | Declara as versões da SDK que o pacote suporta. |
| `capabilities` | Declara recursos e controla acesso aos métodos do SDK. |
| `activation` | Um ruleset é exclusivo e ativado por campanha. |
| `entrypoints.game.styles` | Carrega CSS na página do jogo. |
| `provides.storage` | Seleciona o modelo gerenciado de dados. |
| `provides.actorTypes` | Declara os tipos de ator do ruleset. |
| `actorTypes[].id` | Tipo armazenado no ator e usado para encontrar o controller. |
| `actorTypes[].schema` | Contrato de dados daquele tipo. |
| `actorTypes[].sheet` | Seleciona modo HTML e arquivos de template/controller/style. |

Os arrays vazios `settings`, `dependencies` e `conflicts` indicam que o pacote
mínimo ainda não declara esses recursos.

Regras importantes de carregamento:

- `sheet.template` declara e carrega o template HTML.
- `sheet.style` declara o arquivo relacionado, mas **não** injeta o CSS na
  página. Inclua-o em `entrypoints.game.styles` e declare `assets.styles`.
- `sheet.controller` declara o caminho, mas **não** executa o script. Inclua-o
  em `entrypoints.game.scripts` e declare `assets.scripts`.
- O pacote precisa estar instalado, habilitado e ativo na campanha.

### Disponibilizando o pacote mínimo

Depois de criar manifesto, schema, HTML e CSS, execute:

```bash
grave package validate data/packages/rulesets/meu-ruleset --json
grave package install meu-ruleset --yes --enable
grave campaign package activate <campaign_id> meu-ruleset
grave doctor
```

Troque `<campaign_id>` pelo id real da campanha e recarregue a página do jogo.
Ao editar um pacote já instalado, use `grave package update meu-ruleset` em vez
de instalá-lo novamente.

## 3. Bindings do template

```html
<form class="character-sheet">
  <input aria-label="Nome" data-bind="actor.name">
  <span data-text="actor.type"></span>

  <label>
    Força
    <input type="number" data-bind="system.forca">
  </label>

  <label>
    Biografia
    <textarea data-bind="system.biografia"></textarea>
  </label>

  <div data-rich-text="system.biografiaHtml"></div>
</form>
```

Leia o exemplo de cima para baixo:

1. O `<form>` é apenas semântico/container; o Gravewright cuida da persistência,
   então ele não precisa de URL em `action`.
2. `data-bind="actor.name"` preenche o input com o nome principal e salva edições
   nesse nome.
3. `data-text="actor.type"` mostra o tipo com segurança como texto simples.
4. `data-bind="system.forca"` conecta o input numérico à propriedade `forca`
   definida no schema.
5. O `<textarea>` edita uma string comum.
6. `data-rich-text` só mostra conteúdo formatado depois de passar pelo sanitizer.

Para um ator com estes dados armazenados:

```json
{
  "forca": 14,
  "biografia": "Um cavaleiro errante",
  "biografiaHtml": "<strong>Um cavaleiro errante</strong>"
}
```

`system.forca` resolve para `14`. Não adicione outro segmento `sheet` ou `data`
ao binding; o renderer já expõe os dados armazenados sob `system`.

### Raízes disponíveis

| Ficha | Identidade | Dados do sistema | Permissão |
|---|---|---|---|
| Ator | `actor.id`, `actor.name`, `actor.type` | `system.*` | `canEdit` |
| Item | `item.id`, `item.name`, `item.type` | `system.*` | `canEdit` |

O objeto de ator/item também contém os dados da ficha por compatibilidade, mas
novos templates devem usar `system.*` para dados e `actor.*`/`item.*` para a
identidade.

### Comportamento dos bindings

- `data-text="path"` lê um valor e o atribui com `textContent`.
- `data-rich-text="path"` renderiza HTML sanitizado e exige
  `sheets.richText`.
- `data-bind="path"` inicializa o `value`, escuta o evento `input`, atualiza o
  contexto local e solicita persistência pelo fluxo normal de ator/item.
- `type="number"` é convertido com `Number(value)`. Outros controles atualmente
  produzem strings.
- `actor.name`, `item.name` e `core.name` atualizam o nome principal.
  `system.x` atualiza o dado `x` da ficha.
- Os caminhos usam propriedades separadas por ponto. Índices de array e
  wildcards não fazem parte do contrato documentado.

Checkboxes não recebem coerção booleana especial no modo HTML atual. Use um
controller ou uma representação string/número suportada quando precisar de um
booleano real.

`canEdit` é contexto, não uma permissão client-side. O servidor continua
autoritativo e pode rejeitar escritas. O controller pode desabilitar controles
quando `ctx.data.canEdit` for falso, mas nunca deve tratar o DOM como segurança.

## 4. Adicionando CSS

```css
.character-sheet {
  display: grid;
  gap: 1rem;
  padding: 1rem;
}

.character-sheet input {
  width: 100%;
}
```

Restrinja seletores a uma classe raiz própria do pacote. Estilos de entrypoint
são carregados na página inteira do jogo, não somente dentro do modal da ficha.

Depois de alterar assets estáticos, incremente a `version` do pacote, execute
`grave package update` e recarregue a página para mudar as URLs versionadas.

## 5. Adicionando um controller

Declare capabilities e entrypoints:

```json
{
  "capabilities": [
    "actors.register",
    "sheets.html",
    "sheets.controller",
    "assets.scripts",
    "assets.styles",
    "assets.ui"
  ],
  "entrypoints": {
    "game": {
      "scripts": ["scripts/character-sheet.js"],
      "styles": ["styles/character-sheet.css"]
    }
  }
}
```

Declare o controller no tipo:

```json
"sheet": {
  "mode": "html",
  "template": "sheets/character.html",
  "controller": "scripts/character-sheet.js",
  "style": "styles/character-sheet.css"
}
```

Registre-o a partir do script declarado:

```js
window.GravewrightSDK.register({
  id: "meu-ruleset",

  setup(sdk) {
    sdk.sheets.registerController("character", {
      setup(ctx) {},
      mount(ctx) {},
      update(ctx) {},
      unmount(ctx) {},

      async onAction(action, ctx) {
        if (action.name === "mostrar-resumo") {
          sdk.ui.toast(`${ctx.actor.name}: ${ctx.data.system.forca}`);
        }
      },
    });
  },
});
```

Esse script realiza quatro tarefas separadas:

1. `GravewrightSDK.register` identifica qual pacote ativo é dono do código.
2. `setup(sdk)` recebe o SDK limitado pelas capabilities daquele pacote.
3. `registerController("character", ...)` conecta o comportamento ao tipo.
4. `onAction` compara `action.name` ao valor `data-action` do botão HTML.

O objeto `sdk` é escopado de propósito. Se o controller chama `sdk.ui.toast`, o
manifesto precisa incluir a capability associada (`assets.ui`). Sem ela, o
runtime gera erro em vez de conceder acesso silenciosamente.

Os dois identificadores precisam corresponder exatamente:

- `GravewrightSDK.register({ id })` deve ser igual ao `id` do manifesto.
- `registerController(sheetType, ...)` deve ser igual ao `id` do tipo de
  ator/item, como `character`. Registrar `personagem` para uma ficha
  `character` não conecta o controller.

O pacote deve declarar cada capability exigida pelos métodos SDK utilizados.

## 6. Contexto e ciclo de vida

O controller recebe:

```js
{
  packageId,
  sheetType,
  root,
  data,
  actor,     // somente em fichas de ator
  item,      // somente em fichas de item
  onChange
}
```

Para uma personagem Aria com força 14, a parte útil do contexto é conceitualmente:

```js
{
  packageId: "meu-ruleset",
  sheetType: "character",
  root: HTMLElement,
  actor: { id: "...", name: "Aria", type: "character" },
  data: {
    actor: { id: "...", name: "Aria", type: "character" },
    system: { forca: 14 },
    canEdit: true
  }
}
```

`root` é o elemento que contém esta ficha aberta. Procure elementos com
`ctx.root.querySelector(...)`, não no documento inteiro. Assim várias fichas
abertas ao mesmo tempo continuam independentes.

- `setup(ctx)` roda uma vez para o controller registrado no runtime da página.
- `mount(ctx)` roda depois que o template entra no DOM.
- `update(ctx)` roda após um `data-bind` atualizar os dados locais e quando o
  runtime HTML é atualizado explicitamente.
- `unmount(ctx)` roda antes da remoção dos listeners internos.
- `onAction(action, ctx)` trata elementos com `data-action`.

Escolha cada hook pela responsabilidade:

| Hook | Bons usos | Evite |
|---|---|---|
| `setup` | Configuração única que não pertence a um modal específico. | Ler elementos que ainda não foram montados. |
| `mount` | Inicializar widgets ou observers dentro de `ctx.root`. | Ligar listeners globais sem guardar como removê-los. |
| `update` | Atualizar estado visual calculado depois de mudar um binding. | Substituir todo `root.innerHTML`, destruindo bindings do runtime. |
| `onAction` | Tratar clique explícito vindo de `data-action`. | Comparar o objeto action inteiro com string. Use `action.name`. |
| `unmount` | Desconectar observers, timers e listeners externos. | Salvar estado de última hora que já deveria ter sido persistido. |

Listeners ligados dentro do template desaparecem quando a ficha é renderizada
novamente. Listeners em `document`, `window`, timers, observers ou objetos
externos devem ser removidos em `unmount`.

## 7. Botões e ações

```html
<button type="button" data-action="mostrar-resumo">Mostrar resumo</button>
```

O controller recebe:

```js
{
  name: "mostrar-resumo",
  event: MouseEvent,
  element: HTMLButtonElement
}
```

`data-action` apenas chama `controller.onAction`. Ele **não** executa
automaticamente uma entrada de `rules/actions.gw.json` e não faz nada quando
não há controller correspondente.

Dentro do handler, use somente métodos públicos do SDK escopado, como `sdk.ui`,
`sdk.settings`, `sdk.bus` ou `sdk.chat`, com as capabilities correspondentes.
Não use globals privados do renderer nem dependa de detalhes internos do DOM.

A Sheet IR declarativa possui execução autoritativa de actions no servidor. A
SDK atual de fichas HTML não expõe um método público
`sdk.sheets.executeAction`. Se a ficha depender de actions declarativas, use
Sheet IR naquela interação ou mantenha o controller HTML dentro das operações
públicas documentadas até que esse método exista. Não trate uma rota privada do
core como API de pacote.

## 8. Rich text e segurança

Rich text exige `sheets.richText`:

```html
<article data-rich-text="system.biografiaHtml"></article>
```

O sanitizer remove elementos perigosos como `script`, `iframe`, `object` e
`embed`, atributos de eventos e valores `javascript:`.

Templates não podem conter:

```html
<script src="..."></script>
<button onclick="rolar()">Rolar</button>
```

Scripts inline e handlers inline falham na validação. Coloque o comportamento
em um controller declarado. Somente assets declarados no manifesto são servidos;
arquivos HTML não declarados e traversal de caminhos são rejeitados.

## 9. Fichas de ator, item e token

O modo HTML funciona em entradas de `provides.actorTypes` e
`provides.itemTypes`. Use `actor.*` para identidade de ator, `item.*` para
identidade de item e `system.*` para os dados do pacote.

Fichas HTML abertas a partir de tokens não vinculados persistem no dado da ficha
do token; tokens vinculados persistem no ator. O core faz esse roteamento, então
o template deve continuar usando `system.*`, sem escolher endpoints.

O descriptor HTML suprime o layout declarativo daquele tipo. Um tipo usa um
modo por vez: objeto descriptor HTML ou string apontando para Sheet IR.

## 10. Workflow completo de validação

```bash
grave package validate data/packages/rulesets/meu-ruleset --json
grave package update meu-ruleset --json
grave package doctor meu-ruleset
grave doctor
```

Depois da instalação, ative o ruleset na campanha e recarregue `/game`. O script
do controller só é emitido para pacotes ativos.

Erros comuns:

| Erro | Causa |
|---|---|
| `sdk.sheets.html.invalid_mode` | Objeto descriptor de sheet cujo `mode` não é `html`. |
| `sdk.sheets.html.capability_missing` | Descriptor HTML sem `sheets.html`. |
| `sdk.sheets.html.template_missing` | Declaração/arquivo de template ausente. |
| `sdk.sheets.html.template_unsafe_path` | Caminho inseguro ou template sem `.html`. |
| `sdk.sheets.html.controller_missing` | Arquivo ou `sheets.controller` ausente. |
| `sdk.sheets.html.controller_unsafe_path` | Caminho inseguro do controller. |
| `sdk.sheets.html.style_missing` | Arquivo de estilo declarado não existe. |
| `sdk.sheets.html.style_unsafe_path` | Caminho inseguro do estilo. |
| `sdk.sheets.html.inline_html_forbidden` | HTML inline colocado no manifesto. |
| `sdk.sheets.html.inline_script_forbidden` | Template contém `<script>`. |
| `sdk.sheets.html.inline_handler_forbidden` | Template contém `onclick` ou similar. |
| `sdk.sheets.html.rich_text_capability_missing` | `data-rich-text` sem capability. |

## 11. Checklist de diagnóstico

Se o template não aparecer:

1. Confirme `sheet.mode: "html"` e o tipo do ator/item criado.
2. Valide o pacote e atualize o snapshot instalado.
3. Confirme que o pacote está habilitado e ativo na campanha.
4. Confirme que o template está declarado e existe.

Se os bindings não salvarem:

1. Use `actor.name`/`item.name` para nomes e `system.*` para dados.
2. Verifique `ctx.data.canEdit` e as permissões no servidor.
3. Inspecione a resposta da requisição de patch no navegador.
4. Confirme que schema e validation aceitam o valor.

Se um botão não funcionar:

1. Confirme o controller em `entrypoints.game.scripts`.
2. Confirme `assets.scripts` e `sheets.controller`.
3. Confirme os ids exatos do pacote e do `sheetType`.
4. Use `action.name`, não `action === "nome"`.
5. Confirme que o handler chama somente APIs permitidas pelas capabilities.
6. Incremente a versão, atualize o pacote e recarregue a página.

### Usando as ferramentas de desenvolvedor do navegador

Abra as ferramentas do navegador (normalmente `F12`) e use:

- **Console:** procure `GravewrightSDK.register refused`, erros de capability,
  controller duplicado ou exceções dentro de `onAction`.
- **Network:** filtre pelo id do pacote. Template, CSS e JS devem retornar HTTP
  200 em `/sdk/packages/<id>/asset/...`.
- **Network após editar um campo:** veja a requisição de patch de ator/item.
  HTTP 200 indica aceite; HTTP 400/403 costuma indicar dado inválido ou falta de
  permissão.
- **Elements:** confirme que o template está dentro da raiz da ficha e que o
  atributo `data-bind`/`data-action` esperado existe.

Sintomas úteis:

| Sintoma | Causa mais provável |
|---|---|
| Mensagem “No sheet layout” | Id de tipo diferente, pacote inativo ou descriptor HTML ausente. |
| HTML aparece sem estilo | CSS está em `sheet.style`, mas não no entrypoint do jogo. |
| HTML e CSS aparecem, botão não reage | Script não carregou ou `sheetType` não corresponde. |
| Input muda, mas volta depois | Servidor rejeitou, path/schema está errado ou usuário não pode editar. |
| Código antigo continua rodando | Versão/snapshot do pacote ou página não foi atualizado. |

## 12. Checklist de release

- Mantenha HTML, CSS, schemas e controllers dentro do pacote.
- Declare todos os caminhos e capabilities.
- Restrinja o CSS a uma classe raiz do pacote.
- Use `data-text` para texto simples e `data-rich-text` somente quando preciso.
- Mantenha regras e lógica autoritativa declarativas/no servidor quando a SDK
  oferecer um caminho público.
- Remova listeners externos em `unmount`.
- Teste permissões, tokens vinculados e não vinculados e várias fichas abertas.
- Valide, atualize, rode doctor, incremente a versão e teste após recarregar a
  página completamente.
