# Runtime do navegador — `window.GravewrightSDK`

`window.GravewrightSDK` é o único ponto de entrada público do navegador para scripts de pacote.

A página da mesa carrega os client manifests dos pacotes ativos, carrega os assets declarados pelos pacotes e então o runtime do navegador entrega a cada pacote registrado um objeto `sdk` escopado. O `sdk` escopado expõe apenas namespaces documentados e aplica as capabilities declaradas pelo pacote.

## Registrando um pacote

```js
window.GravewrightSDK.register({
  id: "my-package",
  setup(sdk, payload) {
    // Chamado quando o manifesto do pacote é conhecido.
  },
  ready(sdk, payload) {
    // Chamado depois que o runtime de jogo está pronto.
  },
});
```

`register` retorna `true` quando o registro é aceito e `false` quando rejeitado.

O registro é rejeitado quando:

- `id` está ausente;
- o script não está rodando como um script de propriedade do pacote;
- o id de pacote do script não corresponde ao id reivindicado;
- o pacote não está ativo na campanha atual;
- o pacote já registrou um runtime.

## Propriedade do script

Scripts de pacote são associados ao id do seu manifesto. O runtime verifica o script atual antes de aceitar `register(...)`:

- scripts de pacote só podem reivindicar o id do próprio pacote;
- scripts de pacote não podem se passar por outro pacote;
- registros duplicados são recusados;
- registros de pacote inativo são recusados.

Os metadados de script fornecidos pelo servidor podem incluir `data-gw-package` e `data-gw-nonce`. Quando presentes, o nonce deve corresponder ao nonce do pacote no contexto de jogo.

## Ciclo de vida

### `setup(sdk, payload)`

Chamado uma vez depois que tanto o runtime do pacote quanto o client manifest ativo são conhecidos.

Use `setup` para:

- registrar plugins de runtime;
- registrar comandos;
- registrar comportamento de ficha;
- registrar comportamento de combate;
- inicializar estado local do navegador;
- assinar eventos de pacote.

Não assuma que toda a UI de jogo está pronta a menos que `sdk.game.ready()` retorne `true`.

### `ready(sdk, payload)`

Chamado uma vez depois que o runtime de jogo está pronto.

Use `ready` para:

- ler o contexto ativo;
- inicializar UI que requer o runtime da mesa;
- reagir ao estado de cena/campanha carregado;
- emitir eventos de pacote-pronto.

### Ciclo de vida `ready`

O `ready(sdk, payload)` de um pacote roda uma vez após o runtime da mesa ser inicializado:

```js
window.GravewrightSDK.register({
  id: "my-package",
  ready(sdk, { context }) {
    // O runtime da mesa está pronto.
  },
});
```

## Formato do payload

Tanto `setup` quanto `ready` recebem:

```js
{
  package: /* client manifest ativo para este pacote */,
  context: /* snapshot do contexto de jogo */
}
```

Trate os dados do payload como somente-leitura. Use métodos documentados da SDK para ler ou solicitar mutações.

## Namespaces da SDK escopada

```text
sdk.version
sdk.package
sdk.kind
sdk.capabilities
sdk.context
sdk.game
sdk.bus
sdk.commands
sdk.ui
sdk.chat
sdk.settings
sdk.sheets
sdk.combat
sdk.tokens
sdk.scene
sdk.tools
sdk.content
sdk.i18n
```

Veja [`reference.md`](reference.md) para detalhes completos dos métodos.

## Atalhos

```js
sdk.toast("Hello");                   // alias para sdk.ui.toast
sdk.setting("enabled");               // lê uma setting
sdk.setting("enabled", true);         // grava uma setting
```

Os atalhos aplicam as mesmas capabilities que os métodos de namespace subjacentes.

## Objeto de debug (apenas dev)

Quando o servidor roda com `APP_DEBUG=true`, o runtime expõe um objeto de debug somente-leitura:

```js
GravewrightSDKDebug.packages();   // client manifests dos pacotes ativos
GravewrightSDKDebug.runtimes();   // ids de pacote que registraram um runtime
GravewrightSDKDebug.listeners();  // nomes de eventos registrados
GravewrightSDKDebug.context();    // contexto de jogo congelado
```

`window.GravewrightSDKDebug` está ausente em produção. Não dependa dele em código de pacote.

## Comportamento de erro

Erros no ciclo de vida do pacote são capturados e logados para que um pacote não derrube todo o runtime.

Violações de capability lançam erros claros a partir do método chamado da SDK. Autores de pacote devem corrigir o manifesto ou parar de chamar o método.

## Fronteira pública

Público:

- `window.GravewrightSDK.version`
- `window.GravewrightSDK.register(...)`
- o objeto `sdk` escopado passado aos pacotes registrados

Não público:

- helpers internos de carregamento de manifesto;
- implementação interna do barramento de eventos do pacote;
- globals privados do renderer;
- estrutura do DOM;
- `window.GravewrightSDKDebug` em produção;
