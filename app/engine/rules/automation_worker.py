"""Small lifecycle host for durable registered-action jobs."""

from __future__ import annotations

import asyncio
import os
import uuid
from dataclasses import dataclass

from app.engine.rules.automation_service import AutomationService
from app.helpers.async_blocking import run_blocking
from app.engine.sdk.directed_interaction_service import DirectedInteractionService
from app.engine.sdk.durable_workflow_service import DurableWorkflowService
from app.engine.sdk.gameplay_flow_service import GameplayFlowService
from app.engine.sdk.semantic_timeline_service import SemanticTimelineService
from app.persistence.repositories.semantic_instance_repository import SemanticInstanceRepository
import time
from app.realtime.events import TransportEvent
from app.realtime.transport import RealtimeTransport


@dataclass
class _Worker:
    task: asyncio.Task
    stop: asyncio.Event


# A process can host more than one ASGI lifespan loop in tests and embedding.
# asyncio primitives are loop-bound, so a single module-global task is unsafe.
_workers: dict[asyncio.AbstractEventLoop, _Worker] = {}


async def _emit_timeline_cues(campaign_id: str, timeline: dict) -> None:
    transport=RealtimeTransport()
    for cue in timeline.pop("_cueEvents",[]):
        value=cue.get("value") if isinstance(cue.get("value"),dict) else {};kind=cue.get("type")
        if kind=="AUDIO_PLAY":await transport.to_players(player_ids=((value.get("audience") or {}).get("ids") or []),event=TransportEvent.AUDIO_CHANGED,payload={"room_id":campaign_id,"playback_id":value.get("id"),"state":value.get("state"),"playback":value,"schema_version":1})
        elif kind=="PRESENTATION_SHOW":await transport.to_players(player_ids=list(dict.fromkeys(i for i in [*((value.get("audience") or {}).get("ids") or []),value.get("ownerUserId")] if i)),event=TransportEvent.UI_PRESENTATION_CHANGED,payload={"room_id":campaign_id,"presentation_id":value.get("id"),"presentation":value,"schema_version":1})
        elif kind=="NAVIGATION":await transport.to_players(player_ids=value.get("recipientIds",[]),event=TransportEvent.NAVIGATION_SCENE_CHANGED,payload={"room_id":campaign_id,"scene_id":value.get("sceneId"),"schema_version":1})
        else:
            event={"LIGHT_CREATE":TransportEvent.SCENE_LIGHTS_UPDATED,"SHADER_PRESET":TransportEvent.SCENE_SHADERS_UPDATED,"PARTICLE_CREATE":TransportEvent.SCENE_PARTICLES_UPDATED,"ACTION":TransportEvent.RULES_ACTION_COMPLETED}.get(kind)
            if event:await transport.to_room(room_id=campaign_id,event=event,payload={"room_id":campaign_id,"scene_id":timeline.get("sceneId"),"timeline_id":timeline.get("id"),"cue_id":cue.get("cueId"),"schema_version":1})

async def _emit_workflow_side_effects(campaign_id: str, workflow: dict) -> None:
    transport=RealtimeTransport();interaction=workflow.pop("_interactionEvent",None)
    if interaction:await transport.to_players(player_ids=list(dict.fromkeys([interaction["requester"],*interaction["recipients"]])),event=TransportEvent.INTERACTION_CHANGED,payload={"room_id":campaign_id,"interaction_id":interaction["id"],"schema_version":1})
    for action in workflow.pop("_actionEvents",[]):await transport.to_room(room_id=campaign_id,event=TransportEvent.RULES_ACTION_COMPLETED,payload={"room_id":campaign_id,"package_id":workflow.get("providerPackageId"),"action_id":action.get("action"),"version":action.get("version"),"execution_id":action.get("executionId"),"schema_version":1})


async def _loop(stop: asyncio.Event) -> None:
    worker_id = f"{os.getpid()}-{uuid.uuid4().hex}"
    while not stop.is_set():
        try:
            result = await run_blocking(AutomationService().run_one, worker_id=worker_id)
            expired = await run_blocking(DirectedInteractionService().expire_due)
            for item in expired:
                await RealtimeTransport().to_players(player_ids=item["recipients"],event=TransportEvent.INTERACTION_CHANGED,payload={"room_id":item["campaignId"],"interaction_id":item["id"],"schema_version":1})
            now=int(time.time())
            for campaign_id in await run_blocking(SemanticInstanceRepository().due_campaigns, now):
                workflows=await run_blocking(DurableWorkflowService().recover_campaign,campaign_id,now)
                flows=await run_blocking(GameplayFlowService().recover_campaign,campaign_id,now)
                timelines=await run_blocking(SemanticTimelineService().recover_campaign,campaign_id,now*1000)
                for workflow in workflows:
                    await _emit_workflow_side_effects(campaign_id,workflow)
                    await RealtimeTransport().to_room(room_id=campaign_id,event=TransportEvent.WORKFLOW_CHANGED,payload={"room_id":campaign_id,"workflow_id":workflow["id"],"status":workflow["status"],"schema_version":1})
                for timeline in timelines:
                    await _emit_timeline_cues(campaign_id,timeline)
                    await RealtimeTransport().to_room(room_id=campaign_id,event=TransportEvent.TIMELINE_CHANGED,payload={"room_id":campaign_id,"timeline_id":timeline["id"],"status":timeline["status"],"schema_version":1})
                for flow in flows:
                    await RealtimeTransport().to_room(room_id=campaign_id,event=TransportEvent.GAMEPLAY_FLOW_CHANGED,payload={"room_id":campaign_id,"flow_id":flow["id"],"status":flow["status"],"phase_id":flow.get("phaseId"),"schema_version":1})
            delay = 0.05 if result.value else 0.5
        except Exception:
            delay = 1.0
        try:
            await asyncio.wait_for(stop.wait(), timeout=delay)
        except TimeoutError:
            pass


async def start_automation_worker() -> None:
    loop = asyncio.get_running_loop()
    existing = _workers.get(loop)
    if existing and not existing.task.done():
        return
    stop = asyncio.Event()
    task = asyncio.create_task(_loop(stop), name="gravewright-automation-worker")
    _workers[loop] = _Worker(task=task, stop=stop)


async def stop_automation_worker() -> None:
    loop = asyncio.get_running_loop()
    worker = _workers.pop(loop, None)
    if worker is None:
        return
    worker.stop.set()
    try:
        await asyncio.wait_for(worker.task, timeout=2)
    except (TimeoutError, asyncio.CancelledError):
        worker.task.cancel()
