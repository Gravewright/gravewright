"""Exercise controls with accessibility labels changed before JS initialization."""
import re
from migration_closure import main
from playwright.sync_api import expect


def check(gm, player, data, output):
    gm.add_init_script("""(() => {
      const language = localStorage.getItem('test-label-language') || 'en';
      function translate(root) {
        if (root.nodeType !== 1 && root.nodeType !== 11) return;
        for (const node of [root, ...root.querySelectorAll('*')]) {
          if (node.tagName === 'TEMPLATE') translate(node.content);
          for (const name of ['aria-label', 'title', 'placeholder']) {
            const text = node.getAttribute?.(name);
            if (text && !text.startsWith(language + ': ')) node.setAttribute(name, language + ': ' + text);
          }
        }
      }
      new MutationObserver(records => {
        for (const record of records) for (const node of record.addedNodes) translate(node);
      }).observe(document, {childList:true, subtree:true});
    })()""")
    for language in ('en', 'pt-BR', 'es'):
        gm.evaluate("language => localStorage.setItem('test-label-language', language)", language)
        gm.reload()
        gm.wait_for_function('window.gravewrightTableMedia && window.gravewrightMaps')
        expect(gm.locator('.game-menubar__presence')).to_have_attribute('data-presence', 'seated')
        gm.keyboard.press('Escape')
        gm.wait_for_function('window.gravewrightMaps?.board?.viewport()?.scale > 0')
        print(language, 'ready', flush=True)
        audio = gm.locator('.individual-audio')
        # A missing initialization hook would leave the original, inert controls.
        expect(audio.locator('[data-audio-control]')).to_have_count(0)
        audio.locator('button').first.click()
        volume = audio.locator('input[type=range]').first
        volume.fill('37')
        gm.wait_for_function("Math.abs(Number(localStorage.getItem('gravewright.audio.volume'))-0.37)<0.001")
        audio.locator('button').nth(1).click()
        expect(audio.locator('.individual-audio__mixer')).to_be_visible()
        audio.locator('button').nth(1).click()

        hand = gm.locator('[data-dock-tool=cards]')
        hand.click()
        expect(gm.locator('.card-hand')).to_be_visible()
        hand.click()
        expect(gm.locator('.card-hand')).to_have_count(0)

        gm.locator('.game-menubar__library').click()
        expect(gm.locator('.upload-library')).to_be_visible()
        gm.locator('[data-library-close]').click()
        expect(gm.locator('.upload-library')).to_have_count(0)

        gm.locator('[data-map-visibility]').filter(visible=True).click()
        panel = gm.locator('.game-panel--visibility')
        expect(panel).to_be_visible()
        panel.locator('[data-visibility-action=minimize]').click()
        expect(panel).to_have_class(re.compile('game-panel--minimized'))
        panel.locator('[data-visibility-action=minimize]').click()
        with gm.expect_popup() as popup_info:
            panel.locator('[data-visibility-action=detach]').click()
        popup = popup_info.value
        expect(popup.locator('.game-panel--visibility')).to_be_visible()
        popup.close()
        expect(panel).to_be_visible()
        panel.locator('[data-visibility-action=close]').click()
        expect(panel).to_have_count(0)

        gm.locator('.game-menubar__layer').nth(3).click()
        for tool in ('sound', 'sounds'):
            gm.locator(f'[data-dock-tool={tool}]').click()
            expect(gm.locator('.audio-workspace')).to_be_visible()
            gm.locator(f'[data-dock-tool={tool}]').click()
            expect(gm.locator('.audio-workspace')).to_have_count(0)
        print(f'{language}: translated labels preserve audio, cards, library and visibility controls', flush=True)


if __name__ == '__main__':
    main(check)
