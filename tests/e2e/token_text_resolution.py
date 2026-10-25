"""Token text stays sharp through zoom and dense displays without rebuilding on pan.

Run with the isolated migration_closure browser fixture.
"""

from migration_closure import main


def check(gm, player, data, output):
    for density in (1, 2):
        gm.evaluate("""async density => {
            const {PixiBoardRenderer} = await import('/static/gravewright_maps/runtime/widgets/game-board/lib/pixi-board-renderer.js');
            const {Application, Text} = await import('/static/gravewright_maps/vendor/pixi.js');
            const host = document.createElement('div');
            host.style.cssText = 'position:fixed;inset:0;z-index:99999;background:#303b33';
            document.body.append(host);
            const app = new Application();
            await app.init({width:1000,height:800,resolution:density,autoDensity:true,autoStart:false,antialias:true,background:'#303b33'});
            host.append(app.canvas);
            const board = new PixiBoardRenderer(app, 'Token text fixture');
            const piece = {key:'text',x:100,y:90,size:70,label:'b',accent:'#b89a5b',selected:true,
                conditions:[{label:'Danger',kind:'negative'}]};
            await board.setPieces([piece]);
            const figures = app.stage.children[0].children.find(layer => layer.children.some(root => root.children.some(child => child instanceof Text)));
            window.textFixture = {app,board,host,piece,figures,Text};
        }""", density)
        for zoom in (1, 1.5, 3.2, .35):
            result = gm.evaluate("""async zoom => {
                const {app,board,figures,Text} = textFixture;
                board.setViewport({x:30,y:30,scale:zoom});
                await new Promise(requestAnimationFrame);
                app.render();
                const root = figures.children[0];
                const texts = [...root.children.filter(child => child instanceof Text), ...root.children[3].children];
                const versions = texts.map(text => text._didViewChangeTick);
                board.setViewport({x:40,y:40,scale:zoom});
                const unchanged = texts.every((text,index) => text._didViewChangeTick === versions[index]);
                return {resolutions:texts.map(text => text.resolution),unchanged};
            }""", zoom)
            expected = next(value for value in (1, 2, 4, 8) if value >= max(1, zoom * density))
            assert result["resolutions"] == [expected] * 3, result
            assert result["unchanged"], "Panning invalidated token text"
            if zoom == 3.2:
                gm.screenshot(path=str(output / f"token-text-sharp-{density}.png"))
        gm.evaluate("""async () => {
            const {board,piece} = textFixture;
            board.setViewport({x:30,y:30,scale:3.2});
            await board.setPieces([{...piece,label:'Danger zone',conditions:[{label:'Safe',kind:'positive'}]}]);
        }""")
        gm.screenshot(path=str(output / f"token-text-density-{density}.png"))
        assert gm.evaluate("""() => {
            const {figures,Text} = textFixture;
            const root = figures.children[0];
            return root.children.find(child => child instanceof Text && child.text === 'Danger zone').resolution === (textFixture.app.renderer.resolution === 2 ? 8 : 4)
                && root.children[3].children[0].resolution === (textFixture.app.renderer.resolution === 2 ? 8 : 4);
        }""")
        gm.evaluate("""async () => {
            const {board,piece} = textFixture;
            await board.setPieces([{...piece,label:'Guardian',hovered:true,
                conditions:[{label:'Poisoned',kind:'negative'},{label:'Exhausted',kind:'negative'}]}]);
            await new Promise(requestAnimationFrame);
            textFixture.app.render();
        }""")
        gm.screenshot(path=str(output / f"token-text-conditions-{density}.png"))
        assert gm.evaluate("""() => {
            const {figures,Text} = textFixture;
            const label = figures.children[0].children.find(child => child instanceof Text && child.text.includes('Poisoned'));
            return label?.visible && label.text === 'Guardian\\nPoisoned, Exhausted'
                && label.style.lineHeight > label.style.fontSize;
        }"""), "Hovered token must show a readable second line"
        gm.evaluate("textFixture.board.destroy(); textFixture.host.remove(); delete window.textFixture")
    print("Token text: zoom, density, movement, changed labels and cleanup passed")


if __name__ == '__main__':
    main(check)
