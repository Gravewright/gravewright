# Recipes e providers de capabilities

Uma recipe instala uma composição reproduzível. Dependências concretas são
resolvidas automaticamente; capabilities substituíveis exigem a escolha explícita
de um provider.

```json
{
  "schema_version": 1,
  "kind": "recipe",
  "name": "classic-table",
  "title": "Classic Table",
  "version": "1.0.0",
  "modules": [
    { "manifest_url": "https://example.org/server.json", "state": "active" },
    { "manifest_url": "https://example.org/sqlite.json", "state": "active" },
    { "manifest_url": "https://example.org/game.json", "state": "active" }
  ],
  "capabilities": {
    "gravewright.storage": "sqlite-storage"
  }
}
```

O plano verifica se o módulo escolhido fornece uma versão compatível. Outros
providers da mesma capability selecionada são desabilitados pelo plano. O projeto
resultante ainda precisa possuir exatamente um server ativo.
