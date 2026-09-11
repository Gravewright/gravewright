"""Real GM/player sockets: scheduled viewport, speculative HTTP and blob reuse."""

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


def main():
    output = ROOT / "test-results/map-prefetch"
    output.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix="grave-prefetch-") as temp:
        env = {
            **{
                key: value
                for key, value in os.environ.items()
                if not key.startswith("GRAVEWRIGHT_GM_")
            },
            "GRAVEWRIGHT_DATABASE": temp + "/db.sqlite3",
            "GRAVEWRIGHT_MEDIA_ROOT": temp + "/media",
        }
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
s=Scene.objects.create(campaign=c,name='Grid',width=4096,height=4096,max_lod=3,settings={**DEFAULTS,'initialView':{'x':0,'y':0,'scale':1}})
Broadcast.objects.create(campaign=c,scene=s)
for lod in range(4):
 for y in range(8//2**lod):
  for x in range(8//2**lod):
   buf=BytesIO();Image.new('RGB',(512,512),(40+x*20,40+y*20,80)).save(buf,'WEBP')
   tile=Tile(scene=s,lod=lod,x=x,y=y);tile.file.save(f'{lod}-{x}-{y}.webp',ContentFile(buf.getvalue()),save=True)
result={'campaign':str(c.pk),'map':str(s.pk),'cookie':settings.SESSION_COOKIE_NAME}
for key,user in [('gm',owner),('player',player)]:
 client=Client();client.force_login(user);result[key]=client.session.session_key
print(json.dumps(result))
"""
        data = json.loads(
            subprocess.check_output(
                [sys.executable, "-c", seed], cwd=ROOT, env=env, text=True
            )
        )
        base = f"http://127.0.0.1:{port()}"
        with (output / "server.log").open("w") as log:
            server = subprocess.Popen(
                [
                    sys.executable,
                    "manage.py",
                    "runserver",
                    base.removeprefix("http://"),
                    "--noreload",
                ],
                cwd=ROOT,
                env=env,
                stdout=log,
                stderr=log,
            )
            try:
                for _ in range(100):
                    try:
                        urlopen(base, timeout=1).close()
                        break
                    except OSError:
                        time.sleep(0.1)
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
                        page.on("pageerror", lambda e: errors.append(str(e)))
                        if role == "player":
                            page.on(
                                "request",
                                lambda r: (
                                    requests.append(r.url)
                                    if "/tiles/" in r.url
                                    else None
                                ),
                            )
                        page.goto(base + "/game/" + data["campaign"])
                        page.wait_for_function(
                            "window.gravewrightMaps?.board?.viewport()?.scale === 1"
                        )
                        page.wait_for_function(
                            "streamEvents.some(e=>e.kind==='scene.viewport.ready')"
                        )
                    gm, player = pages
                    player.wait_for_timeout(1000)
                    gm.mouse.move(1200, 400)
                    gm.mouse.down(button="right")
                    gm.mouse.move(176, 400, steps=8)
                    gm.mouse.up(button="right")
                    player.wait_for_function(
                        "streamEvents.some(e=>e.kind==='scene.gm_prefetch.hint' && e.region.lastColumn >= 4)",
                        timeout=20000,
                    )
                    assert player.evaluate(
                        "streamEvents.filter(e=>e.kind==='scene.gm_prefetch.hint').every(e=>e.policy==='utility_per_byte')"
                    )
                    player.wait_for_timeout(1000)
                    warmed = [url for url in requests if "/tiles/0/4/" in url]
                    assert warmed, ("No speculative tile requested", requests)
                    counts = {url: requests.count(url) for url in warmed}
                    player.mouse.move(1200, 400)
                    player.mouse.down(button="right")
                    player.mouse.move(176, 400, steps=8)
                    player.mouse.up(button="right")
                    player.wait_for_timeout(1500)
                    assert all(
                        requests.count(url) == count for url, count in counts.items()
                    ), "Prefetched bytes were fetched again"
                    stats = player.evaluate("gravewrightMaps.board.streamingStats()")
                    assert stats["metrics"]["gm_hint_bytes_used"] > 0, stats
                    assert stats["metrics"]["gm_hint_promoted_to_visible"] > 0, stats
                    assert stats["gmHintBuckets"], stats
                    assert not errors, errors
                    # Reconnection recreates the server subscription from the board heartbeat.
                    before = player.evaluate(
                        "streamEvents.filter(e=>e.kind==='scene.viewport.ready').length"
                    )
                    player.evaluate(
                        "window.sockets.at(-1).close(4000, 'reconnect test')"
                    )
                    player.wait_for_function(
                        "n=>streamEvents.filter(e=>e.kind==='scene.viewport.ready').length > n",
                        arg=before,
                    )
                    report = {
                        "prefetched_tiles_reused": len(warmed),
                        "errors": errors,
                        "reconnected": True,
                        "telemetry": player.evaluate(
                            "gravewrightMaps.board.streamingStats()"
                        ),
                    }
                    (output / "result.json").write_text(json.dumps(report, indent=2))
                    print(json.dumps(report))
                    browser.close()
            finally:
                server.terminate()
                server.wait(timeout=10)


if __name__ == "__main__":
    main()
