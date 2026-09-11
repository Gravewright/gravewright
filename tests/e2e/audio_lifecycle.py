"""Actual browser media transport on two clients; no production accounts."""
from migration_closure import main

SEED = '''
import wave
from gravewright.audio.models import Track
raw=BytesIO()
with wave.open(raw,'wb') as stream:
 stream.setnchannels(1);stream.setsampwidth(1);stream.setframerate(8000);stream.writeframes(bytes([128])*16000)
track=Track.objects.create(campaign=c,name='Short effect',kind='effect',duration=2,loop=False,file=ContentFile(raw.getvalue(),name='effect.wav'))
result['track']=str(track.pk)
'''


def check(gm, player, data, output):
    for page in (gm, player):
        page.on('pageerror',lambda error:print('Browser error:',error,flush=True))
        page.wait_for_function('window.gravewrightTableMedia && window.gravewrightRealtime')
        page.evaluate('''()=>{
          window.observedAudio=[];
          const NativeAudio=window.Audio;
          window.Audio=function(...args){const audio=new NativeAudio(...args);observedAudio.push(audio);return audio};
        }''')
        page.get_by_role('button',name='Enable audio',exact=True).click()
    def command(action):
        return gm.evaluate('''async ({action,scene,track,campaign})=>{
          const state=await (await fetch('/api/containers/'+campaign+'/modules-native/audio?sceneId='+scene)).json();
          return window.gravewrightRealtime.moduleCommand('audio',action,{sceneId:scene,trackId:track,version:state.version});
        }''',{'action':action,'scene':data['map'],'track':data['track'],'campaign':data['campaign']})
    command('play')
    for page in (gm,player):
        page.wait_for_function('observedAudio.some(a=>!a.paused&&a.currentTime>0)')
    for page in (gm,player):
        page.wait_for_function('observedAudio.length>0&&observedAudio.every(a=>a.paused&&(a.ended||!a.getAttribute("src")))',timeout=10000)
    command('play')
    for page in (gm,player):
        page.wait_for_function('observedAudio.length>=2&&!observedAudio.at(-1).paused&&observedAudio.at(-1).currentTime>0')
    command('pause')
    for page in (gm,player):page.wait_for_function('observedAudio.at(-1).paused')
    command('play')
    for page in (gm,player):page.wait_for_function('!observedAudio.at(-1).paused')
    print('Two clients: real HTMLAudio playback, natural end, replay, pause and resume passed',flush=True)


if __name__=='__main__':main(check,seed_extra=SEED)
