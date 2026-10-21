"""Author targeted dice prompts and journal/quest actions in a disposable table.

The native editor, its local simulation, campaign persistence, table sockets and
normal dice service run with synthetic journals and two independent players.
"""
from __future__ import annotations

from copy import deepcopy
import json

import map_builder_blueprints as harness
from map_builder import MEASURE, builder_tool, builder_workspace, change_locale
from map_builder_asset_removal import BuilderReview
from map_builder_reference import close_panel, set_name, wait_ready


serve_blueprints = harness.serve


def serve(fixture, port):
    from django.core import management

    original = management.call_command

    def command(name, *args, **kwargs):
        if name == 'runserver':
            from django.conf import settings
            from django.test import Client
            from django.utils import timezone
            from gravewright.accounts.models import User
            from gravewright.campaigns.models import Membership, Onboarding
            from gravewright.journals import data
            from gravewright.journals.models import Journal

            seed_file = fixture / 'seed.json'
            seed = json.loads(seed_file.read_text(encoding='utf-8'))
            gm = User.objects.get(email='gm@map-builder.test')
            player = User.objects.get(email='player@map-builder.test')
            second = User.objects.create_user('second@map-builder.test', 'synthetic-password-12345', name='Second player')
            membership = Membership.objects.create(campaign_id=seed['campaign'], user=second, role='player')
            Onboarding.objects.create(membership=membership, dismissed=True, player_shown_at=timezone.now())
            client = Client()
            client.force_login(second)
            seed['sessions']['second'] = {'name': settings.SESSION_COOKIE_NAME,
                                         'value': client.cookies[settings.SESSION_COOKIE_NAME].value}
            diary = Journal.objects.create(campaign_id=seed['campaign'], creator=gm,
                title='Synthetic diary with a deliberately long title — 雪', visibility='shared')
            quest = Journal.objects.create(campaign_id=seed['campaign'], creator=gm,
                title='Synthetic quest: recover the copper key', type='quest', visibility='shared',
                data=data.normalize_quest_data({'status': 'available'}))
            seed.update(playerId=str(player.pk), secondId=str(second.pk), diaryId=str(diary.pk),
                        diaryTitle=diary.title, questId=str(quest.pk), questTitle=quest.title)
            seed_file.write_text(json.dumps(seed, indent=2, ensure_ascii=False), encoding='utf-8')
        return original(name, *args, **kwargs)

    management.call_command = command
    try:
        serve_blueprints(fixture, port)
    finally:
        management.call_command = original


def check_browser(base, seed, output, executable):
    from playwright.sync_api import expect, sync_playwright

    campaign = seed['campaign']
    cases, errors, dialogs = [], [], []
    clients, contexts = {}, []
    with sync_playwright() as playwright:
        browser = playwright.chromium.launch(**({'executable_path': str(executable)} if executable else {}))

        def client(role):
            context = browser.new_context(base_url=base, viewport={'width': 1440, 'height': 900})
            context.add_cookies([{**seed['sessions'][role], 'url': base}])
            context.add_init_script('''window.__interactionEvents=[];addEventListener('gravewright:api-event',({detail})=>{
              if(['automation.presentation','dice.ack','dice.error','chat.message'].includes(detail?.type))
                window.__interactionEvents.push(detail);
            });''')
            page = context.new_page()
            page.on('pageerror', lambda error: errors.append({'role': role, 'message': str(error)}))
            page.on('dialog', lambda dialog: (dialogs.append(dialog.message), dialog.dismiss()))
            clients[role] = page
            contexts.append(context)
            return page

        gm = client('gm')
        review = BuilderReview(gm, campaign)

        def game(page):
            page.wait_for_url(f'{base}/game/{campaign}')
            page.wait_for_function('!!window.gravewrightMaps?.current && !!window.gravewrightRealtime')
            expect(page.locator('.game-menubar__presence')).to_have_attribute('data-presence', 'seated')

        def open_editor(identifier):
            builder_tool(gm, 'select')
            builder_workspace(gm)
            gm.locator(f'[data-builder-doors] [data-object-id="{identifier}"]').dblclick()
            modal = gm.locator('[data-smart-object-modal]')
            expect(modal).to_be_visible()
            modal.locator('[data-blueprint-event="interact"]').click()
            return modal

        def card(modal, identifier):
            return modal.locator(f'[data-blueprint-node="{identifier}"]')

        def parameter(modal, identifier, key, value):
            control = card(modal, identifier).locator(f'[data-blueprint-param="{key}"]')
            if control.evaluate('element=>element.tagName') == 'SELECT':
                control.select_option(value)
            else:
                control.fill(value)
                control.dispatch_event('change')

        def add_node(modal, kind, **params):
            before = set(modal.locator('[data-blueprint-node]').evaluate_all('nodes=>nodes.map(node=>node.dataset.blueprintNode)'))
            modal.locator('[data-blueprint-add]').click()
            modal.locator(f'[data-blueprint-pick-type="{kind}"]').click()
            after = set(modal.locator('[data-blueprint-node]').evaluate_all('nodes=>nodes.map(node=>node.dataset.blueprintNode)'))
            identifier, = after - before
            for key, value in params.items():
                parameter(modal, identifier, key, value)
            return identifier

        def connect(modal, before, after):
            modal.locator('[data-blueprint-fit]').click()
            source = (card(modal, before).locator('[data-blueprint-output="next"]') if before else
                modal.locator('[data-blueprint-instance] [data-blueprint-event-port="interact"][data-blueprint-output="next"]'))
            source.click()
            card(modal, after).locator('[data-blueprint-input]').click()

        def journals(page=gm):
            response = page.request.get(f'/api/containers/{campaign}/journals')
            assert response.ok, response.text()
            return response.json()['journals']

        def quest_status():
            quest = next(row for row in journals() if row['id'] == seed['questId'])
            return quest['quest']['status'], quest['version']

        def presentations(page):
            return page.evaluate("__interactionEvents.filter(event=>event.type==='automation.presentation').map(event=>event.payload)")

        try:
            gm.goto(review.builder)
            wait_ready(gm)
            set_name(gm, 'Synthetic dice prompts and journal interactions')
            for x in (8, 18):
                builder_tool(gm, 'door')
                review.stroke((x, 6), (x + 2, 6))
            initial = review.save()
            first, second = [row['id'] for row in initial['document']['doors']]

            modal = open_editor(first)
            roll = add_node(modal, 'requestRoll', expression='2d1', label='Synthetic targeted request', visibility='gm', audienceScope='player')
            parameter(modal, roll, 'audiencePlayer', seed['playerId'])
            quest = add_node(modal, 'setQuestStatus', journalId=seed['questId'], status='active')
            diary = add_node(modal, 'showHandout', journalId=seed['diaryId'], audienceScope='player')
            parameter(modal, diary, 'audiencePlayer', seed['playerId'])
            for before, after in ((None, roll), (roll, quest), (quest, diary)):
                connect(modal, before, after)
            modal.locator('[data-blueprint-simulate]').click()
            expect(modal.locator('[data-blueprint-trace]')).to_contain_text('2d1')
            expect(modal.locator('[data-blueprint-trace]')).to_contain_text(seed['questTitle'])
            assert quest_status() == ('available', 1)
            assert not gm.locator('[data-automation-presentation]').count()
            modal.locator('[data-blueprint-close]').click()
            expect(modal).to_have_count(0)
            saved = review.save()
            modal = open_editor(first)
            expect(card(modal, roll).locator('[data-blueprint-param=audienceScope]')).to_have_value('player')
            expect(card(modal, roll).locator('[data-blueprint-param=audiencePlayer]')).to_have_value(seed['playerId'])
            expect(card(modal, quest).locator('[data-blueprint-param=status]')).to_have_value('active')
            expect(card(modal, diary).locator('[data-blueprint-param=journalId]')).to_have_value(seed['diaryId'])
            modal.locator('[data-blueprint-cancel]').click()
            cases.append({'case': 'real-editor-authors-connects-simulates-saves-and-reopens-targeted-roll-quest-and-diary-actions'})

            modal = open_editor(second)
            all_roll = add_node(modal, 'requestRoll', expression='3d1', label='Synthetic all players', audienceScope='players')
            connect(modal, None, all_roll)
            modal.locator('[data-blueprint-close]').click()
            expect(modal).to_have_count(0)
            saved = review.save()
            authored = deepcopy(saved['document'])
            for locale in ('en', 'pt-BR', 'es'):
                change_locale(gm, locale, campaign)
                for width in (1440, 390):
                    gm.set_viewport_size({'width': width, 'height': 900 if width == 1440 else 844})
                    gm.goto(review.builder + '?project=' + saved['id'])
                    wait_ready(gm)
                    modal = open_editor(first)
                    modal.locator('[data-blueprint-fit]').click()
                    modal.locator('[data-blueprint-simulate]').click()
                    expect(modal.locator('[data-blueprint-trace]')).to_contain_text('2d1')
                    metrics = modal.evaluate(MEASURE)
                    assert not metrics['tiny'] and not metrics['overflow'], metrics
                    gm.screenshot(path=str(output / f'interactions-editor-{locale}-{width}.png'))
                    gm.keyboard.press('Escape')
                    expect(modal).to_have_count(0)
                    assert review.project(saved['id'])['document'] == authored
                    assert quest_status() == ('available', 1)
                    cases.append({'case': 'localized-editor-preview-keeps-authored-values-and-has-no-live-effects',
                                  'locale': locale, 'width': width, 'metrics': metrics})

            change_locale(gm, 'en', campaign)
            gm.set_viewport_size({'width': 1440, 'height': 900})
            gm.goto(review.builder + '?project=' + saved['id'])
            wait_ready(gm)
            close_panel(gm)
            with gm.expect_response(lambda response: response.url.endswith('/generate')) as generated:
                gm.locator('[data-builder-generate]').click()
            assert generated.value.ok, generated.value.text()
            game(gm)
            project = review.project(saved['id'])
            scene = project['sceneId']
            gm.evaluate('scene=>gravewrightRealtime.mapCommand("activate",{mapId:scene})', scene)
            player, second_player = client('player'), client('second')
            for guest in (player, second_player):
                guest.goto(f'/game/{campaign}')
                game(guest)
                expect(guest.locator('.door-controls [role=button]')).to_have_count(2)
            native = gm.request.get(f'/api/maps/{scene}/state').json()['walls']
            first_native = next(row for row in native if any(node.get('label') == 'Synthetic targeted request'
                for graph in row.get('blueprint', {}).get('graphs', {}).values() for node in graph['nodes']))
            second_native = next(row for row in native if row['id'] != first_native['id'] and row['kind'] == 'door')

            def trigger(target, wall):
                # Doors are rendered in their server state order. Keyboard activation
                # uses the same actual control and authored event as pointer input.
                state = target.request.get(f'/api/maps/{scene}/state').json()
                identifiers = [row['id'] for row in state['walls'] if row['kind'] == 'door']
                control = target.locator('.door-controls [role=button]').nth(identifiers.index(wall['id']))
                control.focus()
                control.press('Enter')

            trigger(second_player, first_native)
            prompt = player.locator('[data-presentation-roll]')
            expect(prompt).to_be_visible()
            expect(prompt.locator('code')).to_have_text('2d1')
            expect(player.locator('.journal-window [data-title]')).to_have_text(seed['diaryTitle'])
            assert quest_status() == ('active', 2)
            second_player.wait_for_timeout(350)
            assert not second_player.locator('[data-automation-presentation]').count()
            assert not second_player.locator('.journal-window').count()
            assert not gm.locator('[data-automation-presentation]').count()
            assert [entry['type'] for entry in presentations(player)] == ['roll', 'handout']
            assert not presentations(second_player)
            player.screenshot(path=str(output / 'interactions-player-targeted.png'))
            prompt.locator('[data-presentation-roll-submit]').click()
            expect(prompt.locator('[role=status]')).to_be_visible()
            expect(prompt.locator('[data-presentation-roll-submit]')).to_be_disabled()
            ack = player.evaluate("__interactionEvents.find(event=>event.type==='dice.ack').payload")
            assert ack['message']['roll']['expression'] == '2d1', ack
            assert ack['message']['roll']['secret'] is True, ack
            player.locator('[data-presentation-close]').click()
            cases.append({'case': 'another-player-triggers-fixed-one-player-audience-with-diary-and-quest-change-and-real-secret-dice'})

            # A scene reload closes the reader window before the second request.
            player.reload()
            game(player)
            trigger(player, second_native)
            for guest in (player, second_player):
                form = guest.locator('[data-presentation-roll]')
                expect(form).to_be_visible()
                expect(form.locator('code')).to_have_text('3d1')
                form.locator('[data-presentation-roll-submit]').click()
                expect(form.locator('[role=status]')).to_be_visible()
                expect(form.locator('[data-presentation-roll-submit]')).to_be_disabled()
                ack = guest.evaluate("__interactionEvents.filter(event=>event.type==='dice.ack').at(-1).payload")
                assert ack['message']['roll']['expression'] == '3d1', ack
                assert ack['message']['roll']['secret'] is False, ack
                guest.screenshot(path=str(output / f'interactions-all-{"player" if guest == player else "second"}.png'))
            assert not gm.locator('[data-automation-presentation]').count()
            assert len([row for row in journals(player) if row['id'] == seed['questId']]) == 1
            assert quest_status() == ('active', 2)
            cases.append({'case': 'all-players-audience-delivers-one-real-roll-modal-and-normal-public-chat-result-to-each-player'})
        except Exception:
            for role, page in clients.items():
                page.screenshot(path=str(output / f'failure-{role}.png'), full_page=True)
            (output / 'progress.json').write_text(json.dumps({'cases': cases, 'pageErrors': errors,
                'nativeDialogs': dialogs}, indent=2, ensure_ascii=False), encoding='utf-8')
            raise
        finally:
            for context in contexts:
                context.close()
            browser.close()
    assert not errors, errors
    assert not dialogs, dialogs
    return {'passed': True, 'cases': cases, 'pageErrors': errors, 'nativeDialogs': dialogs,
            'assets': 'Disposable synthetic journals, two players and native door geometry.'}


if __name__ == '__main__':
    harness.__file__ = __file__
    harness.serve = serve
    harness.check_browser = check_browser
    harness.main()
