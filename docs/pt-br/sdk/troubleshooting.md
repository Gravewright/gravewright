# Troubleshooting da SDK

Use este guia quando um pacote não valida, instala, ativa ou roda corretamente.

## Comece pela validação

```bash
grave package validate data/packages/my-package
grave package validate data/packages/my-package --json
grave package doctor my-package
grave doctor --packages-dir data/packages
```

Corrija os erros de validação antes de depurar o comportamento de runtime do navegador.

## O pacote não aparece

Verifique:

- o diretório do pacote está em `data/packages/{kind_plural}/{id}/`;
- `manifest.json` existe;
- o `id` do manifesto corresponde ao nome do diretório;
- `kind` é válido;
- o pacote valida;
- o pacote está instalado/habilitado quando necessário;
- a compatibilidade do pacote não é incompatível.

Comandos úteis:

```bash
grave package list
grave package doctor my-package
grave doctor --json
```

## A validação do manifesto falha

Causas comuns:

- falta `schemaVersion: 1`;
- falta `sdkVersion: "1"`;
- `kind` de pacote inválido;
- id ou path inseguro;
- declaração de compatibilidade ausente;
- capability desconhecida ou proibida;
- modo de ativação errado para o kind;
- ruleset sem modelo de storage ou tipos de ator;
- pacote de assets declarando campos de modelo de jogo;
- path de content pack ausente;
- enum de setting inválido sem `options`.

Veja [`validation.md`](validation.md).

## O script do entrypoint não roda

Verifique:

- o pacote declara a capability `assets.scripts`;
- o path do script está listado em `entrypoints.game.scripts`;
- o path do script existe e é relativo ao pacote;
- o pacote está ativo na campanha atual;
- o console do navegador não tem erros de carregamento de script;
- `window.GravewrightSDK.register({ id })` usa o id de manifesto exato.

## `GravewrightSDK.register` retorna false

Causas prováveis:

- `id` ausente;
- o id não corresponde ao id do manifesto;
- o script não foi carregado como um script de propriedade do pacote;
- o pacote está inativo;
- registro duplicado;
- a checagem de propriedade/nonce do script do pacote falhou.

Inspecione o console do navegador por uma mensagem `GravewrightSDK.register refused ...`.

## Erro de capability em runtime

Exemplo:

```text
Package "my-package" attempted to use sdk.chat.send but does not declare capability "chat.cards".
```

Corrija uma destas opções:

- adicione a capability exigida ao `manifest.json`;
- pare de chamar esse método da SDK;
- substitua o comportamento de runtime por dados declarativos de pacote.

Veja [`capabilities.md`](capabilities.md).

## As settings não persistem

Verifique:

- o pacote declara a capability `settings`;
- a setting está declarada no `manifest.json`;
- a `key` da setting corresponde exatamente;
- `type` e `scope` da setting são válidos;
- settings de enum declaram `options`;
- o id da campanha ativa está disponível ou é passado explicitamente a `sdk.settings.set`.

Exemplo:

```js
await sdk.settings.set("enabled", true, { campaignId: sdk.game.campaign()?.id });
```

## Não é possível carregar o content pack

Verifique:

- o pacote declara a capability `content.packs`;
- o content pack está listado em `provides.contentPacks`;
- o `id` do content pack está correto;
- o `type` do content pack é um dos valores permitidos;
- o `path` do content pack existe e é seguro;
- o runtime usa o `sdk.content.pack(packId)` do pacote atual.

## Os eventos não são recebidos

Verifique:

- ambos os pacotes declaram as capabilities `bus.*` e entradas `interop` correspondentes;
- o listener é registrado antes do evento disparar, ou o evento é emitido após o registro;
- o nome do evento corresponde exatamente;
- o nome do evento tem namespace de pacote;
- a `version` do payload é suportada;
- o pacote par opcional está instalado e ativo quando esperado.

Para integrações opcionais, a ausência de eventos é normal quando o pacote par está inativo.

## Os plugins de runtime de sheet não rodam

Verifique:

- o pacote declara `sheets.runtime`;
- o script do ruleset/addon registra via `sdk.sheets.register(...)`;
- os métodos do plugin usam nomes suportados;
- o plugin retorna o tipo esperado;
- o pacote está ativo na campanha;
- o console do navegador não tem erros de setup.

## Os plugins de runtime de combate não rodam

Verifique:

- o pacote declara `combat.runtime`;
- o pacote registra com `sdk.combat.register(...)` ou `sdk.combat.registerPanel(...)`;
- os handlers/slots do plugin usam nomes suportados;
- os valores de retorno correspondem às expectativas documentadas;
- o pacote está ativo.

## O pacote funciona em debug mas não em produção

Verifique uso acidental de:

- `window.GravewrightSDKDebug`;
- globals privados do renderer;
- estrutura do DOM não documentada como pública;
- dados apenas de teste;
- comportamento de `APP_DEBUG=true`.

`window.GravewrightSDKDebug` está ausente em produção.

## Docs antigos de extensão ainda aparecem

Remova arquivos e links obsoletos. A superfície de extensão suportada é o modelo de pacote da SDK em `docs/sdk/`:

```bash
rm -f docs/api/extension-apis.md

```

Não preserve páginas antigas de API de extensão nos docs públicos. Substitua-as por páginas do modelo de pacote da SDK.
