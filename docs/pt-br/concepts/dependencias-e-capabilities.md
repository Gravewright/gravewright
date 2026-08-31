# Dependências e capabilities

O Gravewright possui duas relações porque elas respondem perguntas diferentes.

## Dependências concretas

Use `dependencies` quando o módulo exige outro pela identidade exata:

```ts
dependencies: { "dice-roller": "^1.2.0" }
```

Só então o factory pode chamar `ctx.use("dice-roller")`. Dependências transitivas
não concedem acesso: se A depende de B e B depende de C, A não pode usar C sem
declará-lo diretamente.

## Capabilities substituíveis

Use `requires` quando o consumidor precisa de um protocolo versionado, sem fixar
a implementação:

```ts
requires: { "gravewright.storage": "^1.0.0" }
```

Um provider declara:

```ts
provides: { "gravewright.storage": "1.1.0" }
```

O consumidor chama `ctx.capability("gravewright.storage")`. O plano precisa
encontrar exatamente um provider ativo e compatível. Recipes podem escolher o
provider explicitamente para tornar a distribuição reproduzível.

## Regra de decisão

- Use dependência para um colaborador nomeado com API específica do módulo.
- Use capability para um protocolo substituível com várias implementações.
- Nunca trate dependência transitiva como permissão implícita.

O marketplace instala dependências concretas ausentes em ordem topológica, mas
informa o grafo antes da operação e não ativa os módulos instalados.
