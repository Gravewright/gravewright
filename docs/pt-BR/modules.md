# Desenvolvimento e operação de módulos

[Índice da documentação](../README.pt-BR.md) · [English](../en/modules.md) · [Referência da API](api.md)

O Gravewright instala pacotes ZIP assinados com JavaScript para o navegador, arquivos auxiliares e um manifesto JSON. O proprietário do servidor instala versões; o mestre da campanha escolhe versões exatas e substituições da interface para uma mesa. A instalação não importa Python do pacote nem inicia seus executáveis.

A licença de módulos de terceiros está descrita na [política de licenciamento](../../LICENSING.pt-BR.md). O manifesto registra a licença escolhida pelo autor; a instalação não a altera.

## Confiança e limites da instalação

Módulos instalados executam como módulos ES na página principal da aplicação. Não há sandbox de iframe, Shadow DOM nem isolamento JavaScript por capacidades. O código pode interagir com a página e o ambiente do navegador. A assinatura autentica o publicador configurado e os bytes do arquivo; não comprova que o código é seguro. Configure chaves de publicadores cujo código você aceita executar nas sessões dos usuários.

As interfaces suportadas verificam no servidor a participação do usuário autenticado na campanha, as permissões dos recursos, a revisão de ativação e o vínculo temporário de montagem, chamado de lease. Esse mecanismo não oferece execução Python, SQL nem carregamento de serviços no servidor. Integrações instaladas separadamente como código Django/Python são código confiável do servidor; veja a [API Python](api.md#interface-python).

Pontos de entrada da implementação:

| Arquivo | Responsabilidade |
| --- | --- |
| [`packages.py`](../../gravewright/modules/packages.py) | Assinaturas, validação ZIP, instalação imutável, revisões e armazenamento JSON |
| [`models.py`](../../gravewright/modules/models.py) | Versões instaladas, ativação por mesa, valores e leases |
| [`views.py`](../../gravewright/modules/views.py) | Rotas de proprietário/mestre, downloads, contexto, arquivos e chamadas validadas |
| [`frontend.py`](../../gravewright/modules/frontend.py) | API de domínio compartilhada e despacho autenticado |
| [`module-runtime.js`](../../gravewright/modules/static/gravewright_modules/module-runtime.js) | Importação, start/register/stop, montagem, substituição e limpeza |
| [`browser-bridge.js`](../../gravewright/modules/static/gravewright_modules/browser-bridge.js) | Arquivos, armazenamento, operações com lease e API de domínio |
| [`workspace.js`](../../gravewright/modules/static/gravewright_modules/workspace.js) | Conexão com as superfícies da mesa e reconciliação da ativação |

## Pacote mínimo para o navegador

Crie esta pasta fora da árvore de fontes ou em um diretório de desenvolvimento ignorado pelo Git:

```text
example.actor-counter/
├── manifest.json
├── main.js
├── styles.css
└── LICENSE.txt
```

`manifest.json`:

```json
{
  "id": "example.actor-counter",
  "name": "Actor counter",
  "version": "1.0.0",
  "sdk": { "requires": ">=1.0.0 <2.0.0", "tested": "1.0.0" },
  "entry": "main.js",
  "description": "Shows the number of actors visible to the current user.",
  "author": "Your name",
  "license": "GPL-3.0-only"
}
```

Escolha sua licença real e inclua seu texto em `LICENSE.txt`. A licença da extensão não precisa corresponder ao valor ilustrativo acima; consulte a política de licenciamento. O schema rejeita campos desconhecidos e exige todos os campos mostrados. IDs precisam de pelo menos um ponto ou hífen, começar com letra minúscula e usar letras minúsculas/dígitos em seus componentes. Versões possuem três números, sem sufixos de pré-lançamento/build. Intervalos do SDK aceitam comparações separadas por espaços, como `>=1.0.0 <2.0.0`; não aceitam `^`, `~`, curingas ou `||`. O carregador verifica o SDK **1.0.0**; a API de domínio separada informa **1.1.0**.

`main.js`:

```javascript
export default {
  start({ styles }) {
    styles.use("styles.css");
  },

  register({ register }) {
    register("actor.directory", async ({ root, api, signal }) => {
      const label = root.ownerDocument.createElement("p");
      label.className = "example-actor-counter";
      root.append(label);

      const render = actors => {
        if (!signal.aborted) label.textContent = `Atores visíveis: ${actors.length}`;
      };

      render(await api.actors.list());
      api.events.on("actors.changed", snapshot => render(snapshot.actors));
    });
  },

  stop() {
    // O host remove estilos, raízes, assinaturas de eventos e referências de API.
  }
};
```

`styles.css`:

```css
.gw-module-root[data-module-id="example.actor-counter"] .example-actor-counter {
  margin: 0.5rem;
  font-weight: 600;
}
```

Crie o ZIP com os arquivos na raiz, sem uma pasta extra envolvendo o pacote:

```sh
cd example.actor-counter
python -m zipfile -c ../actor-counter-1.0.0.zip manifest.json main.js styles.css LICENSE.txt
```

O pacote está pronto para assinatura. Este repositório não possui endpoint para envio de pacotes sem assinatura nem servidor de desenvolvimento de módulos com recarga automática. Os [testes de módulos](../../gravewright/modules/tests.py) e a [fixture de integração no navegador](../../tests/e2e/frontend_api.py) mostram assinatura/instalação em ambientes isolados.

## Declarar um sistema instalado

Um pacote também pode fornecer um sistema de campanha adicionando `system` ao manifesto:

```json
"system": {
  "actorTypes": [
    { "id": "character", "label": "Personagem" },
    { "id": "npc", "label": "Personagem do mestre" }
  ],
  "itemTypes": [{ "id": "gear", "label": "Equipamento" }]
}
```

O ID e o título do sistema vêm de `id` e `name` do pacote. Cada pacote declara um sistema e não pode substituir `gravewright-pdf-system`. Declare pelo menos um tipo de ator; tipos de itens são opcionais. Os IDs dos tipos devem ser únicos em cada lista, começar com letra minúscula e conter apenas letras minúsculas, dígitos, sublinhados ou hífens (máximo de 80 caracteres). Cada lista aceita até 64 entradas, com rótulos de 1–120 caracteres.

Após a instalação assinada, o sistema aparece em Systems, `/api/rulesets` e no formulário de campanha. O catálogo usa a versão instalada compatível e não revogada mais recente de cada pacote, comparando os números da versão. Módulos comuns sem `system` continuam disponíveis em Installed modules. Campanhas existentes podem manter um sistema indisponível ao editar seus detalhes, mas ele não pode ser escolhido para uma nova campanha.

Salvar uma mesa com um sistema instalado seleciona seus tipos e ativa seu pacote de interface. A versão exata já ativa é preservada; trocar o sistema remove o pacote anterior e mantém os demais módulos e preferências de interface. A mesa usa os tipos da versão exata ativada, ou da versão instalada mais recente quando nenhuma está ativada. Os dados dos atores mantêm a estrutura nativa existente; dados específicos do módulo usam as APIs de documentos e armazenamento de módulos. Instalar outra versão não muda automaticamente a versão ativada na mesa.

## Catálogo assinado e ativação

O marketplace usa o catálogo do publicador configurado pelo proprietário do host; não há feed público embutido. Módulos instalados são carregados de `/api/module-packages` independentemente do catálogo remoto e de sua configuração. Atualizar o marketplace descarta os resultados remotos anteriores antes de carregar o catálogo atual e consulta novamente os pacotes instalados após revogações assinadas ou instalação.

`GET /api/marketplace/status`, exclusivo do proprietário, verifica a configuração local sem contatar o publicador nem gravar arquivos de pacotes. Retorna HTTP 200 com `catalogConfigured`, `trustedKeysConfigured`, `ready`, `sdk` e `errors` (lista de `{field, code}`, com `field` igual a `catalog` ou `keys`). Os booleanos indicam configuração local válida, não disponibilidade do publicador. `ready` só é verdadeiro quando a URL HTTPS é válida e o arquivo de confiança contém ao menos uma chave válida. Falhas de configuração retornam HTTP 503 nas consultas ao catálogo e nas instalações, com `{ "error": "<code>" }`:

| Código | Ação do proprietário |
| --- | --- |
| `marketplace_catalog_missing` | Configure a URL HTTPS do catálogo JSON do publicador. |
| `marketplace_catalog_invalid` | Corrija a URL; credenciais, portas inválidas e fragmentos são rejeitados. |
| `marketplace_keys_missing` | Configure o caminho do arquivo de chaves públicas confiáveis. |
| `marketplace_keys_unreadable` | Verifique se o arquivo existe e se o servidor pode lê-lo. |
| `marketplace_keys_invalid` | Corrija o objeto JSON, os IDs ou as chaves públicas Ed25519 em base64. |
| `marketplace_keys_empty` | Adicione ao menos uma chave de publicador confiável. |

Reinicie o host após alterar variáveis de ambiente; edições no arquivo de chaves configurado são lidas na próxima requisição. Falha de rede/publicador continua como `unavailable` (503), dados inválidos de catálogo/pacote como `invalid_data` (400), e assinaturas inválidas ou não confiáveis como `permission_denied` (403). Falhas na configuração de confiança nunca desabilitam a verificação de assinaturas.

Configure `GRAVEWRIGHT_MARKETPLACE_URL` com a URL HTTPS de um catálogo JSON e `GRAVEWRIGHT_MARKETPLACE_KEYS_FILE` com um arquivo JSON no formato `{ "id-da-chave": "chave-publica-Ed25519-de-32-bytes-em-base64" }`. Mantenha chaves privadas fora dos pacotes distribuídos e catálogos públicos. O catálogo é uma lista de registros:

```json
[
  {
    "id": "example.actor-counter",
    "version": "1.0.0",
    "sdk": ">=1.0.0 <2.0.0",
    "download": "https://your-publisher.example/actor-counter-1.0.0.zip",
    "sha256": "<64 caracteres hexadecimais minusculos>",
    "keyId": "publisher-key",
    "signature": "<assinatura Ed25519 em base64>"
  }
]
```

Substitua os exemplos por valores reais. A assinatura abrange todos os campos exceto `signature`, inclusive `status` quando presente, serializados com chaves ordenadas, separadores compactos, escape ASCII e sem NaN. Todos os valores do registro devem ser strings ASCII. Exemplo equivalente em código com Django inicializado:

```python
import base64
import hashlib
from gravewright.modules.packages import canonical

# archive: bytes finais do ZIP; private_key: Ed25519PrivateKey do publicador.
# record: registro acima, sem o campo signature.
record["sha256"] = hashlib.sha256(archive).hexdigest()
record["signature"] = base64.b64encode(private_key.sign(canonical(record))).decode("ascii")
```

Publique o arquivo e o catálogo por HTTPS, configure a chave pública e instale a versão na tela Marketplace do proprietário. Um mestre ativa o módulo em Settings → Extensions da mesa. A rota HTTP de instalação recebe somente `id` e `version`, consulta o catálogo configurado e verifica o ZIP selecionado. Ela não aceita uma URL arbitrária de arquivo enviada na requisição.

Como alternativa inteiramente local, o proprietário pode usar **Instalar de ZIP** na mesma modal. Esse fluxo não consulta o marketplace nem exige catálogo ou chaves de publicador: o envio local é a decisão explícita de confiança do proprietário. O ZIP ainda passa pelas mesmas validações de manifesto, compatibilidade, caminhos, tipos de arquivo, cotas e conteúdo executável. Na seção Sistemas ele deve declarar `system`; na seção Módulos ele não pode declará-lo. Como JavaScript de módulos roda na origem da aplicação, instale somente arquivos confiáveis.

A instalação verifica digest, identidade e intervalo SDK do manifesto, arquivo de entrada, nomes, tipos de entrada e bytes extraídos. Os limites são 64 MiB compactados, 256 MiB expandidos, 4.096 entradas e 64 módulos ativos por mesa. Caminhos não podem atravessar diretórios nem conter barras invertidas, escapes percentuais, pontuação de URL ou NUL. Links simbólicos, entradas criptografadas, nomes duplicados sem distinção de maiúsculas, extensões não permitidas e cabeçalhos reconhecidos de executáveis nativos são rejeitados. As extensões permitidas estão em `ModulePackages.install`; textos de licença precisam de `.txt` ou `.md`, pois arquivos sem extensão são rejeitados.

Por padrão, os arquivos ZIP ficam em `MEDIA_ROOT/modules/archives/` e os pacotes extraídos em `MEDIA_ROOT/modules/packages/<id>/<version>/<digest>/`. Defina, por exemplo, `GRAVEWRIGHT_MODULES_ROOT=/srv/gravewright/modulos` no `.env` para apontar outra pasta; caminhos relativos partem da raiz do projeto e a mudança exige reiniciar o host. O banco guarda manifestos e a origem confiada de cada instalação. Não é possível substituir uma versão com outros bytes. Ativação e acesso autenticado a arquivos verificam novamente o conteúdo; publique uma nova versão em vez de editar arquivos extraídos.

A ativação recebe `{modules, replacements, expectedRevision}`. `modules` relaciona IDs a versões exatas, `replacements` relaciona superfícies a IDs, e `expectedRevision` deve corresponder ao último `moduleSetRevision` lido (`"0"` inicialmente). Uma revisão antiga resulta em `conflict`. Alterações geram nova revisão e notificam a mesa. Clientes também consultam periodicamente e reconciliam ao reconectar.

Um registro assinado com `status: "revoked"` revoga uma versão instalada quando o catálogo é consultado, remove suas ativações e preferências de substituição e altera as revisões afetadas. A revogação depende dessa consulta; não é um push permanente do publicador. Reverter para outra versão instalada altera o código, sem reverter os dados persistidos do módulo.

## Ciclo de vida e montagem

O arquivo de entrada exporta por padrão um objeto com as funções `start`, `register` e `stop`. O runtime rejeita o membro antigo `execute`.

1. Referências antigas são invalidadas antes da reconciliação de uma revisão nova.
2. O runtime importa cada pacote, executa e aguarda `start(moduleContext)` e chama `register(registrationContext)` uma vez.
3. `register` precisa ser síncrono. Ele declara callbacks de montagem, que podem ser assíncronos. Registrar um domínio duas vezes gera `conflict`; domínio desconhecido ou registro depois do retorno de `register` gera `invalid_data`.
4. Cada superfície correspondente recebe raiz própria, contexto congelado, sinal de cancelamento, API, arquivos/estilos/armazenamento e `onDispose`. Superfícies de cena também recebem identificadores da cena; `scene.overlay` oferece conversão de coordenadas.
5. Remover uma superfície, sair da mesa, trocar cena/substituição/revisão ou perder acesso invalida os ciclos correspondentes. A limpeza cancela o sinal primeiro, executa callbacks em ordem inversa e limita cada limpeza assíncrona a cinco segundos. `stop` acontece depois da limpeza, inclusive quando `start` falha após o registro interno do módulo para encerramento.

O contexto de `start` fornece `api`, `assets`, `styles`, `storage`, `signal` e `onDispose`, sem raiz visual nem cena. Blocos de montagem adicionam `root`, `context`, `host`, `events` e eventualmente `viewport`. O registro recebe `register` e uma API cujo `ui.register` encaminha à mesma fase síncrona. Use o `register` fornecido para declarar superfícies do módulo.

Não reutilize a API de uma montagem na próxima. Operações pendentes ou referências descartadas falham com `stale_context`. Adicione listeners com `{ signal }` e registre a limpeza de timers, observers ou recursos externos em `onDispose`. Cancelar no cliente não desfaz escrita já confirmada no servidor. Falhas de início/registro encerram a ativação e restauram a interface nativa; falhas de montagem são reportadas e restauram a superfície nativa quando a substituição selecionada falha.

## Superfícies disponíveis

O [registro e os schemas de contexto](../../gravewright/modules/contracts/registry.json) definem nomes e formatos:

| Superfície | Finalidade / contexto adicional |
| --- | --- |
| `actor.directory` | Lista de atores |
| `actor.sheet` | Ficha de ator; `actorId` |
| `token.sheet` | Ficha de token; ator/token e contexto da cena |
| `item.directory` | Lista de itens |
| `item.sheet` | Ficha de item; `itemId` |
| `journal.sheet` | Documento; `journalId` |
| `scene.directory` | Lista de mapas/cenas |
| `scene.controls` | Controles da cena atual |
| `scene.overlay` | Sobreposição limitada à área visível da cena |
| `chat.log` | Área de chat |
| `combat.tracker` | Combate da cena atual |
| `preferences` | Preferências da mesa |
| `table.interface` | Área da mesa |

`augment` é o padrão e mantém o conteúdo nativo. `replace` o oculta durante a montagem selecionada. Uma única candidata é escolhida automaticamente; candidatas concorrentes exigem preferência explícita da mesa. Extensões em modo augment continuam sendo montadas. O CSS é compartilhado, portanto prefixe seus seletores. Raízes de sobreposição não interceptam entrada por padrão; habilite-a somente nos elementos interativos do módulo.

Coordenadas usam pixels lógicos da cena: origem superior esquerda, x para direita, y para baixo e âncora dos tokens no centro. `viewport.sceneToViewport({x,y})` e `viewport.viewportToScene({x,y})` convertem pixels CSS da área visível, independentemente da densidade de pixels. Use a identidade da cena montada, não a seleção global de mapas.

A API global `gravewright.ui` também oferece `app.shell` e `inside.content`; são superfícies da página do host, não domínios aceitos pelo runtime de pacotes assinados. Veja a [arquitetura do frontend](frontend.md).

## Arquivos, persistência e eventos

Use `assets.url(path)`, `assets.text(path)`, `assets.json(path)` ou `assets.bytes(path)` com caminhos relativos ao pacote. `styles.use(path)` instala CSS e retorna um callback de remoção, também chamado automaticamente no descarte. Esses helpers não oferecem acesso arbitrário à rede como parte do SDK suportado.

| Armazenamento | Escopo | Política de escrita |
| --- | --- | --- |
| `storage.local` | Origem do navegador + ID do módulo; sem separação por mesa/usuário | JSON local, 256 KiB por valor |
| `storage.user` | Módulo + mesa + usuário autenticado | JSON persistente do próprio usuário |
| `storage.table` | Módulo + mesa | Membros leem; mestre escreve |

Valores persistentes têm limite de 256 KiB e cada namespace persistente, 4 MiB. Chaves têm no máximo 240 caracteres. `get` retorna `{value, revision}` ou `null`; `list(prefix)` retorna pares chave/revisão. Crie com `expectedRevision: null`; atualize/exclua com a revisão exata retornada por `get` ou `set`:

```javascript
const previous = await storage.user.get("panel-settings");
const saved = await storage.user.set("panel-settings", { collapsed: true }, {
  expectedRevision: previous?.revision ?? null
});
await storage.user.delete("panel-settings", { expectedRevision: saved.revision });
```

Ao receber `conflict`, leia novamente e decida como combinar alterações. Os valores sobrevivem à desativação e atualização; versione e migre seu próprio JSON. Armazenamento local não é apropriado para dados privados em navegador compartilhado, pois o namespace do módulo é comum entre contas.

Prefira `api.events.on("actors.changed", handler)` e outros eventos de domínio para obter estados autorizados. O `events.on` antigo do bloco expõe `actor.created`, `actor.updated`, `actor.deleted` e `scene.viewport.changed`. A ponte atual infere eventos de ator comparando listas visíveis: estados iniciais/repetidos e mudanças de visibilidade podem parecer criação, atualização ou exclusão. São sinais para atualizar dados, não auditoria de mutações. Releia após reconectar e não dependa deles para executar efeitos exatamente uma vez. Cancele a assinatura com o retorno de `on` ou aguarde a limpeza da montagem.

## Verificação

Na raiz do repositório:

```sh
uv run --locked python manage.py test gravewright.modules gravewright.table.tests.test_frontend_api gravewright.table.tests.test_public_api
node --test tests/modules/*.test.mjs
uv run --locked python tests/e2e/frontend_api.py
uv run --locked python tests/e2e/table_modules.py
```

Os testes de navegador precisam das dependências de desenvolvimento e do navegador Playwright instalado; veja [testes](testing.md). Exercite ativação/desativação, falha de montagem, troca de cena, perda de participação, reconexão, revisões antigas de armazenamento e visões de mestre/jogador. Schemas e testes existentes são referências concretas; este checkout não inclui pacote SDK TypeScript nem verificador automático de compatibilidade entre versões principais.

### Pacotes de idioma para a instalação

O manifesto pode declarar `locales`, associando cada idioma a `{ "name": "Português (Brasil)", "path": "locales/pt-BR.json" }`. Cada catálogo é um objeto JSON de textos originais e traduções, preservando marcadores como `{name}`. O inglês pertence ao host e não pode ser sobrescrito. Um pacote não pode combinar `system` e `locales`, nem executar Python baixado pelo marketplace.

O proprietário ativa os idiomas em Módulos instalados. A rota `POST /api/module-packages/activation` recebe `{ "id": "gravewright.translator", "version": "0.1.0", "enabled": true }` e verifica o arquivo assinado. Somente um pacote de idiomas fica ativo por instalação. A configuração de módulos por campanha rejeita esses pacotes e a lista de extensões da mesa os omite.

Com o pacote ativo, cada usuário escolhe seu idioma nas configurações internas da conta, armazenado em `UserPreference.locale`. Um cookie assinado permite manter o idioma na tela de entrada; outra conta autenticada não herda a preferência desse cookie. Desativar ou revogar o pacote remove o seletor e restaura o inglês no próximo carregamento. Páginas já abertas precisam ser recarregadas.

A tradução abrange dicionários da aplicação, textos literais dos templates e controles criados no navegador. Rótulos reativos são traduzidos antes do processamento pelo Datastar para evitar disputa entre observadores. Nomes, mensagens, conteúdo editável, PDFs e interfaces arbitrárias de terceiros não são traduzidos.

O app Django do [Translator](https://github.com/Gravewright/translator) extrai e mantém os catálogos e gera o ZIP portátil. Ele não precisa estar instalado no Django após a instalação pelo marketplace. O relatório `VALIDATION.md` registra os testes offline e online. A pré-release v0.1.0 exige as alterações do host presentes neste checkout de desenvolvimento.

### Biblioteca de pacotes e instalação

A área interna possui bibliotecas separadas de **Sistemas** e **Módulos**, com visualização em grade/lista, busca e paginação. **Instalar sistema** ou **Instalar módulo** abre o catálogo configurado em uma janela filtrada por categoria. O sistema PDF integrado continua visível sem configuração remota. A biblioteca instalada não consulta o catálogo; os diagnósticos aparecem ao abrir a janela de instalação. Links antigos com `section=marketplace` levam à biblioteca de módulos.

Novos registros assinados devem incluir `"type": "system"` ou `"type": "module"`. O campo participa da assinatura e deve corresponder ao manifesto do ZIP: sistemas declaram `system`. Valores inválidos e divergências são rejeitados. Registros antigos sem tipo continuam válidos e são tratados como módulos antes da instalação; depois, o manifesto instalado determina a categoria. Publicadores de sistemas devem incluir o tipo assinado para que o pacote apareça corretamente antes de ser instalado.

Registros do catálogo aceitam `tags`: até 24 textos Unicode únicos, sem espaços nas extremidades, não vazios e com até 64 caracteres. As tags integram a assinatura e geram categorias na modal de instalação, separadas pelo tipo de pacote. Pacotes sem tags continuam aparecendo em Todos os pacotes.

A modal recebe progresso real via NDJSON de `POST /api/marketplace/install`, solicitando `Accept: application/x-ndjson`. As etapas são `catalog`, `download` (bytes recebidos e total quando conhecido), `verify`, `complete` e `error`. A conclusão só é enviada após verificar e instalar o arquivo. Downloads sem tamanho informado exibem progresso indeterminado e contagem de bytes. O retorno JSON tradicional permanece disponível. Desconectar o navegador não desfaz uma instalação em andamento; atualize a biblioteca para conferir o resultado.

### Personalização opcional por usuário

Um módulo ativo pode exportar `customize(context)` junto aos métodos obrigatórios
do ciclo de vida. A lista de extensões mostra **Personalizar** imediatamente antes
de Desativar (ou sozinho para jogadores). O callback recebe os mesmos assets,
armazenamento e ciclo de vida de `start`; não ganha novas permissões. Use
`storage.user` para preferências pessoais e feche as modais e libere os recursos
em `onDispose`. O host fornece apenas o botão; o módulo mantém sua interface,
assets e validação. Módulos sem esse callback continuam funcionando normalmente.

### Apps Django instalados explicitamente

O operador pode instalar um app Python confiável no ambiente do servidor e definir
`GRAVEWRIGHT_SERVER_APPS` com seu caminho de importação (separado por vírgulas para
vários apps). O AppConfig pode declarar `gravewright_urlconf` para registrar suas
rotas. Cada app deve verificar autenticação, CSRF e permissões nativas. O marketplace
de JavaScript não instala nem ativa código Python por esse mecanismo. Ao recriar o
ambiente Python, reinstale essas dependências gerenciadas separadamente.

As linhas de itens nativas fornecem o formato de arraste
`application/x-gravewright-item`, com `{id, tableId}`. Resolva o identificador pela
API autenticada antes de copiar o item para uma ficha; o conteúdo do arraste não
concede acesso ao documento.

Para apps mantidos em repositórios separados, configure
`GRAVEWRIGHT_SERVER_APP_PATHS` com as pastas raiz dos pacotes (`:` no Linux/macOS,
`;` no Windows). Caminhos relativos partem da raiz do VTT. Esses caminhos
explicitamente confiáveis continuam disponíveis após sincronizar o ambiente;
as dependências dos apps ainda precisam ser instaladas. Os pacotes permanecem
fora do repositório do VTT.

O checkout já traz uma pasta padrão para esses apps: `extensions/django`,
definida por `GRAVEWRIGHT_DJANGO_MODULES_ROOT`. Ela é acrescentada ao `sys.path`
quando existe, de modo que um pacote colocado diretamente nela só precisa do seu
caminho de importação em `GRAVEWRIGHT_SERVER_APPS`; entradas explícitas de
`GRAVEWRIGHT_SERVER_APP_PATHS` têm precedência sobre ela. Os fontes de módulos de
navegador têm a pasta padrão correspondente `extensions/api`
(`GRAVEWRIGHT_API_MODULES_ROOT`), que serve apenas para autoria e documentação —
os pacotes assinados instalados continuam em `MEDIA_ROOT/modules`. Uma pasta
configurada que não existe impede a inicialização; apagar as pastas padrão sem
configurá-las é suportado. O git ignora o conteúdo das duas pastas, para que as
extensões fiquem fora deste repositório.

[Porte ético de módulos](ethical-module-porting.md)
