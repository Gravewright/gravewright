"""Project modal lifecycle, including nested focus and async module saves."""
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from threading import Thread
from playwright.sync_api import sync_playwright, expect

ROOT = Path(__file__).resolve().parents[2]
FILES = {
    '/static/gravewright_table/modal.js': ROOT / 'gravewright/table/static/gravewright_table/modal.js',
    '/static/gravewright_web/escape.js': ROOT / 'gravewright/web/static/gravewright_web/escape.js',
}


class Handler(BaseHTTPRequestHandler):
    def do_GET(self):
        path = self.path.split('?', 1)[0]
        if path in FILES:
            content, kind = FILES[path].read_bytes(), 'text/javascript'
        else:
            content, kind = b'<button id="background">Background</button><aside id="already-inert" inert>Inactive</aside>', 'text/html'
        self.send_response(200)
        self.send_header('Content-Type', kind)
        self.end_headers()
        self.wfile.write(content)

    def log_message(self, *args):
        pass


server = ThreadingHTTPServer(('127.0.0.1', 0), Handler)
thread = Thread(target=server.serve_forever, daemon=True)
thread.start()
try:
    with sync_playwright() as p:
        browser = p.chromium.launch()
        page = browser.new_page()
        errors = []
        page.on('pageerror', lambda error: errors.append(str(error)))
        page.goto(f'http://127.0.0.1:{server.server_port}')
        page.evaluate('''async () => {
          const {mountModal} = await import('/static/gravewright_table/modal.js');
          window.openReview = (id, pending=false, nested=false) => {
            const modal=document.createElement('section');modal.id=id;
            modal.innerHTML='<input><button data-child>Open child</button><p role="alert" hidden></p>';
            modal.querySelector('[data-child]').onclick=()=>window.openReview(id+'-child',false,true);
            if(pending)modal.addEventListener('gravewright:sheet-flush',event=>{
              event.detail.waitUntil(new Promise((resolve,reject)=>{
                window.resolveReview=resolve;window.rejectReview=reject;
              }));
            },{once:true});
            window[id]=mountModal(modal,{nested});return id;
          };
          window.reviewMountModal=mountModal;
        }''')

        def assert_restored():
            assert not page.locator('#background').evaluate('(el)=>el.inert')
            assert page.locator('#already-inert').evaluate('(el)=>el.inert')
            assert page.evaluate('document.body.style.overflow') == ''
            expect(page.locator('.ownership-modal-overlay')).to_have_count(0)

        def assert_focus_trap(modal):
            first, last = modal.locator('input'), modal.locator('[data-child]')
            first.focus()
            page.keyboard.press('Shift+Tab')
            expect(last).to_be_focused()
            page.keyboard.press('Tab')
            expect(first).to_be_focused()

        # Scene and journal forms are cloned from template content, whose inert
        # owner document has neither a body nor a browsing context until adoption.
        page.locator('#background').focus()
        page.evaluate('''() => {
          const template=document.createElement('template');
          template.innerHTML='<form id="template-form"><input><button type="button" data-child>Close</button></form>';
          const form=template.content.firstElementChild.cloneNode(true);
          if(form.ownerDocument.body || form.ownerDocument.defaultView)throw Error('Expected an inert template document');
          window.templateClosed=0;
          form.querySelector('[data-child]').onclick=()=>form.close();
          form.addEventListener('close',()=>window.templateClosed++);
          window.templateForm=form;
          if(reviewMountModal(form)!==form || form.ownerDocument!==document)throw Error('Modal must adopt the original form');
        }''')
        template_form = page.locator('#template-form')
        expect(template_form).to_be_visible()
        expect(template_form.locator('input')).to_be_focused()
        assert page.locator('#background').evaluate('(el)=>el.inert')
        assert_focus_trap(template_form)
        template_form.locator('[data-child]').click()
        expect(template_form).to_have_count(0)
        assert page.evaluate('templateClosed') == 1
        expect(page.locator('#background')).to_be_focused()
        assert_restored()
        page.evaluate('reviewMountModal(window.templateForm)')
        page.keyboard.press('Escape')
        expect(template_form).to_have_count(0)
        assert page.evaluate('templateClosed') == 2
        assert_restored()

        # Real button clicks capture the opener before the child is mounted.
        page.locator('#background').focus()
        page.evaluate("openReview('parent',false,true)")
        parent = page.locator('#parent')
        expect(parent).to_have_attribute('role', 'dialog')
        expect(parent).to_have_attribute('aria-modal', 'true')
        assert_focus_trap(parent)
        parent.locator('[data-child]').click()
        child = page.locator('#parent-child')
        expect(parent).to_be_attached()
        assert parent.evaluate('(el)=>!!el.closest("[inert]")')
        assert not child.evaluate('(el)=>!!el.closest("[inert]")')
        assert_focus_trap(child)
        page.keyboard.press('Escape')
        expect(child).to_have_count(0)
        expect(parent).to_be_visible()
        expect(parent.locator('[data-child]')).to_be_focused()
        assert not parent.evaluate('(el)=>!!el.closest("[inert]")')
        page.keyboard.press('Escape')
        expect(parent).to_have_count(0)
        expect(page.locator('#background')).to_be_focused()
        assert_restored()

        # Provider revocation may remove an ancestor before its descendants.
        page.evaluate("openReview('ancestor',false,true)")
        page.locator('#ancestor [data-child]').click()
        page.locator('#ancestor-child [data-child]').click()
        grandchild = page.locator('#ancestor-child-child')
        page.evaluate('window.ancestor.close(true)')
        expect(page.locator('#ancestor')).to_have_count(0)
        expect(grandchild).to_be_visible()
        assert_focus_trap(grandchild)
        page.keyboard.press('Escape')
        expect(grandchild).to_have_count(0)
        expect(page.locator('#ancestor-child [data-child]')).to_be_focused()
        assert not page.locator('#ancestor-child').evaluate('(el)=>!!el.closest("[inert]")')
        page.keyboard.press('Escape')
        expect(page.locator('#ancestor-child')).to_have_count(0)
        assert_restored()

        # Reusing a section must not reconnect a stale ancestry record or cycle.
        page.evaluate("openReview('reuseA',false,true)")
        page.locator('#reuseA [data-child]').click()
        page.evaluate('window.reuseA.close(true);reviewMountModal(window.reuseA,{nested:true})')
        expect(page.locator('#reuseA input')).to_be_focused()
        page.keyboard.press('Escape')
        expect(page.locator('#reuseA')).to_have_count(0)
        expect(page.locator('#reuseA-child')).to_be_visible()
        assert not page.locator('#reuseA-child').evaluate('(el)=>!!el.closest("[inert]")')
        page.keyboard.press('Escape')
        expect(page.locator('#reuseA-child')).to_have_count(0)
        assert_restored()

        # Passing an already connected section must not make that section inert.
        page.evaluate('''() => {
          const connected=document.createElement('section');connected.id='connected';
          connected.innerHTML='<input>';
          document.body.append(connected);window.connected=reviewMountModal(connected);
        }''')
        expect(page.locator('#connected input')).to_be_focused()
        assert not page.locator('#connected').evaluate('(el)=>!!el.closest("[inert]")')
        page.keyboard.press('Escape')
        expect(page.locator('#connected')).to_have_count(0)
        assert_restored()
        assert page.evaluate('''() => {
          try { reviewMountModal(document.createElement('dialog')); return false; }
          catch (error) { return error instanceof TypeError; }
        }'''), 'The project modal API must reject native HTML dialogs.'
        expect(page.locator('dialog')).to_have_count(0)

        page.evaluate("openReview('ordinary')")
        page.keyboard.press('Escape')
        expect(page.locator('#ordinary')).to_have_count(0)
        page.evaluate("openReview('pending',true)")
        page.keyboard.press('Escape')
        expect(page.locator('#pending')).to_be_visible()
        assert page.locator('#background').evaluate('(el)=>el.inert')
        page.evaluate('resolveReview()')
        expect(page.locator('#pending')).to_have_count(0)
        assert not page.locator('#background').evaluate('(el)=>el.inert')

        page.evaluate("openReview('failed',true)")
        page.keyboard.press('Escape')
        page.evaluate("rejectReview(Error('Unsaved changes'))")
        expect(page.locator('#failed [role=alert]')).to_have_text('Unsaved changes')
        expect(page.locator('#failed')).to_be_visible()
        page.keyboard.press('Escape')
        expect(page.locator('#failed')).to_have_count(0)

        page.evaluate("openReview('first',true);openReview('second')")
        expect(page.locator('#first')).to_be_attached()
        page.evaluate("rejectReview(Error('Conflict'))")
        page.evaluate('window.second.close()')
        expect(page.locator('#first')).to_be_visible()
        assert page.locator('#background').evaluate('(el)=>el.inert')
        page.keyboard.press('Escape')
        expect(page.locator('#first')).to_have_count(0)
        assert not page.locator('#background').evaluate('(el)=>el.inert')
        assert page.evaluate('document.body.style.overflow') == ''

        page.evaluate("openReview('revoked',true);window.revoked.close();window.revoked.close(true)")
        expect(page.locator('#revoked')).to_have_count(0)
        page.evaluate('resolveReview()')
        assert_restored()
        assert not errors, errors
        browser.close()
    print('Modal nested focus, ancestor cleanup, async saves, rejection, successor restoration, ESC and forced revocation passed.')
finally:
    server.shutdown()
    server.server_close()
    thread.join()
