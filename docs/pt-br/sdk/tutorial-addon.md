# Tutorial: do zero a um addon funcionando

Este passo a passo constrói um addon real e instalável do zero: um pacote que mostra um
toast quando o jogo está pronto. O pacote final é distribuído como
[`examples/packages/hello-toast`](../../../examples/packages/hello-toast) e é validado no
CI, então cada passo aqui é comprovadamente funcional.

Um `addon` é um pacote opcional, ativado por campanha. Ele pode adicionar UI, plugins,
settings, chat cards, ferramentas de cena e comportamento de runtime, e vários addons
podem estar ativos na mesma campanha ao mesmo tempo.

## Pré-requisitos

- Um checkout funcional do Gravewright onde a CLI `grave` roda (veja [`inicio.md`](../inicio.md)).
- Uma campanha onde você possa ativar pacotes (anote o id da campanha).

## 1. Faça o scaffold do pacote

Gere um addon que inclui JavaScript confiável:

```bash
grave addon new hello-toast --name "Hello Toast" --js
```

Isto cria o pacote em `data/packages/hello-toast/`:

```text
data/packages/hello-toast/
  manifest.json
  README.md
  assets/
    hello-toast.js
```

O `manifest.json` gerado já declara `kind: "addon"`, `activation.mode: "multiple"`, a
capability `assets.scripts` e a entrada `entrypoints.game.scripts` que carrega seu script.
Como o addon mostra um toast, adicione a capability `assets.ui`:

```json
{
  "kind": "addon",
  "id": "hello-toast",
  "capabilities": ["assets.scripts", "assets.ui"],
  "activation": { "scope": "campaign", "mode": "multiple" },
  "entrypoints": {
    "game": {
      "scripts": ["assets/hello-toast.js"]
    }
  },
  "provides": {}
}
```

> `sdk.toast(...)` tem gate por `assets.ui`. Chamá-lo sem declarar a capability lança um
> erro acionável. Veja [`capabilities.md`](capabilities.md).

## 2. Escreva o runtime

Substitua `assets/hello-toast.js` por:

```js
window.GravewrightSDK.register({
  id: "hello-toast",
  ready(sdk) {
    sdk.toast("Hello from the Gravewright SDK");
  },
});
```

O `id` deve corresponder ao id do manifesto e deve ser chamado do próprio script declarado
pelo pacote. `ready` roda depois que o runtime de jogo está pronto. Veja
[`runtime.md`](runtime.md).

## 3. Valide

```bash
grave package validate data/packages/hello-toast
```

Saída esperada:

```text
hello-toast: ok
```

Se você vir `error: ...`, a mensagem nomeia o campo do manifesto ou o arquivo faltante a
corrigir. A lista completa de chaves de erro está em [`validation.md`](validation.md).

## 4. Instale e habilite

```bash
grave package install hello-toast --yes --enable
```

A instalação imprime as capabilities solicitadas antes de confirmar (avisa quando um
pacote roda JavaScript confiável). `--enable` o disponibiliza para campanhas.

## 5. Ative em uma campanha

```bash
grave campaign package activate <campaign_id> hello-toast
```

Use o **id** da campanha, não o título. Liste os pacotes ativos para confirmar:

```bash
grave campaign package list <campaign_id>
```

## 6. Veja funcionando

Abra a mesa da campanha no Gravewright. Quando o runtime de jogo fica pronto, o toast
**"Hello from the Gravewright SDK"** aparece.

## 7. Depure quando algo estiver errado

```bash
grave package doctor hello-toast
```

O doctor reporta validade do manifesto, status de install/enable e problemas de
dependência com uma correção acionável para cada. Veja
[`troubleshooting.md`](troubleshooting.md).

## Próximos passos

- Adicione uma setting de usuário (veja [`examples/packages/toggle-example`](../../../examples/packages/toggle-example) e [`settings.md`](settings.md)).
- Construa um ruleset: [`tutorial-ruleset.md`](tutorial-ruleset.md).
- Mapeie objetivos para capabilities e APIs: [`power-map.md`](power-map.md).
