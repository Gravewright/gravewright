import{a as _}from"./chunk-JK3SHH7G.js";import{A as u}from"./chunk-SBGB55P5.js";import{A as h,g as I,h as l,j as m,k as x,z as U}from"./chunk-FHKJAZW6.js";var S=class{constructor(t){this._syncFunctionHash=Object.create(null),this._adaptor=t,this._systemCheck()}_systemCheck(){if(!_())throw new Error("Current environment does not allow unsafe-eval, please use pixi.js/unsafe-eval module to enable support.")}ensureUniformGroup(t){let a=this.getUniformGroupData(t);t.buffer||(t.buffer=new x({data:new Float32Array(a.layout.size/4),usage:m.UNIFORM|m.COPY_DST}))}getUniformGroupData(t){return this._syncFunctionHash[t._signature]||this._initUniformGroup(t)}_initUniformGroup(t){let a=t._signature,r=this._syncFunctionHash[a];if(!r){let s=Object.keys(t.uniformStructures).map(n=>t.uniformStructures[n]),f=this._adaptor.createUboElements(s),o=this._generateUboSync(f.uboElements);r=this._syncFunctionHash[a]={layout:f,syncFunction:o}}return this._syncFunctionHash[a]}_generateUboSync(t){return this._adaptor.generateUboSync(t)}syncUniformGroup(t,a,r){let s=this.getUniformGroupData(t);t.buffer||(t.buffer=new x({data:new Float32Array(s.layout.size/4),usage:m.UNIFORM|m.COPY_DST}));let f=null;return a||(a=t.buffer.data,f=t.buffer.dataInt32),r||(r=0),s.syncFunction(t.uniforms,a,f,r),!0}updateUniformGroup(t){if(t.isStatic&&!t._dirtyId)return!1;t._dirtyId=0;let a=this.syncUniformGroup(t);return t.buffer.update(),a}destroy(){this._syncFunctionHash=null}};var M=class extends I{constructor({buffer:t,offset:a,size:r}){super(),this.uid=l("buffer"),this._resourceType="bufferResource",this._touched=0,this._resourceId=l("resource"),this._bufferResource=!0,this.destroyed=!1,this.buffer=t,this.offset=a|0,this.size=r,this.buffer.on("change",this.onBufferChange,this)}get _gcLastUsed(){return this.buffer?._gcLastUsed??-1}set _gcLastUsed(t){this.buffer&&(this.buffer._gcLastUsed=t)}onBufferChange(){this._resourceId=l("resource"),this.emit("change",this)}destroy(t=!1){this.destroyed=!0,t&&this.buffer.destroy(),this.emit("change",this),this.buffer=null,this.removeAllListeners()}};var b={name:"local-uniform-bit",vertex:{header:`

            struct LocalUniforms {
                uTransformMatrix:mat3x3<f32>,
                uColor:vec4<f32>,
                uRound:f32,
            }

            @group(1) @binding(0) var<uniform> localUniforms : LocalUniforms;
        `,main:`
            vColor *= localUniforms.uColor;
            modelMatrix *= localUniforms.uTransformMatrix;
        `,end:`
            if(localUniforms.uRound == 1)
            {
                vPosition = vec4(roundPixels(vPosition.xy, globalUniforms.uResolution), vPosition.zw);
            }
        `}},B={...b,vertex:{...b.vertex,header:b.vertex.header.replace("group(1)","group(2)")}},P={name:"local-uniform-bit",vertex:{header:`

            uniform mat3 uTransformMatrix;
            uniform vec4 uColor;
            uniform float uRound;
        `,main:`
            vColor *= uColor;
            modelMatrix = uTransformMatrix;
        `,end:`
            if(uRound == 1.)
            {
                gl_Position.xy = roundPixels(gl_Position.xy, uResolution);
            }
        `}};var N={name:"texture-bit",vertex:{header:`

        struct TextureUniforms {
            uTextureMatrix:mat3x3<f32>,
        }

        @group(2) @binding(2) var<uniform> textureUniforms : TextureUniforms;
        `,main:`
            uv = (textureUniforms.uTextureMatrix * vec3(uv, 1.0)).xy;
        `},fragment:{header:`
            @group(2) @binding(0) var uTexture: texture_2d<f32>;
            @group(2) @binding(1) var uSampler: sampler;


        `,main:`
            outColor = textureSample(uTexture, uSampler, vUV);
        `}},z={name:"texture-bit",vertex:{header:`
            uniform mat3 uTextureMatrix;
        `,main:`
            uv = (uTextureMatrix * vec3(uv, 1.0)).xy;
        `},fragment:{header:`
        uniform sampler2D uTexture;


        `,main:`
            outColor = texture(uTexture, vUV);
        `}};function H(e,t){for(let a in e.attributes){let r=e.attributes[a],s=t[a];s?(r.format??(r.format=s.format),r.offset??(r.offset=s.offset),r.instance??(r.instance=s.instance)):U(`Attribute ${a} is not present in the shader, but is present in the geometry. Unable to infer attribute details.`)}F(e)}function F(e){let{buffers:t,attributes:a}=e,r={},s={};for(let f in t){let o=t[f];r[o.uid]=0,s[o.uid]=0}for(let f in a){let o=a[f];r[o.buffer.uid]+=h(o.format).stride}for(let f in a){let o=a[f];o.stride??(o.stride=r[o.buffer.uid]),o.start??(o.start=s[o.buffer.uid]),s[o.buffer.uid]+=h(o.format).stride}}var c=[];c[u.NONE]=void 0;c[u.DISABLED]={stencilWriteMask:0,stencilReadMask:0};c[u.RENDERING_MASK_ADD]={stencilFront:{compare:"equal",passOp:"increment-clamp"},stencilBack:{compare:"equal",passOp:"increment-clamp"}};c[u.RENDERING_MASK_REMOVE]={stencilFront:{compare:"equal",passOp:"decrement-clamp"},stencilBack:{compare:"equal",passOp:"decrement-clamp"}};c[u.MASK_ACTIVE]={stencilWriteMask:0,stencilFront:{compare:"equal",passOp:"keep"},stencilBack:{compare:"equal",passOp:"keep"}};c[u.INVERSE_MASK_ACTIVE]={stencilWriteMask:0,stencilFront:{compare:"not-equal",passOp:"keep"},stencilBack:{compare:"not-equal",passOp:"keep"}};var p=[{type:"mat3x3<f32>",test:e=>e.value.a!==void 0,ubo:`
            var matrix = uv[name].toArray(true);
            data[offset] = matrix[0];
            data[offset + 1] = matrix[1];
            data[offset + 2] = matrix[2];
            data[offset + 4] = matrix[3];
            data[offset + 5] = matrix[4];
            data[offset + 6] = matrix[5];
            data[offset + 8] = matrix[6];
            data[offset + 9] = matrix[7];
            data[offset + 10] = matrix[8];
        `,uniform:`
            gl.uniformMatrix3fv(ud[name].location, false, uv[name].toArray(true));
        `},{type:"vec4<f32>",test:e=>e.type==="vec4<f32>"&&e.size===1&&e.value.width!==void 0,ubo:`
            v = uv[name];
            data[offset] = v.x;
            data[offset + 1] = v.y;
            data[offset + 2] = v.width;
            data[offset + 3] = v.height;
        `,uniform:`
            cv = ud[name].value;
            v = uv[name];
            if (cv[0] !== v.x || cv[1] !== v.y || cv[2] !== v.width || cv[3] !== v.height) {
                cv[0] = v.x;
                cv[1] = v.y;
                cv[2] = v.width;
                cv[3] = v.height;
                gl.uniform4f(ud[name].location, v.x, v.y, v.width, v.height);
            }
        `},{type:"vec2<f32>",test:e=>e.type==="vec2<f32>"&&e.size===1&&e.value.x!==void 0,ubo:`
            v = uv[name];
            data[offset] = v.x;
            data[offset + 1] = v.y;
        `,uniform:`
            cv = ud[name].value;
            v = uv[name];
            if (cv[0] !== v.x || cv[1] !== v.y) {
                cv[0] = v.x;
                cv[1] = v.y;
                gl.uniform2f(ud[name].location, v.x, v.y);
            }
        `},{type:"vec4<f32>",test:e=>e.type==="vec4<f32>"&&e.size===1&&e.value.red!==void 0,ubo:`
            v = uv[name];
            data[offset] = v.red;
            data[offset + 1] = v.green;
            data[offset + 2] = v.blue;
            data[offset + 3] = v.alpha;
        `,uniform:`
            cv = ud[name].value;
            v = uv[name];
            if (cv[0] !== v.red || cv[1] !== v.green || cv[2] !== v.blue || cv[3] !== v.alpha) {
                cv[0] = v.red;
                cv[1] = v.green;
                cv[2] = v.blue;
                cv[3] = v.alpha;
                gl.uniform4f(ud[name].location, v.red, v.green, v.blue, v.alpha);
            }
        `},{type:"vec3<f32>",test:e=>e.type==="vec3<f32>"&&e.size===1&&e.value.red!==void 0,ubo:`
            v = uv[name];
            data[offset] = v.red;
            data[offset + 1] = v.green;
            data[offset + 2] = v.blue;
        `,uniform:`
            cv = ud[name].value;
            v = uv[name];
            if (cv[0] !== v.red || cv[1] !== v.green || cv[2] !== v.blue) {
                cv[0] = v.red;
                cv[1] = v.green;
                cv[2] = v.blue;
                gl.uniform3f(ud[name].location, v.red, v.green, v.blue);
            }
        `}];function J(e,t,a){let r=[`
        var v = null;
        var v2 = null;
        var t = 0;
        var index = 0;
        var name = null;
        var arrayOffset = null;
    `],s=0;for(let o=0;o<e.length;o++){let n=e[o],g=n.data.name,y=!1,i=0;for(let v=0;v<p.length;v++)if(p[v].test(n.data)){i=n.offset/4,r.push(`name = "${g}";`,`offset += ${i-s};`,p[v].ubo),y=!0;break}if(!y)if(n.data.size>1)i=n.offset/4,r.push(a(n,i-s));else{let v=t[n.data.type];i=n.offset/4,r.push(`
                    v = uv.${g};
                    offset += ${i-s};
                    ${v};
                `)}s=i}let f=r.join(`
`);return new Function("uv","data","dataInt32","offset",f)}function d(e,t){return`
        for (let i = 0; i < ${e*t}; i++) {
            data[offset + (((i / ${e})|0) * 4) + (i % ${e})] = v[i];
        }
    `}var T={f32:`
        data[offset] = v;`,i32:`
        dataInt32[offset] = v;`,u32:`
        dataInt32[offset] = v;`,"vec2<f32>":`
        data[offset] = v[0];
        data[offset + 1] = v[1];`,"vec3<f32>":`
        data[offset] = v[0];
        data[offset + 1] = v[1];
        data[offset + 2] = v[2];`,"vec4<f32>":`
        data[offset] = v[0];
        data[offset + 1] = v[1];
        data[offset + 2] = v[2];
        data[offset + 3] = v[3];`,"vec2<i32>":`
        dataInt32[offset] = v[0];
        dataInt32[offset + 1] = v[1];`,"vec3<i32>":`
        dataInt32[offset] = v[0];
        dataInt32[offset + 1] = v[1];
        dataInt32[offset + 2] = v[2];`,"vec4<i32>":`
        dataInt32[offset] = v[0];
        dataInt32[offset + 1] = v[1];
        dataInt32[offset + 2] = v[2];
        dataInt32[offset + 3] = v[3];`,"vec2<u32>":`
        dataInt32[offset] = v[0];
        dataInt32[offset + 1] = v[1];`,"vec3<u32>":`
        dataInt32[offset] = v[0];
        dataInt32[offset + 1] = v[1];
        dataInt32[offset + 2] = v[2];`,"vec4<u32>":`
        dataInt32[offset] = v[0];
        dataInt32[offset + 1] = v[1];
        dataInt32[offset + 2] = v[2];
        dataInt32[offset + 3] = v[3];`,"mat2x2<f32>":`
        data[offset] = v[0];
        data[offset + 1] = v[1];
        data[offset + 4] = v[2];
        data[offset + 5] = v[3];`,"mat3x3<f32>":`
        data[offset] = v[0];
        data[offset + 1] = v[1];
        data[offset + 2] = v[2];
        data[offset + 4] = v[3];
        data[offset + 5] = v[4];
        data[offset + 6] = v[5];
        data[offset + 8] = v[6];
        data[offset + 9] = v[7];
        data[offset + 10] = v[8];`,"mat4x4<f32>":`
        for (let i = 0; i < 16; i++) {
            data[offset + i] = v[i];
        }`,"mat3x2<f32>":d(3,2),"mat4x2<f32>":d(4,2),"mat2x3<f32>":d(2,3),"mat4x3<f32>":d(4,3),"mat2x4<f32>":d(2,4),"mat3x4<f32>":d(3,4)},X={...T,"mat2x2<f32>":`
        data[offset] = v[0];
        data[offset + 1] = v[1];
        data[offset + 2] = v[2];
        data[offset + 3] = v[3];
    `};export{S as a,p as b,J as c,T as d,X as e,M as f,b as g,B as h,P as i,N as j,z as k,H as l,c as m};
