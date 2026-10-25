"""Object bundles preserve campaign isolation and reuse existing source validation."""
from copy import deepcopy
import uuid
from django.test import TestCase, override_settings
from gravewright.maps import builder_presets, services
from gravewright.maps.models import BuilderObjectPreset
from gravewright.journals.services import JournalError
from . import test_builder_projects as fixtures


@override_settings(PASSWORD_HASHERS=['django.contrib.auth.hashers.MD5PasswordHasher'], ALLOWED_HOSTS=['testserver'])
class BuilderPresetTests(TestCase):
    setUp=fixtures.BuilderProjectTests.setUp
    asset=fixtures.BuilderProjectTests.asset

    def test_save_retry_validation_and_campaign_scoping(self):
        payload={'request_id':str(uuid.uuid4()),'name':'Room','document':deepcopy(self.doc)}
        result=builder_presets.save(self.campaign.pk,self.gm.pk,payload)
        self.assertEqual(builder_presets.save(self.campaign.pk,self.gm.pk,payload),result)
        self.assertEqual(BuilderObjectPreset.objects.count(),1)
        with self.assertRaises(services.MapError):
            builder_presets.save(self.campaign.pk,self.gm.pk,{**payload,'name':'Different operation'})
        detail=builder_presets.detail(self.campaign.pk,self.gm.pk,result['id'])
        self.assertEqual(detail['document']['floors'],self.doc['floors'])
        self.assertNotIn('document',builder_presets.catalog(self.campaign.pk,self.gm.pk)['presets'][0])
        with self.assertRaises((services.MapError,JournalError)):
            builder_presets.catalog(self.campaign.pk,self.player.pk)
        foreign=self.other.pk
        with self.assertRaises((services.MapError,JournalError)):
            builder_presets.detail(foreign,self.gm.pk,result['id'])
        with self.assertRaises((services.MapError,JournalError)):
            builder_presets.catalog(self.campaign.pk,self.streamer.pk)
        builder_presets.remove(self.campaign.pk,self.gm.pk,result['id'])
        self.assertEqual(BuilderObjectPreset.objects.count(),0)

    def test_invalid_asset_is_not_stored(self):
        document=deepcopy(self.doc);document['assets'][0]['assetId']=str(uuid.uuid4())
        with self.assertRaises(services.MapError):
            builder_presets.save(self.campaign.pk,self.gm.pk,{'request_id':str(uuid.uuid4()),'name':'Invalid','document':document})
        self.assertFalse(BuilderObjectPreset.objects.exists())
