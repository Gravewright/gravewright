(() => {
  "use strict";
  const PACKAGE_ID = "my-custom-shader", APP_ID = "library";
  let sdk, host, button;
  const state = { open: false, entries: [], query: "", selected: "", editingMeta: false, error: "" };
  const messages = {
    en: { title:"My Custom Shader", subtitle:"Create once. Reuse in every scene.", empty:"You haven't saved any custom shaders yet.", first:"Create your first shader", new:"New", search:"Search shaders…", use:"Use", preview:"Preview", edit:"Edit", duplicate:"Duplicate", remove:"Delete", export:"Export", import:"Import JSON", name:"Name", description:"Description", tags:"Tags (comma separated)", save:"Save details", trusted:"Custom shaders are trusted user content." },
    "pt-br": { title:"My Custom Shader", subtitle:"Crie uma vez. Reutilize em qualquer cena.", empty:"Você ainda não salvou custom shaders.", first:"Crie seu primeiro shader", new:"Novo", search:"Buscar shaders…", use:"Usar", preview:"Pré-visualizar", edit:"Editar", duplicate:"Duplicar", remove:"Apagar", export:"Exportar", import:"Importar JSON", name:"Nome", description:"Descrição", tags:"Tags (separadas por vírgula)", save:"Salvar detalhes", trusted:"Custom shaders são conteúdo confiável do usuário." },
    es: { title:"My Custom Shader", subtitle:"Créalo una vez. Reutilízalo en cualquier escena.", empty:"Aún no guardaste custom shaders.", first:"Crea tu primer shader", new:"Nuevo", search:"Buscar shaders…", use:"Usar", preview:"Vista previa", edit:"Editar", duplicate:"Duplicar", remove:"Eliminar", export:"Exportar", import:"Importar JSON", name:"Nombre", description:"Descripción", tags:"Etiquetas (separadas por comas)", save:"Guardar detalles", trusted:"Los custom shaders son contenido de usuario confiable." }
  };
  const lang = () => { const value = (document.documentElement.lang || "en").toLowerCase(); return value.startsWith("pt") ? "pt-br" : value.startsWith("es") ? "es" : "en"; };
  const t = key => messages[lang()][key] || messages.en[key] || key;
  const esc = value => String(value ?? "").replaceAll("&","&amp;").replaceAll("<","&lt;").replaceAll(">","&gt;").replaceAll('"',"&quot;").replaceAll("'","&#039;");
  const rows = value => Array.isArray(value) ? value : value?.rows || [];
  const parse = value => { try { return typeof value === "string" ? JSON.parse(value) : value; } catch { return null; } };
  const selected = () => state.entries.find(entry => entry.id === state.selected) || null;

  async function load() {
    state.entries = rows(await sdk.storage.sqlite.query("global", "listShaders", {})).map(row => ({ ...row, tags: parse(row.tags) || [], definition: parse(row.definition), favorite: Boolean(row.favorite) }));
    if (!selected()) state.selected = state.entries[0]?.id || "";
  }
  async function render() { if (state.open && host) { await sdk.ui.applications.render(APP_ID, host, { state }); const win=host.querySelector(".mcs-window"); if(win&&Number.isFinite(state.left)&&Number.isFinite(state.top)){win.style.left=`${state.left}px`;win.style.top=`${state.top}px`;win.style.transform="none";} } }
  function filtered() { const q = state.query.trim().toLowerCase(); return state.entries.filter(e => !q || `${e.name} ${e.description} ${(e.tags||[]).join(" ")}`.toLowerCase().includes(q)); }
  function card(entry) { return `<button type="button" class="mcs-card ${entry.id===state.selected?"is-selected":""}" data-select="${esc(entry.id)}"><span data-favorite="${esc(entry.id)}" title="Favorite">${entry.favorite?"★":"☆"}</span><strong>${esc(entry.name)}</strong><small>${esc((entry.tags||[]).join(" · "))}</small></button>`; }
  function workspace() {
    const entry = selected();
    return `<section class="mcs-window" role="dialog" aria-label="${t("title")}"><header data-mcs-drag-handle><span class="mcs-drag-grip" aria-hidden="true"></span><div><h2>${t("title")}</h2><p>${t("subtitle")}</p></div><button data-new>+ ${t("new")}</button><button data-close aria-label="Close">×</button></header><div class="mcs-toolbar"><input data-search type="search" value="${esc(state.query)}" placeholder="${t("search")}"><button data-import>${t("import")}</button></div><main><aside>${filtered().map(card).join("") || `<div class="mcs-empty"><p>${t("empty")}</p><button data-new>${t("first")}</button></div>`}</aside><article>${entry ? detail(entry) : `<p>${t("trusted")}</p>`}</article></main>${state.error?`<p class="mcs-error">${esc(state.error)}</p>`:""}<input data-import-file type="file" accept="application/json,.json" hidden></section>`;
  }
  function detail(entry) { return `<div class="mcs-detail"><label>${t("name")}<input data-meta="name" maxlength="100" value="${esc(entry.name)}"></label><label>${t("description")}<textarea data-meta="description" maxlength="500">${esc(entry.description)}</textarea></label><label>${t("tags")}<input data-meta="tags" value="${esc((entry.tags||[]).join(", "))}"></label><div class="mcs-actions"><button data-use>${t("use")}</button><button data-edit>${t("edit")}</button><button data-save-meta>${t("save")}</button><button data-duplicate>${t("duplicate")}</button><button data-export>${t("export")}</button><button data-delete class="danger">${t("remove")}</button></div><small>${t("trusted")}</small></div>`; }
  async function persist(entry, create=false) { const now=Math.floor(Date.now()/1000); const values={id:entry.id,name:entry.name,description:entry.description||"",tags:entry.tags||[],favorite:entry.favorite?1:0,definition:entry.definition,updated_at:now}; if(create)values.created_at=entry.created_at||now; await sdk.storage.sqlite.execute("global",create?"createShader":"updateShader",values); await load(); await render(); }
  async function create() { const definition=await sdk.scene.shaders.customLibrary.openEditor(); if(!definition)return; const now=Math.floor(Date.now()/1000); const entry={id:crypto.randomUUID(),name:`Custom Shader ${state.entries.length+1}`,description:"",tags:[],favorite:false,definition,created_at:now}; await persist(entry,true); state.selected=entry.id; await render(); }
  async function edit(ignore=false) { const entry=selected(); if(!entry)return; const definition=await sdk.scene.shaders.customLibrary.openEditor(entry.definition); if(definition&&!ignore){entry.definition=definition;await persist(entry);} }
  async function saveMeta(root) { const entry=selected(); if(!entry)return; entry.name=root.querySelector('[data-meta="name"]').value.trim()||entry.name; entry.description=root.querySelector('[data-meta="description"]').value.trim(); entry.tags=root.querySelector('[data-meta="tags"]').value.split(",").map(x=>x.trim()).filter(Boolean).slice(0,20); await persist(entry); }
  async function duplicate() { const entry=selected(); if(!entry)return; const copy={...entry,id:crypto.randomUUID(),name:`${entry.name} Copy`,favorite:false,tags:[...entry.tags],definition:structuredClone(entry.definition),created_at:Math.floor(Date.now()/1000)}; await persist(copy,true); state.selected=copy.id; await render(); }
  async function remove() { const entry=selected(); if(!entry||!window.confirm(`${t("remove")} “${entry.name}”?`))return; await sdk.storage.sqlite.execute("global","deleteShader",{id:entry.id}); await load(); await render(); }
  function exportOne() { const entry=selected(); if(!entry)return; const payload={format:"gravewright-custom-shader-library-entry",version:1,name:entry.name,description:entry.description,tags:entry.tags,definition:entry.definition}; const a=document.createElement("a"); a.href=URL.createObjectURL(new Blob([JSON.stringify(payload,null,2)],{type:"application/json"})); a.download=`${entry.name.toLowerCase().replace(/[^a-z0-9]+/g,"-")||"custom-shader"}.json`; a.click(); setTimeout(()=>URL.revokeObjectURL(a.href),0); }
  async function importFile(file) { if(!file||file.size>45000)throw new Error("CUSTOM_SHADER_INVALID"); const payload=JSON.parse(await file.text()); if(payload.format!=="gravewright-custom-shader-library-entry"||payload.version!==1)throw new Error("CUSTOM_SHADER_INVALID"); const validated=await sdk.scene.shaders.customLibrary.openEditor(payload.definition); if(!validated)return; const now=Math.floor(Date.now()/1000); await persist({id:crypto.randomUUID(),name:String(payload.name||"Imported Shader").slice(0,100),description:String(payload.description||"").slice(0,500),tags:Array.isArray(payload.tags)?payload.tags.slice(0,20):[],favorite:false,definition:validated,created_at:now},true); }
  function activate(root) {
    const on=(selector,type,fn)=>root.querySelectorAll(selector).forEach(node=>node.addEventListener(type,fn));
    on("[data-close]","click",close);
    on("[data-new]","click",create);
    on("[data-select]","click",event=>{state.selected=event.currentTarget.dataset.select;state.error="";render();});
    on("[data-favorite]","click",async event=>{event.stopPropagation();const entry=state.entries.find(value=>value.id===event.currentTarget.dataset.favorite);entry.favorite=!entry.favorite;await persist(entry);});
    on("[data-search]","input",event=>{state.query=event.target.value;render();});
    on("[data-use]","click",async()=>{const entry=selected();if(!entry)return;try{state.error="";await sdk.scene.shaders.customLibrary.use(entry.definition);close();}catch(error){state.error=error.code||error.message;await render();}});
    on("[data-edit]","click",()=>edit(false));
    on("[data-save-meta]","click",()=>saveMeta(root));
    on("[data-duplicate]","click",duplicate);
    on("[data-delete]","click",remove);
    on("[data-export]","click",exportOne);
    on("[data-import]","click",()=>root.querySelector("[data-import-file]").click());
    on("[data-import-file]","change",async event=>{try{await importFile(event.target.files[0]);await load();await render();}catch(error){state.error=error.code||error.message;await render();}});
  }
  function installWindowDrag() {
    let drag=null;
    const move=event=>{if(!drag)return;const {win}=drag;state.left=Math.max(8,Math.min(window.innerWidth-win.offsetWidth-8,drag.left+event.clientX-drag.x));state.top=Math.max(8,Math.min(window.innerHeight-win.offsetHeight-8,drag.top+event.clientY-drag.y));win.style.left=`${state.left}px`;win.style.top=`${state.top}px`;win.style.transform="none";};
    const stop=()=>{if(!drag)return;drag.win.classList.remove("is-dragging");drag=null;};
    document.addEventListener("pointerdown",event=>{const handle=event.target.closest?.("[data-mcs-drag-handle]");if(!handle||event.button!==0||event.target.closest("button,input,textarea,select"))return;const win=handle.closest(".mcs-window"),rect=win?.getBoundingClientRect();if(!win||!rect)return;drag={win,x:event.clientX,y:event.clientY,left:rect.left,top:rect.top};win.classList.add("is-dragging");event.preventDefault();});
    document.addEventListener("pointermove",move);document.addEventListener("pointerup",stop);document.addEventListener("pointercancel",stop);
  }
  installWindowDrag();
  async function open(){state.open=true;host.hidden=false;button?.setAttribute("aria-pressed","true");await load();await render();const win=host.querySelector(".mcs-window");if(win&&Number.isFinite(state.left)&&Number.isFinite(state.top)){win.style.left=`${state.left}px`;win.style.top=`${state.top}px`;win.style.transform="none";}}
  function close(){state.open=false;sdk.scene.shaders.customLibrary.clearPreview();sdk.ui.applications.close(APP_ID);if(host)host.hidden=true;button?.setAttribute("aria-pressed","false");}
  window.GravewrightSDK.register({id:PACKAGE_ID,setup(value){sdk=value;sdk.ui.applications.register(APP_ID,{parts:{workspace:{render:workspace,activate}}});sdk.scene.shaders.customLibrary.registerProvider({id:"personal",label:"My Custom Shader",description:"Personal reusable custom shader library",open});},ready(){sdk.ui.slots.register("board.overlay",root=>{host=root;root.className="mcs-overlay";root.hidden=true;});sdk.ui.slots.register("dock.actions",root=>{button=document.createElement("button");button.type="button";button.className="mcs-dock";button.innerHTML='<i class="ph ph-sparkle"></i>';button.title="My Custom Shader";button.addEventListener("click",()=>state.open?close():open());root.appendChild(button);});}});
})();
