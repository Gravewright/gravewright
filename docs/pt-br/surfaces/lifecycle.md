# Ciclo de vida e estado

Um módulo atravessa etapas explícitas:

```text
descoberto → validado → carregado → instanciado → composto → ativo
                                        │                    │
                                        └─── rollback ◄──────┘
                                                             │
                                             dispose ◄── desabilitado
```

- Discovery encontra diretórios com `manifest.json`.
- Load valida metadados e ordem de dependências.
- Instanciação chama `create()` apenas para módulos ativos.
- `ctx.onDispose()` registra o cleanup assim que um recurso externo existe.
- Composição registra middleware, routes e slots.
- O server inicia depois da composição completa.
- Disable executa disposers em ordem reversa.

`gravewright.modules.json` armazena `active` ou `disabled`; ausentes ficam desabilitados. Instalação altera presença física, não ativação.

`kernel.plan()` valida dependências, capabilities, singleton, routes e slots visuais antes de executar factories. Se `create()` falhar, os recursos registrados são liberados em ordem inversa. `kernel.shutdown()` para o server e libera composição e recursos em ordem topológica inversa. A reativação cria uma instância nova.

```ts
create(ctx) {
  const timer = setInterval(runJob, 1_000);
  ctx.onDispose(() => clearInterval(timer));
  return { read, write, stat };
}
```

## Exemplo de rollback

```text
1. middleware /game registrado       ✓
2. registro da route /game falha     ✗
3. disposer do middleware executa    ↩
4. módulo permanece desabilitado
```

Disposers devem ser idempotentes e tolerar cleanup parcial:

```ts
return async () => {
  if (!subscription) return;
  const current = subscription;
  subscription = undefined;
  await current.close();
};
```
