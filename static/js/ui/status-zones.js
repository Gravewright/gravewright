(() => {
    
    const roomZones = new Map();
    const selectedTokensByRoom = new Map();
    let activeEffectTooltip = null;

    function zoneFor(roomId) {
        if (!roomZones.has(roomId)) {
            
            
            roomZones.set(roomId, { players: new Map(), monsters: new Map(), all: new Map() });
        }
        return roomZones.get(roomId);
    }

    function classify(token) {
        if (token.disposition === "friendly") return "players";
        if (token.disposition === "hostile") return "monsters";
        return null;
    }

    function roomIdForScene(sceneId) {
        return document.querySelector(
            `[data-map-canvas][data-scene-id="${sceneId}"]`
        )?.dataset.roomId ?? null;
    }

    function applySnapshot(sceneId, tokens) {
        const roomId = roomIdForScene(sceneId);
        if (!roomId) return;
        const zone = zoneFor(roomId);
        zone.players.clear();
        zone.monsters.clear();
        zone.all.clear();
        for (const tv of tokens) {
            zone.all.set(tv.token_id, tv);
            const side = classify(tv);
            if (side) zone[side].set(tv.token_id, tv);
        }
        renderZones(roomId);
    }

    function applyAdded(sceneId, tokens) {
        const roomId = roomIdForScene(sceneId);
        if (!roomId) return;
        const zone = zoneFor(roomId);
        for (const tv of tokens) {
            zone.all.set(tv.token_id, tv);
            const side = classify(tv);
            if (side) zone[side].set(tv.token_id, tv);
        }
        renderZones(roomId);
    }

    function applyMoved(sceneId, moves) {
        
        const roomId = roomIdForScene(sceneId);
        if (!roomId) return;
        const zone = zoneFor(roomId);
        for (const move of moves) {
            for (const side of ["players", "monsters", "all"]) {
                const t = zone[side].get(move.token_id);
                if (t) {
                    zone[side].set(move.token_id, {
                        ...t,
                        grid_x: move.grid_x,
                        grid_y: move.grid_y,
                        version: move.version ?? t.version,
                    });
                }
            }
        }
        
    }

    function applyDeleted(sceneId, tokenIds) {
        const roomId = roomIdForScene(sceneId);
        if (!roomId) return;
        const zone = zoneFor(roomId);
        for (const id of tokenIds) {
            zone.players.delete(id);
            zone.monsters.delete(id);
            zone.all.delete(id);
        }
        renderZones(roomId);
    }

    function applyVisibilityChanged(sceneId, changes) {
        const roomId = roomIdForScene(sceneId);
        if (!roomId) return;
        const zone = zoneFor(roomId);
        for (const change of changes) {
            for (const side of ["players", "monsters", "all"]) {
                const t = zone[side].get(change.token_id);
                if (t) {
                    zone[side].set(change.token_id, { ...t, hidden: change.hidden });
                }
            }
        }
        renderZones(roomId);
    }

    function applyConditionsUpdated(sceneId, tokenId, conditions) {
        const roomId = roomIdForScene(sceneId);
        if (!roomId) return;
        const zone = zoneFor(roomId);
        let changed = false;
        for (const side of ["players", "monsters", "all"]) {
            const t = zone[side].get(tokenId);
            if (t) {
                zone[side].set(tokenId, { ...t, conditions });
                changed = true;
            }
        }
        if (changed) renderZones(roomId);
    }

    

    function renderZones(roomId) {
        const zone = zoneFor(roomId);
        const playerEl = document.querySelector(`.status-zone--players[data-room-id="${roomId}"]`);
        const monsterEl = document.querySelector(`.status-zone--monsters[data-room-id="${roomId}"]`);
        if (playerEl) renderZoneEl(playerEl, zone.players);
        if (monsterEl) renderZoneEl(monsterEl, zone.monsters);
        if (isActiveRoom(roomId)) renderEffectsHud(roomId);
    }

    function isActiveRoom(roomId) {
        const active = document.querySelector(".room-workspace.is-active");
        return active ? active.dataset.roomId === roomId : true;
    }

    function effectIconName(effect) {
        return String(effect?.category || "").toLowerCase().includes("debuff") ? "skull" : "sparkle";
    }

    function roomIsGm(roomId) {
        const room = document.querySelector(`.room-workspace[data-room-id="${CSS.escape(roomId)}"]`);
        return room?.dataset.isGm === "true";
    }

    function categoryLabel(category) {
        const value = String(category || "").toLowerCase();
        if (value.includes("debuff")) return "Debuff";
        if (value.includes("buff")) return "Buff";
        if (value.includes("condition")) return "Condição";
        return value || "Efeito";
    }

    function durationLabel(duration) {
        if (!duration || typeof duration !== "object") return "";
        const type = String(duration.type || "").toLowerCase();
        if (!type || type === "permanent") return "Permanente";
        if (type === "rounds") {
            const remaining = duration.remaining ?? duration.value;
            return remaining != null ? `${remaining} rodada(s)` : "Rodadas";
        }
        if (type === "minutes") {
            const value = duration.remaining ?? duration.value;
            return value != null ? `${value} minuto(s)` : "Minutos";
        }
        if (type === "session") return "Sessão";
        return type;
    }

    function modifierLabel(modifier) {
        if (!modifier || typeof modifier !== "object") return "";
        const target = modifier.target ? String(modifier.target) : "";
        const operation = modifier.operation ? String(modifier.operation).replaceAll("_", " ") : "";
        const value = modifier.value != null && modifier.value !== "" ? ` ${modifier.value}` : "";
        const label = modifier.label ? String(modifier.label) : "";
        return [label, target, operation + value].filter(Boolean).join(" · ");
    }

    function appendTooltipLine(parent, className, text) {
        if (!text) return;
        const node = document.createElement("div");
        node.className = className;
        node.textContent = text;
        parent.appendChild(node);
    }

    function positionEffectTooltip(anchor) {
        if (!activeEffectTooltip || !anchor) return;
        const rect = anchor.getBoundingClientRect();
        const margin = 10;
        const tip = activeEffectTooltip;
        const height = tip.offsetHeight || 0;
        const width = tip.offsetWidth || 0;
        let left = rect.left - width - margin;
        if (left < margin) left = rect.right + margin;
        left = Math.max(margin, Math.min(left, window.innerWidth - width - margin));
        const top = Math.max(margin, Math.min(rect.top + (rect.height - height) / 2, window.innerHeight - height - margin));
        tip.style.left = `${Math.round(left)}px`;
        tip.style.top = `${Math.round(top)}px`;
    }

    function showEffectTooltip(effect, token, anchor) {
        hideEffectTooltip();
        const tip = document.createElement("div");
        tip.className = "gw-effect-tooltip";
        tip.setAttribute("role", "tooltip");

        appendTooltipLine(tip, "gw-effect-tooltip__token", token.name || "Token");
        appendTooltipLine(tip, "gw-effect-tooltip__title", effect.name || "Efeito");
        appendTooltipLine(tip, "gw-effect-tooltip__meta", categoryLabel(effect.category));
        appendTooltipLine(tip, "gw-effect-tooltip__body", effect.description || "");
        const duration = durationLabel(effect.duration);
        appendTooltipLine(tip, "gw-effect-tooltip__detail", duration ? `Duração: ${duration}` : "");
        appendTooltipLine(tip, "gw-effect-tooltip__detail", effect.concentration ? "Concentração" : "");
        (Array.isArray(effect.modifiers) ? effect.modifiers : []).slice(0, 4).forEach((modifier) => {
            appendTooltipLine(tip, "gw-effect-tooltip__detail", modifierLabel(modifier));
        });

        document.body.appendChild(tip);
        activeEffectTooltip = tip;
        positionEffectTooltip(anchor);
    }

    function hideEffectTooltip() {
        if (!activeEffectTooltip) return;
        activeEffectTooltip.remove();
        activeEffectTooltip = null;
    }

    
    
    function renderEffectsHud(roomId) {
        let hud = document.querySelector("[data-active-effects-hud]");
        if (!hud) {
            hud = document.createElement("aside");
            hud.className = "gw-effects-hud";
            hud.dataset.activeEffectsHud = "1";
            document.body.appendChild(hud);
        }
        const zone = zoneFor(roomId);
        const isGm = roomIsGm(roomId);
        const units = [...zone.all.values()]
            .filter((t) => (isGm || !t.hidden) && Array.isArray(t.effects) && t.effects.length);
        hud.innerHTML = "";
        if (!units.length) {
            hud.hidden = true;
            hideEffectTooltip();
            return;
        }
        hud.hidden = false;
        units.forEach((token) => {
            const row = document.createElement("div");
            row.className = "gw-effects-hud__row";

            const portrait = document.createElement("div");
            portrait.className = "gw-effects-hud__portrait";
            portrait.title = token.name || "";
            if (token.asset_url) {
                const img = document.createElement("img");
                img.className = "gw-effects-hud__portrait-img";
                img.src = token.asset_url;
                img.alt = token.name || "";
                portrait.appendChild(img);
            } else {
                const glyph = document.createElement("i");
                glyph.className = "ph ph-user gw-effects-hud__portrait-glyph";
                glyph.setAttribute("aria-hidden", "true");
                portrait.appendChild(glyph);
            }
            row.appendChild(portrait);

            const list = document.createElement("div");
            list.className = "gw-effects-hud__list";
            token.effects.forEach((effect) => {
                const item = document.createElement("div");
                item.className = "gw-effects-hud__icon";
                item.tabIndex = 0;
                item.setAttribute("role", "img");
                item.setAttribute("aria-label", `${effect.name || "Efeito"}: ${effect.description || categoryLabel(effect.category)}`);
                item.addEventListener("mouseenter", () => showEffectTooltip(effect, token, item));
                item.addEventListener("mousemove", () => positionEffectTooltip(item));
                item.addEventListener("mouseleave", hideEffectTooltip);
                item.addEventListener("focus", () => showEffectTooltip(effect, token, item));
                item.addEventListener("blur", hideEffectTooltip);
                if (effect.img) {
                    const im = document.createElement("img");
                    im.className = "gw-effects-hud__img";
                    im.src = effect.img;
                    im.alt = effect.name || "";
                    item.appendChild(im);
                } else {
                    const ic = document.createElement("i");
                    ic.className = `ph ph-${effectIconName(effect)} gw-effects-hud__glyph`;
                    ic.setAttribute("aria-hidden", "true");
                    item.appendChild(ic);
                }
                list.appendChild(item);
            });
            row.appendChild(list);
            hud.appendChild(row);
        });
    }

    function markSelected(roomId, tokenId) {
        if (roomId) {
            if (tokenId) selectedTokensByRoom.set(roomId, tokenId);
            else selectedTokensByRoom.delete(roomId);
        }

        const selector = roomId
            ? `[data-status-zone][data-room-id="${CSS.escape(roomId)}"] [data-status-unit]`
            : "[data-status-zone] [data-status-unit]";
        document.querySelectorAll(selector).forEach((unit) => {
            const selected = Boolean(tokenId) && unit.dataset.tokenId === tokenId;
            unit.classList.toggle("sz-unit--selected", selected);
            unit.setAttribute("aria-pressed", selected ? "true" : "false");
        });
    }

    function renderZoneEl(container, unitMap) {
        const isGm = container.dataset.isGm === "true";
        const selectedTokenId = selectedTokensByRoom.get(container.dataset.roomId || "") || null;
        const frag = document.createDocumentFragment();

        unitMap.forEach((token) => {
            if (token.hidden && !isGm) return;
            frag.appendChild(buildUnitElement(token, selectedTokenId));
        });

        container.innerHTML = "";
        container.appendChild(frag);
    }

    function buildUnitElement(token, selectedTokenId) {
        const selected = token.token_id === selectedTokenId;
        const div = document.createElement("div");
        div.className = "sz-unit"
            + (token.hidden ? " sz-unit--hidden" : "")
            + (selected ? " sz-unit--selected" : "");
        div.dataset.statusUnit = "";
        div.dataset.tokenId = token.token_id;
        div.tabIndex = 0;
        div.setAttribute("role", "button");
        div.setAttribute("aria-pressed", selected ? "true" : "false");
        div.setAttribute("aria-label", token.name || "Token");

        
        const nameRow = document.createElement("div");
        nameRow.className = "sz-unit-name-row";

        const dot = document.createElement("span");
        dot.className = `sz-disp-dot sz-disp-dot--${token.disposition || "neutral"}`;
        dot.setAttribute("aria-hidden", "true");
        nameRow.appendChild(dot);

        const nameEl = document.createElement("span");
        nameEl.className = "sz-unit-name";
        nameEl.textContent = token.name || "???";
        nameRow.appendChild(nameEl);

        const hp = token.bars?.hp;
        if (hp && hp.max > 0) {
            const hpText = document.createElement("span");
            hpText.className = "sz-unit-hp-text";
            hpText.textContent = `${hp.value}/${hp.max}`;
            nameRow.appendChild(hpText);
        }

        div.appendChild(nameRow);

        
        if (hp && hp.max > 0) {
            const ratio = Math.max(0, Math.min(1, hp.value / hp.max));
            const barWrap = document.createElement("div");
            barWrap.className = "sz-unit-hp-bar-wrap";
            const fill = document.createElement("div");
            let fillCls = "sz-unit-hp-bar-fill";
            if (ratio <= 0.25) fillCls += " sz-unit-hp-bar-fill--low";
            else if (ratio <= 0.5) fillCls += " sz-unit-hp-bar-fill--mid";
            fill.className = fillCls;
            fill.style.width = `${Math.round(ratio * 100)}%`;
            barWrap.appendChild(fill);
            div.appendChild(barWrap);
        }

        
        const conditions = token.conditions || [];
        if (conditions.length > 0) {
            const condRow = document.createElement("div");
            condRow.className = "sz-unit-conditions";
            conditions.forEach((cond) => {
                const pill = document.createElement("span");
                pill.className = `sz-condition sz-condition--${cond.kind || "neutral"}`;
                pill.textContent = cond.label;
                if (cond.duration != null) {
                    pill.title = `${cond.label} (${cond.duration})`;
                }
                condRow.appendChild(pill);
            });
            div.appendChild(condRow);
        }

        return div;
    }

    

    document.addEventListener("click", (event) => {
        const unit = event.target.closest("[data-status-unit]");
        if (!unit) return;
        const tokenId = unit.dataset.tokenId;
        if (!tokenId) return;
        document.dispatchEvent(
            new CustomEvent("vtt:token-select", { detail: { tokenId } })
        );
    });

    document.addEventListener("mouseover", (event) => {
        const unit = event.target.closest("[data-status-unit]");
        if (!unit?.dataset.tokenId) return;
        document.dispatchEvent(new CustomEvent("vtt:token-hover", {
            detail: { tokenId: unit.dataset.tokenId },
        }));
    });

    document.addEventListener("mouseout", (event) => {
        if (!event.target.closest("[data-status-unit]")) return;
        if (event.relatedTarget?.closest?.("[data-status-unit]")) return;
        document.dispatchEvent(new CustomEvent("vtt:token-hover", {
            detail: { tokenId: null },
        }));
    });

    document.addEventListener("focusin", (event) => {
        const unit = event.target.closest("[data-status-unit]");
        if (!unit?.dataset.tokenId) return;
        document.dispatchEvent(new CustomEvent("vtt:token-hover", {
            detail: { tokenId: unit.dataset.tokenId },
        }));
    });

    document.addEventListener("focusout", (event) => {
        if (!event.target.closest("[data-status-unit]")) return;
        document.dispatchEvent(new CustomEvent("vtt:token-hover", {
            detail: { tokenId: null },
        }));
    });

    document.addEventListener("vtt:token-selection-changed", (event) => {
        const { roomId, tokenId } = event.detail ?? {};
        markSelected(roomId || "", tokenId || null);
    });

    document.addEventListener("dblclick", (event) => {
        const unit = event.target.closest("[data-status-unit]");
        if (!unit) return;
        const tokenId = unit.dataset.tokenId;
        if (!tokenId) return;
        window.GravewrightMap?.centerOnToken(tokenId);
        event.preventDefault();
    });

    document.addEventListener("keydown", (event) => {
        if (event.key !== "Enter" && event.key !== " ") return;
        const unit = event.target.closest("[data-status-unit]");
        if (!unit) return;
        const tokenId = unit.dataset.tokenId;
        if (!tokenId) return;
        window.GravewrightMap?.centerOnToken(tokenId);
        event.preventDefault();
    });

    window.GravewrightStatusZones = {
        tokensForRoom(roomId) {
            if (!roomId) return [];
            return Array.from(zoneFor(roomId).all.values());
        },
    };

    

    document.addEventListener("vtt:tokens-loaded", (event) => {
        const { sceneId, roomId, tokens } = event.detail ?? {};
        if (!sceneId || !roomId) return;
        const zone = zoneFor(roomId);
        zone.players.clear();
        zone.monsters.clear();
        zone.all.clear();
        for (const tv of tokens) {
            zone.all.set(tv.token_id, tv);
            const side = classify(tv);
            if (side) zone[side].set(tv.token_id, tv);
        }
        renderZones(roomId);
    });

    document.addEventListener("vtt:transport-event", (event) => {
        const { event: evtName, payload } = event.detail ?? {};
        if (!evtName || !payload?.scene_id) return;

        if (evtName === "tokens.snapshot") {
            applySnapshot(payload.scene_id, payload.tokens || []);
        } else if (evtName === "tokens.created") {
            applyAdded(payload.scene_id, payload.tokens || []);
        } else if (evtName === "tokens.moved") {
            applyMoved(payload.scene_id, payload.tokens || []);
        } else if (evtName === "tokens.deleted") {
            applyDeleted(payload.scene_id, payload.token_ids || []);
        } else if (evtName === "tokens.visibility_changed") {
            applyVisibilityChanged(payload.scene_id, payload.tokens || []);
        } else if (evtName === "tokens.conditions.updated") {
            if (payload.token_id) {
                applyConditionsUpdated(payload.scene_id, payload.token_id, payload.conditions || []);
            }
        }
        
        
    });
})();
