import io
import wave
from unittest.mock import patch
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase
from gravewright.table.tests import test_modules as fixtures
from gravewright.maps.services import MapError
from .models import Track, Playlist
from .metadata import inspect
from .soundtrack import gain_at


class AudioLifecycleTests(TestCase):
    setUp=fixtures.TableModuleTests.setUp
    command=fixtures.TableModuleTests.command
    state=fixtures.TableModuleTests.state

    def track(self):
        return Track.objects.create(campaign=self.campaign,name='Effect',duration=2,kind='effect',loop=False)

    def transport(self,action,sound,at,**extra):
        version=self.state('audio')['version']
        with patch('gravewright.audio.services.time.time',return_value=at):
            return self.command('audio',action,{'sceneId':str(self.scene.pk),'trackId':str(sound.pk),'version':version,**extra})

    def test_upload_reads_real_duration_and_rejects_false_headers(self):
        raw=io.BytesIO()
        with wave.open(raw,'wb') as stream:
            stream.setnchannels(1);stream.setsampwidth(1);stream.setframerate(8000);stream.writeframes(bytes(16000))
        self.client.force_login(self.gm)
        response=self.client.post(f'/api/containers/{self.campaign.pk}/media/audio',{'file':SimpleUploadedFile('sample.wav',raw.getvalue()),'purpose':'effect'})
        self.assertEqual(response.status_code,200,response.content)
        sound=Track.objects.get(pk=response.json()['id'])
        self.assertEqual(sound.duration,2);self.assertFalse(sound.loop)
        with self.assertRaises(MapError):inspect(io.BytesIO(b'RIFFxxxxWAVEgarbage'))

    def test_end_replay_pause_seek_and_non_looping_effects(self):
        sound=self.track()
        self.transport('play',sound,10,loop=True)
        with patch('gravewright.audio.services.time.time',return_value=11):
            playing=self.state('audio')['playback']['ambient'][0]
        self.assertFalse(playing['loop']);self.assertEqual(playing['position'],1)
        self.transport('pause',sound,11)
        self.transport('pause',sound,15)
        with patch('gravewright.audio.services.time.time',return_value=15):
            self.assertEqual(self.state('audio')['playback']['ambient'][0]['position'],1)
        self.transport('play',sound,16)
        with patch('gravewright.audio.services.time.time',return_value=20):
            done=self.state('audio')['playback']['ambient'][0]
        self.assertEqual(done['status'],'stopped');self.assertEqual(done['position'],2)
        self.transport('play',sound,21)
        with patch('gravewright.audio.services.time.time',return_value=21):
            replay=self.state('audio')['playback']['ambient'][0]
        self.assertEqual(replay['position'],0);self.assertNotEqual(playing['playId'],replay['playId'])
        with self.assertRaises(MapError):self.transport('seek',sound,22,position=3)

    def test_resume_does_not_rewind_an_already_playing_score(self):
        sound=self.track()
        playlist=Playlist.objects.create(campaign=self.campaign,name='Timeline',tracks=[{'soundId':str(sound.pk),'duration':20,'gain':1}],fade=0)
        with patch('gravewright.audio.soundtrack.time.time',return_value=10):
            started=self.command('audio','score-start',{'sceneId':str(self.scene.pk),'expectedVersion':0,'id':str(playlist.pk),'kind':'playlist'})
        with patch('gravewright.audio.soundtrack.time.time',return_value=15):
            resumed=self.command('audio','score-resume',{'sceneId':str(self.scene.pk),'expectedVersion':started['version']})
        self.assertEqual(resumed['position'],5)

    def test_interrupted_crossfade_keeps_current_outgoing_gains(self):
        sounds=[self.track() for _ in range(3)]
        playlists=[Playlist.objects.create(campaign=self.campaign,name='Mix',tracks=[{'soundId':str(s.pk),'duration':20,'gain':1}],fade=4) for s in sounds]
        version=0
        for at,playlist in enumerate(playlists):
            with patch('gravewright.audio.soundtrack.time.time',return_value=at):
                result=self.command('audio','score-start',{'sceneId':str(self.scene.pk),'expectedVersion':version,'id':str(playlist.pk),'kind':'playlist'})
                version=result['version']
        outgoing={r['asset']['id']:gain_at(r,2) for r in result['playbacks'] if r.get('fade')}
        self.assertAlmostEqual(outgoing[str(sounds[0].pk)],.1875)
        self.assertAlmostEqual(outgoing[str(sounds[1].pk)],.25)
