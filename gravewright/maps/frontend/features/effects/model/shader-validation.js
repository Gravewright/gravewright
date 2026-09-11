import { text as gwText } from '../../../shared/config/i18n/text.js';
import { PREAMBLE, USER_PREFIX, USER_SUFFIX } from '../../scene-layers/lib/shader-language.js';
/** A draft gets its own small compiler context; bad GLSL never reaches the live board. */
export class ShaderDraftValidator {
    gl;
    validate(source) {
        if (!source.trim())
            return gwText('The shader is empty.');
        if (source.length > 32000)
            return gwText('Text is too long (32000 character limit).');
        this.gl ??= document.createElement('canvas').getContext('webgl2');
        const gl = this.gl;
        if (!gl)
            return gwText('WebGL 2 is unavailable to validate this shader.');
        const shader = gl.createShader(gl.FRAGMENT_SHADER);
        if (!shader)
            return gwText('Could not validate the shader.');
        try {
            gl.shaderSource(shader, PREAMBLE + USER_PREFIX + source + USER_SUFFIX);
            gl.compileShader(shader);
            return gl.getShaderParameter(shader, gl.COMPILE_STATUS) ? '' : gl.getShaderInfoLog(shader)?.replaceAll('\0', '').trim() || gwText('Invalid GLSL code.');
        }
        finally {
            gl.deleteShader(shader);
        }
    }
    dispose() { this.gl?.getExtension('WEBGL_lose_context')?.loseContext(); this.gl = undefined; }
}
