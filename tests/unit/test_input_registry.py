from app.engine.sdk.input_registry_service import InputRegistryService
from tests.conftest import seed_campaign, seed_user


def test_declarative_commands_binding_conflict_and_reserved_shortcut(db):
    user=seed_user();campaign=seed_campaign(user);service=InputRegistryService()
    for package,command in (("bar","toggle"),("map","grid")):
        assert service.register(campaign_id=campaign,package_id=package,kind="command",definition={"id":command,"label":command,"contexts":["scene","text-input-excluded"],"registeredAction":f"{package}:do@1"}).success
    assert service.set_binding(campaign_id=campaign,user_id=user,package_id="bar",command_id="toggle",binding="Shift+H").success
    assert service.set_binding(campaign_id=campaign,user_id=user,package_id="map",command_id="grid",binding="Shift+H").error_key=="sdk.input.binding_conflict"
    assert service.set_binding(campaign_id=campaign,user_id=user,package_id="bar",command_id="toggle",binding="Ctrl+L").error_key=="sdk.input.binding_reserved"

