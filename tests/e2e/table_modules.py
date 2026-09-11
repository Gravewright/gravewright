from migration_closure import main


def check(gm,player,data,output):
    errors=[]
    gm.on('pageerror',lambda error:errors.append(str(error)))
    gm.wait_for_function('window.gravewrightTableMedia && window.gravewrightRealtime')
    # Native modules use the same authenticated WebSocket as the rest of the table.
    deck=gm.evaluate("""async()=>await window.gravewrightRealtime.moduleCommand('cards','create',{name:'E2E Deck',cards:['Ace','Two']})""")
    gm.get_by_role('button',name='Your hand',exact=True).click()
    gm.locator('.card-hand').wait_for()
    assert gm.locator('.card-hand select').first.input_value()==deck['id']
    gm.evaluate("window.cardStates=[];window.addEventListener('gravewright:resources',e=>{if(e.detail.module==='cards')window.cardStates.push(e.detail.state)})")
    player.evaluate("async id=>window.gravewrightRealtime.moduleCommand('cards','draw',{deck_instance_id:id,count:1})",deck['id'])
    gm.wait_for_function("window.cardStates.some(s=>s.decks.some(d=>d.draw_count===1))")
    assert gm.evaluate('window.cardStates.at(-1).hand.length')==0
    print('Card hand and private WebSocket delivery verified',flush=True)
    gm.keyboard.press('Control+k')
    gm.locator('[data-command-palette-input]').fill('Scene')
    gm.wait_for_timeout(400)
    gm.keyboard.press('Escape')
    print('Command palette mounted',flush=True)
    player.evaluate("window.markerState=null;window.addEventListener('gravewright:map-layers',e=>window.markerState=e.detail)")
    gm.get_by_role('button',name='Shapes',exact=True).click()
    surface=gm.locator('.game-board__surface').bounding_box()
    gm.mouse.move(surface['x']+450,surface['y']+200)
    gm.mouse.down()
    gm.mouse.move(surface['x']+650,surface['y']+260,steps=8)
    gm.mouse.up()
    player.wait_for_function('window.markerState?.markers?.length===1')
    gm.keyboard.press('Escape')
    print('Shared marker delivered to player',flush=True)
    # Escape closes the shape editor; selecting a token requires Select mode.
    gm.get_by_role('button',name='Select',exact=True).click()
    gm.get_by_role('button',name='Token: Fighter',exact=True).click()
    gm.locator('[data-native-directory-toggle="combat"]').click()
    gm.locator('#combat-panel').wait_for(state='visible')
    gm.locator('#combat-panel [data-combat-action="combatants/add-selected"]').click()
    gm.locator('#combat-panel [data-combat-initiative]').fill('12 + A')
    gm.locator('#combat-panel [data-combat-initiative]').press('Tab')
    gm.locator('#combat-panel [data-combat-action="start"]').click()
    gm.locator('#combat-panel [data-combat-action="turn/next"]').click()
    gm.locator('#combat-panel .gw-combat-header__title').get_by_text('Round 2',exact=True).wait_for()
    print('Combat selection, textual initiative and turn advancement verified',flush=True)
    gm.locator('#combat-panel [data-close]').click()
    gm.locator('[data-native-directory-toggle="items"]').click()
    gm.locator('#items-panel').wait_for(state='visible')
    gm.locator('#items-panel [data-close]').click()
    gm.get_by_role('button',name='Individual mixer',exact=True).click()
    gm.locator('.individual-audio__mixer').wait_for(state='visible')
    assert gm.locator('.individual-audio__mixer input').count()==4
    gm.evaluate('''async()=>{
      const data=new Uint8Array(8044),view=new DataView(data.buffer);
      const text=(at,s)=>[...s].forEach((c,i)=>data[at+i]=c.charCodeAt(0));
      text(0,'RIFF');view.setUint32(4,8036,true);text(8,'WAVEfmt ');view.setUint32(16,16,true);view.setUint16(20,1,true);view.setUint16(22,1,true);view.setUint32(24,8000,true);view.setUint32(28,8000,true);view.setUint16(32,1,true);view.setUint16(34,8,true);text(36,'data');view.setUint32(40,8000,true);data.fill(128,44);
      await window.gravewrightTableMedia.upload(new File([data],'silence.wav',{type:'audio/wav'}));
      window.gravewrightTableMedia.showAudio();
    }''')
    gm.locator('.audio-panel').wait_for(state='visible')
    gm.locator('.audio-panel__list').get_by_role('button',name='Scene',exact=True).first.click()
    gm.locator('.audio-panel').get_by_role('button',name='Pause',exact=True).first.wait_for()
    gm.locator('.audio-panel').get_by_role('button',name='Pause',exact=True).first.click()
    gm.screenshot(path=str(output/'table-modules.png'))
    assert not errors,errors
    print('Directories and individual mixer mounted without JavaScript errors',flush=True)


if __name__=='__main__':
    main(check,seed_extra="""
from gravewright.actors.models import Actor
from gravewright.tokens.models import Token
from gravewright.pdf_system.schema import normalize
actor=Actor.objects.create(campaign=c,name='Fighter',data=normalize({}),permissions={str(player.pk):'owner'})
Token.objects.create(scene=s,actor=actor,grid_x=3,grid_y=4)
""")
