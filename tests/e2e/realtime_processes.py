"""Real Redis and two independent ASGI processes, with an isolated database."""
import subprocess
import uuid
from migration_closure import main


def check(gm,player,data,output,restart):
    def send(page,text):
        page.evaluate("text=>sockets.at(-1).send(JSON.stringify({type:'chat.say',payload:{requestId:crypto.randomUUID(),text}}))",text)
    def received(page,text):
        page.wait_for_function("text=>document.querySelector('#chat-panel')?.textContent.includes(text)",arg=text)
    gm.wait_for_function('window.gravewrightRealtime')
    player.wait_for_function('window.gravewrightRealtime')
    send(gm,'Across workers one');received(player,'Across workers one')
    send(player,'Across workers two');received(gm,'Across workers two')
    print('Messages delivered in both directions through Redis between two ASGI processes',flush=True)
    previous=player.evaluate('sockets.length')
    restart(1)
    player.wait_for_function('count=>sockets.length>count&&sockets.at(-1).readyState===1',arg=previous,timeout=30000)
    send(gm,'After worker restart');received(player,'After worker restart')
    player.reload()
    received(player,'Across workers one');received(player,'After worker restart')
    print('Worker restart, WebSocket reconnection and persisted chat history verified',flush=True)


if __name__=='__main__':
    name='gravewright-test-'+uuid.uuid4().hex[:12]
    subprocess.run(['docker','run','--rm','-d','--name',name,'--memory','128m','-p','127.0.0.1::6379','redis:7-alpine','redis-server','--save','','--appendonly','no'],check=True,stdout=subprocess.DEVNULL)
    try:
        mapped=subprocess.check_output(['docker','port',name,'6379/tcp'],text=True).strip()
        main(check,server_count=2,environment=lambda temp:{'GRAVEWRIGHT_REDIS_URL':'redis://'+mapped+'/0'})
    finally:
        subprocess.run(['docker','rm','-f',name],check=False,stdout=subprocess.DEVNULL)
