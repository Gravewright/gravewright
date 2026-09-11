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

## Catálogo assinado e ativação

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

A instalação verifica digest, identidade e intervalo SDK do manifesto, arquivo de entrada, nomes, tipos de entrada e bytes extraídos. Os limites são 64 MiB compactados, 256 MiB expandidos, 4.096 entradas e 64 módulos ativos por mesa. Caminhos não podem atravessar diretórios nem conter barras invertidas, escapes percentuais, pontuação de URL ou NUL. Links simbólicos, entradas criptografadas, nomes duplicados sem distinção de maiúsculas, extensões não permitidas e cabeçalhos reconhecidos de executáveis nativos são rejeitados. As extensões permitidas estão em `ModulePackages.install`; textos de licença precisam de `.txt` ou `.md`, pois arquivos sem extensão são rejeitados.

Os arquivos ZIP ficam em `MEDIA_ROOT/modules/archives/`; os pacotes extraídos, em `MEDIA_ROOT/modules/packages/<id>/<version>/<digest>/`. O banco guarda manifestos e registros assinados. Não é possível substituir uma versão com outros bytes. Ativação e acesso autenticado a arquivos verificam novamente o conteúdo; publique uma nova versão em vez de editar arquivos extraídos.

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
