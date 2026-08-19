import json
from pathlib import Path


ROOT=Path(__file__).resolve().parents[2]


def test_semantic_runtime_sdk_is_bounded_and_fully_formalized():
    source=(ROOT/"static/js/sdk/gravewright-sdk.js").read_text(encoding="utf-8")
    for method in ("workflows.register","workflows.start","workflows.get","workflows.list","workflows.cancel","gameplay.flows.register","gameplay.flows.start","gameplay.flows.get","gameplay.flows.list","gameplay.flows.advance","gameplay.flows.submit","tokens.transfer","tokens.transferMany","timelines.register","timelines.start","timelines.get","timelines.list","timelines.cancel"):
        assert f'"sdk.{method}"' in source
    for module in ("durable_workflow_service","gameplay_flow_service","token_transfer_service",
                   "semantic_timeline_service"):
        service=(ROOT/f"app/engine/sdk/{module}.py").read_text(encoding="utf-8")
        for forbidden in ("eval(","exec(","callback_url","executeStep","RAW_GLSL","setTimeout"):
            assert forbidden not in service, module
    contract=json.loads((ROOT/"docs/sdk/_data/gravewright-sdk-1.json").read_text(encoding="utf-8"))
    assert contract["sdkVersion"]=="1"
    assert contract["genericAudit"]["unresolvedReturns"]==0
    assert contract["genericAudit"]["unresolvedParameters"]==0
    assert {"workflow.changed","gameplay.flow.changed","timeline.changed","tokens.transferred"}<={event["name"] for event in contract["events"]}


def test_semantic_runtime_method_capability_mapping_is_exact():
    capabilities=json.loads((ROOT/"app/engine/sdk/capabilities.json").read_text(encoding="utf-8"))["capabilities"]
    mapped={method:name for name,value in capabilities.items() for method in value.get("methods",[])}
    assert mapped["workflows.get"]=="workflows.read" and mapped["workflows.cancel"]=="workflows.control"
    assert mapped["gameplay.flows.submit"]=="gameplay.flows.participate"
    assert mapped["tokens.transferMany"]=="tokens.transfer"
    assert mapped["timelines.cancel"]=="timelines.control"
