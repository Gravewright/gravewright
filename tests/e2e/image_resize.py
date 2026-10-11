"""Exercise scene-image handles in Chromium without a development database."""
import functools
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
import threading

from playwright.sync_api import sync_playwright, expect

ROOT = Path(__file__).resolve().parents[2]


class QuietHandler(SimpleHTTPRequestHandler):
    def log_message(self, *_args):
        pass


def main():
    server = ThreadingHTTPServer(('127.0.0.1', 0), functools.partial(QuietHandler, directory=str(ROOT)))
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        with sync_playwright() as playwright:
            browser = playwright.chromium.launch(headless=True)
            page = browser.new_page(viewport={'width': 1400, 'height': 1200})
            errors = []
            page.on('pageerror', lambda error: errors.append(str(error)))
            page.goto(f'http://127.0.0.1:{server.server_port}/')
            page.evaluate("""async () => {
                const {default: Images} = await import('/gravewright/maps/frontend/features/images/ui/ImageWorkspace.native.js');
                document.body.innerHTML = '<div id="host" style="position:relative;width:1300px;height:1100px"></div>';
                const css = document.createElement('link');
                css.rel = 'stylesheet'; css.href = '/gravewright/maps/static/gravewright_maps/tools.css';
                document.head.append(css);
                window.commands = [];
                window.saved = {id: 'image', version: 1, x: 300, y: 200, scale: 1, rotation: 0,
                    natural_width: 200, natural_height: 100, z_index: 0};
                let instance;
                window.mountImage = (zoom = 1, rotation = 0) => {
                    instance?.destroy();
                    saved.rotation = rotation;
                    instance = Images(document.querySelector('#host'), {
                        HttpClient: class {}, read() {},
                        props: {images: [saved], viewport: {x: 100, y: 100, scale: zoom},
                            cell: 70, grid: true, tool: 'select', containerId: 'table', blockId: 'scene'},
                        async command(area, action, data) {
                            commands.push({area, action, data});
                            if (window.rejectSave) throw Error('conflict');
                            saved = {...saved, x: data.x, y: data.y, scale: data.scale, version: saved.version + 1};
                            instance.update({images: [saved]});
                        }, emit() {},
                    });
                };
                mountImage();
            }""")
            for zoom, rotation in [(1, 0), (0.5, 45), (1.5, 90)]:
                page.evaluate('([zoom, rotation]) => mountImage(zoom, rotation)', [zoom, rotation])
                image = page.locator('.image-workspace__image')
                image.click()
                handles = page.locator('.image-workspace__resize')
                expect(handles).to_have_count(4)
                old = page.evaluate('({...saved})')
                box = handles.nth(2).bounding_box()
                x, y = box['x'] + box['width'] / 2, box['y'] + box['height'] / 2
                count = page.evaluate('commands.length')
                page.mouse.move(x, y)
                page.mouse.down()
                page.mouse.move(x + 45, y + 60, steps=5)
                page.mouse.up()
                try:
                    page.wait_for_function('(n) => commands.length === n + 1', arg=count, timeout=5000)
                except Exception:
                    print({'zoom': zoom, 'rotation': rotation, 'errors': errors,
                           'commands': page.evaluate('commands'), 'handle': box})
                    raise
                command = page.evaluate('commands.at(-1)')
                assert command['area'] == 'images' and command['action'] == 'update'
                assert command['data']['placement_id'] == 'image'
                assert command['data']['expected_version'] == old['version']
                assert command['data']['scale'] != old['scale']
                persisted = page.evaluate('({...saved})')
                page.evaluate('([zoom, rotation]) => mountImage(zoom, rotation)', [zoom, rotation])
                assert abs(float(image.get_attribute('width')) - 200 * persisted['scale']) < 1e-8
            # Cancelling a drag restores the previous dimensions without saving.
            image.click()
            box = page.locator('.image-workspace__resize').nth(2).bounding_box()
            x, y = box['x'] + box['width'] / 2, box['y'] + box['height'] / 2
            count = page.evaluate('commands.length')
            width = image.get_attribute('width')
            page.mouse.move(x, y)
            page.mouse.down()
            page.mouse.move(x + 30, y + 30, steps=3)
            page.keyboard.press('Escape')
            page.mouse.up()
            expect(image).to_have_attribute('width', width)
            assert page.evaluate('commands.length') == count
            # Failed writes restore the image and show an error.
            image.click()
            page.evaluate('window.rejectSave = true')
            page.locator('.image-workspace__resize').nth(2).focus()
            page.keyboard.press('ArrowRight')
            expect(page.locator('.image-workspace__status')).to_have_attribute('role', 'alert')
            expect(image).to_have_attribute('width', width)
            assert not errors, errors
            browser.close()
            print('Scene image resize browser checks passed.')
    finally:
        server.shutdown()
        server.server_close()
        thread.join()


if __name__ == '__main__':
    main()
