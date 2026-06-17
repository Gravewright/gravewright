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

## Comandos

```bash
grave package validate data/packages/my-package
grave package doctor my-package
```

## Validação como contrato de autoria

Se a validação não consegue entender um recurso, provavelmente ele não está declarativo o suficiente. Prefira corrigir o manifesto em vez de contornar via runtime.
