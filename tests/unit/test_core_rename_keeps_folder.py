from app.engine.actors.actor_service import ActorService
from app.engine.items.item_service import ItemService
from app.persistence.repositories.actor_folder_repository import ActorFolderRepository
from app.persistence.repositories.actor_repository import ActorRepository
from app.persistence.repositories.item_folder_repository import ItemFolderRepository
from app.persistence.repositories.item_repository import ItemRepository
from tests.conftest import seed_campaign, seed_user


def test_renaming_actor_without_folder_field_keeps_its_folder(db):
    gm_id = seed_user(name="GM", email="actor-rename-folder@test.com")
    campaign_id = seed_campaign(gm_id)
    folder_id = ActorFolderRepository().create(
        campaign_id=campaign_id, created_by_user_id=gm_id, name="Heroes"
    )
    repository = ActorRepository()
    actor_id = repository.create(
        campaign_id=campaign_id,
        system_id="test-system",
        actor_type="character",
        name="Old name",
        created_by_user_id=gm_id,
        folder_id=folder_id,
    )

    result = ActorService().update_core(
        actor_id=actor_id, user_id=gm_id, name="New name"
    )

    actor = repository.get(actor_id)
    assert result.success
    assert actor["name"] == "New name"
    assert actor["folder_id"] == folder_id


def test_renaming_item_without_folder_field_keeps_its_folder(db):
    gm_id = seed_user(name="GM", email="item-rename-folder@test.com")
    campaign_id = seed_campaign(gm_id)
    folder_id = ItemFolderRepository().create(
        campaign_id=campaign_id, created_by_user_id=gm_id, name="Equipment"
    )
    repository = ItemRepository()
    item_id = repository.create(
        campaign_id=campaign_id,
        system_id="test-system",
        item_type="equipment",
        name="Old name",
        created_by_user_id=gm_id,
        folder_id=folder_id,
    )

    result = ItemService().update_core(
        item_id=item_id, user_id=gm_id, name="New name"
    )

    item = repository.get(item_id)
    assert result.success
    assert item["name"] == "New name"
    assert item["folder_id"] == folder_id
