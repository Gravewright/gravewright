# APIs públicas do Gravewright

A API pública para extensões do Gravewright é a **Gravewright SDK v1**.

Autores devem criar pacotes SDK declarativos em `data/packages/{kind_plural}/{id}/`, com `manifest.json`, arquivos declarados e, quando necessário, runtime JavaScript escopado por pacote.

## Onde começar

Leia a documentação da SDK em:

- [`../sdk/README.md`](../sdk/README.md)
- [`../sdk/declarative-model.md`](../sdk/declarative-model.md)
- [`../sdk/author-complete-checklist.md`](../sdk/author-complete-checklist.md)
- [`../sdk/power-map.md`](../sdk/power-map.md)

## Superfície pública suportada

A superfície pública é composta por:

1. `manifest.json` validado pelo schema da SDK v1;
2. arquivos declarados pelo manifesto;
3. capabilities declaradas em `capabilities`;
4. entrypoints declarados em `entrypoints`;
5. objeto escopado `sdk` recebido por `window.GravewrightSDK.register(...)`.

Qualquer global, endpoint, store, evento WebSocket, estrutura DOM ou função interna não documentada como SDK pública deve ser considerado privado.
