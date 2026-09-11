"""Import and compile the user's AI response containing interspersed Markdown."""
import re
from pathlib import Path
from migration_closure import main
from playwright.sync_api import expect


def check(gm, player, data, output):
    raw=(Path(__file__).resolve().parents[1]/'fixtures/shader-ai-mixed-markdown.txt').read_text()
    expected=re.sub(r'^```(?:arduino|cpp|java)?\n','',raw,flags=re.M).replace('\\*','*').replace('\\\n','\n').strip()
    gm.context.grant_permissions(['clipboard-read','clipboard-write'])
    gm.get_by_role('group',name='Layers',exact=True).get_by_role('button',name='Effects',exact=True).click()
    gm.get_by_role('button',name='Shaders',exact=True).click()
    gm.locator('[data-shader-preset="orb-1"]').click()
    gm.mouse.click(650,400)
    gm.locator('[data-effect-kind="shader"]').first.dblclick()
    editor=gm.locator('.effect-editor--shader')
    original=editor.locator('#effect-shader-source').input_value()
    editor.get_by_role('button',name='AI prompt',exact=True).click()
    modal=gm.locator('dialog.shader-prompt-dialog')
    modal.get_by_label('Desired effect',exact=True).fill('A swirling sandstorm')
    modal.get_by_role('button',name='Copy instructions and continue',exact=True).click()
    modal.get_by_label('GLSL returned by the AI',exact=True).fill(raw)
    modal.get_by_role('button',name='Insert into editor',exact=True).click()
    expect(modal).to_have_count(0)
    expect(editor.locator('#effect-shader-source')).to_have_value(expected)
    stored=lambda:gm.evaluate("async id=>(await(await fetch('/api/maps/'+id+'/state')).json()).shaders[0].source",data['map'])
    assert stored()==original,'Import should only edit the draft'
    # Copy/paste can also escape the fences, mix quote wrappers and omit a mate.
    editor.get_by_role('button',name='AI prompt',exact=True).click()
    modal.get_by_label('Desired effect',exact=True).fill('A swirling sandstorm')
    modal.get_by_role('button',name='Copy instructions and continue',exact=True).click()
    response=modal.get_by_label('GLSL returned by the AI',exact=True)
    response.fill("'''\nfloat density = 0.5;\n'''")
    modal.get_by_role('button',name='Insert into editor',exact=True).click()
    expect(response).to_have_value('float density = 0.5;')
    expect(modal).to_contain_text('does not contain void main()')
    expect(editor.locator('#effect-shader-source')).to_have_value(expected)
    variant=raw.replace('```', '\\`\\`\\`', 1).replace('```', "'''", 1)
    variant += '\n```\u200b\n'
    response.fill(variant)
    modal.get_by_role('button',name='Insert into editor',exact=True).click()
    expect(modal).to_have_count(0)
    expect(editor.locator('#effect-shader-source')).to_have_value(expected)
    assert stored()==original,'Reimport should still only edit the draft'
    # Save goes through the actual WebGL2 validator before sending the command.
    editor.get_by_role('button',name='Save',exact=True).click()
    gm.wait_for_function("async ([id,source])=>(await(await fetch('/api/maps/'+id+'/state')).json()).shaders[0].source===source",arg=[data['map'],expected],timeout=15000)
    expect(editor.locator('.effect-editor__actions [role=status]')).to_be_empty()
    print('User response and escaped/mixed/incomplete wrappers imported intact; missing main explained; WebGL2 compilation and explicit Save passed',flush=True)


if __name__=='__main__':main(check)
