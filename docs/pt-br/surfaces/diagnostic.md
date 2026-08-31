# Diagnóstico

`ctx.diagnostic.record()` emite um evento semântico de auditoria opt-in.

```ts
ctx.diagnostic.record({
  event: "dice.roll",
  actor: "Player",
  action: "Roll d20",
  status: "success",
  details: { sides: 20, result: 10 },
});
```

`status` descreve sucesso técnico da execução, não sucesso nas regras do RPG. O host grava somente quando iniciado com `grave run --diagnostic`.

Diagnostics são observabilidade opt-in e best-effort. Sem reporter configurado,
`record()` é intencionalmente no-op e nunca altera o comportamento do módulo.
Não use diagnostics como canal de controle ou tratamento de erro: falhas fatais
devem continuar sendo expressas por throw ou retorno explícito.

Use nomes públicos e ações semânticas. Nunca emita tokens, IDs de sessão, paths privados, requests completos, secrets ou dados pessoais. Campos inseguros são filtrados, mas o autor deve minimizar na origem.

## Sucesso e falha

```ts
try {
  const result = roll(20);
  ctx.diagnostic.record({ event: "dice.roll", actor: "Player", action: "Roll d20", status: "success", details: { result } });
  return result;
} catch {
  ctx.diagnostic.record({ event: "dice.roll", actor: "Player", action: "Roll d20", status: "failure", reason: "Dice service unavailable" });
  throw new Error("roll failed");
}
```

Bom detalhe: `{ sides: 20, result: 10 }`. Mau detalhe: `{ token, sessionId, requestBody, absolutePath }`.
