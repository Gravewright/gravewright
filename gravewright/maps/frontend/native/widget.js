/** Native DOM adapter for the original map tool markup. No framework dependency.
 * Expressions are fixed, build-time template strings; user content is text/attributes only.
 */
const CELL = Symbol('cell');
const expressions = new Map();
function evaluate(code, ctx, eventMode = false) {
    const key = (eventMode ? 'event:' : 'value:') + code;
    let fn = expressions.get(key);
    if (!fn) {
        fn = new Function('scope', `with(scope){${eventMode ? code : 'return ' + code}}`);
        expressions.set(key, fn);
    }
    return fn(ctx);
}
function scoped(base, extras = {}) { return new Proxy(extras, { has: (_, key) => key !== Symbol.unscopables, get: (o, k) => k === Symbol.unscopables ? undefined : k in o ? o[k] : base[k], set: (o, k, v) => { if (k in o)
        o[k] = v;
    else
        base[k] = v; return true; } }); }
function className(v) { return typeof v === 'object' ? Array.isArray(v) ? v.map(className).join(' ') : Object.keys(v || {}).filter(k => v[k]).join(' ') : v ?? ''; }
function setAttr(el, key, value) {
    if (key === 'key' || key === 'ref')
        return;
    if (key === 'style' && value && typeof value === 'object') {
        for (const [k, v] of Object.entries(value)) {
            if (k.startsWith('--')) el.style.setProperty(k, v);
            else el.style[k] = v;
        }
        return;
    }
    if (key === 'class')
        value = className(value);
    if (['disabled', 'checked', 'selected', 'multiple', 'required', 'hidden'].includes(key)) {
        el.toggleAttribute(key, !!value);
        return;
    }
    if (value === undefined || value === null || value === false && !key.startsWith('aria-'))
        el.removeAttribute(key);
    else
        el.setAttribute(key, String(value));
}
function dispose(el) { el._instance?.destroy(); el._cleanup?.(); for (const child of el.childNodes)
    dispose(child); }
function patch(parent, fresh) {
    const nodes = [...fresh.childNodes];
    for (let i = 0; i < nodes.length; i++) {
        const next = nodes[i];
        let old = parent.childNodes[i];
        if (!old || old.nodeName !== next.nodeName || old._key !== next._key) {
            if (old) {
                dispose(old);
                old.replaceWith(next);
            }
            else
                parent.append(next);
            old = next;
        }
        else if (next.nodeType === 3) {
            if (old.textContent !== next.textContent)
                old.textContent = next.textContent;
            continue;
        }
        if (next.nodeType !== 1)
            continue;
        if (old !== next) {
            // The movable directive owns these classes, independently of template state.
            for (const name of ['gw-movable-resizable', 'gw-window--focused', 'gw-move-handle', 'gw-move-handle--active'])
                if (old.classList.contains(name)) next.classList.add(name);
            for (const attr of [...old.attributes])
                // Canvas backing dimensions belong to the renderer. Removing either
                // attribute resets its pixels/context even when its CSS size is unchanged.
                if (!next.hasAttribute(attr.name) && attr.name !== 'style'
                    // Uncontrolled disclosure state belongs to the browser/user.
                    && !(old.nodeName === 'DETAILS' && attr.name === 'open')
                    && !(old.nodeName === 'CANVAS' && ['width', 'height'].includes(attr.name)))
                    old.removeAttribute(attr.name);
            for (const attr of next.attributes)
                if (old.getAttribute(attr.name) !== attr.value)
                    old.setAttribute(attr.name, attr.value);
            for (const name of old._events || [])
                old[name] = null;
            for (const name of next._events || [])
                old[name] = next[name];
            old._events = next._events;
        }
        if (next._component) {
            if (!old._instance)
                old._instance = next._component(old, next._options);
            else
                old._instance.update(next._options.props, next._options);
        }
        else if (old !== next)
            patch(old, next);
        else {
            const content = document.createDocumentFragment();
            content.append(...old.childNodes);
            patch(old, content);
        }
        if (next._ref)
            next._ref.value = old;
        if (next._value !== undefined && old.value !== String(next._value))
            old.value = String(next._value);
        if (next._checked !== undefined)
            old.checked = next._checked;
        if (next._movable && !old._cleanup) {
            next._movable.mounted(old);
            old._cleanup = () => next._movable.unmounted(old);
        }
    }
    while (parent.childNodes.length > nodes.length) {
        dispose(parent.lastChild);
        parent.lastChild.remove();
    }
}
export function model(options) { return { [CELL]: true, get value() { return options.props.modelValue; }, set value(v) { options.props.modelValue = v; options.emit('update:modelValue', v); } }; }
export function widget(markup, setup) {
    return function mount(host, initial) {
        const options = { ...initial, props: { ...initial.props } };
        let stopped = false, queued = false, rendering = false, locals = {}, exposed = {};
        const mounted = [], unmount = [], watches = [];
        const portal = document.createElement('div');
        portal.style.display = 'contents';
        document.body.append(portal);
        const schedule = () => { if (!queued && !stopped) {
            queued = true;
            queueMicrotask(() => { queued = false; if (!stopped)
                render(); });
        } };
        const api = { ref(value) { return { [CELL]: true, get value() { return value; }, set value(next) { if (value !== next) {
                    value = next;
                    if (!(next instanceof Node))
                        schedule();
                } } }; },
            computed(read) { return { [CELL]: true, get value() { return read(); } }; },
            watch(read, fn, opts = {}) { const get = typeof read === 'function' ? read : () => read.value; const entry = { get, fn, value: get(), signature: undefined }; entry.signature = signature(entry.value); watches.push(entry); if (opts.immediate)
                fn(entry.value); },
            onMounted(fn) { mounted.push(fn); }, onBeforeUnmount(fn) { unmount.push(fn); }, nextTick() { return Promise.resolve(); }, defineExpose(value) { exposed = value; } };
        function signature(value) { try {
            return JSON.stringify(value);
        }
        catch {
            return value;
        } }
        const ctx = new Proxy({}, { has: () => true, get: (_, key) => { if (key === Symbol.unscopables)
                return; const v = key in locals ? locals[key] : key in options.props ? options.props[key] : globalThis[key]; return v?.[CELL] ? v.value : v; }, set: (_, key, v) => { if (locals[key]?.[CELL])
                locals[key].value = v;
            else if (key in locals)
                locals[key] = v;
            else
                options.props[key] = v; schedule(); return true; } });
        locals = setup(options, api);
        function trigger(code, scope, event, args) {
            const valueScope = scoped(scope, { $event: event, $args: args });
            try {
                const bare = code.trim().replace(/;$/, '');
                let result;
                if (/^[\w$.]+$/.test(bare)) {
                    const fn = evaluate(bare, valueScope);
                    result = typeof fn === 'function' ? fn(...(args || [event])) : fn;
                }
                else
                    result = evaluate(code, valueScope, true);
                if (result?.finally)
                    result.finally(schedule).catch(console.error);
            }
            finally {
                schedule();
            }
        }
        function children(list, scope, svg = false, portalTarget) {
            const fragment = document.createDocumentFragment();
            let branch = false;
            for (const item of list) {
                if (item.when !== undefined) {
                    branch = !!evaluate(item.when, scope);
                    if (!branch)
                        continue;
                }
                else if (item.otherwiseWhen !== undefined) {
                    if (branch)
                        continue;
                    branch = !!evaluate(item.otherwiseWhen, scope);
                    if (!branch)
                        continue;
                }
                else if (item.otherwise) {
                    if (branch)
                        continue;
                    branch = true;
                }
                else if (item.text === undefined || item.text.trim())
                    branch = false;
                if (item.each) {
                    const values = evaluate(item.each.value, scope) || [];
                    let i = 0;
                    for (const [key, value] of (Array.isArray(values) ? values.map((v, i) => [i, v]) : Object.entries(values))) {
                        const tuple = item.each.names[0]?.startsWith('[');
                        const extra = tuple ? Object.fromEntries(item.each.names.map((name, index) => [name.replace(/[\[\]]/g, '').trim(), value[index]])) : { [item.each.names[0]]: value };
                        if (!tuple && item.each.names[1])
                            extra[item.each.names[1]] = key;
                        if (!tuple && item.each.names[2])
                            extra[item.each.names[2]] = i++;
                        fragment.append(children([{ ...item, each: undefined, when: undefined }], scoped(scope, extra), svg, portalTarget));
                    }
                    continue;
                }
                if (item.text !== undefined || item.value !== undefined) {
                    fragment.append(document.createTextNode(item.text ?? String(evaluate(item.value, scope) ?? '')));
                    continue;
                }
                if (item.tag === 'Teleport') {
                    portalTarget.append(children(item.children, scope, false, portalTarget));
                    continue;
                }
                if (item.tag === 'template') {
                    fragment.append(children(item.children, scope, svg, portalTarget));
                    continue;
                }
                if (item.tag === 'slot') {
                    fragment.append(options.slots?.() || document.createDocumentFragment());
                    continue;
                }
                let tag = item.tag === 'component' ? evaluate(item.bind.is, scope) : item.tag;
                const attrs = { ...item.attrs, ...(item.spread ? evaluate(item.spread, scope) : {}) };
                for (const [k, v] of Object.entries(item.bind))
                    attrs[k] = evaluate(v, scope);
                if (item.bind.class)
                    attrs.class = [item.attrs.class, attrs.class];
                if (typeof tag === 'string' && tag.startsWith('Ph')) {
                    const template = document.querySelector('#map-native-icons');
                    const svgIcon = template?.content.querySelector(`[data-icon="${tag}"][data-weight="${attrs.weight || 'regular'}"]`)?.firstElementChild;
                    if (svgIcon) {
                        const el = svgIcon.cloneNode(true);
                        for (const [k, v] of Object.entries(attrs))
                            setAttr(el, k, v);
                        fragment.append(el);
                    }
                    continue;
                }
                const component = typeof tag === 'function' ? tag : scope[tag];
                const isComponent = typeof component === 'function' && (/^[A-Z]/.test(String(tag)) || typeof tag === 'function');
                const el = svg && !isComponent || tag === 'svg' ? document.createElementNS('http://www.w3.org/2000/svg', tag) : document.createElement(isComponent ? 'div' : tag);
                el._key = attrs.key ?? (isComponent ? tag : undefined);
                if (isComponent) {
                    el.style.display = 'contents';
                    el._component = component;
                    const props = {};
                    for (const [k, v] of Object.entries(attrs))
                        props[k.replace(/-([a-z])/g, (_, x) => x.toUpperCase())] = v;
                    if (item.model)
                        props.modelValue = evaluate(item.model.path, scope);
                    el._options = { ...options, props, slots: () => children(item.children, scope, false, portalTarget), emit: (name, ...args) => {
                            if (name === 'update:modelValue' && item.model) {
                                evaluate(item.model.path + '=$event', scoped(scope, { $event: args[0] }), true);
                                schedule();
                            }
                            for (const handler of item.events)
                                if (handler.event === name)
                                    trigger(handler.code, scope, args[0], args);
                        } };
                }
                else {
                    for (const [k, v] of Object.entries(attrs))
                        setAttr(el, k, v);
                    if (['input', 'textarea', 'select'].includes(tag) && attrs.value !== undefined)
                        el._value = attrs.value;
                    if (attrs.checked !== undefined)
                        el._checked = !!attrs.checked;
                    if (attrs.ref)
                        el._ref = locals[attrs.ref];
                    if (item.movable)
                        el._movable = locals.vMovableResizable;
                    if (item.show && !evaluate(item.show, scope))
                        el.style.display = 'none';
                    el._events = [];
                    if (item.model) {
                        const val = evaluate(item.model.path, scope);
                        if (attrs.type === 'checkbox')
                            el._checked = !!val;
                        else
                            el._value = val ?? '';
                        const name = tag === 'select' ? 'onchange' : 'oninput';
                        el._events.push(name);
                        el[name] = (event) => { let value = attrs.type === 'checkbox' ? event.target.checked : event.target.value; if (item.model.mods.includes('number'))
                            value = Number(value); evaluate(item.model.path + '=$event', scoped(scope, { $event: value }), true); schedule(); };
                        // Commit the toggle before global click handlers schedule a render.
                        // Keep change support for callers dispatching a change explicitly.
                        if (attrs.type === 'checkbox') {
                            el.onclick = el.onchange = el.oninput;
                            el._events.push('onclick', 'onchange');
                        }
                    }
                    for (const handler of item.events) {
                        const name = 'on' + handler.event;
                        const previous = el[name];
                        el._events.push(name);
                        el[name] = event => {
                            const keys = { enter: 'Enter', esc: 'Escape', escape: 'Escape', space: ' ' };
                            for (const mod of handler.mods)
                                if (keys[mod] && event.key !== keys[mod])
                                    return;
                            if (handler.mods.includes('self') && event.target !== event.currentTarget)
                                return;
                            if (handler.mods.includes('stop'))
                                event.stopPropagation();
                            if (handler.mods.includes('prevent'))
                                event.preventDefault();
                            previous?.(event);
                            trigger(handler.code, scope, event);
                        };
                    }
                    el.append(children(item.children, scope, svg || tag === 'svg', portalTarget));
                }
                fragment.append(el);
            }
            return fragment;
        }
        function render() {
            if (rendering || stopped)
                return;
            rendering = true;
            try {
                for (const watch of watches) {
                    const value = watch.get(), next = signature(value);
                    if (next !== watch.signature) {
                        const old = watch.value;
                        watch.signature = next;
                        watch.value = value;
                        watch.fn(value, old);
                    }
                }
                const freshPortal = document.createDocumentFragment();
                const fresh = children(markup, ctx, false, freshPortal);
                patch(host, fresh);
                patch(portal, freshPortal);
            }
            finally {
                rendering = false;
            }
        }
        render();
        for (const fn of mounted)
            fn();
        schedule();
        return { update(props, next = {}) { Object.assign(options.props, props); for (const key of ['emit', 'slots'])
                if (next[key])
                    options[key] = next[key]; schedule(); }, get scope() { return ctx; }, call(name, ...args) { const result = (exposed[name] || ctx[name])?.(...args); schedule(); return result; }, destroy() { if (stopped)
                return; stopped = true; for (const fn of unmount)
                fn(); for (const node of host.childNodes)
                dispose(node); host.replaceChildren(); dispose(portal); portal.remove(); } };
    };
}
