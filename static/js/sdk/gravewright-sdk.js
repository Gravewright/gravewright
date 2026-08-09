











(() => {
    const caps = window.GravewrightSDKCapabilities;
    const VERSION = "1";


    const manifestsById = new Map();
    const runtimes = new Map();
    const setupDone = new Set();
    const readyDone = new Set();
    let context = {};
    let gameReady = false;




    const busListeners = new Map();

    function busSubscribe(name, fn) {
        const key = String(name || "").trim();
        if (!key || typeof fn !== "function") return () => {};
        if (!busListeners.has(key)) busListeners.set(key, new Set());
        busListeners.get(key).add(fn);
        return () => busListeners.get(key)?.delete(fn);
    }

    function busPublish(name, payload) {
        const set = busListeners.get(String(name || "").trim());
        if (!set) return;

        const frozen = freeze(clone(payload));
        for (const fn of [...set]) {
            try {
                fn(frozen);
            } catch (err) {
                console.error(`GravewrightSDK bus "${name}" listener failed`, err);
            }
        }
    }


    const busProviders = new Map();
    const BUS_DEFAULT_TIMEOUT_MS = 5000;

    function busError(code, message) {
        return { ok: false, error: { code, message: message || code } };
    }

    function busException(code, message) {
        const error = new Error(message || code);
        error.code = code;
        return error;
    }

    function interopDeclares(pkg, section, name) {
        const entries = pkg && pkg.interop && pkg.interop[section];
        return !!(entries && typeof entries === "object" && entries[name]);
    }

    function busProvide(method, handler, packageId) {
        const key = String(method || "").trim();
        if (!key || typeof handler !== "function") return () => {};
        if (busProviders.has(key)) {
            throw busException("bus.provider_conflict", `duplicate provider for "${key}"`);
        }
        busProviders.set(key, { handler, packageId });
        return () => {
            const current = busProviders.get(key);
            if (current && current.handler === handler && current.packageId === packageId) {
                busProviders.delete(key);
            }
        };
    }

    async function busRequest(method, payload, options, callerPackageId) {
        const provider = busProviders.get(String(method || "").trim());
        if (!provider) {
            return busError("bus.provider_not_found", `no provider for "${method}"`);
        }
        const timeoutMs =
            Number(options && (options.timeoutMs || options.timeout)) || BUS_DEFAULT_TIMEOUT_MS;
        const frozen = freeze(clone(payload));
        let timer;
        const providerContext = freeze({
            callerPackageId: String(callerPackageId || ""),
            providerPackageId: provider.packageId,
            userId: context.user?.id,
            campaignId: context.campaign?.id,
            permissions: clone(context.permissions || null),
        });
        const timeout = new Promise((resolve) => {
            timer = setTimeout(
                () => resolve(busError("bus.provider_timeout", "provider timed out")),
                timeoutMs
            );
        });
        try {
            const value = await Promise.race([
                Promise.resolve().then(() => provider.handler(frozen, providerContext)),
                timeout,
            ]);

            if (value && value.ok === true && Object.prototype.hasOwnProperty.call(value, "value")) {
                return value;
            }
            if (value && value.ok === false && value.error) return value;
            return { ok: true, value };
        } catch (err) {
            return busError("bus.response_invalid", String((err && err.message) || err));
        } finally {
            clearTimeout(timer);
        }
    }


    function parseJsonScript(id, fallback) {
        const el = document.getElementById(id);
        if (!el) return fallback;
        try {
            return JSON.parse(el.textContent || "");
        } catch (err) {
            console.error(`Invalid JSON in #${id}`, err);
            return fallback;
        }
    }

    function clone(value) {
        if (value == null) return value;
        try {
            return JSON.parse(JSON.stringify(value));
        } catch (_err) {
            return value;
        }
    }

    function freeze(value) {
        return value && typeof value === "object" ? Object.freeze(value) : value;
    }

    function currentScriptPackageIdFromSrc() {
        const src = document.currentScript?.src || "";
        if (!src) return "";
        try {
            const url = new URL(src, window.location.href);
            const match = url.pathname.match(/^\/sdk\/packages\/([^/]+)\/asset\//);
            return match ? decodeURIComponent(match[1]) : "";
        } catch (_err) {
            return "";
        }
    }







    function currentScriptPackageId() {
        const el = document.currentScript;
        const declared = el?.dataset?.gwPackage || "";
        if (declared) {
            const nonces = (context && context.packageNonces) || {};
            const expected = nonces[declared];
            const provided = el?.dataset?.gwNonce || "";
            if (expected && provided && expected === provided) {
                return declared;
            }
            console.error(
                `GravewrightSDK refused package "${declared}": missing or invalid nonce`
            );
            return "";
        }
        return currentScriptPackageIdFromSrc();
    }


    const sheetControllers = new Map();
    const mountedSheets = new WeakMap();

    function sheetKey(packageId, sheetType) {
        return `${packageId}:${String(sheetType || "").trim()}`;
    }

    function getPath(source, path) {
        return String(path || "")
            .split(".")
            .filter(Boolean)
            .reduce((value, part) => (value == null ? undefined : value[part]), source);
    }

    function setPath(source, path, value) {
        const parts = String(path || "").split(".").filter(Boolean);
        let cursor = source;
        for (const part of parts.slice(0, -1)) {
            if (!cursor[part] || typeof cursor[part] !== "object") cursor[part] = {};
            cursor = cursor[part];
        }
        if (parts.length) cursor[parts[parts.length - 1]] = value;
    }

    function sanitizeRichText(value) {
        const template = document.createElement("template");
        template.innerHTML = String(value == null ? "" : value);
        template.content.querySelectorAll("script, iframe, object, embed").forEach((n) => n.remove());
        template.content.querySelectorAll("*").forEach((node) => {
            for (const attr of [...node.attributes]) {
                const name = attr.name.toLowerCase();
                const val = String(attr.value || "").trim().toLowerCase();
                if (name.startsWith("on") || val.startsWith("javascript:")) {
                    node.removeAttribute(attr.name);
                }
            }
        });
        return template.innerHTML;
    }

    function actorIdFromContext(ctx) {
        return String(ctx?.actor?.id || ctx?.data?.actor?.id || ctx?.data?.id || "");
    }

    function postRollFormula(actorId, formula, label) {
        const client = window.GravewrightCore && window.GravewrightCore.http;
        if (!client?.postJson) throw new Error("GravewrightCore.http is not available");
        return client.postJson("/game/actor/roll", {
            actor_id: String(actorId || ""),
            formula: String(formula || ""),
            label: String(label || ""),
        });
    }

    function postRollIntent(payload) {
        const client = window.GravewrightCore && window.GravewrightCore.http;
        if (!client?.postJson) throw new Error("GravewrightCore.http is not available");
        const target = payload?.target && typeof payload.target === "object" ? payload.target : {};
        return client.postJson("/game/actor/action", {
            actor_id: String(payload?.actorId || payload?.actor_id || ""),
            action_id: String(payload?.actionId || payload?.action_id || ""),
            inputs: payload?.inputs && typeof payload.inputs === "object" ? payload.inputs : {},
            rollOptions:
                payload?.rollOptions && typeof payload.rollOptions === "object"
                    ? payload.rollOptions
                    : undefined,
            target_actor_id: String(
                payload?.targetActorId || payload?.target_actor_id || target.actorId || target.actor_id || ""
            ),
            target_token_id: String(
                payload?.targetTokenId || payload?.target_token_id || target.tokenId || target.token_id || ""
            ),
        });
    }

    function requirePackageApi(packageId, apiName) {
        const pkg = manifestsById.get(String(packageId || ""));
        caps.requireApiCapability(pkg, apiName);
    }



    function whenBlockEditorReady(callback) {
        if (window.GWBlockEditor) return callback();
        document.addEventListener("gw:block-editor-ready", () => callback(), { once: true });
    }

    function blockEditorLabels() {
        const tag = document.querySelector("[data-journal-editor-labels]");
        try {
            return JSON.parse(tag?.textContent || "{}");
        } catch (_err) {
            return {};
        }
    }





    function mountRichEditor(node, ctx, cleanups) {
        const path = node.dataset.richEditor;
        const editable = ctx.data?.canEdit !== false;
        let handle = null;
        whenBlockEditorReady(() => {
            if (handle || !document.contains(node) || !window.GWBlockEditor) return;


            try {
                handle = window.GWBlockEditor.mount(node, {
                    editable,
                    labels: blockEditorLabels(),
                    doc: getPath(ctx.data, path),
                    onChange: (doc) => setPath(ctx.data, path, doc),
                });
                handle.editor?.on?.("blur", () => ctx.onChange?.(path, handle.getDoc()));
            } catch (err) {
                console.error("GravewrightSDK rich editor mount failed", err);
            }
        });
        cleanups.push(() => {
            try {
                handle?.destroy();
            } catch (_err) {

            }
        });
    }




    async function mountEmbeddedItemEditor(host, item, ctx) {
        if (host.dataset.loaded === "1") return;
        host.dataset.loaded = "1";
        const type = String(item?.type || "item");
        try {
            const actorId = actorIdFromContext(ctx);
            const url = `/game/actor/${encodeURIComponent(actorId)}/item/${encodeURIComponent(item.id)}/sheet-bundle`;
            const response = await fetch(url, {
                credentials: "same-origin",
                cache: "no-store",
                headers: { Accept: "application/json" },
            });
            if (!response.ok) throw new Error(`embedded item ${response.status}`);
            const bundle = await response.json();
            const renderer = window.GravewrightItemSheetInternals?.renderEmbedded;
            if (typeof renderer !== "function") throw new Error("embedded item renderer unavailable");
            renderer(host, bundle, {
                onChange(path, value) {
                    let target = String(path || "");
                    if (target === "core.name") target = "name";
                    else if (target.startsWith("sheet.")) target = `data.${target.slice(6)}`;
                    ctx.onItemChange?.(item.id, target, value);
                },
            });
        } catch (err) {
            console.error("Failed to load embedded item sheet", {
                actorId: actorIdFromContext(ctx),
                itemId: item?.id || "",
                itemType: item?.type || "",
                error: err,
            });
            host.textContent = "Failed to load item sheet.";
        }
    }

    function openEmbeddedItemModal(item, ctx) {
        const dialog = document.createElement("dialog");
        dialog.className = "gw-embedded-item-modal";
        dialog.dataset.package = String(ctx.packageId || "");
        const header = document.createElement("header");
        header.className = "gw-embedded-item-modal__header";
        const title = document.createElement("strong");
        title.textContent = String(item?.name || item?.type || "Item");
        const close = document.createElement("button");
        close.type = "button";
        close.className = "gw-embedded-item-modal__close";
        close.setAttribute("aria-label", "Close");
        close.innerHTML = '<i class="ph ph-x" aria-hidden="true"></i>';
        header.append(title, close);
        const body = document.createElement("div");
        body.className = "gw-embedded-item-modal__body";
        dialog.append(header, body);
        document.body.appendChild(dialog);

        const dispose = () => {
            unmountHtmlSheet(body);
            dialog.remove();
        };
        close.addEventListener("click", () => dialog.close());
        dialog.addEventListener("close", dispose, { once: true });
        dialog.addEventListener("click", (event) => {
            if (event.target === dialog) dialog.close();
        });
        dialog.showModal();
        void mountEmbeddedItemEditor(body, item, ctx);
    }



    function itemActionsOf(node) {
        const raw = node.dataset.itemActions;
        if (!raw) return [];
        let parsed;
        try {
            parsed = JSON.parse(raw);
        } catch {
            console.error("data-item-actions inválido", raw);
            return [];
        }
        if (!Array.isArray(parsed)) return [];
        return parsed.filter((spec) => spec && typeof spec === "object" && spec.action).slice(0, 6);
    }



    function localeText(packageId, key, fallback) {
        const catalog = manifestsById.get(packageId)?.locale || {};
        if (key && Object.prototype.hasOwnProperty.call(catalog, key)) return catalog[key];
        return fallback || key || "";
    }

    function renderItemList(node, ctx, cleanups) {
        const path = node.dataset.itemList;
        const value = getPath(ctx.data, path);
        const items = Array.isArray(value) ? value : [];
        const editable = ctx.data?.canEdit !== false;
        node.replaceChildren();
        if (!items.length) {
            const empty = document.createElement("p");
            empty.className = "gw-item-list__empty";
            empty.textContent = node.dataset.emptyText || "No items yet.";
            node.appendChild(empty);
            return;
        }
        items.forEach((item) => {
            const row = document.createElement("div");
            row.className = "gw-item-list__row";
            row.dataset.itemType = String(item?.type || "item");
            const identity = document.createElement("div");
            identity.className = "gw-item-list__identity";
            const label = document.createElement("button");
            label.type = "button";
            label.className = "gw-item-list__open";
            label.textContent = (item && (item.name || item.type)) || "Item";
            label.setAttribute("aria-haspopup", "dialog");
            identity.appendChild(label);

            const data = item?.data && typeof item.data === "object" ? item.data : {};
            const facts = [
                ["skill", data.skill],
                ["damage", data.damage],
                ["range", data.range],
                ["rof", data.rof ? `CdT ${data.rof}` : ""],
                ["ap", Number(data.ap) ? `PA ${data.ap}` : ""],
            ].filter(([, value]) => value !== "" && value != null);
            if (facts.length) {
                const meta = document.createElement("div");
                meta.className = "gw-item-list__meta";
                facts.forEach(([kind, value]) => {
                    const fact = document.createElement("span");
                    fact.className = `gw-item-list__fact gw-item-list__fact--${kind}`;
                    fact.textContent = String(value);
                    meta.appendChild(fact);
                });
                identity.appendChild(meta);
            }
            row.appendChild(identity);

            const actions = document.createElement("div");
            actions.className = "gw-item-list__actions";




            itemActionsOf(node).forEach((spec) => {
                const button = document.createElement("button");
                button.type = "button";
                button.className = "gw-item-list__action";
                button.textContent = localeText(ctx.packageId, spec.labelKey, spec.label);
                button.dataset.itemAction = spec.action;
                const onAction = () =>
                    ctx.onItemAction?.(item.id, spec.action, {
                        element: button,
                        label: button.textContent,
                    });
                button.addEventListener("click", onAction);
                cleanups.push(() => button.removeEventListener("click", onAction));
                actions.appendChild(button);
            });

            if (editable) {
                const edit = document.createElement("button");
                const editLabel = localeText(ctx.packageId, `${ctx.packageId}.ui.editar`, "Edit");
                edit.type = "button";
                edit.className = "gw-item-list__edit";
                edit.title = editLabel;
                edit.setAttribute("aria-label", editLabel);
                edit.innerHTML = '<i class="ph ph-pencil-simple" aria-hidden="true"></i>';
                const onEdit = () => openEmbeddedItemModal(item, ctx);
                edit.addEventListener("click", onEdit);
                cleanups.push(() => edit.removeEventListener("click", onEdit));
                actions.appendChild(edit);

                const remove = document.createElement("button");
                const removeLabel = localeText(ctx.packageId, `${ctx.packageId}.ui.remover`, "Remove");
                remove.type = "button";
                remove.className = "gw-item-list__remove";
                remove.title = removeLabel;
                remove.setAttribute("aria-label", removeLabel);
                remove.innerHTML = '<i class="ph ph-trash" aria-hidden="true"></i>';
                const onRemove = async () => {
                    const message = localeText(
                        ctx.packageId,
                        `${ctx.packageId}.ui.confirmar.remocao`,
                        `Remove ${item?.name || "item"}?`
                    ).replace("{name}", String(item?.name || ""));
                    const confirm = window.GravewrightCore?.dialog?.confirm;
                    if (confirm && !(await confirm(message, { variant: "danger" }))) return;
                    const next = items.filter((it) => it !== item);
                    setPath(ctx.data, path, next);
                    ctx.onChange?.(path, next);
                };
                remove.addEventListener("click", onRemove);
                cleanups.push(() => remove.removeEventListener("click", onRemove));
                actions.appendChild(remove);
            }
            row.appendChild(actions);
            node.appendChild(row);
            const onOpen = () => openEmbeddedItemModal(item, ctx);
            label.addEventListener("click", onOpen);
            cleanups.push(() => {
                label.removeEventListener("click", onOpen);
            });
        });
    }



    function wireTabs(root, cleanups) {
        const tablists = [...root.querySelectorAll('[role="tablist"]')].filter(
            (list) => list.closest("[data-sheet-type]") === root.querySelector("[data-sheet-type]")
        );
        tablists.forEach((tablist) => {
            const tabs = [...tablist.querySelectorAll(":scope > [data-tab]")];
            if (!tabs.length) return;
            const owner = tablist.parentElement;
            const panels = [...(owner?.children || [])].filter((node) => node.dataset?.tabPanel);
            const activate = (name) => {
                tabs.forEach((tab) => {
                    const active = tab.dataset.tab === name;
                    tab.classList.toggle("is-active", active);
                    tab.setAttribute("aria-selected", active ? "true" : "false");
                    tab.tabIndex = active ? 0 : -1;
                });
                panels.forEach((panel) => {
                    panel.hidden = panel.dataset.tabPanel !== name;
                });
            };
            tabs.forEach((tab) => {
                const onClick = () => {
                    activate(tab.dataset.tab);



                    const modal = root.closest?.("[data-modal-window]");
                    if (modal) {
                        document.dispatchEvent(
                            new CustomEvent("vtt:modal-content-updated", { detail: { modal } })
                        );
                    }
                };
                tab.addEventListener("click", onClick);
                cleanups.push(() => tab.removeEventListener("click", onClick));
            });




            const current = tabs.find((tab) => tab.classList.contains("is-active"));
            activate((current || tabs[0]).dataset.tab);
        });
    }

    function bindHtmlSheet(root, ctx, controller) {
        const cleanups = [];

        wireTabs(root, cleanups);
        root.querySelectorAll("[data-text]").forEach((node) => {
            node.textContent = getPath(ctx.data, node.dataset.text) ?? "";
        });
        root.querySelectorAll("[data-rich-text]").forEach((node) => {
            node.innerHTML = sanitizeRichText(getPath(ctx.data, node.dataset.richText));
        });
        root.querySelectorAll("[data-rich-editor]").forEach((node) => {
            mountRichEditor(node, ctx, cleanups);
        });
        root.querySelectorAll("[data-item-list]").forEach((node) => {
            renderItemList(node, ctx, cleanups);
        });
        root.querySelectorAll("[data-bind]").forEach((node) => {
            const path = node.dataset.bind;
            const value = getPath(ctx.data, path);




            const editando = node === document.activeElement;
            if (node.type === "checkbox") node.checked = !!value;
            else if ("value" in node && !editando) node.value = value ?? "";
            const read = () =>
                node.type === "checkbox"
                    ? node.checked
                    : node.type === "number" ? Number(node.value) : node.value;



            const onLocal = () => {
                setPath(ctx.data, path, read());
                controller.update?.(ctx);
            };






            const onCommit = () => {
                setPath(ctx.data, path, read());
                ctx.onChange?.(path, read());
                controller.update?.(ctx);
            };

            const live = node.type === "checkbox" ? null : "input";
            if (live) {
                node.addEventListener(live, onLocal);
                cleanups.push(() => node.removeEventListener(live, onLocal));
            }
            node.addEventListener("change", onCommit);
            cleanups.push(() => node.removeEventListener("change", onCommit));
        });
        root.querySelectorAll("[data-action]").forEach((node) => {
            const onClick = (event) => {










                const handled = controller.onAction?.(
                    { name: node.dataset.action, event, element: node },
                    ctx
                );
                if (handled === true) return;
                ctx.onAction?.(node.dataset.action, { event, element: node });
            };
            node.addEventListener("click", onClick);
            cleanups.push(() => node.removeEventListener("click", onClick));
        });
        root.querySelectorAll("[data-roll]").forEach((node) => {
            const onClick = (event) => {
                event.preventDefault();
                requirePackageApi(ctx.packageId, "dice.roll");
                void postRollFormula(
                    actorIdFromContext(ctx),
                    node.dataset.roll,
                    node.dataset.rollLabel || node.textContent || ""
                );
            };
            node.addEventListener("click", onClick);
            cleanups.push(() => node.removeEventListener("click", onClick));
        });
        return cleanups;
    }

    function registerSheetController(packageId, sheetType, controller) {
        const key = sheetKey(packageId, sheetType);
        if (!sheetType || !controller || typeof controller !== "object") return false;
        if (sheetControllers.has(key)) {
            throw new Error(`Duplicate sheet controller "${sheetType}" for package "${packageId}"`);
        }
        sheetControllers.set(key, { ...controller, setupDone: false });
        return true;
    }

    function mountHtmlSheet(packageId, sheetType, root, data = {}, options = {}) {
        if (!root) return false;


        const controller = sheetControllers.get(sheetKey(packageId, sheetType)) || {};
        const ctx = {
            packageId,
            sheetType,
            root,
            data,
            actor: data.actor || null,
            item: data.item || null,
            onChange: options.onChange,
            onAction: options.onAction,
            onItemChange: options.onItemChange,
            onItemAction: options.onItemAction,
        };
        if (!controller.setupDone) {
            try {
                controller.setup?.(ctx);
            } catch (err) {
                console.error("GravewrightSDK sheet controller setup failed", err);
            }
            controller.setupDone = true;
        }
        try {
            controller.mount?.(ctx);
        } catch (err) {
            console.error("GravewrightSDK sheet controller mount failed", err);
        }
        const cleanups = bindHtmlSheet(root, ctx, controller);
        mountedSheets.set(root, { controller, ctx, cleanups });
        return true;
    }

    function updateHtmlSheet(root, data = {}) {
        const mounted = mountedSheets.get(root);
        if (!mounted) return false;
        mounted.ctx.data = data;
        mounted.cleanups.forEach((fn) => fn());
        mounted.cleanups = bindHtmlSheet(root, mounted.ctx, mounted.controller);
        mounted.controller.update?.(mounted.ctx);
        return true;
    }

    function unmountHtmlSheet(root) {
        const mounted = mountedSheets.get(root);
        if (!mounted) return false;
        mounted.controller.unmount?.(mounted.ctx);
        mounted.cleanups.forEach((fn) => fn());
        mountedSheets.delete(root);
        return true;
    }








    async function unwrap(promise, what) {
        const result = await promise;
        if (!result?.ok) {
            throw new Error(
                `${what} failed (${result?.status || 0}): ${result?.errorKey || "unknown"}`
            );
        }
        return result.data;
    }

    function buildScopedSdk(pkg) {
        const requireCap = (apiName) => caps.requireApiCapability(pkg, apiName);
        const http = () => window.GravewrightCore && window.GravewrightCore.http;

        const namespaces = {
            version: VERSION,
            package: freeze({
                id: pkg.id,
                kind: pkg.kind,
                version: pkg.version || "0",



                assetUrl: (relativePath) =>
                    `/sdk/packages/${encodeURIComponent(pkg.id)}/asset/${String(relativePath || "")
                        .split("/")
                        .filter(Boolean)
                        .map(encodeURIComponent)
                        .join("/")}`,
            }),
            kind: pkg.kind,
            capabilities: Object.freeze({
                has: (c) => caps.hasCapability(pkg, c),
                require: (c, apiName = "sdk") => {
                    caps.requireCapability(pkg, c, apiName);
                    return true;
                },
                list: () => Object.freeze([...(pkg.capabilities || [])]),
            }),
            context: () => freeze(clone(context)),
            game: Object.freeze({
                context: () => freeze(clone(context)),
                campaign: () => freeze(clone(context.campaign || null)),
                scene: () => freeze(clone(context.scene || null)),
                user: () => freeze(clone(context.user || null)),
                ready: () => gameReady,
            }),
            bus: Object.freeze({


                publish(name, payload) {
                    requireCap("bus.publish");
                    const event = String(name || "");
                    if (event !== pkg.id && !event.startsWith(pkg.id + ".")) {
                        throw new Error(
                            `Package "${pkg.id}" cannot publish to foreign namespace "${event}"`
                        );
                    }
                    if (!interopDeclares(pkg, "emits", event)) {
                        throw busException(
                            "sdk.interop.event_undeclared",
                            `Package "${pkg.id}" did not declare emitted event "${event}"`
                        );
                    }
                    return busPublish(event, payload);
                },
                subscribe(name, fn) {
                    requireCap("bus.subscribe");


                    const event = String(name || "");
                    if (!interopDeclares(pkg, "listens", event)) {
                        throw busException(
                            "sdk.interop.event_undeclared",
                            `Package "${pkg.id}" did not declare listened event "${event}"`
                        );
                    }
                    return busSubscribe(event, fn);
                },
                provide(method, handler) {
                    requireCap("bus.provide");
                    const name = String(method || "");
                    if (name !== pkg.id && !name.startsWith(pkg.id + ".")) {
                        throw new Error(
                            `Package "${pkg.id}" cannot provide in foreign namespace "${name}"`
                        );
                    }
                    if (!interopDeclares(pkg, "provides", name)) {
                        throw busException(
                            "sdk.interop.method_undeclared",
                            `Package "${pkg.id}" did not declare provided method "${name}"`
                        );
                    }
                    return busProvide(name, handler, pkg.id);
                },
                request(method, payload, options) {
                    requireCap("bus.request");


                    const name = String(method || "");
                    if (!interopDeclares(pkg, "requires", name)) {
                        throw busException(
                            "sdk.interop.method_undeclared",
                            `Package "${pkg.id}" did not declare required method "${name}"`
                        );
                    }
                    return busRequest(name, payload, options, pkg.id);
                },
            }),
            commands: Object.freeze({
                register(name, handler) {
                    requireCap("commands.register");
                    document.dispatchEvent(
                        new CustomEvent("vtt:command-register", {
                            detail: { name, handler, packageId: pkg.id },
                        })
                    );
                },
            }),
            assets: Object.freeze({



                async list(options = {}) {
                    requireCap("assets.list");
                    const client = http();
                    const campaignId = options.campaignId || context.campaign?.id || "";
                    if (!client?.getJson) throw new Error("GravewrightCore.http is not available");
                    if (!campaignId) throw new Error("sdk.assets.list requires an active campaign");

                    const state = await unwrap(
                        client.getJson(`/game/assets/state/${encodeURIComponent(campaignId)}`),
                        "sdk.assets.list"
                    );
                    const assets = Array.isArray(state?.assets) ? state.assets : [];
                    return options.kind
                        ? assets.filter((asset) => asset.kind === options.kind)
                        : assets;
                },
            }),
            ui: Object.freeze({
                toast(message, options) {
                    requireCap("ui.toast");
                    return window.GravewrightToasts?.show?.(message, options);
                },
                openModal(modalId) {
                    requireCap("ui.openModal");
                    return window.GravewrightModals?.open?.(modalId);
                },
                closeModal(modalOrId) {
                    requireCap("ui.closeModal");
                    return window.GravewrightModals?.close?.(modalOrId);
                },
            }),
            chat: Object.freeze({
                send(message) {
                    requireCap("chat.send");
                    document.dispatchEvent(
                        new CustomEvent("vtt:chat-send", {
                            detail: { message, packageId: pkg.id },
                        })
                    );
                },
            }),
            dice: Object.freeze({
                roll({ formula, label = "", actorId = "" } = {}) {
                    requireCap("dice.roll");
                    return postRollFormula(actorId, formula, label);
                },
            }),
            rolls: Object.freeze({
                intent(payload = {}) {
                    requireCap("rolls.intent");
                    return postRollIntent(payload);
                },
            }),
            settings: Object.freeze({
                definitions() {
                    requireCap("settings.definitions");
                    return freeze(clone(pkg.settingDefinitions || []));
                },
                all() {
                    requireCap("settings.all");
                    return freeze(clone(pkg.settingValues || {}));
                },
                get(key, fallback = undefined) {
                    requireCap("settings.get");
                    const values = pkg.settingValues || {};
                    return Object.prototype.hasOwnProperty.call(values, key)
                        ? clone(values[key])
                        : fallback;
                },
                async set(key, value, options = {}) {
                    requireCap("settings.set");
                    const client = http();
                    if (!client?.postJson) throw new Error("GravewrightCore.http is not available");



                    const body = await unwrap(
                        client.postJson("/sdk/packages/settings", {
                            package_id: pkg.id,
                            key,
                            value,
                            campaign_id: options.campaignId || context.campaign?.id || "",
                        }),
                        "sdk.settings.set"
                    );
                    if (body?.success) {
                        pkg.settingValues = { ...(pkg.settingValues || {}), [key]: body.value };
                    }
                    return body;
                },
            }),
            sheets: Object.freeze({
                helpers() {
                    requireCap("sheets.helpers");
                    return window.GravewrightSheets?.helpers || {};
                },
                register(plugin) {
                    requireCap("sheets.register");
                    return window.GravewrightSheets?.registerSystem?.(pkg.id, plugin);
                },
                registerController(sheetType, controller) {
                    requireCap("sheets.registerController");
                    return registerSheetController(pkg.id, sheetType, controller);
                },
            }),
            combat: Object.freeze({
                register(plugin) {
                    requireCap("combat.register");
                    return window.GravewrightCombat?.registerSystem?.(pkg.id, plugin);
                },
                registerPanel(panel) {
                    requireCap("combat.registerPanel");
                    if (!panel || typeof panel !== "object") return false;
                    window.GravewrightCombatPanel = Object.freeze({ ...panel });
                    return true;
                },
                dispatch(name, payload) {
                    requireCap("combat.dispatch");
                    return window.GravewrightCombat?.dispatch?.(pkg.id, name, payload);
                },
                renderSlot(name, payload) {
                    requireCap("combat.renderSlot");
                    return window.GravewrightCombat?.renderSlot?.(pkg.id, name, payload) || [];
                },
            }),
            tokens: Object.freeze({
                centerOn(tokenId) {
                    requireCap("tokens.centerOn");
                    return window.GravewrightMap?.centerOnToken?.(tokenId);
                },
            }),
            scene: Object.freeze({
                activeCanvas() {
                    requireCap("scene.activeCanvas");
                    return window.GravewrightMap?.activeCanvas?.() || null;
                },
                activeCameraForScene(sceneId) {
                    requireCap("scene.activeCameraForScene");
                    return window.GravewrightMap?.activeCameraForScene?.(sceneId) || null;
                },
            }),
            tools: Object.freeze({
                activeTool() {
                    requireCap("tools.activeTool");
                    return window.GravewrightTools?.activeTool || "select";
                },
            }),
            content: Object.freeze({
                async packs() {
                    requireCap("content.packs");
                    const client = http();
                    if (!client?.getJson) return [];
                    return unwrap(
                        client.getJson(`/sdk/packages/${pkg.id}/content/packs`),
                        "sdk.content.packs"
                    );
                },
                async pack(packId) {
                    requireCap("content.pack");
                    const client = http();
                    if (!client?.getJson) return null;
                    return unwrap(
                        client.getJson(`/sdk/packages/${pkg.id}/content/pack/${packId}`),
                        "sdk.content.pack"
                    );
                },
            }),
            storage: Object.freeze({



                sqlite: Object.freeze({
                    async query(scope, name, params = {}) {
                        requireCap("storage.sqlite.query");
                        const client = http();
                        if (!client?.postJson) return null;
                        return unwrap(
                            client.postJson(`/sdk/packages/${pkg.id}/storage/sqlite/query`, {
                                scope,
                                query: name,
                                params,
                                campaign_id: context.campaign?.id || "",
                            }),
                            "sdk.storage.sqlite.query"
                        );
                    },
                    async execute(scope, name, params = {}) {
                        requireCap("storage.sqlite.execute");
                        const client = http();
                        if (!client?.postJson) return null;
                        return unwrap(
                            client.postJson(`/sdk/packages/${pkg.id}/storage/sqlite/execute`, {
                                scope,
                                query: name,
                                params,
                                campaign_id: context.campaign?.id || "",
                            }),
                            "sdk.storage.sqlite.execute"
                        );
                    },
                    async status(scope) {
                        requireCap("storage.sqlite.status");
                        const client = http();
                        if (!client?.postJson) return null;
                        return unwrap(
                            client.postJson(`/sdk/packages/${pkg.id}/storage/sqlite/status`, {
                                scope,
                                campaign_id: context.campaign?.id || "",
                            }),
                            "sdk.storage.sqlite.status"
                        );
                    },
                }),
            }),
            i18n: Object.freeze({
                t(key, fallback) {
                    requireCap("i18n.t");
                    const catalog = pkg.locale || {};
                    return Object.prototype.hasOwnProperty.call(catalog, key)
                        ? catalog[key]
                        : fallback != null
                          ? fallback
                          : key;
                },
            }),
        };


        namespaces.toast = (message, options) => namespaces.ui.toast(message, options);
        namespaces.setting = (key, value) =>
            value === undefined ? namespaces.settings.get(key) : namespaces.settings.set(key, value);

        return Object.freeze(namespaces);
    }


    function runSetup(id) {
        if (setupDone.has(id)) return;
        const runtime = runtimes.get(id);
        const pkg = manifestsById.get(id);
        if (!runtime || !pkg) return;
        setupDone.add(id);
        const sdk = buildScopedSdk(pkg);
        try {
            runtime.setup?.(sdk, { package: pkg, context });
        } catch (err) {
            console.error(`GravewrightSDK setup failed for "${id}"`, err);
        }
        if (gameReady) runReady(id);
    }

    function runReady(id) {
        if (readyDone.has(id)) return;
        const runtime = runtimes.get(id);
        const pkg = manifestsById.get(id);
        if (!runtime || !pkg) return;
        readyDone.add(id);
        const sdk = buildScopedSdk(pkg);
        try {
            runtime.ready?.(sdk, { package: pkg, context });
        } catch (err) {
            console.error(`GravewrightSDK ready failed for "${id}"`, err);
        }
    }

    function register(definition) {
        const id = String(definition?.id || "").trim();
        if (!id) {
            console.error("GravewrightSDK.register requires an id");
            return false;
        }
        const scriptPackageId = currentScriptPackageId();
        if (!scriptPackageId) {
            console.error(`GravewrightSDK.register refused "${id}" outside a package script`);
            return false;
        }
        if (scriptPackageId !== id) {
            console.error(
                `GravewrightSDK.register refused package "${id}" from script owned by "${scriptPackageId}"`
            );
            return false;
        }
        if (!manifestsById.has(id)) {
            console.error(`GravewrightSDK.register refused inactive package "${id}"`);
            return false;
        }
        if (runtimes.has(id)) {
            console.error(`GravewrightSDK.register refused duplicate package "${id}"`);
            return false;
        }
        runtimes.set(id, {
            setup: typeof definition.setup === "function" ? definition.setup : null,
            ready: typeof definition.ready === "function" ? definition.ready : null,
        });


        runSetup(id);
        return true;
    }

    function loadManifests(manifests) {
        for (const manifest of manifests || []) {
            if (manifest && manifest.id) {
                manifestsById.set(manifest.id, {
                    ...manifest,
                    interop: manifest.interop || {},
                    settingDefinitions: manifest.settingDefinitions || [],
                    settingValues: manifest.settingValues || manifest.settings || {},
                });
            }
        }
        for (const id of manifestsById.keys()) {
            if (runtimes.has(id)) runSetup(id);
        }
    }

    function init() {

        gameReady = true;
        for (const id of manifestsById.keys()) {
            if (runtimes.has(id)) runReady(id);
        }
    }

    const publicApi = {
        version: VERSION,
        register,
    };
    window.GravewrightSDK = Object.freeze(publicApi);
    window.GravewrightHTMLSheets = Object.freeze({
        mount: mountHtmlSheet,
        update: updateHtmlSheet,
        unmount: unmountHtmlSheet,
        sanitizeRichText,
    });

    context = Object.freeze({ ...(parseJsonScript("gravewright-game-context", {}) || {}) });
    loadManifests(parseJsonScript("gravewright-sdk-packages", []) || []);





    if (context.debug === true) {
        window.GravewrightSDKDebug = Object.freeze({
            packages: () => Array.from(manifestsById.values()),
            runtimes: () => Array.from(runtimes.keys()),
            context: () => context,
        });
    }



    if (document.readyState === "complete") {
        init();
    } else {
        document.addEventListener("DOMContentLoaded", init, { once: true });
    }
})();
