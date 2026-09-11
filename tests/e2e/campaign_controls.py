"""Table entry, expiring read-only stream sessions and realtime removal."""
from migration_closure import main
from playwright.sync_api import expect


def check(gm,player,data,output):
    gm.wait_for_function("document.querySelector('#table-workspace').dataset.onboardingReady==='true'")
    expect(gm.get_by_role('heading',name='Prepare your first session')).to_have_count(0)
    expect(gm.locator('[data-campaign-help]')).to_have_count(0)
    link=gm.evaluate("""async p=>{const c=await(await fetch('/__gravewright/csrf')).json();const r=await fetch('/api/containers/'+p.campaign+'/streamer-link',{method:'POST',headers:{[c.header||'X-CSRF-Token']:c.token}});if(!r.ok)throw Error(await r.text());return r.json();}""",data)
    context=gm.context.browser.new_context(viewport={'width':1440,'height':1000})
    try:
        page=context.new_page();errors=[];page.on('pageerror',lambda e:errors.append(str(e)))
        page.goto(link['url'])
        page.wait_for_function("document.querySelector('#table-workspace')?.dataset.role==='streamer'")
        page.wait_for_function("document.querySelector('[data-presence]')?.dataset.presence==='seated'")
        expect(page.locator('.game-board__surface')).to_be_visible()
        # A separate hostile socket must not bypass UI restrictions.
        result=page.evaluate("""p=>new Promise((resolve,reject)=>{const ws=new WebSocket(location.origin.replace('http','ws')+'/ws/tables/'+p.campaign+'/');const timer=setTimeout(()=>{ws.close();reject(Error('No read-only response'));},10000);ws.onmessage=e=>{const m=JSON.parse(e.data);if(m.type==='table.joined')ws.send(JSON.stringify({type:'chat.say',payload:{text:'forbidden',clientId:crypto.randomUUID()}}));if(m.type==='error'){clearTimeout(timer);ws.close();resolve(m.payload);}};})""",data)
        assert result['code']=='read_only',result
        response=page.request.post(page.url.split('/game/')[0]+'/api/containers',data={'name':'Forbidden'})
        assert response.status==403
        gm.evaluate("""async p=>{const c=await(await fetch('/__gravewright/csrf')).json();await fetch('/api/containers/'+p.campaign+'/streamer-link/revoke',{method:'POST',headers:{[c.header||'X-CSRF-Token']:c.token}});}""",data)
        page.wait_for_function("document.querySelector('[data-presence]')?.dataset.presence!=='seated'")
        assert page.request.get(page.url.split('/game/')[0]+'/api/containers/'+data['campaign']+'/modules-native/cards').status==403
        assert not errors,errors
    finally:context.close()
    gm.evaluate("""async p=>{const c=await(await fetch('/__gravewright/csrf')).json();const r=await fetch('/api/containers/'+p.campaign+'/members/ban',{method:'POST',headers:{[c.header||'X-CSRF-Token']:c.token,'Content-Type':'application/json'},body:JSON.stringify({user_id:p.player_id})});if(!r.ok)throw Error(await r.text());}""",data)
    player.wait_for_function("document.querySelector('[data-presence]')?.dataset.presence!=='seated'")
    print('Direct table entry, streamer read-only socket, revocation and participant removal passed',flush=True)

if __name__=='__main__':main(check)
