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
- Composição registra middleware, routes e slots.
- O server inicia depois da composição completa.
- Disable executa disposers em ordem reversa.

`gravewright.modules.json` armazena `active` ou `disabled`; ausentes ficam desabilitados. Instalação altera presença física, não ativação.

A inicialização do kernel é one-shot. Reativação cria outra instância e não preserva estado volátil. Valores JavaScript já extraídos podem sobreviver ao disable.

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
