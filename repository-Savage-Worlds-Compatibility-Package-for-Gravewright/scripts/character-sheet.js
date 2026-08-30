(function () {
  "use strict";

  const PACKAGE_ID = "savage-worlds";
  const ATTRIBUTE_DEFAULTS = [
    { key: "agility", label: "Agilidade", abbr: "AGI" },
    { key: "smarts", label: "Astúcia", abbr: "AST" },
    { key: "spirit", label: "Espírito", abbr: "ESP" },
    { key: "strength", label: "Força", abbr: "FOR" },
    { key: "vigor", label: "Vigor", abbr: "VIG" },
  ];
  const DICE = [4, 6, 8, 10, 12];
  const attributeEditMode = new WeakMap();
  // The HTML sheets predate package localization and still contain Portuguese
  // fallback copy. Keep those fallbacks readable when i18n is unavailable, but
  // translate every static text node and UI attribute when a locale is active.
  const STATIC_I18N = {
    "Ancestralidade": "savage-worlds.ui.ancestralidade", "Conceito": "savage-worlds.ui.conceito",
    "Estágio": "savage-worlds.ui.patente", "Patente": "savage-worlds.ui.patente",
    "Avanços": "savage-worlds.ui.avancos", "Dado Selvagem": "savage-worlds.ui.wild.die",
    "Principal": "savage-worlds.ui.principal", "Combate": "savage-worlds.ui.combate",
    "Vantagens": "savage-worlds.ui.edges", "Complicações": "savage-worlds.ui.hindrances",
    "Inventário": "savage-worlds.ui.inventario", "Poderes": "savage-worlds.ui.poderes",
    "Sobre": "savage-worlds.ui.sobre", "Recursos": "savage-worlds.ui.recursos",
    "Estado": "savage-worlds.ui.estado",
    "Atalhos": "savage-worlds.ui.atalhos",
    "Ferimentos": "savage-worlds.ui.ferimentos", "Fadiga": "savage-worlds.ui.fadiga",
    "Derivados": "savage-worlds.ui.derivados", "Aparar": "savage-worlds.ui.parry",
    "Resistência": "savage-worlds.ui.toughness", "Movimentação": "savage-worlds.ui.pace",
    "Sobrecarga": "savage-worlds.ui.sobrecarga", "Benes": "savage-worlds.ui.bennies",
    "Atual": "savage-worlds.ui.atual", "Máx.": "savage-worlds.ui.max.abbr",
    "Máxima": "savage-worlds.ui.maxima", "Máximo": "savage-worlds.ui.maximo",
    "Mínima": "savage-worlds.ui.minima", "Condições": "savage-worlds.ui.condicoes",
    "Abalado": "savage-worlds.cond.abalado", "Distraído": "savage-worlds.cond.distraido",
    "Vulnerável": "savage-worlds.cond.vulneravel", "Atordoado": "savage-worlds.cond.atordoado",
    "Enredado": "savage-worlds.cond.enredado", "Imobilizado": "savage-worlds.cond.imobilizado",
    "Preso": "savage-worlds.cond.imobilizado", "Caído": "savage-worlds.cond.caido",
    "Prostrado": "savage-worlds.cond.caido", "Sobrecarregado": "savage-worlds.cond.sobrecarregado",
    "Fatigado": "savage-worlds.cond.fatigado", "Incapacitado": "savage-worlds.cond.incapacitado",
    "Esperando": "savage-worlds.cond.esperando", "Aguardando": "savage-worlds.cond.esperando",
    "Mirando": "savage-worlds.cond.mirando", "Defendendo": "savage-worlds.cond.defendendo",
    "Defesa": "savage-worlds.cond.defendendo", "Atributos": "savage-worlds.ui.atributos",
    "Descontrolado": "savage-worlds.cond.descontrolado", "Destroçado": "savage-worlds.cond.destrocado",
    "Em chamas": "savage-worlds.cond.em.chamas", "Corrida": "savage-worlds.ui.corrida",
    "Agilidade": "savage-worlds.ui.agilidade", "Astúcia": "savage-worlds.ui.astucia",
    "Espírito": "savage-worlds.ui.espirito", "Força": "savage-worlds.ui.forca",
    "Vigor": "savage-worlds.ui.vigor", "Perícias": "savage-worlds.ui.pericias",
    "Perícia": "savage-worlds.ui.pericia", "Atributo": "savage-worlds.ui.atributo",
    "Dado": "savage-worlds.ui.dado", "Mod.": "savage-worlds.ui.modificador.abbr",
    "Armas": "savage-worlds.ui.armas", "Proteção": "savage-worlds.ui.protecao",
    "Carga": "savage-worlds.ui.carga", "Equipamento": "savage-worlds.ui.equipamento",
    "Antecedente Arcano": "savage-worlds.ui.fundo.arcano", "Fundo Arcano": "savage-worlds.ui.fundo.arcano",
    "Pontos": "savage-worlds.ui.pontos", "História": "savage-worlds.ui.historia",
    "Anotações": "savage-worlds.ui.anotacoes", "Armadura": "savage-worlds.ui.armadura",
    "Avarias": "savage-worlds.ui.avarias", "Manobra": "savage-worlds.ui.manobra",
    "Tamanho": "savage-worlds.ui.tamanho", "Tripulação": "savage-worlds.ui.tripulacao",
    "Velocidade máxima": "savage-worlds.ui.velocidade", "Nome": "savage-worlds.ui.nome",
    "Nome do grupo": "savage-worlds.ui.nome.grupo", "Nome do veículo": "savage-worlds.ui.nome.veiculo",
    "Aliados, tropas ou organização": "savage-worlds.ui.grupo.placeholder",
    "Perfil da unidade": "savage-worlds.ui.perfil.unidade", "Estrutura": "savage-worlds.ui.estrutura",
    "Escala": "savage-worlds.ui.escala", "Arraste uma perícia para adicionar": "savage-worlds.ui.empty.pericia",
    "Novato": "savage-worlds.rank.novice", "Experiente": "savage-worlds.rank.seasoned",
    "Veterano": "savage-worlds.rank.veteran", "Heroico": "savage-worlds.rank.heroic",
    "Lendário": "savage-worlds.rank.legendary", "Ficha": "savage-worlds.ui.ficha",
    "Dado de Agilidade": "savage-worlds.ui.dado.de.agilidade",
    "Dado de Astúcia": "savage-worlds.ui.dado.de.astucia",
    "Dado de Espírito": "savage-worlds.ui.dado.de.espirito",
    "Dado de Força": "savage-worlds.ui.dado.de.forca",
    "Dado de Vigor": "savage-worlds.ui.dado.de.vigor",
    "Modificador de Agilidade": "savage-worlds.ui.modificador.de.agilidade",
    "Modificador de Astúcia": "savage-worlds.ui.modificador.de.astucia",
    "Modificador de Espírito": "savage-worlds.ui.modificador.de.espirito",
    "Modificador de Força": "savage-worlds.ui.modificador.de.forca",
    "Modificador de Vigor": "savage-worlds.ui.modificador.de.vigor",
    "Arraste uma arma para a ficha": "savage-worlds.ui.empty.arma",
    "Arraste uma vantagem para a ficha": "savage-worlds.ui.empty.vantagem",
    "Arraste uma complicação para a ficha": "savage-worlds.ui.empty.complicacao",
    "Arraste armadura ou escudo para a ficha": "savage-worlds.ui.empty.protecao",
    "Arraste equipamento para a ficha": "savage-worlds.ui.empty.equipamento",
    "Arraste um poder para a ficha": "savage-worlds.ui.empty.poder",
    "Gerencie o efetivo abstrato do grupo como um único recurso durante a cena.": "savage-worlds.ui.grupo.ajuda",
  };
  // Consumed by the SDK's generic item-list controls for this package:
  // savage-worlds.ui.editar, savage-worlds.ui.confirmar.remocao
  const benniesBySheet = new WeakMap();
  const preparedInitiativeDecks = new Set();
  const initiativeDealsInFlight = new Set();
  const initiativeCardsByCampaign = new Map();
  const confirmedInitiativeStateByCampaign = new Map();
  const observedInitiativeState = new Map();
  let combatTrackerIsGm = false;

  function t(sdk, key, fallback) {
    try { return sdk.i18n.t(key, fallback); }
    catch { return fallback; }
  }

  function localizePackage(root, sdk) {
    (root || document).querySelectorAll?.("[data-package-i18n]").forEach((node) => {
      const key = node.dataset.packageI18n;
      if (key?.startsWith("savage-worlds.")) {
        const translated = t(sdk, key, node.textContent);
        if (translated !== node.textContent) node.textContent = translated;
      }
    });
    (root || document).querySelectorAll?.("[data-package-i18n-template]").forEach((node) => {
      const key = node.dataset.packageI18nTemplate;
      if (!key?.startsWith("savage-worlds.")) return;
      let args = {};
      try { args = JSON.parse(node.dataset.packageI18nArgs || "{}"); } catch { args = {}; }
      let translated = t(sdk, key, node.textContent);
      Object.entries(args).forEach(([name, value]) => {
        translated = translated.replaceAll(`{${name}}`, String(value));
      });
      if (translated !== node.textContent) node.textContent = translated;
    });
  }

  function localizeStatic(root, sdk) {
    if (!root) return;
    const walker = document.createTreeWalker(root, NodeFilter.SHOW_TEXT);
    let node;
    while ((node = walker.nextNode())) {
      const source = node.nodeValue.trim();
      const key = STATIC_I18N[source];
      if (!key) continue;
      const translated = t(sdk, key, source);
      node.nodeValue = node.nodeValue.replace(source, translated);
    }
    root.querySelectorAll("[placeholder], [title], [aria-label], [data-empty-text]").forEach((element) => {
      ["placeholder", "title", "aria-label", "data-empty-text"].forEach((attribute) => {
        const source = element.getAttribute(attribute);
        const key = STATIC_I18N[source];
        if (key) element.setAttribute(attribute, t(sdk, key, source));
      });
    });
  }

  function announceBennies(ctx, sdk) {
    const current = number(ctx.data?.system?.bennies?.value);
    const previous = benniesBySheet.get(ctx.root);
    benniesBySheet.set(ctx.root, current);
    if (previous == null || previous === current) return;
    const gained = current > previous;
    const amount = Math.abs(current - previous);
    const key = gained ? "savage-worlds.toast.bennies.gained" : "savage-worlds.toast.bennies.spent";
    const template = t(sdk, key, gained ? "Bennie gained" : "Bennie spent");
    sdk.ui.toast(template.replace("{count}", String(amount)), {
      variant: gained ? "success" : "warning",
      icon: gained ? "ph-plus-circle" : "ph-minus-circle",
    });
  }

  function wireBenniesControl(ctx, sdk) {
    const control = ctx.root.querySelector(".sw-bennies-control");
    if (!control || control.dataset.swBenniesWired === "1") return;
    control.dataset.swBenniesWired = "1";
    const current = control.querySelector('[data-bind="system.bennies.value"]');
    const maximum = control.querySelector('[data-bind="system.bennies.max"]');
    control.querySelectorAll("[data-sw-benny-step]").forEach((button) => {
      const step = Number(button.dataset.swBennyStep || 0);
      button.title = step < 0
        ? t(sdk, "savage-worlds.ui.bennies.gastar", "Gastar Bene")
        : t(sdk, "savage-worlds.ui.bennies.ganhar", "Ganhar Bene");
      button.setAttribute("aria-label", button.title);
      button.addEventListener("click", () => {
        const value = Math.max(0, number(current?.value));
        const max = Math.max(0, number(maximum?.value));
        const next = step < 0 ? Math.max(0, value - 1) : Math.min(max || value + 1, value + 1);
        if (next !== value) ctx.onChange?.("system.bennies.value", next);
      });
    });
  }

  function paintBennyImage(root, sdk) {
    const src = String(sdk.settings.get("benny_asset_src", "") || "").trim();
    root.querySelectorAll?.(".sw-bennies-coin").forEach((coin) => {
      coin.classList.toggle("has-custom-image", Boolean(src));
      coin.style.backgroundImage = src ? `url(${JSON.stringify(src)})` : "";
    });
  }

  function wireConditionsDialog(ctx, sdk) {
    const dialog = ctx.root.querySelector("[data-sw-conditions-dialog]");
    const trigger = ctx.root.querySelector("[data-sw-open-conditions]");
    const close = dialog?.querySelector("[data-sw-close-conditions]");
    if (!dialog || !trigger || trigger.dataset.swConditionsWired === "1") return;
    trigger.dataset.swConditionsWired = "1";
    trigger.addEventListener("click", () => {
      if (!dialog.open) dialog.showModal();
    });
    close?.addEventListener("click", () => dialog.close());
    dialog.addEventListener("click", (event) => {
      if (event.target === dialog) dialog.close();
    });
    close?.setAttribute("aria-label", t(sdk, "savage-worlds.ui.fechar", "Fechar"));
  }

  function normalizedName(value) {
    return String(value || "")
      .normalize("NFD")
      .replace(/[\u0300-\u036f]/g, "")
      .replace(/[_-]+/g, " ")
      .trim()
      .toLowerCase();
  }

  function normalizedCardName(card) {
    return normalizedName(card?.name);
  }

  function isJokerCard(card) {
    return /joker|coringa/.test(normalizedCardName(card));
  }

  function cardScore(card) {
    const name = normalizedCardName(card);
    // A Joker may also carry numeric metadata. It must always outrank the Ace
    // in the tracker's default order, even though its owner may act at any time.
    if (isJokerCard(card)) return 200;
    const metadata = card?.metadata || {};
    const explicit = Number(metadata.initiative ?? metadata.rank);
    if (Number.isFinite(explicit)) return explicit * 10 + Number(metadata.suitRank || 0);
    const rank = /\b(a|ace|as)\b/.test(name) ? 14
      : /\b(k|king|rei)\b/.test(name) ? 13
      : /\b(q|queen|dama|rainha)\b/.test(name) ? 12
      : /\b(j|jack|valete)\b/.test(name) ? 11
      : Number(name.match(/\b(10|0?[2-9])\b/)?.[1] || 0);
    const suit = /spade|espada/.test(name) ? 4
      : /heart|copa/.test(name) ? 3
      : /diamond|ouro/.test(name) ? 2
      : /club|paus?/.test(name) ? 1 : 0;
    return rank * 10 + suit;
  }

  function jokerRoundEffect(combatant, round) {
    return {
      id: `savage-joker-${combatant.id}`,
      name: "Curinga",
      enabled: true,
      duration: { type: "rounds", remaining: 1 },
      data: {
        source: "savage-worlds.initiative.joker",
        combatId: String(combatant.combat_id || ""),
        round: Number(round || 1),
        modifiers: [
          { id: "joker-trait", target: "roll.check", operation: "add", value: 2, label: "Curinga" },
          { id: "joker-damage", target: "roll.damage", operation: "add", value: 2, label: "Curinga" },
        ],
      },
    };
  }

  async function applyJokerRoundEffects(dealt, state, sdk, knownActors = []) {
    const jokerActorIds = new Set(
      dealt.filter((entry) => isJokerCard(entry.card)).map((entry) => String(entry.actor_id || "")).filter(Boolean)
    );
    const actorIds = Array.from(new Set(dealt.map((entry) => String(entry.actor_id || "")).filter(Boolean)));
    const known = new Map(knownActors.filter(Boolean).map((actor) => [String(actor.id), actor]));
    const actors = await Promise.all(actorIds.map((actorId) => known.get(actorId) || sdk.actors.get(actorId)));
    const relevant = new Map(actors.filter(Boolean).map((actor) => [String(actor.id), actor]));
    const members = await sdk.campaign.members();
    const playerIds = new Set(
      members.filter((member) => member.role === "player").map((member) => String(member.userId))
    );
    const playerCharacters = actors.filter((actor) => actor && actor.owner_user_ids?.some((ownerId) => playerIds.has(String(ownerId))));
    const anyJoker = jokerActorIds.size > 0;

    await Promise.all(Array.from(relevant.values()).map(async (actor) => {
      const snapshot = await sdk.actors.data(actor.id);
      const data = snapshot?.data || {};
      const effects = Array.isArray(data.effects) ? data.effects : [];
      const nextEffects = effects.filter((effect) => effect?.data?.source !== "savage-worlds.initiative.joker");
      const combatant = dealt.find((entry) => String(entry.actor_id || "") === String(actor.id));
      if (jokerActorIds.has(String(actor.id)) && combatant) {
        nextEffects.push(jokerRoundEffect(combatant, state?.round));
      }
      await sdk.actors.patchData(actor.id, { effects: nextEffects });
    }));
    if (anyJoker) {
      await Promise.all(playerCharacters.map(async (actor) => {
        const snapshot = await sdk.actors.data(actor.id);
        const current = Math.max(0, number(snapshot?.data?.bennies?.value));
        await sdk.actors.patchData(actor.id, { "bennies.value": current + 1 });
      }));
    }
  }

  function initiativeGroups(combatants, actors) {
    const actorTypes = new Map(actors.filter(Boolean).map((actor) => [String(actor.id), actor.type]));
    const groups = [];
    const extrasByActor = new Map();
    combatants.forEach((combatant) => {
      const actorId = String(combatant.actor_id || "");
      if (actorId && actorTypes.get(actorId) === "extra") {
        let group = extrasByActor.get(actorId);
        if (!group) {
          group = [];
          extrasByActor.set(actorId, group);
          groups.push(group);
        }
        group.push(combatant);
      } else {
        groups.push([combatant]);
      }
    });
    return groups;
  }

  async function dealInitiative(state, sdk) {
    const campaignId = state?.campaign_id || document.querySelector("[data-combat-panel]")?.dataset.roomId || "";
    const combatants = Array.isArray(state?.combatants) ? state.combatants : [];
    if (!campaignId || !combatants.length) return;
    const actorIds = Array.from(new Set(combatants.map((entry) => String(entry.actor_id || "")).filter(Boolean)));
    const actors = await Promise.all(actorIds.map((actorId) => sdk.actors.get(actorId)));
    const groups = initiativeGroups(combatants, actors);
    const cardsState = await sdk.cards.state();
    const selectedDeckId = String(sdk.settings.get("initiative_deck_id", "") || "");
    let deck = (cardsState.decks || []).find((entry) => entry.id === selectedDeckId)
      || (cardsState.decks || []).find((entry) => Number(entry.draw_count) >= groups.length)
      || (cardsState.decks || [])[0];
    if (!deck) throw new Error(t(sdk, "savage-worlds.initiative.no.deck", "No deck available"));
    const deckSize = (cardsState.cards || []).filter((card) => card?.deck_instance_id === deck.id).length;
    const previousTurnHadJoker = (cardsState.cards || []).some((card) =>
      card?.deck_instance_id === deck.id && isJokerCard(card)
      && card.face_state === "face_up" && card.visibility === "room"
    );
    if (previousTurnHadJoker || Number(deck.draw_count) < groups.length) {
      await sdk.cards.reset(deck.id, { shuffle: true });
      preparedInitiativeDecks.add(deck.id);
    } else if (!preparedInitiativeDecks.has(deck.id) && deckSize > 0 && Number(deck.draw_count) === deckSize) {
      // A newly instantiated deck is definition-ordered, so it needs its initial
      // pre-combat shuffle. This is distinct from reshuffling between rounds.
      await sdk.cards.shuffle(deck.id);
      preparedInitiativeDecks.add(deck.id);
    }

    const dealt = [];
    for (const group of groups) {
      const draw = await sdk.cards.draw(deck.id, {
        count: 1,
        destination: "chat", reveal: true,
      });
      const card = draw.cards?.[0];
      if (!card) continue;
      group.forEach((combatant) => dealt.push({ ...combatant, card, score: cardScore(card) }));
    }

    dealt.sort((a, b) => b.score - a.score);
    if (dealt.length !== combatants.length) throw new Error("Incomplete initiative deal");
    initiativeCardsByCampaign.set(campaignId, new Map(
      dealt.map((entry) => [String(entry.id), entry.card])
    ));
    const confirmedState = await sdk.combat.setInitiativeOrder(dealt.map((entry) => ({
      combatantId: entry.id,
      value: entry.card.name || "?",
    })));
    await applyJokerRoundEffects(dealt, confirmedState || state, sdk, actors);
    confirmedInitiativeStateByCampaign.set(campaignId, confirmedState);
    sdk.ui.toast(t(sdk, "savage-worlds.initiative.dealt", "Action cards dealt."), { variant: "success", icon: "ph-cards" });
  }

  function initiativeStateSnapshot(state) {
    return {
      active: Boolean(state?.active),
      round: Number(state?.round || 0),
      combatants: (Array.isArray(state?.combatants) ? state.combatants : [])
        .map((combatant) => String(combatant.id)).sort().join("|"),
    };
  }

  function shouldDealForObservedState(previous, state) {
    const combatants = Array.isArray(state?.combatants) ? state.combatants : [];
    if (!state?.active || !combatants.length) return false;
    if (!previous) return combatants.every((combatant) => !String(combatant.initiative || "").trim());
    const current = initiativeStateSnapshot(state);
    return (!previous.active && current.active) || current.round !== previous.round;
  }

  async function observeInitiativeState(sdk) {
    if (!combatTrackerIsGm) return;
    const state = await sdk.combat.current();
    const campaignId = String(state?.campaign_id || document.querySelector("[data-combat-panel]")?.dataset.roomId || "");
    if (!campaignId) return;
    const previous = observedInitiativeState.get(campaignId);
    const shouldDeal = shouldDealForObservedState(previous, state);
    observedInitiativeState.set(campaignId, initiativeStateSnapshot(state));
    const combatants = Array.isArray(state.combatants) ? state.combatants : [];
    if (!shouldDeal || !combatants.length || initiativeDealsInFlight.has(campaignId)) return;

    initiativeDealsInFlight.add(campaignId);
    await dealInitiative(state, sdk).catch((error) => {
      sdk.ui.toast(String(error?.message || error), { variant: "danger" });
    }).finally(() => initiativeDealsInFlight.delete(campaignId));
  }

  function initiativeButton({ state, isGm }, sdk) {
    if (!isGm || !state?.active) return [];
    const control = element("div", "sw-initiative-controls");
    const select = element("select", "sw-initiative-deck");
    select.title = t(sdk, "savage-worlds.settings.initiative.deck.label", "Initiative deck");
    select.setAttribute("aria-label", select.title);
    const loading = element("option", "", t(sdk, "savage-worlds.initiative.deck.loading", "Loading decks…"));
    loading.value = "";
    select.append(loading);
    select.disabled = true;

    const button = element("button", "gw-combat-icon sw-initiative-deal");
    const label = t(sdk, "savage-worlds.initiative.deal", "Deal action cards");
    button.type = "button";
    button.title = label;
    button.setAttribute("aria-label", label);
    button.innerHTML = '<i class="ph ph-cards" aria-hidden="true"></i>';
    button.addEventListener("click", async () => {
      button.disabled = true;
      try { await dealInitiative(state, sdk); }
      catch (error) { sdk.ui.toast(String(error?.message || error), { variant: "danger" }); }
      finally { button.disabled = false; }
    });
    select.addEventListener("change", async () => {
      select.disabled = true;
      try {
        await sdk.settings.set("initiative_deck_id", select.value);
      } catch (error) {
        sdk.ui.toast(String(error?.message || error), { variant: "danger" });
      } finally {
        select.disabled = false;
      }
    });
    void sdk.cards.state().then((cardsState) => {
      const decks = Array.isArray(cardsState?.decks) ? cardsState.decks : [];
      const selected = String(sdk.settings.get("initiative_deck_id", "") || "");
      select.replaceChildren();
      if (!decks.length) {
        const empty = element("option", "", t(sdk, "savage-worlds.initiative.no.deck", "No deck available"));
        empty.value = "";
        select.append(empty);
        button.disabled = true;
        return;
      }
      decks.forEach((deck) => {
        const option = element("option", "", `${deck.name || deck.id} (${Number(deck.draw_count) || 0})`);
        option.value = deck.id;
        select.append(option);
      });
      select.value = decks.some((deck) => deck.id === selected) ? selected : decks[0].id;
      select.disabled = false;
    }).catch((error) => {
      loading.textContent = t(sdk, "savage-worlds.initiative.no.deck", "No deck available");
      button.disabled = true;
      console.warn("[savage-worlds] initiative decks unavailable", error);
    });
    control.append(select, button);
    return [control];
  }

  function savageTurnActions({ combatant, state, isGm }, sdk) {
    if (!isGm || !state?.active) return [];
    const joker = isJokerCard({ name: combatant?.initiative });
    const resume = Boolean(state.interrupted && combatant?.is_current);
    const canHold = !state.interrupted && combatant?.is_current && !combatant?.has_acted;
    const canActNow = !state.interrupted && !combatant?.is_current && !combatant?.has_acted
      && (combatant?.holding || joker);
    if (!resume && !canHold && !canActNow) return [];
    const label = resume ? t(sdk, "savage-worlds.initiative.resume", "Retomar turno interrompido")
      : canHold ? t(sdk, "savage-worlds.initiative.hold", "Aguardar")
      : t(sdk, "savage-worlds.initiative.act.now", "Agir agora");
    const button = element("button", "gw-combat-icon sw-joker-turn-action");
    button.type = "button";
    button.title = label;
    button.setAttribute("aria-label", label);
    button.innerHTML = `<i class="ph ${resume ? "ph-arrow-u-up-left" : canHold ? "ph-hand-palm" : "ph-lightning"}" aria-hidden="true"></i>`;
    button.addEventListener("click", async () => {
      button.disabled = true;
      try {
        if (resume) await sdk.combat.resumeTurn();
        else if (canHold) {
          await sdk.combat.setHolding(combatant.id, true);
          await sdk.combat.advance(1);
        } else await sdk.combat.interruptTurn(combatant.id);
      } catch (error) {
        sdk.ui.toast(String(error?.message || error), { variant: "danger" });
      } finally {
        button.disabled = false;
      }
    });
    return [button];
  }

  async function paintInitiativeCards({ panel, state }, sdk) {
    const campaignId = state?.campaign_id || panel?.dataset.roomId || "";
    const combatants = Array.isArray(state?.combatants) ? state.combatants : [];
    if (!campaignId || !combatants.length || !panel?.isConnected) return;
    const assigned = initiativeCardsByCampaign.get(campaignId) || new Map();
    let available = [];
    // A distribuição já devolve a carta pública, inclusive a URL da imagem.
    // Renderize esse resultado imediatamente; consultar o estado outra vez aqui
    // criava uma corrida em que a primeira pintura abortava e só o repaint
    // seguinte mostrava as cartas.
    if (!assigned.size) {
      let cardsState;
      try { cardsState = await sdk.cards.state(); }
      catch { return; }
      if (!panel.isConnected) return;
      available = (cardsState.cards || []).filter((card) => card?.front_asset_id && card?.name);
    }
    const used = new Set();
    combatants.forEach((combatant) => {
      const initiative = String(combatant?.initiative || "").trim();
      if (!initiative) return;
      let card = assigned.get(String(combatant.id)) || null;
      const index = card ? -1 : available.findIndex((candidateCard, candidate) =>
        !used.has(candidate) && String(candidateCard.name).trim() === initiative
      );
      if (!card && index < 0) return;
      if (!card) {
        card = available[index];
        used.add(index);
      }
      const row = panel.querySelector(`[data-combatant-id="${CSS.escape(String(combatant.id))}"]`);
      const original = row?.querySelector("[data-combat-initiative], .gw-combat-combatant__score");
      if (!row || !original || row.querySelector(".sw-action-card-initiative")) return;

      const figure = element("button", "sw-action-card-initiative");
      figure.type = "button";
      figure.title = initiative;
      figure.setAttribute("aria-label", `${initiative} — ${combatant.name || ""}`);
      const image = document.createElement("img");
      image.src = card.front_asset_url || "";
      image.alt = initiative;
      image.draggable = false;
      image.addEventListener("error", () => {
        figure.classList.add("is-image-missing");
        figure.textContent = initiative;
      }, { once: true });
      figure.appendChild(image);
      original.classList.add("sw-action-card-initiative__editor");
      figure.addEventListener("click", () => {
        if (!original.matches("input")) return;
        row.classList.toggle("is-editing-action-card");
        if (row.classList.contains("is-editing-action-card")) original.focus();
      });
      original.insertAdjacentElement("beforebegin", figure);
    });
  }

  function restoreConfirmedInitiativeOrder({ panel, state }) {
    const campaignId = state?.campaign_id || panel?.dataset.roomId || "";
    const confirmed = confirmedInitiativeStateByCampaign.get(campaignId);
    if (!confirmed || Number(confirmed.round) !== Number(state?.round)) return false;
    const renderedIds = (state?.combatants || []).map((entry) => String(entry.id));
    const confirmedIds = (confirmed.combatants || []).map((entry) => String(entry.id));
    if (renderedIds.length !== confirmedIds.length) return false;
    if ([...renderedIds].sort().join("|") !== [...confirmedIds].sort().join("|")) return false;
    if (renderedIds.join("|") === confirmedIds.join("|")) return false;

    // An add/remove response can repaint after the atomic initiative response.
    // Replay only the newer confirmed state; advancing within the same order is
    // deliberately left alone so its current-turn marker remains authoritative.
    document.dispatchEvent(new CustomEvent("vtt:combat-sdk-state", { detail: confirmed }));
    return true;
  }

  function element(tag, className, text) {
    const node = document.createElement(tag);
    if (className) node.className = className;
    if (text != null) node.textContent = text;
    return node;
  }

  function select(options, value) {
    const node = element("select");
    options.forEach(([key, label]) => {
      const option = element("option", "", label);
      option.value = key;
      option.selected = String(key) === String(value);
      node.appendChild(option);
    });
    return node;
  }

  function number(value) {
    const n = Number(value);
    return Number.isFinite(n) ? n : 0;
  }

  // Ferimentos e Fadiga são trilhas curtas e fechadas: 3 e 2. Digitar um número
  // num campo é a forma mais lenta de andar numa escala que cabe em três cliques
  // — e o limite vem da ficha, não de um "/ 3" escrito à mão no template.
  function renderPips(ctx, kind) {
    const host = ctx.root.querySelector(`[data-sw-pips="${kind}"]`);
    if (!host) return;
    const track = ctx.data?.system?.[kind] || {};
    const value = number(track.value);
    const max = Math.max(1, number(track.max) || 1);
    host.replaceChildren();

    const limit = kind === "fatigue" ? max + 1 : max;
    for (let index = 1; index <= limit; index += 1) {
      const pip = element("button", "sw-pip");
      if (kind === "fatigue" && index > max) pip.classList.add("sw-pip--incapacitated");
      pip.type = "button";
      pip.dataset.swPip = String(index);
      if (index <= value) pip.classList.add("is-on");
      pip.setAttribute("aria-pressed", index <= value ? "true" : "false");
      pip.setAttribute("aria-label", `${index}`);
      // Clicar no último marcado desmarca: subir e descer pela mesma trilha,
      // sem um segundo controle só para voltar.
      pip.addEventListener("click", () => {
        const next = value === index ? index - 1 : index;
        ctx.onChange?.(`system.${kind}.value`, next);
        if (kind === "fatigue") {
          ctx.onChange?.("system.conditions.fatigued", next > 0);
          if (next > max) ctx.onChange?.("system.conditions.incapacitated", true);
          else if (value > max && number(ctx.data?.system?.wounds?.value) <= number(ctx.data?.system?.wounds?.max)) {
            ctx.onChange?.("system.conditions.incapacitated", false);
          }
        }
      });
      host.appendChild(pip);
    }

    // Incapacitado é o passo além da trilha, e ele existe: mostrar o excedente
    // é melhor do que fingir que a trilha parou.
    if (value > max) host.appendChild(element("span", "sw-pip-over", `+${value - max}`));
    host.dataset.swFull = value >= max ? "1" : "";
  }

  function renderFatigueRecovery(ctx, sdk) {
    const fatigueHost = ctx.root.querySelector('[data-sw-pips="fatigue"]');
    const fieldset = fatigueHost?.closest("fieldset");
    if (!fieldset) return;
    fieldset.querySelector("[data-sw-recover-fatigue]")?.remove();
    const button = element("button", "sw-fatigue-recovery");
    button.type = "button";
    button.dataset.swRecoverFatigue = "1";
    button.title = t(sdk, "savage-worlds.ui.recuperar.fadiga", "Recuperar um nível de Fadiga");
    button.setAttribute("aria-label", button.title);
    button.disabled = number(ctx.data?.system?.fatigue?.value) < 1;
    button.append(element("i", "ph ph-bed", ""));
    button.addEventListener("click", (event) => {
      event.preventDefault(); event.stopPropagation();
      ctx.onAction?.("state.recover-fatigue", { event, element: button, label: button.title });
    });
    const actions = fieldset.querySelector(".sw-track-actions");
    if (actions) actions.append(button);
    else fieldset.append(button);
  }

  function invokeItemShortcut(ctx, sdk, item, actionId, button) {
    if (!item?.id || typeof ctx.onItemAction !== "function") {
      sdk.ui.toast(t(sdk, "savage-worlds.ui.atalho.indisponivel", "Atalho indisponível."), { variant: "danger" });
      return;
    }
    try {
      const result = ctx.onItemAction(item.id, actionId, {
        element: button,
        label: button.textContent,
      });
      Promise.resolve(result).catch((error) => sdk.ui.toast(String(error?.message || error), { variant: "danger" }));
    } catch (error) {
      sdk.ui.toast(String(error?.message || error), { variant: "danger" });
    }
  }

  function shortcutButton(ctx, sdk, item, actionId, label) {
    const button = element("button", "", label);
    button.type = "button";
    button.addEventListener("click", (event) => {
      event.preventDefault();
      event.stopPropagation();
      invokeItemShortcut(ctx, sdk, item, actionId, button);
    });
    return button;
  }

  function renderWeaponShortcuts(ctx, sdk) {
    let host = ctx.root.querySelector("[data-sw-weapon-shortcuts]");
    if (!host) {
      const attributes = ctx.root.querySelector(".sw-traits")?.closest(".sw-card");
      if (!attributes) return;
      const column = element("div", "sw-summary-column");
      attributes.before(column);
      column.appendChild(attributes);
      const card = element("section", "sw-card sw-shortcuts");
      const heading = element("h2", "", t(sdk, "savage-worlds.ui.atalhos", "Atalhos"));
      host = element("div");
      host.dataset.swWeaponShortcuts = "1";
      card.append(heading, host);
      column.appendChild(card);
    }
    const weapons = (Array.isArray(ctx.data?.system?.weapons) ? ctx.data.system.weapons : [])
      .filter((weapon) => weapon?.data?.equipped === true)
      .map((item) => ({ item, kind: "weapon" }));
    const powers = (Array.isArray(ctx.data?.system?.powers) ? ctx.data.system.powers : [])
      .filter((power) => power?.data?.equipped === true)
      .map((item) => ({ item, kind: "power" }));
    const shortcuts = [...weapons, ...powers];
    host.replaceChildren();
    if (!shortcuts.length) {
      const empty = element(
        "p",
        "sw-shortcuts-empty",
        t(sdk, "savage-worlds.ui.atalhos.vazio", "Equipe uma arma ou prepare um poder para criar um atalho."),
      );
      host.appendChild(empty);
      return;
    }
    shortcuts.forEach(({ item, kind }) => {
      const row = element("div", "sw-shortcut-row");
      const identity = element("div", "sw-shortcut-identity");
      identity.appendChild(element("strong", "", item.name || t(sdk, kind === "power" ? "savage-worlds.ui.poder" : "savage-worlds.ui.arma", kind === "power" ? "Poder" : "Arma")));
      const tracksAmmo = Number(item.data?.ammo?.max || 0) > 0;
      const ammoFact = tracksAmmo
        ? `${t(sdk, "savage-worlds.ui.municao.atual", "Munição")}: ${Number(item.data?.ammo?.value || 0)}/${Number(item.data?.ammo?.max || 0)}`
        : "";
      const powerCostFact = kind === "power"
        ? `${Number(item.data?.powerPoints || 0)} PP`
        : "";
      const facts = [item.data?.damage, item.data?.range, powerCostFact, ammoFact].filter(Boolean).join(" · ");
      if (facts) identity.appendChild(element("small", "", facts));

      const actions = element("div", "sw-shortcut-actions");
      if (kind === "power") {
        actions.append(shortcutButton(
          ctx, sdk, item,
          ctx.sheetType === "extra" ? "roll.power.extra" : "roll.power",
          t(sdk, "savage-worlds.ui.conjurar", "Conjurar"),
        ));
      } else {
        actions.append(shortcutButton(
          ctx, sdk, item,
          ctx.sheetType === "extra" ? "roll.attack.extra" : "roll.attack",
          t(sdk, "savage-worlds.ui.atacar", "Atacar"),
        ));
        if (tracksAmmo) actions.append(shortcutButton(
          ctx, sdk, item, "item.reload",
          t(sdk, "savage-worlds.ui.recarregar", "Recarregar"),
        ));
      }
      if (item.data?.damage) actions.append(shortcutButton(ctx, sdk, item, "roll.damage", t(sdk, "savage-worlds.ui.dano", "Dano")));
      row.append(identity, actions);
      host.appendChild(row);
    });
  }

  // Um derivado que muda por causa de uma condição não pode mudar em silêncio:
  // sem a legenda, o Aparar 10 parece erro de conta.
  function renderDerivedNotes(ctx) {
    const conditions = ctx.data?.system?.conditions || {};
    const protection = equippedProtection(ctx);
    const notes = {
      parry: [
        protection.parry ? `+${protection.parry} escudo` : "",
        protection.cover ? `−${protection.cover} cobertura à distância` : "",
        conditions.defending ? "+4 defendendo" : "",
        conditions.prone ? "−2 caído" : "",
      ],
      // A proteção equipada já está dentro do número; dizer de onde vieram os
      // pontos evita que a Resistência 8 pareça erro de conta.
      toughness: [protection.armor ? `+${protection.armor} armadura (torso)` : ""],
      pace: [conditions.encumbered ? "−2 sobrecarregado" : "", conditions.prone ? "caído" : ""],
      load: [number(ctx.data?.system?.stats?.load?.encumbrance) ? "−1 por nível" : ""],
    };
    Object.entries(notes).forEach(([stat, lines]) => {
      const node = ctx.root.querySelector(`[data-sw-why="${stat}"]`);
      if (node) node.textContent = lines.filter(Boolean).join(" · ");
    });
    ctx.root.querySelectorAll(".sw-derived > div").forEach((box) => {
      const label = box.querySelector("small")?.textContent?.trim() || "Derivado";
      const value = box.querySelector("b")?.textContent?.trim() || "—";
      const detail = box.querySelector("em")?.textContent?.trim();
      const description = `${label}: ${value}${detail ? ` · ${detail}` : ""}`;
      box.title = description;
      box.setAttribute("aria-label", description);
      if (!box.hasAttribute("tabindex")) box.tabIndex = 0;
    });
  }

  function renderEscapeAction(ctx) {
    const bound = ctx.root.querySelector('[data-bind="system.conditions.bound"]');
    const entangled = ctx.root.querySelector('[data-bind="system.conditions.entangled"]');
    const fieldset = bound?.closest("fieldset") || entangled?.closest("fieldset");
    if (!fieldset) return;
    fieldset.querySelector("[data-sw-escape-action]")?.remove();
    const skills = Array.isArray(ctx.data?.system?.skills) ? ctx.data.system.skills : [];
    const athletics = skills.find((item) => String(item?.data?.key || "") === "athletics")
      || skills.find((item) => normalizedName(item?.name) === "atletismo");
    const button = element("button", "sw-condition-action", athletics ? "Libertar-se (Atletismo −2)" : "Libertar-se (Força −2)");
    button.type = "button";
    button.dataset.swEscapeAction = "1";
    fieldset.appendChild(button);
    const isExtra = ctx.sheetType === "extra";
    if (athletics) {
      button.addEventListener("click", () => ctx.onItemAction?.(
        athletics.id,
        isExtra ? "roll.escape.skill.extra" : "roll.escape.skill",
        { element: button, label: athletics.name || "Atletismo" },
      ));
    } else {
      button.dataset.action = isExtra ? "roll.escape.extra" : "roll.escape";
    }
    button.hidden = !(bound?.checked || entangled?.checked);
  }

  function isFighting(item) {
    if (String(item?.data?.key || "") === activeParrySkillKey) return true;
    const name = normalizedName(item?.name);
    return name === normalizedName(activeParrySkillLabel);
  }

  function isHealing(item) {
    const key = String(item?.data?.key || "");
    const name = normalizedName(item?.name);
    return key === "healing" || name === "curar" || name === "healing";
  }

  let activeParrySkillKey = "fighting";
  let activeParrySkillLabel = "Lutar";

  function configuredSkills(sdk) {
    try {
      const parsed = JSON.parse(String(sdk.settings.get("core_skills_json", "[]") || "[]"));
      return Array.isArray(parsed)
        ? parsed.map((skill) => ({ ...skill, isCore: skill.isCore ?? skill.key !== "fighting" }))
        : [];
    } catch (_error) {
      return [];
    }
  }

  function configuredAttributes(sdk) {
    let parsed = [];
    try {
      parsed = JSON.parse(String(sdk.settings.get("attributes_json", "[]") || "[]"));
    } catch (_error) {
      parsed = [];
    }
    return ATTRIBUTE_DEFAULTS.map((fallback) => {
      const configured = Array.isArray(parsed) ? parsed.find((entry) => entry?.key === fallback.key) : null;
      const abbr = String(configured?.abbr || fallback.abbr).trim().slice(0, 3).toUpperCase();
      return {
        key: fallback.key,
        label: String(configured?.label || fallback.label).trim() || fallback.label,
        abbr: abbr || fallback.abbr,
      };
    });
  }

  function attributeDieImage(sides) {
    const points = {
      4: "24,4 44,42 4,42",
      6: "6,6 42,6 42,42 6,42",
      8: "24,3 44,24 24,45 4,24",
      10: "24,3 44,18 36,44 12,44 4,18",
      12: "14,4 34,4 45,17 40,39 24,46 8,39 3,17",
    };
    const svg = document.createElementNS("http://www.w3.org/2000/svg", "svg");
    svg.classList.add("sw-attribute-die");
    svg.setAttribute("viewBox", "0 0 48 48");
    svg.setAttribute("aria-hidden", "true");
    const polygon = document.createElementNS(svg.namespaceURI, "polygon");
    polygon.setAttribute("points", points[sides] || points[6]);
    svg.append(polygon);
    return svg;
  }

  function invokeAttributeRoll(ctx, sdk, definition, button, event) {
    event.preventDefault();
    event.stopPropagation();
    const actionId = `roll.trait.${definition.key}${ctx.sheetType === "extra" ? ".extra" : ""}`;
    if (typeof ctx.onAction !== "function") {
      sdk.ui.toast(t(sdk, "savage-worlds.ui.rolagem.indisponivel", "Rolagem indisponível."), { variant: "danger" });
      return;
    }
    try {
      const result = ctx.onAction(actionId, { event, element: button, label: definition.label });
      Promise.resolve(result).catch((error) => sdk.ui.toast(String(error?.message || error), { variant: "danger" }));
    } catch (error) {
      sdk.ui.toast(String(error?.message || error), { variant: "danger" });
    }
  }

  function renderAttributes(ctx, sdk) {
    const host = ctx.root.querySelector("[data-sw-attribute-cards]");
    const toggle = ctx.root.querySelector("[data-sw-edit-attributes]");
    if (!host || !toggle) return;
    const definitions = configuredAttributes(sdk);
    const editing = attributeEditMode.get(ctx.root) === true;
    toggle.textContent = editing ? t(sdk, "savage-worlds.ui.concluir", "Concluir") : t(sdk, "savage-worlds.ui.editar", "Editar");
    toggle.setAttribute("aria-pressed", String(editing));
    toggle.onclick = () => {
      attributeEditMode.set(ctx.root, !editing);
      renderAttributes(ctx, sdk);
    };
    host.replaceChildren();
    const attributes = ctx.data?.system?.attributes || {};
    const body = element("div", editing ? "sw-traits sw-attributes-editor" : "sw-attributes-grid");
    definitions.forEach((definition) => {
      const value = attributes[definition.key] || {};
      const sides = Number(value.sides || 4);
      const modifier = Number(value.modifier || 0);
      if (!editing) {
        const card = element("button", "sw-attribute-card");
        card.type = "button";
        card.title = `${definition.label}: d${sides}${modifier ? ` ${modifier > 0 ? "+" : ""}${modifier}` : ""}`;
        card.setAttribute("aria-label", card.title);
        card.append(
          element("strong", "sw-attribute-abbr", definition.abbr),
          attributeDieImage(sides),
          element("span", "sw-attribute-value", `d${sides}${modifier ? ` ${modifier > 0 ? "+" : ""}${modifier}` : ""}`),
        );
        card.addEventListener("click", (event) => invokeAttributeRoll(ctx, sdk, definition, card, event));
        body.append(card);
        return;
      }
      const row = element("div", "sw-trait");
      const name = element("button", "", definition.label);
      name.type = "button";
      name.addEventListener("click", (event) => invokeAttributeRoll(ctx, sdk, definition, name, event));
      const die = select(DICE.map((entry) => [entry, `d${entry}`]), sides);
      die.setAttribute("aria-label", `Dado de ${definition.label}`);
      die.addEventListener("change", () => ctx.onChange?.(`system.attributes.${definition.key}.sides`, Number(die.value)));
      const modifierInput = element("input");
      modifierInput.type = "number";
      modifierInput.value = modifier;
      modifierInput.setAttribute("aria-label", `Modificador de ${definition.label}`);
      modifierInput.addEventListener("change", () => ctx.onChange?.(`system.attributes.${definition.key}.modifier`, Number(modifierInput.value) || 0));
      row.append(name, element("small", "", definition.abbr), die, modifierInput);
      body.append(row);
    });
    if (editing && ctx.sheetType === "character") {
      const wildSides = Number(ctx.data?.system?.wildDie?.sides || 6);
      const row = element("div", "sw-trait sw-wild-die-editor");
      const label = element("span", "sw-wild-die-label", t(sdk, "savage-worlds.ui.wild.die", "Dado Selvagem"));
      const die = select(DICE.map((entry) => [entry, `d${entry}`]), wildSides);
      die.setAttribute("aria-label", t(sdk, "savage-worlds.ui.wild.die", "Dado Selvagem"));
      die.addEventListener("change", () => ctx.onChange?.("system.wildDie.sides", Number(die.value)));
      row.append(label, element("small", "", "DS"), die, element("span"));
      body.append(row);
    }
    host.append(body);
  }

  function syncConfiguredParrySkill(sdk) {
    const key = String(sdk.settings.get("parry_skill_key", "fighting") || "fighting");
    activeParrySkillKey = key;
    activeParrySkillLabel = configuredSkills(sdk).find((skill) => skill.key === key)?.label || key;
  }

  function syncCoreSkills(ctx, sdk) {
    const skills = Array.isArray(ctx.data?.system?.skills) ? ctx.data.system.skills : [];
    const conventions = configuredSkills(sdk);
    let changed = false;
    conventions.filter((skill) => skill.isCore).forEach((skill) => {
      const existing = skills.find((item) => String(item?.data?.key || "") === skill.key)
        || skills.find((item) => normalizedName(item?.name) === normalizedName(skill.label));
      if (existing) {
        if (!existing.data?.key) {
          existing.data = existing.data || {};
          existing.data.key = skill.key;
          changed = true;
        }
        return;
      }
      skills.push({
        id: `core-skill-${skill.key}`,
        type: "skill",
        name: skill.label,
        data: {
          key: skill.key,
          attribute: skill.attribute,
          die: { sides: 4, modifier: 0 },
          isCore: true,
        },
      });
      changed = true;
    });
    if (changed) ctx.onChange?.("system.skills", skills);
  }

  function renderSkills(ctx, sdk) {
    syncConfiguredParrySkill(sdk);
    const host = ctx.root.querySelector("[data-sw-skill-rows]");
    if (!host) return;
    const skills = Array.isArray(ctx.data?.system?.skills) ? ctx.data.system.skills : [];
    const conventions = configuredSkills(sdk);
    skills.forEach((item) => {
      if (item?.data?.key) return;
      const match = conventions.find((skill) => normalizedName(skill.label) === normalizedName(item?.name));
      if (match) {
        item.data.key = match.key;
        ctx.onItemChange?.(item.id, "data.key", match.key);
      }
    });
    const fighting = skills.find(isFighting);
    const fightingSides = fighting ? Number(fighting.data?.die?.sides || 4) : 0;
    const parry = ctx.data?.system?.stats?.parry;
    if (parry && Number(parry.fightingSides) !== fightingSides) {
      parry.fightingSides = fightingSides;
      ctx.onChange?.("system.stats.parry.fightingSides", fightingSides);
    }
    host.replaceChildren();

    skills.forEach((item) => {
      const data = item?.data || {};
      const row = element("div", "sw-skill-row");

      const skillFallback = t(sdk, "savage-worlds.ui.pericia", "Perícia");
      const name = element("button", "sw-skill-roll", item?.name || skillFallback);
      name.type = "button";
      name.addEventListener("click", (event) => {
        event.preventDefault();
        event.stopPropagation();
        const actionId = isHealing(item)
          ? (ctx.sheetType === "extra" ? "roll.healing.extra" : "roll.healing")
          : (ctx.sheetType === "extra" ? "roll.skill.extra" : "roll.skill");
        ctx.onItemAction?.(item.id, actionId, { element: name, label: item?.name || skillFallback });
      });

      const attribute = select(configuredAttributes(sdk).map((entry) => [entry.key, entry.abbr]), data.attribute || "agility");
      attribute.setAttribute("aria-label", t(sdk, "savage-worlds.ui.atributo", "Atributo"));
      attribute.addEventListener("change", () => ctx.onItemChange?.(item.id, "data.attribute", attribute.value));

      const die = select(DICE.map((sides) => [sides, `d${sides}`]), data.die?.sides || 4);
      die.setAttribute("aria-label", t(sdk, "savage-worlds.ui.dado", "Dado"));
      die.addEventListener("change", () => {
        const sides = Number(die.value);
        ctx.onItemChange?.(item.id, "data.die.sides", sides);
        if (isFighting(item)) ctx.onChange?.("system.stats.parry.fightingSides", sides);
      });

      const modifier = element("input");
      modifier.type = "number";
      modifier.value = Number(data.die?.modifier || 0);
      modifier.setAttribute("aria-label", t(sdk, "savage-worlds.ui.modificador", "Modificador"));
      modifier.addEventListener("change", () => ctx.onItemChange?.(item.id, "data.die.modifier", Number(modifier.value) || 0));

      const remove = element("button", "sw-skill-remove", "×");
      remove.type = "button";
      remove.title = t(sdk, "savage-worlds.ui.remover", "Remover");
      remove.addEventListener("click", () => {
        ctx.onChange?.("system.skills", skills.filter((skill) => skill !== item));
        if (isFighting(item)) ctx.onChange?.("system.stats.parry.fightingSides", 0);
      });

      const rowActions = element("div", "sw-skill-row-actions");
      const support = element("button", "sw-skill-support", "+");
      support.type = "button";
      support.title = t(sdk, "savage-worlds.ui.suporte", "Suporte");
      support.setAttribute("aria-label", support.title);
      support.addEventListener("click", (event) => {
        event.preventDefault(); event.stopPropagation();
        invokeItemShortcut(ctx, sdk, item, ctx.sheetType === "extra" ? "roll.support.extra" : "roll.support", support);
      });
      const opposed = element("button", "sw-skill-opposed");
      opposed.type = "button";
      opposed.title = t(sdk, "savage-worlds.ui.teste.resistido", "Teste Resistido");
      opposed.setAttribute("aria-label", opposed.title);
      opposed.append(element("i", "ph ph-arrows-left-right", ""));
      opposed.addEventListener("click", (event) => {
        event.preventDefault(); event.stopPropagation();
        invokeItemShortcut(ctx, sdk, item, ctx.sheetType === "extra" ? "roll.opposed.extra" : "roll.opposed", opposed);
      });
      rowActions.append(support, opposed, remove);

      // A linha tem a forma da linha de atributo: nome, dado, modificador. O
      // resumo da perícia mora na ficha do item — é dado do item, e aqui só
      // caberia espremendo as quatro colunas que a mesa consulta em jogo.
      row.append(name, attribute, die, modifier, rowActions);
      host.appendChild(row);
    });

    host.appendChild(unskilledRow(ctx));
    host.classList.toggle("is-empty", skills.length === 0);
  }

  function mountSystemSettings(root, sdk) {
    root.classList.add("sw-system-setup-host");
    const editable = root.parentElement?.dataset.canEdit === "true";
    const skills = configuredSkills(sdk).map((skill) => ({ ...skill }));
    const form = element("form", "sw-system-setup");
    const title = element("header", "sw-system-setup__header");
    title.append(
      element("h3", "", "Configuração do Savage Worlds"),
      element("p", "", "Defina as convenções usadas pelas fichas e automações desta campanha."),
    );
    const skillRows = element("div", "sw-system-setup__skills");
    const attributes = configuredAttributes(sdk).map((attribute) => ({ ...attribute }));
    function paintSkills() {
      skillRows.replaceChildren();
      skills.filter((skill) => skill.isCore !== false).forEach((skill) => {
        const index = skills.indexOf(skill);
        const row = element("div", "sw-system-setup__skill-row");
        const label = document.createElement("input");
        label.value = String(skill.label || "");
        label.placeholder = "Nome da perícia";
        label.disabled = !editable;
        label.addEventListener("input", () => { skill.label = label.value; });
        const attribute = document.createElement("select");
        attribute.disabled = !editable;
        attributes.forEach((definition) => {
          const option = element("option", "", definition.label); option.value = definition.key; attribute.append(option);
        });
        attribute.value = String(skill.attribute || "agility");
        attribute.addEventListener("change", () => { skill.attribute = attribute.value; });
        const remove = element("button", "sw-system-setup__remove", "×");
        remove.type = "button"; remove.disabled = !editable; remove.title = "Remover perícia";
        remove.addEventListener("click", () => { skills.splice(index, 1); paintSkills(); paintParry(); });
        row.append(label, attribute, remove); skillRows.append(row);
      });
    }
    const parry = document.createElement("select");
    parry.disabled = !editable;
    function paintParry() {
      const selected = parry.value || String(sdk.settings.get("parry_skill_key", "fighting") || "fighting");
      parry.replaceChildren();
      skills.forEach((skill) => { const option = element("option", "", skill.label || skill.key); option.value = skill.key; parry.append(option); });
      parry.value = skills.some((skill) => skill.key === selected) ? selected : (skills[0]?.key || "");
    }
    const add = element("button", "secondary-action", "Adicionar perícia");
    add.type = "button"; add.disabled = !editable;
    add.addEventListener("click", () => {
      let number = skills.length + 1;
      while (skills.some((skill) => skill.key === `skill_${number}`)) number += 1;
      skills.push({ key: `skill_${number}`, label: `Perícia ${number}`, attribute: "agility", isCore: true });
      paintSkills(); paintParry();
    });
    const deck = document.createElement("select"); deck.disabled = true;
    deck.append(element("option", "", "Carregando baralhos…"));
    const selectedDeck = String(sdk.settings.get("initiative_deck_id", "") || "");
    void sdk.cards.state().then((state) => {
      const decks = Array.isArray(state?.decks) ? state.decks : [];
      deck.replaceChildren();
      const none = element("option", "", "Nenhum baralho"); none.value = ""; deck.append(none);
      decks.forEach((entry) => { const option = element("option", "", entry.name || entry.id); option.value = entry.id; deck.append(option); });
      deck.value = decks.some((entry) => entry.id === selectedDeck) ? selectedDeck : "";
      deck.disabled = !editable;
    }).catch(() => { deck.firstElementChild.textContent = "Baralhos indisponíveis"; });
    const singular = document.createElement("input"); singular.value = sdk.settings.get("currency_singular", "Ouro"); singular.disabled = !editable;
    const plural = document.createElement("input"); plural.value = sdk.settings.get("currency_plural", "Ouro"); plural.disabled = !editable;
    const abbreviation = document.createElement("input"); abbreviation.value = sdk.settings.get("currency_abbreviation", "$"); abbreviation.disabled = !editable;
    let bennyAssetSrc = String(sdk.settings.get("benny_asset_src", "") || "");
    let bennyAssetId = String(sdk.settings.get("benny_asset_id", "") || "");
    let pendingBennyFile = null;
    let pendingPreviewUrl = "";
    const field = (label, control, hint = "") => {
      const wrapper = element("label", "sw-system-setup__field"); wrapper.append(element("span", "", label), control);
      if (hint) wrapper.append(element("small", "", hint)); return wrapper;
    };
    const skillsCard = element("section", "sw-system-setup__card sw-system-setup__card--skills");
    skillsCard.append(element("h4", "", "Perícias básicas"), element("p", "", "Os identificadores permanecem estáveis; altere os nomes usados na mesa."), skillRows, add);
    const attributeRows = element("div", "sw-system-setup__attributes");
    attributes.forEach((definition) => {
      const row = element("div", "sw-system-setup__attribute-row");
      const label = document.createElement("input");
      label.value = definition.label; label.maxLength = 40; label.disabled = !editable;
      label.setAttribute("aria-label", `Nome de ${definition.label}`);
      label.addEventListener("input", () => { definition.label = label.value; });
      label.addEventListener("change", () => { paintSkills(); });
      const abbr = document.createElement("input");
      abbr.value = definition.abbr; abbr.maxLength = 3; abbr.disabled = !editable;
      abbr.placeholder = "ABC"; abbr.autocomplete = "off";
      abbr.setAttribute("aria-label", `Sigla de ${definition.label}`);
      abbr.addEventListener("input", () => {
        abbr.value = abbr.value.toUpperCase().slice(0, 3);
        definition.abbr = abbr.value;
      });
      row.append(label, abbr); attributeRows.append(row);
    });
    const attributesCard = element("section", "sw-system-setup__card sw-system-setup__card--attributes");
    attributesCard.append(element("h4", "", "Atributos"), element("p", "", "Defina o nome e a sigla de até três letras exibida na ficha."), attributeRows);
    const rulesCard = element("section", "sw-system-setup__card sw-system-setup__card--rules");
    rulesCard.append(field("Perícia usada no Aparar", parry), field("Baralho de iniciativa", deck));
    const currencyCard = element("section", "sw-system-setup__card sw-system-setup__card--currency");
    currencyCard.append(element("h4", "", "Moeda"), field("Singular", singular), field("Plural", plural), field("Abreviação", abbreviation));
    const appearanceCard = element("section", "sw-system-setup__card sw-system-setup__card--appearance");
    const bennyPreview = element("div", "sw-system-setup__benny-preview");
    const bennyPreviewImage = document.createElement("img");
    bennyPreviewImage.alt = "Imagem do Bene";
    const bennyPlaceholder = element("i", "ph ph-coin");
    bennyPreview.append(bennyPreviewImage, bennyPlaceholder);
    const bennyFile = document.createElement("input");
    bennyFile.type = "file"; bennyFile.accept = "image/png,image/jpeg,image/webp"; bennyFile.disabled = !editable;
    const removeBennyImage = element("button", "secondary-action", "Remover imagem");
    removeBennyImage.type = "button"; removeBennyImage.disabled = !editable;
    function paintBennyPreview() {
      const src = pendingPreviewUrl || bennyAssetSrc;
      bennyPreviewImage.src = src;
      bennyPreviewImage.hidden = !src;
      bennyPlaceholder.hidden = Boolean(src);
      removeBennyImage.disabled = !editable || !src;
    }
    bennyFile.addEventListener("change", () => {
      if (pendingPreviewUrl) URL.revokeObjectURL(pendingPreviewUrl);
      pendingBennyFile = bennyFile.files?.[0] || null;
      pendingPreviewUrl = pendingBennyFile ? URL.createObjectURL(pendingBennyFile) : "";
      paintBennyPreview();
    });
    removeBennyImage.addEventListener("click", () => {
      if (pendingPreviewUrl) URL.revokeObjectURL(pendingPreviewUrl);
      pendingPreviewUrl = ""; pendingBennyFile = null; bennyAssetSrc = ""; bennyAssetId = "";
      bennyFile.value = ""; paintBennyPreview();
    });
    appearanceCard.append(
      element("h4", "", "Aparência dos Benes"),
      element("p", "", "Esta imagem será usada na moeda de Bene das fichas desta campanha."),
      bennyPreview,
      field("Imagem do Bene", bennyFile, "PNG, JPEG ou WebP."),
      removeBennyImage,
    );
    paintBennyPreview();
    const save = element("button", "sw-system-setup__save", "Salvar configuração");
    save.type = "submit"; save.disabled = !editable;
    form.addEventListener("submit", async (event) => {
      event.preventDefault(); save.disabled = true;
      try {
        if (pendingBennyFile) {
          const uploaded = await sdk.assets.ingest(pendingBennyFile);
          bennyAssetSrc = String(uploaded?.asset?.src || "");
          bennyAssetId = String(uploaded?.asset?.id || "");
          pendingBennyFile = null;
          if (pendingPreviewUrl) URL.revokeObjectURL(pendingPreviewUrl);
          pendingPreviewUrl = "";
        }
        const values = [
          ["attributes_json", JSON.stringify(attributes.map((attribute, index) => ({
            key: attribute.key,
            label: attribute.label.trim() || ATTRIBUTE_DEFAULTS[index].label,
            abbr: attribute.abbr.trim().slice(0, 3).toUpperCase() || ATTRIBUTE_DEFAULTS[index].abbr,
          })))],
          ["core_skills_json", JSON.stringify(skills)],
          ["parry_skill_key", parry.value],
          ["initiative_deck_id", deck.value],
          ["currency_singular", singular.value.trim() || "Ouro"],
          ["currency_plural", plural.value.trim() || singular.value.trim() || "Ouro"],
          ["currency_abbreviation", abbreviation.value.trim()],
          ["benny_asset_src", bennyAssetSrc],
          ["benny_asset_id", bennyAssetId],
          ["setup_version", 1],
        ];
        for (const [key, value] of values) await sdk.settings.set(key, value);
        syncConfiguredParrySkill(sdk);
        document.querySelectorAll("[data-swade-character]").forEach((sheet) => paintBennyImage(sheet, sdk));
        paintBennyPreview();
        sdk.ui.toast("Configuração do Savage Worlds salva.", { variant: "success" });
      } catch (error) { sdk.ui.toast(String(error?.message || error), { variant: "danger" }); }
      finally { save.disabled = !editable; }
    });
    paintSkills(); paintParry();
    form.append(title, skillsCard, attributesCard, rulesCard, currencyCard, appearanceCard, save);
    root.replaceChildren(form);
  }

  function coversTorso(locations) {
    const value = normalizedName(locations || "torso");
    return !value || ["torso", "corpo", "tronco", "all", "todos"].some((part) => value.split(/[,;/]+/).map((entry) => entry.trim()).includes(part));
  }

  // A Resistência resumida da ficha usa a proteção do torso. Armaduras sobrepostas
  // usam o maior valor integral e metade (arredondada para baixo) das demais.
  // Escudos são separados: bônus de Aparar e cobertura nunca viram Resistência.
  function equippedProtection(ctx) {
    const protection = Array.isArray(ctx.data?.system?.protection)
      ? ctx.data.system.protection
      : [];
    const armor = [];
    let parry = 0;
    let cover = 0;
    protection.forEach((item) => {
      const data = item?.data || {};
      if (!data.equipped) return;
      if (String(item?.type || "") === "shield") {
        parry += Math.max(0, number(data.parryBonus));
        cover = Math.max(cover, Math.max(0, number(data.coverBonus)));
        return;
      }
      if (String(item?.type || "") === "armor" && coversTorso(data.locations)) {
        armor.push(Math.max(0, number(data.armor)));
      }
    });
    armor.sort((left, right) => right - left);
    const layeredArmor = armor.reduce((total, value, index) => total + (index ? Math.floor(value / 2) : value), 0);
    return {
      armor: Math.min(20, layeredArmor),
      parry: Math.min(6, parry),
      cover: Math.min(6, cover),
    };
  }

  // Mesma disciplina do dado de Lutar: o valor derivado é recalculado a cada
  // pintura e só é gravado quando muda, senão cada abertura de ficha viraria um
  // POST — e um evento de sala — sem nada ter acontecido.
  function syncProtection(ctx) {
    const protection = equippedProtection(ctx);
    const toughness = ctx.data?.system?.stats?.toughness;
    if (toughness && number(toughness.armor) !== protection.armor) {
      toughness.armor = protection.armor;
      ctx.onChange?.("system.stats.toughness.armor", protection.armor);
    }
    const parry = ctx.data?.system?.stats?.parry;
    if (parry && number(parry.shield) !== protection.parry) {
      parry.shield = protection.parry;
      ctx.onChange?.("system.stats.parry.shield", protection.parry);
    }
  }

  function carriedWeight(ctx) {
    return ["weapons", "protection", "gear"].reduce((total, collection) => {
      const items = Array.isArray(ctx.data?.system?.[collection]) ? ctx.data.system[collection] : [];
      return total + items.reduce((subtotal, item) => {
        const data = item?.data || {};
        const quantity = data.quantity == null ? 1 : Math.max(0, number(data.quantity));
        return subtotal + Math.max(0, number(data.weight)) * quantity;
      }, 0);
    }, 0);
  }

  function syncCarriedLoad(ctx) {
    const load = ctx.data?.system?.stats?.load;
    if (!load) return;
    const value = carriedWeight(ctx);
    if (Math.abs(number(load.value) - value) < 0.001) return;
    load.value = value;
    ctx.onChange?.("system.stats.load.value", value);
  }

  // Testar algo que o personagem não treinou é d4−2, e acontece o tempo todo.
  // Ficava num botão à parte, longe da lista onde a pessoa procura perícia —
  // agora é a última linha dela, fixa: não se arrasta nem se remove.
  function unskilledRow(ctx) {
    const row = element("div", "sw-skill-row sw-skill-row--fixed");

    const name = element("button", "sw-skill-roll", "Sem perícia");
    name.type = "button";
    name.dataset.swI18n = "savage-worlds.ui.sem.pericia";
    name.addEventListener("click", (event) => {
      event.preventDefault();
      event.stopPropagation();
      const actionId = ctx.sheetType === "extra" ? "roll.unskilled.extra" : "roll.unskilled";
      ctx.onAction?.(actionId, { event, element: name });
    });

    const attribute = element("span", "sw-skill-fixed", "—");
    const die = element("span", "sw-skill-fixed", "d4");
    const modifier = element("span", "sw-skill-fixed", "−2");

    row.append(name, attribute, die, modifier, element("span"));
    return row;
  }

  function applyBurstDamage(sdk, message) {
    const metadata = message?.metadata || {};
    const pool = metadata.pool || {};
    const targets = Array.isArray(pool.declaredTargets) ? pool.declaredTargets : [];
    const hits = (Array.isArray(pool.kept) ? pool.kept : [])
      .filter((entry) => Number(entry?.total || 0) >= Number(pool.target || 4));
    const actorId = String(metadata.actorId || "");
    const itemInstanceId = String(metadata.source?.itemInstanceId || "");
    if (!targets.length || !hits.length || !actorId || !itemInstanceId) {
      sdk.ui.toast("Esta rajada não possui acerto e alvo declarado para aplicar.", { variant: "warning" });
      return;
    }

    document.querySelectorAll(".gw-roll-modal[data-sw-burst-damage]").forEach((node) => node.remove());
    const overlay = element("div", "gw-roll-modal");
    overlay.dataset.swBurstDamage = "1";
    const dialog = element("div", "gw-roll-dialog");
    dialog.setAttribute("role", "dialog");
    dialog.setAttribute("aria-modal", "true");
    dialog.appendChild(element("div", "gw-roll-dialog__title", "Aplicar dano da rajada"));

    const targetLabel = element("label", "gw-roll-dialog__field");
    targetLabel.appendChild(element("span", "gw-roll-dialog__label", "Alvo"));
    const targetSelect = element("select", "gw-roll-dialog__input");
    targets.forEach((target) => {
      const option = element("option", "", `${target.targetName} (${target.amount} disparo(s))`);
      option.value = target.targetTokenId;
      targetSelect.appendChild(option);
    });
    targetLabel.appendChild(targetSelect);

    const hitLabel = element("label", "gw-roll-dialog__field");
    hitLabel.appendChild(element("span", "gw-roll-dialog__label", "Acerto"));
    const hitSelect = element("select", "gw-roll-dialog__input");
    hits.forEach((hit, index) => {
      const raises = Math.max(0, Math.floor((Number(hit.total) - Number(pool.target || 4)) / Number(pool.step || 4)));
      const option = element("option", "", `Resultado ${hit.total}${raises ? ` · ${raises} ampliação(ões)` : ""}`);
      option.value = String(index);
      option.dataset.raise = raises > 0 ? "1" : "0";
      hitSelect.appendChild(option);
    });
    hitLabel.appendChild(hitSelect);

    const actions = element("div", "gw-roll-dialog__actions");
    const cancel = element("button", "gw-roll-dialog__btn", "Cancelar");
    cancel.type = "button";
    cancel.addEventListener("click", () => overlay.remove());
    const apply = element("button", "gw-roll-dialog__btn gw-roll-dialog__btn--primary", "Rolar dano");
    apply.type = "button";
    apply.addEventListener("click", async () => {
      const target = targets.find((entry) => String(entry.targetTokenId) === targetSelect.value);
      const selectedHit = hitSelect.selectedOptions[0];
      if (!target || !selectedHit) return;
      overlay.remove();
      const result = await sdk.rolls.intent({
        actorId,
        itemInstanceId,
        actionId: "roll.damage",
        targetTokenId: target.targetTokenId,
        targetActorId: target.targetActorId,
        rollOptions: { raise: selectedHit.dataset.raise === "1" },
      });
      if (result?.applied) sdk.ui.toast(`${target.targetName}: dano aplicado.`, { variant: "success" });
    });
    actions.append(cancel, apply);
    dialog.append(targetLabel, hitLabel, actions);
    overlay.appendChild(dialog);
    overlay.addEventListener("mousedown", (event) => { if (event.target === overlay) overlay.remove(); });
    document.body.appendChild(overlay);
    targetSelect.focus();
  }

  window.GravewrightSDK.register({
    id: PACKAGE_ID,
    setup(sdk) {
      syncConfiguredParrySkill(sdk);
      sdk.rolls.actions.register(
        {
          id: "spend-benny-reroll",
          label: t(sdk, "savage-worlds.roll.reroll", "Gastar Bene e rerrolar"),
          intents: ["check", "attack", "damage"],
          excludeActionIds: ["roll.soak", "roll.soak.extra", "roll.unshake", "roll.unshake.extra"],
        },
        (message) => sdk.rolls.reroll(message.message_id)
      );
      sdk.rolls.actions.register(
        {
          id: "apply-burst-damage",
          label: t(sdk, "savage-worlds.ui.aplicar.dano", "Aplicar dano"),
          intents: ["attack"],
          actionIds: ["roll.attack", "roll.attack.extra"],
        },
        (message) => applyBurstDamage(sdk, message)
      );
      sdk.ui.slots.register("settings.system", (root) => mountSystemSettings(root, sdk));
      function paint(ctx) {
        announceBennies(ctx, sdk);
        wireBenniesControl(ctx, sdk);
        paintBennyImage(ctx.root, sdk);
        wireConditionsDialog(ctx, sdk);
        syncCoreSkills(ctx, sdk);
        syncCarriedLoad(ctx);
        renderPips(ctx, "wounds");
        renderPips(ctx, "fatigue");
        renderFatigueRecovery(ctx, sdk);
        renderWeaponShortcuts(ctx, sdk);
        renderDerivedNotes(ctx);
        renderEscapeAction(ctx);
        renderAttributes(ctx, sdk);
        renderSkills(ctx, sdk);
        syncProtection(ctx);
        // As linhas são reconstruídas a cada pintura, então a tradução tem de
        // vir depois delas — não só na montagem.
        ctx.root.querySelectorAll("[data-sw-i18n]").forEach((node) => {
          node.textContent = t(sdk, node.dataset.swI18n, node.textContent);
        });
        localizeStatic(ctx.root, sdk);
      }

      const controller = {
        mount(ctx) {
          paint(ctx);
        },
        update(ctx) {
          paint(ctx);
        },
        onAction(action, ctx) {
          const actionId = String(action?.name || "");
          if (!actionId.startsWith("roll.")) return false;
          ctx.onAction?.(actionId, {
            event: action?.event,
            element: action?.element,
          });
          return true;
        },
      };
      const localizationController = {
        mount(ctx) {
          ctx.root.querySelectorAll("[data-sw-i18n]").forEach((node) => {
            node.textContent = t(sdk, node.dataset.swI18n, node.textContent);
          });
          localizeStatic(ctx.root, sdk);
        },
        update(ctx) {
          ctx.root.querySelectorAll("[data-sw-i18n]").forEach((node) => {
            node.textContent = t(sdk, node.dataset.swI18n, node.textContent);
          });
          localizeStatic(ctx.root, sdk);
        },
      };
      sdk.sheets.register({
        autoFitWidth(actorType) {
          return actorType === "character" ? 859 : null;
        },
        autoFitMinWidth(actorType) {
          return actorType === "character" ? 859 : null;
        },
        autoFitHeight(actorType) {
          return actorType === "character" ? 741 : null;
        },
        autoFitMinHeight(actorType) {
          return actorType === "character" ? 741 : null;
        },
      });
      sdk.sheets.registerController("character", controller);
      sdk.sheets.registerController("extra", controller);
      sdk.sheets.registerController("vehicle", localizationController);
      sdk.sheets.registerController("group", localizationController);
      sdk.combat.register({
        handlers: {
          combatantMeta: ({ combatant }) => combatant?.holding
            ? t(sdk, "savage-worlds.initiative.holding", "Aguardando") : "",
          afterRender: (payload) => {
            combatTrackerIsGm = Boolean(payload.isGm);
            void observeInitiativeState(sdk);
            if (restoreConfirmedInitiativeOrder(payload)) return;
            return paintInitiativeCards(payload, sdk);
          },
        },
        slots: {
          toolbar: (payload) => initiativeButton(payload, sdk),
          combatantActions: (payload) => savageTurnActions(payload, sdk),
        },
      });
      sdk.events.on("combat.updated", () => { void observeInitiativeState(sdk); });

      // Chat payloads retain semantic locale keys. Resolve them here so every
      // browser sees the message in its own language, not the sender's.
      const translateChat = () => localizePackage(document, sdk);
      new MutationObserver(translateChat).observe(document.body, { childList: true, subtree: true });
      translateChat();
    },
  });
})();
