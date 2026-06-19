from __future__ import annotations

from dataclasses import dataclass

from app.business.permissions import PermissionService
from app.contracts.transport import RealtimeGatewayContract
from app.engine.dice.roll_service import RollService
from app.helpers.async_blocking import run_blocking
from app.domain.chat import ChatMessageKind
from app.domain.chat import ChatVisibility
from app.domain.permissions.permissions import TablePermission
from app.domain.roles import PlayerRole
from app.persistence.repositories.campaign_repository import CampaignRepository
from app.persistence.repositories.chat_message_repository import ChatMessageRepository
from app.realtime.events import TransportEvent


@dataclass(frozen=True)
class ChatResult:
    success: bool
    error_key: str | None = None


def _strip_command(content: str, *names: str) -> str | None:
    """Return the argument after a `/name ` command prefix, or None if no match."""
    for name in names:
        prefix = f"{name} "
        if content.startswith(prefix):
            return content[len(prefix):].strip()
    return None


class ChatService:
    MAX_CONTENT_LEN = 2000

    def __init__(self) -> None:
        self.campaigns = CampaignRepository()
        self.permissions = PermissionService()
        self.roller = RollService()
        self.messages = ChatMessageRepository()

    async def send_system_message(
        self,
        *,
        campaign_id: str,
        content: str,
        transport: RealtimeGatewayContract,
        metadata: dict | None = None,
    ) -> ChatResult:
        """Broadcast a public, system-authored message (combat ticks, automation).

        Live-only — like whispers/secret rolls, system notices are not persisted
        (the chat_messages table requires a real author_user_id).
        """
        content = (content or "").strip()
        if not content:
            return ChatResult(success=False, error_key="game.chat.errors.empty_message")
        content = content[: self.MAX_CONTENT_LEN]

        message_id = self.messages.generate_id()
        await transport.chat_to_room(
            room_id=campaign_id,
            message={
                "message_id": message_id,
                "room_id": campaign_id,
                "author": "Sistema",
                "author_id": "",
                "role": ChatVisibility.SYSTEM.value,
                "kind": ChatMessageKind.SYSTEM,
                "content": content,
                "metadata": metadata or {},
            },
        )
        return ChatResult(success=True)

    def create_roll_message(
        self,
        *,
        campaign_id: str,
        author_user_id: str,
        author_name: str,
        actor_name: str | None,
        label: str | None,
        expression: str | None,
        groups: list[dict] | None,
        modifier: int | None,
        total: int | None,
        visibility: str,
        metadata: dict | None,
    ) -> dict | None:
        role = self.campaigns.get_member_role(
            campaign_id=campaign_id,
            user_id=author_user_id,
        )
        if role is None:
            return None

        message_id = self.messages.generate_id()
        gm_only = visibility in {"gm", "gm_only", "private", "self"}
        chat_visibility = ChatVisibility.GM_ONLY if gm_only else ChatVisibility.PUBLIC
        author = actor_name or author_name
        self.messages.create(
            message_id=message_id,
            campaign_id=campaign_id,
            author_user_id=author_user_id,
            author_name=author,
            author_role=role,
            kind=ChatMessageKind.ROLL,
            content=label,
            expression=expression,
            groups=groups,
            modifier=modifier,
            total=total,
            visibility=chat_visibility,
            metadata=metadata,
        )

        return {
            "message_id": message_id,
            "room_id": campaign_id,
            "author": author,
            "author_id": author_user_id,
            "role": role,
            "kind": ChatMessageKind.ROLL,
            "content": label,
            "expression": expression,
            "groups": groups,
            "modifier": modifier,
            "total": total,
            "metadata": metadata,
            "gm_only": gm_only,
        }

    async def send_message(
        self,
        *,
        campaign_id: str,
        sender_user_id: str,
        sender_name: str,
        content: str,
        transport: RealtimeGatewayContract,
    ) -> ChatResult:
        # P0: every DB touch here is offloaded off the event loop via run_blocking
        # so a slow/contended write never stalls the realtime gateway.
        role = await run_blocking(
            self.campaigns.get_member_role,
            campaign_id=campaign_id,
            user_id=sender_user_id,
        )
        if role is None:
            return ChatResult(success=False, error_key="game.chat.errors.not_a_member")

        content = content.strip()

        if not content:
            return ChatResult(success=False, error_key="game.chat.errors.empty_message")

        if len(content) > self.MAX_CONTENT_LEN:
            return ChatResult(success=False, error_key="game.chat.errors.message_too_long")

        message_id = self.messages.generate_id()
        base: dict = {
            "message_id": message_id,
            "room_id": campaign_id,
            "author": sender_name,
            "author_id": sender_user_id,
            "role": role,
        }

        gmroll_expr = _strip_command(content, "/gmroll")
        if gmroll_expr is not None:
            return await self._send_gmroll(
                campaign_id=campaign_id,
                sender_user_id=sender_user_id,
                expression=gmroll_expr,
                base=base,
                transport=transport,
            )

        roll_expr = _strip_command(content, "/roll", "/r")
        if roll_expr is not None:
            result = self.roller.evaluate(roll_expr)
            if result is None:
                return ChatResult(success=False, error_key="game.chat.errors.invalid_roll")

            await run_blocking(
                self.messages.create,
                message_id=message_id,
                campaign_id=campaign_id,
                author_user_id=sender_user_id,
                author_name=sender_name,
                author_role=role,
                kind=ChatMessageKind.ROLL,
                content=None,
                expression=result.expression,
                groups=result.groups,
                modifier=result.modifier,
                total=result.total,
                visibility=ChatVisibility.PUBLIC,
            )
            await transport.chat_to_room(
                room_id=campaign_id,
                message={
                    **base,
                    "kind": ChatMessageKind.ROLL,
                    "expression": result.expression,
                    "groups": result.groups,
                    "modifier": result.modifier,
                    "total": result.total,
                },
            )
            return ChatResult(success=True)

        if content.startswith("/w "):
            return await self._send_whisper(
                campaign_id=campaign_id,
                sender_user_id=sender_user_id,
                arg=content[3:].strip(),
                base=base,
                transport=transport,
            )

        if content.startswith("/me "):
            emote_text = content[4:].strip()
            await run_blocking(
                self.messages.create,
                message_id=message_id,
                campaign_id=campaign_id,
                author_user_id=sender_user_id,
                author_name=sender_name,
                author_role=role,
                kind=ChatMessageKind.EMOTE,
                content=emote_text,
                expression=None,
                groups=None,
                modifier=None,
                total=None,
                visibility=ChatVisibility.PUBLIC,
            )
            await transport.chat_to_room(
                room_id=campaign_id,
                message={**base, "kind": ChatMessageKind.EMOTE, "content": emote_text},
            )

        elif content.startswith("/gm "):
            gm_text = content[4:].strip()
            await run_blocking(
                self.messages.create,
                message_id=message_id,
                campaign_id=campaign_id,
                author_user_id=sender_user_id,
                author_name=sender_name,
                author_role=role,
                kind=ChatMessageKind.TEXT,
                content=gm_text,
                expression=None,
                groups=None,
                modifier=None,
                total=None,
                visibility=ChatVisibility.GM_ONLY,
            )
            await transport.chat_to_gm(
                room_id=campaign_id,
                message={**base, "kind": ChatMessageKind.TEXT, "content": gm_text},
            )

        else:
            await run_blocking(
                self.messages.create,
                message_id=message_id,
                campaign_id=campaign_id,
                author_user_id=sender_user_id,
                author_name=sender_name,
                author_role=role,
                kind=ChatMessageKind.TEXT,
                content=content,
                expression=None,
                groups=None,
                modifier=None,
                total=None,
                visibility=ChatVisibility.PUBLIC,
            )
            await transport.chat_to_room(
                room_id=campaign_id,
                message={**base, "kind": ChatMessageKind.TEXT, "content": content},
            )

        return ChatResult(success=True)

    async def _send_gmroll(
        self,
        *,
        campaign_id: str,
        sender_user_id: str,
        expression: str,
        base: dict,
        transport: RealtimeGatewayContract,
    ) -> ChatResult:
        if not await run_blocking(
            self.permissions.can,
            user_id=sender_user_id,
            campaign_id=campaign_id,
            permission=TablePermission.CHAT_SEND_TO_GM,
        ):
            return ChatResult(success=False, error_key="permissions.errors.denied")

        result = self.roller.evaluate(expression)
        if result is None:
            return ChatResult(success=False, error_key="game.chat.errors.invalid_roll")

        members = await run_blocking(self.campaigns.list_members, campaign_id=campaign_id)
        gm_ids = [
            member["user_id"]
            for member in members
            if member["role"] == PlayerRole.GM.value
        ]
        await transport.chat_whisper(
            room_id=campaign_id,
            sender_player_id=sender_user_id,
            target_player_ids=[uid for uid in gm_ids if uid != sender_user_id],
            message={
                **base,
                "kind": ChatMessageKind.ROLL,
                "secret": True,
                "expression": result.expression,
                "groups": result.groups,
                "modifier": result.modifier,
                "total": result.total,
            },
        )
        return ChatResult(success=True)

    async def _send_whisper(
        self,
        *,
        campaign_id: str,
        sender_user_id: str,
        arg: str,
        base: dict,
        transport: RealtimeGatewayContract,
    ) -> ChatResult:
        if not await run_blocking(
            self.permissions.can,
            user_id=sender_user_id,
            campaign_id=campaign_id,
            permission=TablePermission.CHAT_WHISPER,
        ):
            return ChatResult(success=False, error_key="permissions.errors.denied")

        target_ids, target_name, text = await run_blocking(
            self._resolve_whisper, campaign_id=campaign_id, arg=arg
        )
        if not target_ids:
            return ChatResult(success=False, error_key="game.chat.errors.invalid_whisper_target")
        if not text:
            return ChatResult(success=False, error_key="game.chat.errors.empty_message")

        await transport.chat_whisper(
            room_id=campaign_id,
            sender_player_id=sender_user_id,
            target_player_ids=[uid for uid in target_ids if uid != sender_user_id],
            message={
                **base,
                "kind": ChatMessageKind.TEXT,
                "content": text,
                "target_names": [target_name],
            },
        )
        return ChatResult(success=True)

    def _resolve_whisper(
        self,
        *,
        campaign_id: str,
        arg: str,
    ) -> tuple[list[str], str, str]:
        """Resolve `<member name> <message>`. Matches the longest member name prefix."""
        arg = arg.strip()
        if not arg:
            return [], "", ""

        lowered = arg.lower()
        members = self.campaigns.list_members(campaign_id=campaign_id)

        best_name: str | None = None
        for member in sorted(members, key=lambda m: len(m["name"] or ""), reverse=True):
            name = (member["name"] or "").strip()
            if not name:
                continue
            name_lower = name.lower()
            if lowered == name_lower or lowered.startswith(f"{name_lower} "):
                best_name = name
                break

        if best_name is None:
            return [], "", ""

        target_ids = [
            member["user_id"]
            for member in members
            if (member["name"] or "").strip().lower() == best_name.lower()
        ]
        message = arg[len(best_name):].strip()
        return target_ids, best_name, message

    async def delete_message(
        self,
        *,
        campaign_id: str,
        user_id: str,
        message_id: str,
        transport: RealtimeGatewayContract,
    ) -> ChatResult:
        role = await run_blocking(
            self.campaigns.get_member_role,
            campaign_id=campaign_id,
            user_id=user_id,
        )
        if role is None:
            return ChatResult(success=False, error_key="game.chat.errors.not_a_member")

        message = await run_blocking(
            self.messages.get_for_campaign,
            campaign_id=campaign_id,
            message_id=message_id,
        )
        if message is None:
            return ChatResult(success=False, error_key="game.chat.errors.not_found")

        can_delete_any = await run_blocking(
            self.permissions.can,
            user_id=user_id,
            campaign_id=campaign_id,
            permission=TablePermission.CHAT_DELETE_ANY,
        )
        can_delete_own = (
            message["author_user_id"] == user_id
            and await run_blocking(
                self.permissions.can,
                user_id=user_id,
                campaign_id=campaign_id,
                permission=TablePermission.CHAT_DELETE_OWN,
            )
        )

        if not can_delete_any and not can_delete_own:
            return ChatResult(success=False, error_key="permissions.errors.denied")

        await run_blocking(
            self.messages.delete_for_campaign,
            campaign_id=campaign_id,
            message_id=message_id,
        )
        await transport.to_room(
            room_id=campaign_id,
            event=TransportEvent.CHAT_MESSAGE_DELETED,
            payload={"room_id": campaign_id, "message_id": message_id},
        )
        return ChatResult(success=True)

    async def clear_messages(
        self,
        *,
        campaign_id: str,
        user_id: str,
        transport: RealtimeGatewayContract,
    ) -> ChatResult:
        role = await run_blocking(
            self.campaigns.get_member_role,
            campaign_id=campaign_id,
            user_id=user_id,
        )
        if role is None:
            return ChatResult(success=False, error_key="game.chat.errors.not_a_member")

        if not await run_blocking(
            self.permissions.can,
            user_id=user_id,
            campaign_id=campaign_id,
            permission=TablePermission.CHAT_DELETE_ANY,
        ):
            return ChatResult(success=False, error_key="permissions.errors.denied")

        await run_blocking(self.messages.delete_all_for_campaign, campaign_id=campaign_id)
        await transport.to_room(
            room_id=campaign_id,
            event=TransportEvent.CHAT_MESSAGES_CLEARED,
            payload={"room_id": campaign_id},
        )
        return ChatResult(success=True)
