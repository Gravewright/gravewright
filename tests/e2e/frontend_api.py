"""Public global and mounted API, tested against real HTTP and two browsers."""
from migration_closure import main
from management import SEED

SEED = SEED.replace("reg.register('actor.directory'", "reg.api.ui.register('actor.directory'")
SEED = SEED.replace("const value=await block.host.call('actor.list',{});", "window.probeApi=block.api;const value={items:await block.api.actors.list()};")


def check(gm, player, data, output):
    errors=[]
    gm.on('pageerror', lambda error: errors.append(str(error)))
    gm.on('console', lambda message: print('Browser:', message.text, flush=True) if message.type == 'error' else None)
    player.on('pageerror', lambda error: errors.append(str(error)))
    gm.wait_for_function('window.gravewright && window.gravewrightRealtime')
    player.wait_for_function('window.gravewright && window.gravewrightRealtime')
    gm.evaluate("()=>{window.apiChanges=[];window.unsubscribeApi=gravewright.events.on('actors.changed', e=>window.apiChanges.push(e));}")
    actor=gm.evaluate("async()=>await gravewright.actors.create({name:'Global API hero'})")
    gm.evaluate('id=>window.createdApiActor=id',actor['id'])
    try:
        gm.wait_for_function('window.apiChanges.some(e=>e.actors?.some(a=>a.id===window.createdApiActor))', timeout=10000)
    except Exception:
        print('API diagnostic:', gm.evaluate('({events:window.apiChanges,actor:window.createdApiActor,context:gravewright.context,projected:gravewright.events.on.toString().includes("projected")})'), flush=True)
        raise
    assert gm.evaluate('async id=>(await gravewright.actors.get(id)).name',actor['id'])=='Global API hero'
    assert player.evaluate('async id=>(await gravewright.actors.list()).some(a=>a.id===id)',actor['id']) is False
    gm.evaluate("async id=>await gravewright.actors.update(id,{name:'Updated API hero'})",actor['id'])
    assert gm.evaluate('async id=>(await gravewright.actors.get(id)).name',actor['id'])=='Updated API hero'
    message=gm.evaluate("async()=>await gravewright.chat.send({text:'Domain API hello'})")
    delivered = player.locator(f'#chat-log [data-message-id="{message["id"]}"]')
    delivered.wait_for(state='attached')
    assert 'Domain API hello' in delivered.inner_text()
    print('Global API writes, private projections and live events passed',flush=True)
    gm.evaluate("""()=>{window.releaseApiUI=gravewright.ui.register('actor.directory',({root,api,onDispose})=>{
      root.dataset.globalProbe='true';root.textContent='Global surface';
      window.surfaceApi=api;onDispose(()=>window.surfaceDisposed=true);
    });}""")
    gm.wait_for_function("document.querySelector('[data-global-probe]')")
    gm.evaluate('window.releaseApiUI()')
    assert gm.evaluate('window.surfaceDisposed')
    assert gm.evaluate("async()=>{try{await window.surfaceApi.actors.list();return false;}catch(e){return e.code==='stale_context';}}")
    gm.get_by_role('button',name='Settings',exact=True).click()
    gm.get_by_role('button',name='Extensions',exact=True).click()
    gm.get_by_role('button',name='Activate',exact=True).click()
    gm.wait_for_function('window.probeApi')
    assert gm.evaluate('async()=> (await window.probeApi.actors.list()).length')==1
    gm.get_by_role('button',name='Deactivate',exact=True).click()
    gm.wait_for_function('window.moduleStops>=1')
    assert gm.evaluate("async()=>{try{await window.probeApi.actors.list();return false;}catch(e){return e.code==='stale_context';}}")
    base=gm.url.split('/game/')[0]
    gm.goto(base+'/inside')
    gm.wait_for_function('window.gravewright')
    assert len(gm.evaluate('async()=>await gravewright.campaigns.list()'))>=1
    assert gm.evaluate("typeof gravewright.ui.register")=='function'
    assert not errors,errors
    print('Global surfaces, module-scoped API disposal and Inside API passed',flush=True)


if __name__=='__main__':
    main(check,seed_extra=SEED,environment=lambda temp: {'GRAVEWRIGHT_MARKETPLACE_KEYS_FILE':temp+'/keys.json'})
