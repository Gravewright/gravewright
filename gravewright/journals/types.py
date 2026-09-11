"""Quest projections, board links and atomic weighted draws."""
from copy import deepcopy
import secrets
import uuid

from gravewright.accounts.services import AuthError
from gravewright.campaigns.models import Membership
from gravewright.chat.models import Message, Recipient
from gravewright.chat.services import consume_limit, public_message
from . import data as shapes
from .models import BoardEntry


def via_board(journal, who):
    from .services import permissions
    if journal.type != 'quest' or journal.data.get('status') not in shapes.PLAYER_VISIBLE_STATUSES:
        return False
    return any(permissions(link.board, who)[0] for link in journal.quest_links.select_related('board').filter(
        board__campaign_id=who.campaign_id, board__type='quest_board').prefetch_related('board__access'))


def project(journal, who, clean):
    gm = who.role == 'gm'
    if journal.type == 'quest':
        builder = shapes.build_quest_gm_view if gm else shapes.build_quest_player_view
        return {'quest': builder(title=journal.title, data=clean)}
    if journal.type == 'quest_board':
        entries = []
        for link in journal.board_links.select_related('quest').filter(quest__campaign_id=who.campaign_id, quest__type='quest').order_by('-pinned', 'sort_order', 'id'):
            card = shapes.build_quest_card(title=link.quest.title, data=link.quest.data)
            if not gm and card['status'] not in shapes.PLAYER_VISIBLE_STATUSES:
                continue
            entries.append({'quest_id': str(link.quest_id), 'pinned': link.pinned,
                            'sort_order': link.sort_order, 'card': card})
        return {'board_entries': entries, 'board_display_entries': [e for e in entries if e['card']['status'] in shapes.PLAYER_VISIBLE_STATUSES]}
    if journal.type == 'roll_table':
        total = sum(e['weight'] for e in clean['entries'] if e['active'] and (clean['withReplacement'] or not e['drawn']))
        if clean['resultVisibility'] == 'gm' and not gm:
            for entry in clean['entries']:
                entry['result'] = ''
        return {'roll_table': {**clean, 'totalWeight': total}}
    return {}


def clean_type(raw, clean, journal, who):
    from .services import JournalError, preserve_secrets
    gm = who.role == 'gm'
    for key, limit in [('objectives',64),('rewards',64),('entries',256)]:
        if key in raw and (not isinstance(raw[key],list) or len(raw[key]) > limit):
            raise JournalError('Too many or invalid document entries.')
        rows = clean.get(key, [])
        if len({row['id'] for row in rows}) != len(rows):
            raise JournalError('Document entries must have unique identifiers.')
    existing = shapes.normalize_data_for(journal.type, journal.data)
    if journal.type == 'quest':
        image = clean['public']['image']
        if image['assetId']:
            image['src'] = '/game/journal/asset/' + image['assetId']
        if not gm:
            clean['gm'] = existing['gm']
            clean['public']['description'] = preserve_secrets(clean['public']['description'], existing['public']['description'])
            for key in ['objectives','rewards']:
                hidden = [r for r in existing[key] if not r['visibleToPlayers']]
                if {r['id'] for r in hidden} & {r['id'] for r in clean[key]}:
                    raise JournalError('Entry not found or access denied.')
                for row in clean[key]:
                    row['visibleToPlayers'] = True
                clean[key].extend(deepcopy(hidden))
                if len(clean[key]) > 64:
                    raise JournalError('Use up to 64 entries.')
    if journal.type == 'roll_table' and not gm:
        clean['resultVisibility'] = existing['resultVisibility']
        if existing['resultVisibility'] == 'gm':
            originals = {e['id']: e for e in existing['entries']}
            # An editor without GM access cannot erase or forge a hidden result.
            for entry in clean['entries']:
                entry['result'] = originals.get(entry['id'], {}).get('result', '')
    return clean


def apply(journal, who, action, payload):
    from .services import JournalError, get, identifier
    gm = who.role == 'gm'
    if action == 'status':
        if journal.type != 'quest' or payload.get('status') not in shapes.QUEST_STATUSES:
            raise JournalError('Invalid quest status.')
        journal.data = shapes.normalize_quest_data(journal.data)
        journal.data['status'] = payload['status']
    elif action.startswith('board-'):
        if journal.type != 'quest_board':
            raise JournalError('Choose a quest board.')
        if action == 'board-reorder':
            raw = payload.get('ordered_quest_ids')
            if not isinstance(raw, list): raise JournalError('Invalid quest order.')
            ids = [identifier(value) for value in raw]
            links = {link.quest_id: link for link in journal.board_links.all()}
            if len(ids) != len(set(ids)) or set(ids) != set(links):
                raise JournalError('The board changed. Try ordering its quests again.')
            for index, quest_id in enumerate(ids):
                link = links[quest_id]; link.sort_order = (index+1)*10; link.save(update_fields=['sort_order'])
        else:
            quest = get(payload.get('quest_id'), who)
            if quest.type != 'quest': raise JournalError('Choose a quest.')
            link = journal.board_links.filter(quest=quest).first()
            if action == 'board-add':
                if not link:
                    last = journal.board_links.order_by('-sort_order').first()
                    BoardEntry.objects.create(board=journal, quest=quest, sort_order=(last.sort_order if last else 0)+10)
            elif action == 'board-remove':
                if link: link.delete()
            elif action == 'board-pin':
                if not link or type(payload.get('pinned')) is not bool: raise JournalError('Invalid board entry.')
                link.pinned = payload['pinned']; link.save(update_fields=['pinned'])
            else: raise JournalError('Unknown board command.')
    elif action in {'roll','reset'}:
        if journal.type != 'roll_table' or not gm:
            raise JournalError('Only the GM can roll or reset a table.')
        table = shapes.normalize_roll_table_data(journal.data)
        if action == 'reset':
            for entry in table['entries']: entry['drawn'] = False
        else:
            eligible = [e for e in table['entries'] if e['active'] and (table['withReplacement'] or not e['drawn'])]
            total = sum(e['weight'] for e in eligible)
            if not total: raise JournalError('This table has no available entries.')
            # Reuse the chat flood limit across sockets and roll types.
            locked = Membership.objects.select_for_update().get(pk=who.pk)
            try: consume_limit(locked)
            except AuthError: raise JournalError('Too many rolls. Please wait a moment.') from None
            ticket = secrets.randbelow(total) + 1
            cursor = ticket
            for entry in eligible:
                cursor -= entry['weight']
                if cursor <= 0: break
            if not table['withReplacement']: entry['drawn'] = True
            roll = {'kind':'journal.roll_table', 'title':journal.title, 'journalId':str(journal.pk),
                    'entry':deepcopy(entry), 'ticket':ticket, 'totalWeight':total,
                    'secret':table['resultVisibility']=='gm'}
            expression = f'1d{total}'
            roll.update({'expression':expression, 'result':{'value':{'kind':'number','value':ticket},
                'rolls':[{'sourceSpan':{'start':0,'end':len(expression)},
                          'facts':[{'id':'draw','face':ticket,'cause':{'kind':'initial'}}],
                          'selection':{'draw':'active'}}]}})
            from gravewright.chat.context import scene_for
            try: scene = scene_for(who, payload.get('mapId'), payload.get('block_id'))
            except AuthError: raise JournalError('Scene not found or access denied.') from None
            message = Message.objects.create(campaign_id=who.campaign_id, author_id=who.user_id, scene=scene,
                author_name=who.user.name, request_id=uuid.uuid4(), text=f"{journal.title} — {entry['name']}: {entry['result']}", visibility=table['resultVisibility'], roll=roll)
            if roll['secret']:
                Recipient.objects.bulk_create([Recipient(message=message, user_id=pk) for pk in Membership.objects.filter(
                    campaign_id=who.campaign_id, role='gm').values_list('user_id',flat=True)])
            journal.data = table
            return {'entry':deepcopy(entry), 'message_id':message.pk}
        journal.data = table
    else:
        raise JournalError('Unknown journal command.')
    return {}


def chat_event(message_id, campaign_id):
    message = Message.objects.get(pk=message_id, campaign_id=campaign_id)
    return {'type':'room.message', 'message':public_message(message),
            'audience':[str(pk) for pk in message.recipients.values_list('user_id',flat=True)] if message.visibility=='gm' else None}
