/**
 * Black Vault — a cooperative supernatural infiltration mission.
 *
 * Every authoritative decision in this module lives on the server: phase
 * commitment is a Gameplay Flow, every branch is a Durable Workflow BRANCH over a
 * projected Directed Interaction answer, and every consequence is a registered
 * action. Nothing here decides an outcome in the browser.
 */
(() => {
  "use strict";

  const PACKAGE_ID = "black-vault";

  const FLOW = "infiltration";
  const PHASES = ["BRIEFING", "PLANNING", "REVEAL", "RESOLUTION", "SECURITY_RESPONSE", "EXTRACTION", "COMPLETE"];
  const PLANNING_CHOICES = ["MOVE", "HACK", "DISTRACT", "SCAN", "USE_CARD"];

  const ALARM_WORKFLOW = "alarm-response";
  const TERMINAL_WORKFLOW = "terminal-hack";
  const ALARM_TIMELINE = "alarm-cascade";
  const EXTRACTION_TIMELINE = "extraction";

  const TYPE = {
    terminal: `${PACKAGE_ID}.vault-terminal`,
    pedestal: `${PACKAGE_ID}.artifact-pedestal`,
    elevator: `${PACKAGE_ID}.vault-elevator`,
    beacon: `${PACKAGE_ID}.alarm-beacon`,
    clue: `${PACKAGE_ID}.clue-pin`,
  };
  const ZONE = { restricted: `${PACKAGE_ID}.restricted`, extraction: `${PACKAGE_ID}.extraction` };
  // The drag source is keyed by the reference kind it carries.
  const DRAG = { source: "card", target: `${PACKAGE_ID}.terminal-slot` };

  const VAULT_DOOR = { x1: 480, y1: 120, x2: 480, y2: 620 };

  // Operator shortcuts. The Input Registry owns the physical keys; these are only
  // the semantic commands and the bindings the operator starts with.
  const COMMAND = { operations: "open-operations", scanner: "engage-scanner" };

  let sdk;
  const disposers = [];
  let mission = null;
  let overlayHost = null;
  let systemsActorId = null;

  const beat = (name, detail = "") => sdk.storage.sqlite.execute("campaign", "recordBeat", {
    missionId: mission?.flowId || "unstarted", beat: name, detail: String(detail), at: Math.floor(Date.now() / 1000),
  }).catch(() => {});

  // ---------------------------------------------------------------- definitions

  function flowDefinition() {
    return {
      id: FLOW, schemaVersion: 1, turnModel: "SIMULTANEOUS",
      phases: PHASES.map((id) => ({ id, label: id.replace(/_/g, " "), submissionPolicy: "all" })),
    };
  }

  /**
   * The jammer branch. `resultKey` projects the player's answer into workflow
   * context so the BRANCH — not this file — selects the consequence.
   */
  function alarmWorkflow(systemsActorId, eligible, deadline) {
    return {
      id: ALARM_WORKFLOW, schemaVersion: 1, maxDuration: 3600,
      steps: [
        { type: "ACTION", action: `${PACKAGE_ID}:alarm.raise@1`, input: { actorId: systemsActorId } },
        {
          type: "INTERACTION", resultKey: "jammerDecision",
          request: {
            kind: "black-vault.jammer", recipients: [eligible],
            title: "Bloqueador EMP", text: "Usar bloqueador EMP?",
            responseSchema: { type: "single-choice", choices: [
              { id: "USE_JAMMER", label: "Usar bloqueador EMP" },
              { id: "DECLINE", label: "Deixar o alarme soar" },
            ] },
            visibility: "requester", deadline, responsePolicy: "immutable",
          },
        },
        { type: "BRANCH", key: "jammerDecision", equals: "USE_JAMMER", then: 3, else: 4 },
        { type: "ACTION", action: `${PACKAGE_ID}:alarm.suppress@1`, input: { actorId: systemsActorId } },
        { type: "COMPLETE", reason: "alarm-resolved" },
      ],
    };
  }

  function terminalWorkflow(systemsActorId, eligible, deadline, quietSeconds, fastSeconds) {
    return {
      id: TERMINAL_WORKFLOW, schemaVersion: 1, maxDuration: 3600,
      steps: [
        {
          type: "INTERACTION", resultKey: "overrideMode",
          request: {
            kind: "black-vault.override", recipients: [eligible],
            title: "Vault Terminal", text: "Escolha o modo de override.",
            responseSchema: { type: "single-choice", choices: [
              { id: "QUIET_OVERRIDE", label: "Quiet Override" },
              { id: "FAST_OVERRIDE", label: "Fast Override" },
            ] },
            visibility: "requester", deadline, responsePolicy: "immutable",
          },
        },
        { type: "BRANCH", key: "overrideMode", equals: "QUIET_OVERRIDE", then: 2, else: 4 },
        { type: "WAIT_UNTIL", delaySeconds: quietSeconds },
        { type: "BRANCH", key: "overrideMode", equals: "QUIET_OVERRIDE", then: 6, else: 6 },
        { type: "WAIT_UNTIL", delaySeconds: fastSeconds },
        { type: "ACTION", action: `${PACKAGE_ID}:vault.trace@1`, input: { actorId: systemsActorId } },
        { type: "ACTION", action: `${PACKAGE_ID}:vault.unlock@1`, input: { actorId: systemsActorId } },
        { type: "COMPLETE", reason: "vault-open" },
      ],
    };
  }

  /** Semantic composition only: no renderer, no GLSL, no package timer. */
  function alarmTimeline(sceneId, alarmSound) {
    return {
      id: ALARM_TIMELINE, schemaVersion: 1,
      cues: [
        { cueId: "siren", offsetMs: 0, type: "AUDIO_PLAY", parameters: {
          asset: { kind: "library-asset", id: alarmSound.asset.id }, channel: "sfx",
          gain: 0.9, loop: false, audience: { kind: "campaign" }, sceneId } },
        { cueId: "warning", offsetMs: 0, type: "PRESENTATION_SHOW", parameters: {
          mode: "title-card", content: { title: "ALARME", text: "Resposta de segurança acionada." },
          audience: { kind: "campaign" } } },
        { cueId: "redlight", offsetMs: 400, type: "LIGHT_CREATE", parameters: {
          x: 700, y: 350, bright_radius: 120, dim_radius: 320, color: "#ff2f3a", intensity: 0.9 } },
        { cueId: "bloom", offsetMs: 600, type: "SHADER_PRESET", parameters: { presetId: "vortex-1" } },
        { cueId: "sparks", offsetMs: 900, type: "PARTICLE_CREATE", parameters: {
          x: 700, y: 350, kind: "ember", density: 0.6, scale: 4 } },
      ],
    };
  }

  function extractionTimeline(sceneId) {
    return {
      id: EXTRACTION_TIMELINE, schemaVersion: 1,
      cues: [
        { cueId: "fade", offsetMs: 0, type: "PRESENTATION_SHOW", parameters: {
          mode: "title-card", content: { title: "EXTRAÇÃO", text: "A equipe desaparece na noite." },
          audience: { kind: "campaign" } } },
        { cueId: "silence", offsetMs: 1200, type: "SHADER_PRESET", parameters: { presetId: "fog-1" } },
      ],
    };
  }

  function objectTypes() {
    const point = ["point"];
    return [
      { typeId: TYPE.terminal, schemaVersion: 1, displayName: "Vault Terminal", geometryKinds: point,
        dataSchema: { type: "object", properties: { state: { type: "string" } } },
        visualDefinition: [{ kind: "shape", tint: "#39d0ff" }],
        interactionDefinitions: [{ id: "hack", label: "Hack" }] },
      { typeId: TYPE.pedestal, schemaVersion: 1, displayName: "Artifact Pedestal", geometryKinds: point,
        dataSchema: { type: "object", properties: { taken: { type: "boolean" } } },
        visualDefinition: [{ kind: "shape", tint: "#e0c060" }],
        interactionDefinitions: [{ id: "take-artifact", label: "Take Artifact" }] },
      { typeId: TYPE.elevator, schemaVersion: 1, displayName: "Vault Elevator", geometryKinds: point,
        dataSchema: { type: "object", properties: { destinationSceneId: { type: "string" } } },
        visualDefinition: [{ kind: "shape", tint: "#9a8cff" }],
        interactionDefinitions: [{ id: "enter-inner-vault", label: "Enter Inner Vault" }] },
      { typeId: TYPE.beacon, schemaVersion: 1, displayName: "Alarm Beacon", geometryKinds: point,
        dataSchema: { type: "object", properties: { armed: { type: "boolean" } } },
        visualDefinition: [{ kind: "shape", tint: "#ff2f3a" }],
        interactionDefinitions: [{ id: "inspect", label: "Inspect" }] },
      { typeId: TYPE.clue, schemaVersion: 1, displayName: "Clue Pin", geometryKinds: point,
        dataSchema: { type: "object", properties: { contentReference: { type: "string" } } },
        visualDefinition: [{ kind: "shape", tint: "#8fdc7a" }],
        interactionDefinitions: [{ id: "open-clue", label: "Open Clue" }] },
    ];
  }

  // ------------------------------------------------------------------ provisioning

  async function ensureSound(name, packagePath) {
    const existing = (await sdk.sounds.list({ kind: "sound-effect", query: name })).find((s) => s.name === name);
    if (existing) return existing;
    return sdk.sounds.create({
      name, asset: { kind: "package-asset", id: packagePath }, kind: "sound-effect",
      defaultGain: 0.7, defaultLoop: true, tags: ["black-vault", "environment"],
    });
  }

  async function ensureEmitter(sceneId, sound, position, radius, enabled) {
    const existing = (await sdk.scene.spatialSounds.list(sceneId)).find((e) => e.soundId === sound.id);
    if (existing) return existing;
    return sdk.scene.spatialSounds.create(sceneId, {
      soundId: sound.id, position, radius, gain: sound.defaultGain, falloff: "smooth",
      loop: true, enabled, audience: { kind: "campaign" }, constrainedByWalls: true,
    });
  }

  async function ensureVaultDoor(sceneId) {
    const walls = await sdk.scene.geometry.walls(sceneId);
    const existing = walls.find((w) => w.kind === "door"
      && w.x1 === VAULT_DOOR.x1 && w.y1 === VAULT_DOOR.y1 && w.x2 === VAULT_DOOR.x2 && w.y2 === VAULT_DOOR.y2);
    if (existing) return existing;
    return (await sdk.scene.geometry.createWall(sceneId, { ...VAULT_DOOR, kind: "door", presentation: "normal" })).wall;
  }

  async function ensureZone(sceneId, type, geometry) {
    const existing = (await sdk.scene.zones.list(sceneId)).find((z) => z.type === type);
    if (existing) return existing;
    return sdk.scene.zones.create(sceneId, { type, geometry, audience: { kind: "campaign" }, enabled: true, tags: ["black-vault"] });
  }

  async function ensureObject(sceneId, typeId, position, data) {
    const existing = (await sdk.scene.objects.list(sceneId)).find((o) => o.typeId === typeId);
    if (existing) return existing;
    return sdk.scene.objects.create(sceneId, {
      typeId, geometry: { kind: "point", x: position.x, y: position.y },
      data, audience: { kind: "campaign" },
    });
  }

  async function ensureClueJournal() {
    const title = "Black Vault — Recovered Log";
    const listed = await sdk.journals.list({ type: "lore" });
    const existing = (listed?.journals || []).find((entry) => entry.title === title);
    const journalId = existing?.id || (await sdk.journals.create({
      title, type: "lore", visibility: "private",
      data: { sections: [{ id: "intro", kind: "text", title: "Recovered Log",
        body: "The vault's night shift never clocked out." }] },
    })).journal_id;
    return sdk.content.ref("journal", journalId);
  }

  // ---------------------------------------------------------------------- mission

  /** Operatives are the campaign's players; the GM runs the op, not the infiltration. */
  async function operatives() {
    const roster = await sdk.campaign.members();
    return roster.filter((member) => member.role === "player").map((member) => member.userId);
  }

  async function startMission(sceneId) {
    const participants = await operatives();
    if (!participants.length) return null;
    await sdk.gameplay.flows.register(flowDefinition());
    const flow = await sdk.gameplay.flows.start({
      definitionId: FLOW, participants, sceneId, idempotencyKey: `black-vault:${sceneId}`,
    });
    mission = { flowId: flow.id, sceneId, participants };
    await beat("MISSION_STARTED", sceneId);
    return flow;
  }

  /**
   * Whoever actually tripped the zone answers for it. The token reports its
   * canonical controllers; the module picks an operative among them and never
   * acts as that user.
   */
  async function recipientForToken(tokenId, sceneId) {
    const token = await sdk.tokens.get(tokenId, { sceneId });
    const controllers = token?.controllers || [];
    const operative = controllers.find((userId) => mission?.participants?.includes(userId));
    return operative || mission?.participants?.[0] || null;
  }

  async function submitPlan(flowId, choice, version) {
    if (!PLANNING_CHOICES.includes(choice)) throw new TypeError("unknown Black Vault plan");
    return sdk.gameplay.flows.submit(flowId, { action: choice }, { expectedVersion: version });
  }

  async function advance(flowId, version) {
    return sdk.gameplay.flows.advance(flowId, { expectedVersion: version });
  }

  async function raiseAlarm(systemsActorId, eligible, sceneId) {
    const deadline = Math.floor(Date.now() / 1000) + 900;
    await sdk.workflows.register(alarmWorkflow(systemsActorId, eligible, deadline));
    await beat("ALARM_TRIGGERED", eligible);
    return sdk.workflows.start({ definitionId: ALARM_WORKFLOW, sceneId, idempotencyKey: `alarm:${sceneId}` });
  }

  async function hackTerminal(systemsActorId, eligible, sceneId, hardened) {
    const deadline = Math.floor(Date.now() / 1000) + 900;
    await sdk.workflows.register(terminalWorkflow(systemsActorId, eligible, deadline, hardened ? 120 : 60, 5));
    await beat("TERMINAL_HACK", eligible);
    return sdk.workflows.start({ definitionId: TERMINAL_WORKFLOW, sceneId, idempotencyKey: `terminal:${sceneId}` });
  }

  async function playAlarmCascade(sceneId, alarmSound) {
    await sdk.timelines.register(alarmTimeline(sceneId, alarmSound));
    return sdk.timelines.start({
      definitionId: ALARM_TIMELINE, sceneId, audience: { kind: "campaign", ids: [] },
      idempotencyKey: `alarm-cascade:${sceneId}`,
    });
  }

  async function extract(transfers, destinationSceneId, audience) {
    // Movement and viewpoint are deliberately two operations: the party is moved
    // atomically, then only authorized viewers are navigated.
    const result = await sdk.tokens.transferMany(transfers);
    await sdk.navigation.scene.go({ sceneId: destinationSceneId, recipients: audience });
    await sdk.timelines.register(extractionTimeline(destinationSceneId));
    await sdk.timelines.start({
      definitionId: EXTRACTION_TIMELINE, sceneId: destinationSceneId,
      audience: { kind: "campaign", ids: [] }, idempotencyKey: `extraction:${destinationSceneId}`,
    });
    await beat("EXTRACTION", destinationSceneId);
    return result;
  }

  /** The infiltration kit is native Card content, never a package-side inventory. */
  async function ensureKit(artworkAssetId) {
    const decks = await sdk.cards.state();
    const existing = (decks.decks || []).find((deck) => deck.name === "Black Vault Infiltration Kit");
    if (existing) return existing;
    return (await sdk.cards.definitions.instantiate("infiltration-kit", {
      version: 1, name: "Black Vault Infiltration Kit",
      artwork: { "access-card": artworkAssetId, artifact: artworkAssetId },
      metadata: { missionId: mission?.flowId || "black-vault" },
    })).deck;
  }

  async function drawAccessCard(deckId) {
    await beat("ACCESS_CARD_DRAWN", deckId);
    return sdk.cards.draw(deckId, { count: 1, destination: "hand" });
  }

  /** Slotting the credential is a declarative drop, resolved by the registered action. */
  async function slotAccessCard(cardId, terminalObjectId, position) {
    return sdk.ui.dragDrop.drop({
      operation: "place",
      payload: { kind: "card", reference: sdk.content.ref("card", cardId), schemaVersion: 1 },
      destination: {
        targetDefinitionId: DRAG.target, kind: "scene-object",
        resource: { id: terminalObjectId },
        worldPosition: { x: position.x, y: position.y },
      },
      idempotencyKey: `slot:${cardId}`,
    });
  }

  async function takeArtifact(pedestalObjectId, deckId) {
    await sdk.scene.objects.interact(pedestalObjectId, "take-artifact");
    await beat("ARTIFACT_TAKEN", pedestalObjectId);
    return sdk.cards.draw(deckId, { count: 1, destination: "hand" });
  }

  async function announce(title, text, audience) {
    return sdk.ui.presentations.show({
      mode: "title-card", content: { title, text }, audience, duration: 8,
    });
  }

  async function missionState() {
    if (!mission) return null;
    const [flow, workflows, timelines] = await Promise.all([
      sdk.gameplay.flows.get(mission.flowId),
      sdk.workflows.list(),
      sdk.timelines.list(),
    ]);
    const alarm = workflows.find((value) => value.definitionId === ALARM_WORKFLOW);
    const systems = systemsActorId ? await sdk.actors.data(systemsActorId).catch(() => null) : null;
    return {
      scanner: systems?.blackVault?.scanner || "IDLE",
      flow,
      alarm: alarm ? alarm.status : "CLEAR",
      cascadeRunning: timelines.some((value) => value.definitionId === ALARM_TIMELINE && value.status === "RUNNING"),
    };
  }

  // --------------------------------------------------------------------- surfaces

  function operationsApplication() {
    return {
      title: "Black Vault Operations",
      parts: {
        async status(appContext, partRoot) {
          const doc = partRoot.ownerDocument;
          const panel = doc.createElement("section");
          panel.className = "black-vault-operations";
          const state = await missionState();
          const flow = state?.flow || null;
          const rows = [
            ["Phase", flow?.phaseId || "—"],
            ["Alarm", state?.alarm || "—"],
            ["Objective", appContext?.objective || "Reach the Inner Vault"],
            ["Scanner", state?.scanner || "IDLE"],
            ["Team", flow ? `${Object.keys(flow.submissions).length}/${flow.participants.length} ready` : "—"],
          ];
          for (const [label, value] of rows) {
            const row = doc.createElement("p");
            row.textContent = `${label}: ${value}`;
            panel.appendChild(row);
          }
          return panel;
        },
      },
    };
  }

  async function registerSurfaces() {
    for (const definition of objectTypes()) disposers.push(await sdk.scene.objectTypes.register(definition));

    disposers.push(await sdk.ui.dragDrop.registerSource({
      id: DRAG.source, referenceKinds: ["card"], operations: ["place"],
      label: "Access credential", schemaVersion: 1,
    }));
    disposers.push(await sdk.ui.dragDrop.registerTarget({
      id: DRAG.target, operations: ["place"], surface: "scene-world-object",
      targetKinds: ["scene-object"], worldObjectTypeId: TYPE.terminal,
      actionReference: `${PACKAGE_ID}:terminal.slot-card@1`, schemaVersion: 1,
    }));

    disposers.push(sdk.ui.applications.register("operations", operationsApplication()));
    registerOperationsPanel();
    await registerOperationsCommand();
  }

  /**
   * Operations is a package application, so the core owns its DOM: the module
   * only says where it lives and when it is visible.
   */
  function registerOperationsPanel() {
    disposers.push(sdk.ui.slots.register("board.overlay", (root) => {
      overlayHost = root;
      root.className = "black-vault-overlay";
      root.hidden = true;
    }));
    disposers.push(sdk.ui.slots.register("dock.actions", (root) => {
      const button = root.ownerDocument.createElement("button");
      button.type = "button";
      button.className = "black-vault-dock";
      button.textContent = "Vault Ops";
      button.title = "Black Vault Operations";
      button.addEventListener("click", () => void toggleOperations());
      root.appendChild(button);
    }));
  }

  async function toggleOperations() {
    if (!overlayHost) return;
    if (!overlayHost.hidden) {
      overlayHost.hidden = true;
      sdk.ui.applications.close("operations");
      return;
    }
    await openOperations();
  }

  /** Opening and focusing are the same act: render the application into its host. */
  async function openOperations() {
    if (!overlayHost) return;
    overlayHost.hidden = false;
    await sdk.ui.applications.render("operations", overlayHost);
  }

  /**
   * Operations answers to a key as well as to the dock button. The handler receives
   * a semantic invocation from the core Input Runtime — never a keyboard event — and
   * opens the application through the same public API the button uses.
   */
  async function registerOperationsCommand() {
    disposers.push(await sdk.input.commands.register({
      id: COMMAND.operations, label: "Open Black Vault Operations",
      description: "Open or focus the Operations console.",
      contexts: ["global"], defaultBindings: ["Alt+O"],
    }, () => openOperations()));
  }

  /**
   * Engaging the scanner is a mission consequence, so it is server-authoritative:
   * the command carries no payload from the browser. The mission actor is pre-bound
   * here, once it is known, and the server executes the registered action with that
   * canonical input.
   */
  async function registerScannerCommand(systemsActorId) {
    disposers.push(await sdk.input.commands.register({
      id: COMMAND.scanner, label: "Engage vault scanner",
      description: "Run the vault scanner from the operator console.",
      contexts: ["global"], defaultBindings: ["Alt+S"],
      registeredAction: `${PACKAGE_ID}:scanner.engage@1`,
      actionInput: { actorId: systemsActorId },
    }));
  }

  /**
   * The alarm is triggered by authoritative movement, never by polling geometry:
   * the core zone event carries the zone id, which we resolve semantically.
   */
  function subscribe(systemsActorId) {
    disposers.push(sdk.events.on("zone.entered", async (event) => {
      if (!mission || !event?.zone_id) return;
      const zone = await sdk.scene.zones.get(event.zone_id);
      if (zone?.type !== ZONE.restricted) return;
      const operative = await recipientForToken(event.token_id, event.scene_id);
      if (!operative) return;
      await raiseAlarm(systemsActorId, operative, mission.sceneId);
    }));
    disposers.push(sdk.events.on("scene.object.interacted", async (event) => {
      if (!mission || !event?.object_id) return;
      const object = await sdk.scene.objects.get(event.object_id);
      if (!object) return;
      if (object.typeId === TYPE.clue && object.data?.contentReference) {
        // A reference is a pointer: the core still decides whether it opens.
        if (await sdk.content.can(object.data.contentReference, "read")) {
          await sdk.content.open(object.data.contentReference);
        }
        return;
      }
      if (object.typeId === TYPE.terminal) {
        const hardened = sdk.settings.get("difficulty", "standard") === "hardened";
        await hackTerminal(systemsActorId, mission.participants?.[0], mission.sceneId, hardened);
      }
      if (object.typeId === TYPE.beacon) {
        const alarm = (await sdk.sounds.list({ kind: "sound-effect", query: "Security Alarm" }))[0];
        if (alarm) await playAlarmCascade(mission.sceneId, alarm);
      }
    }));
  }

  // ------------------------------------------------------------------------ entry

  window.GravewrightSDK.register({
    id: PACKAGE_ID,
    async setup(value) {
      sdk = value;
      await registerSurfaces();
    },
    async ready() {
      const scene = await sdk.scene.active();
      if (!scene) return;
      const sceneId = scene.id;

      const generator = await ensureSound("Generator Hum", "audio/generator-hum.ogg");
      const alarm = await ensureSound("Security Alarm", "audio/security-alarm.ogg");
      await ensureEmitter(sceneId, generator, { x: 280, y: 280 }, 560, true);
      await ensureEmitter(sceneId, alarm, { x: 700, y: 350 }, 700, false);

      const door = await ensureVaultDoor(sceneId);
      if (door) await sdk.scene.geometry.setDoorState(door.id, "closed");

      await ensureZone(sceneId, ZONE.restricted, { shape: "rect", x: 520, y: 160, width: 360, height: 360 });
      await ensureObject(sceneId, TYPE.terminal, { x: 640, y: 300 }, { state: "locked" });
      await ensureObject(sceneId, TYPE.beacon, { x: 700, y: 350 }, { armed: true });
      await ensureObject(sceneId, TYPE.elevator, { x: 860, y: 420 }, { destinationSceneId: "" });
      const clueReference = await ensureClueJournal();
      await ensureObject(sceneId, TYPE.clue, { x: 320, y: 480 }, { contentReference: clueReference });

      const systems = (await sdk.actors.list()).find((a) => a.name === "Vault Systems");
      if (systems) {
        systemsActorId = systems.id;
        await startMission(sceneId);
        subscribe(systems.id);
        await registerScannerCommand(systems.id);
      }
      if (sdk.settings.get("tutorialHints", true)) {
        sdk.ui.toast("Black Vault ready — open Operations from the dock.");
      }
    },
    teardown() {
      while (disposers.length) {
        const dispose = disposers.pop();
        try { if (typeof dispose === "function") dispose(); } catch (error) { void error; }
      }
      sdk.ui.applications.close("operations");
      overlayHost = null;
      mission = null;
      systemsActorId = null;
    },
  });
})();
