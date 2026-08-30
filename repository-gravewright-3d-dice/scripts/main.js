(function () {
    "use strict";

    const PACKAGE_ID = "gravewright-3d-dice";
    const Core = globalThis.Gravewright3DDiceCore;
    const PACKAGE_VERSION = "1.2.0";
    let rendererModule = globalThis.Gravewright3DDiceRenderer || null;
    let rendererPromise = null;
    let stylePromise = null;
    let runtime = null;

    function createRuntime(sdk) {
        const disposers = [];
        const seen = new Set();
        const seenOrder = [];
        let renderer = null;
        let overlayHost = null;
        let disposed = false;

        function remember(id) {
            const key = String(id || "");
            if (!key || seen.has(key)) return false;
            seen.add(key);
            seenOrder.push(key);
            if (seenOrder.length > 500) seen.delete(seenOrder.shift());
            return true;
        }

        async function animateMessage(messageId) {
            if (disposed || !remember(messageId)) return;
            try {
                const message = await sdk.chat.get(messageId);
                if (!message || !Array.isArray(message.groups) || !message.groups.length) return;
                const dice = Core.visualDice(message.groups);
                if (!dice.length || disposed) return;
                const activeRenderer = await ensureRenderer();
                if (!activeRenderer || disposed) return;
                const color = Core.normalizeColor(sdk.settings.get("dice_color", Core.FALLBACK_COLOR));
                const fontColor = Core.normalizeColor(sdk.settings.get("font_color", "#ffffff"));
                activeRenderer.enqueue({id: message.id, dice, color, fontColor, authorUserId: message.author_user_id});
            } catch (error) {
                console.warn("Gravewright 3D Dice skipped an unavailable roll", error);
            }
        }

        function packageAsset(path) {
            return `/sdk/packages/${PACKAGE_ID}/asset/${path}?v=${PACKAGE_VERSION}`;
        }

        function loadStyles() {
            if (stylePromise) return stylePromise;
            stylePromise = new Promise((resolve, reject) => {
                const link = document.createElement("link");
                link.rel = "stylesheet";
                link.href = packageAsset("styles/gravewright-3d-dice.css");
                link.onload = resolve;
                link.onerror = reject;
                document.head.appendChild(link);
            });
            return stylePromise;
        }

        function loadRenderer() {
            if (rendererModule) return Promise.resolve(rendererModule);
            if (rendererPromise) return rendererPromise;
            rendererPromise = new Promise((resolve, reject) => {
                const script = document.createElement("script");
                script.src = packageAsset("scripts/dice-renderer.js");
                script.async = true;
                script.onload = () => {
                    rendererModule = globalThis.Gravewright3DDiceRenderer || null;
                    if (rendererModule) resolve(rendererModule);
                    else reject(new Error("3D dice renderer did not register"));
                };
                script.onerror = () => reject(new Error("Could not load 3D dice renderer"));
                document.head.appendChild(script);
            });
            return rendererPromise;
        }

        async function ensureRenderer() {
            if (renderer || disposed || !overlayHost) return renderer;
            const [, loadedRenderer] = await Promise.all([loadStyles(), loadRenderer()]);
            if (!renderer && !disposed && overlayHost) renderer = new loadedRenderer.DiceRenderer(overlayHost);
            return renderer;
        }

        async function ready() {
            if (disposed) return;
            const available = sdk.ui.slots.available();
            if (available.includes("settings.modules")) {
                disposers.push(sdk.ui.slots.register("settings.modules", host => {
                    mountModuleSettings(host, sdk);
                    const modal = host.closest("[data-modal-window]");
                    if (modal && !modal.hidden) void loadStyles().catch(() => {});
                }));
                const onModalOpened = event => {
                    if (event.detail?.modal?.getElementsByClassName?.("dice-module-setup").length) {
                        void loadStyles().catch(() => {});
                    }
                };
                document.addEventListener("vtt:modal-opened", onModalOpened);
                disposers.push(() => document.removeEventListener("vtt:modal-opened", onModalOpened));
            }
            if (available.includes("board.overlay")) {
                disposers.push(sdk.ui.slots.register("board.overlay", host => {
                    overlayHost = host;
                    if (!host.firstElementChild) {
                        const shell = document.createElement("div");
                        shell.className = "gravewright-3d-dice";
                        shell.dataset.activeDice = "0";
                        shell.dataset.physicsBodies = "0";
                        shell.dataset.queuedRolls = "0";
                        host.appendChild(shell);
                    }
                }));
            }

            disposers.push(sdk.events.on("chat.created", event => {
                if (event.resourceId) void animateMessage(event.resourceId);
            }));
            try {
                const history = await sdk.chat.list({limit: 100});
                history.forEach(message => remember(message.id));
            } catch (error) {
                console.warn("Gravewright 3D Dice could not initialize roll deduplication", error);
            }
        }

        function destroy() {
            if (disposed) return;
            disposed = true;
            while (disposers.length) {
                try { disposers.pop()(); } catch (error) { console.warn("Gravewright 3D Dice disposer failed", error); }
            }
            renderer?.destroy();
            renderer = null;
            overlayHost = null;
            seen.clear();
            seenOrder.length = 0;
        }

        return Object.freeze({ready, destroy, snapshot: () => renderer?.snapshot() || {activeDice: 0, physicsBodies: 0, queuedRolls: 0, animationCallbacks: 0}});
    }

    function element(tag, className, text) {
        const node = document.createElement(tag);
        if (className) node.className = className;
        if (text !== undefined) node.textContent = text;
        return node;
    }

    function mountModuleSettings(host, sdk) {
        const editable = host.parentElement?.dataset.canEdit === "true";
        const form = element("form", "dice-module-setup");
        const header = element("header", "dice-module-setup__header");
        header.append(
            element("h3", "", "Dados 3D"),
            element("p", "", "Escolha as cores usadas nos próximos lançamentos desta mesa."),
        );
        const preview = element("div", "dice-module-setup__preview");
        preview.setAttribute("aria-hidden", "true");
        const die = element("span", "dice-module-setup__die", "20");
        preview.append(die);
        const fields = element("div", "dice-module-setup__fields");
        const colorField = (labelText, key, fallback) => {
            const label = element("label", "dice-module-setup__field");
            const caption = element("span", "", labelText);
            const input = document.createElement("input");
            input.type = "color";
            input.value = Core.normalizeColor(sdk.settings.get(key, fallback));
            input.disabled = !editable;
            label.append(caption, input);
            fields.append(label);
            return input;
        };
        const diceColor = colorField("Cor do dado", "dice_color", Core.FALLBACK_COLOR);
        const fontColor = colorField("Cor da fonte", "font_color", "#ffffff");
        const paintPreview = () => {
            die.style.backgroundColor = diceColor.value;
            die.style.color = fontColor.value;
        };
        diceColor.addEventListener("input", paintPreview);
        fontColor.addEventListener("input", paintPreview);
        paintPreview();
        const footer = element("footer", "dice-module-setup__footer");
        const status = element("output", "dice-module-setup__status");
        status.setAttribute("aria-live", "polite");
        const save = element("button", "dice-module-setup__save", "Salvar configuração");
        save.type = "submit";
        save.disabled = !editable;
        footer.append(status, save);
        form.addEventListener("submit", async event => {
            event.preventDefault();
            save.disabled = true;
            status.textContent = "Salvando…";
            try {
                await sdk.settings.set("dice_color", diceColor.value);
                await sdk.settings.set("font_color", fontColor.value);
                status.textContent = "Configuração salva.";
            } catch (error) {
                status.textContent = String(error?.message || error);
            } finally {
                save.disabled = !editable;
            }
        });
        form.append(header, preview, fields, footer);
        host.replaceChildren(form);
    }

    globalThis.GravewrightSDK.register({
        id: PACKAGE_ID,
        setup(sdk) {
            runtime?.destroy();
            runtime = createRuntime(sdk);
        },
        async ready(sdk) {
            if (!runtime) runtime = createRuntime(sdk);
            await runtime.ready();
        },
        unload() {
            runtime?.destroy();
            runtime = null;
        },
    });
})();
