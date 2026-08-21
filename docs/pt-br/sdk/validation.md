# Validação

A validação garante que o pacote segue o contrato SDK v1 antes de ser instalado ou ativado.

## O que deve ser validado

- presença de campos obrigatórios;
- tipos corretos no manifesto;
- `kind` permitido;
- `activation.mode` compatível com `kind`;
- formato de `id` e `version`;
- `compatibility` coerente;
- capabilities permitidas;
- relação entre capabilities e entrypoints;
- relação entre capabilities e `provides`;
- paths relativos e seguros;
- existência de arquivos referenciados;
- dependências e conflitos;
- shapes de `settings`, `contentPacks`, `assets`, `sheets`, `rules` e mappings.

## Erros comuns

| Problema | Correção |
|---|---|
| `entrypoints.game.scripts` sem `assets.scripts` | adicione a capability ou remova script. |
| `entrypoints.game.styles` sem `assets.styles` | adicione a capability ou remova style. |
| Script não chama `window.GravewrightSDK.register` | registre o pacote ou remova o script. |
| `id` do runtime difere do manifesto | alinhe os ids. |
| Capability sem uso | remova ou declare o recurso correspondente. |
| Path com `..` | use path relativo seguro dentro do pacote. |
| Arquivo declarado não existe | corrija path ou inclua arquivo. |
| `ruleset` com `activation.mode: multiple` | use `exclusive`. |
| `library` ativado como pacote comum | use `passive` e dependências. |
| Chave desconhecida em `provides` | use apenas campos suportados ou trate como campo planejado fora do contrato ativo. |
| `provides.rules` como array | use objeto, por exemplo `{ "formulas": "rules/formulas.gw.json" }`. |
| `compatibility.verified` com versão do produto ou pre-release | use `"1"`, o identificador canônico da SDK 1 RC 1. |

## Códigos recentes

| Código | Significado | Correção |
|---|---|---|
| `sdk.validation.rules_shape_invalid` | `provides.rules` não é objeto. | Use entradas nome-para-path, por exemplo `{ "formulas": "rules/formulas.gw.json" }`. |
| `sdk.validation.provides_key_unknown` | `provides` contém chave que a engine não consome. | Use campos suportados ou aguarde a superfície ficar ativa. |
| `sdk.validation.compatibility_prerelease` | `verified` usa uma versão do produto ou pre-release em vez do identificador canônico da SDK. | Use `compatibility.verified: "1"`. |

## Comandos

```bash
grave package validate data/packages/my-package
grave package doctor my-package
```

## Validação como contrato de autoria

Se a validação não consegue entender um recurso, provavelmente ele não está declarativo o suficiente. Prefira corrigir o manifesto em vez de contornar via runtime.
