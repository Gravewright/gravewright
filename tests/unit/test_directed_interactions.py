import time
from app.engine.sdk.directed_interaction_service import DirectedInteractionService
from tests.conftest import seed_campaign, seed_member, seed_user

def _world():
    gm=seed_user(name="GM"); one=seed_user(name="One"); two=seed_user(name="Two"); campaign=seed_campaign(gm); seed_member(campaign,one,"player"); seed_member(campaign,two,"player"); return gm,one,two,campaign

def _request(service,campaign,gm,recipients,schema=None,**extra):
    values={"recipients":recipients,"title":"Reaction","text":"Use Shield?","responseSchema":schema or {"type":"boolean"},"deadline":int(time.time())+300,**extra}
    return service.request(campaign_id=campaign,user_id=gm,package_id="combat-addon",values=values)

def test_request_recipient_authority_privacy_and_reconnect(db):
    gm,one,two,campaign=_world(); service=DirectedInteractionService(); made=_request(service,campaign,gm,[one,two])
    assert made.success
    assert not service.respond(campaign_id=campaign,interaction_id=made.value["id"],user_id=gm,response=True).success
    answered=service.respond(campaign_id=campaign,interaction_id=made.value["id"],user_id=one,response=True,idempotency_key="retry-1")
    assert answered.success and list(answered.value["responses"])==[one]
    other=service.get(campaign_id=campaign,interaction_id=made.value["id"],user_id=two)
    assert other.success and other.value["responses"]=={}
    assert service.list(campaign_id=campaign,user_id=two,status="open",recipient_me=True).value[0]["id"]==made.value["id"]
    retry=service.respond(campaign_id=campaign,interaction_id=made.value["id"],user_id=one,response=True,idempotency_key="retry-1")
    assert retry.success

def test_typed_responses_duplicate_cancel_and_timeout(db):
    gm,one,_,campaign=_world(); service=DirectedInteractionService()
    schemas_values=[({"type":"single-choice","choices":[{"id":"a","label":"A"}]},"a"),({"type":"multi-choice","choices":[{"id":"a","label":"A"},{"id":"b","label":"B"}],"maxSelections":2},["a","b"]),({"type":"number","minimum":1,"maximum":3},2),({"type":"string","maxLength":4},"yes")]
    for schema,value in schemas_values:
        made=_request(service,campaign,gm,[one],schema)
        assert service.respond(campaign_id=campaign,interaction_id=made.value["id"],user_id=one,response=value).success
    made=_request(service,campaign,gm,[one]); assert service.cancel(campaign_id=campaign,interaction_id=made.value["id"],user_id=gm).success
    assert service.respond(campaign_id=campaign,interaction_id=made.value["id"],user_id=one,response=True).error_key.endswith("cancelled")
    expired=_request(service,campaign,gm,[one]); row=service._find(campaign,expired.value["id"]); payload=dict(row["payload"]); payload["deadline"]=int(time.time())-1
    service.store.put(namespace=service.NS,campaign_id=campaign,scope_id=service.SCOPE,owner_user_id=row["owner_user_id"],entry_key=row["entry_key"],audience=row["audience"],payload=payload,ttl_seconds=60,expected_version=row["version"])
    assert service.respond(campaign_id=campaign,interaction_id=expired.value["id"],user_id=one,response=True).error_key.endswith("expired")

def test_cross_campaign_and_invalid_schema_fail_closed(db):
    gm,one,_,campaign=_world(); outsider=seed_user(name="Outsider"); service=DirectedInteractionService()
    assert not _request(service,campaign,gm,[outsider]).success
    assert not _request(service,campaign,gm,[one],{"type":"arbitrary-json"}).success
