import{H as wt,W as bt,Z as _t,d as mt,ea as St,h as dt,j as P,k as L,la as Bt,p as vt,pa as At,w as yt,z as gt}from"./chunk-FHKJAZW6.js";var k=new Set,J=!1;function Y(r,t,e=2){let n=t&&t.length,i=n?t[0]*e:r.length;k.size&&k.clear();let o=Pt(r,0,i,e,!0),s=[];if(!o||o.next===o.prev)return s;let u=0,a=0,l=0;if(n&&(o=ye(r,t,o,e)),r.length>80*e){u=r[0],a=r[1];let h=u,d=a;for(let p=e;p<i;p+=e){let m=r[p],f=r[p+1];m<u&&(u=m),f<a&&(a=f),m>h&&(h=m),f>d&&(d=f)}l=Math.max(h-u,d-a),l=l!==0?32767/l:0}return O(o,s,u,a,l),s}function Pt(r,t,e,n,i){let o=null;if(i===Te(r,t,e,n)>0)for(let s=t;s<e;s+=n)o=Ut(s/n|0,r[s],r[s+1],o);else for(let s=e-n;s>=t;s-=n)o=Ut(s/n|0,r[s],r[s+1],o);return o&&G(o,o.next)&&(V(o),o=o.next),o}function M(r,t=r){let e=t===r,n=r,i;do i=!1,n!==n.next&&(k.size===0||!k.has(n))&&(G(n,n.next)||w(n.prev,n,n.next)===0)?((e||n===t)&&(t=n.prev),J=!0,V(n),n=n.prev,i=!0):(e||n!==t)&&(n=n.next,i=!e);while(i||n!==t);return t}function O(r,t,e,n,i){i&&Ae(r,e,n,i);let o=r,s=!1;for(;r.prev!==r.next;){let u=r.prev,a=r.next;if(w(u,r,a)<0&&(i?me(r,e,n,i):pe(r))){t.push(u.i,r.i,a.i),V(r),r=a,o=a;continue}if(r=a,r===o){if(J=!1,r=M(r),J){o=r;continue}if(!s){r=de(r,t),o=r,s=!0;continue}ve(r,t,e,n,i);break}}}function pe(r){let t=r.prev,e=r,n=r.next,i=t.x,o=e.x,s=n.x,u=t.y,a=e.y,l=n.y,h=Math.min(i,o,s),d=Math.min(u,a,l),p=Math.max(i,o,s),m=Math.max(u,a,l),f=n.next;for(;f!==t;){if(f.x>=h&&f.x<=p&&f.y>=d&&f.y<=m&&!(i===f.x&&u===f.y)&&W(i,u,o,a,s,l,f.x,f.y)&&w(f.prev,f,f.next)>=0)return!1;f=f.next}return!0}function me(r,t,e,n){let i=r.prev,o=r,s=r.next,u=i.x,a=o.x,l=s.x,h=i.y,d=o.y,p=s.y,m=Math.min(u,a,l),f=Math.min(h,d,p),y=Math.max(u,a,l),b=Math.max(h,d,p),c=rt(m,f,t,e,n),B=rt(y,b,t,e,n),x=r.prevZ;for(;x&&x.z>=c;){if(x.x>=m&&x.x<=y&&x.y>=f&&x.y<=b&&x!==s&&!(u===x.x&&h===x.y)&&W(u,h,a,d,l,p,x.x,x.y)&&w(x.prev,x,x.next)>=0)return!1;x=x.prevZ}let v=r.nextZ;for(;v&&v.z<=B;){if(v.x>=m&&v.x<=y&&v.y>=f&&v.y<=b&&v!==s&&!(u===v.x&&h===v.y)&&W(u,h,a,d,l,p,v.x,v.y)&&w(v.prev,v,v.next)>=0)return!1;v=v.nextZ}return!0}function de(r,t){let e=r,n=!1;do{let i=e.prev,o=e.next.next;Ct(i,e,e.next,o,!1)&&E(i,o)&&E(o,i)&&(t.push(i.i,e.i,o.i),V(e),V(e.next),e=r=o,n=!0),e=e.next}while(e!==r);return n?M(e):e}function ve(r,t,e,n,i){let o=r;do{let s=o.next.next;for(;s!==o.prev;){if(o.i!==s.i&&Ue(o,s)){let u=kt(o,s);o=M(o,o.next),u=M(u,u.next),O(o,t,e,n,i),O(u,t,e,n,i);return}s=s.next}o=o.next}while(o!==r)}var q=!1;function ye(r,t,e,n){let i=[];for(let o=0,s=t.length;o<s;o++){let u=t[o]*n,a=o<s-1?t[o+1]*n:r.length,l=Pt(r,u,a,n,!1);l===l.next&&k.add(l),i.push(Me(l))}i.sort(ge),be(r.length/n,t.length),Tt(e,e),q=!0;for(let o=0;o<i.length;o++)e=we(i[o],e);return q=!1,M(e)}function ge(r,t){return r.x-t.x||r.y-t.y||(r.next.y-r.y)/(r.next.x-r.x)-(t.next.y-t.y)/(t.next.x-t.x)}function we(r,t){let e=Se(r,t);if(!e)return t;let n=kt(e,r),i=n.next;return Tt(e,i.next),M(n,n.next),M(e,e.next)}var zt=16,g=new Float64Array(0),N=0,tt=[],et=[];function be(r,t){let e=Math.ceil((r+2*t)/zt)+t+2;g.length<e*4&&(g=new Float64Array(e*4)),N=0}function Tt(r,t){let e=r;do{let n=N++;tt[n]=e;let i=1/0,o=1/0,s=-1/0,u=-1/0,a=0;do{let h=e.next;e.z=n,e.x<i&&(i=e.x),e.x>s&&(s=e.x),e.y<o&&(o=e.y),e.y>u&&(u=e.y),h.x<i&&(i=h.x),h.x>s&&(s=h.x),h.y<o&&(o=h.y),h.y>u&&(u=h.y),e=h}while(++a<zt&&e!==t);et[n]=e;let l=n*4;g[l]=i,g[l+1]=o,g[l+2]=s,g[l+3]=u}while(e!==t)}function _e(r,t){let e=r.z*4;t.x<g[e]&&(g[e]=t.x),t.y<g[e+1]&&(g[e+1]=t.y),t.x>g[e+2]&&(g[e+2]=t.x),t.y>g[e+3]&&(g[e+3]=t.y)}function It(r){let t=et[r];for(;t.prev.next!==t;)t=t.next;return et[r]=t,t}function Mt(r){let t=tt[r];for(;t.prev.next!==t;)t=t.next;return tt[r]=t,t}function Se(r,t){let e=t,n=r.x,i=r.y,o=-1/0,s;if(G(r,e))return e;for(let p=0,m=0;p<N;p++,m+=4){if(i<g[m+1]||i>g[m+3]||g[m]>n||g[m+2]<=o)continue;let f=It(p);e=Mt(p);do{if(e.prev.next===e){if(G(r,e.next))return e.next;if(i<=e.y&&i>=e.next.y&&e.next.y!==e.y){let y=e.x+(i-e.y)*(e.next.x-e.x)/(e.next.y-e.y);if(y<=n&&y>o&&(o=y,s=e.x<e.next.x?e:e.next,y===n))return s}}e=e.next}while(e!==f)}if(!s)return null;let u=s.x,a=s.y,l=Math.min(i,a),h=Math.max(i,a),d=1/0;for(let p=0,m=0;p<N;p++,m+=4){if(g[m+2]<u||g[m]>n||g[m+3]<l||g[m+1]>h)continue;let f=It(p);e=Mt(p);do{if(e.prev.next===e&&n>=e.x&&e.x>=u&&n!==e.x&&W(i<a?n:o,i,u,a,i<a?o:n,i,e.x,e.y)){let y=Math.abs(i-e.y)/(n-e.x);(E(e,r)||e.y===i&&e.next.y===i&&e.next.x>n)&&(y<d||y===d&&(e.x>s.x||e.x===s.x&&Be(s,e)))&&(s=e,d=y)}e=e.next}while(e!==f)}return s}function Be(r,t){return w(r.prev,r,t.prev)<0&&w(t.next,r,r.next)<0}var _=[],z=[],I=new Uint32Array(0),T=new Uint32Array(0),C=new Uint32Array(256);function Ae(r,t,e,n){let i=r,o=0;do i.z=rt(i.x,i.y,t,e,n),_[o++]=i,i=i.next;while(i!==r);Ie(o);let s=null;for(let u=0;u<o;u++){let a=_[u];a.prevZ=s,s&&(s.nextZ=a),s=a}s.nextZ=null}function Ie(r){if(r<=32){for(let t=1;t<r;t++){let e=_[t],n=e.z,i=t-1;for(;i>=0&&_[i].z>n;)_[i+1]=_[i],i--;_[i+1]=e}return}I.length<r&&(I=new Uint32Array(r),T=new Uint32Array(r),z=new Array(r));for(let t=0;t<r;t++)I[t]=_[t].z;j(r,_,I,z,T,0),j(r,z,T,_,I,8),j(r,_,I,z,T,16),j(r,z,T,_,I,24)}function j(r,t,e,n,i,o){C.fill(0);for(let u=0;u<r;u++)C[e[u]>>>o&255]++;let s=0;for(let u=0;u<256;u++){let a=C[u];C[u]=s,s+=a}for(let u=0;u<r;u++){let a=e[u],l=C[a>>>o&255]++;n[l]=t[u],i[l]=a}}function rt(r,t,e,n,i){return r=(r-e)*i|0,t=(t-n)*i|0,r=(r|r<<8)&16711935,r=(r|r<<4)&252645135,r=(r|r<<2)&858993459,r=(r|r<<1)&1431655765,t=(t|t<<8)&16711935,t=(t|t<<4)&252645135,t=(t|t<<2)&858993459,t=(t|t<<1)&1431655765,r|t<<1}function Me(r){let t=r,e=r;do(t.x<e.x||t.x===e.x&&t.y<e.y)&&(e=t),t=t.next;while(t!==r);return e}function W(r,t,e,n,i,o,s,u){return(i-s)*(t-u)>=(r-s)*(o-u)&&(r-s)*(n-u)>=(e-s)*(t-u)&&(e-s)*(o-u)>=(i-s)*(n-u)}function Ue(r,t){let e=G(r,t)&&w(r.prev,r,r.next)>0&&w(t.prev,t,t.next)>0;return r.next.i!==t.i&&(e||E(r,t)&&E(t,r)&&(w(r.prev,r,t.prev)!==0||w(r,t.prev,t)!==0))&&!Pe(r,t)&&(e||ze(r,t))}function w(r,t,e){return(t.y-r.y)*(e.x-t.x)-(t.x-r.x)*(e.y-t.y)}function G(r,t){return r.x===t.x&&r.y===t.y}function Ct(r,t,e,n,i=!0){let o=w(r,t,e),s=w(r,t,n),u=w(e,n,r),a=w(e,n,t);return(o>0&&s<0||o<0&&s>0)&&(u>0&&a<0||u<0&&a>0)?!0:i?!!(o===0&&Z(r,e,t)||s===0&&Z(r,n,t)||u===0&&Z(e,r,n)||a===0&&Z(e,t,n)):!1}function Z(r,t,e){return t.x<=Math.max(r.x,e.x)&&t.x>=Math.min(r.x,e.x)&&t.y<=Math.max(r.y,e.y)&&t.y>=Math.min(r.y,e.y)}function Pe(r,t){let e=Math.min(r.x,t.x),n=Math.max(r.x,t.x),i=Math.min(r.y,t.y),o=Math.max(r.y,t.y),s=r;do{let u=s.next;if(s.x>n&&u.x>n||s.x<e&&u.x<e||s.y>o&&u.y>o||s.y<i&&u.y<i){s=u;continue}if(s.i!==r.i&&u.i!==r.i&&s.i!==t.i&&u.i!==t.i&&Ct(s,u,r,t))return!0;s=u}while(s!==r);return!1}function E(r,t){return w(r.prev,r,r.next)<0?w(r,t,r.next)>=0&&w(r,r.prev,t)>=0:w(r,t,r.prev)<0||w(r,r.next,t)<0}function ze(r,t){let e=r,n=!1,i=(r.x+t.x)/2,o=(r.y+t.y)/2;do{let s=e.next;e.y>o!=s.y>o&&i<(s.x-e.x)*(o-e.y)/(s.y-e.y)+e.x&&(n=!n),e=s}while(e!==r);return n}function kt(r,t){let e=nt(r.i,r.x,r.y),n=nt(t.i,t.x,t.y),i=r.next,o=t.prev;return r.next=t,t.prev=r,e.next=i,i.prev=e,n.next=e,e.prev=n,o.next=n,n.prev=o,n}function Ut(r,t,e,n){let i=nt(r,t,e);return n?(i.next=n.next,i.prev=n,n.next.prev=i,n.next=i):(i.prev=i,i.next=i),i}function V(r){r.next.prev=r.prev,r.prev.next=r.next,r.prevZ&&(r.prevZ.nextZ=r.nextZ),r.nextZ&&(r.nextZ.prevZ=r.prevZ),q&&_e(r.prev,r.next)}function nt(r,t,e){return{i:r,x:t,y:e,prev:null,next:null,z:0,prevZ:null,nextZ:null}}function Te(r,t,e,n){let i=0;for(let o=t,s=e-n;o<e;o+=n)i+=(r[s]-r[o])*(r[o+1]+r[s+1]),s=o;return i}var Qe=Y.default||Y;function it(r,t,e){if(r)for(let n in r){let i=n.toLocaleLowerCase(),o=t[i];if(o){let s=r[n];n==="header"&&(s=s.replace(/@in\s+[^;]+;\s*/g,"").replace(/@out\s+[^;]+;\s*/g,"")),e&&o.push(`//----${e}----//`),o.push(s)}else gt(`${n} placement hook does not exist in shader`)}}var Ce=/\{\{(.*?)\}\}/g;function ot(r){let t={};return(r.match(Ce)?.map(n=>n.replace(/[{()}]/g,""))??[]).forEach(n=>{t[n]=[]}),t}function Gt(r,t){let e,n=/@in\s+([^;]+);/g;for(;(e=n.exec(r))!==null;)t.push(e[1])}function st(r,t,e=!1){let n=[];Gt(t,n),r.forEach(u=>{u.header&&Gt(u.header,n)});let i=n;e&&i.sort();let o=i.map((u,a)=>`       @location(${a}) ${u},`).join(`
`),s=t.replace(/@in\s+[^;]+;\s*/g,"");return s=s.replace("{{in}}",`
${o}
`),s}function Et(r,t){let e,n=/@out\s+([^;]+);/g;for(;(e=n.exec(r))!==null;)t.push(e[1])}function ke(r){let e=/\b(\w+)\s*:/g.exec(r);return e?e[1]:""}function Ge(r){let t=/@.*?\s+/g;return r.replace(t,"")}function Vt(r,t){let e=[];Et(t,e),r.forEach(a=>{a.header&&Et(a.header,e)});let n=0,i=e.sort().map(a=>a.indexOf("builtin")>-1?a:`@location(${n++}) ${a}`).join(`,
`),o=e.sort().map(a=>`       var ${Ge(a)};`).join(`
`),s=`return VSOutput(
            ${e.sort().map(a=>` ${ke(a)}`).join(`,
`)});`,u=t.replace(/@out\s+[^;]+;\s*/g,"");return u=u.replace("{{struct}}",`
${i}
`),u=u.replace("{{start}}",`
${o}
`),u=u.replace("{{return}}",`
${s}
`),u}function ut(r,t){let e=r;for(let n in t){let i=t[n];i.join(`
`).length?e=e.replace(`{{${n}}}`,`//-----${n} START-----//
${i.join(`
`)}
//----${n} FINISH----//`):e=e.replace(`{{${n}}}`,"")}return e}var A=Object.create(null),at=new Map,Ee=0;function Dt({template:r,bits:t}){let e=$t(r,t);if(A[e])return A[e];let{vertex:n,fragment:i}=Ve(r,t);return A[e]=Ft(n,i,t),A[e]}function Rt({template:r,bits:t}){let e=$t(r,t);return A[e]||(A[e]=Ft(r.vertex,r.fragment,t)),A[e]}function Ve(r,t){let e=t.map(s=>s.vertex).filter(s=>!!s),n=t.map(s=>s.fragment).filter(s=>!!s),i=st(e,r.vertex,!0);i=Vt(e,i);let o=st(n,r.fragment,!0);return{vertex:i,fragment:o}}function $t(r,t){return t.map(e=>(at.has(e)||at.set(e,Ee++),at.get(e))).sort((e,n)=>e-n).join("-")+r.vertex+r.fragment}function Ft(r,t,e){let n=ot(r),i=ot(t);return e.forEach(o=>{it(o.vertex,n,o.name),it(o.fragment,i,o.name)}),{vertex:ut(r,n),fragment:ut(t,i)}}var Ht=`
    @in aPosition: vec2<f32>;
    @in aUV: vec2<f32>;

    @out @builtin(position) vPosition: vec4<f32>;
    @out vUV : vec2<f32>;
    @out vColor : vec4<f32>;

    {{header}}

    struct VSOutput {
        {{struct}}
    };

    @vertex
    fn main( {{in}} ) -> VSOutput {

        var worldTransformMatrix = globalUniforms.uWorldTransformMatrix;
        var modelMatrix = mat3x3<f32>(
            1.0, 0.0, 0.0,
            0.0, 1.0, 0.0,
            0.0, 0.0, 1.0
          );
        var position = aPosition;
        var uv = aUV;

        {{start}}

        vColor = vec4<f32>(1., 1., 1., 1.);

        {{main}}

        vUV = uv;

        var modelViewProjectionMatrix = globalUniforms.uProjectionMatrix * worldTransformMatrix * modelMatrix;

        vPosition =  vec4<f32>((modelViewProjectionMatrix *  vec3<f32>(position, 1.0)).xy, 0.0, 1.0);

        vColor *= globalUniforms.uWorldColorAlpha;

        {{end}}

        {{return}}
    };
`,jt=`
    @in vUV : vec2<f32>;
    @in vColor : vec4<f32>;

    {{header}}

    @fragment
    fn main(
        {{in}}
      ) -> @location(0) vec4<f32> {

        {{start}}

        var outColor:vec4<f32>;

        {{main}}

        var finalColor:vec4<f32> = outColor * vColor;

        {{end}}

        return finalColor;
      };
`,Zt=`
    in vec2 aPosition;
    in vec2 aUV;

    out vec4 vColor;
    out vec2 vUV;

    {{header}}

    void main(void){

        mat3 worldTransformMatrix = uWorldTransformMatrix;
        mat3 modelMatrix = mat3(
            1.0, 0.0, 0.0,
            0.0, 1.0, 0.0,
            0.0, 0.0, 1.0
          );
        vec2 position = aPosition;
        vec2 uv = aUV;

        {{start}}

        vColor = vec4(1.);

        {{main}}

        vUV = uv;

        mat3 modelViewProjectionMatrix = uProjectionMatrix * worldTransformMatrix * modelMatrix;

        gl_Position = vec4((modelViewProjectionMatrix * vec3(position, 1.0)).xy, 0.0, 1.0);

        vColor *= uWorldColorAlpha;

        {{end}}
    }
`,Nt=`

    in vec4 vColor;
    in vec2 vUV;

    out vec4 finalColor;

    {{header}}

    void main(void) {

        {{start}}

        vec4 outColor;

        {{main}}

        finalColor = outColor * vColor;

        {{end}}
    }
`;var Wt={name:"global-uniforms-bit",vertex:{header:`
        struct GlobalUniforms {
            uProjectionMatrix:mat3x3<f32>,
            uWorldTransformMatrix:mat3x3<f32>,
            uWorldColorAlpha: vec4<f32>,
            uResolution: vec2<f32>,
        }

        @group(0) @binding(0) var<uniform> globalUniforms : GlobalUniforms;
        `}},cr={name:"global-uniforms-ubo-bit",vertex:{header:`
          uniform globalUniforms {
            mat3 uProjectionMatrix;
            mat3 uWorldTransformMatrix;
            vec4 uWorldColorAlpha;
            vec2 uResolution;
          };
        `}},Yt={name:"global-uniforms-bit",vertex:{header:`
          uniform mat3 uProjectionMatrix;
          uniform mat3 uWorldTransformMatrix;
          uniform vec4 uWorldColorAlpha;
          uniform vec2 uResolution;
        `}};function Kt({bits:r,name:t}){let e=Dt({template:{fragment:jt,vertex:Ht},bits:[Wt,...r]});return Bt.from({name:t,vertex:{source:e.vertex,entryPoint:"main"},fragment:{source:e.fragment,entryPoint:"main"}})}function Qt({bits:r,name:t}){return new St({name:t,...Rt({template:{vertex:Zt,fragment:Nt},bits:[Yt,...r]})})}var Xt={name:"color-bit",vertex:{header:`
            @in aColor: vec4<f32>;
        `,main:`
            vColor *= vec4<f32>(aColor.rgb * aColor.a, aColor.a);
        `}},Lt={name:"color-bit",vertex:{header:`
            in vec4 aColor;
        `,main:`
            vColor *= vec4(aColor.rgb * aColor.a, aColor.a);
        `}};var lt={};function De(r){let t=[];if(r===1)t.push("@group(1) @binding(0) var textureSource1: texture_2d<f32>;"),t.push("@group(1) @binding(1) var textureSampler1: sampler;");else{let e=0;for(let n=0;n<r;n++)t.push(`@group(1) @binding(${e++}) var textureSource${n+1}: texture_2d<f32>;`),t.push(`@group(1) @binding(${e++}) var textureSampler${n+1}: sampler;`)}return t.join(`
`)}function Re(r){let t=[];if(r===1)t.push("outColor = textureSampleGrad(textureSource1, textureSampler1, vUV, uvDx, uvDy);");else{t.push("switch vTextureId {");for(let e=0;e<r;e++)e===r-1?t.push("  default:{"):t.push(`  case ${e}:{`),t.push(`      outColor = textureSampleGrad(textureSource${e+1}, textureSampler${e+1}, vUV, uvDx, uvDy);`),t.push("      break;}");t.push("}")}return t.join(`
`)}function Jt(r){return lt[r]||(lt[r]={name:"texture-batch-bit",vertex:{header:`
                @in aTextureIdAndRound: vec2<u32>;
                @out @interpolate(flat) vTextureId : u32;
            `,main:`
                vTextureId = aTextureIdAndRound.y;
            `,end:`
                if(aTextureIdAndRound.x == 1)
                {
                    vPosition = vec4<f32>(roundPixels(vPosition.xy, globalUniforms.uResolution), vPosition.zw);
                }
            `},fragment:{header:`
                @in @interpolate(flat) vTextureId: u32;

                ${De(r)}
            `,main:`
                var uvDx = dpdx(vUV);
                var uvDy = dpdy(vUV);

                ${Re(r)}
            `}}),lt[r]}var ct={};function $e(r){let t=[];for(let e=0;e<r;e++)e>0&&t.push("else"),e<r-1&&t.push(`if(vTextureId < ${e}.5)`),t.push("{"),t.push(`	outColor = texture(uTextures[${e}], vUV);`),t.push("}");return t.join(`
`)}function Ot(r){return ct[r]||(ct[r]={name:"texture-batch-bit",vertex:{header:`
                in vec2 aTextureIdAndRound;
                out float vTextureId;

            `,main:`
                vTextureId = aTextureIdAndRound.y;
            `,end:`
                if(aTextureIdAndRound.x == 1.)
                {
                    gl_Position.xy = roundPixels(gl_Position.xy, uResolution);
                }
            `},fragment:{header:`
                in float vTextureId;

                uniform sampler2D uTextures[${r}];

            `,main:`

                ${$e(r)}
            `}}),ct[r]}var qt={name:"round-pixels-bit",vertex:{header:`
            fn roundPixels(position: vec2<f32>, targetSize: vec2<f32>) -> vec2<f32>
            {
                return (floor(((position * 0.5 + 0.5) * targetSize) + 0.5) / targetSize) * 2.0 - 1.0;
            }
        `}},te={name:"round-pixels-bit",vertex:{header:`
            vec2 roundPixels(vec2 position, vec2 targetSize)
            {
                return (floor(((position * 0.5 + 0.5) * targetSize) + 0.5) / targetSize) * 2.0 - 1.0;
            }
        `}};function ft(r,t,e,n){if(e??(e=0),n??(n=Math.min(r.byteLength-e,t.byteLength)),!(e&7)&&!(n&7)){let i=n/8;new Float64Array(t,0,i).set(new Float64Array(r,e,i))}else if(!(e&3)&&!(n&3)){let i=n/4;new Float32Array(t,0,i).set(new Float32Array(r,e,i))}else new Uint8Array(t).set(new Uint8Array(r,e,n))}var ee={normal:"normal-npm",add:"add-npm",screen:"screen-npm"},Fe=(r=>(r[r.DISABLED=0]="DISABLED",r[r.RENDERING_MASK_ADD=1]="RENDERING_MASK_ADD",r[r.MASK_ACTIVE=2]="MASK_ACTIVE",r[r.INVERSE_MASK_ACTIVE=3]="INVERSE_MASK_ACTIVE",r[r.RENDERING_MASK_REMOVE=4]="RENDERING_MASK_REMOVE",r[r.NONE=5]="NONE",r))(Fe||{});var He=["precision mediump float;","void main(void){","float test = 0.1;","%forloop%","gl_FragColor = vec4(0.0);","}"].join(`
`);function je(r){let t="";for(let e=0;e<r;++e)e>0&&(t+=`
else `),e<r-1&&(t+=`if(test == ${e}.0){}`);return t}function re(r,t){if(r===0)throw new Error("Invalid value of `0` passed to `checkMaxIfStatementsInShader`");let e=t.createShader(t.FRAGMENT_SHADER);try{for(;;){let n=He.replace(/%forloop%/gi,je(r));if(t.shaderSource(e,n),t.compileShader(e),!t.getShaderParameter(e,t.COMPILE_STATUS))r=r/2|0;else break}}finally{t.deleteShader(e)}return r}var ne={};function ie(r){let t=ne[r];if(t)return t;let e=new Int32Array(r);for(let n=0;n<r;n++)e[n]=n;return t=ne[r]=new vt({uTextures:{value:e,type:"i32",size:r}},{isStatic:!0}),t}var D=class{constructor(t){typeof t=="number"?this.rawBinaryData=new ArrayBuffer(t):t instanceof Uint8Array?this.rawBinaryData=t.buffer:this.rawBinaryData=t,this.uint32View=new Uint32Array(this.rawBinaryData),this.float32View=new Float32Array(this.rawBinaryData),this.size=this.rawBinaryData.byteLength}get int8View(){return this._int8View||(this._int8View=new Int8Array(this.rawBinaryData)),this._int8View}get uint8View(){return this._uint8View||(this._uint8View=new Uint8Array(this.rawBinaryData)),this._uint8View}get int16View(){return this._int16View||(this._int16View=new Int16Array(this.rawBinaryData)),this._int16View}get int32View(){return this._int32View||(this._int32View=new Int32Array(this.rawBinaryData)),this._int32View}get float64View(){return this._float64Array||(this._float64Array=new Float64Array(this.rawBinaryData)),this._float64Array}get bigUint64View(){return this._bigUint64Array||(this._bigUint64Array=new BigUint64Array(this.rawBinaryData)),this._bigUint64Array}view(t){return this[`${t}View`]}destroy(){this.rawBinaryData=null,this.uint32View=null,this.float32View=null,this.uint16View=null,this._int8View=null,this._uint8View=null,this._int16View=null,this._int32View=null,this._float64Array=null,this._bigUint64Array=null}static sizeOf(t){switch(t){case"int8":case"uint8":return 1;case"int16":case"uint16":return 2;case"int32":case"uint32":case"float32":return 4;default:throw new Error(`${t} isn't a valid view type`)}}};function xt(r,t){return t.alphaMode==="no-premultiply-alpha"&&ee[r]||r}var U=null;function oe(){if(U)return U;let r=_t();return U=r.getParameter(r.MAX_TEXTURE_IMAGE_UNITS),U=re(U,r),r.getExtension("WEBGL_lose_context")?.loseContext(),U}var K=class{constructor(){this.ids=Object.create(null),this.textures=[],this.count=0}clear(){for(let t=0;t<this.count;t++){let e=this.textures[t];this.textures[t]=null,this.ids[e.uid]=null}this.count=0}};var ht=class{constructor(){this.renderPipeId="batch",this.action="startBatch",this.start=0,this.size=0,this.textures=new K,this.blendMode="normal",this.topology="triangle-strip",this.canBundle=!0}destroy(){this.textures=null,this.gpuBindGroup=null,this.bindGroup=null,this.batcher=null,this.elements=null}},$=[],Q=0;wt.register({clear:()=>{if($.length>0)for(let r of $)r&&r.destroy();$.length=0,Q=0}});function se(){return Q>0?$[--Q]:new ht}function ue(r){r.elements=null,$[Q++]=r}var R=0,ae=class le{constructor(t){this.uid=dt("batcher"),this.dirty=!0,this.batchIndex=0,this.batches=[],this._elements=[],t={...le.defaultOptions,...t},t.maxTextures||(yt("v8.8.0","maxTextures is a required option for Batcher now, please pass it in the options"),t.maxTextures=oe());let{maxTextures:e,attributesInitialSize:n,indicesInitialSize:i}=t;this.attributeBuffer=new D(n*4),this.indexBuffer=new Uint16Array(i),this.maxTextures=e}begin(){this.elementSize=0,this.elementStart=0,this.indexSize=0,this.attributeSize=0;for(let t=0;t<this.batchIndex;t++)ue(this.batches[t]);this.batchIndex=0,this._batchIndexStart=0,this._batchIndexSize=0,this.dirty=!0}add(t){this._elements[this.elementSize++]=t,t._indexStart=this.indexSize,t._attributeStart=this.attributeSize,t._batcher=this,this.indexSize+=t.indexSize,this.attributeSize+=t.attributeSize*this.vertexSize}checkAndUpdateTexture(t,e){let n=t._batch.textures.ids[e._source.uid];return!n&&n!==0?!1:(t._textureId=n,t.texture=e,!0)}updateElement(t){this.dirty=!0;let e=this.attributeBuffer;t.packAsQuad?this.packQuadAttributes(t,e.float32View,e.uint32View,t._attributeStart,t._textureId):this.packAttributes(t,e.float32View,e.uint32View,t._attributeStart,t._textureId)}break(t){let e=this._elements;if(!e[this.elementStart])return;let n=se(),i=n.textures;i.clear();let o=e[this.elementStart],s=xt(o.blendMode,o.texture._source),u=o.topology;this.attributeSize*4>this.attributeBuffer.size&&this._resizeAttributeBuffer(this.attributeSize*4),this.indexSize>this.indexBuffer.length&&this._resizeIndexBuffer(this.indexSize);let a=this.attributeBuffer.float32View,l=this.attributeBuffer.uint32View,h=this.indexBuffer,d=this._batchIndexSize,p=this._batchIndexStart,m="startBatch",f=[],y=this.maxTextures;for(let b=this.elementStart;b<this.elementSize;++b){let c=e[b];e[b]=null;let x=c.texture._source,v=xt(c.blendMode,x),S=s!==v||u!==c.topology;if(x._batchTick===R&&!S){c._textureId=x._textureBindLocation,d+=c.indexSize,c.packAsQuad?(this.packQuadAttributes(c,a,l,c._attributeStart,c._textureId),this.packQuadIndex(h,c._indexStart,c._attributeStart/this.vertexSize)):(this.packAttributes(c,a,l,c._attributeStart,c._textureId),this.packIndex(c,h,c._indexStart,c._attributeStart/this.vertexSize)),c._batch=n,f.push(c);continue}x._batchTick=R,(i.count>=y||S)&&(this._finishBatch(n,p,d-p,i,s,u,t,m,f),m="renderBatch",p=d,s=v,u=c.topology,n=se(),i=n.textures,i.clear(),f=[],++R),c._textureId=x._textureBindLocation=i.count,i.ids[x.uid]=i.count,i.textures[i.count++]=x,c._batch=n,f.push(c),d+=c.indexSize,c.packAsQuad?(this.packQuadAttributes(c,a,l,c._attributeStart,c._textureId),this.packQuadIndex(h,c._indexStart,c._attributeStart/this.vertexSize)):(this.packAttributes(c,a,l,c._attributeStart,c._textureId),this.packIndex(c,h,c._indexStart,c._attributeStart/this.vertexSize))}i.count>0&&(this._finishBatch(n,p,d-p,i,s,u,t,m,f),p=d,++R),this.elementStart=this.elementSize,this._batchIndexStart=p,this._batchIndexSize=d}_finishBatch(t,e,n,i,o,s,u,a,l){t.gpuBindGroup=null,t.bindGroup=null,t.action=a,t.batcher=this,t.textures=i,t.blendMode=o,t.topology=s,t.start=e,t.size=n,t.elements=l,++R,this.batches[this.batchIndex++]=t,u.add(t)}finish(t){this.break(t)}ensureAttributeBuffer(t){t*4<=this.attributeBuffer.size||this._resizeAttributeBuffer(t*4)}ensureIndexBuffer(t){t<=this.indexBuffer.length||this._resizeIndexBuffer(t)}_resizeAttributeBuffer(t){let e=Math.max(t,this.attributeBuffer.size*2),n=new D(e);ft(this.attributeBuffer.rawBinaryData,n.rawBinaryData),this.attributeBuffer=n}_resizeIndexBuffer(t){let e=this.indexBuffer,n=Math.max(t,e.length*1.5);n+=n%2;let i=n>65535?new Uint32Array(n):new Uint16Array(n);if(i.BYTES_PER_ELEMENT!==e.BYTES_PER_ELEMENT)for(let o=0;o<e.length;o++)i[o]=e[o];else ft(e.buffer,i.buffer);this.indexBuffer=i}packQuadIndex(t,e,n){t[e]=n+0,t[e+1]=n+1,t[e+2]=n+2,t[e+3]=n+0,t[e+4]=n+2,t[e+5]=n+3}packIndex(t,e,n,i){let o=t.indices,s=t.indexSize,u=t.indexOffset,a=t.attributeOffset;for(let l=0;l<s;l++)e[n++]=i+o[l+u]-a}destroy(t={}){if(this.batches!==null){for(let e=0;e<this.batchIndex;e++)ue(this.batches[e]);this.batches=null,this.geometry.destroy(!0),this.geometry=null,t.shader&&(this.shader?.destroy(),this.shader=null);for(let e=0;e<this._elements.length;e++)this._elements[e]&&(this._elements[e]._batch=null);this._elements=null,this.indexBuffer=null,this.attributeBuffer.destroy(),this.attributeBuffer=null}}};ae.defaultOptions={maxTextures:null,attributesInitialSize:4,indicesInitialSize:6};var ce=ae;var Ze=new Float32Array(1),Ne=new Uint32Array(1),X=class extends bt{constructor(){let e=new L({data:Ze,label:"attribute-batch-buffer",usage:P.VERTEX|P.COPY_DST,shrinkToFit:!1}),n=new L({data:Ne,label:"index-batch-buffer",usage:P.INDEX|P.COPY_DST,shrinkToFit:!1}),i=24;super({attributes:{aPosition:{buffer:e,format:"float32x2",stride:i,offset:0},aUV:{buffer:e,format:"float32x2",stride:i,offset:8},aColor:{buffer:e,format:"unorm8x4",stride:i,offset:16},aTextureIdAndRound:{buffer:e,format:"uint16x2",stride:i,offset:20}},indexBuffer:n})}};var F=class extends At{constructor(t){let e=Qt({name:"batch",bits:[Lt,Ot(t),te]}),n=Kt({name:"batch",bits:[Xt,Jt(t),qt]});super({glProgram:e,gpuProgram:n,resources:{batchSamplers:ie(t)}}),this.maxTextures=t}};var H=null,fe=class xe extends ce{constructor(t){super(t),this.geometry=new X,this.name=xe.extension.name,this.vertexSize=6,H??(H=new F(t.maxTextures)),this.shader=H}packAttributes(t,e,n,i,o){let s=o<<16|t.roundPixels&65535,u=t.transform,a=u.a,l=u.b,h=u.c,d=u.d,p=u.tx,m=u.ty,{positions:f,uvs:y}=t,b=t.color,c=t.attributeOffset,B=c+t.attributeSize;for(let x=c;x<B;x++){let v=x*2,S=f[v],pt=f[v+1];e[i++]=a*S+h*pt+p,e[i++]=d*pt+l*S+m,e[i++]=y[v],e[i++]=y[v+1],n[i++]=b,n[i++]=s}}packQuadAttributes(t,e,n,i,o){let s=t.texture,u=t.transform,a=u.a,l=u.b,h=u.c,d=u.d,p=u.tx,m=u.ty,f=t.bounds,y=f.maxX,b=f.minX,c=f.maxY,B=f.minY,x=s.uvs,v=t.color,S=o<<16|t.roundPixels&65535;e[i+0]=a*b+h*B+p,e[i+1]=d*B+l*b+m,e[i+2]=x.x0,e[i+3]=x.y0,n[i+4]=v,n[i+5]=S,e[i+6]=a*y+h*B+p,e[i+7]=d*B+l*y+m,e[i+8]=x.x1,e[i+9]=x.y1,n[i+10]=v,n[i+11]=S,e[i+12]=a*y+h*c+p,e[i+13]=d*c+l*y+m,e[i+14]=x.x2,e[i+15]=x.y2,n[i+16]=v,n[i+17]=S,e[i+18]=a*b+h*c+p,e[i+19]=d*c+l*b+m,e[i+20]=x.x3,e[i+21]=x.y3,n[i+22]=v,n[i+23]=S}_updateMaxTextures(t){this.shader.maxTextures!==t&&(H=new F(t),this.shader=H)}destroy(){this.shader=null,super.destroy()}};fe.extension={type:[mt.Batcher],name:"default"};var nn=fe;var he=class{constructor(t){this.items=Object.create(null);let{renderer:e,type:n,onUnload:i,priority:o,name:s}=t;this._renderer=e,e.gc.addResourceHash(this,"items",n,o??0),this._onUnload=i,this.name=s}add(t){return this.items[t.uid]?!1:(this.items[t.uid]=t,t.once("unload",this.remove,this),t._gcLastUsed=this._renderer.gc.now,!0)}remove(t,...e){if(!this.items[t.uid])return;let n=t._gpuData[this._renderer.uid];n&&(this._onUnload?.(t,...e),n.destroy(),t._gpuData[this._renderer.uid]=null,this.items[t.uid]=null)}removeAll(...t){Object.values(this.items).forEach(e=>e&&this.remove(e,...t))}destroy(...t){this.removeAll(...t),this.items=Object.create(null),this._renderer=null,this._onUnload=null}};export{Qe as a,D as b,it as c,ot as d,st as e,Vt as f,ut as g,Dt as h,Rt as i,Ht as j,jt as k,Zt as l,Nt as m,Wt as n,cr as o,Yt as p,Kt as q,Qt as r,Xt as s,Lt as t,Jt as u,Ot as v,qt as w,te as x,ft as y,ee as z,Fe as A,xt as B,re as C,oe as D,K as E,ht as F,ce as G,X as H,ie as I,F as J,nn as K,he as L};
