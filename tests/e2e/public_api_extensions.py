"""Exercise public API 1.2 with owned files and disposable GM/player campaigns."""
from __future__ import annotations

import argparse
from datetime import datetime, timezone
from io import BytesIO
import json
import os
from pathlib import Path
import socket
import subprocess
import sys
import time
import traceback
from urllib.request import urlopen

from map_builder import ROOT, fixture_environment
from pdf_field_actions import ROLL_PROBE, serve as serve_pdf


def serve(fixture, port):
    from django.core import management
    original = management.call_command

    def command(name, *args, **kwargs):
        if name == "runserver":
            from django.core.files.base import ContentFile
            from gravewright.actors.models import Actor
            from gravewright.campaigns.models import Campaign, Membership
            from gravewright.maps.models import MapAsset
            from PIL import Image

            seed_file = fixture / "seed.json"
            seed = json.loads(seed_file.read_text(encoding="utf-8"))
            actor = Actor.objects.get(pk=seed["actor"])
            campaign = Campaign.objects.create(owner=actor.campaign.owner, name="Other API test campaign",
                                               system="gravewright-pdf-system")
            Membership.objects.create(campaign=campaign, user=campaign.owner, role="gm")
            foreign_actor = Actor.objects.create(campaign=campaign, name="Foreign API character")
            foreign_asset = MapAsset(campaign=campaign, name="Foreign API image", width=8, height=8)
            with Image.new("RGB", (8, 8), "#8080ff") as image, BytesIO() as output:
                image.save(output, "PNG")
                foreign_asset.file.save("foreign-api-image.png", ContentFile(output.getvalue()), save=True)
            seed.update(otherCampaign=str(campaign.pk), foreignActor=str(foreign_actor.pk),
                        foreignAsset=str(foreign_asset.pk))
            seed_file.write_text(json.dumps(seed, indent=2), encoding="utf-8")
        return original(name, *args, **kwargs)

    management.call_command = command
    try:
        serve_pdf(fixture, port)
    finally:
        management.call_command = original


def check_browser(base, seed, output, executable):
    from playwright.sync_api import expect, sync_playwright
    records, errors, dialogs, failed = [], [], [], []
    with sync_playwright() as playwright:
        browser = playwright.chromium.launch(**({"executable_path": str(executable)} if executable else {}))
        contexts = []

        def client(role):
            context = browser.new_context(base_url=base, viewport={"width": 1440, "height": 1000})
            contexts.append(context)
            context.add_init_script(ROLL_PROBE)
            context.add_cookies([{**seed["sessions"][role], "url": base}])
            page = context.new_page()
            page.on("pageerror", lambda error: errors.append(str(error)))
            page.on("requestfailed", lambda request: failed.append({"url": request.url, "error": request.failure}))

            def native_dialog(dialog):
                dialogs.append({"type": dialog.type, "message": dialog.message})
                dialog.dismiss()

            page.on("dialog", native_dialog)
            response = page.goto(f"{base}/game/{seed['campaign']}")
            assert response.ok, response.status
            page.wait_for_function("!!window.gravewright && !!window.gravewrightRealtime && !!window.gravewrightMaps")
            expect(page.locator(".game-menubar__presence")).to_have_attribute("data-presence", "seated")
            page.evaluate("seed=>{window.__apiSeed=seed;window.__api=window.gravewright.forTable(seed.campaign);}", seed)
            return page

        gm = player = None
        try:
            gm = client("gm")
            discovered = gm.evaluate("""() => {
              const capabilities=gravewright.capabilities(),api=window.__api;
              const value={version:gravewright.version,context:api.context,
                domains:Object.keys(capabilities.domains),binary:capabilities.binary.maps};
              capabilities.domains.mapBuilder.save='changed';
              value.isolated=gravewright.capabilities().domains.mapBuilder.save==='save';
              return value;
            }""")
            assert discovered["version"] == "1.2.0" and discovered["isolated"], discovered
            assert {"mapBuilder", "blueprints", "library", "system"} <= set(discovered["domains"])
            assert discovered["context"]["tableId"] == seed["campaign"]
            records.append({"case": "capabilities-discovery-and-table-bound-api-1-2"})

            result = gm.evaluate("""async () => {
              const other=gravewright.forTable(__apiSeed.otherCampaign),foreign=await other.actors.list();
              let denied;try{await __api.library.download({id:__apiSeed.foreignAsset});}catch(error){denied=error.code;}
              return {foreign:foreign.map(row=>row.id),denied,current:__api.context.tableId};
            }""")
            assert result["foreign"] == [seed["foreignActor"]] and result["denied"] == "not_found", result
            assert result["current"] == seed["campaign"]
            records.append({"case": "for-table-switch-and-foreign-binary-id-remain-campaign-scoped"})

            result = gm.evaluate("""async () => {
              const folder=await __api.library.createFolder({name:'Synthetic API assets'}),canvas=document.createElement('canvas');
              canvas.width=32;canvas.height=16;canvas.getContext('2d').fillStyle='#428562';canvas.getContext('2d').fillRect(0,0,32,16);
              const blob=await new Promise(resolve=>canvas.toBlob(resolve,'image/png'));
              const uploaded=await __api.library.upload({file:new File([blob],'synthetic-api.png',{type:'image/png'}),folderId:folder.id});
              const downloaded=await __api.library.download({id:uploaded.id});
              const bitmap=await createImageBitmap(downloaded.blob),width=bitmap.width,height=bitmap.height;bitmap.close();
              window.__apiUploaded=uploaded.id;
              return {width,height,size:downloaded.size,type:downloaded.contentType,folder:folder.id,
                row:(await __api.library.state()).assets.find(row=>row.id===uploaded.id)};
            }""")
            assert (result["width"], result["height"], result["type"]) == (32, 16, "image/png"), result
            assert result["size"] > 0 and result["row"]["folder_id"] == result["folder"]
            records.append({"case": "binary-library-upload-download-returns-blob-and-native-image"})

            result = gm.evaluate("""async () => {
              const projectId=crypto.randomUUID(),document={schemaVersion:2,name:'Synthetic API room',columns:2,rows:2,
                cellSize:32,background:'#112233',assets:[],floors:[],walls:[],doors:[]};
              const saved=await __api.mapBuilder.save({projectId,expectedVersion:0,document});
              const read=await __api.mapBuilder.read({projectId}),state=await __api.mapBuilder.state();
              const generated=await __api.mapBuilder.generate({projectId,expectedVersion:saved.project.version});
              const adopted=await __api.mapBuilder.adopt({sceneId:generated.scene.id,expectedSceneVersion:generated.scene.version});
              const network=await __api.blueprints.state({sceneId:generated.scene.id}),templates=await __api.blueprints.templates();
              window.__apiGenerated=generated.scene.id;
              return {same:read.project.document.name===document.name,listed:state.projects.some(row=>row.id===projectId),
                generated:generated.scene,adopted:adopted.project.sceneId,network:network.sceneId,templates:templates.templates.length};
            }""")
            assert result["same"] and result["listed"] and result["generated"]["width"] == 64, result
            assert result["generated"]["visibility"] == "gm" and result["adopted"] == result["generated"]["id"], result
            records.append({"case": "map-builder-save-read-generate-adopt-and-blueprint-catalogs"})

            result = gm.evaluate("""async () => {
              const canvas=document.createElement('canvas');canvas.width=canvas.height=32;
              canvas.getContext('2d').fillStyle='#16324f';canvas.getContext('2d').fillRect(0,0,32,32);
              const portable={format:.2,resolution:{map_origin:{x:0,y:0},map_size:{x:1,y:1},pixels_per_grid:32},
                line_of_sight:[],objects_line_of_sight:[],portals:[],lights:[],
                environment:{baked_lighting:false,ambient_light:'ffffffff'},image:canvas.toDataURL('image/png').split(',')[1]};
              const payload={file:new File([JSON.stringify(portable)],'synthetic-api.uvtt',{type:'application/json'}),
                name:'Synthetic imported API room',builderEditable:true},options={requestId:crypto.randomUUID()};
              const first=await __api.maps.importUniversalVtt(payload,options),retry=await __api.maps.importUniversalVtt(payload,options);
              const exported=await __api.maps.exportUniversalVtt({sceneId:first.scene.id});
              return {same:first.scene.id===retry.scene.id,editable:first.builderEditable,width:first.scene.width,
                format:exported.document.format,image:exported.document.image.length};
            }""")
            assert result["same"] and result["editable"] and result["width"] == 32 and result["format"] == .2, result
            assert result["image"] > 0
            records.append({"case": "binary-uvtt-import-native-retry-and-json-export"})

            result = gm.evaluate("""async () => {
              const before=await __api.system.state(),view=await __api.system.call('pdf.read',{actorId:__apiSeed.actor});
              const field='manual_'+__apiSeed.manualFields[0].id.replaceAll('-','');
              const action={field,roll:{formula:'1d1 + @value',label:'Synthetic API roll'}};
              await __api.system.call('pdf.configure',{actorId:view.id,source:view.source,version:view.version,
                sheetVersion:view.sheetVersion,changes:{fieldActions:[action]}});
              const after=await __api.system.call('pdf.read',{actorId:view.id});window.__apiPdfView=after;
              return {system:before.systemId,operations:before.operations.map(row=>row.name),
                value:after.data.fields[field],label:after.data.pdf.fieldActions[0].roll.label};
            }""")
            assert result["system"] == "gravewright-pdf-system" and "pdf.configure" in result["operations"], result
            assert result["value"] == 10 and result["label"] == "Synthetic API roll", result
            records.append({"case": "system-capabilities-pdf-read-and-configure-preserve-current-values"})

            result = gm.evaluate("""async () => {
              const bundle=await __api.system.call('pdf.exportMapping',{actorId:__apiSeed.actor});
              const created=await __api.system.call('pdf.templates.create',{name:'Synthetic API mapping',bundle});
              const read=await __api.system.call('pdf.templates.read',{id:created.id});
              const updated=await __api.system.call('pdf.templates.update',{id:created.id,revision:read.revision,
                name:'Renamed API mapping',bundle});
              const exported=await __api.system.call('pdf.templates.export',{id:created.id});
              const imported=await __api.system.call('pdf.templates.import',{name:'Imported API mapping',bundle:JSON.stringify(exported)});
              const listed=await __api.system.call('pdf.templates.list');
              await __api.system.call('pdf.templates.delete',{id:created.id,revision:updated.revision});
              await __api.system.call('pdf.templates.delete',{id:imported.id,revision:imported.revision});
              return {read:read.name,updated:updated.name,listed:listed.items.length,
                final:(await __api.system.call('pdf.templates.list')).items.length,
                containsValues:JSON.stringify(exported).includes('Aster'),manualCount:exported.manualFields.length};
            }""")
            assert result["read"] == "Synthetic API mapping" and result["updated"] == "Renamed API mapping", result
            assert result["listed"] == 2 and result["final"] == 0 and not result["containsValues"] and result["manualCount"] == 2, result
            records.append({"case": "pdf-template-crud-json-import-export-omit-character-values"})

            player = client("player")
            result = player.evaluate("""async () => {
              const field='manual_'+__apiSeed.manualFields[0].id.replaceAll('-','');
              const rolled=await __api.system.call('pdf.roll',{actorId:__apiSeed.actor,field,
                source:'asset:'+__apiSeed.pdfAssets[0],mapId:__apiSeed.selectedScene},{requestId:crypto.randomUUID()});
              return {value:rolled.roll.result.value.value,label:rolled.roll.label};
            }""")
            assert result["value"] == 11 and result["label"] == "Synthetic API roll", result
            player.wait_for_function("window.__pdfActionRolls.some(row=>row.roll?.label==='Synthetic API roll')")
            records.append({"case": "player-system-roll-uses-current-authorized-field-and-publishes-native-chat"})

            result = player.evaluate("""async () => {
              const errors={};for (const [name,operation] of [
                ['builder',()=>__api.mapBuilder.state()],['library',()=>__api.library.createFolder({name:'Forbidden'})],
                ['templates',()=>__api.system.call('pdf.templates.list')],
                ['configure',async()=>{const view=await __api.system.call('pdf.read',{actorId:__apiSeed.actor});
                  return __api.system.call('pdf.configure',{actorId:view.id,source:view.source,version:view.version,
                    sheetVersion:view.sheetVersion,changes:{fieldActions:[]}});}],
                ['otherTable',()=>gravewright.forTable(__apiSeed.otherCampaign).actors.list()],
              ]) {try{await operation();errors[name]='accepted';}catch(error){errors[name]=error.code;}}
              return errors;
            }""")
            assert set(result.values()) == {"permission_denied"}, result
            records.append({"case": "player-denied-gm-capabilities-configuration-and-foreign-table"})

            result = gm.evaluate("""async () => {
              const controller=new AbortController();controller.abort();const result={};
              for(const [name,operation] of [['json',()=>__api.mapBuilder.state({}, {signal:controller.signal})],
                ['binary',()=>__api.library.download({id:__apiUploaded},{signal:controller.signal})]]) {
                try{await operation();result[name]='accepted';}catch(error){result[name]=error.code;}
              }return result;
            }""")
            assert result == {"json": "cancelled", "binary": "cancelled"}, result
            records.append({"case": "explicit-cancellation-propagates-through-json-and-binary-api"})

            result = gm.evaluate("""async () => {
              await __api.maps.navigate({mapId:__apiGenerated});
              const privateState=await __api.maps.state();
              const bound=gravewright.forTable(__apiSeed.campaign,{sceneId:__apiGenerated});
              let boundNull;try{await bound.maps.navigate({mapId:null});boundNull='accepted';}
                catch(error){boundNull=error.code;}
              const unchanged=await __api.maps.state();
              await __api.maps.navigate({mapId:null});
              const followed=await __api.maps.state();
              return {private:privateState.navigatingMapId,target:__apiGenerated,
                boundNull,unchanged:unchanged.navigatingMapId,
                followed:followed.navigatingMapId,broadcast:followed.activeMapId};
            }""")
            assert result['boundNull'] == 'stale_context' and result['unchanged'] == result['target'], result
            assert result["private"] == result["target"] and result["followed"] == result["broadcast"] == seed["selectedScene"], result
            records.append({"case": "bound-null-navigation-rejected-and-unbound-null-resumes-broadcast"})

            result = gm.evaluate("""async () => {
              const status=await gravewright.accounts.status(),session=await gravewright.accounts.session();
              const invitation=await gravewright.campaigns.invitationStatus(__apiSeed.campaign);
              const snapshots=await gravewright.administration.snapshots(__apiSeed.campaign);
              return {status:typeof status,session:typeof session,invitation:typeof invitation,snapshots:typeof snapshots};
            }""")
            assert all(value == "object" for value in result.values()), result
            records.append({"case": "global-account-invitation-and-snapshot-adapters-read-native-owner-data"})
            gm.screenshot(path=str(output / "public-api-table.png"), full_page=True)
        except Exception:
            (output / "browser-diagnostics.json").write_text(json.dumps({"completedCases": records,
                "pageErrors": errors, "nativeDialogs": dialogs, "failedRequests": failed}, indent=2), encoding="utf-8")
            for name, page in (("gm", gm), ("player", player)):
                if page:
                    page.screenshot(path=str(output / f"failure-{name}.png"), full_page=True)
            raise
        finally:
            for context in contexts:
                context.close()
            browser.close()
    assert not errors, errors
    assert not dialogs, dialogs
    assert not [request for request in failed if request["error"] != "net::ERR_ABORTED"], failed
    return {"passed": True, "cases": records, "pageErrors": errors, "nativeDialogs": dialogs, "failedRequests": failed,
            "assets": "Generated synthetic image/UVTT files, synthetic PDF fields and two disposable campaigns."}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path)
    parser.add_argument("--browser-executable", type=Path)
    parser.add_argument("--serve", action="store_true", help=argparse.SUPPRESS)
    parser.add_argument("--fixture", type=Path, help=argparse.SUPPRESS)
    parser.add_argument("--port", type=int, default=0, help=argparse.SUPPRESS)
    args = parser.parse_args()
    if args.serve:
        serve(args.fixture, args.port)
        return
    output = (args.output or ROOT / "data/public-api-extensions" /
              datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S%fZ")).resolve()
    if output.exists() and any(output.iterdir()):
        raise RuntimeError("Use a fresh, empty output directory.")
    output.mkdir(parents=True, exist_ok=True)
    fixture = output / "fixture"
    fixture.mkdir()
    with socket.socket() as connection:
        connection.bind(("127.0.0.1", 0))
        port = connection.getsockname()[1]
    fixture_environment(fixture, port)
    executable = sys._base_executable if os.name == "nt" else sys.executable
    command = [executable, "-B", "-X", "utf8", str(Path(__file__).resolve())]
    base = f"http://127.0.0.1:{port}"
    with (output / "server.log").open("w", encoding="utf-8") as log:
        server = subprocess.Popen([*command, "--serve", "--fixture", str(fixture), "--port", str(port)],
                                  cwd=ROOT, env=os.environ.copy(), stdout=log, stderr=log)
        try:
            for _ in range(300):
                if server.poll() is not None:
                    raise RuntimeError(f"Fixture exited; inspect {output / 'server.log'}")
                try:
                    with urlopen(base, timeout=1):
                        break
                except OSError:
                    time.sleep(.1)
            else:
                raise RuntimeError("Fixture did not become ready.")
            seed = json.loads((fixture / "seed.json").read_text(encoding="utf-8"))
            report = check_browser(base, seed, output, args.browser_executable)
            (output / "report.json").write_text(json.dumps(report, indent=2), encoding="utf-8")
            print(json.dumps({"passed": True, "cases": len(report["cases"]), "report": str(output / "report.json")}))
        except Exception:
            (output / "failure.txt").write_text(traceback.format_exc(), encoding="utf-8")
            raise
        finally:
            server.terminate()
            try:
                server.wait(timeout=10)
            except subprocess.TimeoutExpired:
                server.kill()
                server.wait()
            (output / "server-exit.json").write_text(json.dumps({"pid": server.pid, "exitCode": server.returncode}), encoding="utf-8")


if __name__ == "__main__":
    main()
