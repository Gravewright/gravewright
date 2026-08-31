import { readdir, readFile } from "node:fs/promises";
import path from "node:path";
import { fileURLToPath } from "node:url";
import { defineModule, MODULE_KINDS, type BaseRequest, type BaseResponse } from "@gravewright/sdk";
import { loadCatalogs } from "./catalog.js";
import { installWithDependencies, resolveDependencyPlan } from "./dependency-install.js";
import { installRecipe, planRecipe } from "./recipe.js";

const modulesDirectory = path.resolve(path.dirname(fileURLToPath(import.meta.url)), "..");
const projectRoot = path.dirname(modulesDirectory);

async function list() {
  const modules = [];
  for (const entry of await readdir(modulesDirectory, { withFileTypes: true })) {
    if (!entry.isDirectory() || entry.name.startsWith(".")) continue;
    try {
      const manifest = JSON.parse(await readFile(path.join(modulesDirectory, entry.name, "manifest.json"), "utf8"));
      modules.push({ name: manifest.name, version: manifest.version, kind: manifest.kind });
    } catch { /* diretórios comuns não são módulos */ }
  }
  return modules.sort((left, right) => left.name.localeCompare(right.name));
}

async function install(manifestUrl: string) {
  const catalog = await loadCatalogs(projectRoot);
  return installWithDependencies(manifestUrl, modulesDirectory, catalog.packages, catalog.revoked);
}

function page(): string {
  return `<!doctype html><html lang="pt-BR"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width"><title>Gravewright Marketplace</title><style>:root{color-scheme:dark}*{box-sizing:border-box}body{max-width:64rem;margin:7vh auto;padding:0 1.25rem;background:#0c0c0e;color:#eee;font:16px system-ui}header{display:flex;justify-content:space-between;align-items:end;gap:1rem}h1{margin-bottom:.25rem}.muted{color:#aaa}.actions,.kinds{display:flex;flex-wrap:wrap;gap:.65rem}.kinds{margin:2rem 0}.kind{min-width:8.5rem;padding:1rem;text-transform:capitalize}.grid{display:grid;grid-template-columns:repeat(auto-fit,minmax(17rem,1fr));gap:1rem}.card{border:1px solid #333;background:#141418;padding:1rem;border-radius:.6rem}.tag{font-size:.75rem;color:#c4b5fd;text-transform:uppercase}button,input{padding:.7rem;border:1px solid #555;background:#1b1b20;color:#eee;border-radius:.35rem}button{cursor:pointer;border-color:#8b5cf6}input{width:100%}#status{white-space:pre-wrap;min-height:1.5rem}dialog{width:min(56rem,calc(100% - 2rem));max-height:82vh;padding:0;border:1px solid #444;border-radius:.7rem;background:#101014;color:#eee}dialog::backdrop{background:#000b}.modal-head{position:sticky;top:0;display:flex;justify-content:space-between;align-items:center;padding:1rem 1.25rem;background:#101014;border-bottom:1px solid #333}.modal-body{padding:1.25rem;overflow:auto}.manual{display:grid;grid-template-columns:1fr auto;gap:.5rem}.empty{color:#999;padding:2rem 0}</style></head><body><header><div><h1>Marketplace</h1><div class="muted">Escolha uma categoria para explorar</div></div><div class="actions"><button id="refresh">Atualizar</button><button id="open-url">Instalar por URL</button></div></header><p id="status"></p><main class="kinds" id="kinds"></main>
<dialog id="packages-modal"><div class="modal-head"><h2 id="modal-title"></h2><button data-close="packages-modal">Fechar</button></div><div class="modal-body"><div class="grid" id="packages"></div></div></dialog>
<dialog id="url-modal"><div class="modal-head"><h2>Instalar por URL</h2><button data-close="url-modal">Fechar</button></div><div class="modal-body"><p class="muted">Informe a URL HTTPS estável do manifest.</p><div class="manual"><input id="url" type="url" placeholder="https://example.org/module/manifest.json"><button id="install-url">Instalar</button></div></div></dialog><script>
const kinds=${JSON.stringify(MODULE_KINDS)},status=document.querySelector('#status'),buttons=document.querySelector('#kinds'),packages=document.querySelector('#packages'),modal=document.querySelector('#packages-modal'),title=document.querySelector('#modal-title'),urlModal=document.querySelector('#url-modal');let catalog=[];
function button(label,filter){const b=document.createElement('button');b.className='kind';b.textContent=label;b.onclick=()=>openPackages(label,filter);buttons.append(b)}
function card(p){const e=document.createElement('article');e.className='card';const heading=document.createElement('h3');heading.textContent=p.title;const tag=document.createElement('div');tag.className='tag';tag.textContent=p.version+' · '+p.catalog;const desc=document.createElement('p');desc.textContent=p.description||p.name;e.append(tag,heading,desc);if(p.type==='module'){const b=document.createElement('button');b.textContent='Instalar';b.onclick=()=>installModule(p.manifest_url);e.append(b)}else{const inspect=document.createElement('button');inspect.textContent='Ver plano';inspect.onclick=()=>api({action:'install-recipe',recipe_url:p.recipe_url,dry_run:true});const apply=document.createElement('button');apply.textContent='Aplicar receita';apply.onclick=()=>api({action:'install-recipe',recipe_url:p.recipe_url});e.append(inspect,apply)}return e}
function openPackages(label,filter){title.textContent=label;packages.textContent='';const selected=catalog.filter(filter);if(!selected.length){const empty=document.createElement('p');empty.className='empty';empty.textContent='Nenhum item disponível nesta categoria.';packages.append(empty)}else for(const item of selected)packages.append(card(item));modal.showModal()}
async function request(body){const r=await fetch('/marketplace',{method:'POST',headers:{'content-type':'application/json','x-gravewright-action':'install'},body:JSON.stringify(body)});return {ok:r.ok,data:await r.json()}}
async function api(body){status.textContent='Processando…';const result=await request(body);status.textContent=result.ok?(body.dry_run?'Plano válido: ':'Concluído: ')+JSON.stringify(result.data,null,2):'Erro: '+result.data.error;if(result.ok&&!body.dry_run){modal.close();urlModal.close()}return result}
async function installModule(manifestUrl){status.textContent='Resolvendo dependências…';const plan=await request({action:'install-module',manifest_url:manifestUrl,dry_run:true});if(!plan.ok){status.textContent='Erro: '+plan.data.error;return}const deps=plan.data.dependencies||[];if(deps.length){const lines=deps.map(d=>'• '+d.name+' '+d.version).join('\\n');if(!confirm('Este módulo depende de:\\n\\n'+lines+'\\n\\nOrdem de instalação:\\n'+plan.data.install_order.join(' → ')+'\\n\\nContinuar?')){status.textContent='Instalação cancelada.';return}}await api({action:'install-module',manifest_url:manifestUrl})}
async function load(){status.textContent='Carregando…';try{const r=await fetch('/marketplace?format=json');const j=await r.json();catalog=j.packages||[];status.textContent=(j.warnings||[]).join('\\n')}catch{status.textContent='Não foi possível carregar os catálogos'}}
for(const kind of kinds)button(kind,p=>p.type==='module'&&p.kind===kind);button('Recipes',p=>p.type==='recipe');document.querySelector('#refresh').onclick=load;document.querySelector('#open-url').onclick=()=>urlModal.showModal();document.querySelector('#install-url').onclick=()=>installModule(document.querySelector('#url').value);for(const close of document.querySelectorAll('[data-close]'))close.onclick=()=>document.querySelector('#'+close.dataset.close).close();for(const dialog of document.querySelectorAll('dialog'))dialog.onclick=e=>{if(e.target===dialog)dialog.close()};load();
</script></body></html>`;
}

async function marketplace(request: BaseRequest, response: BaseResponse) {
  if (request.method === "GET") {
    if (request.query.format === "json") {
      const catalog = await loadCatalogs(projectRoot);
      return response.json({ packages: catalog.packages, warnings: catalog.warnings, installed: await list() });
    }
    return response.text(page());
  }
  if (request.method !== "POST") return response.status(405).json({ error: "method_not_allowed" });
  if (request.headers["x-gravewright-action"] !== "install") return response.status(403).json({ error: "action_header_required" });
  const body = request.body as Record<string, unknown> | null;
  if (!body || typeof body !== "object") return response.status(400).json({ error: "invalid_request" });
  try {
    const catalog = await loadCatalogs(projectRoot);
    if ((body.action === "install-module" || body.action === undefined) && typeof body.manifest_url === "string" && body.manifest_url.length <= 2048) {
      if (body.dry_run === true) {
        const plan = await resolveDependencyPlan(body.manifest_url, modulesDirectory, catalog.packages, catalog.revoked);
        const root = plan.at(-1)!;
        return response.json({
          name: root.manifest.name,
          version: root.manifest.version,
          dependencies: plan.slice(0, -1).map(({ manifest }) => ({ name: manifest.name, version: manifest.version })),
          install_order: plan.map(({ manifest }) => manifest.name),
        });
      }
      return response.status(201).json(await installWithDependencies(body.manifest_url, modulesDirectory, catalog.packages, catalog.revoked));
    }
    if (body.action === "install-recipe" && typeof body.recipe_url === "string" && body.recipe_url.length <= 2048) {
      const result = body.dry_run === true
        ? await planRecipe(body.recipe_url, modulesDirectory, catalog.packages, catalog.revoked)
        : await installRecipe(body.recipe_url, modulesDirectory, catalog.packages, catalog.revoked);
      return response.status(body.dry_run === true ? 200 : 201).json(result);
    }
    return response.status(400).json({ error: "invalid_request" });
  } catch { return response.status(400).json({ error: "operation_failed" }); }
}

export default defineModule({
  name: "marketplace", kind: "system", provider: "core", version: "0.2.0",
  routes: { "/marketplace": "marketplace" },
  exports: { get: ["read", "write", "stat", "marketplace", "list", "install"] },
  create(_ctx) {
    return {
      read(resource: string) {
        if (resource === "modules") return list();
        throw new Error(`Unknown marketplace resource: ${resource}`);
      },
      write(resource: string, value: unknown) {
        if (resource === "install" && typeof value === "string") return install(value);
        throw new Error(`Unknown marketplace resource: ${resource}`);
      },
      async stat() { return { installed: (await list()).length }; },
      marketplace, list, install,
    };
  },
});
