/** Normalize Markdown wrappers without dropping GLSL between fenced snippets. */
export function normalizeShaderSource(value) {
    const lines = value.replace(/\r\n?/g, '\n').trim().split('\n');
    const output = [];
    let blockComment = false, continuation = false;
    for (const line of lines) {
        // AI responses can mix fence types, omit a mate, or escape the fence itself.
        // A standalone fence cannot be GLSL; remove it without discarding its content.
        const markerLine = line.replace(/\\([`'~])/g, '$1').replace(/[\u200B\uFEFF]/g, '').replace(/[‘’]/g, "'").replace(/\\[ \t]*$/, '');
        if (!blockComment && !continuation && /^[ \t]*(`{3,}|~{3,}|'{3,})[ \t]*([\w.+#-]+(?:[ \t]+[\w.+#-]+)*)?[ \t]*$/.test(markerLine)) continue;
        const directive = continuation || (!blockComment && /^[ \t]*#/.test(line));
        let clean = '', quote = '';
        for (let i = 0; i < line.length; i++) {
            const char = line[i], next = line[i + 1];
            if (blockComment) {
                clean += char;
                if (char === '*' && next === '/') { clean += next; i++; blockComment = false; }
            } else if (quote) {
                clean += char;
                if (char === '\\' && next) { clean += next; i++; }
                else if (char === quote) quote = '';
            } else if (char === '/' && next === '/') {
                clean += line.slice(i); break;
            } else if (char === '/' && next === '*') {
                clean += '/*'; i++; blockComment = true;
            } else if (char === '"' || char === "'") {
                quote = char; clean += char;
            } else if (char === '\\' && !directive) {
                if (/^[ \t]*$/.test(line.slice(i + 1))) break;
                if (/[\\`*_{}\[\]()#+\-.!<>|]/.test(next || '')) { clean += next; i++; }
                else clean += char;
            } else if (char !== '\u200B' && char !== '\uFEFF') clean += char === '\u00a0' ? ' ' : char;
        }
        output.push(clean);
        continuation = directive && /\\[ \t]*$/.test(line);
    }
    return output.join('\n').trim();
}
