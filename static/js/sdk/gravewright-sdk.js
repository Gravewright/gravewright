











(() => {
    const caps = window.GravewrightSDKCapabilities;
    const VERSION = "1";


    const manifestsById = new Map();
    const runtimes = new Map();
    const setupDone = new Set();
    const readyDone = new Set();
    let context = {};
    let gameReady = false;

    function coerceClientSetting(definition, value) {
        let next = value;
        if (definition.type === "boolean") {
            if (typeof value === "string") {
                const token = value.trim().toLowerCase();
                if (["true", "1", "yes", "on"].includes(token)) next = true;
                else if (["false", "0", "no", "off", ""].includes(token)) next = false;
                else throw new TypeError(`Invalid value for setting ${definition.key}`);
            } else if (value === 0 || value === 1) next = Boolean(value);
            else if (typeof value !== "boolean") throw new TypeError(`Invalid value for setting ${definition.key}`);
        } else if (definition.type === "integer") {
            next = typeof value === "string" && value.trim() !== "" ? Number(value) : value;
            if (!Number.isInteger(next)) throw new TypeError(`Invalid value for setting ${definition.key}`);
        } else if (definition.type === "number") {
            next = typeof value === "string" && value.trim() !== "" ? Number(value) : value;
            if (typeof next !== "number" || !Number.isFinite(next)) throw new TypeError(`Invalid value for setting ${definition.key}`);
        } else if (definition.type === "enum") {
            if (!(definition.options || []).includes(value)) throw new TypeError(`Invalid value for setting ${definition.key}`);
        } else {
            if (value === null || value === undefined) throw new TypeError(`Invalid value for setting ${definition.key}`);
            next = String(value);
        }
        if (typeof next === "number" && definition.minimum !== null && definition.minimum !== undefined && next < definition.minimum) throw new RangeError(`Setting ${definition.key} is below minimum`);
        if (typeof next === "number" && definition.maximum !== null && definition.maximum !== undefined && next > definition.maximum) throw new RangeError(`Setting ${definition.key} is above maximum`);
        if (definition.pattern && typeof next === "string" && !(new RegExp(`^(?:${definition.pattern})$`)).test(next)) throw new TypeError(`Invalid value for setting ${definition.key}`);
        return next;
    }




    const busListeners = new Map();
    const sdkEventDisposers = new Map();
    const SDK_EVENT_TYPES = Object.freeze([
        "game.ready", "actor.created", "actor.updated", "actor.deleted",
        "item.created", "item.updated", "item.deleted", "token.created", "token.moved",
        "token.updated", "token.deleted", "scene.changed", "scene.geometry.changed",
        "scene.effects.changed", "chat.created", "combat.started", "combat.updated",
        "combat.turn.changed", "combat.ended", "setting.changed", "actor.data.updated",
        "journal.created", "journal.updated", "journal.deleted", "cards.state.changed",
        "scene.fog.changed", "scene.images.changed", "scene.templates.changed",
        "pdf.annotations.changed", "scene.shaders.changed",
        "rules.action.completed",
        "token.targets.changed", "scene.measurements.changed", "pdf.presentation.changed", "automation.job.changed",
    ]);
    const TRANSPORT_TO_SDK_EVENT = Object.freeze({
        "actor.created": "actor.created", "actor.updated": "actor.updated", "actor.deleted": "actor.deleted",
        "item.created": "item.created", "item.updated": "item.updated", "item.deleted": "item.deleted",
        "sheet.data.updated": "actor.data.updated",
        "token.created": "token.created", "tokens.created": "token.created",
        "token.moved": "token.moved", "tokens.moved": "token.moved",
        "token.updated": "token.updated", "tokens.updated": "token.updated",
        "token.deleted": "token.deleted", "tokens.deleted": "token.deleted",
        "scene.activated": "scene.changed", "scene.updated": "scene.changed",
        "scene.walls.updated": "scene.geometry.changed", "scene.lights.updated": "scene.geometry.changed",
        "scene.particles.updated": "scene.effects.changed", "scene.shaders.updated": "scene.effects.changed",
        "fog.updated": "scene.fog.changed", "scene.images.updated": "scene.images.changed",
        "board.area_marker.upserted": "scene.templates.changed", "board.area_marker.deleted": "scene.templates.changed", "board.area_marker.cleared": "scene.templates.changed",
        "journal.created": "journal.created", "journal.updated": "journal.updated", "journal.deleted": "journal.deleted",
        "cards.state.updated": "cards.state.changed",
        "pdf.annotations.changed": "pdf.annotations.changed",
        "scene.shader_presets.updated": "scene.shaders.changed",
        "rules.action.completed": "rules.action.completed",
        "token.targets.changed": "token.targets.changed", "scene.measurements.changed": "scene.measurements.changed",
        "pdf.presentation.changed": "pdf.presentation.changed", "automation.job.changed": "automation.job.changed",
        "chat.message.created": "chat.created", "combat.started": "combat.started",
        "combat.updated": "combat.updated", "combat.ended": "combat.ended",
        "setting.changed": "setting.changed", "campaign.table_settings.changed": "setting.changed",
    });

    function semanticEvent(type, payload) {
        const id = payload.actor_id || payload.item_id || payload.token_id || payload.journal_id || payload.template_id || payload.document_id || payload.scene_id
            || payload.combat_id || payload.message_id || "";
        const resource = { id: String(id), version: Number(payload.version || 0) };
        if (type.startsWith("token.") && Array.isArray(payload.tokens)) {
            resource.ids = payload.tokens.map((token) => String(token.token_id || token.id || "")).filter(Boolean).slice(0, 100);
        }
        const changes = Array.isArray(payload.changed_paths) ? payload.changed_paths.slice(0, 32)
            : payload.changed && typeof payload.changed === "object" ? Object.keys(payload.changed).slice(0, 32) : [];
        return { type, version: 1, resource, changes };
    }

    function createSdkEvents(pkg, requireCap, runtimeRead) {
        const register = (type, handler, once = false) => {
            requireCap(once ? "events.once" : "events.on");
            if (!SDK_EVENT_TYPES.includes(type) || typeof handler !== "function") return () => {};
            let disposed = false;
            let pending = null;
            let queued = false;
            const dispose = () => {
                if (disposed) return;
                disposed = true;
                document.removeEventListener("vtt:transport-event", transportListener);
                document.removeEventListener("vtt:game-ready", readyListener);
                sdkEventDisposers.get(pkg.id)?.delete(dispose);
            };
            const deliver = (payload) => {
                pending = payload;
                if (queued) return;
                queued = true;
                queueMicrotask(() => {
                    queued = false;
                    const next = pending;
                    pending = null;
                    if (disposed || !next) return;
                    const started = performance.now();
                    try {
                        handler(freeze(clone(next)));
                    } catch (error) {
                        console.error(`GravewrightSDK event "${type}" listener failed for "${pkg.id}"`, error);
                    } finally {
                        const elapsed = performance.now() - started;
                        if (elapsed > 16) console.warn(`GravewrightSDK slow event callback: ${pkg.id} ${type} ${elapsed.toFixed(1)}ms`);
                    }
                    if (once) dispose();
                });
            };
            const transportListener = async (domEvent) => {
                const envelope = domEvent.detail || {};
                if (TRANSPORT_TO_SDK_EVENT[envelope.event] !== type
                    && !(type === "combat.turn.changed" && envelope.event === "combat.updated")) return;
                const payload = envelope.payload || {};
                try {
                    if (type.startsWith("actor.") && payload.actor_id) {
                        if (!type.endsWith(".deleted")) {
                            await runtimeRead("actors", { entity_id: payload.actor_id }, "sdk.events.on");
                        }
                    }
                    if (type.startsWith("item.") && payload.item_id) {
                        if (!type.endsWith(".deleted")) {
                            await runtimeRead("items", { entity_id: payload.item_id }, "sdk.events.on");
                        }
                    }
                    if (type.startsWith("journal.") && payload.journal_id && !type.endsWith(".deleted")) {
                        await runtimeRead("journals", { entity_id: payload.journal_id }, "sdk.events.on");
                    }
                    if (type === "cards.state.changed") await runtimeRead("cards", {}, "sdk.events.on");
                    if (type === "scene.fog.changed") await runtimeRead("fog", { scene_id: payload.scene_id }, "sdk.events.on");
                    if (type === "scene.images.changed") await runtimeRead("scene.images", { scene_id: payload.scene_id }, "sdk.events.on");
                    if (type === "scene.templates.changed" && payload.template_id && envelope.event !== "board.area_marker.deleted") {
                        await runtimeRead("scene.templates", { scene_id: payload.scene_id, entity_id: payload.template_id }, "sdk.events.on");
                    }
                    if (type === "pdf.annotations.changed" && payload.document_id) {
                        await runtimeRead("pdf.annotations", { document_id: payload.document_id }, "sdk.events.on");
                    }
                    if (type === "scene.shaders.changed" && payload.scene_id) {
                        await runtimeRead("shader.instances", { scene_id: payload.scene_id }, "sdk.events.on");
                    }
                    if (type === "token.targets.changed") await runtimeRead("token.targets", { scene_id: payload.scene_id }, "sdk.events.on");
                    if (type === "scene.measurements.changed") await runtimeRead("shared.measurements", { scene_id: payload.scene_id }, "sdk.events.on");
                    if (type === "pdf.presentation.changed") await runtimeRead("pdf.presentation", { document_id: payload.document_id }, "sdk.events.on");
                    if (type === "automation.job.changed") await runtimeRead("automation.jobs", { entity_id: payload.job_id }, "sdk.events.on");
                } catch (_) {
                    return;
                }
                deliver(semanticEvent(type, payload));
            };
            const readyListener = () => type === "game.ready" && deliver({ type, version: 1 });
            document.addEventListener("vtt:transport-event", transportListener);
            document.addEventListener("vtt:game-ready", readyListener);
            if (!sdkEventDisposers.has(pkg.id)) sdkEventDisposers.set(pkg.id, new Set());
            sdkEventDisposers.get(pkg.id).add(dispose);
            return dispose;
        };
        return Object.freeze({
            on: (type, handler) => register(String(type || ""), handler, false),
            once: (type, handler) => register(String(type || ""), handler, true),
            available() { requireCap("events.available"); return Object.freeze([...SDK_EVENT_TYPES]); },
        });
    }

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

    function freeze(value, seen = new WeakSet()) {
        if (!value || typeof value !== "object" || seen.has(value)) return value;
        seen.add(value);
        Object.values(value).forEach((child) => freeze(child, seen));
        return Object.freeze(value);
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
            const panels = [...(owner?.querySelectorAll?.(":scope > [data-tab-panel]") || [])];
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
        const campaignId = () => context.campaign?.id || "";
        const runtimeUrl = (resource, params = {}) => {
            const query = new URLSearchParams({
                campaign_id: campaignId(),
                package_id: pkg.id,
            });
            Object.entries(params).forEach(([key, value]) => {
                if (value !== undefined && value !== null && value !== "") query.set(key, value);
            });
            return `/sdk/runtime/read/${encodeURIComponent(resource)}?${query}`;
        };
        const runtimeRead = async (resource, params, method) => {
            const client = http();
            if (!client?.getJson) throw new Error("GravewrightCore.http is not available");
            if (!campaignId()) throw new Error(`${method} requires an active campaign`);
            return freeze(clone(await unwrap(client.getJson(runtimeUrl(resource, params)), method)));
        };
        const runtimeCommand = async (command, payload, method) => {
            const client = http();
            if (!client?.postJson) throw new Error("GravewrightCore.http is not available");
            if (!campaignId()) throw new Error(`${method} requires an active campaign`);
            return freeze(clone(await unwrap(client.postJson(`/sdk/runtime/command/${encodeURIComponent(command)}`, {
                campaign_id: campaignId(), package_id: pkg.id, payload: payload || {},
            }), method)));
        };

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
                supported: (c) => Object.values(caps.CAPABILITIES).includes(String(c || "")),
            }),
            context: () => freeze(clone(context)),
            game: Object.freeze({
                context: () => freeze(clone(context)),
                campaign: () => freeze(clone(context.campaign || null)),
                scene: () => freeze(clone(context.scene || null)),
                user: () => freeze(clone(context.user || null)),
                ready: () => gameReady,
            }),
            events: createSdkEvents(pkg, requireCap, runtimeRead),
            permissions: Object.freeze({
                async check(action, resource = {}) {
                    requireCap("permissions.check");
                    return runtimeRead(
                        "permissions",
                        { action, entity_id: resource.actorId || resource.itemId || resource.tokenId || resource.sceneId || resource.id },
                        "sdk.permissions.check"
                    );
                },
                async can(action, resource = {}) {
                    requireCap("permissions.can");
                    const data = await this.check(action, resource);
                    return data.allowed === true;
                },
            }),
            packages: Object.freeze({
                async get(packageId) {
                    requireCap("packages.get");
                    return (await runtimeRead("packages", { entity_id: String(packageId || "") }, "sdk.packages.get")).package;
                },
                async has(packageId) {
                    requireCap("packages.has");
                    return Boolean(await this.get(packageId));
                },
            }),
            actors: Object.freeze({
                async get(actorId) {
                    requireCap("actors.get");
                    return (await runtimeRead("actors", { entity_id: actorId }, "sdk.actors.get")).actor;
                },
                async list(query = {}) {
                    requireCap("actors.list");
                    const data = await runtimeRead("actors", { entity_type: query.type, folder_id: query.folderId, cursor: query.cursor, limit: Math.min(Number(query.limit) || 100, 100) }, "sdk.actors.list");
                    return freeze(data.actors || []);
                },
                async data(actorId) {
                    requireCap("actors.data");
                    return runtimeRead("actors.data", { entity_id: actorId }, "sdk.actors.data");
                },
                async create(input = {}) { requireCap("actors.create"); return runtimeCommand("actors.create", input, "sdk.actors.create"); },
                async update(actorId, patch = {}, options = {}) { requireCap("actors.update"); return runtimeCommand("actors.update", { ...patch, id: actorId, expectedVersion: options.expectedVersion }, "sdk.actors.update"); },
                async delete(actorId) { requireCap("actors.delete"); return runtimeCommand("actors.delete", { id: actorId }, "sdk.actors.delete"); },
                async patchData(actorId, patch = {}) { requireCap("actors.patchData"); return runtimeCommand("actors.patchData", { actorId, patch }, "sdk.actors.patchData"); },
                items: Object.freeze({
                    async slots(actorId) { requireCap("actors.items.slots"); return (await runtimeRead("actor.item.slots", { entity_id: actorId }, "sdk.actors.items.slots")).slots || []; },
                    async listCopies(actorId, options = {}) { requireCap("actors.items.listCopies"); return (await runtimeRead("actor.item.copies", { entity_id: actorId, slot: options.slot }, "sdk.actors.items.listCopies")).copies || []; },
                    async insertCopy(actorId, sourceItemId, options = {}) { requireCap("actors.items.insertCopy"); return runtimeCommand("actorItems.insertCopy", { actorId, sourceItemId, slot: options.slot }, "sdk.actors.items.insertCopy"); },
                    async removeCopy(actorId, localInstanceId, options = {}) { requireCap("actors.items.removeCopy"); return runtimeCommand("actorItems.removeCopy", { actorId, localInstanceId, slot: options.slot }, "sdk.actors.items.removeCopy"); },
                }),
            }),
            items: Object.freeze({
                async get(itemId) {
                    requireCap("items.get");
                    return (await runtimeRead("items", { entity_id: itemId }, "sdk.items.get")).item;
                },
                async list(query = {}) {
                    requireCap("items.list");
                    const data = await runtimeRead("items", { entity_type: query.type, folder_id: query.folderId, cursor: query.cursor, limit: Math.min(Number(query.limit) || 100, 100) }, "sdk.items.list");
                    return freeze(data.items || []);
                },
                async create(input = {}) { requireCap("items.create"); return runtimeCommand("items.create", input, "sdk.items.create"); },
                async update(itemId, patch = {}, options = {}) { requireCap("items.update"); return runtimeCommand("items.update", { ...patch, id: itemId, expectedVersion: options.expectedVersion }, "sdk.items.update"); },
                async delete(itemId) { requireCap("items.delete"); return runtimeCommand("items.delete", { id: itemId }, "sdk.items.delete"); },
                async patchData(itemId, patch = {}) { requireCap("items.patchData"); return runtimeCommand("items.patchData", { itemId, patch }, "sdk.items.patchData"); },
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
                async ingest(file) {
                    requireCap("assets.ingest");
                    if (!(file instanceof File)) throw new TypeError("sdk.assets.ingest requires a user-selected File");
                    const bytes = new Uint8Array(await file.arrayBuffer());
                    let binary = "";
                    for (let offset = 0; offset < bytes.length; offset += 0x8000) binary += String.fromCharCode(...bytes.subarray(offset, offset + 0x8000));
                    return runtimeCommand("assets.ingest", { source: { kind: "browser-file", name: file.name, mime: file.type, base64: btoa(binary) } }, "sdk.assets.ingest");
                },
                async cancelImport(assetId) {
                    requireCap("assets.cancelImport");
                    return runtimeCommand("assets.cancelImport", { assetId }, "sdk.assets.cancelImport");
                },
            }),
            ui: Object.freeze({
                toast(message, options) {
                    requireCap("ui.toast");
                    const toasts = window.GravewrightToasts;
                    return toasts?.showToast?.(message, options) ?? toasts?.show?.(message, options);
                },
                openModal(modalId) {
                    requireCap("ui.openModal");
                    return window.GravewrightModals?.open?.(modalId);
                },
                closeModal(modalOrId) {
                    requireCap("ui.closeModal");
                    return window.GravewrightModals?.close?.(modalOrId);
                },
                applications: Object.freeze({
                    register(applicationId, definition) {
                        requireCap("ui.applications.register");
                        return window.GravewrightApplications?.register?.(pkg.id, applicationId, definition);
                    },
                    render(applicationId, host, appContext = {}, options = {}) {
                        requireCap("ui.applications.render");
                        return window.GravewrightApplications?.render?.(pkg.id, applicationId, host, appContext, options);
                    },
                    close(applicationId) {
                        requireCap("ui.applications.close");
                        return window.GravewrightApplications?.close?.(pkg.id, applicationId);
                    },
                }),
                slots: Object.freeze({
                    available() {
                        requireCap("ui.slots.available");
                        return Object.freeze([...document.querySelectorAll("[data-sdk-slot]")].map((node) => node.dataset.sdkSlot).filter((value, index, all) => all.indexOf(value) === index));
                    },
                    register(slotId, render) {
                        requireCap("ui.slots.register");
                        const selector = `[data-sdk-slot="${CSS.escape(String(slotId || ""))}"]`;
                        const hosts = [...document.querySelectorAll(selector)].filter((node) => !node.dataset.roomId || node.dataset.roomId === campaignId());
                        const roots = hosts.map((host) => {
                            const root = document.createElement("span");
                            root.dataset.sdkPackage = pkg.id;
                            root.dataset.sdkOwnedRoot = String(slotId || "");
                            host.appendChild(root);
                            if (typeof render === "function") render(root, freeze(clone(context)));
                            return root;
                        });
                        let disposed = false;
                        const dispose = () => {
                            if (disposed) return;
                            disposed = true;
                            roots.forEach((root) => root.remove());
                            sdkEventDisposers.get(pkg.id)?.delete(dispose);
                        };
                        if (!sdkEventDisposers.has(pkg.id)) sdkEventDisposers.set(pkg.id, new Set());
                        sdkEventDisposers.get(pkg.id).add(dispose);
                        return dispose;
                    },
                }),
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
                async list(options = {}) {
                    requireCap("chat.list");
                    const messages = (await runtimeRead("chat", {}, "sdk.chat.list")).messages || [];
                    return messages.slice(-Math.min(Number(options.limit) || 50, 100));
                },
                async get(messageId) {
                    requireCap("chat.get");
                    return (await runtimeRead("chat", { entity_id: messageId }, "sdk.chat.get")).message;
                },
            }),
            journals: Object.freeze({
                async get(journalId) { requireCap("journals.get"); return (await runtimeRead("journals", { entity_id: journalId }, "sdk.journals.get")).journal; },
                async list(options = {}) { requireCap("journals.list"); return runtimeRead("journals", { entity_type: options.type, folder_id: options.folderId, limit: options.limit || 100 }, "sdk.journals.list"); },
                async create(input = {}) { requireCap("journals.create"); return runtimeCommand("journals.create", input, "sdk.journals.create"); },
                async update(journalId, patch = {}) { requireCap("journals.update"); return runtimeCommand("journals.update", { ...patch, journalId }, "sdk.journals.update"); },
                async delete(journalId) { requireCap("journals.delete"); return runtimeCommand("journals.delete", { journalId }, "sdk.journals.delete"); },
            }),
            handouts: Object.freeze({
                async present(resourceType, resourceId, audience = {}) { requireCap("handouts.present"); return runtimeCommand("handouts.present", { resourceType, resourceId, subjectType: audience.type || "all", subjectId: audience.id || "" }, "sdk.handouts.present"); },
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
                    const values = { ...(pkg.settingValues || {}) };
                    (pkg.settingDefinitions || []).filter((entry) => entry.scope === "client").forEach((entry) => {
                        try {
                            const stored = localStorage.getItem(`gravewright:setting:${pkg.id}:${entry.key}`);
                            values[entry.key] = stored === null ? entry.default : JSON.parse(stored);
                        } catch (_error) { values[entry.key] = entry.default; }
                    });
                    return freeze(clone(values));
                },
                get(key, fallback = undefined) {
                    requireCap("settings.get");
                    const definition = (pkg.settingDefinitions || []).find((entry) => entry.key === key);
                    if (definition?.scope === "client") {
                        try {
                            const stored = localStorage.getItem(`gravewright:setting:${pkg.id}:${key}`);
                            return stored === null ? clone(definition.default ?? fallback) : JSON.parse(stored);
                        } catch (_error) { return clone(definition.default ?? fallback); }
                    }
                    const values = pkg.settingValues || {};
                    return Object.prototype.hasOwnProperty.call(values, key)
                        ? clone(values[key])
                        : fallback;
                },
                async set(key, value, options = {}) {
                    requireCap("settings.set");
                    const definition = (pkg.settingDefinitions || []).find((entry) => entry.key === key);
                    if (!definition) throw new TypeError(`Unknown setting: ${key}`);
                    if (definition.scope === "client") {
                        value = coerceClientSetting(definition, value);
                        const previous = this.get(key);
                        localStorage.setItem(`gravewright:setting:${pkg.id}:${key}`, JSON.stringify(value));
                        document.dispatchEvent(new CustomEvent("vtt:sdk-setting-changed", { detail: { packageId: pkg.id, key, value: clone(value), previous, scope: "client" } }));
                        return freeze({ success: true, package_id: pkg.id, key, value: clone(value), scope: "client" });
                    }
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
                        const previous = pkg.settingValues?.[key];
                        pkg.settingValues = { ...(pkg.settingValues || {}), [key]: body.value };
                        document.dispatchEvent(new CustomEvent("vtt:sdk-setting-changed", { detail: { packageId: pkg.id, key, value: clone(body.value), previous, scope: definition.scope === "global" ? "package" : definition.scope } }));
                    }
                    return body;
                },
                scope(key) {
                    requireCap("settings.get");
                    const scope = (pkg.settingDefinitions || []).find((entry) => entry.key === key)?.scope;
                    return scope === "global" ? "package" : (scope || null);
                },
                onChange(key, handler) {
                    requireCap("settings.get");
                    if (typeof handler !== "function") throw new TypeError("settings.onChange requires a handler");
                    const listener = (event) => {
                        if (event.detail?.packageId === pkg.id && (!key || event.detail.key === key)) handler(freeze(clone(event.detail)));
                    };
                    document.addEventListener("vtt:sdk-setting-changed", listener);
                    return () => document.removeEventListener("vtt:sdk-setting-changed", listener);
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
                async current() {
                    requireCap("combat.current");
                    return runtimeRead("combat", {}, "sdk.combat.current");
                },
                async combatants() {
                    requireCap("combat.combatants");
                    return (await runtimeRead("combat", {}, "sdk.combat.combatants")).combatants || [];
                },
                async start(input = {}) { requireCap("combat.start"); return runtimeCommand("combat.start", input, "sdk.combat.start"); },
                async end() { requireCap("combat.end"); return runtimeCommand("combat.end", {}, "sdk.combat.end"); },
                async advance(delta = 1) { requireCap("combat.advance"); return runtimeCommand("combat.advance", { delta }, "sdk.combat.advance"); },
                async advanceRound(delta = 1) { requireCap("combat.advanceRound"); return runtimeCommand("combat.advanceRound", { delta }, "sdk.combat.advanceRound"); },
                async setTurn(combatantId) { requireCap("combat.setTurn"); return runtimeCommand("combat.setTurn", { combatantId }, "sdk.combat.setTurn"); },
                async add(input = {}) { requireCap("combat.add"); return runtimeCommand("combat.add", input, "sdk.combat.add"); },
                async remove(combatantId) { requireCap("combat.remove"); return runtimeCommand("combat.remove", { combatantId }, "sdk.combat.remove"); },
                async setFlags(combatantId, flags = {}) { requireCap("combat.setFlags"); return runtimeCommand("combat.setFlags", { combatantId, hidden: flags.hidden, defeated: flags.defeated }, "sdk.combat.setFlags"); },
                async rollInitiative(options = {}) { requireCap("combat.rollInitiative"); return runtimeCommand("combat.rollInitiative", { scope: options.scope || "all", combatantId: options.combatantId || "" }, "sdk.combat.rollInitiative"); },
                async setInitiative(combatantId, value) { requireCap("combat.setInitiative"); return runtimeCommand("combat.setInitiative", { combatantId, value }, "sdk.combat.setInitiative"); },
                async moveCombatant(combatantId, delta) { requireCap("combat.moveCombatant"); return runtimeCommand("combat.moveCombatant", { combatantId, delta }, "sdk.combat.moveCombatant"); },
                async setInitiativeOrder(entries) {
                    requireCap("combat.setInitiativeOrder");
                    const state = await runtimeCommand("combat.setInitiativeOrder", { entries }, "sdk.combat.setInitiativeOrder");
                    document.dispatchEvent(new CustomEvent("vtt:combat-sdk-state", { detail: state }));
                    return state;
                },
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
            automation: Object.freeze({
                async schedule(actionId, input = {}, options = {}) { requireCap("automation.schedule"); return (await runtimeCommand("automation.schedule", { actionId, input, version: options.version, runAtUtc: options.runAtUtc, idempotencyKey: options.idempotencyKey, originExecutionId: options.originExecutionId, originJobId: options.originJobId, causalDepth: options.causalDepth || 0 }, "sdk.automation.schedule")).job; },
                async get(jobId) { requireCap("automation.get"); return (await runtimeRead("automation.jobs", { entity_id: jobId }, "sdk.automation.get")).job; },
                async list() { requireCap("automation.list"); return (await runtimeRead("automation.jobs", {}, "sdk.automation.list")).jobs || []; },
                async cancel(jobId) { requireCap("automation.cancel"); return (await runtimeCommand("automation.cancel", { jobId }, "sdk.automation.cancel")).job; },
                async audit() { requireCap("automation.audit"); return (await runtimeRead("automation.audit", {}, "sdk.automation.audit")).events || []; },
            }),
            tokens: Object.freeze({
                async get(tokenId, options = {}) {
                    requireCap("tokens.get");
                    return (await runtimeRead("tokens", { entity_id: tokenId, scene_id: options.sceneId || context.scene?.id }, "sdk.tokens.get")).token;
                },
                async list(options = {}) {
                    requireCap("tokens.list");
                    return (await runtimeRead("tokens", { scene_id: options.sceneId || context.scene?.id, limit: Math.min(Number(options.limit) || 100, 500) }, "sdk.tokens.list")).tokens || [];
                },
                async move(tokenId, position = {}, options = {}) { requireCap("tokens.move"); return runtimeCommand("tokens.move", { id: tokenId, sceneId: position.sceneId || context.scene?.id, x: position.x, y: position.y, expectedVersion: options.expectedVersion }, "sdk.tokens.move"); },
                async create(input = {}) { requireCap("tokens.create"); return runtimeCommand("tokens.create", input, "sdk.tokens.create"); },
                async update(tokenId, patch = {}, options = {}) { requireCap("tokens.update"); return runtimeCommand("tokens.update", { id: tokenId, sceneId: options.sceneId || context.scene?.id, patch, expectedVersion: options.expectedVersion }, "sdk.tokens.update"); },
                async delete(tokenId, options = {}) { requireCap("tokens.delete"); return runtimeCommand("tokens.delete", { id: tokenId, sceneId: options.sceneId || context.scene?.id }, "sdk.tokens.delete"); },
                centerOn(tokenId) {
                    requireCap("tokens.centerOn");
                    return window.GravewrightMap?.centerOnToken?.(tokenId);
                },
                targets: Object.freeze({
                    async list(sceneId = context.scene?.id) { requireCap("tokens.targets.list"); return (await runtimeRead("token.targets", { scene_id: sceneId }, "sdk.tokens.targets.list")).ids || []; },
                    async set(ids, sceneId = context.scene?.id) { requireCap("tokens.targets.set"); return (await runtimeCommand("tokenTargets.set", { sceneId, ids }, "sdk.tokens.targets.set")).ids || []; },
                    async clear(sceneId = context.scene?.id) { requireCap("tokens.targets.clear"); return (await runtimeCommand("tokenTargets.clear", { sceneId }, "sdk.tokens.targets.clear")).ids || []; },
                }),
            }),
            cards: Object.freeze({
                async state() { requireCap("cards.state"); return runtimeRead("cards", {}, "sdk.cards.state"); },
                definitions: Object.freeze({
                    async list() { requireCap("cards.state"); return (await runtimeRead("card.definitions", {}, "sdk.cards.definitions.list")).definitions || []; },
                    async get(id, version) { requireCap("cards.state"); return (await runtimeRead("card.definitions", { entity_id: id, version }, "sdk.cards.definitions.get")).definition || null; },
                    async instantiate(id, options = {}) { requireCap("cards.shuffle"); return runtimeCommand("cards.instantiateDefinition", { definitionId: id, version: options.version, name: options.name, artwork: options.artwork || {}, metadata: options.metadata || {} }, "sdk.cards.definitions.instantiate"); },
                }),
                async shuffle(deckId) { requireCap("cards.shuffle"); return runtimeCommand("cards.shuffle", { deckId }, "sdk.cards.shuffle"); },
                async reset(deckId, options = {}) { requireCap("cards.reset"); return runtimeCommand("cards.reset", { deckId, shuffle: options.shuffle !== false }, "sdk.cards.reset"); },
                async draw(deckId, options = {}) { requireCap("cards.draw"); return runtimeCommand("cards.draw", { deckId, count: options.count || 1, destination: options.destination || "hand", mode: options.mode || "top", targetPileId: options.targetPileId, reveal: Boolean(options.reveal) }, "sdk.cards.draw"); },
                async reveal(cardIds) { requireCap("cards.reveal"); return runtimeCommand("cards.reveal", { cardIds: Array.isArray(cardIds) ? cardIds : [cardIds] }, "sdk.cards.reveal"); },
                async discard(cardIds) { requireCap("cards.discard"); return runtimeCommand("cards.discard", { cardIds: Array.isArray(cardIds) ? cardIds : [cardIds] }, "sdk.cards.discard"); },
                async play(cardId, options = {}) { requireCap("cards.play"); return runtimeCommand("cards.play", { cardId, sceneId: options.sceneId || context.scene?.id, x: options.x || 0, y: options.y || 0, rotation: options.rotation || 0, scale: options.scale || 1, reveal: options.faceUp !== false }, "sdk.cards.play"); },
                async updatePlacement(placementId, patch = {}) { requireCap("cards.updatePlacement"); return runtimeCommand("cards.updatePlacement", { placementId, patch }, "sdk.cards.updatePlacement"); },
                async discardPlacement(placementId) { requireCap("cards.discardPlacement"); return runtimeCommand("cards.discardPlacement", { placementId }, "sdk.cards.discardPlacement"); },
            }),
            scene: Object.freeze({
                async get(sceneId) {
                    requireCap("scene.get");
                    return (await runtimeRead("scenes", { entity_id: sceneId }, "sdk.scene.get")).scene;
                },
                async list() {
                    requireCap("scene.list");
                    return (await runtimeRead("scenes", {}, "sdk.scene.list")).scenes || [];
                },
                async active() {
                    requireCap("scene.active");
                    const data = await runtimeRead("scenes", {}, "sdk.scene.active");
                    return data.scenes.find((scene) => scene.id === data.active_scene_id) || null;
                },
                activeCanvas() {
                    requireCap("scene.activeCanvas");
                    return window.GravewrightMap?.activeCanvas?.() || null;
                },
                activeCameraForScene(sceneId) {
                    requireCap("scene.activeCameraForScene");
                    return window.GravewrightMap?.activeCameraForScene?.(sceneId) || null;
                },
                geometry: Object.freeze({
                    async walls(sceneId = context.scene?.id) {
                        requireCap("scene.geometry.walls");
                        return (await runtimeRead("geometry", { scene_id: sceneId }, "sdk.scene.geometry.walls")).walls || [];
                    },
                    async lights(sceneId = context.scene?.id) {
                        requireCap("scene.geometry.lights");
                        return (await runtimeRead("geometry", { scene_id: sceneId }, "sdk.scene.geometry.lights")).lights || [];
                    },
                    async createWall(sceneId, input = {}) { requireCap("scene.geometry.createWall"); return runtimeCommand("geometry.createWall", { ...input, sceneId }, "sdk.scene.geometry.createWall"); },
                    async updateWall(wallId, patch = {}) { requireCap("scene.geometry.updateWall"); return runtimeCommand("geometry.updateWall", { id: wallId, values: patch }, "sdk.scene.geometry.updateWall"); },
                    async deleteWall(wallId) { requireCap("scene.geometry.deleteWall"); return runtimeCommand("geometry.deleteWall", { id: wallId }, "sdk.scene.geometry.deleteWall"); },
                    async splitWall(wallId, x, y) { requireCap("scene.geometry.splitWall"); return runtimeCommand("geometry.splitWall", { id: wallId, x, y }, "sdk.scene.geometry.splitWall"); },
                    async moveWallNode(sceneId, from, to) { requireCap("scene.geometry.moveWallNode"); return runtimeCommand("geometry.moveWallNode", { sceneId, from, to }, "sdk.scene.geometry.moveWallNode"); },
                    async moveWalls(sceneId, wallIds, delta) { requireCap("scene.geometry.moveWalls"); return runtimeCommand("geometry.moveWalls", { sceneId, wallIds, dx: delta?.x || 0, dy: delta?.y || 0 }, "sdk.scene.geometry.moveWalls"); },
                    async deleteWalls(wallIds) { requireCap("scene.geometry.deleteWalls"); return runtimeCommand("geometry.deleteWalls", { wallIds }, "sdk.scene.geometry.deleteWalls"); },
                    async setDoorState(wallId, state) { requireCap("scene.geometry.setDoorState"); return runtimeCommand("geometry.setDoorState", { id: wallId, state }, "sdk.scene.geometry.setDoorState"); },
                    async createLight(sceneId, input = {}) { requireCap("scene.geometry.createLight"); return runtimeCommand("geometry.createLight", { ...input, sceneId }, "sdk.scene.geometry.createLight"); },
                    async updateLight(lightId, patch = {}) { requireCap("scene.geometry.updateLight"); return runtimeCommand("geometry.updateLight", { id: lightId, values: patch }, "sdk.scene.geometry.updateLight"); },
                    async deleteLight(lightId) { requireCap("scene.geometry.deleteLight"); return runtimeCommand("geometry.deleteLight", { id: lightId }, "sdk.scene.geometry.deleteLight"); },
                }),
                effects: Object.freeze({
                    async presets() {
                        requireCap("scene.effects.presets");
                        return (await runtimeRead("effects.presets", {}, "sdk.scene.effects.presets")).presets || [];
                    },
                    async list(sceneId = context.scene?.id) {
                        requireCap("scene.effects.list");
                        return runtimeRead("effects", { scene_id: sceneId }, "sdk.scene.effects.list");
                    },
                    async create(sceneId, kind, values = {}) { requireCap("scene.effects.create"); return runtimeCommand("effects.create", { sceneId, kind, values }, "sdk.scene.effects.create"); },
                    async update(effectId, kind, values = {}) { requireCap("scene.effects.update"); return runtimeCommand("effects.update", { id: effectId, kind, values }, "sdk.scene.effects.update"); },
                    async delete(effectId, kind) { requireCap("scene.effects.delete"); return runtimeCommand("effects.delete", { id: effectId, kind }, "sdk.scene.effects.delete"); },
                }),
                shaders: Object.freeze({
                    async presets() { requireCap("scene.shaders.presets"); return (await runtimeRead("shader.presets", {}, "sdk.scene.shaders.presets")).presets || []; },
                    async getPreset(presetId) { requireCap("scene.shaders.getPreset"); return (await runtimeRead("shader.preset", { entity_id: presetId }, "sdk.scene.shaders.getPreset")).preset; },
                    async list(sceneId = context.scene?.id) { requireCap("scene.shaders.list"); return (await runtimeRead("shader.instances", { scene_id: sceneId }, "sdk.scene.shaders.list")).instances || []; },
                    async apply(sceneId, input = {}) { requireCap("scene.shaders.apply"); return (await runtimeCommand("shaders.apply", { sceneId, presetId: input.presetId, schemaVersion: input.schemaVersion || 1, parameters: input.parameters || {} }, "sdk.scene.shaders.apply")).instance; },
                    async update(id, patch = {}, options = {}) { requireCap("scene.shaders.update"); return (await runtimeCommand("shaders.update", { id, parameters: patch.parameters || patch, expectedVersion: options.expectedVersion }, "sdk.scene.shaders.update")).instance; },
                    async enable(id, enabled, options = {}) { requireCap("scene.shaders.enable"); return (await runtimeCommand("shaders.update", { id, parameters: { enabled: Boolean(enabled) }, expectedVersion: options.expectedVersion }, "sdk.scene.shaders.enable")).instance; },
                    async remove(id) { requireCap("scene.shaders.remove"); return runtimeCommand("shaders.remove", { id }, "sdk.scene.shaders.remove"); },
                }),
                fog: Object.freeze({
                    async state(sceneId = context.scene?.id) { requireCap("scene.fog.state"); return runtimeRead("fog", { scene_id: sceneId }, "sdk.scene.fog.state"); },
                    async enable(sceneId = context.scene?.id, initial = "hide_all") { requireCap("scene.fog.enable"); return runtimeCommand("fog.enable", { sceneId, initial }, "sdk.scene.fog.enable"); },
                    async disable(sceneId = context.scene?.id) { requireCap("scene.fog.disable"); return runtimeCommand("fog.disable", { sceneId }, "sdk.scene.fog.disable"); },
                    async reset(sceneId = context.scene?.id, to = "hide_all") { requireCap("scene.fog.reset"); return runtimeCommand("fog.reset", { sceneId, to }, "sdk.scene.fog.reset"); },
                    async paint(sceneId = context.scene?.id, ops = [], options = {}) { requireCap("scene.fog.paint"); return runtimeCommand("fog.paint", { sceneId, ops, expectedVersion: options.expectedVersion }, "sdk.scene.fog.paint"); },
                }),
                images: Object.freeze({
                    async list(sceneId = context.scene?.id) { requireCap("scene.images.list"); return runtimeRead("scene.images", { scene_id: sceneId }, "sdk.scene.images.list"); },
                    async place(sceneId, assetId, options = {}) { requireCap("scene.images.place"); return runtimeCommand("sceneImages.place", { sceneId, assetId, ...options }, "sdk.scene.images.place"); },
                    async update(placementId, patch = {}, options = {}) { requireCap("scene.images.update"); return runtimeCommand("sceneImages.update", { placementId, patch, expectedVersion: options.expectedVersion }, "sdk.scene.images.update"); },
                    async delete(placementId) { requireCap("scene.images.delete"); return runtimeCommand("sceneImages.delete", { placementId }, "sdk.scene.images.delete"); },
                }),
                templates: Object.freeze({
                    async list(sceneId = context.scene?.id) { requireCap("scene.templates.list"); return (await runtimeRead("scene.templates", { scene_id: sceneId }, "sdk.scene.templates.list")).templates || []; },
                    async get(sceneId, templateId) { requireCap("scene.templates.get"); return (await runtimeRead("scene.templates", { scene_id: sceneId, entity_id: templateId }, "sdk.scene.templates.get")).template; },
                    async create(sceneId, values = {}) { requireCap("scene.templates.create"); return runtimeCommand("templates.create", { sceneId, values }, "sdk.scene.templates.create"); },
                    async update(templateId, patch = {}, options = {}) { requireCap("scene.templates.update"); return runtimeCommand("templates.update", { templateId, values: patch, expectedVersion: options.expectedVersion }, "sdk.scene.templates.update"); },
                    async delete(templateId, options = {}) { requireCap("scene.templates.delete"); return runtimeCommand("templates.delete", { templateId, expectedVersion: options.expectedVersion }, "sdk.scene.templates.delete"); },
                }),
                measurements: Object.freeze({
                    async measure(sceneId, from, to) {
                        requireCap("scene.measurements.measure");
                        const points = [from, to].map((point) => ({ x: Number(point?.x), y: Number(point?.y) }));
                        if (points.some((point) => !Number.isFinite(point.x) || !Number.isFinite(point.y))) {
                            throw new TypeError("sdk.scene.measurements.measure requires finite world points");
                        }
                        const scene = await namespaces.scene.get(sceneId || context.scene?.id);
                        const dx = points[1].x - points[0].x;
                        const dy = points[1].y - points[0].y;
                        const worldDistance = Math.hypot(dx, dy);
                        const gridSize = Number(scene?.grid_size || 0);
                        return freeze({
                            sceneId: scene.id,
                            from: points[0],
                            to: points[1],
                            worldDistance,
                            gridDistance: gridSize > 0 ? worldDistance / gridSize : null,
                            gridSize: gridSize > 0 ? gridSize : null,
                        });
                    },
                    async share(sceneId, geometry, options = {}) { requireCap("scene.measurements.share"); return (await runtimeCommand("measurements.share", { sceneId, geometry, audience: options.audience || "campaign", ttlSeconds: options.ttlSeconds || 30 }, "sdk.scene.measurements.share")).measurement; },
                    async listShared(sceneId = context.scene?.id) { requireCap("scene.measurements.listShared"); return (await runtimeRead("shared.measurements", { scene_id: sceneId }, "sdk.scene.measurements.listShared")).measurements || []; },
                    async cancel(sceneId, measurementId) { requireCap("scene.measurements.cancel"); return runtimeCommand("measurements.cancel", { sceneId, measurementId }, "sdk.scene.measurements.cancel"); },
                }),
            }),
            tools: Object.freeze({
                activeTool() {
                    requireCap("tools.activeTool");
                    return window.GravewrightTools?.activeTool || "select";
                },
                register(definition = {}) {
                    requireCap("tools.register");
                    if (!window.GravewrightTools?.registerPackageTool) {
                        throw new Error("sdk.tools.register is not available");
                    }
                    const localId = String(definition.id || "");
                    if (!/^[a-z0-9]+(?:-[a-z0-9]+)*$/.test(localId)) {
                        throw new TypeError("sdk.tools.register id must be a package-local kebab-case id");
                    }
                    if (definition.capability) requireCap(String(definition.capability));
                    const fullId = `${pkg.id}.${localId}`;
                    const coreDispose = window.GravewrightTools.registerPackageTool({
                        id: fullId,
                        packageId: pkg.id,
                        label: String(definition.label || localId),
                        icon: String(definition.icon || "ph-cursor-click"),
                        cursor: String(definition.cursor || "crosshair"),
                        when: typeof definition.when === "function"
                            ? () => definition.when(freeze(clone(context)))
                            : null,
                        activate: typeof definition.activate === "function"
                            ? (toolContext) => definition.activate(freeze(clone(toolContext)))
                            : null,
                        deactivate: typeof definition.deactivate === "function"
                            ? (toolContext) => definition.deactivate(freeze(clone(toolContext)))
                            : null,
                        pointer: typeof definition.pointer === "function"
                            ? (pointer) => definition.pointer(freeze(clone(pointer)))
                            : null,
                    });
                    let disposed = false;
                    const dispose = () => {
                        if (disposed) return;
                        disposed = true;
                        coreDispose();
                        sdkEventDisposers.get(pkg.id)?.delete(dispose);
                    };
                    if (!sdkEventDisposers.has(pkg.id)) sdkEventDisposers.set(pkg.id, new Set());
                    sdkEventDisposers.get(pkg.id).add(dispose);
                    return dispose;
                },
            }),
            rules: Object.freeze({
                actions: Object.freeze({
                    async list() { requireCap("rules.actions.list"); return (await runtimeRead("rules.actions", {}, "sdk.rules.actions.list")).actions || []; },
                    async get(actionId) { requireCap("rules.actions.get"); return (await runtimeRead("rules.actions", { entity_id: actionId }, "sdk.rules.actions.get")).action; },
                    async execute(actionId, input = {}, options = {}) { requireCap("rules.actions.execute"); return runtimeCommand("rules.action.execute", { actionId, input, version: options.version, idempotencyKey: options.idempotencyKey }, "sdk.rules.actions.execute"); },
                    async resolve({ provider, semantic } = {}) { requireCap("rules.actions.get"); if (provider !== "active-ruleset" || !semantic) throw new TypeError("sdk.rules.actions.resolve requires active-ruleset and semantic"); return (await runtimeRead("rules.actions", { action: semantic }, "sdk.rules.actions.resolve")).action; },
                    async executeReference(reference, input = {}, options = {}) { requireCap("rules.actions.execute"); const match = /^([^:]+):(.+)@(\d+)$/.exec(String(reference || "")); if (!match) throw new TypeError("invalid registered action reference"); return runtimeCommand("rules.action.execute", { providerPackageId: match[1], actionId: match[2], version: Number(match[3]), input, idempotencyKey: options.idempotencyKey }, "sdk.rules.actions.executeReference"); },
                }),
            }),
            pdf: Object.freeze({
                async get(documentId) {
                    requireCap("pdf.get");
                    return (await runtimeRead("pdf", { document_id: documentId }, "sdk.pdf.get")).document;
                },
                async metadata(documentId) {
                    requireCap("pdf.metadata");
                    const document = (await runtimeRead("pdf", { document_id: documentId }, "sdk.pdf.metadata")).document;
                    const { url, ...metadata } = document || {};
                    return metadata;
                },
                viewer: Object.freeze({
                    async open(reference, options = {}) {
                        requireCap("pdf.viewer.open");
                        const documentId = typeof reference === "string" ? reference : reference?.documentId || reference?.id;
                        if (!documentId) throw new TypeError("sdk.pdf.viewer.open requires a document id or ref");
                        const result = await runtimeRead("pdf.viewer", { document_id: documentId }, "sdk.pdf.viewer.open");
                        const detail = { document: result.document, options: { ...options }, packageId: pkg.id };
                        document.dispatchEvent(new CustomEvent("vtt:pdf-viewer-open", { detail }));
                        const viewer = window.GravewrightPdfViewer;
                        let opened = {};
                        if (viewer && options.host) {
                            opened = await viewer.open({ host: options.host, url: result.document.url, assetUrl: options.assetUrl || null, page: options.page || 1, zoom: options.zoom || 1, spread: Boolean(options.spread), onPageChange: options.onPageChange || null });
                            if (options.anchor) await viewer.goToAnchor?.(options.anchor);
                        }
                        return freeze({ ...result.document, ...opened, page: viewer?.currentPage?.() || Number(options.page) || 1 });
                    },
                    async goToPage(documentId, page) {
                        requireCap("pdf.viewer.goToPage");
                        const value = await window.GravewrightPdfViewer?.goToPage?.(page);
                        document.dispatchEvent(new CustomEvent("vtt:pdf-viewer-page", { detail: { documentId, page, packageId: pkg.id } }));
                        return value ?? Number(page);
                    },
                    async search(documentId, query) {
                        requireCap("pdf.viewer.search");
                        const matches = await window.GravewrightPdfViewer?.search?.(query);
                        document.dispatchEvent(new CustomEvent("vtt:pdf-viewer-search", { detail: { documentId, query, packageId: pkg.id } }));
                        return freeze(matches || []);
                    },
                    currentPage(documentId) {
                        requireCap("pdf.viewer.currentPage");
                        const page = window.GravewrightPdfViewer?.currentPage?.() ?? null;
                        document.dispatchEvent(new CustomEvent("vtt:pdf-viewer-current-page", { detail: { documentId, page, packageId: pkg.id } }));
                        return page;
                    },
                }),
                annotations: Object.freeze({
                    async list(documentId) {
                        requireCap("pdf.annotations.list");
                        return (await runtimeRead("pdf.annotations", { document_id: documentId }, "sdk.pdf.annotations.list")).annotations || [];
                    },
                    async create(documentId, annotation = {}) {
                        requireCap("pdf.annotations.create");
                        return (await runtimeCommand("pdf.annotations.create", { ...annotation, documentId }, "sdk.pdf.annotations.create")).annotation;
                    },
                    async update(documentId, annotationId, annotation = {}) { requireCap("pdf.annotations.update"); return runtimeCommand("pdf.annotations.update", { documentId, annotationId, ...annotation }, "sdk.pdf.annotations.update"); },
                    async delete(documentId, annotationId) { requireCap("pdf.annotations.delete"); return runtimeCommand("pdf.annotations.delete", { documentId, annotationId }, "sdk.pdf.annotations.delete"); },
                }),
                presentation: Object.freeze({
                    async start(documentId, input = {}) { requireCap("pdf.presentation.start"); return (await runtimeCommand("pdf.presentation.start", { documentId, ...input }, "sdk.pdf.presentation.start")).presentation; },
                    async current(documentId) { requireCap("pdf.presentation.current"); return (await runtimeRead("pdf.presentation", { document_id: documentId }, "sdk.pdf.presentation.current")).presentation; },
                    async update(documentId, page, options = {}) { requireCap("pdf.presentation.update"); return (await runtimeCommand("pdf.presentation.update", { documentId, page, expectedVersion: options.expectedVersion }, "sdk.pdf.presentation.update")).presentation; },
                    async end(documentId) { requireCap("pdf.presentation.end"); return runtimeCommand("pdf.presentation.end", { documentId }, "sdk.pdf.presentation.end"); },
                }),
            }),
            content: Object.freeze({
                ref(kind, resourceId, options = {}) {
                    requireCap("content.ref");
                    const campaign = options.campaignId || campaignId();
                    const encode = encodeURIComponent;
                    if (!campaign || !kind || !resourceId) throw new TypeError("sdk.content.ref requires kind, id and an active campaign");
                    const parent = options.parentKind && options.parentId
                        ? `/${encode(options.parentKind)}/${encode(options.parentId)}` : "";
                    const query = new URLSearchParams();
                    if (options.page) query.set("page", String(options.page));
                    if (options.anchor) query.set("anchor", String(options.anchor));
                    return `grave://campaign/${encode(campaign)}${parent}/${encode(kind)}/${encode(resourceId)}${query.size ? `?${query}` : ""}`;
                },
                async resolve(reference) {
                    requireCap("content.resolve");
                    const value = typeof reference === "string" ? reference : this.ref(reference.kind, reference.id || reference.documentId, reference);
                    return runtimeRead("content.references", { reference: value }, "sdk.content.resolve");
                },
                async get(reference) {
                    requireCap("content.get");
                    return (await this.resolve(reference)).value;
                },
                async can(reference, action = "read") {
                    requireCap("content.can");
                    if (action !== "read" && action !== "view" && action !== "open") return false;
                    try { return Boolean((await this.resolve(reference)).value); }
                    catch (_error) { return false; }
                },
                async open(reference, options = {}) {
                    requireCap("content.open");
                    const resolved = await this.resolve(reference);
                    const detail = { ...resolved, options: { ...options }, packageId: pkg.id };
                    document.dispatchEvent(new CustomEvent("vtt:content-open", { detail }));
                    return resolved;
                },
                link(reference, options = {}) {
                    requireCap("content.link");
                    const uri = typeof reference === "string" ? reference : this.ref(reference.kind, reference.id || reference.documentId, reference);
                    return freeze({ type: "grave-reference", ref: uri, label: String(options.label || ""), icon: String(options.icon || "") });
                },
                async search(query = "", options = {}) {
                    requireCap("content.search");
                    const kinds = Array.isArray(options.kinds) ? options.kinds.join(",") : (options.kinds || "");
                    const page = await runtimeRead("content.index", { q: query, kinds, cursor: options.cursor || "", limit: Math.min(Number(options.limit) || 50, 100) }, "sdk.content.search");
                    return freeze({ entries: page.entries || [], nextCursor: page.nextCursor || null });
                },
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
    window.addEventListener("beforeunload", () => {
        for (const disposers of sdkEventDisposers.values()) {
            [...disposers].forEach((dispose) => dispose());
        }
        sdkEventDisposers.clear();
    }, { once: true });

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
