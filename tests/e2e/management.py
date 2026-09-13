"""Inside administration and signed module runtime using isolated native services."""

from migration_closure import main
from playwright.sync_api import expect

SEED = r'''
import base64,hashlib,zipfile
from pathlib import Path
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
from gravewright.modules.packages import ModulePackages,canonical
key=Ed25519PrivateKey.generate()
keys={'test':base64.b64encode(key.public_key().public_bytes_raw()).decode()}
Path(os.environ['GRAVEWRIGHT_MARKETPLACE_KEYS_FILE']).write_text(json.dumps(keys))
manifest={'id':'example.probe','name':'Runtime probe','description':'Browser integration test','version':'1.0.0','sdk':{'requires':'>=1.0.0 <2.0.0','tested':'1.0.0'},'entry':'main.js','author':'Test','license':'MIT'}
code="""export default {async start(ctx){window.moduleStarts=(window.moduleStarts||0)+1;},register(reg){reg.register('actor.directory',async block=>{const p=document.createElement('p');p.dataset.moduleProbe='true';p.textContent='Signed module active';block.root.append(p);const value=await block.host.call('actor.list',{});p.dataset.actorCount=String(value.items.length);});reg.register('scene.overlay',block=>{const p=document.createElement('span');p.dataset.overlayProbe=block.context.sceneId;const at=block.viewport.sceneToViewport({x:70,y:70});p.textContent=at.x+','+at.y;block.root.append(p);});},stop(){window.moduleStops=(window.moduleStops||0)+1;}};"""
out=BytesIO()
with zipfile.ZipFile(out,'w') as z:z.writestr('manifest.json',json.dumps(manifest));z.writestr('main.js',code)
raw=out.getvalue();record={'id':manifest['id'],'version':'1.0.0','sdk':manifest['sdk']['requires'],'download':'https://example.test/probe.zip','sha256':hashlib.sha256(raw).hexdigest(),'keyId':'test'}
record['signature']=base64.b64encode(key.sign(canonical(record))).decode()
ModulePackages(Path(settings.MEDIA_ROOT)/'modules',keys).install(record,raw)
'''


def check(gm, player, data, output):
    base = gm.url.split("/game/")[0]
    gm.get_by_role("button", name="Settings", exact=True).click()
    gm.get_by_role("button", name="Extensions", exact=True).click()
    expect(gm.get_by_text("Runtime probe", exact=True)).to_be_visible()
    gm.get_by_role("button", name="Activate", exact=True).click()
    gm.wait_for_function("window.moduleStarts===1")
    player.wait_for_function("window.moduleStarts===1")
    gm.keyboard.press("Escape")
    gm.get_by_role("button", name="Actors", exact=True).click()
    expect(gm.locator("[data-module-probe]")).to_be_visible()
    expect(gm.locator("[data-module-probe]")).to_have_attribute("data-actor-count", "0")
    expect(gm.locator("[data-overlay-probe]")).to_have_attribute(
        "data-overlay-probe", data["map"]
    )
    gm.screenshot(path=str(output / "module-active.png"))
    gm.get_by_role("button", name="Settings", exact=True).click()
    gm.get_by_role("button", name="Deactivate", exact=True).click()
    expect(gm.locator("[data-module-probe]")).to_have_count(0)
    player.wait_for_function("window.moduleStops>=1")
    print(
        "Signed module activation, SDK call, overlay and two-peer cleanup passed",
        flush=True,
    )
    player.goto(base + "/inside")
    gm.goto(base + "/inside?section=addons")
    expect(
        gm.get_by_role("heading", name="Modules", exact=True)
    ).to_be_visible()
    expect(gm.get_by_text("Runtime probe", exact=True)).to_be_visible()
    gm.goto(base + "/inside?section=administration")
    expect(gm.get_by_role("heading", name="Administration", exact=True)).to_be_visible()
    gm.get_by_role("button", name="diagnostics", exact=True).click()
    expect(gm.get_by_role("heading", name="database", exact=True)).to_be_visible()
    gm.get_by_role("button", name="updates", exact=True).click()
    gm.get_by_label("Release channel").select_option("testing")
    gm.get_by_role("button", name="Save channel", exact=True).click()
    expect(gm.locator("[data-administration]")).to_have_attribute("aria-busy", "false")
    expect(gm.get_by_label("Release channel")).to_have_value("testing")
    assert (
        gm.evaluate(
            "async()=> (await(await fetch('/api/admin/status')).json()).updates.channel"
        )
        == "testing"
    )
    gm.screenshot(path=str(output / "administration-updates.png"))
    gm.goto(base + "/inside")
    gm.get_by_role("button", name="Table options", exact=True).click()
    gm.get_by_role("button", name="Backup", exact=True).click()
    expect(gm.get_by_role("heading", name="Copies · Prefetch")).to_be_visible()
    gm.get_by_role("button", name="Create snapshot", exact=True).click()
    expect(gm.get_by_text("Before the next session", exact=True)).to_be_visible()
    gm.get_by_role("button", name="Restore", exact=True).click()
    gm.get_by_label("Type RESTORE").fill("RESTORE")
    gm.get_by_role("button", name="Confirm", exact=True).click()
    expect(gm.locator("[data-confirm]")).to_be_hidden(timeout=15000)
    with gm.expect_download() as download:
        gm.get_by_text("Export portable campaign ZIP", exact=True).click()
    path = output / "campaign-export.zip"
    download.value.save_as(str(path))
    gm.get_by_role("button", name="Close", exact=True).click()
    gm.goto(base + "/inside?section=administration")
    gm.locator("[name=archive]").set_input_files(path)
    gm.locator("[data-form=import] [name=title]").fill("Imported through Inside")
    gm.get_by_role("button", name="Import campaign", exact=True).click()
    expect(
        gm.get_by_role("heading", name="Imported through Inside", exact=True)
    ).to_be_visible(timeout=15000)
    print(
        "Inside modules, administration, backup restore, export and import passed",
        flush=True,
    )


if __name__ == "__main__":
    main(
        check,
        seed_extra=SEED,
        environment=lambda temp: {
            "GRAVEWRIGHT_MARKETPLACE_KEYS_FILE": temp + "/keys.json"
        },
    )
