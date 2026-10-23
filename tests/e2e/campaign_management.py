"""Create shared campaign journals before joining a table, using native editors."""
from __future__ import annotations

import argparse
from datetime import datetime, timezone
import json
import os
from pathlib import Path
import socket
import subprocess
import sys
import time
import traceback
from urllib.request import urlopen

from map_builder import ROOT, MEASURE, change_locale, fixture_environment
from pdf_manual_fields import serve as serve_pdf


DIARY_TITLE = "Synthetic chronicle with a deliberately long title for the campaign management interface"
QUEST_TITLE = "Synthetic quest with a deliberately long title about the abandoned northern observatory"
PUBLIC_TEXT = "The northern observatory awaits the expedition. " * 12
EDITED_TEXT = "The co-GM added a safe route through the eastern valley. " * 10
GM_SECRET = "MANAGEMENT_SYNTHETIC_SECRET: The observatory keeper is an illusion."
QUEST_SECRET = "MANAGEMENT_QUEST_SECRET: The patron planted the missing artifact."


def serve(fixture, port):
    from django.core import management
    original = management.call_command

    def command(name, *args, **kwargs):
        if name == "runserver":
            from io import BytesIO
            import wave
            from django.conf import settings
            from django.core.files.base import ContentFile
            from django.test import Client
            from gravewright.accounts.models import User
            from gravewright.actors.models import Actor
            from gravewright.audio.models import Track
            from gravewright.campaigns.models import Campaign, Membership, Onboarding
            from gravewright.journals.models import Journal

            seed_file = fixture / "seed.json"
            seed = json.loads(seed_file.read_text(encoding="utf-8"))
            actor = Actor.objects.get(pk=seed["actor"])
            cogm = User.objects.create_user("cogm@campaign-management.test", "synthetic-browser-pass", name="Synthetic co-GM")
            membership = Membership.objects.create(campaign=actor.campaign, user=cogm, role="gm")
            Onboarding.objects.create(membership=membership, dismissed=True)
            client = Client()
            client.force_login(cogm)
            seed["sessions"]["cogm"] = {"name": settings.SESSION_COOKIE_NAME,
                                          "value": client.cookies[settings.SESSION_COOKIE_NAME].value}
            foreign = Campaign.objects.create(owner=actor.campaign.owner, name="Unrelated synthetic campaign")
            document = Journal.objects.create(campaign=foreign, creator=foreign.owner, title="Foreign private document")
            audio_bytes = BytesIO()
            with wave.open(audio_bytes, 'wb') as audio:
                audio.setnchannels(1)
                audio.setsampwidth(2)
                audio.setframerate(8000)
                audio.writeframes(b'\0\0' * 8000 * 20)
            track = Track(campaign=actor.campaign, name='Synthetic local preview', content_type='audio/wav', duration=20)
            track.file.save('synthetic-preview.wav', ContentFile(audio_bytes.getvalue()), save=True)
            seed.update(otherCampaign=str(foreign.pk), foreignJournal=str(document.pk), cogm=str(cogm.pk),
                        previewTrack=str(track.pk))
            seed_file.write_text(json.dumps(seed, indent=2), encoding="utf-8")
        return original(name, *args, **kwargs)

    management.call_command = command
    try:
        serve_pdf(fixture, port)
    finally:
        management.call_command = original


def snapshot(fixture):
    import django
    django.setup()
    from gravewright.maps.models import Broadcast, SceneNavigation
    from gravewright.realtime.models import PresenceConnection

    campaign = json.loads((fixture / "seed.json").read_text(encoding="utf-8"))["campaign"]
    print(json.dumps({
        "broadcast": list(Broadcast.objects.filter(campaign_id=campaign).order_by("pk").values()),
        "navigation": list(SceneNavigation.objects.filter(membership__campaign_id=campaign).order_by("pk").values()),
        "presence": list(PresenceConnection.objects.filter(membership__campaign_id=campaign).order_by("pk").values()),
    }, default=str, sort_keys=True))


def revoke_fixture_gm(fixture):
    import django
    django.setup()
    from gravewright.campaigns.models import Membership

    seed = json.loads((fixture / 'seed.json').read_text(encoding='utf-8'))
    updated = Membership.objects.filter(campaign_id=seed['campaign'], user_id=seed['cogm'], role='gm').update(role='player')
    assert updated == 1, 'The disposable co-GM membership must exist.'


def check_browser(base, seed, output, executable, read_snapshot, revoke_gm):
    from playwright.sync_api import expect, sync_playwright

    records, errors, dialogs, failed = [], [], [], []
    campaign = seed["campaign"]
    management_path = f"/campaigns/{campaign}/manage"
    management_api = f"/api/containers/{campaign}/management"
    before = read_snapshot()
    (output / "control-before.json").write_text(json.dumps(before, indent=2), encoding="utf-8")
    with sync_playwright() as playwright:
        browser = playwright.chromium.launch(**({"executable_path": str(executable)} if executable else {}))
        contexts, pages, sockets = [], {}, {}

        def client(role, *, manage=True):
            context = browser.new_context(base_url=base, viewport={"width": 1440, "height": 1000})
            contexts.append(context)
            context.add_cookies([{**seed["sessions"][role], "url": base}])
            page = context.new_page()
            pages[role] = page
            sockets[role] = []
            page.on("websocket", lambda socket: sockets[role].append(socket.url))
            page.on("pageerror", lambda error: errors.append(error.stack or str(error)))
            page.on("requestfailed", lambda request: failed.append({"url": request.url, "error": request.failure}))

            def native_dialog(dialog):
                dialogs.append({"type": dialog.type, "message": dialog.message})
                dialog.dismiss()

            page.on("dialog", native_dialog)
            if manage:
                response = page.goto(base + '/inside')
                assert response.ok, (role, response.status)
                entry = page.locator(f'a[href="{management_path}"]')
                expect(entry).to_be_visible()
                page.screenshot(path=str(output / f'campaign-entry-{role}-1440.png'), full_page=True)
                entry.click()
                expect(page).to_have_url(base + management_path)
                expect(page.locator('#table-workspace[data-management="true"]')).to_be_visible()
                page.wait_for_function("!!window.gravewright && !!window.gravewrightRealtime && !!window.gravewrightJournals")
                expect(page.locator('#table-workspace')).to_have_attribute('data-manager-ready', 'true')
                assert not sockets[role], (role, sockets[role])
                assert page.locator('.game-table__stage canvas').count() == 0
            return page

        def nav(page, section):
            page.locator(f'[data-manager-section="{section}"]').click()

        def create(page, kind, title):
            nav(page, "overview")
            page.locator(f'[data-manager-create="{kind}"]:visible').click()
            dialog = page.locator(f'.table-form-modal[data-window-key="manager-create-{kind}"]')
            expect(dialog).to_be_visible()
            dialog.locator('[name=title]').fill(title)
            dialog.locator('[type=submit]').click()
            window = page.locator(f'.journal-window[data-journal-type="{kind}"]')
            expect(window).to_be_visible()
            return window, window.get_attribute("data-journal-id")

        def flush(page, window, document_id):
            assert page.evaluate("id=>window.gravewrightJournals.flush(id)", document_id)
            expect(window.locator('.journal-window__error')).to_be_hidden()

        def close(window):
            window.locator('[data-action=close]').click()
            expect(window).to_have_count(0)

        def open_journal(page, document_id):
            nav(page, "journals")
            page.evaluate("id=>window.gravewrightJournals.open(id)", document_id)
            window = page.locator(f'.journal-window[data-journal-id="{document_id}"]')
            expect(window).to_be_visible()
            return window

        def share(page, document_id):
            page.evaluate("""async id=>{
              const view=await gravewright.ownership.read({kind:'journals',id});
              await gravewright.ownership.update({kind:'journals',id,version:view.version,permissions:{default:'read'}});
            }""", document_id)

        def journals(page):
            response = page.request.get(f"{base}/api/containers/{campaign}/journals")
            assert response.ok, response.text()
            return response.json()["journals"]

        try:
            gm = client("gm")
            response = gm.request.get(base + management_api)
            assert response.ok, response.text()
            expect(gm.locator('[data-manager-section=members]')).to_be_visible()
            gm.screenshot(path=str(output / 'overview-empty-1440.png'), full_page=True)
            nav(gm, 'quests')
            expect(gm.locator('[data-manager-quest-id]')).to_have_count(0)
            gm.screenshot(path=str(output / 'quests-empty-1440.png'), full_page=True)
            records.append({"case": "owner-gm-management-shell-loads-native-tools-without-socket-or-board"})

            diary, diary_id = create(gm, 'diary', DIARY_TITLE)
            expect(diary.locator('[data-empty-cover]')).to_be_visible()
            diary.screenshot(path=str(output / 'native-diary-empty-1440.png'))
            diary.locator('[data-empty-cover]').click()
            diary.get_by_role('textbox', name='Journal cover', exact=True).fill(PUBLIC_TEXT)
            diary.locator('[data-action=gm]').click()
            diary.get_by_role('textbox', name='GM notes', exact=True).fill(GM_SECRET)
            flush(gm, diary, diary_id)
            close(diary)
            share(gm, diary_id)
            saved = next(row for row in journals(gm) if row['id'] == diary_id)
            assert PUBLIC_TEXT.strip() in json.dumps(saved) and GM_SECRET in json.dumps(saved)
            records.append({"case": "native-diary-editor-creates-public-content-and-persisted-gm-notes"})

            cogm = client('cogm')
            assert cogm.request.get(base + management_api).ok
            diary = open_journal(cogm, diary_id)
            diary.get_by_role('textbox', name='Journal cover', exact=True).fill(EDITED_TEXT)
            flush(cogm, diary, diary_id)
            close(diary)
            saved = next(row for row in journals(gm) if row['id'] == diary_id)
            assert EDITED_TEXT.strip() in json.dumps(saved) and GM_SECRET in json.dumps(saved)
            records.append({"case": "participant-account-with-gm-membership-edits-same-native-diary"})

            quest, quest_id = create(cogm, 'quest', QUEST_TITLE)
            quest.locator('[data-action=edit]').click()
            quest.locator('[data-q=summary]').fill('Find the missing instrument and return safely. ' * 5)
            quest.locator('[data-q=location]').fill('The eastern valley and the abandoned observatory')
            quest.get_by_role('textbox', name='Quest description', exact=True).fill(PUBLIC_TEXT)
            quest.locator('[data-quest-tab=gm]').click()
            quest.get_by_role('textbox', name='GM notes', exact=True).fill(QUEST_SECRET)
            flush(cogm, quest, quest_id)
            close(quest)
            share(cogm, quest_id)
            saved = next(row for row in journals(gm) if row['id'] == quest_id)
            assert saved['type'] == 'quest' and QUEST_SECRET in json.dumps(saved)
            nav(cogm, 'quests')
            expect(cogm.locator(f'[data-manager-quest-id="{quest_id}"]')).to_be_visible()
            records.append({"case": "native-quest-editor-persists-public-description-and-private-gm-data"})

            player = client('player', manage=False)
            player.goto(base + '/inside')
            expect(player.locator(f'a[href="{management_path}"]')).to_have_count(0)
            for path in (management_path, management_api):
                response = player.request.get(base + path)
                assert response.status in (403, 404), (path, response.status)
            for page in (gm, cogm):
                for path in (f"/campaigns/{seed['otherCampaign']}/manage",
                             f"/api/containers/{seed['otherCampaign']}/management"):
                    response = page.request.get(base + path)
                    assert response.status in (403, 404), (path, response.status)
            projected = journals(player)
            serialized = json.dumps(projected)
            assert GM_SECRET not in serialized and QUEST_SECRET not in serialized
            assert any(row['id'] == diary_id for row in projected)
            assert any(row['id'] == quest_id for row in projected)
            records.append({"case": "management-denies-player-and-unrelated-campaign-and-projects-gm-secrets-out"})
            authored, _ = create(gm, 'diary', 'Overview')
            close(authored)

            nav(gm, 'actors')
            gm.evaluate('id=>window.gravewrightActors.open(id)', seed['actor'])
            sheet = gm.locator('.actor-directory__sheet')
            expect(sheet.locator('.pdf-sheet__canvas')).to_have_count(1)
            sheet.locator('[data-pdf=togglePicker]').click()
            sheet.locator('[data-pdf-sources]').get_by_role('button', name='Synthetic fillable.pdf', exact=True).click()
            hp = sheet.locator('.pdf-sheet__fields [data-pdf-field=HP]')
            expect(hp).to_be_visible()
            hp.fill('31')
            sheet.locator('[data-window=close]').click()
            expect(sheet).to_have_count(0)
            gm.evaluate('id=>window.gravewrightActors.open(id)', seed['actor'])
            expect(sheet.locator('.pdf-sheet__fields [data-pdf-field=HP]')).to_have_value('31')
            sheet.screenshot(path=str(output / 'native-pdf-character-1440.png'))
            sheet.locator('[data-window=close]').click()
            expect(sheet).to_have_count(0)
            records.append({"case": "native-pdf-character-sheet-edits-and-reopens-without-a-table-connection"})

            nav(gm, 'maps')
            gm.locator(f'[data-manager-map-select="{seed["selectedScene"]}"]').click()
            nav(gm, 'audio')
            gm.locator('[data-manager-audio-workspace]').click()
            expect(gm.locator('.audio-panel')).to_be_visible()
            gm.locator('.audio-panel').get_by_role('button', name='Close audio', exact=True).click()
            expect(gm.locator('.audio-panel')).to_have_count(0)
            preview = gm.locator('[data-manager-audio] audio')
            expect(preview).to_have_count(1)
            preview.evaluate('''async audio=>{
              audio.muted=true; await audio.play(); window.__managementPreview=audio;
            }''')
            gm.locator('[data-manager-refresh]').click()
            expect(gm.locator('[data-manager-refresh]')).to_be_enabled()
            assert gm.evaluate('''window.__managementPreview===document.querySelector('[data-manager-audio] audio')
              && !window.__managementPreview.paused''')
            preview.evaluate('audio=>audio.pause()')
            records.append({"case": "selecting-scene-before-lazy-audio-import-opens-native-scene-audio"})

            for section in ('library', 'audio', 'cards', 'compendiums', 'combat', 'members'):
                nav(gm, section)
                if section == 'library':
                    expect(gm.locator('[data-manager-library] .asset-library')).to_be_visible()
                elif section == 'cards':
                    expect(gm.locator('[data-manager-decks]')).not_to_be_empty()
                elif section in ('compendiums', 'combat'):
                    expect(gm.locator(f'[data-native-directory="{section}"]')).to_be_visible()
                    gm.wait_for_function('name=>window.gravewrightRealtime.states.has(name)', arg=section)
                elif section == 'audio':
                    gm.wait_for_function("window.gravewrightRealtime.states.has('audio')")
                expect(gm.locator('[data-manager-error]')).to_be_hidden()
                gm.screenshot(path=str(output / f'panel-{section}-1440.png'), full_page=True)
            records.append({"case": "library-audio-decks-compendiums-encounters-and-members-mount-without-a-board"})
            nav(gm, 'members')
            gm.locator('[data-manager-invite]').click()
            invitation = gm.locator('.table-form-modal[data-window-key="manager-invitation"]')
            expect(invitation).to_be_visible()
            expect(invitation.locator('[name=code]')).to_have_attribute('readonly', '')
            assert invitation.locator('[name=code]').input_value()
            invite_status = gm.evaluate('id=>gravewright.campaigns.invitationStatus(id)', campaign)
            assert invite_status['active'] and invite_status['maxUses'] == 10 and invite_status['useCount'] == 0
            remaining_hours = (invite_status['expiresAt'] - gm.evaluate('Date.now()')) / 3600000
            assert 23.9 < remaining_hours <= 24.01, invite_status
            invitation.locator('[data-cancel]').click()
            expect(invitation).to_have_count(0)
            gm.locator('[data-manager-members]').get_by_role('button', name='Remove participant', exact=True).first.click()
            removal = gm.locator('.table-form-modal[data-window-key="manager-remove-member"]')
            expect(removal).to_be_visible()
            removal.locator('[data-cancel]').click()
            expect(removal).to_have_count(0)
            records.append({"case": "native-invitation-has-24-hour-ten-use-defaults-and-removal-can-be-cancelled"})

            nav(gm, 'maps')
            scene = gm.locator(f'[data-manager-maps] [data-scene-id="{seed["selectedScene"]}"]')
            expect(scene).to_be_visible()
            scene.locator('[data-manager-map-select]').click()
            expect(scene.locator('[data-manager-map-select]')).to_have_attribute('aria-pressed', 'true')
            scene.get_by_role('button', name='Edit scene', exact=True).click()
            settings = gm.locator('.table-form-modal[data-window-key^="managed-scene:"]')
            expect(settings.locator('[name=name]')).not_to_have_value('')
            settings.locator('[data-cancel]').click()
            expect(settings).to_have_count(0)
            scene.get_by_role('button', name='Export Universal VTT', exact=True).click()
            uvtt = gm.locator('[data-universal-vtt]')
            expect(uvtt).to_be_visible()
            uvtt.locator('[data-uvtt-close]').click()
            expect(uvtt).to_have_count(0)
            gm.locator('#campaign-search').fill('observatory')
            results = gm.locator('[data-manager-search-results]')
            expect(results.get_by_role('button').filter(has_text=QUEST_TITLE)).to_be_visible()
            gm.locator('#campaign-search').fill('')
            expect(results).to_be_hidden()
            records.append({"case": "scene-context-native-settings-uvtt-modal-and-search-work-without-navigation"})

            for locale in ('en', 'pt-BR', 'es'):
                change_locale(gm, locale, campaign)
                gm.set_viewport_size({'width': 320, 'height': 844})
                gm.goto(base + management_path)
                gm.wait_for_function('!!window.gravewrightJournals')
                expect(gm.locator('#table-workspace')).to_have_attribute('data-manager-ready', 'true')
                navigation_labels = {
                    'en': ('Enter table', 'Back to campaigns'),
                    'pt-BR': ('Entrar na mesa', 'Voltar às campanhas'),
                    'es': ('Entrar en la mesa', 'Volver a las campañas'),
                }
                enter_label, back_label = navigation_labels[locale]
                expect(gm.locator('.campaign-manager__enter')).to_have_text(enter_label)
                expect(gm.locator('.campaign-manager__back')).to_have_text(back_label)
                authored_title = gm.locator('[data-manager-documents] button').filter(has_text='Overview').locator('span')
                expect(authored_title).to_have_text('Overview')
                expect(authored_title).to_have_attribute('translate', 'no')
                gm.locator('#campaign-search').fill('Overview')
                search_title = gm.locator('[data-manager-search-results] button').filter(has_text='Overview').locator('span')
                expect(search_title).to_have_text('Overview')
                expect(search_title).to_have_attribute('translate', 'no')
                metrics = gm.locator('[data-manager-search-results]').evaluate(MEASURE)
                assert not metrics['tiny'] and not metrics['overflow'], (locale, metrics)
                gm.locator('#campaign-search').fill('')
                expect(gm.locator('[data-manager-search-results]')).to_be_hidden()
                nav(gm, 'quests')
                labels = {'en': 'Quests', 'pt-BR': 'Missões', 'es': 'Misiones'}
                expect(gm.locator('[data-manager-section=quests]')).to_have_text(labels[locale])
                expect(gm.locator(f'[data-manager-quest-id="{quest_id}"]')).to_be_visible()
                metrics = gm.locator('#table-workspace').evaluate(MEASURE)
                assert not metrics['tiny'] and not metrics['overflow'], (locale, metrics)
                assert gm.evaluate('document.documentElement.scrollWidth<=innerWidth+1'), locale
                gm.screenshot(path=str(output / f'quests-{locale}-320.png'), full_page=True)
                nav(gm, 'journals')
                window = open_journal(gm, diary_id)
                assert EDITED_TEXT.strip() in window.inner_text()
                metrics = window.evaluate(MEASURE)
                assert not metrics['tiny'] and not metrics['overflow'], (locale, metrics)
                window.screenshot(path=str(output / f'native-diary-{locale}-320.png'))
                close(window)
                records.append({"case": f"localized-management-and-native-long-diary-{locale}-320"})

            nav(cogm, 'maps')
            cogm.locator(f'[data-manager-map-select="{seed["selectedScene"]}"]').click()
            nav(cogm, 'audio')
            cogm.locator('[data-manager-audio-workspace]').click()
            expect(cogm.locator('.audio-panel')).to_be_visible()
            cogm.evaluate('id=>window.gravewrightJournals.open(id)', diary_id)
            diary = cogm.locator(f'.journal-window[data-journal-id="{diary_id}"]')
            expect(diary).to_be_visible()
            diary.locator('[data-action=gm]').click()
            expect(diary.get_by_role('textbox', name='GM notes', exact=True)).to_contain_text(GM_SECRET)
            cogm.evaluate('id=>window.gravewrightActors.open(id)', seed['actor'])
            expect(cogm.locator('.actor-directory__sheet .pdf-sheet__canvas')).to_have_count(1)
            revoke_gm()
            cogm.evaluate("window.dispatchEvent(new Event('focus'))")
            expect(cogm.locator('#table-workspace.campaign-manager--revoked')).to_be_visible()
            expect(cogm.locator('.audio-panel, .actor-directory__sheet, .journal-window')).to_have_count(0)
            assert GM_SECRET not in cogm.content() and QUEST_SECRET not in cogm.content()
            assert cogm.request.get(base + management_api).status in (403, 404)
            cogm.screenshot(path=str(output / 'revoked-cogm-1440.png'), full_page=True)
            records.append({"case": "revoked-gm-access-closes-native-audio-character-and-journal-windows"})

            for role in ('gm', 'cogm', 'player'):
                assert not sockets[role], (role, sockets[role])
            after = read_snapshot()
            (output / 'control-after.json').write_text(json.dumps(after, indent=2), encoding='utf-8')
            assert after == before, {'before': before, 'after': after}
            records.append({"case": "management-does-not-change-broadcast-private-navigation-or-table-presence"})

            change_locale(gm, 'en', campaign)
            gm.set_viewport_size({'width': 1440, 'height': 1000})
            response = gm.goto(f'{base}/game/{campaign}')
            assert response.ok
            gm.wait_for_function('!!window.gravewrightMaps && !!window.gravewrightJournals')
            expect(gm.locator('.game-menubar__presence')).to_have_attribute('data-presence', 'seated')
            gm.wait_for_function('id=>window.gravewrightMaps.current?.id===id', arg=seed['selectedScene'])
            gm.evaluate('id=>window.gravewrightJournals.open(id)', diary_id)
            window = gm.locator(f'.journal-window[data-journal-id="{diary_id}"]')
            expect(window).to_be_visible()
            expect(window.get_by_role('textbox', name='Journal cover', exact=True)).to_contain_text(EDITED_TEXT.strip())
            close(window)
            response = player.goto(f'{base}/game/{campaign}')
            assert response.ok
            player.wait_for_function('!!window.gravewrightJournals')
            expect(player.locator('.game-menubar__presence')).to_have_attribute('data-presence', 'seated')
            player.evaluate('id=>window.gravewrightJournals.open(id)', diary_id)
            window = player.locator(f'.journal-window[data-journal-id="{diary_id}"]')
            expect(window).to_be_visible()
            assert EDITED_TEXT.strip() in window.inner_text()
            assert GM_SECRET not in player.content() and QUEST_SECRET not in player.content()
            expect(window.locator('[data-action=gm]')).to_be_hidden()
            player.screenshot(path=str(output / 'same-diary-on-player-table-1440.png'), full_page=True)
            records.append({"case": "same-journal-documents-are-visible-on-real-table-with-player-filtering"})
            close(window)
            gm.evaluate('id=>gravewright.maps.navigate({mapId:id})', seed['broadcastScene'])
            for page in (gm, player):
                page.wait_for_function('id=>window.gravewrightMaps.current?.id===id', arg=seed['broadcastScene'])
                page.wait_for_function('!!window.gravewrightTableMedia')
                page.evaluate('''()=>{
                  window.__managementAudio=[]; const NativeAudio=window.Audio;
                  window.Audio=function(...args){const audio=new NativeAudio(...args);__managementAudio.push(audio);return audio};
                }''')
                page.get_by_role('button', name='Enable audio', exact=True).click()

            def playback(action):
                gm.evaluate('''async ({campaign,scene,track,action})=>{
                  const api=gravewright.forTable(campaign,{sceneId:scene}); const state=await api.audio.state();
                  await api.audio[action]({trackId:track,version:state.version});
                }''', {'campaign': campaign, 'scene': seed['broadcastScene'], 'track': seed['previewTrack'], 'action': action})

            playback('play')
            for page in (gm, player):
                page.wait_for_function('__managementAudio.some(audio=>!audio.paused&&audio.currentTime>0)')
            playback('pause')
            for page in (gm, player):
                page.wait_for_function('__managementAudio.length>0&&__managementAudio.every(audio=>audio.paused)')
            playback('play')
            for page in (gm, player):
                page.wait_for_function('__managementAudio.some(audio=>!audio.paused&&audio.currentTime>0)')
            playback('stop')
            for page in (gm, player):
                page.wait_for_function('__managementAudio.every(audio=>audio.paused&&!audio.getAttribute("src"))')
            records.append({"case": "real-table-audio-play-pause-resume-stop-reaches-two-browser-clients"})
            assert not errors, errors
            assert not dialogs, dialogs
            assert not [request for request in failed if request['error'] != 'net::ERR_ABORTED'], failed
        except Exception:
            (output / 'browser-diagnostics.json').write_text(json.dumps({'completedCases': records,
                'pageErrors': errors, 'nativeDialogs': dialogs, 'failedRequests': failed, 'websockets': sockets}, indent=2), encoding='utf-8')
            for role, page in pages.items():
                page.screenshot(path=str(output / f'failure-{role}.png'), full_page=True)
            raise
        finally:
            for context in contexts:
                context.close()
            browser.close()
    return {'passed': True, 'cases': records, 'pageErrors': errors, 'nativeDialogs': dialogs,
            'failedRequests': failed, 'managementPreservedTableState': before == after,
            'assets': 'Generated synthetic PDFs, a silent WAV preview, and authored synthetic journal/quest text only.'}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path)
    parser.add_argument('--browser-executable', type=Path)
    parser.add_argument('--serve', action='store_true', help=argparse.SUPPRESS)
    parser.add_argument('--snapshot', action='store_true', help=argparse.SUPPRESS)
    parser.add_argument('--revoke-gm', action='store_true', help=argparse.SUPPRESS)
    parser.add_argument('--fixture', type=Path, help=argparse.SUPPRESS)
    parser.add_argument('--port', type=int, default=0, help=argparse.SUPPRESS)
    args = parser.parse_args()
    if args.serve:
        serve(args.fixture, args.port)
        return
    if args.snapshot:
        snapshot(args.fixture)
        return
    if args.revoke_gm:
        revoke_fixture_gm(args.fixture)
        return
    output = (args.output or ROOT / 'data/campaign-management' /
              datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S%fZ')).resolve()
    if output.exists() and any(output.iterdir()):
        raise RuntimeError('Use a fresh, empty output directory.')
    output.mkdir(parents=True, exist_ok=True)
    fixture = output / 'fixture'
    fixture.mkdir()
    with socket.socket() as connection:
        connection.bind(('127.0.0.1', 0))
        port = connection.getsockname()[1]
    fixture_environment(fixture, port)
    executable = sys._base_executable if os.name == 'nt' else sys.executable
    command = [executable, '-B', '-X', 'utf8', str(Path(__file__).resolve())]
    base = f'http://127.0.0.1:{port}'
    with (output / 'server.log').open('w', encoding='utf-8') as log:
        server = subprocess.Popen([*command, '--serve', '--fixture', str(fixture), '--port', str(port)],
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
                raise RuntimeError('Fixture did not become ready.')
            seed = json.loads((fixture / 'seed.json').read_text(encoding='utf-8'))

            def read_snapshot():
                return json.loads(subprocess.check_output([*command, '--snapshot', '--fixture', str(fixture)],
                                                         cwd=ROOT, env=os.environ.copy(), text=True, encoding='utf-8'))

            def revoke_gm():
                subprocess.check_call([*command, '--revoke-gm', '--fixture', str(fixture)],
                                      cwd=ROOT, env=os.environ.copy())

            report = check_browser(base, seed, output, args.browser_executable, read_snapshot, revoke_gm)
            (output / 'report.json').write_text(json.dumps(report, indent=2), encoding='utf-8')
            print(json.dumps({'passed': True, 'cases': len(report['cases']), 'report': str(output / 'report.json')}))
        except Exception:
            (output / 'failure.txt').write_text(traceback.format_exc(), encoding='utf-8')
            raise
        finally:
            server.terminate()
            try:
                server.wait(timeout=10)
            except subprocess.TimeoutExpired:
                server.kill()
                server.wait()
            (output / 'server-exit.json').write_text(json.dumps({'pid': server.pid, 'exitCode': server.returncode}), encoding='utf-8')


if __name__ == '__main__':
    main()
