# Tooling administrativo opcional

`read`, `stat` e `write` são integrações opcionais de host/CLI. Não pertencem aos contratos dos kinds, não entram automaticamente em `exports.get` e nunca ficam disponíveis no `Context`.

```json
{ "tooling": { "read": true, "stat": true, "write": true } }
```

- `read` alimenta `grave help <module> [tópico]` com documentação estruturada.
- `stat` alimenta `grave doctor` com informações de saúde do próprio módulo.
- `write` alimenta `grave test [módulo]` com um harness de autoteste.

Se uma operação for declarada, a factory precisa implementá-la. Esses hooks são conveniências operacionais, não sandbox nem protocolo entre módulos.
