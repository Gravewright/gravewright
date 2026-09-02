# Documentação do Gravewright

Este guia documenta o repositório na versão `0.1.0`. As APIs ainda são pré-1.0; a compatibilidade segue a [política de governança do SDK](../SDK-GOVERNANCE.md).

## 1. Visão geral

Gravewright é um VTT extensível construído sobre um pequeno kernel modular. Gravewright é o produto, o kernel é sua infraestrutura modular interna, o SDK é a superfície pública de autoria e os módulos são extensões do VTT. O host descobre módulos locais, valida manifests, planeja uma composição respeitando dependências, cria os módulos, inicia os três papéis estruturais e libera seus recursos. Extensões comuns usam `kind: "module"` e podem ser ativadas ou desativadas durante a execução.

O sistema não escolhe framework web, banco de dados ou renderizador do navegador. Implementações fornecem essas decisões através de contratos pequenos do SDK.

## 2. Arquitetura

```text
CLI / host
   │ descobre modules/* e lê gravewright.modules.json
   ▼
@gravewright/kernel ── valida manifests e grafo de dependências
   │
   ├── exatamente um server ativo
   ├── exatamente um backend ativo
   ├── exatamente um frontend ativo
   └── zero ou mais módulos de funcionalidade ativos
          │
          └── dependência declarada → somente exports públicos
```

O host raiz (`src/start-gravewright.ts`) cria um `Kernel`, carrega cada diretório com `manifest.json`, aplica o estado persistido e inicializa o plano. `@gravewright/sdk` contém contratos; `@gravewright/kernel`, carregamento e orquestração; `@gravewright/ui`, componentes Vue e CSS opcionais.

Os limites são explícitos, mas módulos não são isolados: o código importado tem as permissões do processo hospedeiro.

## 3. Manifest

Cada módulo possui `modules/<diretório>/manifest.json`:

```json
{
  "name": "dice-tools",
  "kind": "module",
  "provider": "community",
  "version": "1.2.0",
  "entry": "./index.ts",
  "types": "./types.ts",
  "dependencies": { "rules": "^1.0.0" },
  "tooling": { "read": true, "stat": true },
  "exports": { "get": ["roll"] }
}
```

| Campo | Obrigatório | Significado |
| --- | --- | --- |
| `name` | sim | Identificador não vazio e único na instalação |
| `kind` | sim | `server`, `frontend`, `backend` ou `module` |
| `provider` | sim | `core`, `community`, `official`, `licensed` ou `partner` |
| `version` | sim | Versão semântica válida |
| `entry` | sim | Factory contida no diretório do módulo |
| `types` | não | Arquivo de aumento de tipos contido no módulo |
| `dependencies` | não | Nomes concretos de módulos e intervalos SemVer |
| `tooling` | não | Operações administrativas `read`, `write` ou `stat`; somente `true` é aceito |
| `exports.get` | não | Nomes públicos únicos; o objeto `exports` é obrigatório |
| `manifest_url` | não | String que identifica um manifest remoto |
| `download_url` | não | String de URL estável para o arquivo da release mais recente |
| `download_sha256` | não | SHA-256 hexadecimal, com 64 caracteres, desse arquivo |

Campos desconhecidos, `exports.set` e `exports.prop` são rejeitados. Caminhos são conferidos novamente depois da resolução de links simbólicos. Consulte o [schema v1](../schema/manifest-v1.json).

`gravewright.modules.json` guarda o estado da instalação separadamente:

```json
{ "my-server": "active", "dice-tools": "disabled" }
```

Entradas ausentes significam `disabled`. Escritas usam arquivo temporário e renomeação atômica.

## 4. Lifecycle

A inicialização segue esta ordem:

1. Valida a composição e ordena topologicamente dependências antes de consumidores.
2. Importa e cria cada módulo ativo na ordem planejada.
3. Inicia backend, frontend e server, nessa ordem.
4. Se houver falha, interrompe componentes estruturais iniciados/tentados e libera recursos em ordem inversa de módulo e registro.

O encerramento para server, frontend e backend, então libera recursos na ordem inversa de ativação. Chamar `shutdown()` novamente após o encerramento é seguro. Use `ctx.onDispose(fn)` para rotas, listeners, timers e conexões.

Somente `module` admite `activate()` e `disable()` em runtime. Trocar estruturas exige reinício. Falhas de ativação revertem estado e recursos. Um módulo com dependente ativo não pode ser desativado. Mutações são serializadas.

## 5. Dependências

Dependências são identidades concretas e intervalos SemVer, não capacidades ou tipos:

```json
"dependencies": { "character-store": ">=1.2 <2" }
```

O alvo deve existir, estar ativo, satisfazer o intervalo e não criar ciclo. Autodependência falha. Dependências transitivas não concedem acesso: se `a` usa `c`, deve declarar `c`, mesmo em `a → b → c`. `ctx.use("character-store")` aceita somente nomes declarados diretamente.

Dependências npm são diferentes. O SDK normalmente deve ser `peerDependency`; bibliotecas de runtime ficam no `package.json` do módulo.

## 6. Exports

`exports.get` é toda a superfície pública. Cada nome declarado deve ser propriedade própria do objeto retornado. Consumidores usam:

```ts
const rules = ctx.use("rules");
const calculate = rules.get("calculate");
```

Um nome não declarado falha mesmo que exista no objeto. Não há setter público, injeção de propriedade, busca por tipo ou capacidade. Prefira poucos exports orientados a comportamento.

## 7. Contrato do server

Um `server` declara e implementa `start`, `stop`, `http`, `route` e `middleware`. `route(mount, handler)` e `middleware(mount, handler)` retornam disposers. Requests e responses usam `BaseRequest` e `BaseResponse`, neutros de transporte. `http` é intencionalmente `unknown`; consumidores precisam definir sua própria integração tipada.

O `realtime` opcional, quando listado em `exports.get`, fornece `toRoom`, `toGM` e `toWhisper`, recebendo mensagens `{ type, payload }`. O SDK não prescreve WebSocket, SSE ou persistência.

## 8. Contrato do backend

Um `backend` declara e implementa `start()` e `stop()`, síncronos ou assíncronos. Ele controla o lifecycle da aplicação no servidor e persistência, mas não possui API obrigatória de banco. Exponha armazenamento de domínio por exports explícitos e dependências declaradas. O backend inicia antes do server.

## 9. Contrato do frontend

O módulo Node `frontend` declara e implementa `start()` e `stop()` para disponibilizar o bundle do navegador. O kernel nunca chama métodos DOM.

O bundle pode implementar `ClientFrontend`: `mount(root)`, `unmount()` e `slot(name, module, contribution)`. Uma contribuição tem `id`, ordem opcional e `mount(container)`, que pode retornar disposer. Nomes de slot são identificadores de protocolo escolhidos pelo frontend. `@gravewright/ui` é opcional e exporta componentes Vue e estilos em `@gravewright/ui/styles`.

## 10. Módulos de funcionalidade

`module` representa extensões comuns do Gravewright, incluindo funcionalidades de produto e jogo. Não tem exports obrigatórios e pode ser ativado ou desativado a quente. A factory recebe somente `use`, `onDispose` e `diagnostic`, pode ser assíncrona e deve retornar um objeto. Registre o cleanup assim que adquirir um recurso.

`tooling` administrativo é separado dos exports de produto. Se declarado, o objeto deve implementar a operação. O host usa `Kernel.tooling`; `grave help` mapeia para `read`, `grave test` para `write` e `grave doctor` pode chamar `stat`.

## 11. CLI

Neste repositório use `npm run grave -- <comando>`; com o binário instalado, use `grave`.

| Comando | Finalidade |
| --- | --- |
| `grave run [--diagnostic] [--diagnostic-file caminho]` | Inicia o projeto e opcionalmente grava diário de ações sanitizado |
| `grave new <kind> [name]` | Cria módulo; aceita `--minimal`, `--example-complete`, tooling, `--realtime`, metadados, testes, README, Git e `--dry-run` |
| `grave doctor [--json]` | Verifica inventário, estado, manifests, dependências, estruturas e health tooling |
| `grave test [module]` | Executa tooling `write` de um ou todos os módulos ativos elegíveis |
| `grave help [comando-ou-tópico]` | Mostra ajuda ou chama tooling `read` para um tópico |
| `grave module build [caminho] [--check]` | Gera ou verifica manifest e tipos a partir de `defineModule()` |

Códigos de saída: `0` sucesso, `1` falha operacional/validação e `2` erro de uso ou descoberta do projeto.

## 12. Criação de módulo

```bash
npm run grave -- new module dice-tools --example-complete
```

Edite `modules/dice-tools/index.ts`, adicione nomes públicos a `exports.get`, declare todas as dependências concretas e execute:

```bash
npm run grave -- module build modules/dice-tools
npm run grave -- module build modules/dice-tools --check
npm run grave -- doctor
```

O build importa a entrada TypeScript, lê metadados de `defineModule` e gera `manifest.json` e `types.ts`. O arquivo de tipos aumenta `ModuleRegistry`, tornando nomes e exports type-safe. Depois da revisão, ative explicitamente em `gravewright.modules.json`.

## 13. Exemplos mínimos

```ts
import { defineModule } from "@gravewright/sdk";

export default defineModule({
  name: "dice-tools",
  kind: "module",
  provider: "community",
  version: "1.0.0",
  exports: { get: ["roll"] },
  create(ctx) {
    const timer = setInterval(() => {}, 60_000);
    ctx.onDispose(() => clearInterval(timer));
    return { roll: (sides: number) => 1 + Math.floor(Math.random() * sides) };
  },
});
```

Módulo que registra rota (o manifest deve declarar o server concreto):

```ts
create(ctx) {
  const route = ctx.use("my-server").get("route") as RouteRegistrar;
  ctx.onDispose(route("/health", (_request, response) => {
    response.status(200).json({ ok: true });
  }));
  return {};
}
```

## 14. Troubleshooting

| Sintoma | Solução |
| --- | --- |
| `Expected exactly one active ...` | Ative exatamente um módulo de cada tipo estrutural e desative duplicados |
| `requires missing/disabled dependency` | Instale e ative o nome exato ou atualize o consumidor |
| `requires ... but ... is loaded` | Use versão compatível ou altere o intervalo após testes |
| `Circular dependency detected` | Extraia comportamento compartilhado e remova uma aresta do grafo |
| `cannot use undeclared dependency` | Adicione nome concreto e intervalo a `dependencies` |
| `cannot access export` | Publique em `exports.get` somente se fizer parte do contrato |
| `manifest/types is stale` | Rode `grave module build <caminho>` e versione os gerados |
| `entry/types outside module directory` | Use caminho relativo interno; escapes por symlink são rejeitados |
| Projeto não abre uma mesa | Rode `grave doctor`; o checkout limpo não inclui estruturas configuradas |

Use `grave doctor --json` em automações. Diagnóstico é opt-in; revise antes de compartilhar.

## 15. Referência do SDK

### Valores e helpers

- `MODULE_KINDS`, `ModuleKind`; `MODULE_PROVIDERS`, `ModuleProvider`; `ModuleState`.
- `STRUCTURAL_EXPORTS`: nomes mínimos por tipo estrutural.
- `defineModule(definition)`: helper tipado com metadados congelados em `.definition`.
- `InferModuleAPI<typeof module>`: deriva a superfície pública `get`.

### Tipos de autoria

- `ModuleDefinition<T>`, `DefinedModule`, `ModuleManifest`, `ModuleTooling`.
- `ModuleRegistry`: interface vazia aumentada para tipar dependências concretas.
- `Context<R>`: `use`, `onDispose` e `diagnostic` tipados.
- `DynamicContext`: fallback sem nomes estáticos para hosts dinâmicos.
- `ModuleAPI`, `ModuleRef<T>`, `Dispose`.

### Contratos

- `ServerContract`, `BackendContract`, `FrontendContract`, `ContractDefinition<K>`.
- `BaseRequest`, `BaseResponse`, `RouteHandler`, `RouteRegistrar`.
- `MiddlewareNext`, `MiddlewareHandler`, `MiddlewareRegistrar`.
- `ServerMessage`, `ServerRealtime`.
- `ClientFrontend`, `FrontendSlotContribution`, `FrontendSlotRegistrar`.
- `DiagnosticAction`, `DiagnosticActionStatus`, `DiagnosticReporter`.

### API do kernel

`@gravewright/kernel` exporta `Kernel`, `KernelOptions`, `LoadOptions` e `ActivationPlan`. Métodos principais: `load`, `plan`, `initialize`, `use`, `tooling`, `activate`, `disable` e `shutdown`. `load` existe apenas antes da inicialização; `activate`/`disable`, depois e somente para funcionalidades.
