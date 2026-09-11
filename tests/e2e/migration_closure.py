"""Isolated GM/player browser fixture and integrated migration checks."""

import json
import os
import subprocess
import sys
import tempfile
import time
from pathlib import Path
from urllib.request import urlopen

from maps import port
from playwright.sync_api import sync_playwright

ROOT = Path(__file__).resolve().parents[2]


def wait_for_server_exit(server):
    """Reap an owned test server even when Daphne outlives its shutdown grace."""
    try:
        server.wait(timeout=10)
    except subprocess.TimeoutExpired:
        server.kill()
        server.wait()


def main(effects_check=None, *, seed_extra="", environment=None, server_count=1):
    output = ROOT / "test-results/migration-closure"
    output.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix="grave-prefetch-") as temp:
        env = {
            **os.environ,
            "GRAVEWRIGHT_DATABASE": temp + "/db.sqlite3",
            "GRAVEWRIGHT_MEDIA_ROOT": temp + "/media",
        }
        if environment:
            env.update(environment(temp))
        subprocess.run(
            [sys.executable, "manage.py", "migrate", "--noinput"],
            cwd=ROOT,
            env=env,
            check=True,
            stdout=subprocess.DEVNULL,
        )
        seed = """
import os,json
os.environ.setdefault('DJANGO_SETTINGS_MODULE','config.settings')
import django;django.setup()
from django.test import Client
from django.conf import settings
from django.core.files.base import ContentFile
from gravewright.accounts.models import User
from gravewright.campaigns.models import Campaign,Membership
from gravewright.maps.models import Scene,Tile,Broadcast
from gravewright.maps.services import DEFAULTS
from PIL import Image
from io import BytesIO
owner=User.objects.create_user('gm@example.test','password-123',name='GM',role='owner')
player=User.objects.create_user('player@example.test','password-123',name='Player')
c=Campaign.objects.create(owner=owner,name='Prefetch')
Membership.objects.create(campaign=c,user=owner,role='gm');Membership.objects.create(campaign=c,user=player)
# The shared fixture represents users who have completed the introduction.
from gravewright.campaigns.models import Onboarding
from django.utils import timezone
for membership in c.memberships.all():Onboarding.objects.create(membership=membership,dismissed=True,player_shown_at=timezone.now())
s=Scene.objects.create(campaign=c,name='Grid',width=4096,height=4096,max_lod=3,settings={**DEFAULTS,'initialView':{'x':0,'y':0,'scale':1}})
Broadcast.objects.create(campaign=c,scene=s)
for lod in range(4):
 for y in range(8//2**lod):
  for x in range(8//2**lod):
   buf=BytesIO();Image.new('RGB',(512,512),(40+x*20,40+y*20,80)).save(buf,'WEBP')
   tile=Tile(scene=s,lod=lod,x=x,y=y);tile.file.save(f'{lod}-{x}-{y}.webp',ContentFile(buf.getvalue()),save=True)
from gravewright.journals.models import Journal
journal=Journal.objects.create(campaign=c,creator=owner,title='Temporary handout',data={'sections':[]})
result={'journal':str(journal.pk),'player_id':str(player.pk),'campaign':str(c.pk),'map':str(s.pk),'cookie':settings.SESSION_COOKIE_NAME}
for key,user in [('gm',owner),('player',player)]:
 client=Client();client.force_login(user);result[key]=client.session.session_key
print(json.dumps(result))
"""
        if seed_extra:
            seed = seed.replace("print(json.dumps(result))", seed_extra + "\nprint(json.dumps(result))")
        data = json.loads(
            subprocess.check_output(
                [sys.executable, "-c", seed], cwd=ROOT, env=env, text=True
            )
        )
        bases = [f"http://127.0.0.1:{port()}" for _ in range(server_count)]
        base = bases[0]
        with (output / "server.log").open("w") as log:
            def start(index):
                process=subprocess.Popen([sys.executable,"manage.py","runserver",bases[index].removeprefix("http://"),"--noreload"],cwd=ROOT,env=env,stdout=log,stderr=log)
                return process
            servers=[]
            def ready(index):
                for _ in range(100):
                    try:
                        urlopen(bases[index],timeout=1).close();return
                    except OSError:time.sleep(.1)
                raise RuntimeError('ASGI process failed to start')
            def restart(index):
                servers[index].terminate()
                wait_for_server_exit(servers[index])
                servers[index]=start(index);ready(index)
            try:
                for index in range(server_count):servers.append(start(index))
                for index in range(server_count):ready(index)
                with sync_playwright() as pw:
                    browser = pw.chromium.launch()
                    pages = []
                    errors = []
                    requests = []
                    for role in ("gm", "player"):
                        ctx = browser.new_context(
                            viewport={"width": 1440, "height": 1000}
                        )
                        ctx.add_cookies(
                            [{"name": data["cookie"], "value": data[role], "url": base}]
                        )
                        ctx.add_init_script(
                            "window.streamEvents=[];window.sockets=[];const Native=window.WebSocket;window.WebSocket=class extends Native{constructor(...args){super(...args);window.sockets.push(this)}};for(const kind of ['scene.viewport.ready','scene.gm_prefetch.hint'])window.addEventListener('gravewright:'+kind,e=>window.streamEvents.push({kind,...e.detail}));"
                        )
                        page = ctx.new_page()
                        pages.append(page)
                        page.on(
                            "pageerror",
                            lambda e: (
                                errors.append(str(e)),
                                print("PAGE ERROR:", str(e), flush=True),
                            ),
                        )
                        if role == "player":
                            page.on(
                                "request",
                                lambda r: (
                                    requests.append(r.url)
                                    if "/tiles/" in r.url
                                    else None
                                ),
                            )
                        page.goto(bases[min(len(pages)-1,len(bases)-1)] + "/game/" + data["campaign"])
                        page.wait_for_function(
                            "window.gravewrightMaps?.board?.viewport()?.scale === 1"
                        )
                        page.wait_for_function(
                            "streamEvents.some(e=>e.kind==='scene.viewport.ready')"
                        )
                    gm, player = pages
                    if effects_check:
                        if server_count>1:effects_check(gm,player,data,output,restart)
                        else:effects_check(gm, player, data, output)
                        assert not errors, errors
                        browser.close()
                        return
                    from io import BytesIO

                    from PIL import Image
                    from playwright.sync_api import expect

                    gm.get_by_role("button", name="Draw", exact=True).first.click()
                    expect(gm.locator(".drawing-paint")).to_be_visible()
                    gm.mouse.move(400, 300)
                    gm.mouse.down()
                    gm.mouse.move(520, 370, steps=8)
                    gm.mouse.up()
                    gm.wait_for_function(
                        "async id => (await (await fetch('/api/maps/'+id+'/state')).json()).drawings.rows.length === 1",
                        arg=data["map"],
                    )
                    gm.get_by_role("button", name="Close drawing").click()
                    gm.get_by_role("button", name="Measure", exact=True).first.click()
                    expect(gm.locator(".measure-panel")).to_be_visible()
                    gm.mouse.move(400, 300)
                    gm.mouse.down()
                    gm.mouse.move(650, 300, steps=5)
                    gm.mouse.up()
                    expect(gm.locator(".measurement-workspace text")).to_have_count(1)
                    gm.get_by_role("button", name="Close measurement").click()
                    gm.get_by_role("group", name="Layers", exact=True).get_by_role(
                        "button", name="Effects", exact=True
                    ).click()
                    gm.get_by_role("button", name="Particles", exact=True).click()
                    expect(gm.locator(".effect-picker")).to_be_visible()
                    gm.locator(".effect-picker").get_by_role(
                        "button", name="Close picker", exact=True
                    ).click()
                    gm.mouse.click(450, 330)
                    gm.wait_for_function(
                        "async id => (await (await fetch('/api/maps/'+id+'/state')).json()).particles.length === 1",
                        arg=data["map"],
                    )
                    gm.locator('[data-effect-kind="particle"]').first.dblclick()
                    expect(gm.locator(".effect-editor")).to_be_visible()
                    gm.locator(".effect-editor__header button").click()
                    gm.get_by_role("button", name="Shaders", exact=True).click()
                    expect(gm.locator(".effect-picker")).to_be_visible()
                    gm.locator(".effect-picker").get_by_role(
                        "button", name="Close picker", exact=True
                    ).click()
                    gm.mouse.click(750, 400)
                    gm.locator('[data-effect-kind="shader"]').first.dblclick()
                    expect(gm.locator(".effect-editor--shader")).to_be_visible()
                    source = gm.locator("#effect-shader-source").input_value()
                    gm.locator("#effect-shader-source").fill(
                        source + "\n// migrated editor"
                    )
                    gm.locator(".effect-editor__actions button").last.click()
                    gm.wait_for_function(
                        "async id => (await (await fetch('/api/maps/'+id+'/state')).json()).shaders[0]?.source.includes('migrated editor')",
                        arg=data["map"],
                    )
                    gm.locator(".effect-editor__header button").click()
                    gm.locator(".game-menubar__library").click()
                    expect(gm.locator(".asset-library")).to_be_visible()
                    content = BytesIO()
                    Image.new("RGB", (64, 64), "red").save(content, "PNG")
                    gm.locator(".asset-library input[type=file]").first.set_input_files(
                        {
                            "name": "marker.png",
                            "mimeType": "image/png",
                            "buffer": content.getvalue(),
                        }
                    )
                    expect(gm.locator(".asset-library__card")).to_have_count(1)
                    asset = gm.request.get(
                        base
                        + "/api/containers/"
                        + data["campaign"]
                        + "/library/asset-state"
                    ).json()["assets"][0]
                    gm.get_by_role("button", name="Close library", exact=True).click()
                    gm.evaluate(
                        "asset=>{const dt=new DataTransfer();dt.setData('application/x-gravewright-library-image',asset);const el=document.elementFromPoint(650,400);el.dispatchEvent(new DragEvent('drop',{bubbles:true,clientX:650,clientY:400,dataTransfer:dt}));}",
                        asset["id"],
                    )
                    gm.wait_for_function(
                        "async id => (await (await fetch('/api/maps/'+id+'/state')).json()).images.length === 1",
                        arg=data["map"],
                    )
                    assert player.request.get(base + asset["src"]).status == 200
                    gm.get_by_role("button", name="Journals", exact=True).click()
                    gm.get_by_role(
                        "button", name="Temporary handout", exact=True
                    ).click()
                    gm.get_by_role("button", name="Present journal", exact=True).click()
                    gm.locator("[data-presentation] select").select_option(
                        data["player_id"]
                    )
                    gm.locator("[data-presentation]").get_by_role(
                        "button", name="Present", exact=True
                    ).click()
                    expect(player.locator(".journal-window")).to_be_visible()
                    expect(player.locator(".journal-window [data-title]")).to_have_text(
                        "Temporary handout"
                    )
                    expect(
                        player.locator(".journal-window [data-action=present]")
                    ).to_be_hidden()
                    assert (
                        player.request.get(
                            base + "/api/containers/" + data["campaign"] + "/journals"
                        ).json()["journals"]
                        == []
                    )
                    gm.evaluate(
                        "id=>sockets.at(-1).send(JSON.stringify({type:'chat.say',payload:{requestId:crypto.randomUUID(),text:'/w Player hidden greeting',mapId:id}}))",
                        data["map"],
                    )
                    expect(player.locator(".chat-message--whisper")).to_contain_text(
                        "hidden greeting"
                    )
                    gm.screenshot(path=str(output / "tools-and-handout.png"))
                    assert not errors, errors
                    print("Closure tools browser checks passed")
                    browser.close()
            finally:
                for server in servers:
                    server.terminate()
                for server in servers:
                    wait_for_server_exit(server)


if __name__ == "__main__":
    main()
