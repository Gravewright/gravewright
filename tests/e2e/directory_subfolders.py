"""Subfolders created from collapsed parents become visible in every directory."""
from playwright.sync_api import expect
from migration_closure import main

SEED = '''
from zipfile import ZipFile
from gravewright.modules.packages import host
manifest={'id':'example.folder-review','version':'0.1.0','name':'Folder review','description':'Synthetic fixture','author':'Tests','license':'MIT','entry':'main.js','sdk':{'requires':'>=1.0.0 <2.0.0','tested':'1.0.0'},'system':{'actorTypes':[{'id':'character','label':'Character'}],'itemTypes':[{'id':'gear','label':'Gear'}]}}
buffer=BytesIO()
with ZipFile(buffer,'w') as archive:
 archive.writestr('manifest.json',json.dumps(manifest))
 archive.writestr('main.js','export default {start(){},stop(){}};')
host().install_local(buffer.getvalue(),expected_type='system')
c.system=manifest['id'];c.save(update_fields=['system'])
'''

def check(gm,player,data,output):
    problems=[]
    for domain,toggle,create,label,field in [
        ('maps','gravewrightMaps.toggle()',"gravewrightRealtime.mapCommand('folder-create',{label:'Parent maps',color:'#c9a44c'})",'.gw-folder__label','label'),
        ('actors','gravewrightActors.toggle()',"gravewrightRealtime.resourceCommand('actors','folder.create',{name:'Parent actors',color:'#c9a44c'})",'.gw-folder__label','label'),
        ('journals','gravewrightJournals.toggle()',"gravewrightRealtime.journalCommand('folder-create',{name:'Parent journals',color:'#c9a44c'})",'.gw-folder__label','name'),
        ('items',"document.querySelector('[data-native-directory-toggle=items]').click()","gravewright.items.createFolder({name:'Parent items'})",'.item-directory__folder-name','name'),
    ]:
        if domain=='items': gm.evaluate("async()=>{window.gravewright=(await import('/static/gravewright_modules/frontend-api.js')).gravewright}")
        gm.evaluate('()=>'+create)
        gm.evaluate(toggle)
        panel=gm.locator('#'+domain+'-panel');expect(panel).to_be_visible()
        folder_selector='.item-directory__folder' if domain=='items' else '.gw-folder'
        parent=panel.locator(folder_selector).filter(has=gm.locator(label,has_text='Parent '+domain)).first
        expect(parent).to_be_visible()
        button=parent.locator(':scope > header '+('.item-directory__folder-toggle' if domain=='items' else '.gw-folder__toggle'))
        if button.get_attribute('aria-expanded')=='true':button.click()
        if domain=='maps':parent.locator(':scope > header .gw-folder__actions button').nth(1).click()
        elif domain=='journals':parent.locator(':scope > header [data-subfolder]').click()
        else:
            button.click(button='right')
            gm.locator('.directory-context-menu').get_by_role('menuitem',name='Create subfolder' if domain=='items' else 'Create folder',exact=True).click()
        form=gm.locator('.table-form-modal:visible' if domain=='items' else '.directory-dialog:visible')
        expect(form).to_be_visible()
        form.locator('[name='+field+']').fill('Child '+domain)
        form.locator('button[type=submit]').click()
        child=parent.locator(label,has_text='Child '+domain)
        expect(child).to_have_count(1)
        if not child.is_visible():problems.append(domain+': created but hidden inside collapsed parent')
        else:expect(button).to_have_attribute('aria-expanded','true')
        gm.evaluate(toggle)
    assert not problems,problems
    gm.reload();gm.wait_for_function('!!gravewrightMaps.board?.viewport()')
    for domain,toggle,label in [('maps','gravewrightMaps.toggle()','.gw-folder__label'),('actors','gravewrightActors.toggle()','.gw-folder__label'),('journals','gravewrightJournals.toggle()','.gw-folder__label'),('items',"document.querySelector('[data-native-directory-toggle=items]').click()",'.item-directory__folder-name')]:
        gm.evaluate(toggle)
        expect(gm.locator('#'+domain+'-panel '+label,has_text='Child '+domain)).to_be_visible()
        gm.evaluate(toggle)
    print('All four directories: subfolder creation, automatic expansion and reload persistence passed',flush=True)

if __name__=='__main__':main(check,seed_extra=SEED)
