import { capabilityDescriptions } from "../locales/pt-br.capabilities.mjs";
import { resolveCapabilityRegistry } from "./capability-registry.mjs";

const capabilityRegistryResult = resolveCapabilityRegistry();
const capabilityRegistry = capabilityRegistryResult.registry;

const capabilityGroups = [
  ["sdk-capabilities-atores-itens", "Capabilities: atores e itens", ["actors.", "items."]],
  ["sdk-capabilities-assets-ui", "Capabilities: assets e interface", ["assets.", "ui."]],
  ["sdk-capabilities-eventos", "Capabilities: bus, eventos e comandos", ["bus.", "events.", "commands."]],
  ["sdk-capabilities-jogo", "Capabilities: chat, cartas e combate", ["chat.", "cards.", "combat.", "dice.", "rolls."]],
  ["sdk-capabilities-conteudo", "Capabilities: conteúdo, diários e PDF", ["content.", "journals.", "handouts.", "pdf."]],
  ["sdk-capabilities-cena", "Capabilities: cenas e tokens", ["scene.", "tokens."]],
  ["sdk-capabilities-regras", "Capabilities: regras, fichas e persistência", ["rules.", "sheets.", "settings", "storage.", "locales", "permissions."]],
  ["sdk-capabilities-automacao", "Capabilities: automação, interação e fluxos", ["packages.", "campaign.members.", "users.", "automation.", "interactions.", "audio.", "sounds.", "navigation.", "input.", "workflows.", "gameplay.", "timelines."]],
];

function capabilityGuidance(name) {
  if (name === "actors.write") return {
    use: "Use para criar atores, atualizar campos públicos do recurso principal e excluir quando o contrato/authority do usuário permitirem. Para alterar somente system data validada, prefira actors.data.write.",
    limit: "Não ignora ownership, não escolhe outra campaign arbitrariamente, não escreve colunas privadas de persistence, não muda permissões e não concede papel ao usuário.",
    avoid: "Não envie uma representação de banco, permissions_json, campaign_id de outra mesa ou substituição completa de data. Use DTO público e patch específico.",
  };
  if (name === "scene.geometry.write") return {
    use: "Use para criar, atualizar, dividir, mover ou excluir walls; alterar doors; e criar/atualizar/excluir lights como geometria lógica da cena.",
    limit: "Não fornece PIXI, RenderTexture, lighting layer, shaders, GPU buffers, canvas interno nem qualquer objeto do renderer. Também não ignora a authority de GM na cena.",
    avoid: "Não tente sincronizar geometria manipulando sprites/layers locais. Envie a operação lógica ao serviço; o host atualiza persistência, realtime e renderer.",
  };
  const read = name.endsWith(".read") || name === "content.index" || name === "content.references" || name === "permissions.inspect";
  const write = /\.(write|manage|move)$/.test(name) || name === "rules.actions";
  const asset = name.startsWith("assets.");
  const manifestOnly = (capabilityRegistry.capabilities[name].methods || []).length === 0;
  if (read) return {
    use: "Declare quando o pacote precisa consultar dados que o usuário atual já tem permissão para ver.",
    limit: "Não amplia visibilidade, não ignora ownership e não autoriza alteração. O servidor filtra a resposta para a campanha e o usuário atuais.",
    avoid: "Não use a leitura para montar um cache permanente de dados privados nem presuma que GM e Player recebem a mesma coleção.",
  };
  if (write) return {
    use: "Declare somente quando o pacote inicia uma mudança autoritativa nesse domínio.",
    limit: "A capability expõe a intenção, mas o servidor ainda valida papel, ownership, campanha, schema e estado atual.",
    avoid: "Não use para contornar a UI, alterar recursos de outro usuário ou substituir dados inteiros quando existe uma operação de patch específica.",
  };
  if (asset) return {
    use: "Declare quando o manifest fornece ou carrega exatamente esse tipo de asset.",
    limit: "Autoriza apenas assets declarados por caminhos seguros dentro do pacote; não concede filesystem nem rede arbitrária.",
    avoid: "Não use caminhos absolutos, traversal com '..', URLs remotas como substituto de asset empacotado ou tipos diferentes do declarado.",
  };
  if (manifestOnly) return {
    use: "Esta é uma capability declarativa: use-a quando o bloco correspondente aparece no manifest/provides.",
    limit: "Ela valida e habilita metadados consumidos pelo core, mas não cria um método JavaScript no objeto sdk.",
    avoid: "Não tente chamar sdk com o nome da capability e não declare o gate sem fornecer o documento ou descriptor correspondente.",
  };
  return {
    use: "Declare quando o runtime do pacote chama uma das APIs listadas abaixo.",
    limit: "O gate libera somente essas APIs públicas e mantém validação de contexto e permissões no host.",
    avoid: "Não substitua a API por fetch em rota interna, acesso a globals privados ou manipulação do DOM do core.",
  };
}

function authorityLevel(name) {
  if (name === "storage.sqlite") return "STORAGE";
  if (/^(bus\.|events\.|commands\.)/.test(name)) return "EVENT";
  if (/^(assets\.ui|ui\.|sheets\.|scene\.overlays)/.test(name)) return "UI";
  if (/\.(write|manage|move)$/.test(name) || ["rules.actions", "handouts.present"].includes(name)) return /^(scene\.|combat\.|cards\.)/.test(name) ? "ADMIN-LIKE" : "WRITE";
  if (/\.read$/.test(name) || ["content.index", "content.references", "permissions.inspect"].includes(name)) return "READ";
  return "UI";
}

function permissionRequirements(name) {
  if (/^(actors|items)\.read/.test(name)) return "O usuário deve ser membro da campanha e enxergar o recurso por ownership/permissão efetiva.";
  if (/^(actors|items)\.(write|data\.write)/.test(name)) return "Criação exige authority apropriada na campanha; alteração/exclusão exige que o usuário possa editar o recurso. O servidor valida tipo, schema e versão.";
  if (/^tokens\.(read|move|manage)/.test(name)) return name === "tokens.read" ? "O usuário recebe somente tokens visíveis." : "GM pode operar todos; Player somente tokens que controla e apenas nas operações permitidas.";
  if (/^scene\..*\.write|^scene\.effects\.write|^scene\.fog\.write|^scene\.images\.write/.test(name)) return "Normalmente requer GM/authority de edição da cena. A cena deve pertencer à campanha ativa.";
  if (/^scene\..*\.read|^scene\.read/.test(name)) return "Requer membership e visibilidade da cena; camada GM e objetos ocultos são filtrados para Players.";
  if (/^combat\.manage|^cards\.manage/.test(name)) return "Requer authority de GM ou operação expressamente permitida pelo serviço autoritativo.";
  if (/^(journals|pdf|chat|content|assets\.library)/.test(name)) return "Requer membership; o serviço retorna ou altera somente conteúdo visível/editável pelo usuário atual.";
  if (name === "permissions.inspect") return "Só consulta a decisão efetiva do próprio usuário; não consulta nem altera permissões de terceiros.";
  if (name === "settings") return "O escopo decide a autoridade: client é local, user pertence ao usuário, campaign/package exigem authority apropriada.";
  if (name === "storage.sqlite") return "Campaign scope exige pacote ativo e contexto de campanha; global scope segue a autoridade definida pelo host. Nunca há acesso ao banco de outro pacote.";
  return "O pacote precisa estar instalado, habilitado e ativo; operações continuam limitadas ao contexto e papel do usuário atual.";
}

function possibleErrors(name) {
  const errors = ["CAPABILITY_REQUIRED: capability ausente ou método gated"];
  if (/read|write|manage|move|present|inspect|actions/.test(name)) errors.push("PERMISSION_DENIED: usuário/contexto sem authority");
  if (/write|manage|move|settings|storage|actions|geometry|fog|images/.test(name)) errors.push("VALIDATION_FAILED: payload, schema, parâmetro ou estado inválido");
  if (/actors|items|tokens|scene|combat|journals|cards/.test(name)) errors.push("NOT_FOUND: recurso inexistente, oculto ou fora da campanha");
  if (/write|manage|move/.test(name)) errors.push("STALE_VERSION / CONFLICT: versão ou estado mudou antes da gravação");
  if (name === "storage.sqlite") errors.push("QUERY_DISALLOWED / LIMIT_EXCEEDED: SQL não permitido, timeout, linhas, bytes ou tamanho excedidos");
  return errors.map((error) => `- ${error}`).join("\n");
}

function visibilityFiltering(name) {
  if (/^(actors|items|tokens|scene|chat|journals|content|pdf|cards|assets\.library)/.test(name)) return "Sim. O backend projeta a resposta conforme campanha, role, ownership, visibilidade do recurso e camada. Ausência na resposta pode significar ocultação, não inexistência.";
  if (/^(bus|events)\./.test(name)) return "Eventos e payloads são limitados ao pacote/campanha e devem carregar apenas dados que o usuário poderia observar pela API normal.";
  if (/\.write|\.manage|\.move|rules\.actions/.test(name)) return "A escrita não recebe dados privados adicionais. O servidor resolve o alvo e recusa operações fora do recorte autorizado.";
  return "Não retorna coleções de jogo diretamente; ainda assim, contexto e payload não devem ser usados para inferir dados ocultos.";
}

function lifecycleNotes(name) {
  if (["bus.subscribe", "events.subscribe", "settings"].includes(name)) return "Guarde a função de unsubscribe retornada e execute-a no teardown/unmount. Não acumule subscriptions ao reabrir fichas ou aplicações.";
  if (["commands.register", "bus.provide", "sheets.controller", "sheets.runtime", "ui.slots", "ui.applications", "combat.runtime"].includes(name)) return "Registre uma vez em setup. Remova listeners, observers, timers e mounts próprios em unmount/close; não registre novamente a cada render.";
  if (name === "assets.scripts" || name === "assets.styles") return "Assets carregam enquanto o pacote está ativo na página. Incremente version, execute package update e recarregue para invalidar cache.";
  if (name === "storage.sqlite") return "Migrations são aplicadas e versionadas pelo host. Nunca edite uma migration já aplicada; crie a próxima e inclua storage em backups.";
  return "Sem teardown especial. Aguarde Promises quando houver runtime assíncrono e trate a possibilidade de a campanha/recurso mudar antes da conclusão.";
}

function relatedCapabilities(name) {
  const domain = name.split(".")[0];
  const relations = {
    actors: ["actors.read", "actors.write", "actors.data.write", "permissions.inspect", "tokens.mappings"],
    items: ["items.read", "items.write", "items.data.write", "permissions.inspect"],
    tokens: ["tokens.read", "tokens.move", "tokens.manage", "actors.read", "scene.read"],
    scene: ["scene.read", "scene.geometry.read", "scene.geometry.write", "scene.effects.read", "scene.effects.write", "scene.fog.read", "scene.fog.write", "scene.images.read", "scene.images.write"],
    combat: ["combat.config", "combat.read", "combat.manage", "combat.runtime", "cards.read", "cards.manage", "events.subscribe"],
    cards: ["cards.read", "cards.manage", "combat.manage", "events.subscribe"],
    sheets: ["sheets.declarative", "sheets.html", "sheets.controller", "sheets.runtime", "actors.data.write", "items.data.write"],
    storage: ["settings", "storage.sqlite"],
    settings: ["storage.sqlite", "events.subscribe"],
    bus: ["bus.publish", "bus.subscribe", "bus.provide", "bus.request"],
  };
  return [...new Set((relations[domain] || allCapabilities.map(([item]) => item).filter((item) => item.startsWith(`${domain}.`))).filter((item) => item !== name))];
}

function minimalExample(name, methods) {
  const declarations = `\`\`\`json\n"capabilities": ["${name}"]\n\`\`\``;
  if (!methods.length) return `${declarations}\n\nEsta capability é consumida pelo manifest/descriptor; não existe uma chamada \`sdk.${name}\`.`;
  const examples = {
    "actors.read": "const actors = await sdk.actors.list();\nconst actor = await sdk.actors.get(actorId);",
    "actors.write": "const actor = await sdk.actors.create({ name: \"Aria\", type: \"character\" });\nawait sdk.actors.update(actor.id, { name: \"Aria Ventos\" });",
    "actors.data.write": "await sdk.actors.patchData(actorId, { hp: { value: 8 } });",
    "tokens.move": "await sdk.tokens.move(tokenId, { x: 12, y: 8 });",
    "dice.roll": "await sdk.dice.roll({ formula: \"1d20+3\", label: \"Percepção\" });",
    "bus.subscribe": "const off = sdk.bus.subscribe(\"meu-pacote.evento\", handler);\n// teardown: off();",
    "bus.publish": "sdk.bus.publish(\"meu-pacote.evento\", { version: 1, resourceId });",
    "settings": "const value = sdk.settings.get(\"minha-setting\");\nconst off = sdk.settings.onChange(\"minha-setting\", handler);",
    "storage.sqlite": "await sdk.storage.sqlite.execute(\"campaign\", \"saveState\", params);\nconst rows = await sdk.storage.sqlite.query(\"campaign\", \"getState\", params);",
    "scene.geometry.write": "await sdk.scene.geometry.createWall(sceneId, wallInput);\nawait sdk.scene.geometry.setDoorState(sceneId, wallId, \"open\");",
  };
  const code = examples[name] || methods.map((method) => `await sdk.${method}(/* parâmetros do contrato */);`).join("\n");
  return `${declarations}\n\n\`\`\`js\n${code}\n\`\`\``;
}

function capabilityHref(name) {
  const group = capabilityGroups.find(([_slug, _title, prefixes]) => prefixes.some((prefix) => name === prefix || name.startsWith(prefix)));
  return group ? `${group[0]}.html#${name.toLowerCase().replace(/[^a-z0-9]+/g, "-")}` : "sdk-capabilities-runtime.html";
}

function capabilitySection(name, raw) {
  const methods = raw.methods || [];
  const guide = capabilityGuidance(name);
  const surfaces = (raw.surfaces || []).map((item) => `\`${item}\``).join(", ") || "nenhuma";
  const methodList = methods.length ? methods.map((method) => `- \`sdk.${method}\``).join("\n") : "Nenhum método de runtime. O uso acontece pelo manifest ou por arquivos declarativos.";
  const related = relatedCapabilities(name).map((item) => `[\`${item}\`](${capabilityHref(item)})`).join(", ") || "Nenhuma direta.";
  return `## \`${name}\`\n\n**Authority level:** \`${authorityLevel(name)}\` · **Status:** \`${raw.status}\` · **Superfícies:** ${surfaces}\n\n### O que autoriza\n\n${capabilityDescriptions[name] || raw.description}\n\n### Quando usar\n\n${guide.use}\n\n### O que NÃO autoriza\n\n${guide.limit}\n\n> [!IMPORTANT]\n> Declarar a capability não eleva o usuário, não ignora ownership e não troca o contexto para outra campanha.\n\n### Métodos liberados\n\n${methodList}\n\n### Requisitos de permissão do usuário\n\n${permissionRequirements(name)}\n\n### Exemplo mínimo\n\n${minimalExample(name, methods)}\n\n### Erros possíveis\n\n${possibleErrors(name)}\n\n### Segurança e visibility filtering\n\n${visibilityFiltering(name)}\n\n### Lifecycle e teardown\n\n${lifecycleNotes(name)}\n\n### Capabilities relacionadas\n\n${related}\n\n> [!WARNING]\n> **Não use assim:** ${guide.avoid}\n`;
}

const allCapabilities = Object.entries(capabilityRegistry.capabilities);
const generatedCapabilityGuides = capabilityGroups.map(([slug, title, prefixes]) => {
  const entries = allCapabilities.filter(([name]) => prefixes.some((prefix) => name === prefix || name.startsWith(prefix)));
  return {
    slug, section: "Referência de capabilities", title,
    summary: `Referência detalhada de ${entries.length} capabilities: uso, limites, APIs e anti-padrões.`,
    body: `# ${title}\n\nEsta página documenta ${entries.length} capabilities individualmente. Capability é gate de API, não elevação de privilégio: toda operação continua sujeita ao servidor.\n\n${entries.map(([name, raw]) => capabilitySection(name, raw)).join("\n")}`,
  };
});

const capabilityPageByName = new Map();
for (const [slug, _title, prefixes] of capabilityGroups) {
  for (const [name] of allCapabilities.filter(([cap]) => prefixes.some((prefix) => cap === prefix || cap.startsWith(prefix)))) {
    capabilityPageByName.set(name, `${slug}.html#${name.toLowerCase().replace(/[^a-z0-9]+/g, "-")}`);
  }
}
const capLink = (name) => `[\`${name}\`](${capabilityPageByName.get(name)})`;
const intentGuide = {
  slug: "sdk-mapa-de-poder", section: "Referência de capabilities", title: "Mapa de poder da SDK",
  summary: "Parta da intenção do pacote e descubra as capabilities mínimas necessárias.",
  body: `# Mapa de poder da SDK

Comece pela intenção, não pela lista de permissões. Declare o conjunto mínimo e teste a combinação como GM e Player.

## Tokens e atores

- **Reagir ao movimento de token:** ${capLink("events.subscribe")} + ${capLink("tokens.read")}.
- **Mover um token controlado:** ${capLink("tokens.move")}; adicione ${capLink("tokens.read")} somente se precisar consultar antes.
- **Criar ou excluir token:** ${capLink("tokens.manage")}: mais sensível que mover.
- **Ler a ficha visível:** ${capLink("actors.read")}.
- **Alterar dados validados da ficha:** ${capLink("actors.data.write")}.
- **Criar/renomear/excluir ator:** ${capLink("actors.write")}.

## Cena

- **Ler paredes, portas e luzes:** ${capLink("scene.geometry.read")}.
- **Criar/alterar geometria lógica:** ${capLink("scene.geometry.write")}.
- **Reagir a efeitos:** ${capLink("scene.effects.read")} ou ${capLink("events.subscribe")}.
- **Pintar/resetar fog:** ${capLink("scene.fog.write")}.
- **Colocar uma imagem autorizada:** ${capLink("scene.images.write")} + leitura da origem adequada.

> [!IMPORTANT]
> Geometria lógica significa walls, doors e lights. Não significa PIXI, RenderTexture, lighting layer, shaders, GPU buffers ou acesso ao renderer.

## Combate e cartas

- **Iniciativa numérica declarativa:** ${capLink("combat.config")} + regras/rolagens do ruleset.
- **Iniciativa por cartas:** ${capLink("combat.manage")} + ${capLink("cards.read")} + ${capLink("cards.manage")} + ${capLink("events.subscribe")}.
- **Somente exibir o combate:** ${capLink("combat.read")}.
- **Painel customizado:** ${capLink("combat.runtime")} + uma capability de UI apropriada.

## Conteúdo e interface

- **Pesquisar conteúdo permitido:** ${capLink("content.index")}.
- **Abrir referência universal:** ${capLink("content.references")}.
- **Apresentar handout sem dar acesso permanente:** ${capLink("handouts.present")}.
- **Montar UI em região oficial:** ${capLink("ui.slots")}.
- **Janela própria incremental:** ${capLink("ui.applications")}.
- **Toast/modal simples:** ${capLink("assets.ui")}.

## Persistência e integração

- **Preferência configurável:** ${capLink("settings")}.
- **Tabelas próprias e consultas nomeadas:** ${capLink("storage.sqlite")}.
- **Emitir evento sem resposta:** ${capLink("bus.publish")}.
- **Ouvir evento:** ${capLink("bus.subscribe")}.
- **Pedir resposta a outro pacote:** ${capLink("bus.request")} + provider com ${capLink("bus.provide")}.

## Regra de minimização

Se você só lê, não declare write. Se só move token, não declare manage. Se usa uma ficha declarativa, não carregue JavaScript. Se precisa de configuração pequena, não crie banco. Se o core já tem uma intenção autoritativa, não acesse renderer ou rota interna.`,
};

const coveredCapabilities = new Set(generatedCapabilityGuides.flatMap((guide) => [...guide.body.matchAll(/^## `([^`]+)`/gm)].map((match) => match[1])));
if (coveredCapabilities.size !== allCapabilities.length) {
  const missing = allCapabilities.map(([name]) => name).filter((name) => !coveredCapabilities.has(name));
  throw new Error(`Capabilities sem documentação: ${missing.join(", ")}`);
}
export function buildCapabilityReference() {
  return {
    intentGuide,
    guides: generatedCapabilityGuides,
    capabilityCount: allCapabilities.length,
    registrySource: capabilityRegistryResult.source,
  };
}
