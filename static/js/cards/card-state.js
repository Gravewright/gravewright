(function () {
  const Cards = (window.GravewrightCards = window.GravewrightCards || {});

  class CardStateStore {
    constructor() {
      this.state = { decks: [], piles: [], cards: [], scene_placements: [] };
      this.listeners = new Set();
    }

    replaceState(nextState) {
      this.state = nextState || {};
      this.emit();
    }

    subscribe(listener) {
      this.listeners.add(listener);
      return () => this.listeners.delete(listener);
    }

    emit() {
      this.listeners.forEach((listener) => listener(this.state));
    }

    getDeck(deckInstanceId) {
      return (this.state.decks || []).find((deck) => deck.id === deckInstanceId) || null;
    }

    getPile(pileId) {
      return (this.state.piles || []).find((pile) => pile.id === pileId) || null;
    }

    getHandForUser(userId) {
      return (this.state.piles || []).find((pile) => pile.kind === "hand" && pile.owner_user_id === userId) || null;
    }

    cardsForPile(pileId) {
      return (this.state.cards || []).filter((card) => card.current_pile_id === pileId);
    }

    cardsForDeck(deckInstanceId) {
      return (this.state.cards || []).filter((card) => card.deck_instance_id === deckInstanceId);
    }
  }

  Cards.CardStateStore = CardStateStore;
})();
