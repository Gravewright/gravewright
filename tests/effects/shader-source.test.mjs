import test from 'node:test';
import assert from 'node:assert/strict';
import {readFileSync} from 'node:fs';
import {normalizeShaderSource} from '../../gravewright/maps/frontend/features/effects/model/shader-source.js';
import {shaderSource} from '../../gravewright/maps/frontend/features/effects/ui/shader-prompt-dialog.js';

test('escaped fences and invisible formatting from copied responses are removed', () => {
    const source = 'void main() { finalColor = vec4(0.0); }';
    const fence = '\\`\\`\\`';
    assert.equal(shaderSource(fence+'java\\\n'+source+'\n'+fence), source);
    assert.equal(shaderSource('‘’‘glsl\n'+source+'\n```\u200B'), source);
    assert.equal(shaderSource(source.replace('void main', 'vo\u200Bid\u00a0main')), source);
    assert.throws(()=>shaderSource('```\n```'), /empty/);
    assert.throws(()=>shaderSource('float a = 0.0;'), /does not contain void main/);
    assert.throws(()=>shaderSource(source+' '.repeat(32001)+'// end'), /exceeds/);
});

test('user response: all code survives interspersed arduino/cpp/java fences and Markdown escapes', () => {
    const raw = readFileSync(new URL('../fixtures/shader-ai-mixed-markdown.txt', import.meta.url), 'utf8');
    const expected = raw.replace(/^```(?:arduino|cpp|java)?\n/gm, '').replaceAll('\\*', '*').replace(/\\\n/g, '\n').trim();
    assert.equal(shaderSource(raw), expected);
    assert.equal(shaderSource(expected), expected);
    assert.equal(shaderSource(raw.replaceAll('\n', '\r\n')), expected);
});

test('normal GLSL, comments and preprocessor continuations are preserved', () => {
    const source = '// keep \\* and ``` in comments\n/*\n```java\n\\*\n```\n*/\n#define DOUBLE(x) \\\n ((x) * 2.0)\nvoid main() { finalColor = vec4(DOUBLE(0.1)); }';
    assert.equal(shaderSource(source), source);
    assert.equal(shaderSource('~~~glsl\n'+source+'\n~~~'), source);
});

test('incomplete wrappers are removed and responses without executable main are rejected', () => {
    assert.equal(normalizeShaderSource('```java\nvoid main() {}'), 'void main() {}');
    assert.equal(normalizeShaderSource('```glsl\nvoid main() {}\n~~~'), 'void main() {}');
    assert.throws(()=>shaderSource('// void main() {}'));
    assert.throws(()=>shaderSource('/* void main() {} */'));
    assert.throws(()=>shaderSource('void main() {'+'x'.repeat(32000)+'}'));
});

test('triple single quotes work around complete shaders and interspersed snippets', () => {
    const source = 'void main() {\nfinalColor = vec4(0.0);\n}';
    for (const label of ['', 'glsl', 'java']) {
        assert.equal(shaderSource("'''"+label+'\r\n'+source+"\r\n'''"), source);
    }
    assert.equal(shaderSource("void main() {\n'''\nfinalColor = vec4(0.0);\n'''\n}"), source);
    assert.equal(shaderSource("/*\n'''\n*/\n"+source), "/*\n'''\n*/\n"+source);
    assert.equal(shaderSource("'''\n"+source), source);
    assert.equal(shaderSource("'''\n"+source+'\n```'), source);
    assert.throws(()=>shaderSource("'''\nlighjwrepgwreis\n'''"));
});
