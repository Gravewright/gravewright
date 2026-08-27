











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
        "scene.zones.changed", "zone.entered", "zone.left", "zone.crossed", "interaction.changed",
        "scene.objects.changed", "scene.object.interacted", "scene.object.selected", "ui.presentation.changed",
        "audio.changed", "navigation.scene.changed", "input.binding.changed",
        "workflow.changed", "gameplay.flow.changed", "timeline.changed", "tokens.transferred",
        "user.presentation.changed",
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
        "scene.zones.changed": "scene.zones.changed", "zone.entered": "zone.entered", "zone.left": "zone.left", "zone.crossed": "zone.crossed",
        "interaction.changed": "interaction.changed",
        "scene.objects.changed": "scene.objects.changed", "scene.object.interacted": "scene.object.interacted", "ui.presentation.changed": "ui.presentation.changed",
        "audio.changed": "audio.changed", "navigation.scene.changed": "navigation.scene.changed", "input.binding.changed": "input.binding.changed",
        "workflow.changed": "workflow.changed", "gameplay.flow.changed": "gameplay.flow.changed", "timeline.changed": "timeline.changed", "tokens.transferred": "tokens.transferred",
        "user.presentation.changed": "user.presentation.changed",
        "chat.message.created": "chat.created", "combat.started": "combat.started",
        "combat.updated": "combat.updated", "combat.ended": "combat.ended",
        "setting.changed": "setting.changed", "campaign.table_settings.changed": "setting.changed",
    });

    function semanticEvent(type, payload) {
        const id = payload.actor_id || payload.item_id || payload.token_id || payload.object_id || payload.zone_id || payload.interaction_id || payload.journal_id || payload.template_id || payload.document_id || payload.user_id || payload.scene_id
            || payload.combat_id || payload.message_id || "";
        const event = { type, version: 1 };
        if (id) event.resourceId = String(id);
        if (payload.scene_id) event.sceneId = String(payload.scene_id);
        return event;
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
                document.removeEventListener("vtt:scene-object-selected", selectionListener);
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
                    if (type === "scene.zones.changed" && payload.zone_id && !payload.deleted) await runtimeRead("scene.zones", { entity_id: payload.zone_id }, "sdk.events.on");
                    if (type === "interaction.changed" && payload.interaction_id) await runtimeRead("interactions", { entity_id: payload.interaction_id }, "sdk.events.on");
                    if (type === "scene.objects.changed" && payload.object_id && !payload.deleted) await runtimeRead("scene.objects", { entity_id: payload.object_id }, "sdk.events.on");
                    if (type === "ui.presentation.changed" && payload.presentation_id && !payload.closed) await runtimeRead("ui.presentations", { entity_id: payload.presentation_id }, "sdk.events.on");
                    if (type === "user.presentation.changed" && payload.user_id) await runtimeRead("user.presentations", { entity_id: payload.user_id }, "sdk.events.on");
                } catch (_) {
                    return;
                }
                deliver(semanticEvent(type, payload));
            };
            const readyListener = () => type === "game.ready" && deliver({ type, version: 1 });
            const selectionListener = event => type === "scene.object.selected" && deliver({ type, version: 1, resourceId: String(event.detail?.id || ""), sceneId: String(event.detail?.sceneId || "") || undefined });
            document.addEventListener("vtt:transport-event", transportListener);
            document.addEventListener("vtt:game-ready", readyListener);
            document.addEventListener("vtt:scene-object-selected", selectionListener);
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
        const itemInstanceId = String(payload?.itemInstanceId || payload?.item_instance_id || "");
        return client.postJson(itemInstanceId ? "/game/actor/item/action" : "/game/actor/action", {
            actor_id: String(payload?.actorId || payload?.actor_id || ""),
            item_instance_id: itemInstanceId || undefined,
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
        window.GravewrightJournalEditorAssets?.loadBlockEditor?.().catch(() => {});
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

    /**
     * One semantic invocation of a registered Input command.
     *
     * The core Input Runtime owns every physical listener, so what arrives here is
     * already resolved metadata — never a KeyboardEvent, DOM node or renderer event.
     * A package-owned handler runs locally with no server authority of its own; the
     * registered action, when the command declares one, is executed by the server
     * from its own canonical pre-bound input. No invocation metadata is ever sent as
     * action input.
     */
    async function dispatchInputCommand(packageId, commandId, serverBound, handler, invocation, runtimeCommand) {
        const detail = freeze({
            commandId, packageId,
            source: String(invocation?.source || "binding"),
            binding: invocation?.binding ? String(invocation.binding) : null,
            context: String(invocation?.context || "global"),
        });
        if (typeof handler === "function") {
            try { await handler(detail); }
            catch (err) { console.error(`GravewrightSDK input command "${commandId}" handler failed`, err); }
        }
        if (!serverBound) return;
        return runtimeCommand("input.execute", { commandId }, "sdk.input.commands.execute");
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
            input: Object.freeze({
                commands: Object.freeze({
                    async register(definition = {}, handler = null) { requireCap("input.commands.register"); await runtimeCommand("input.register", { kind: "command", definition }, "sdk.input.commands.register"); return window.GravewrightInputRuntime?.registerCommand(pkg.id, definition, invocation => dispatchInputCommand(pkg.id, definition.id, Boolean(definition.registeredAction), handler, invocation, runtimeCommand)) || (() => {}); },
                    async list() { requireCap("input.commands.list"); return (await runtimeRead("input.commands", {}, "sdk.input.commands.list")).commands || []; },
                    async execute(commandId, inputs = {}) { requireCap("input.commands.execute"); return (await runtimeCommand("input.execute", { commandId, inputs }, "sdk.input.commands.execute")).result; },
                }),
                bindings: Object.freeze({
                    async get() { requireCap("input.bindings.get"); return (await runtimeRead("input.bindings", {}, "sdk.input.bindings.get")).bindings || []; },
                    async set(commandId, binding, options = {}) { requireCap("input.bindings.set"); const result=(await runtimeCommand("input.bindings.set", { commandId, binding, expectedVersion: options.expectedVersion }, "sdk.input.bindings.set")).result; window.GravewrightInputRuntime?.updateBinding(pkg.id, commandId, result.binding); return result; },
                }),
                gestures: Object.freeze({
                    async register(definition = {}, handler = null) { requireCap("input.gestures.register"); await runtimeCommand("input.register", { kind: "gesture", definition }, "sdk.input.gestures.register"); return window.GravewrightInputRuntime?.registerGesture(pkg.id, definition, invocation => dispatchInputCommand(pkg.id, definition.commandId, true, handler, invocation, runtimeCommand)) || (() => {}); },
                }),
            }),
            campaign: Object.freeze({
                async members() { requireCap("campaign.members"); return (await runtimeRead("campaign.members", {}, "sdk.campaign.members")).members || []; },
            }),
            users: Object.freeze({
                presentation: Object.freeze({
                    async get(userId) { requireCap("users.presentation.get"); return (await runtimeRead("user.presentations", { entity_id: userId }, "sdk.users.presentation.get")).presentation; },
                    async list() { requireCap("users.presentation.list"); return (await runtimeRead("user.presentations", {}, "sdk.users.presentation.list")).presentations || []; },
                }),
            }),
            navigation: Object.freeze({
                scene: Object.freeze({
                    async go(input = {}) { requireCap("navigation.scene.go"); return (await runtimeCommand("navigation.scene.go", { input }, "sdk.navigation.scene.go")).navigation; },
                    async getState() { requireCap("navigation.scene.getState"); return (await runtimeRead("navigation.scene", {}, "sdk.navigation.scene.getState")).navigation; },
                }),
            }),
            workflows: Object.freeze({
                async register(definition = {}) { requireCap("workflows.register"); return (await runtimeCommand("workflows.register", { definition }, "sdk.workflows.register")).definition; },
                async start(input = {}) { requireCap("workflows.start"); return (await runtimeCommand("workflows.start", { input }, "sdk.workflows.start")).workflow; },
                async get(id) { requireCap("workflows.get"); return (await runtimeRead("workflows", { entity_id: id }, "sdk.workflows.get")).workflow; },
                async list() { requireCap("workflows.list"); return (await runtimeRead("workflows", {}, "sdk.workflows.list")).workflows || []; },
                async cancel(id, options = {}) { requireCap("workflows.cancel"); return (await runtimeCommand("workflows.cancel", { id, expectedVersion: options.expectedVersion }, "sdk.workflows.cancel")).workflow; },
            }),
            gameplay: Object.freeze({
                flows: Object.freeze({
                    async register(definition = {}) { requireCap("gameplay.flows.register"); return (await runtimeCommand("gameplay.flows.register", { definition }, "sdk.gameplay.flows.register")).definition; },
                    async start(input = {}) { requireCap("gameplay.flows.start"); return (await runtimeCommand("gameplay.flows.start", { input }, "sdk.gameplay.flows.start")).flow; },
                    async get(id) { requireCap("gameplay.flows.get"); return (await runtimeRead("gameplay.flows", { entity_id: id }, "sdk.gameplay.flows.get")).flow; },
                    async list() { requireCap("gameplay.flows.list"); return (await runtimeRead("gameplay.flows", {}, "sdk.gameplay.flows.list")).flows || []; },
                    async advance(id, options = {}) { requireCap("gameplay.flows.advance"); return (await runtimeCommand("gameplay.flows.advance", { id, expectedVersion: options.expectedVersion }, "sdk.gameplay.flows.advance")).flow; },
                    async submit(id, value, options = {}) { requireCap("gameplay.flows.submit"); return (await runtimeCommand("gameplay.flows.submit", { id, value, expectedVersion: options.expectedVersion }, "sdk.gameplay.flows.submit")).flow; },
                }),
            }),
            timelines: Object.freeze({
                async register(definition = {}) { requireCap("timelines.register"); return (await runtimeCommand("timelines.register", { definition }, "sdk.timelines.register")).definition; },
                async start(input = {}) { requireCap("timelines.start"); return (await runtimeCommand("timelines.start", { input }, "sdk.timelines.start")).timeline; },
                async get(id) { requireCap("timelines.get"); return (await runtimeRead("timelines", { entity_id: id }, "sdk.timelines.get")).timeline; },
                async list() { requireCap("timelines.list"); return (await runtimeRead("timelines", {}, "sdk.timelines.list")).timelines || []; },
                async cancel(id, options = {}) { requireCap("timelines.cancel"); return (await runtimeCommand("timelines.cancel", { id, expectedVersion: options.expectedVersion }, "sdk.timelines.cancel")).timeline; },
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
            audio: Object.freeze({
                async play(input = {}) { requireCap("audio.play"); return (await runtimeCommand("audio.play", { input }, "sdk.audio.play")).playback; },
                async get(id) { requireCap("audio.get"); return (await runtimeRead("audio.playbacks", { entity_id: id }, "sdk.audio.get")).playback; },
                async list(options = {}) { requireCap("audio.list"); return (await runtimeRead("audio.playbacks", { scene_id: options.sceneId }, "sdk.audio.list")).playbacks || []; },
                async update(id, patch = {}, options = {}) { requireCap("audio.update"); return (await runtimeCommand("audio.update", { id, patch, expectedVersion: options.expectedVersion }, "sdk.audio.update")).playback; },
                async stop(id, options = {}) { requireCap("audio.stop"); return (await runtimeCommand("audio.stop", { id, fade: options.fade, expectedVersion: options.expectedVersion }, "sdk.audio.stop")).playback; },
            }),
            sounds: Object.freeze({
                async list(options = {}) { requireCap("sounds.list"); return (await runtimeRead("sounds", { q: options.query, kinds: options.kind, cursor: options.cursor, limit: options.limit }, "sdk.sounds.list")).sounds || []; },
                async get(id) { requireCap("sounds.get"); return (await runtimeRead("sounds", { entity_id: id }, "sdk.sounds.get")).sound; },
                async create(input = {}) { requireCap("sounds.create"); return (await runtimeCommand("sounds.create", { input }, "sdk.sounds.create")).sound; },
                async update(id, patch = {}, options = {}) { requireCap("sounds.update"); return (await runtimeCommand("sounds.update", { id, patch, expectedVersion: options.expectedVersion }, "sdk.sounds.update")).sound; },
                async delete(id, options = {}) { requireCap("sounds.delete"); return runtimeCommand("sounds.delete", { id, expectedVersion: options.expectedVersion }, "sdk.sounds.delete"); },
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
                presentations: Object.freeze({
                    async show(input = {}) { requireCap("ui.presentations.show"); return (await runtimeCommand("presentations.show", { input }, "sdk.ui.presentations.show")).presentation; },
                    async get(id) { requireCap("ui.presentations.get"); return (await runtimeRead("ui.presentations", { entity_id: id }, "sdk.ui.presentations.get")).presentation; },
                    async list(options = {}) { requireCap("ui.presentations.list"); return (await runtimeRead("ui.presentations", { scene_id: options.sceneId || context.scene?.id }, "sdk.ui.presentations.list")).presentations || []; },
                    async wait(id, options = {}) {
                        requireCap("ui.presentations.get");
                        const timeout = Math.max(100, Math.min(60000, Number(options.timeoutMs) || 60000));
                        const started = Date.now();
                        return new Promise((resolve, reject) => {
                            let busy = false;
                            let settled = false;
                            let timer = null;
                            const cleanup = () => {
                                if (timer !== null) window.clearInterval(timer);
                                document.removeEventListener("vtt:transport-event", changed);
                            };
                            const finish = value => {
                                if (settled) return;
                                settled = true;
                                cleanup();
                                resolve(value);
                            };
                            const fail = error => {
                                if (settled) return;
                                settled = true;
                                cleanup();
                                reject(error);
                            };
                            const check = async () => {
                                if (busy || settled) return;
                                busy = true;
                                try {
                                    const value = (await runtimeRead("ui.presentations", { entity_id: id }, "sdk.ui.presentations.wait")).presentation;
                                    if (!value || value.status !== "active") return finish(value);
                                    if (Date.now() - started >= timeout) fail(new Error("sdk.ui.presentations.wait_timeout"));
                                } catch (error) { fail(error); }
                                finally { busy = false; }
                            };
                            const changed = event => {
                                if (event.detail?.event !== "ui.presentation.changed" || event.detail?.payload?.presentation_id !== id) return;
                                const value = event.detail.payload.presentation;
                                if (value && value.status !== "active") finish(value);
                                else void check();
                            };
                            document.addEventListener("vtt:transport-event", changed);
                            timer = window.setInterval(check, 250);
                            void check();
                        });
                    },
                    async update(id, patch = {}, options = {}) { requireCap("ui.presentations.update"); return (await runtimeCommand("presentations.update", { id, patch, expectedVersion: options.expectedVersion }, "sdk.ui.presentations.update")).presentation; },
                    async close(id, options = {}) { requireCap("ui.presentations.close"); return (await runtimeCommand("presentations.close", { id, expectedVersion: options.expectedVersion }, "sdk.ui.presentations.close")).presentation; },
                }),
                dragDrop: Object.freeze({
                    async registerSource(definition = {}) { requireCap("ui.dragDrop.registerSource"); await runtimeCommand("dragDrop.register", { kind: "source", definition }, "sdk.ui.dragDrop.registerSource"); const local=window.GravewrightSemanticPointerHost?.registerSource(pkg.id,definition,input=>runtimeCommand("dragDrop.drop",{input},"sdk.ui.dragDrop.drop"),campaignId()); return () => { local?.(); return runtimeCommand("dragDrop.unregister", { kind: "source", id: definition.id }, "sdk.ui.dragDrop.unregisterSource"); }; },
                    async registerTarget(definition = {}) { requireCap("ui.dragDrop.registerTarget"); await runtimeCommand("dragDrop.register", { kind: "target", definition }, "sdk.ui.dragDrop.registerTarget"); const local=window.GravewrightSemanticPointerHost?.registerTarget(pkg.id,definition); return () => { local?.(); return runtimeCommand("dragDrop.unregister", { kind: "target", id: definition.id }, "sdk.ui.dragDrop.unregisterTarget"); }; },
                    async sources() { requireCap("ui.dragDrop.sources"); return (await runtimeRead("ui.dragDrop", { action: "sources" }, "sdk.ui.dragDrop.sources")).sources || []; },
                    async targets() { requireCap("ui.dragDrop.targets"); return (await runtimeRead("ui.dragDrop", { action: "targets" }, "sdk.ui.dragDrop.targets")).targets || []; },
                    async drop(input = {}) { requireCap("ui.dragDrop.drop"); return (await runtimeCommand("dragDrop.drop", { input }, "sdk.ui.dragDrop.drop")).result; },
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
                actions: Object.freeze({
                    register(definition, handler) {
                        requireCap("rolls.actions.register");
                        return window.GravewrightRollActions?.register?.(pkg.id, definition, handler) || false;
                    },
                }),
                intent(payload = {}) {
                    requireCap("rolls.intent");
                    return postRollIntent(payload);
                },
                reroll(messageId) {
                    requireCap("rolls.reroll");
                    const client = window.GravewrightCore && window.GravewrightCore.http;
                    if (!client?.postJson) throw new Error("GravewrightCore.http is not available");
                    return unwrap(client.postJson("/game/roll/reroll", {
                        campaign_id: context.campaign?.id || "",
                        message_id: String(messageId || ""),
                    }), "sdk.rolls.reroll");
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
                async interruptTurn(combatantId) { requireCap("combat.interruptTurn"); return runtimeCommand("combat.interruptTurn", { combatantId }, "sdk.combat.interruptTurn"); },
                async resumeTurn() { requireCap("combat.resumeTurn"); return runtimeCommand("combat.resumeTurn", {}, "sdk.combat.resumeTurn"); },
                async setHolding(combatantId, holding = true) { requireCap("combat.setHolding"); return runtimeCommand("combat.setHolding", { combatantId, holding: Boolean(holding) }, "sdk.combat.setHolding"); },
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
            interactions: Object.freeze({
                async request(input = {}) { requireCap("interactions.request"); return (await runtimeCommand("interactions.request", { input }, "sdk.interactions.request")).interaction; },
                async get(id) { requireCap("interactions.get"); return (await runtimeRead("interactions", { entity_id: id }, "sdk.interactions.get")).interaction; },
                async list(options = {}) { requireCap("interactions.list"); return (await runtimeRead("interactions", { status: options.status, recipient: options.recipient }, "sdk.interactions.list")).interactions || []; },
                async respond(id, response, options = {}) { requireCap("interactions.respond"); return (await runtimeCommand("interactions.respond", { id, response, expectedVersion: options.expectedVersion, idempotencyKey: options.idempotencyKey }, "sdk.interactions.respond")).interaction; },
                async cancel(id, options = {}) { requireCap("interactions.cancel"); return (await runtimeCommand("interactions.cancel", { id, expectedVersion: options.expectedVersion }, "sdk.interactions.cancel")).interaction; },
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
                async move(tokenId, position = {}, options = {}) { requireCap("tokens.move"); return runtimeCommand("tokens.move", { id: tokenId, sceneId: position.sceneId || context.scene?.id, x: position.x, y: position.y, expectedVersion: options.expectedVersion, originExecutionId: options.originExecutionId, originJobId: options.originJobId, causalDepth: options.causalDepth || 0 }, "sdk.tokens.move"); },
                async transfer(tokenId, destination = {}, options = {}) { requireCap("tokens.transfer"); return (await runtimeCommand("tokens.transfer", { input: { tokenId, sceneId: destination.sceneId, x: destination.x, y: destination.y, elevation: destination.elevation, expectedVersion: options.expectedVersion, navigateAudience: options.navigateAudience } }, "sdk.tokens.transfer")).transfer; },
                async transferMany(transfers = [], options = {}) { requireCap("tokens.transferMany"); return (await runtimeCommand("tokens.transferMany", { input: { transfers, navigateAudience: options.navigateAudience } }, "sdk.tokens.transferMany")).transfer; },
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
                    customLibrary: Object.freeze({
                        registerProvider(definition = {}) {
                            requireCap("scene.shaders.customLibrary.registerProvider");
                            const host = window.GravewrightCustomShaderLibraries;
                            if (!host?.registerProvider) throw new Error("CUSTOM_SHADER_UNAVAILABLE");
                            const disposeCore = host.registerProvider(pkg.id, {
                                id: definition.id, label: definition.label, description: definition.description,
                                open: typeof definition.open === "function" ? () => definition.open(freeze(clone(context))) : null,
                            });
                            let disposed = false;
                            const dispose = () => {
                                if (disposed) return; disposed = true; disposeCore();
                                sdkEventDisposers.get(pkg.id)?.delete(dispose);
                            };
                            if (!sdkEventDisposers.has(pkg.id)) sdkEventDisposers.set(pkg.id, new Set());
                            sdkEventDisposers.get(pkg.id).add(dispose);
                            return dispose;
                        },
                        async openEditor(definition = null) {
                            requireCap("scene.shaders.customLibrary.openEditor");
                            const result = await window.GravewrightCustomShaderLibraries?.openEditor?.(definition ? clone(definition) : null);
                            return result ? freeze(clone(result)) : null;
                        },
                        preview(definition) {
                            requireCap("scene.shaders.customLibrary.preview");
                            return freeze(clone(window.GravewrightCustomShaderLibraries?.preview?.(clone(definition))));
                        },
                        clearPreview() {
                            requireCap("scene.shaders.customLibrary.clearPreview");
                            return freeze(clone(window.GravewrightCustomShaderLibraries?.clearPreview?.()));
                        },
                        async use(definition) {
                            requireCap("scene.shaders.customLibrary.use");
                            return freeze(clone(await window.GravewrightCustomShaderLibraries?.use?.(clone(definition))));
                        },
                    }),
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
                zones: Object.freeze({
                    async list(sceneId = context.scene?.id) { requireCap("scene.zones.list"); return (await runtimeRead("scene.zones", { scene_id: sceneId }, "sdk.scene.zones.list")).zones || []; },
                    async get(id) { requireCap("scene.zones.get"); return (await runtimeRead("scene.zones", { entity_id: id }, "sdk.scene.zones.get")).zone; },
                    async members(id) { requireCap("scene.zones.members"); return (await runtimeRead("scene.zones", { entity_id: id, action: "members" }, "sdk.scene.zones.members")).members || []; },
                    async create(sceneId, input = {}) { requireCap("scene.zones.create"); return (await runtimeCommand("zones.create", { sceneId, values: input }, "sdk.scene.zones.create")).zone; },
                    async update(id, patch = {}, options = {}) { requireCap("scene.zones.update"); return (await runtimeCommand("zones.update", { id, patch, expectedVersion: options.expectedVersion }, "sdk.scene.zones.update")).zone; },
                    async delete(id, options = {}) { requireCap("scene.zones.delete"); return runtimeCommand("zones.delete", { id, expectedVersion: options.expectedVersion }, "sdk.scene.zones.delete"); },
                }),
                objectTypes: Object.freeze({
                    async register(definition = {}) {
                        requireCap("scene.objectTypes.register");
                        await runtimeCommand("objectTypes.register", { definition }, "sdk.scene.objectTypes.register");
                        let disposed = false;
                        const dispose = () => { if (!disposed) { disposed = true; sdkEventDisposers.get(pkg.id)?.delete(dispose); } };
                        if (!sdkEventDisposers.has(pkg.id)) sdkEventDisposers.set(pkg.id, new Set());
                        sdkEventDisposers.get(pkg.id).add(dispose);
                        return dispose;
                    },
                }),
                objects: Object.freeze({
                    async list(sceneId = context.scene?.id, options = {}) { requireCap("scene.objects.list"); return (await runtimeRead("scene.objects", { scene_id: sceneId, q: options.query }, "sdk.scene.objects.list")).objects || []; },
                    async get(id) { requireCap("scene.objects.get"); return (await runtimeRead("scene.objects", { entity_id: id }, "sdk.scene.objects.get")).object; },
                    async hitTest(sceneId, point, options = {}) { requireCap("scene.objects.hitTest"); return (await runtimeRead("scene.objects", { scene_id: sceneId, action: "hitTest", q: point?.x, reference: point?.y, limit: options.tolerance ?? 8 }, "sdk.scene.objects.hitTest")).objects || []; },
                    async create(sceneId, input = {}) { requireCap("scene.objects.create"); return (await runtimeCommand("objects.create", { sceneId, input }, "sdk.scene.objects.create")).object; },
                    async update(id, patch = {}, options = {}) { requireCap("scene.objects.update"); return (await runtimeCommand("objects.update", { id, patch, expectedVersion: options.expectedVersion }, "sdk.scene.objects.update")).object; },
                    async delete(id, options = {}) { requireCap("scene.objects.delete"); return runtimeCommand("objects.delete", { id, expectedVersion: options.expectedVersion }, "sdk.scene.objects.delete"); },
                    async interact(id, interactionId, options = {}) { requireCap("scene.objects.interact"); return (await runtimeCommand("objects.interact", { id, interactionId, expectedVersion: options.expectedVersion }, "sdk.scene.objects.interact")).interaction; },
                }),
                spatialSounds: Object.freeze({
                    async list(sceneId = context.scene?.id) { requireCap("scene.spatialSounds.list"); return (await runtimeRead("scene.spatialSounds", { scene_id: sceneId }, "sdk.scene.spatialSounds.list")).spatialSounds || []; },
                    async get(id) { requireCap("scene.spatialSounds.get"); return (await runtimeRead("scene.spatialSounds", { entity_id: id }, "sdk.scene.spatialSounds.get")).spatialSound; },
                    async create(sceneId, input = {}) { requireCap("scene.spatialSounds.create"); return (await runtimeCommand("spatialSounds.create", { sceneId, input }, "sdk.scene.spatialSounds.create")).spatialSound; },
                    async update(id, patch = {}, options = {}) { requireCap("scene.spatialSounds.update"); return (await runtimeCommand("spatialSounds.update", { id, patch, expectedVersion: options.expectedVersion }, "sdk.scene.spatialSounds.update")).spatialSound; },
                    async delete(id, options = {}) { requireCap("scene.spatialSounds.delete"); return runtimeCommand("spatialSounds.delete", { id, expectedVersion: options.expectedVersion }, "sdk.scene.spatialSounds.delete"); },
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
        installInteractionHost(pkg, sdk);
        installSemanticHosts(pkg, sdk);
        try {
            runtime.ready?.(sdk, { package: pkg, context });
        } catch (err) {
            console.error(`GravewrightSDK ready failed for "${id}"`, err);
        }
    }

    const interactionHosts = new Set();
    const semanticHosts = new Set();
    function installSemanticHosts(pkg, sdk) {
        if (semanticHosts.has(pkg.id)) return;
        semanticHosts.add(pkg.id);
        const disposers = sdkEventDisposers.get(pkg.id) || new Set();
        sdkEventDisposers.set(pkg.id, disposers);
        if (caps.hasCapability(pkg, "scene.objects.read")) {
            const canvas = window.GravewrightMap?.activeCanvas?.() || document.querySelector("[data-map-canvas]");
            const viewport = canvas?.closest("[data-map-viewport]");
            if (canvas && viewport) {
                const layer = document.createElement("div");
                layer.dataset.sceneObjectLayer = pkg.id;
                Object.assign(layer.style, { position: "absolute", inset: "0", pointerEvents: "none", overflow: "hidden" });
                viewport.append(layer);
                let objects = [];
                const point = geometry => geometry.kind === "point" || geometry.kind === "circle" ? { x: geometry.x, y: geometry.y }
                    : geometry.kind === "rect" ? { x: geometry.x + geometry.width / 2, y: geometry.y + geometry.height / 2 }
                    : geometry.points?.length ? { x: (Math.min(...geometry.points.map(p=>p.x))+Math.max(...geometry.points.map(p=>p.x)))/2, y: (Math.min(...geometry.points.map(p=>p.y))+Math.max(...geometry.points.map(p=>p.y)))/2 } : { x: 0, y: 0 };
                const draw = () => {
                    const state = window.GravewrightMap?.stateFor?.(canvas);
                    if (!state) return;
                    layer.replaceChildren(...objects.filter(object => object.enabled).map(object => {
                        const anchor = point(object.geometry); const node = document.createElement("button"); node.type = "button";
                        node.dataset.sceneObjectId = object.id; node.dataset.sceneObjectType = object.typeId; node.dataset.sceneObjectVersion = String(object.version);
                        node.dataset.interactionCount = String(object.interactions?.length || 0);
                        node.title = object.presentation?.label || object.typeId;
                        node.textContent = object.providerAvailable === false ? "?" : object.presentation?.icon || object.presentation?.label || "◆";
                        Object.assign(node.style, { position: "absolute", pointerEvents: "auto", left: `${state.offsetX + anchor.x * state.zoom}px`, top: `${state.offsetY + anchor.y * state.zoom}px`, transform: "translate(-50%,-50%)", opacity: String(Math.max(.1, Math.min(1, Number(object.presentation?.opacity ?? 1)))) });
                        const geometry=object.geometry;const stroke=object.presentation?.stroke||"#f3c969";const fill=object.presentation?.fill||"rgba(243,201,105,.2)";
                        if(geometry.kind==="rect"||geometry.kind==="circle"){node.style.width=`${(geometry.kind==="rect"?geometry.width:geometry.radius*2)*state.zoom}px`;node.style.height=`${(geometry.kind==="rect"?geometry.height:geometry.radius*2)*state.zoom}px`;node.style.border=`${Math.max(1,Number(object.presentation?.lineWidth||2))}px solid ${stroke}`;node.style.background=fill;if(geometry.kind==="circle")node.style.borderRadius="50%";}
                        if(geometry.kind==="polygon"||geometry.kind==="polyline"){const xs=geometry.points.map(p=>p.x),ys=geometry.points.map(p=>p.y),minX=Math.min(...xs),maxX=Math.max(...xs),minY=Math.min(...ys),maxY=Math.max(...ys);node.style.width=`${Math.max(1,(maxX-minX)*state.zoom)}px`;node.style.height=`${Math.max(1,(maxY-minY)*state.zoom)}px`;node.style.background=geometry.kind==="polygon"?fill:"transparent";if(geometry.kind==="polygon"){node.style.border=`${Math.max(1,Number(object.presentation?.lineWidth||2))}px solid ${stroke}`;node.style.clipPath=`polygon(${geometry.points.map(p=>`${(p.x-minX)/(maxX-minX||1)*100}% ${(p.y-minY)/(maxY-minY||1)*100}%`).join(",")})`;}else{node.textContent="";const svg=document.createElementNS("http://www.w3.org/2000/svg","svg");svg.setAttribute("viewBox",`0 0 ${maxX-minX||1} ${maxY-minY||1}`);svg.setAttribute("width","100%");svg.setAttribute("height","100%");const line=document.createElementNS(svg.namespaceURI,"polyline");line.setAttribute("points",geometry.points.map(p=>`${p.x-minX},${p.y-minY}`).join(" "));line.setAttribute("fill","none");line.setAttribute("stroke",stroke);line.setAttribute("stroke-width",String(Math.max(1,Number(object.presentation?.lineWidth||2))/state.zoom));svg.append(line);node.append(svg);}}
                        node.addEventListener("click", () => { layer.querySelectorAll("[aria-selected]").forEach(n => n.removeAttribute("aria-selected")); node.setAttribute("aria-selected", "true"); document.dispatchEvent(new CustomEvent("vtt:scene-object-selected", { detail: { id: object.id, typeId: object.typeId } })); const interaction=object.interactions?.[0];if(interaction)void sdk.scene.objects.interact(object.id,interaction.id,{expectedVersion:object.version}); });
                        node.addEventListener("contextmenu", event => {
                            event.preventDefault();const properties=object.dataSchema?.properties||{};if(!object.providerAvailable||!Object.keys(properties).length)return;
                            const dialog=document.createElement("dialog");dialog.dataset.sceneObjectEditor=object.id;const form=document.createElement("form");form.method="dialog";const draft=clone(object.data||{});
                            for(const [key,rule] of Object.entries(properties).slice(0,32)){if(!rule||!["string","number","integer","boolean"].includes(rule.type)&&!Array.isArray(rule.enum))continue;const label=document.createElement("label");label.append(document.createTextNode(String(rule.title||key)));let input;if(Array.isArray(rule.enum)){input=document.createElement("select");for(const value of rule.enum){const option=document.createElement("option");option.value=String(value);option.textContent=String(value);option.selected=value===draft[key];input.append(option);}}else{input=document.createElement("input");input.type=rule.type==="boolean"?"checkbox":rule.type==="number"||rule.type==="integer"?"number":"text";if(input.type==="checkbox")input.checked=Boolean(draft[key]);else input.value=String(draft[key]??"");}input.addEventListener("input",()=>{draft[key]=input.type==="checkbox"?input.checked:rule.type==="number"?Number(input.value):rule.type==="integer"?Math.trunc(Number(input.value)):input.value;});label.append(input);form.append(label);}
                            const save=document.createElement("button");save.type="submit";save.textContent="Save";const cancel=document.createElement("button");cancel.type="button";cancel.textContent="Cancel";cancel.addEventListener("click",()=>dialog.close());form.append(cancel,save);form.addEventListener("submit",async submit=>{submit.preventDefault();try{Object.assign(object,await sdk.scene.objects.update(object.id,{data:draft},{expectedVersion:object.version}));dialog.close();}catch(error){console.error("Scene object edit failed",error);}});dialog.addEventListener("close",()=>dialog.remove(),{once:true});dialog.append(form);document.body.append(dialog);dialog.showModal();
                        });
                        if (object.editor?.movable && caps.hasCapability(pkg, "scene.objects.write")) node.addEventListener("pointerdown", event => {
                            event.preventDefault(); node.setPointerCapture(event.pointerId);
                            const original=clone(object.geometry); const start=window.GravewrightMap.worldFromScreen(canvas,event.clientX,event.clientY);
                            const shifted=(geometry,dx,dy)=>geometry.kind==="point"||geometry.kind==="circle"?{...geometry,x:geometry.x+dx,y:geometry.y+dy}:geometry.kind==="rect"?{...geometry,x:geometry.x+dx,y:geometry.y+dy}:{...geometry,points:geometry.points.map(p=>({x:p.x+dx,y:p.y+dy}))};
                            const move=next=>{const current=window.GravewrightMap.worldFromScreen(canvas,next.clientX,next.clientY);object.geometry=shifted(original,current.worldX-start.worldX,current.worldY-start.worldY);position();};
                            const cancel=()=>{object.geometry=original;position();cleanup();};
                            const commit=async next=>{move(next);cleanup();try{const updated=await sdk.scene.objects.update(object.id,{geometry:object.geometry},{expectedVersion:object.version});Object.assign(object,updated);}catch(_){object.geometry=original;}position();};
                            const cleanup=()=>{node.removeEventListener("pointermove",move);node.removeEventListener("pointerup",commit);node.removeEventListener("pointercancel",cancel);};
                            node.addEventListener("pointermove",move);node.addEventListener("pointerup",commit);node.addEventListener("pointercancel",cancel);
                        });
                        return node;
                    }));
                };
                const position = () => {
                    const state=window.GravewrightMap?.stateFor?.(canvas);if(!state)return;
                    for(const node of layer.querySelectorAll("[data-scene-object-id]")){const object=objects.find(item=>item.id===node.dataset.sceneObjectId);if(!object)continue;const anchor=point(object.geometry);node.style.left=`${state.offsetX+anchor.x*state.zoom}px`;node.style.top=`${state.offsetY+anchor.y*state.zoom}px`;}
                };
                const refresh = async () => { try { objects = await sdk.scene.objects.list(context.scene?.id); draw(); } catch (_) {} };
                const onEvent = event => { if (["scene.objects.changed","scene.changed","token.moved"].includes(event.detail?.event)) void refresh(); };
                const onMapViewChanged = event => { if (event.detail?.canvas === canvas) position(); };
                document.addEventListener("vtt:transport-event", onEvent); document.addEventListener("vtt:map-view-changed", onMapViewChanged); window.addEventListener("resize", draw); void refresh();
                disposers.add(() => { window.removeEventListener("resize", draw); document.removeEventListener("vtt:map-view-changed", onMapViewChanged); document.removeEventListener("vtt:transport-event", onEvent); layer.remove(); });
            }
        }
        if (caps.hasCapability(pkg, "ui.presentations")) {
            const host = document.createElement("section"); host.dataset.semanticPresentationHost = pkg.id;
            Object.assign(host.style, { position: "fixed", inset: "0", pointerEvents: "none", zIndex: "10000" }); document.body.append(host);
            let timer;const acknowledged=new Set();
            const render = async () => {
                window.clearTimeout(timer);
                let presentations=[]; try { presentations=await sdk.ui.presentations.list({ sceneId: context.scene?.id }); } catch (_) { timer=window.setTimeout(render,60000);return; }
                for(const p of presentations){if(p.status==="active"&&p.audience?.ids?.includes(context.user?.id)&&p.endsAt&&Date.now()>=p.endsAt&&!acknowledged.has(p.id)){acknowledged.add(p.id);void runtimeCommand("presentations.ack",{id:p.id},"core.presentations.ack").catch(()=>acknowledged.delete(p.id));}}
                host.replaceChildren(...presentations.filter(p => p.status==="active"&&p.audience?.ids?.includes(context.user?.id)&&(!p.endsAt||Date.now()<p.endsAt)).map(p => {
                    const node=document.createElement("article"); node.dataset.presentationId=p.id; node.dataset.presentationMode=p.mode;
                    Object.assign(node.style,{pointerEvents:"auto",position:"absolute",left:"50%",top:p.mode==="world-anchor"?"40%":"15%",transform:"translateX(-50%)",maxWidth:"32rem"});
                    if (p.mode==="world-anchor" && p.anchor) {
                        const target=document.querySelector(p.anchor.kind==="scene-object"?`[data-scene-object-id="${CSS.escape(p.anchor.id)}"]`:`[data-token-id="${CSS.escape(p.anchor.id)}"]`);
                        if (target) { const box=target.getBoundingClientRect();node.style.left=`${box.left+box.width/2}px`;node.style.top=`${box.top}px`;node.style.transform="translate(-50%,-100%)"; }
                        else if (p.anchor.kind==="token") {
                            const canvas=window.GravewrightMap?.activeCanvas?.();const state=canvas&&window.GravewrightMap?.stateFor?.(canvas);const token=canvas&&window.GravewrightMap?.tokenStoreFor?.(canvas)?.get?.(p.anchor.id);const box=canvas?.getBoundingClientRect();const grid=Number(canvas?.dataset.sceneGridSize||canvas?.dataset.sceneTileSize||70);
                            if(!state||!token||!box)node.hidden=true;else{node.style.left=`${box.left+state.offsetX+(Number(token.grid_x)+Number(token.width_cells||1)/2)*grid*state.zoom}px`;node.style.top=`${box.top+state.offsetY+Number(token.grid_y)*grid*state.zoom}px`;node.style.transform="translate(-50%,-100%)";}
                        } else node.hidden=true;
                    }
                    if (p.mode==="screen-overlay" || p.mode==="fade") Object.assign(node.style,{inset:"0",transform:"none",maxWidth:"none",background:`rgba(0,0,0,${Math.max(0,Math.min(1,Number(p.content?.value ?? .65)))})`});
                    if(p.content?.preset==="letterbox")Object.assign(node.style,{borderBlock:"10vh solid #000",background:"transparent"});
                    if(p.content?.preset==="damage-flash")node.style.background="rgba(180,0,0,.45)";
                    if(p.content?.asset){const img=document.createElement("img");img.alt="";img.src=p.content.asset.kind==="package-asset"?`/sdk/packages/${encodeURIComponent(p.packageId)}/asset/${p.content.asset.id.split("/").map(encodeURIComponent).join("/")}`:`/game/journal/asset/${encodeURIComponent(p.content.asset.id)}`;Object.assign(img.style,{maxWidth:"100%",maxHeight:"100%",objectFit:"contain"});node.append(img);}
                    for (const key of ["title","subtitle","text","label"]) if (p.content?.[key]) { const el=document.createElement(key==="title"?"h2":"p"); el.textContent=p.content[key]; node.append(el); }
                    if (p.mode==="countdown" && p.deadline) { const value=document.createElement("time"); value.textContent=String(Math.max(0,p.deadline-Math.floor(Date.now()/1000))); node.append(value); }
                    for (const button of p.content?.buttons || []) { const el=document.createElement("button");el.type="button";el.textContent=button.label;el.addEventListener("click",()=>void sdk.rules?.actions?.executeReference?.(button.actionReference,{},{}));node.append(el); }
                    return node;
                }));
                const hasLiveClock = presentations.some(p => p.status === "active"
                    && p.audience?.ids?.includes(context.user?.id) && (p.endsAt || p.deadline));
                timer = window.setTimeout(render, hasLiveClock ? 1000 : 60000);
            };
            const onEvent=event=>{if (["ui.presentation.changed","scene.activated","token.moved","token.updated","token.deleted","scene.objects.changed"].includes(event.detail?.event))void render();};
            document.addEventListener("vtt:transport-event",onEvent);void render();
            disposers.add(()=>{window.clearTimeout(timer);document.removeEventListener("vtt:transport-event",onEvent);host.remove();void sdk.ui.presentations.list().then(rows=>Promise.all(rows.map(row=>sdk.ui.presentations.close(row.id,{expectedVersion:row.version}).catch(()=>null)))).catch(()=>null);});
        }
    }
    function installInteractionHost(pkg, sdk) {
        if (interactionHosts.has(pkg.id) || !caps.hasCapability(pkg, "interactions.respond")) return;
        interactionHosts.add(pkg.id);
        let showing = false;
        const present = async () => {
            if (showing) return;
            let pending;
            try { pending = await sdk.interactions.list({ status: "open", recipient: "me" }); }
            catch (_) { return; }
            const interaction = pending[0];
            if (!interaction) return;
            showing = true;
            const dialog = document.createElement("dialog");
            dialog.dataset.testid = "directed-interaction";
            const form = document.createElement("form"); form.method = "dialog";
            const title = document.createElement("h2"); title.textContent = interaction.prompt.title;
            title.dataset.testid = "directed-interaction-title";
            const text = document.createElement("p"); text.textContent = interaction.prompt.text;
            text.dataset.testid = "directed-interaction-prompt";
            const field = document.createElement("div"); const schema = interaction.responseSchema;
            let control;
            if (schema.type === "boolean") {
                control = document.createElement("input"); control.type = "checkbox";
                const label = document.createElement("label"); label.append(control, document.createTextNode(" Yes")); field.append(label);
            } else if (schema.type === "single-choice" || schema.type === "multi-choice") {
                control = document.createElement("select"); control.multiple = schema.type === "multi-choice";
                for (const choice of schema.choices || []) { const option = document.createElement("option"); option.value = choice.id; option.textContent = choice.label; control.append(option); }
                field.append(control);
            } else {
                control = document.createElement("input"); control.type = schema.type === "number" ? "number" : "text";
                if (schema.minimum != null) control.min = String(schema.minimum); if (schema.maximum != null) control.max = String(schema.maximum); if (schema.maxLength) control.maxLength = schema.maxLength;
                field.append(control);
            }
            control.dataset.testid = "directed-interaction-response";
            const decline = document.createElement("button"); decline.type = "button"; decline.textContent = "Close";
            const submit = document.createElement("button"); submit.type = "submit"; submit.textContent = "Respond";
            submit.dataset.testid = "directed-interaction-submit";
            form.append(title, text, field, decline, submit); dialog.append(form); document.body.append(dialog);
            decline.addEventListener("click", () => dialog.close());
            form.addEventListener("submit", async event => {
                event.preventDefault();
                let value = schema.type === "boolean" ? control.checked : schema.type === "multi-choice" ? [...control.selectedOptions].map(option => option.value) : schema.type === "number" ? Number(control.value) : control.value;
                try { await sdk.interactions.respond(interaction.id, value, { expectedVersion: interaction.version, idempotencyKey: `${interaction.id}:${interaction.version}` }); dialog.close(); } catch (error) { console.error("Directed interaction response failed", error); }
            });
            dialog.addEventListener("close", () => { showing = false; dialog.remove(); queueMicrotask(present); }, { once: true });
            dialog.showModal();
        };
        document.addEventListener("vtt:transport-event", event => { if (event.detail?.event === "interaction.changed") void present(); });
        void present();
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
