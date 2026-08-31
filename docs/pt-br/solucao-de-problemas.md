# Solução de problemas

Comece com `grave doctor`; use `grave doctor --json` quando outra ferramenta
precisar consumir o resultado.

## “Exactly one active server is required”

Confira `gravewright.modules.json`. Ative um módulo `server` e desative todos os
outros servers. Módulos instalados começam desativados.

## `ctx.use("nome")` foi rejeitado

O chamador precisa declarar o módulo exato em `dependencies`; a dependência deve
estar ativa e sua versão deve satisfazer o range SemVer. Dependência transitiva
não conta.

## `ctx.use("nome")` tem tipo `unknown`

Confira se `types.ts` aumenta `ModuleRegistry` com o nome entre aspas e execute:

```bash
npm run types:sync
npm run typecheck
```

## Uma contribuição visual não aparece

Confira se a room renderiza exatamente um elemento para cada classe `gw-*`, se o
manifest expõe esses slots e se a contribuição está em `exports.get` e `slots`.
A validação do DOM ocorre depois de `mount()`.

## O projeto importa, mas falha durante a ativação

Mova conexões, listeners, timers e abertura de banco do import para `create()`.
Registre cleanup imediatamente com `ctx.onDispose()`. O plano não desfaz efeitos
executados durante a avaliação do módulo.

## Falha de integridade no marketplace

Não tente desativar a verificação. Confirme que o ZIP do release é imutável e
recalcule `download_sha256`. Nome e versão do manifest remoto devem corresponder
ao manifest dentro do arquivo.
