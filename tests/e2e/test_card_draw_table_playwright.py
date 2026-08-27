from __future__ import annotations

from pathlib import Path

from playwright.sync_api import expect, sync_playwright


ROOT = Path(__file__).resolve().parents[2]


def test_single_draw_modal_supports_hand_chat_and_table_placement() -> None:
    with sync_playwright() as playwright:
        browser = playwright.chromium.launch(headless=True)
        page = browser.new_page(viewport={"width": 1000, "height": 760})
        page.set_content("""
          <body data-current-user-id="gm" data-card-label-draw="Comprar"
                data-card-draw-title="Comprar carta" data-card-draw-destination="Destino"
                data-card-draw-hand="Mão" data-card-draw-table="Mesa" data-card-draw-chat="Chat"
                data-card-draw-state="Estado" data-card-draw-face-up="Virada para cima"
                data-card-draw-face-down="Virada para baixo" data-card-draw-quantity="Quantidade"
                data-card-draw-available="{count} disponíveis" data-card-draw-cancel="Cancelar"
                data-card-draw-submit="Comprar">
            <article class="room-workspace is-active" data-is-gm="true">
              <div data-map-viewport style="position:relative;width:800px;height:500px">
                <canvas data-map-canvas data-room-id="room" data-scene-id="scene"
                        style="width:800px;height:500px"></canvas>
                <div class="card-scene-layer" data-card-scene-layer data-room-id="room"
                     style="position:absolute;inset:0"></div>
              </div>
            </article>
            <section data-card-panel data-card-panel-mode="hand" data-room-id="room" data-is-gm="true">
              <div data-card-notice hidden></div><div data-card-hand></div>
            </section>
          </body>
        """)
        page.add_style_tag(path=str(ROOT / "static/css/game.css"))
        page.add_script_tag(path=str(ROOT / "static/js/cards/card-state.js"))
        page.evaluate("""
          () => {
            window.__draws = [];
            window.__plays = [];
            window.__state = {campaign_id: 'room', decks: [{id: 'deck', name: 'Tarot', draw_count: 3}],
              piles: [{id: 'hand', kind: 'hand', owner_user_id: 'gm'}],
              cards: [{id: 'held-card', name: 'The Moon', deck_instance_id: 'deck',
                current_pile_id: 'hand', front_asset_id: 'front', back_asset_id: 'back'}],
              scene_placements: []};
            window.GravewrightMap = {
              activeCanvas: () => document.querySelector('[data-map-canvas]'),
              stateFor: () => ({zoom: 1, offsetX: 0, offsetY: 0}),
            };
            window.GravewrightCards.api = {
              fetchCardState: async () => structuredClone(window.__state),
              drawCards: async (_room, payload) => {
                window.__draws.push(payload);
                const cards = Array.from({length: payload.count}, (_, index) => ({
                  id: `draw-${window.__draws.length}-${index}`, name: `Card ${index}`,
                  front_asset_id: 'front', back_asset_id: 'back', face_state: payload.reveal ? 'face_up' : 'face_down',
                }));
                return {cards};
              },
              playCardToScene: async (_room, payload) => { window.__plays.push(payload); return {placement: {id: `p-${window.__plays.length}`}}; },
              updateSceneCardPlacement: async () => ({}), discardSceneCardPlacement: async () => ({}),
            };
          }
        """)
        page.add_script_tag(path=str(ROOT / "static/js/cards/card-panel.js"))
        page.evaluate("document.dispatchEvent(new Event('DOMContentLoaded'))")
        page.wait_for_selector('[data-card-action="open-draw"]')

        page.eval_on_selector('[data-card-action="view-hand"]', "button => button.click()")
        preview = page.locator("dialog.card-preview-dialog")
        expect(preview).to_be_visible()
        expect(preview.locator("strong")).to_have_text("The Moon")
        expect(preview.locator("img")).to_have_attribute("src", "/game/journal/asset/front")
        preview.locator("[data-card-preview-close]").click()
        expect(page.locator("dialog.card-preview-dialog")).to_have_count(0)

        page.evaluate("document.querySelector('[data-card-action=\"open-draw\"]').click()")
        expect(page.locator("dialog.card-draw-dialog")).to_be_visible()
        assert page.locator("dialog.card-draw-dialog").count() == 1
        page.eval_on_selector("dialog [data-card-draw-cancel]", "node => node.click()")
        expect(page.locator("dialog.card-draw-dialog")).to_have_count(0)
        assert page.evaluate("window.__draws.length") == 0

        page.evaluate("document.querySelector('[data-card-action=\"open-draw\"]').click()")
        page.eval_on_selector('dialog[open] [name="destination"][value="table"]', "node => node.checked = true")
        page.eval_on_selector('dialog[open] [name="face"][value="face_down"]', "node => node.checked = true")
        count = page.locator("dialog[open] [data-card-draw-count]")
        count.fill("0")
        expect(page.locator("dialog[open] [data-card-draw-submit]")).to_be_disabled()
        count.fill("2")
        page.eval_on_selector("dialog[open] [data-card-draw-form]", "form => form.requestSubmit()")
        page.wait_for_function("window.__draws.length === 1")
        page.wait_for_selector(".card-placement-preview", state="attached")
        page.mouse.move(320, 240)
        page.mouse.down()
        page.mouse.up()
        page.wait_for_function("window.__plays.length === 2")
        assert page.evaluate("window.__draws[0]") == {
            "deck_instance_id": "deck", "count": 2, "destination": "hand", "reveal": False,
        }
        plays = page.evaluate("window.__plays")
        assert len({play["card_id"] for play in plays}) == 2
        assert all(play["scene_id"] == "scene" and play["reveal"] is False for play in plays)
        assert plays[1]["x"] - plays[0]["x"] == 22
        assert plays[1]["y"] - plays[0]["y"] == 16

        page.evaluate("document.querySelector('[data-card-action=\"open-draw\"]').click()")
        page.eval_on_selector('dialog[open] [name="destination"][value="hand"]', "node => node.checked = true")
        page.eval_on_selector('dialog[open] [name="face"][value="face_up"]', "node => node.checked = true")
        page.eval_on_selector("dialog[open] [data-card-draw-form]", "form => form.requestSubmit()")
        page.wait_for_function("window.__draws.length === 2")
        assert page.evaluate("window.__draws[1].destination") == "hand"

        page.evaluate("document.querySelector('[data-card-action=\"open-draw\"]').click()")
        page.eval_on_selector('dialog[open] [name="destination"][value="chat"]', "node => node.checked = true")
        page.eval_on_selector('dialog[open] [name="face"][value="face_down"]', "node => node.checked = true")
        page.eval_on_selector("dialog[open] [data-card-draw-form]", "form => form.requestSubmit()")
        page.wait_for_function("window.__draws.length === 3")
        assert page.evaluate("window.__draws[2].destination") == "chat"
        assert page.evaluate("window.__draws[2].reveal") is False
        browser.close()
