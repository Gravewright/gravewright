(function () {
  const Cards = (window.GravewrightCards = window.GravewrightCards || {});

  function csrf() {
    return typeof window.csrfToken === "function" ? window.csrfToken() : "";
  }

  async function request(url, payload) {
    const response = await fetch(url, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        Accept: "application/json",
        "x-csrftoken": csrf(),
      },
      body: JSON.stringify(payload || {}),
      credentials: "same-origin",
    });
    const data = await response.json().catch(() => ({}));
    if (!response.ok) {
      const error = new Error(data.error_key || "game.cards.errors.request_failed");
      error.response = response;
      error.payload = data;
      throw error;
    }
    return data;
  }

  async function fetchCardState(campaignId) {
    const response = await fetch(`/game/cards/state/${encodeURIComponent(campaignId)}`, {
      headers: { Accept: "application/json" },
      credentials: "same-origin",
    });
    const data = await response.json().catch(() => ({}));
    if (!response.ok) {
      const error = new Error(data.error_key || "game.cards.errors.request_failed");
      error.response = response;
      error.payload = data;
      throw error;
    }
    return data;
  }

  function createDeckDefinition(campaignId, payload) {
    return request("/game/cards/decks", { ...payload, campaign_id: campaignId });
  }

  function instantiateDeck(campaignId, deckDefinitionId, payload) {
    return request("/game/cards/decks/instantiate", {
      ...(payload || {}),
      campaign_id: campaignId,
      deck_definition_id: deckDefinitionId,
    });
  }

  function shuffleDeck(campaignId, deckInstanceId) {
    return request("/game/cards/decks/shuffle", {
      campaign_id: campaignId,
      deck_instance_id: deckInstanceId,
    });
  }

  function deleteDeck(campaignId, deckInstanceId) {
    return request("/game/cards/decks/delete", {
      campaign_id: campaignId,
      deck_instance_id: deckInstanceId,
    });
  }

  function resetDeck(campaignId, deckInstanceId, payload) {
    return request("/game/cards/decks/reset", {
      ...(payload || {}),
      campaign_id: campaignId,
      deck_instance_id: deckInstanceId,
    });
  }

  function drawCards(campaignId, payload) {
    return request("/game/cards/draw", { ...(payload || {}), campaign_id: campaignId });
  }

  function revealCards(campaignId, cardIds) {
    return request("/game/cards/reveal", { campaign_id: campaignId, card_ids: cardIds || [] });
  }

  function discardCards(campaignId, cardIds) {
    return request("/game/cards/discard", { campaign_id: campaignId, card_ids: cardIds || [] });
  }

  function playCardToScene(campaignId, payload) {
    return request("/game/cards/play-to-scene", { ...(payload || {}), campaign_id: campaignId });
  }

  function updateSceneCardPlacement(campaignId, payload) {
    return request("/game/cards/scene-placement/update", { ...(payload || {}), campaign_id: campaignId });
  }

  function discardSceneCardPlacement(campaignId, placementId) {
    return request("/game/cards/scene-placement/discard", {
      campaign_id: campaignId,
      placement_id: placementId,
    });
  }

  async function uploadCardAsset(campaignId, file, options) {
    const form = new FormData();
    form.append("campaign_id", campaignId);
    form.append("purpose", (options && options.purpose) || "card_front");
    form.append("file", file);
    const response = await fetch("/game/cards/assets/upload", {
      method: "POST",
      headers: { Accept: "application/json", "x-csrftoken": csrf() },
      body: form,
      credentials: "same-origin",
    });
    const data = await response.json().catch(() => ({}));
    if (!response.ok) {
      const error = new Error(data.error_key || "game.cards.errors.request_failed");
      error.response = response;
      error.payload = data;
      throw error;
    }
    return data;
  }

  Cards.api = Object.freeze({
    createDeckDefinition,
    deleteDeck,
    discardSceneCardPlacement,
    discardCards,
    drawCards,
    fetchCardState,
    instantiateDeck,
    playCardToScene,
    resetDeck,
    revealCards,
    shuffleDeck,
    uploadCardAsset,
    updateSceneCardPlacement,
  });
})();
