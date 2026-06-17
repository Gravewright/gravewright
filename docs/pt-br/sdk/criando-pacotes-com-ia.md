# Criando Pacotes Com IA

O Gravewright foi desenhado para autores descreverem um sistema ou extensão em linguagem natural, deixarem o CLI gerar um scaffold seguro e usarem `grave package doctor` para manter o pacote dentro do contrato do SDK.

## O ciclo

1. Gere um scaffold de pacote.
2. Peça para um assistente de IA editar apenas o diretório desse pacote.
3. Valide o pacote.
4. Cole a saída do doctor de volta no assistente.
5. Repita até `grave package doctor` ficar limpo.

## Exemplo de ruleset

```bash
grave ruleset new my-rpg --name "My RPG" --sheets --rolls --combat --content
```

Prompt:

```text
You are editing a Gravewright SDK v1 ruleset package.

Only edit files inside data/packages/rulesets/my-rpg.
Do not edit Gravewright core.
Do not invent capabilities.
Prefer declarative schemas, sheets, rules, mappings, content packs, and locales.
After each change, the package must pass:

grave package validate data/packages/rulesets/my-rpg
grave package doctor my-rpg
```

## Exemplo de addon

```bash
grave addon new my-addon --name "My Addon" --js --settings
```

Prompt:

```text
You are editing a Gravewright SDK v1 addon package.

Only edit files inside data/packages/addons/my-addon.
Use window.GravewrightSDK.register({ id, setup, ready }).
Only call SDK APIs allowed by the declared capabilities.
Do not access raw database, raw filesystem, backend internals, or undocumented globals.
```

## Corrigindo saída do doctor

Quando o doctor reportar erros, cole a saída no assistente:

```bash
grave package doctor my-rpg --json
```

Prompt:

```text
Here is the Gravewright package doctor output.
Explain what is wrong, then provide a minimal patch.
Only change package files.
Do not change Gravewright core.
Do not invent capabilities.
```

## Regras de segurança

- Não envie `.env`, arquivos de banco, mapas privados ou conteúdo privado de campanha para ferramentas externas de IA.
- Não peça para a IA contornar erros do validador.
- Não use conteúdo comercial ou protegido por copyright sem direito de distribuição.
- Trate pacotes com `assets.scripts` como JavaScript confiável.
- Rode `grave backup` antes de aplicar mudanças de pacote em uma mesa importante.
