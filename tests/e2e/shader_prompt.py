"""Shader authoring: one-click clipboard, feedback and unchanged source."""
from migration_closure import main
from playwright.sync_api import expect


def check(gm, player, data, output):
    gm.context.grant_permissions(['clipboard-read', 'clipboard-write'])
    gm.get_by_role('group',name='Layers',exact=True).get_by_role('button',name='Effects',exact=True).click()
    gm.get_by_role('button',name='Shaders',exact=True).click()
    gm.locator('[data-shader-preset="orb-1"]').click()
    gm.mouse.click(650,400)
    gm.locator('[data-effect-kind="shader"]').first.dblclick()
    editor=gm.locator('.effect-editor--shader')
    expect(editor).to_be_visible()
    source=editor.locator('#effect-shader-source').input_value()
    button=editor.get_by_role('button',name='AI prompt',exact=True)
    button.click()
    modal=gm.locator('dialog.shader-prompt-dialog')
    expect(modal).to_be_visible()
    confirm=modal.get_by_role('button',name='Copy instructions and continue',exact=True)
    expect(confirm).to_be_disabled()
    description='Slow violet mist with glowing sparks; $& stays literal.'
    modal.get_by_label('Desired effect',exact=True).fill(description)
    gm.screenshot(path=str(output/'shader-ai-description.png'))
    confirm.click()
    result=modal.get_by_label('GLSL returned by the AI',exact=True)
    expect(result).to_be_visible()
    gm.screenshot(path=str(output/'shader-ai-result.png'))
    prompt=gm.evaluate('navigator.clipboard.readText()')
    assert description in prompt and 'OUTPUT CONTRACT — RAW SOURCE FILE' in prompt
    assert 'Do not split the shader into snippets.' in prompt and '`' not in prompt
    result.fill('This is not shader code')
    modal.get_by_role('button',name='Insert into editor',exact=True).click()
    expect(modal.get_by_role('alert')).to_contain_text('void main()')
    assert editor.locator('#effect-shader-source').input_value()==source
    code='void main() { finalColor = vec4(0.0); }'
    result.fill('```glsl\n'+code+'\n```')
    modal.get_by_role('button',name='Insert into editor',exact=True).click()
    expect(modal).to_have_count(0)
    expect(editor.locator('#effect-shader-source')).to_have_value(code)
    saved=gm.evaluate("async id=>(await(await fetch('/api/maps/'+id+'/state')).json()).shaders[0].source",data['map'])
    assert saved==source, 'Inserting must not save the shader automatically'
    button.click()
    modal.get_by_label('Desired effect',exact=True).fill('Rain')
    gm.evaluate("()=>{navigator.clipboard.writeText=async()=>{throw new DOMException('Denied','NotAllowedError')}}")
    modal.get_by_role('button',name='Copy instructions and continue',exact=True).click()
    expect(modal.get_by_role('alert')).to_contain_text('Could not copy')
    expect(modal.get_by_label('Desired effect',exact=True)).to_have_value('Rain')
    expect(editor).to_be_visible()
    gm.keyboard.press('Escape')
    expect(modal).to_have_count(0)
    expect(editor).to_be_visible()
    expect(editor.locator('#effect-shader-source')).to_have_value(code)
    print('Shader AI wizard: actual clipboard, description, fenced GLSL insertion, no automatic save, invalid input, clipboard failure and Escape passed',flush=True)


if __name__=='__main__':main(check)
