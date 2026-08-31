# Criando um módulo Gravewright

[English](../en/creating-a-module.md) · [Templates mínimos](../minimal-templates/README.md) · [Exemplo](../examples/dice-roller/README.md)

Este guia cobre o ciclo completo de um módulo: scaffold, implementação, tipos, composição, validação e release.

Para detalhes de cada contrato, consulte a [referência de superfícies públicas](surfaces/README.md).

## 1. Escolha um kind

Kinds descrevem o papel do módulo. Eles não selecionam uma implementação nem concedem privilégios ocultos.

| Kind | Papel esperado |
| --- | --- |
| `server` | Transporte do host, routes, middleware e slots |
| `campaign` | Dados e operações de campanha |
| `room` | Comportamento da mesa ou sala compartilhada |
| `marketplace` | Descoberta de módulos e recipes |
| `ruleset` | Regras e resolução do jogo |
| `addon` | Capacidade opcional e transversal |
| `asset` | Armazenamento, índice ou entrega de assets |
| `ui` | Capacidade de interface |
| `system` | Serviço transversal da plataforma, como autenticação, tradução, storage, sessões ou logging |

Somente `server` possui contrato mínimo no kernel. O projeto precisa de exatamente um server ativo. Todos os outros kinds são opcionais.

`system` e `ruleset` possuem fronteiras diferentes de propósito. Um módulo `system` oferece serviços técnicos da plataforma, independentes das mecânicas de RPG. Um `ruleset` cuida das regras, testes, combate, condições e resolução. Uma distribuição jogável completa continua sendo uma recipe que combina ambos com UI, assets e addons opcionais.

## 2. Gere o scaffold

Na raiz do projeto:

```bash
npm run grave -- new addon fog-of-war
```

Com a CLI instalada globalmente:

```bash
grave new addon fog-of-war
```

O nome é normalizado para kebab-case minúsculo. A estrutura gerada é:

```text
modules/fog-of-war/
├── manifest.json
├── index.ts
└── types.ts
```

Para adicionar README, teste e um evento de diagnóstico:

```bash
grave new addon fog-of-war --example-complete
```

Módulos novos não são ativados automaticamente.

## 3. Implemente o módulo

`index.ts` define metadados, composição, exports e a factory da instância:

```ts
import { defineModule } from "@gravewright/sdk";

export default defineModule({
  name: "fog-of-war",
  kind: "addon",
  provider: "community",
  version: "0.1.0",
  exports: { get: ["reveal", "isRevealed"] },
  create(ctx) {
    const revealed = new Set<string>();
    return {
      reveal(area: string) {
        revealed.add(area);
        ctx.diagnostic.record({
          event: "fog.revealed",
          actor: "System",
          action: "Reveal map area",
          status: "success",
          details: { area },
        });
      },
      isRevealed(area: string) {
        return revealed.has(area);
      },
    };
  },
});
```

`create()` roda na ativação. Imports não devem abrir portas, conectar bancos ou iniciar timers. O objeto retornado é a instância, mas somente nomes declarados em `exports` atravessam a fronteira.

## 4. Declare exports

```ts
exports: {
  get: ["roll", "reset"],
  prop: ["status"],
}
```

- `get` expõe valores legíveis e comandos chamáveis.
- `prop` expõe uma propriedade legível e gravável.
- `set` existe por compatibilidade, mas está deprecated. Prefira comandos explícitos em `get`, como `configure()`.

Todo export deve existir no retorno de `create()`. Um nome não pode ser duplicado nem aparecer em categorias diferentes.

## 5. Gere manifest e tipos

```bash
grave module build modules/fog-of-war
grave module build modules/fog-of-war --check
```

O segundo comando é adequado para CI e falha quando os artefatos estão desatualizados.

```json
{
  "name": "fog-of-war",
  "kind": "addon",
  "provider": "community",
  "version": "0.1.0",
  "entry": "./index.ts",
  "types": "./types.ts",
  "exports": {
    "get": ["reveal", "isRevealed"]
  }
}
```

Essa duplicação é intencional: o manifest estático é validado antes da importação do código.

## 6. Registre a API TypeScript

O `types.ts` gerado infere a API pública e registra o nome exato:

```ts
import type { InferModuleAPI } from "@gravewright/sdk";
import module from "./index.js";

export type FogOfWarAPI = InferModuleAPI<typeof module>;

declare module "@gravewright/sdk" {
  interface ModuleRegistry {
    "fog-of-war": FogOfWarAPI;
  }
}
```

Sincronize o registry do workspace:

```bash
npm run types:sync
npm run typecheck
```

O consumidor passa a receber a API inferida:

```ts
const fog = ctx.use("fog-of-war");
fog.get("reveal")("north-wing");
const visible = fog.get("isRevealed")("north-wing");
```

## 7. Consuma outro módulo

Declare a dependência antes de usar `ctx.use()`:

```ts
export default defineModule({
  name: "dice-log",
  kind: "addon",
  provider: "community",
  version: "1.0.0",
  dependencies: { "dice-roller": "^1.0.0" },
  exports: { get: ["rollAndLog"] },
  create(ctx) {
    const dice = ctx.use("dice-roller");
    return {
      rollAndLog() {
        return dice.get("roll")(20);
      },
    };
  },
});
```

O kernel valida presença, estado ativo, SemVer compatível e ordem de inicialização. Dependências usam o nome concreto do módulo, não apenas seu kind.

Quando esse módulo é instalado pelo marketplace, o Gravewright procura dependências ausentes pelo nome nos catálogos configurados. Ele valida todas as faixas SemVer, rejeita ciclos e versões locais incompatíveis, prepara o grafo inteiro e instala em ordem topológica: dependências primeiro, módulo solicitado por último. A instalação não ativa módulos automaticamente.

## 8. Componha routes, middleware e slots

Módulos publicam handlers sem depender de Express:

```ts
import { defineModule, type BaseRequest, type BaseResponse } from "@gravewright/sdk";

export default defineModule({
  name: "character-sheet",
  kind: "ui",
  provider: "community",
  version: "1.0.0",
  routes: { "/characters": "characters" },
  exports: { get: ["characters"] },
  create(_ctx) {
    return {
      characters(_request: BaseRequest, response: BaseResponse) {
        response.json({ characters: [] });
      },
    };
  },
});
```

Os pontos de composição mapeiam mounts ou slots para exports:

```ts
routes: { "/characters": "characters" },
middleware: { "/characters": ["authenticate", "audit"] },
slots: { "room.toolbar": ["toolbarButton"] },
```

Todo valor referenciado também precisa estar em `exports.get`. Registrars retornam disposers para rollback e desativação.

## 9. Diagnóstico

Registre ações semânticas e nomes públicos, nunca secrets ou payloads brutos:

```ts
ctx.diagnostic.record({
  event: "dice.rolled",
  actor: "Player",
  action: "Roll d20",
  status: "success",
  details: { sides: 20, result: 10 },
});
```

`status` informa se a ação de software funcionou, não se o resultado teve sucesso no RPG.

```bash
grave run --diagnostic
```

Não registre tokens, IDs de sessão, paths privados, corpos de request ou dados pessoais.

## 10. Ative e valide

Defina o estado em `gravewright.modules.json`:

```json
{
  "server": "active",
  "fog-of-war": "active"
}
```

Execute:

```bash
npm run types:sync
npm run typecheck
npm test
npm run grave -- doctor
npm run grave -- run
```

`grave doctor` encontra manifests inválidos, problemas de estado, dependências ausentes e configurações incorretas de server.

## 11. Teste a capacidade

Teste o comportamento público, incluindo falhas, disposers, chamadas de dependência e drift do manifest:

```ts
import assert from "node:assert/strict";
import test from "node:test";

test("roll stays inside the requested die", () => {
  const result = Math.floor(Math.random() * 6) + 1;
  assert.ok(result >= 1 && result <= 6);
});
```

## 12. Publique uma release

O marketplace instala releases, nunca a branch `main`.

1. Gere um ZIP com `manifest.json` e a entry.
2. Crie uma release versionada e imutável.
3. Calcule o SHA-256 do ZIP.
4. Publique um manifest estável, como `latest.json`.
5. Envie essa URL ao catálogo do marketplace.

O manifest remoto acrescenta:

```json
{
  "name": "fog-of-war",
  "kind": "addon",
  "provider": "community",
  "version": "1.0.0",
  "entry": "./index.js",
  "exports": { "get": ["reveal", "isRevealed"] },
  "download_url": "https://example.org/releases/fog-of-war-1.0.0.zip",
  "download_sha256": "64-caracteres-hexadecimais"
}
```

O manifest estável pode apontar para uma versão nova no futuro. O ZIP publicado deve permanecer imutável.

## Checklist

- Nome em kebab-case minúsculo, igual ao diretório e à chave do registry.
- Versão SemVer válida.
- Todo alvo de `ctx.use()` aparece em `dependencies`.
- Todo valor exposto ou composto é declarado explicitamente.
- Imports não causam efeitos externos.
- `types.ts` amplia `ModuleRegistry` com o nome entre aspas.
- Build `--check`, typecheck, testes e doctor passam.
- ZIP e SHA-256 da release são imutáveis e correspondem ao manifest remoto.
