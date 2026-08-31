# Dependencies

`dependencies` associa nomes concretos de módulos a faixas SemVer.

```ts
dependencies: {
  "dice-roller": "^1.0.0",
  "event-log": "~2.3.0",
}
```

Elas atuam em três etapas:

1. O marketplace resolve módulos ausentes e instala o grafo em ordem topológica.
2. O kernel valida presença, estado ativo e versões antes das factories.
3. `ctx.use()` autoriza comunicação somente com nomes declarados.

Uma versão instalada compatível é reutilizada. Entrada ausente no catálogo, incompatibilidade ou ciclo cancela a instalação antes do commit. Instalar não ativa automaticamente.

Dependa da menor API pública estável possível. Uma dependência continua sendo uma decisão de acoplamento de produto.

## Exemplo de instalação transitiva

```text
combat-ui 1.0.0
└── combat ^2.0.0
    ├── dice-roller ^1.2.0
    └── event-log ~3.1.0
```

Instalar `combat-ui` produz:

```text
dice-roller → event-log → combat → combat-ui
```

Se `event-log 3.1.4` já estiver instalado, será reutilizado. Se houver `event-log 4.0.0`, a operação para por incompatibilidade em vez de substituí-lo silenciosamente.

```ts
dependencies: { combat: "^2.0.0" }
```

O manifest usa nomes; URLs continuam sendo responsabilidade do catálogo.

## Capabilities substituíveis

```ts
requires: { "gravewright.storage": "^1.0.0" }
provides: { "gravewright.storage": "1.2.0" }
```

O consumidor chama `ctx.capability("gravewright.storage")`. Deve existir exatamente
um provider ativo compatível. Recipes escolhem implementações pelo mapa
`capabilities`. Use `dependencies` quando o acoplamento concreto for intencional.
