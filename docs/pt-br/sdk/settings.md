# Settings

Settings permitem que usuários ou campanhas configurem o comportamento de um pacote. Elas devem ser declaradas no manifesto e acessadas pelo runtime somente quando necessário.

## Declaração

```json
"settings": [
  {
    "key": "enabled",
    "type": "boolean",
    "scope": "campaign",
    "default": true,
    "label": "Enabled",
    "description": "Enable this package feature."
  }
]
```

## Campos recomendados

| Campo | Descrição |
|---|---|
| `key` | Identificador estável usado por `sdk.settings`. |
| `type` | Tipo do valor. |
| `scope` | Escopo da configuração. |
| `default` | Valor inicial seguro. |
| `label` | Texto visível ao usuário. |
| `description` | Explica efeito e impacto. |

## Runtime

```js
const enabled = sdk.settings.get("enabled");
sdk.settings.set("enabled", false);
const all = sdk.settings.all();
const defs = sdk.settings.definitions();

sdk.setting("enabled");
sdk.setting("enabled", true);
```

Capability exigida: `settings`.

## Boas práticas

- Declare settings antes de ler no runtime.
- Use defaults seguros.
- Evite mudar `key` depois de publicado.
- Use `scope` de campanha para comportamento compartilhado.
- Use `scope` de usuário para preferências pessoais.
- Documente settings no README do pacote.

## Coerção de valores e escopo (estabilidade)

Os valores são coeridos de forma **estrita** para o `type` da setting; um valor
não reconhecido é rejeitado com o código estável `sdk.settings.invalid_value` em
vez de virar o default silenciosamente.

- `boolean` — verdadeiro: `true`, `"true"`, `"1"`, `"yes"`, `"on"`, `1`; falso:
  `false`, `"false"`, `"0"`, `"no"`, `"off"`, `""`, `0`. Qualquer outro valor é
  inválido (em especial, `"false"` nunca vira `true`).
- `integer` / `number` — devem parsear corretamente; booleanos e strings não
  numéricas são inválidos.
- `enum` — deve ser uma das `options` declaradas.

A precedência de escopo para o valor efetivo é **default → campaign → user**. O
escopo `user` é **por usuário, global entre campanhas** (indexado por user id,
não por campanha). Um valor armazenado com JSON corrompido cai no default na
leitura e é reportado pelo doctor (`setting_value_corrupted`).
