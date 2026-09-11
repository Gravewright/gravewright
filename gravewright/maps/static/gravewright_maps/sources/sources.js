// gravewright/maps/frontend/shared/config/i18n/text.js
var listeners = /* @__PURE__ */ new Set();
function notifyTextChange() {
  for (const listener of listeners)
    listener();
}
var currentLocale = () => "en";
var resolve = (source) => source;
function registerTextResolver(resolver, locale = () => "en") {
  resolve = resolver;
  currentLocale = locale;
  notifyTextChange();
  return () => {
    if (resolve === resolver) {
      resolve = (source) => source;
      currentLocale = () => "en";
      notifyTextChange();
    }
  };
}
function text(source, ...values) {
  return resolve(source).replace(/\{(\d+)\}/g, (match, index) => Number(index) < values.length ? String(values[Number(index)]) : match);
}
if (typeof window !== "undefined") {
  const apply = (detail) => registerTextResolver((source) => {
    const translated = detail.messages?.text?.[source];
    return typeof translated === "string" ? translated : source;
  }, () => detail.id || "en");
  window.addEventListener("gravewright:locale", (event) => apply(event.detail));
  if (window.gravewrightLocale) apply(window.gravewrightLocale);
}

// gravewright/maps/frontend/features/lighting/model/light-profiles.js
var lightPresets = [
  { id: "torch", get name() {
    return text("Torch");
  }, bright_radius: 2, dim_radius: 5, intensity: 0.9, color: "#ff9a3c", angle: 360 },
  { id: "pulse", get name() {
    return text("Pulse");
  }, bright_radius: 2, dim_radius: 5, intensity: 0.9, color: "#55aaff", angle: 360 },
  { id: "none", get name() {
    return text("Steady");
  }, bright_radius: 2, dim_radius: 4, intensity: 0.85, color: "#ffd8a8", angle: 360 }
];

// gravewright/maps/frontend/features/effects/model/particle-profiles.js
var PARTICLE_DEFAULTS = {
  smoke: { scale: 3, density: 0.6, color: "#9aa3ad" },
  ember: { scale: 2, density: 0.5, color: "#ff9040" },
  dust: { scale: 6, density: 0.45, color: "#d8cdb4" },
  arcane: { scale: 2.5, density: 0.6, color: "#c9a6ff" },
  rain: { scale: 8, density: 0.7, color: "#9bc9e8" },
  snow: { scale: 8, density: 0.65, color: "#edf7ff" },
  firefly: { scale: 5, density: 0.55, color: "#ffe46b" },
  leaves: { scale: 7, density: 0.55, color: "#a87035" },
  bubbles: { scale: 4, density: 0.6, color: "#8de8ff" },
  ash: { scale: 8, density: 0.6, color: "#77736e" },
  blood: { scale: 3, density: 0.7, color: "#a10f20" },
  runes: { scale: 3, density: 0.65, color: "#69a7ff" }
};

// gravewright/maps/frontend/features/scene-layers/lib/shader-language.js
var PREAMBLE = `#version 300 es
precision highp float;

in vec2 vTextureCoord;
out vec4 finalColor;



uniform sampler2D gwUTexture;

uniform float gwUQuality;
uniform float gwULightResponse;
uniform float gwUAmbient;
uniform float gwUTime;
uniform float gwUIntensity;
uniform float gwUOpacity;
uniform float gwUScale;
uniform float gwUSpeed;
uniform vec3 gwUColor;


uniform vec2 gwUResolution;
uniform float gwUAspect;



uniform vec2 gwUOrigin;
uniform float gwURadius;
uniform float gwURotation;


uniform vec3 gwUCamera;



uniform sampler2D gwULightBuffer;


uniform vec2 gwUScreen;










uniform vec2 gwUFrameOrigin;


vec2 gwScreen(vec2 uv) {
    return uv * gwUResolution + gwUFrameOrigin;
}


vec2 gwScreenUV(vec2 uv) {
    return gwScreen(uv) / max(gwUScreen, vec2(1.0));
}



vec4 gwLight(vec2 uv) {
    return texture(gwULightBuffer, gwScreenUV(uv));
}



vec4 gwIlluminate(vec4 color, vec2 uv, float strength) {
    vec3 illumination = clamp(vec3(gwUAmbient) + gwLight(uv).rgb, vec3(0.0), vec3(1.5));
    float alpha = max(color.a, 0.0001);
    vec3 linearColor = pow(max(color.rgb / alpha, vec3(0.0)), vec3(2.2));
    vec3 lit = pow(linearColor * mix(vec3(1.0), illumination, clamp(strength, 0.0, 1.0)), vec3(1.0 / 2.2));
    return vec4(lit * color.a, color.a);
}
vec2 gwWorld(vec2 uv) {
    return (gwScreen(uv) - gwUCamera.xy) / max(gwUCamera.z, 0.0001);
}


vec2 gwRotated(vec2 uv) {
    vec2 d = gwWorld(uv) - gwUOrigin;
    float c = cos(gwURotation);
    float s = sin(gwURotation);
    return gwUOrigin + vec2(d.x * c - d.y * s, d.x * s + d.y * c);
}










float gwFeature() {
    float base = gwURadius > 0.0 ? gwURadius * 0.6 : 420.0;
    return max(base * gwUScale, 1.0);
}



vec2 gwPattern(vec2 uv) {


    return (gwRotated(uv) - gwUOrigin) / gwFeature();
}
`;
var USER_PREFIX = `#define uTexture gwUTexture
#define uQuality gwUQuality
#define uTime gwUTime
#define uIntensity gwUIntensity
#define uOpacity gwUOpacity
#define uScale gwUScale
#define uSpeed gwUSpeed
#define uColor gwUColor
#define uResolution gwUResolution
#define uAspect gwUAspect
#define uOrigin gwUOrigin
#define uRadius gwURadius
#define uRotation gwURotation
#define uCamera gwUCamera
#define uLightBuffer gwULightBuffer
#define uScreen gwUScreen
#define uFrameOrigin gwUFrameOrigin
#define main gwUserMain
`;
var USER_SUFFIX = "\n#undef main\nvoid main() { gwUserMain(); finalColor *= gwUOpacity; finalColor = gwIlluminate(finalColor, vTextureCoord, gwULightResponse); }\n";

// gravewright/maps/frontend/features/effects/model/shader-validation.js
var ShaderDraftValidator = class {
  gl;
  validate(source) {
    if (!source.trim())
      return text("The shader is empty.");
    if (source.length > 32e3)
      return text("Text is too long (32000 character limit).");
    this.gl ??= document.createElement("canvas").getContext("webgl2");
    const gl = this.gl;
    if (!gl)
      return text("WebGL 2 is unavailable to validate this shader.");
    const shader = gl.createShader(gl.FRAGMENT_SHADER);
    if (!shader)
      return text("Could not validate the shader.");
    try {
      gl.shaderSource(shader, PREAMBLE + USER_PREFIX + source + USER_SUFFIX);
      gl.compileShader(shader);
      return gl.getShaderParameter(shader, gl.COMPILE_STATUS) ? "" : gl.getShaderInfoLog(shader)?.replaceAll("\0", "").trim() || text("Invalid GLSL code.");
    } finally {
      gl.deleteShader(shader);
    }
  }
  dispose() {
    this.gl?.getExtension("WEBGL_lose_context")?.loseContext();
    this.gl = void 0;
  }
};

// gravewright/maps/frontend/features/scene-layers/lib/shader-presets.js
var shaderPresets = [
  {
    "opacity": 1,
    "intensity": 0.8,
    "scale": 1,
    "speed": 1,
    "rotation": 0,
    "radius": 6,
    "enabled": true,
    "id": "orb-1",
    get "category"() {
      return text("Energy");
    },
    get "name"() {
      return text("Arcane Sun");
    },
    get "description"() {
      return text("Radiant disk with a turbulent corona, long rays, and sparks.");
    },
    "color": "#8f6bff",
    "blend_mode": "add",
    "source": "float gwpHash(vec2 p){return fract(sin(dot(p,vec2(127.1,311.7)))*43758.5453123);}\nfloat gwpNoise(vec2 p){vec2 i=floor(p),f=fract(p);f=f*f*(3.0-2.0*f);return mix(mix(gwpHash(i),gwpHash(i+vec2(1.0,0.0)),f.x),mix(gwpHash(i+vec2(0.0,1.0)),gwpHash(i+vec2(1.0)),f.x),f.y);}\nfloat gwpFbm(vec2 p){float v=0.0,a=0.5;for(int i=0;i<5;i++){if(i>=int(mix(1.0,5.0,uQuality)))break;v+=a*gwpNoise(p);p=p*2.03+vec2(13.7,9.2);a*=0.5;}return v;}\nvec2 gwpRot(vec2 p,float a){float c=cos(a),s=sin(a);return mat2(c,-s,s,c)*p;}\nfloat gwpSat(float x){return clamp(x,0.0,1.0);}\nfloat gwpBand(float x,float c,float w){return exp(-pow((x-c)/max(w,0.0001),2.0));}\nfloat gwpLine(float x,float w){return 1.0-smoothstep(w,w*1.8,abs(x));}\nfloat gwpDisk(vec2 p,float r,float soft){return 1.0-smoothstep(r-soft,r,length(p));}\nvoid main(){\nvec2 p=gwPattern(vTextureCoord);float t=uTime*uSpeed*0.75;float d=length(p);float a0=atan(p.y,p.x);\nfloat corona=gwpFbm(vec2(a0*3.4,t*0.22)+vec2(d*5.0,-t*0.11));\nfloat core=exp(-d*d*6.2);float rim=gwpBand(d,0.61+0.035*sin(t*1.7),0.055);\nfloat rayMask=pow(max(0.0,cos(a0*9.0+t*0.9+corona*2.7)),10.0);\nfloat rays=rayMask*exp(-d*1.45)*(1.0-smoothstep(0.18,0.95,d));\nfloat sparks=pow(gwpNoise(p*18.0+vec2(t,-t*0.7)),16.0)*(1.0-smoothstep(0.28,1.0,d));\nfloat e=(core*1.15+rim*0.9+rays*0.72+sparks*0.45)*(0.78+0.32*corona)*uIntensity;\nfloat a=gwpSat(e);\nvec3 c=mix(uColor,vec3(1.0,0.92,0.72),gwpSat(core+rim+rays*0.4));\nfinalColor=vec4(c*a,a);\n}",
    "light_response": 0,
    "light_emission": 0.15
  },
  {
    "opacity": 1,
    "intensity": 0.8,
    "scale": 1,
    "speed": 1.1,
    "rotation": 0,
    "radius": 6,
    "enabled": true,
    "id": "orb-2",
    get "category"() {
      return text("Energy");
    },
    get "name"() {
      return text("Solar Star");
    },
    get "description"() {
      return text("Pulsing star with two flare patterns and a living corona.");
    },
    "color": "#ff9a32",
    "blend_mode": "screen",
    "source": "float gwpHash(vec2 p){return fract(sin(dot(p,vec2(127.1,311.7)))*43758.5453123);}\nfloat gwpNoise(vec2 p){vec2 i=floor(p),f=fract(p);f=f*f*(3.0-2.0*f);return mix(mix(gwpHash(i),gwpHash(i+vec2(1.0,0.0)),f.x),mix(gwpHash(i+vec2(0.0,1.0)),gwpHash(i+vec2(1.0)),f.x),f.y);}\nfloat gwpFbm(vec2 p){float v=0.0,a=0.5;for(int i=0;i<5;i++){if(i>=int(mix(1.0,5.0,uQuality)))break;v+=a*gwpNoise(p);p=p*2.03+vec2(13.7,9.2);a*=0.5;}return v;}\nvec2 gwpRot(vec2 p,float a){float c=cos(a),s=sin(a);return mat2(c,-s,s,c)*p;}\nfloat gwpSat(float x){return clamp(x,0.0,1.0);}\nfloat gwpBand(float x,float c,float w){return exp(-pow((x-c)/max(w,0.0001),2.0));}\nfloat gwpLine(float x,float w){return 1.0-smoothstep(w,w*1.8,abs(x));}\nfloat gwpDisk(vec2 p,float r,float soft){return 1.0-smoothstep(r-soft,r,length(p));}\nvoid main(){\nvec2 p=gwPattern(vTextureCoord);float t=uTime*uSpeed;float d=length(p);float ang=atan(p.y,p.x);\nfloat disk=exp(-d*d*9.0);float pulse=0.82+0.18*sin(t*3.0);\nfloat flareA=pow(max(0.0,cos(ang*14.0-t*1.6)),22.0)*exp(-d*1.8);\nfloat flareB=pow(max(0.0,cos(ang*5.0+t*0.8)),12.0)*exp(-d*2.4);\nfloat crown=gwpBand(d,0.48+0.03*sin(ang*7.0+t*2.0),0.035);\nfloat grain=0.7+0.45*gwpFbm(p*7.0+vec2(t*0.25));\nfloat e=(disk*1.35*pulse+crown+flareA*0.9+flareB*0.45)*grain*uIntensity;\nfloat a=gwpSat(e);\nvec3 hot=mix(uColor,vec3(1.0,0.98,0.82),gwpSat(disk*1.5+crown));\nfinalColor=vec4(hot*a,a);\n}",
    "light_response": 0,
    "light_emission": 0.15
  },
  {
    "opacity": 1,
    "intensity": 0.8,
    "scale": 0.9,
    "speed": 0.7,
    "rotation": 0,
    "radius": 5,
    "enabled": true,
    "id": "orb-3",
    get "category"() {
      return text("Energy");
    },
    get "name"() {
      return text("Glacial Core");
    },
    get "description"() {
      return text("Hexagonal crystal with facets, spikes, and shimmering frost.");
    },
    "color": "#58cfff",
    "blend_mode": "add",
    "source": "float gwpHash(vec2 p){return fract(sin(dot(p,vec2(127.1,311.7)))*43758.5453123);}\nfloat gwpNoise(vec2 p){vec2 i=floor(p),f=fract(p);f=f*f*(3.0-2.0*f);return mix(mix(gwpHash(i),gwpHash(i+vec2(1.0,0.0)),f.x),mix(gwpHash(i+vec2(0.0,1.0)),gwpHash(i+vec2(1.0)),f.x),f.y);}\nfloat gwpFbm(vec2 p){float v=0.0,a=0.5;for(int i=0;i<5;i++){if(i>=int(mix(1.0,5.0,uQuality)))break;v+=a*gwpNoise(p);p=p*2.03+vec2(13.7,9.2);a*=0.5;}return v;}\nvec2 gwpRot(vec2 p,float a){float c=cos(a),s=sin(a);return mat2(c,-s,s,c)*p;}\nfloat gwpSat(float x){return clamp(x,0.0,1.0);}\nfloat gwpBand(float x,float c,float w){return exp(-pow((x-c)/max(w,0.0001),2.0));}\nfloat gwpLine(float x,float w){return 1.0-smoothstep(w,w*1.8,abs(x));}\nfloat gwpDisk(vec2 p,float r,float soft){return 1.0-smoothstep(r-soft,r,length(p));}\nvoid main(){\nvec2 p=gwPattern(vTextureCoord);float t=uTime*uSpeed*0.45;float d=length(p);float ang=atan(p.y,p.x);\nfloat facets=abs(cos(ang*3.0));\nfloat crystalR=0.52+0.13*facets;\nfloat shell=gwpBand(d,crystalR,0.035);\nfloat spokes=pow(abs(cos(ang*6.0)),18.0)*(1.0-smoothstep(0.08,0.82,d));\nfloat inner=exp(-d*d*13.0)*(0.8+0.2*sin(t*2.0));\nfloat frost=pow(gwpNoise(p*16.0-vec2(t*0.2)),10.0)*gwpDisk(p,0.75,0.2);\nfloat e=(shell*1.15+spokes*0.52+inner+frost*0.28)*uIntensity;\nfloat a=gwpSat(e);\nvec3 c=mix(uColor,vec3(0.92,1.0,1.0),gwpSat(shell+inner+frost*0.4));\nfinalColor=vec4(c*a,a);\n}",
    "light_response": 0,
    "light_emission": 0.15
  },
  {
    "opacity": 1,
    "intensity": 0.9,
    "scale": 1.1,
    "speed": 1,
    "rotation": 0,
    "radius": 5,
    "enabled": true,
    "id": "orb-4",
    get "category"() {
      return text("Energy");
    },
    get "name"() {
      return text("Crimson Eye");
    },
    get "description"() {
      return text("Living arcane eye with an iris, vertical pupil, and pulsing veins.");
    },
    "color": "#ff253a",
    "blend_mode": "screen",
    "source": "float gwpHash(vec2 p){return fract(sin(dot(p,vec2(127.1,311.7)))*43758.5453123);}\nfloat gwpNoise(vec2 p){vec2 i=floor(p),f=fract(p);f=f*f*(3.0-2.0*f);return mix(mix(gwpHash(i),gwpHash(i+vec2(1.0,0.0)),f.x),mix(gwpHash(i+vec2(0.0,1.0)),gwpHash(i+vec2(1.0)),f.x),f.y);}\nfloat gwpFbm(vec2 p){float v=0.0,a=0.5;for(int i=0;i<5;i++){if(i>=int(mix(1.0,5.0,uQuality)))break;v+=a*gwpNoise(p);p=p*2.03+vec2(13.7,9.2);a*=0.5;}return v;}\nvec2 gwpRot(vec2 p,float a){float c=cos(a),s=sin(a);return mat2(c,-s,s,c)*p;}\nfloat gwpSat(float x){return clamp(x,0.0,1.0);}\nfloat gwpBand(float x,float c,float w){return exp(-pow((x-c)/max(w,0.0001),2.0));}\nfloat gwpLine(float x,float w){return 1.0-smoothstep(w,w*1.8,abs(x));}\nfloat gwpDisk(vec2 p,float r,float soft){return 1.0-smoothstep(r-soft,r,length(p));}\nvoid main(){\nvec2 p=gwPattern(vTextureCoord);float t=uTime*uSpeed*0.6;\np=gwpRot(p,0.08*sin(t*0.7));\nfloat d=length(p);\nfloat eye=1.0-smoothstep(0.0,0.055,abs(length(vec2(p.x,p.y*1.8))-0.63));\nfloat iris=gwpBand(d,0.34+0.025*sin(t*1.7),0.12)*(0.65+0.35*gwpFbm(p*8.0+vec2(t*0.2)));\nfloat pupil=1.0-smoothstep(0.035,0.11,abs(p.x));\npupil*=gwpDisk(vec2(p.x,p.y*1.5),0.31,0.07);\nfloat veins=pow(max(0.0,sin(atan(p.y,p.x)*11.0+d*24.0+gwpFbm(p*5.0)*4.0)),12.0)*gwpDisk(p,0.62,0.12);\nfloat e=(eye*0.85+iris*0.9+veins*0.42)*(1.0-pupil*0.8)*uIntensity;\nfloat a=gwpSat(e);\nvec3 c=mix(uColor,vec3(1.0,0.55,0.32),iris*0.65);\nc*=1.0-pupil*0.75;\nfinalColor=vec4(c*a,a);\n}",
    "light_response": 0,
    "light_emission": 0.15
  },
  {
    "opacity": 1,
    "intensity": 0.8,
    "scale": 1,
    "speed": 0.6,
    "rotation": 0,
    "radius": 6,
    "enabled": true,
    "id": "orb-5",
    get "category"() {
      return text("Energy");
    },
    get "name"() {
      return text("Spectral Moon");
    },
    get "description"() {
      return text("Spectral crescent with a halo, motes, and ghostly mist.");
    },
    "color": "#b9d5ff",
    "blend_mode": "screen",
    "source": "float gwpHash(vec2 p){return fract(sin(dot(p,vec2(127.1,311.7)))*43758.5453123);}\nfloat gwpNoise(vec2 p){vec2 i=floor(p),f=fract(p);f=f*f*(3.0-2.0*f);return mix(mix(gwpHash(i),gwpHash(i+vec2(1.0,0.0)),f.x),mix(gwpHash(i+vec2(0.0,1.0)),gwpHash(i+vec2(1.0)),f.x),f.y);}\nfloat gwpFbm(vec2 p){float v=0.0,a=0.5;for(int i=0;i<5;i++){if(i>=int(mix(1.0,5.0,uQuality)))break;v+=a*gwpNoise(p);p=p*2.03+vec2(13.7,9.2);a*=0.5;}return v;}\nvec2 gwpRot(vec2 p,float a){float c=cos(a),s=sin(a);return mat2(c,-s,s,c)*p;}\nfloat gwpSat(float x){return clamp(x,0.0,1.0);}\nfloat gwpBand(float x,float c,float w){return exp(-pow((x-c)/max(w,0.0001),2.0));}\nfloat gwpLine(float x,float w){return 1.0-smoothstep(w,w*1.8,abs(x));}\nfloat gwpDisk(vec2 p,float r,float soft){return 1.0-smoothstep(r-soft,r,length(p));}\nvoid main(){\nvec2 p=gwPattern(vTextureCoord);float t=uTime*uSpeed*0.25;\nfloat d1=length(p-vec2(-0.06,0.0));\nfloat moon=gwpDisk(p-vec2(-0.06,0.0),0.58,0.08)*(1.0-gwpDisk(p-vec2(0.18,0.02),0.52,0.08));\nfloat halo=gwpBand(d1,0.61,0.13)*0.65;\nfloat ghosts=gwpFbm(p*4.5+vec2(t*0.18,-t*0.08))*gwpBand(d1,0.54,0.34);\nfloat motes=pow(gwpNoise(p*14.0+vec2(0.0,t*0.2)),18.0)*gwpDisk(p,0.9,0.2);\nfloat e=(moon+halo+ghosts*0.24+motes*0.38)*uIntensity;\nfloat a=gwpSat(e);\nvec3 c=mix(uColor,vec3(0.94,0.98,1.0),moon+halo*0.45);\nfinalColor=vec4(c*a,a);\n}",
    "light_response": 0,
    "light_emission": 0.15
  },
  {
    "opacity": 1,
    "intensity": 0.8,
    "scale": 1,
    "speed": 1,
    "rotation": 0,
    "radius": 6,
    "enabled": true,
    "id": "portal-1",
    get "category"() {
      return text("Portals");
    },
    get "name"() {
      return text("Violet Portal");
    },
    get "description"() {
      return text("Spiral ring with a turbulent inner surface.");
    },
    "color": "#9b55ff",
    "blend_mode": "add",
    "source": "float gwpHash(vec2 p){return fract(sin(dot(p,vec2(127.1,311.7)))*43758.5453123);}\nfloat gwpNoise(vec2 p){vec2 i=floor(p),f=fract(p);f=f*f*(3.0-2.0*f);return mix(mix(gwpHash(i),gwpHash(i+vec2(1.0,0.0)),f.x),mix(gwpHash(i+vec2(0.0,1.0)),gwpHash(i+vec2(1.0)),f.x),f.y);}\nfloat gwpFbm(vec2 p){float v=0.0,a=0.5;for(int i=0;i<5;i++){if(i>=int(mix(1.0,5.0,uQuality)))break;v+=a*gwpNoise(p);p=p*2.03+vec2(13.7,9.2);a*=0.5;}return v;}\nvec2 gwpRot(vec2 p,float a){float c=cos(a),s=sin(a);return mat2(c,-s,s,c)*p;}\nfloat gwpSat(float x){return clamp(x,0.0,1.0);}\nfloat gwpBand(float x,float c,float w){return exp(-pow((x-c)/max(w,0.0001),2.0));}\nfloat gwpLine(float x,float w){return 1.0-smoothstep(w,w*1.8,abs(x));}\nfloat gwpDisk(vec2 p,float r,float soft){return 1.0-smoothstep(r-soft,r,length(p));}\nvoid main(){\nvec2 p=gwPattern(vTextureCoord);float t=uTime*uSpeed*0.7;float d=length(p);float ang=atan(p.y,p.x);\nfloat warp=(gwpFbm(p*4.0+vec2(t))-0.5)*0.16;\nfloat ring=gwpBand(d,0.69+warp,0.06);\nfloat spiral=0.5+0.5*sin(ang*5.0-d*15.0+t*3.0+warp*10.0);\nfloat inner=(1.0-smoothstep(0.08,0.67,d))*(0.25+0.75*gwpFbm(gwpRot(p,t*0.15)*4.0));\nfloat e=(ring*(0.65+0.75*spiral)+inner*0.5)*uIntensity;\nfloat a=gwpSat(e);\nvec3 c=mix(uColor,vec3(1.0),ring*0.9);\nfinalColor=vec4(c*a,a);\n}",
    "light_response": 0,
    "light_emission": 0.15
  },
  {
    "opacity": 1,
    "intensity": 0.95,
    "scale": 1,
    "speed": 1,
    "rotation": 0,
    "radius": 5,
    "enabled": true,
    "id": "portal-2",
    get "category"() {
      return text("Portals");
    },
    get "name"() {
      return text("Infernal Rift");
    },
    get "description"() {
      return text("Jagged, glowing, unstable vertical rift.");
    },
    "color": "#ff3b18",
    "blend_mode": "screen",
    "source": "float gwpHash(vec2 p){return fract(sin(dot(p,vec2(127.1,311.7)))*43758.5453123);}\nfloat gwpNoise(vec2 p){vec2 i=floor(p),f=fract(p);f=f*f*(3.0-2.0*f);return mix(mix(gwpHash(i),gwpHash(i+vec2(1.0,0.0)),f.x),mix(gwpHash(i+vec2(0.0,1.0)),gwpHash(i+vec2(1.0)),f.x),f.y);}\nfloat gwpFbm(vec2 p){float v=0.0,a=0.5;for(int i=0;i<5;i++){if(i>=int(mix(1.0,5.0,uQuality)))break;v+=a*gwpNoise(p);p=p*2.03+vec2(13.7,9.2);a*=0.5;}return v;}\nvec2 gwpRot(vec2 p,float a){float c=cos(a),s=sin(a);return mat2(c,-s,s,c)*p;}\nfloat gwpSat(float x){return clamp(x,0.0,1.0);}\nfloat gwpBand(float x,float c,float w){return exp(-pow((x-c)/max(w,0.0001),2.0));}\nfloat gwpLine(float x,float w){return 1.0-smoothstep(w,w*1.8,abs(x));}\nfloat gwpDisk(vec2 p,float r,float soft){return 1.0-smoothstep(r-soft,r,length(p));}\nvoid main(){\nvec2 p=gwPattern(vTextureCoord);float t=uTime*uSpeed*1.1;\nvec2 q=gwpRot(p,0.17*sin(t*0.3));\nfloat jag=(gwpFbm(vec2(q.y*5.0,t*0.35))-0.5)*0.28;\nfloat crack=gwpLine(q.x+jag,0.055+0.018*sin(q.y*18.0+t*2.0));\nfloat body=crack*(1.0-smoothstep(0.82,1.05,abs(q.y)));\nfloat glow=exp(-abs(q.x+jag)*7.0)*(1.0-smoothstep(0.76,1.05,abs(q.y)));\nfloat teeth=pow(max(0.0,sin(q.y*19.0+t*1.7+gwpFbm(q*4.0)*3.0)),10.0)*glow;\nfloat e=(body*1.2+glow*0.65+teeth*0.38)*uIntensity;\nfloat a=gwpSat(e);\nvec3 c=mix(uColor,vec3(1.0,0.72,0.22),body+teeth*0.5);\nfinalColor=vec4(c*a,a);\n}",
    "light_response": 0,
    "light_emission": 0.15
  },
  {
    "opacity": 1,
    "intensity": 0.8,
    "scale": 1.1,
    "speed": 0.7,
    "rotation": 0,
    "radius": 6,
    "enabled": true,
    "id": "portal-3",
    get "category"() {
      return text("Portals");
    },
    get "name"() {
      return text("Fey Passage");
    },
    get "description"() {
      return text("A crown of petals and runes with a shimmering interior.");
    },
    "color": "#55e89b",
    "blend_mode": "screen",
    "source": "float gwpHash(vec2 p){return fract(sin(dot(p,vec2(127.1,311.7)))*43758.5453123);}\nfloat gwpNoise(vec2 p){vec2 i=floor(p),f=fract(p);f=f*f*(3.0-2.0*f);return mix(mix(gwpHash(i),gwpHash(i+vec2(1.0,0.0)),f.x),mix(gwpHash(i+vec2(0.0,1.0)),gwpHash(i+vec2(1.0)),f.x),f.y);}\nfloat gwpFbm(vec2 p){float v=0.0,a=0.5;for(int i=0;i<5;i++){if(i>=int(mix(1.0,5.0,uQuality)))break;v+=a*gwpNoise(p);p=p*2.03+vec2(13.7,9.2);a*=0.5;}return v;}\nvec2 gwpRot(vec2 p,float a){float c=cos(a),s=sin(a);return mat2(c,-s,s,c)*p;}\nfloat gwpSat(float x){return clamp(x,0.0,1.0);}\nfloat gwpBand(float x,float c,float w){return exp(-pow((x-c)/max(w,0.0001),2.0));}\nfloat gwpLine(float x,float w){return 1.0-smoothstep(w,w*1.8,abs(x));}\nfloat gwpDisk(vec2 p,float r,float soft){return 1.0-smoothstep(r-soft,r,length(p));}\nvoid main(){\nvec2 p=gwPattern(vTextureCoord);float t=uTime*uSpeed*0.35;float d=length(p);float ang=atan(p.y,p.x);\nfloat petals=0.56+0.11*cos(ang*7.0+t*0.7);\nfloat wreath=gwpBand(d,petals,0.055);\nfloat runes=pow(max(0.0,cos(ang*14.0-t*0.4)),16.0)*gwpBand(d,0.73,0.09);\nfloat shimmer=(1.0-smoothstep(0.12,0.7,d))*(0.3+0.7*gwpFbm(p*5.0+vec2(t*0.15,-t*0.2)));\nfloat e=(wreath+runes*0.65+shimmer*0.34)*uIntensity;\nfloat a=gwpSat(e);\nvec3 c=mix(uColor,vec3(0.95,1.0,0.82),wreath+runes*0.5);\nfinalColor=vec4(c*a,a);\n}",
    "light_response": 0,
    "light_emission": 0.15
  },
  {
    "opacity": 0.9,
    "intensity": 0.8,
    "scale": 1,
    "speed": 1,
    "rotation": 0,
    "radius": 6,
    "enabled": true,
    "id": "portal-4",
    get "category"() {
      return text("Portals");
    },
    get "name"() {
      return text("Astral Hole");
    },
    get "description"() {
      return text("Empty core with gravitational lensing, a disk, and stars.");
    },
    "color": "#467cff",
    "blend_mode": "add",
    "source": "float gwpHash(vec2 p){return fract(sin(dot(p,vec2(127.1,311.7)))*43758.5453123);}\nfloat gwpNoise(vec2 p){vec2 i=floor(p),f=fract(p);f=f*f*(3.0-2.0*f);return mix(mix(gwpHash(i),gwpHash(i+vec2(1.0,0.0)),f.x),mix(gwpHash(i+vec2(0.0,1.0)),gwpHash(i+vec2(1.0)),f.x),f.y);}\nfloat gwpFbm(vec2 p){float v=0.0,a=0.5;for(int i=0;i<5;i++){if(i>=int(mix(1.0,5.0,uQuality)))break;v+=a*gwpNoise(p);p=p*2.03+vec2(13.7,9.2);a*=0.5;}return v;}\nvec2 gwpRot(vec2 p,float a){float c=cos(a),s=sin(a);return mat2(c,-s,s,c)*p;}\nfloat gwpSat(float x){return clamp(x,0.0,1.0);}\nfloat gwpBand(float x,float c,float w){return exp(-pow((x-c)/max(w,0.0001),2.0));}\nfloat gwpLine(float x,float w){return 1.0-smoothstep(w,w*1.8,abs(x));}\nfloat gwpDisk(vec2 p,float r,float soft){return 1.0-smoothstep(r-soft,r,length(p));}\nvoid main(){\nvec2 p=gwPattern(vTextureCoord);float t=uTime*uSpeed*0.5;float d=length(p);float ang=atan(p.y,p.x);\nfloat hole=1.0-smoothstep(0.22,0.36,d);\nfloat lens=gwpBand(d,0.48+0.03*sin(ang*4.0+t),0.055);\nfloat acc=pow(0.5+0.5*sin(ang*4.0-d*22.0+t*2.2),5.0)*gwpBand(d,0.62,0.25);\nfloat stars=pow(gwpNoise(p*22.0+vec2(t*0.03)),24.0)*gwpDisk(p,0.88,0.12)*(1.0-hole);\nfloat e=(lens*1.15+acc*0.7+stars*0.7)*(1.0-hole*0.92)*uIntensity;\nfloat a=gwpSat(e);\nvec3 c=mix(uColor,vec3(0.88,0.95,1.0),lens+stars);\nfinalColor=vec4(c*a,a);\n}",
    "light_response": 0,
    "light_emission": 0.15
  },
  {
    "opacity": 1,
    "intensity": 0.8,
    "scale": 1,
    "speed": 0.5,
    "rotation": 0,
    "radius": 5,
    "enabled": true,
    "id": "portal-5",
    get "category"() {
      return text("Portals");
    },
    get "name"() {
      return text("Golden Seal");
    },
    get "description"() {
      return text("Precise ritual geometry with rings, glyphs, and symmetrical rays.");
    },
    "color": "#ffc95b",
    "blend_mode": "screen",
    "source": "float gwpHash(vec2 p){return fract(sin(dot(p,vec2(127.1,311.7)))*43758.5453123);}\nfloat gwpNoise(vec2 p){vec2 i=floor(p),f=fract(p);f=f*f*(3.0-2.0*f);return mix(mix(gwpHash(i),gwpHash(i+vec2(1.0,0.0)),f.x),mix(gwpHash(i+vec2(0.0,1.0)),gwpHash(i+vec2(1.0)),f.x),f.y);}\nfloat gwpFbm(vec2 p){float v=0.0,a=0.5;for(int i=0;i<5;i++){if(i>=int(mix(1.0,5.0,uQuality)))break;v+=a*gwpNoise(p);p=p*2.03+vec2(13.7,9.2);a*=0.5;}return v;}\nvec2 gwpRot(vec2 p,float a){float c=cos(a),s=sin(a);return mat2(c,-s,s,c)*p;}\nfloat gwpSat(float x){return clamp(x,0.0,1.0);}\nfloat gwpBand(float x,float c,float w){return exp(-pow((x-c)/max(w,0.0001),2.0));}\nfloat gwpLine(float x,float w){return 1.0-smoothstep(w,w*1.8,abs(x));}\nfloat gwpDisk(vec2 p,float r,float soft){return 1.0-smoothstep(r-soft,r,length(p));}\nvoid main(){\nvec2 p=gwPattern(vTextureCoord);float t=uTime*uSpeed*0.2;float d=length(p);float ang=atan(p.y,p.x);\nfloat r1=gwpBand(d,0.35,0.018);\nfloat r2=gwpBand(d,0.58,0.022);\nfloat r3=gwpBand(d,0.76,0.018);\nfloat spokes=pow(abs(cos(ang*6.0+t*0.25)),30.0)*step(0.34,d)*(1.0-step(0.76,d));\nfloat glyph=pow(max(0.0,cos(ang*12.0+t*0.15)),28.0)*gwpBand(d,0.67,0.065);\nvec2 q1=gwpRot(p,3.14159/6.0);\nvec2 q2=gwpRot(p,-3.14159/6.0);\nfloat triangle=gwpLine(max(abs(q1.x)*0.866+q1.y*0.5,q2.x*0.866-q2.y*0.5)-0.38,0.018);\nfloat e=(r1+r2+r3+spokes*0.45+glyph*0.8+triangle*0.3)*uIntensity;\nfloat a=gwpSat(e);\nvec3 c=mix(uColor,vec3(1.0,0.96,0.7),gwpSat(r1+r2+r3+glyph));\nfinalColor=vec4(c*a,a);\n}",
    "light_response": 0,
    "light_emission": 0.15
  },
  {
    "opacity": 0.72,
    "intensity": 0.8,
    "scale": 2.2,
    "speed": 0.65,
    "rotation": 0,
    "radius": 0,
    "enabled": true,
    "id": "fog-1",
    get "category"() {
      return text("Atmosphere");
    },
    get "name"() {
      return text("Swamp Mist");
    },
    get "description"() {
      return text("Layered banks of damp mist that respond to light.");
    },
    "color": "#708f68",
    "blend_mode": "normal",
    "source": "float gwpHash(vec2 p){return fract(sin(dot(p,vec2(127.1,311.7)))*43758.5453123);}\nfloat gwpNoise(vec2 p){vec2 i=floor(p),f=fract(p);f=f*f*(3.0-2.0*f);return mix(mix(gwpHash(i),gwpHash(i+vec2(1.0,0.0)),f.x),mix(gwpHash(i+vec2(0.0,1.0)),gwpHash(i+vec2(1.0)),f.x),f.y);}\nfloat gwpFbm(vec2 p){float v=0.0,a=0.5;for(int i=0;i<5;i++){if(i>=int(mix(1.0,5.0,uQuality)))break;v+=a*gwpNoise(p);p=p*2.03+vec2(13.7,9.2);a*=0.5;}return v;}\nvec2 gwpRot(vec2 p,float a){float c=cos(a),s=sin(a);return mat2(c,-s,s,c)*p;}\nfloat gwpSat(float x){return clamp(x,0.0,1.0);}\nfloat gwpBand(float x,float c,float w){return exp(-pow((x-c)/max(w,0.0001),2.0));}\nfloat gwpLine(float x,float w){return 1.0-smoothstep(w,w*1.8,abs(x));}\nfloat gwpDisk(vec2 p,float r,float soft){return 1.0-smoothstep(r-soft,r,length(p));}\nvoid main(){\nvec2 p=gwPattern(vTextureCoord);float t=uTime*uSpeed*0.18;\nvec2 q=p*2.4+vec2(t*0.7,t*0.16);\nfloat low=gwpFbm(q+vec2(0.0,p.y*0.4));\nfloat high=gwpFbm(q*2.1-vec2(t*0.22,0.0));\nfloat bank=smoothstep(0.42,0.78,low+high*0.35);\nfloat strata=0.58+0.42*sin(p.y*5.0+low*4.0);\nvec4 L=gwLight(vTextureCoord);\nfloat lit=clamp(L.a,0.0,1.0);\nfloat a=bank*strata*uIntensity*0.7*mix(0.55,1.0,lit);\nvec3 c=mix(uColor,uColor+L.rgb*0.45,lit);\nfinalColor=vec4(c*a,a);\n}",
    "light_response": 0.8,
    "light_emission": 0
  },
  {
    "opacity": 0.82,
    "intensity": 0.9,
    "scale": 1.8,
    "speed": 1,
    "rotation": 0,
    "radius": 10,
    "enabled": true,
    "id": "fog-2",
    get "category"() {
      return text("Atmosphere");
    },
    get "name"() {
      return text("Black Smoke");
    },
    get "description"() {
      return text("Turbulent columns of dense smoke rising and curling.");
    },
    "color": "#30343d",
    "blend_mode": "multiply",
    "source": "float gwpHash(vec2 p){return fract(sin(dot(p,vec2(127.1,311.7)))*43758.5453123);}\nfloat gwpNoise(vec2 p){vec2 i=floor(p),f=fract(p);f=f*f*(3.0-2.0*f);return mix(mix(gwpHash(i),gwpHash(i+vec2(1.0,0.0)),f.x),mix(gwpHash(i+vec2(0.0,1.0)),gwpHash(i+vec2(1.0)),f.x),f.y);}\nfloat gwpFbm(vec2 p){float v=0.0,a=0.5;for(int i=0;i<5;i++){if(i>=int(mix(1.0,5.0,uQuality)))break;v+=a*gwpNoise(p);p=p*2.03+vec2(13.7,9.2);a*=0.5;}return v;}\nvec2 gwpRot(vec2 p,float a){float c=cos(a),s=sin(a);return mat2(c,-s,s,c)*p;}\nfloat gwpSat(float x){return clamp(x,0.0,1.0);}\nfloat gwpBand(float x,float c,float w){return exp(-pow((x-c)/max(w,0.0001),2.0));}\nfloat gwpLine(float x,float w){return 1.0-smoothstep(w,w*1.8,abs(x));}\nfloat gwpDisk(vec2 p,float r,float soft){return 1.0-smoothstep(r-soft,r,length(p));}\nvoid main(){\nvec2 p=gwPattern(vTextureCoord);float t=uTime*uSpeed*0.28;\nvec2 q=vec2(p.x*2.2,p.y*1.25+t*0.55);\nfloat curl=gwpFbm(q*2.0+vec2(gwpFbm(q+3.0),-gwpFbm(q-4.0)));\nfloat columns=gwpFbm(vec2(p.x*4.0,p.y*1.2+t*0.45));\nfloat smoke=smoothstep(0.32,0.74,curl*0.7+columns*0.5);\nfloat feather=1.0-smoothstep(0.65,1.12,length(vec2(p.x*0.9,p.y*0.6)));\nvec4 L=gwLight(vTextureCoord);\nfloat a=smoke*feather*uIntensity*0.82;\nvec3 c=mix(uColor*0.55,uColor+L.rgb*0.12,clamp(L.a,0.0,1.0));\nfinalColor=vec4(c*a,a);\n}",
    "light_response": 0.8,
    "light_emission": 0
  },
  {
    "opacity": 0.58,
    "intensity": 0.8,
    "scale": 2.5,
    "speed": 0.55,
    "rotation": 0,
    "radius": 0,
    "enabled": true,
    "id": "fog-3",
    get "category"() {
      return text("Atmosphere");
    },
    get "name"() {
      return text("Frost Mist");
    },
    get "description"() {
      return text("Low mist with suspended ice crystals.");
    },
    "color": "#a8dcf0",
    "blend_mode": "screen",
    "source": "float gwpHash(vec2 p){return fract(sin(dot(p,vec2(127.1,311.7)))*43758.5453123);}\nfloat gwpNoise(vec2 p){vec2 i=floor(p),f=fract(p);f=f*f*(3.0-2.0*f);return mix(mix(gwpHash(i),gwpHash(i+vec2(1.0,0.0)),f.x),mix(gwpHash(i+vec2(0.0,1.0)),gwpHash(i+vec2(1.0)),f.x),f.y);}\nfloat gwpFbm(vec2 p){float v=0.0,a=0.5;for(int i=0;i<5;i++){if(i>=int(mix(1.0,5.0,uQuality)))break;v+=a*gwpNoise(p);p=p*2.03+vec2(13.7,9.2);a*=0.5;}return v;}\nvec2 gwpRot(vec2 p,float a){float c=cos(a),s=sin(a);return mat2(c,-s,s,c)*p;}\nfloat gwpSat(float x){return clamp(x,0.0,1.0);}\nfloat gwpBand(float x,float c,float w){return exp(-pow((x-c)/max(w,0.0001),2.0));}\nfloat gwpLine(float x,float w){return 1.0-smoothstep(w,w*1.8,abs(x));}\nfloat gwpDisk(vec2 p,float r,float soft){return 1.0-smoothstep(r-soft,r,length(p));}\nvoid main(){\nvec2 p=gwPattern(vTextureCoord);float t=uTime*uSpeed*0.12;\nfloat floorBand=1.0-smoothstep(-0.95,0.65,p.y);\nfloat curls=gwpFbm(vec2(p.x*3.0+t*0.3,p.y*5.0)+vec2(sin(p.y*5.0+t)*0.3,0.0));\nfloat mist=smoothstep(0.46,0.77,curls)*floorBand;\nfloat crystals=pow(gwpNoise(p*18.0+vec2(t*0.12,0.0)),20.0)*floorBand;\nvec4 L=gwLight(vTextureCoord);\nfloat lit=clamp(L.a,0.0,1.0);\nfloat a=(mist*0.55+crystals*0.28)*uIntensity*mix(0.65,1.0,lit);\nvec3 c=mix(uColor,vec3(0.94,1.0,1.0),crystals+lit*0.18);\nfinalColor=vec4(c*a,a);\n}",
    "light_response": 0.8,
    "light_emission": 0
  },
  {
    "opacity": 0.76,
    "intensity": 0.9,
    "scale": 1.6,
    "speed": 1,
    "rotation": 0,
    "radius": 9,
    "enabled": true,
    "id": "fog-4",
    get "category"() {
      return text("Atmosphere");
    },
    get "name"() {
      return text("Purple Miasma");
    },
    get "description"() {
      return text("Cellular toxic gas with bubbles and internal veins.");
    },
    "color": "#9a45b8",
    "blend_mode": "normal",
    "source": "float gwpHash(vec2 p){return fract(sin(dot(p,vec2(127.1,311.7)))*43758.5453123);}\nfloat gwpNoise(vec2 p){vec2 i=floor(p),f=fract(p);f=f*f*(3.0-2.0*f);return mix(mix(gwpHash(i),gwpHash(i+vec2(1.0,0.0)),f.x),mix(gwpHash(i+vec2(0.0,1.0)),gwpHash(i+vec2(1.0)),f.x),f.y);}\nfloat gwpFbm(vec2 p){float v=0.0,a=0.5;for(int i=0;i<5;i++){if(i>=int(mix(1.0,5.0,uQuality)))break;v+=a*gwpNoise(p);p=p*2.03+vec2(13.7,9.2);a*=0.5;}return v;}\nvec2 gwpRot(vec2 p,float a){float c=cos(a),s=sin(a);return mat2(c,-s,s,c)*p;}\nfloat gwpSat(float x){return clamp(x,0.0,1.0);}\nfloat gwpBand(float x,float c,float w){return exp(-pow((x-c)/max(w,0.0001),2.0));}\nfloat gwpLine(float x,float w){return 1.0-smoothstep(w,w*1.8,abs(x));}\nfloat gwpDisk(vec2 p,float r,float soft){return 1.0-smoothstep(r-soft,r,length(p));}\nvoid main(){\nvec2 p=gwPattern(vTextureCoord);float t=uTime*uSpeed*0.32;\nvec2 q=p*4.0+vec2(-t*0.5,t*0.22);\nvec2 cell=floor(q);vec2 f=fract(q)-0.5;\nfloat h=gwpHash(cell);\nvec2 drift=vec2(sin(t+h*8.0),cos(t*0.7+h*11.0))*0.18;\nfloat bubble=exp(-dot(f+drift,f+drift)*(12.0+18.0*h));\nfloat cloud=smoothstep(0.4,0.72,gwpFbm(p*3.0+vec2(t*0.16)));\nfloat veins=pow(max(0.0,sin((p.x-p.y)*9.0+t*1.6+cloud*4.0)),8.0);\nfloat e=(bubble*0.7+cloud*0.65+veins*cloud*0.15)*uIntensity;\nfloat a=min(e,0.76);\nvec3 c=mix(uColor,vec3(0.65,1.0,0.45),bubble*0.12);\nfinalColor=vec4(c*a,a);\n}",
    "light_response": 0.8,
    "light_emission": 0
  },
  {
    "opacity": 0.5,
    "intensity": 0.8,
    "scale": 2,
    "speed": 0.45,
    "rotation": 0,
    "radius": 0,
    "enabled": true,
    "id": "fog-5",
    get "category"() {
      return text("Atmosphere");
    },
    get "name"() {
      return text("Ancient Dust");
    },
    get "description"() {
      return text("Suspended motes, haze, and faint backlit shafts.");
    },
    "color": "#b69a70",
    "blend_mode": "screen",
    "source": "float gwpHash(vec2 p){return fract(sin(dot(p,vec2(127.1,311.7)))*43758.5453123);}\nfloat gwpNoise(vec2 p){vec2 i=floor(p),f=fract(p);f=f*f*(3.0-2.0*f);return mix(mix(gwpHash(i),gwpHash(i+vec2(1.0,0.0)),f.x),mix(gwpHash(i+vec2(0.0,1.0)),gwpHash(i+vec2(1.0)),f.x),f.y);}\nfloat gwpFbm(vec2 p){float v=0.0,a=0.5;for(int i=0;i<5;i++){if(i>=int(mix(1.0,5.0,uQuality)))break;v+=a*gwpNoise(p);p=p*2.03+vec2(13.7,9.2);a*=0.5;}return v;}\nvec2 gwpRot(vec2 p,float a){float c=cos(a),s=sin(a);return mat2(c,-s,s,c)*p;}\nfloat gwpSat(float x){return clamp(x,0.0,1.0);}\nfloat gwpBand(float x,float c,float w){return exp(-pow((x-c)/max(w,0.0001),2.0));}\nfloat gwpLine(float x,float w){return 1.0-smoothstep(w,w*1.8,abs(x));}\nfloat gwpDisk(vec2 p,float r,float soft){return 1.0-smoothstep(r-soft,r,length(p));}\nvoid main(){\nvec2 p=gwPattern(vTextureCoord);float t=uTime*uSpeed*0.08;\nvec2 q=p*12.0;vec2 cell=floor(q);vec2 f=fract(q)-0.5;float h=gwpHash(cell);\nf.y+=fract(t*0.18+h)-0.5;\nf.x+=sin(t*0.7+h*20.0)*0.12;\nfloat mote=exp(-dot(f,f)*(75.0+90.0*h))*step(0.56,h);\nfloat haze=smoothstep(0.52,0.82,gwpFbm(p*2.1+vec2(t*0.05,0.0)));\nfloat shafts=pow(max(0.0,0.5+0.5*sin((p.x+p.y*0.35)*7.0+t*0.15)),10.0)*0.12;\nvec4 L=gwLight(vTextureCoord);float lit=clamp(L.a,0.0,1.0);\nfloat a=(mote*0.85+haze*0.22+shafts)*uIntensity*mix(0.35,1.0,lit);\nvec3 c=mix(uColor,uColor+L.rgb*0.7,lit);\nfinalColor=vec4(c*a,a);\n}",
    "light_response": 0.8,
    "light_emission": 0
  },
  {
    "opacity": 1,
    "intensity": 0.8,
    "scale": 1,
    "speed": 1,
    "rotation": 0,
    "radius": 4,
    "enabled": true,
    "id": "flame-1",
    get "category"() {
      return text("Fire");
    },
    get "name"() {
      return text("Campfire");
    },
    get "description"() {
      return text("Broad flame with irregular tongues and rising embers.");
    },
    "color": "#ff6a18",
    "blend_mode": "add",
    "source": "float gwpHash(vec2 p){return fract(sin(dot(p,vec2(127.1,311.7)))*43758.5453123);}\nfloat gwpNoise(vec2 p){vec2 i=floor(p),f=fract(p);f=f*f*(3.0-2.0*f);return mix(mix(gwpHash(i),gwpHash(i+vec2(1.0,0.0)),f.x),mix(gwpHash(i+vec2(0.0,1.0)),gwpHash(i+vec2(1.0)),f.x),f.y);}\nfloat gwpFbm(vec2 p){float v=0.0,a=0.5;for(int i=0;i<5;i++){if(i>=int(mix(1.0,5.0,uQuality)))break;v+=a*gwpNoise(p);p=p*2.03+vec2(13.7,9.2);a*=0.5;}return v;}\nvec2 gwpRot(vec2 p,float a){float c=cos(a),s=sin(a);return mat2(c,-s,s,c)*p;}\nfloat gwpSat(float x){return clamp(x,0.0,1.0);}\nfloat gwpBand(float x,float c,float w){return exp(-pow((x-c)/max(w,0.0001),2.0));}\nfloat gwpLine(float x,float w){return 1.0-smoothstep(w,w*1.8,abs(x));}\nfloat gwpDisk(vec2 p,float r,float soft){return 1.0-smoothstep(r-soft,r,length(p));}\nvoid main(){\nvec2 p=gwPattern(vTextureCoord);float t=uTime*uSpeed;float y=p.y+0.72;\nfloat sway=(gwpFbm(vec2(y*3.0,t*0.8))-0.5)*0.35;\nfloat width=max(0.08,0.68-(y+0.1)*0.5);\nfloat body=1.0-smoothstep(width*0.35,width,abs(p.x+sway));\nbody*=smoothstep(-0.35,-0.05,y)*(1.0-smoothstep(0.1,1.12,y));\nfloat tongues=0.55+0.55*gwpFbm(vec2((p.x+sway)*5.0,y*4.0-t*1.8));\nfloat ember=pow(gwpNoise(p*16.0-vec2(0.0,t*2.0)),18.0)*smoothstep(-0.3,0.9,y);\nfloat a=gwpSat((body*tongues+ember*0.25)*uIntensity);\nvec3 c=mix(uColor,vec3(1.0,0.95,0.55),gwpSat(body*(1.0-y*0.45)));\nfinalColor=vec4(c*a,a);\n}",
    "light_response": 0,
    "light_emission": 0.35
  },
  {
    "opacity": 1,
    "intensity": 0.8,
    "scale": 0.9,
    "speed": 1.1,
    "rotation": 0,
    "radius": 4,
    "enabled": true,
    "id": "flame-2",
    get "category"() {
      return text("Fire");
    },
    get "name"() {
      return text("Blue Flame");
    },
    get "description"() {
      return text("Narrow blue jet with a white core and fast oscillation.");
    },
    "color": "#299cff",
    "blend_mode": "screen",
    "source": "float gwpHash(vec2 p){return fract(sin(dot(p,vec2(127.1,311.7)))*43758.5453123);}\nfloat gwpNoise(vec2 p){vec2 i=floor(p),f=fract(p);f=f*f*(3.0-2.0*f);return mix(mix(gwpHash(i),gwpHash(i+vec2(1.0,0.0)),f.x),mix(gwpHash(i+vec2(0.0,1.0)),gwpHash(i+vec2(1.0)),f.x),f.y);}\nfloat gwpFbm(vec2 p){float v=0.0,a=0.5;for(int i=0;i<5;i++){if(i>=int(mix(1.0,5.0,uQuality)))break;v+=a*gwpNoise(p);p=p*2.03+vec2(13.7,9.2);a*=0.5;}return v;}\nvec2 gwpRot(vec2 p,float a){float c=cos(a),s=sin(a);return mat2(c,-s,s,c)*p;}\nfloat gwpSat(float x){return clamp(x,0.0,1.0);}\nfloat gwpBand(float x,float c,float w){return exp(-pow((x-c)/max(w,0.0001),2.0));}\nfloat gwpLine(float x,float w){return 1.0-smoothstep(w,w*1.8,abs(x));}\nfloat gwpDisk(vec2 p,float r,float soft){return 1.0-smoothstep(r-soft,r,length(p));}\nvoid main(){\nvec2 p=gwPattern(vTextureCoord);float t=uTime*uSpeed*1.25;float y=p.y+0.78;\nfloat wiggle=sin(y*7.0-t*2.2)*0.05+(gwpNoise(vec2(y*5.0,t))-0.5)*0.12;\nfloat cone=max(0.045,0.34-(y+0.15)*0.2);\nfloat outer=1.0-smoothstep(cone*0.55,cone,abs(p.x+wiggle));\nouter*=smoothstep(-0.3,-0.05,y)*(1.0-smoothstep(0.12,1.18,y));\nfloat core=1.0-smoothstep(cone*0.12,cone*0.42,abs(p.x+wiggle*0.4));\ncore*=1.0-smoothstep(0.05,0.82,y);\nfloat a=gwpSat((outer*0.7+core)*uIntensity);\nvec3 c=mix(uColor,vec3(0.92,0.98,1.0),core);\nfinalColor=vec4(c*a,a);\n}",
    "light_response": 0,
    "light_emission": 0.35
  },
  {
    "opacity": 1,
    "intensity": 0.9,
    "scale": 1,
    "speed": 1,
    "rotation": 0,
    "radius": 4,
    "enabled": true,
    "id": "flame-3",
    get "category"() {
      return text("Fire");
    },
    get "name"() {
      return text("Green Fire");
    },
    get "description"() {
      return text("Bubbling alchemical combustion with green flames.");
    },
    "color": "#52e858",
    "blend_mode": "add",
    "source": "float gwpHash(vec2 p){return fract(sin(dot(p,vec2(127.1,311.7)))*43758.5453123);}\nfloat gwpNoise(vec2 p){vec2 i=floor(p),f=fract(p);f=f*f*(3.0-2.0*f);return mix(mix(gwpHash(i),gwpHash(i+vec2(1.0,0.0)),f.x),mix(gwpHash(i+vec2(0.0,1.0)),gwpHash(i+vec2(1.0)),f.x),f.y);}\nfloat gwpFbm(vec2 p){float v=0.0,a=0.5;for(int i=0;i<5;i++){if(i>=int(mix(1.0,5.0,uQuality)))break;v+=a*gwpNoise(p);p=p*2.03+vec2(13.7,9.2);a*=0.5;}return v;}\nvec2 gwpRot(vec2 p,float a){float c=cos(a),s=sin(a);return mat2(c,-s,s,c)*p;}\nfloat gwpSat(float x){return clamp(x,0.0,1.0);}\nfloat gwpBand(float x,float c,float w){return exp(-pow((x-c)/max(w,0.0001),2.0));}\nfloat gwpLine(float x,float w){return 1.0-smoothstep(w,w*1.8,abs(x));}\nfloat gwpDisk(vec2 p,float r,float soft){return 1.0-smoothstep(r-soft,r,length(p));}\nvoid main(){\nvec2 p=gwPattern(vTextureCoord);float t=uTime*uSpeed*0.8;float y=p.y+0.65;\nfloat bubbling=0.18*sin(p.x*12.0+t*3.0)+0.12*sin(p.x*23.0-t*2.0);\nfloat w=max(0.09,0.56-(y+0.12)*0.4+bubbling*0.18);\nfloat flame=1.0-smoothstep(w*0.45,w,abs(p.x+(gwpFbm(vec2(y*5.0,t))-0.5)*0.28));\nflame*=smoothstep(-0.42,-0.08,y)*(1.0-smoothstep(0.0,0.9,y));\nfloat bubbles=pow(gwpNoise(p*12.0+vec2(t*0.3,-t*1.4)),14.0)*gwpDisk(vec2(p.x,y-0.05),0.72,0.22);\nfloat a=gwpSat((flame*(0.6+0.7*gwpFbm(p*6.0-vec2(0.0,t)))+bubbles*0.35)*uIntensity);\nvec3 c=mix(uColor,vec3(0.85,1.0,0.35),bubbles+flame*0.25);\nfinalColor=vec4(c*a,a);\n}",
    "light_response": 0,
    "light_emission": 0.35
  },
  {
    "opacity": 0.85,
    "intensity": 0.8,
    "scale": 1.05,
    "speed": 1,
    "rotation": 0,
    "radius": 4,
    "enabled": true,
    "id": "flame-4",
    get "category"() {
      return text("Fire");
    },
    get "name"() {
      return text("Dark Ember");
    },
    get "description"() {
      return text("Dark fire pierced by charcoal and red embers.");
    },
    "color": "#d52b20",
    "blend_mode": "screen",
    "source": "float gwpHash(vec2 p){return fract(sin(dot(p,vec2(127.1,311.7)))*43758.5453123);}\nfloat gwpNoise(vec2 p){vec2 i=floor(p),f=fract(p);f=f*f*(3.0-2.0*f);return mix(mix(gwpHash(i),gwpHash(i+vec2(1.0,0.0)),f.x),mix(gwpHash(i+vec2(0.0,1.0)),gwpHash(i+vec2(1.0)),f.x),f.y);}\nfloat gwpFbm(vec2 p){float v=0.0,a=0.5;for(int i=0;i<5;i++){if(i>=int(mix(1.0,5.0,uQuality)))break;v+=a*gwpNoise(p);p=p*2.03+vec2(13.7,9.2);a*=0.5;}return v;}\nvec2 gwpRot(vec2 p,float a){float c=cos(a),s=sin(a);return mat2(c,-s,s,c)*p;}\nfloat gwpSat(float x){return clamp(x,0.0,1.0);}\nfloat gwpBand(float x,float c,float w){return exp(-pow((x-c)/max(w,0.0001),2.0));}\nfloat gwpLine(float x,float w){return 1.0-smoothstep(w,w*1.8,abs(x));}\nfloat gwpDisk(vec2 p,float r,float soft){return 1.0-smoothstep(r-soft,r,length(p));}\nvoid main(){\nvec2 p=gwPattern(vTextureCoord);float t=uTime*uSpeed*0.55;float y=p.y+0.7;\nfloat drift=(gwpFbm(vec2(y*3.0,t*0.4))-0.5)*0.42;\nfloat w=max(0.07,0.5-(y+0.2)*0.38);\nfloat silhouette=1.0-smoothstep(w*0.4,w,abs(p.x+drift));\nsilhouette*=smoothstep(-0.38,-0.05,y)*(1.0-smoothstep(0.0,0.82,y));\nfloat holes=smoothstep(0.48,0.8,gwpFbm(p*7.0-vec2(0.0,t*0.7)));\nfloat ember=pow(gwpNoise(p*18.0+vec2(t*0.2,-t)),20.0)*silhouette;\nfloat a=gwpSat((silhouette*(0.48+0.35*holes)+ember*0.7)*uIntensity);\nvec3 c=mix(uColor*0.38,vec3(1.0,0.16,0.04),ember+silhouette*(1.0-holes)*0.2);\nfinalColor=vec4(c*a,a);\n}",
    "light_response": 0,
    "light_emission": 0.35
  },
  {
    "opacity": 1,
    "intensity": 0.8,
    "scale": 1,
    "speed": 0.7,
    "rotation": 0,
    "radius": 5,
    "enabled": true,
    "id": "flame-5",
    get "category"() {
      return text("Fire");
    },
    get "name"() {
      return text("Sacred Fire");
    },
    get "description"() {
      return text("Symmetrical flame with a halo and golden rays.");
    },
    "color": "#ffd35a",
    "blend_mode": "add",
    "source": "float gwpHash(vec2 p){return fract(sin(dot(p,vec2(127.1,311.7)))*43758.5453123);}\nfloat gwpNoise(vec2 p){vec2 i=floor(p),f=fract(p);f=f*f*(3.0-2.0*f);return mix(mix(gwpHash(i),gwpHash(i+vec2(1.0,0.0)),f.x),mix(gwpHash(i+vec2(0.0,1.0)),gwpHash(i+vec2(1.0)),f.x),f.y);}\nfloat gwpFbm(vec2 p){float v=0.0,a=0.5;for(int i=0;i<5;i++){if(i>=int(mix(1.0,5.0,uQuality)))break;v+=a*gwpNoise(p);p=p*2.03+vec2(13.7,9.2);a*=0.5;}return v;}\nvec2 gwpRot(vec2 p,float a){float c=cos(a),s=sin(a);return mat2(c,-s,s,c)*p;}\nfloat gwpSat(float x){return clamp(x,0.0,1.0);}\nfloat gwpBand(float x,float c,float w){return exp(-pow((x-c)/max(w,0.0001),2.0));}\nfloat gwpLine(float x,float w){return 1.0-smoothstep(w,w*1.8,abs(x));}\nfloat gwpDisk(vec2 p,float r,float soft){return 1.0-smoothstep(r-soft,r,length(p));}\nvoid main(){\nvec2 p=gwPattern(vTextureCoord);float t=uTime*uSpeed*0.6;float y=p.y+0.72;\nfloat w=max(0.08,0.45-(y+0.05)*0.3);\nfloat flame=1.0-smoothstep(w*0.36,w,abs(p.x+sin(y*6.0+t)*0.06));\nflame*=smoothstep(-0.35,-0.08,y)*(1.0-smoothstep(0.0,1.05,y));\nfloat halo=gwpBand(length(p-vec2(0.0,-0.18)),0.62,0.12)*0.35;\nfloat rays=pow(max(0.0,cos(atan(p.y,p.x)*8.0+t*0.35)),22.0)*exp(-length(p)*2.1)*0.5;\nfloat a=gwpSat((flame+halo+rays)*uIntensity);\nvec3 c=mix(uColor,vec3(1.0,1.0,0.86),flame+halo*0.4);\nfinalColor=vec4(c*a,a);\n}",
    "light_response": 0,
    "light_emission": 0.35
  },
  {
    "opacity": 0.65,
    "intensity": 0.8,
    "scale": 1.4,
    "speed": 1,
    "rotation": 0,
    "radius": 0,
    "enabled": true,
    "id": "liquid-1",
    get "category"() {
      return text("Water");
    },
    get "name"() {
      return text("Water Reflection");
    },
    get "description"() {
      return text("Crossing wave caustics with small concentric ripples.");
    },
    "color": "#45a8d8",
    "blend_mode": "screen",
    "source": "float gwpHash(vec2 p){return fract(sin(dot(p,vec2(127.1,311.7)))*43758.5453123);}\nfloat gwpNoise(vec2 p){vec2 i=floor(p),f=fract(p);f=f*f*(3.0-2.0*f);return mix(mix(gwpHash(i),gwpHash(i+vec2(1.0,0.0)),f.x),mix(gwpHash(i+vec2(0.0,1.0)),gwpHash(i+vec2(1.0)),f.x),f.y);}\nfloat gwpFbm(vec2 p){float v=0.0,a=0.5;for(int i=0;i<5;i++){if(i>=int(mix(1.0,5.0,uQuality)))break;v+=a*gwpNoise(p);p=p*2.03+vec2(13.7,9.2);a*=0.5;}return v;}\nvec2 gwpRot(vec2 p,float a){float c=cos(a),s=sin(a);return mat2(c,-s,s,c)*p;}\nfloat gwpSat(float x){return clamp(x,0.0,1.0);}\nfloat gwpBand(float x,float c,float w){return exp(-pow((x-c)/max(w,0.0001),2.0));}\nfloat gwpLine(float x,float w){return 1.0-smoothstep(w,w*1.8,abs(x));}\nfloat gwpDisk(vec2 p,float r,float soft){return 1.0-smoothstep(r-soft,r,length(p));}\nvoid main(){\nvec2 p=gwPattern(vTextureCoord);float t=uTime*uSpeed*0.4;\nfloat w1=sin(p.x*8.0+t*1.7+p.y*2.3);\nfloat w2=sin(p.y*11.0-t*1.2+p.x*3.4);\nfloat w3=sin((p.x+p.y)*6.5+t*0.7);\nfloat caustic=pow(abs(w1+w2+w3)*0.333,5.0);\nfloat ripples=gwpBand(abs(sin(length(p-vec2(sin(t)*0.2,cos(t)*0.2))*18.0-t*2.0)),0.0,0.12);\nvec4 L=gwLight(vTextureCoord);\nfloat lit=clamp(L.a,0.0,1.0);\nfloat a=(caustic*0.72+ripples*0.15)*uIntensity*0.65;\nvec3 c=mix(uColor,vec3(0.78,0.96,1.0)+L.rgb*0.35,gwpSat(caustic+lit*0.25));\nfinalColor=vec4(c*a,a);\n}",
    "light_response": 0.8,
    "light_emission": 0
  },
  {
    "opacity": 0.72,
    "intensity": 0.8,
    "scale": 1.8,
    "speed": 0.65,
    "rotation": 0,
    "radius": 0,
    "enabled": true,
    "id": "liquid-2",
    get "category"() {
      return text("Water");
    },
    get "name"() {
      return text("Ocean Abyss");
    },
    get "description"() {
      return text("Broad, crossing, deep waves with dark troughs.");
    },
    "color": "#164f83",
    "blend_mode": "multiply",
    "source": "float gwpHash(vec2 p){return fract(sin(dot(p,vec2(127.1,311.7)))*43758.5453123);}\nfloat gwpNoise(vec2 p){vec2 i=floor(p),f=fract(p);f=f*f*(3.0-2.0*f);return mix(mix(gwpHash(i),gwpHash(i+vec2(1.0,0.0)),f.x),mix(gwpHash(i+vec2(0.0,1.0)),gwpHash(i+vec2(1.0)),f.x),f.y);}\nfloat gwpFbm(vec2 p){float v=0.0,a=0.5;for(int i=0;i<5;i++){if(i>=int(mix(1.0,5.0,uQuality)))break;v+=a*gwpNoise(p);p=p*2.03+vec2(13.7,9.2);a*=0.5;}return v;}\nvec2 gwpRot(vec2 p,float a){float c=cos(a),s=sin(a);return mat2(c,-s,s,c)*p;}\nfloat gwpSat(float x){return clamp(x,0.0,1.0);}\nfloat gwpBand(float x,float c,float w){return exp(-pow((x-c)/max(w,0.0001),2.0));}\nfloat gwpLine(float x,float w){return 1.0-smoothstep(w,w*1.8,abs(x));}\nfloat gwpDisk(vec2 p,float r,float soft){return 1.0-smoothstep(r-soft,r,length(p));}\nvoid main(){\nvec2 p=gwPattern(vTextureCoord);float t=uTime*uSpeed*0.22;\nfloat swell=0.5+0.5*sin(p.x*3.2+t*0.55+sin(p.y*2.4-t*0.2));\nfloat cross=0.5+0.5*sin(p.y*4.1-t*0.42+p.x*1.6);\nfloat trenches=smoothstep(0.38,0.72,gwpFbm(p*2.3+vec2(t*0.07,-t*0.04)));\nfloat foam=pow(abs(swell-cross),5.0)*0.32;\nfloat a=gwpSat((swell*0.3+cross*0.22+trenches*0.45+foam)*uIntensity*0.72);\nvec3 c=mix(uColor*0.45,uColor*1.15,foam+0.15*swell);\nfinalColor=vec4(c*a,a);\n}",
    "light_response": 0.8,
    "light_emission": 0
  },
  {
    "opacity": 0.7,
    "intensity": 0.8,
    "scale": 1.1,
    "speed": 0.9,
    "rotation": 0,
    "radius": 6,
    "enabled": true,
    "id": "liquid-3",
    get "category"() {
      return text("Water");
    },
    get "name"() {
      return text("Acid Pool");
    },
    get "description"() {
      return text("Corrosive film with cellular bubbles and glowing veins.");
    },
    "color": "#78d934",
    "blend_mode": "screen",
    "source": "float gwpHash(vec2 p){return fract(sin(dot(p,vec2(127.1,311.7)))*43758.5453123);}\nfloat gwpNoise(vec2 p){vec2 i=floor(p),f=fract(p);f=f*f*(3.0-2.0*f);return mix(mix(gwpHash(i),gwpHash(i+vec2(1.0,0.0)),f.x),mix(gwpHash(i+vec2(0.0,1.0)),gwpHash(i+vec2(1.0)),f.x),f.y);}\nfloat gwpFbm(vec2 p){float v=0.0,a=0.5;for(int i=0;i<5;i++){if(i>=int(mix(1.0,5.0,uQuality)))break;v+=a*gwpNoise(p);p=p*2.03+vec2(13.7,9.2);a*=0.5;}return v;}\nvec2 gwpRot(vec2 p,float a){float c=cos(a),s=sin(a);return mat2(c,-s,s,c)*p;}\nfloat gwpSat(float x){return clamp(x,0.0,1.0);}\nfloat gwpBand(float x,float c,float w){return exp(-pow((x-c)/max(w,0.0001),2.0));}\nfloat gwpLine(float x,float w){return 1.0-smoothstep(w,w*1.8,abs(x));}\nfloat gwpDisk(vec2 p,float r,float soft){return 1.0-smoothstep(r-soft,r,length(p));}\nvoid main(){\nvec2 p=gwPattern(vTextureCoord);float t=uTime*uSpeed*0.65;\nvec2 q=p*6.0;vec2 cell=floor(q);vec2 f=fract(q)-0.5;\nfloat h=gwpHash(cell);float r=0.12+0.28*h;\nfloat bubble=gwpBand(length(f+vec2(sin(t+h*8.0),cos(t*0.6+h*10.0))*0.12),r,0.055);\nfloat film=gwpFbm(p*5.0+vec2(t*0.18));\nfloat veins=pow(max(0.0,sin((p.x-p.y)*10.0+t+film*4.0)),9.0);\nfloat a=gwpSat((bubble*0.9+film*0.25+veins*0.18)*uIntensity*0.7);\nvec3 c=mix(uColor,vec3(0.9,1.0,0.18),bubble+veins*0.25);\nfinalColor=vec4(c*a,a);\n}",
    "light_response": 0.8,
    "light_emission": 0
  },
  {
    "opacity": 0.9,
    "intensity": 0.95,
    "scale": 1.3,
    "speed": 1,
    "rotation": 0,
    "radius": 8,
    "enabled": true,
    "id": "liquid-4",
    get "category"() {
      return text("Water");
    },
    get "name"() {
      return text("Flowing Lava");
    },
    get "description"() {
      return text("Dark plates separated by moving incandescent veins.");
    },
    "color": "#ff4b18",
    "blend_mode": "add",
    "source": "float gwpHash(vec2 p){return fract(sin(dot(p,vec2(127.1,311.7)))*43758.5453123);}\nfloat gwpNoise(vec2 p){vec2 i=floor(p),f=fract(p);f=f*f*(3.0-2.0*f);return mix(mix(gwpHash(i),gwpHash(i+vec2(1.0,0.0)),f.x),mix(gwpHash(i+vec2(0.0,1.0)),gwpHash(i+vec2(1.0)),f.x),f.y);}\nfloat gwpFbm(vec2 p){float v=0.0,a=0.5;for(int i=0;i<5;i++){if(i>=int(mix(1.0,5.0,uQuality)))break;v+=a*gwpNoise(p);p=p*2.03+vec2(13.7,9.2);a*=0.5;}return v;}\nvec2 gwpRot(vec2 p,float a){float c=cos(a),s=sin(a);return mat2(c,-s,s,c)*p;}\nfloat gwpSat(float x){return clamp(x,0.0,1.0);}\nfloat gwpBand(float x,float c,float w){return exp(-pow((x-c)/max(w,0.0001),2.0));}\nfloat gwpLine(float x,float w){return 1.0-smoothstep(w,w*1.8,abs(x));}\nfloat gwpDisk(vec2 p,float r,float soft){return 1.0-smoothstep(r-soft,r,length(p));}\nvoid main(){\nvec2 p=gwPattern(vTextureCoord);float t=uTime*uSpeed*0.32;\nfloat n=gwpFbm(p*3.2+vec2(t*0.18,-t*0.06));\nfloat n2=gwpFbm(p*7.0-vec2(t*0.1,t*0.12));\nfloat veins=pow(gwpSat(1.0-abs(n-n2)*3.2),6.0);\nfloat plates=smoothstep(0.43,0.62,n);\nfloat glow=veins*(0.75+0.25*sin(t*1.4+n*8.0));\nfloat a=gwpSat((plates*0.42+glow*1.1)*uIntensity*0.9);\nvec3 c=mix(vec3(0.22,0.025,0.01),uColor,plates);\nc=mix(c,vec3(1.0,0.82,0.22),glow);\nfinalColor=vec4(c*a,a);\n}",
    "light_response": 0.8,
    "light_emission": 0
  },
  {
    "opacity": 0.55,
    "intensity": 0.8,
    "scale": 1.2,
    "speed": 0.8,
    "rotation": 0,
    "radius": 0,
    "enabled": true,
    "id": "liquid-5",
    get "category"() {
      return text("Water");
    },
    get "name"() {
      return text("Mercury");
    },
    get "description"() {
      return text("Metallic surface with specular ridges and liquid interference.");
    },
    "color": "#b9c5d2",
    "blend_mode": "screen",
    "source": "float gwpHash(vec2 p){return fract(sin(dot(p,vec2(127.1,311.7)))*43758.5453123);}\nfloat gwpNoise(vec2 p){vec2 i=floor(p),f=fract(p);f=f*f*(3.0-2.0*f);return mix(mix(gwpHash(i),gwpHash(i+vec2(1.0,0.0)),f.x),mix(gwpHash(i+vec2(0.0,1.0)),gwpHash(i+vec2(1.0)),f.x),f.y);}\nfloat gwpFbm(vec2 p){float v=0.0,a=0.5;for(int i=0;i<5;i++){if(i>=int(mix(1.0,5.0,uQuality)))break;v+=a*gwpNoise(p);p=p*2.03+vec2(13.7,9.2);a*=0.5;}return v;}\nvec2 gwpRot(vec2 p,float a){float c=cos(a),s=sin(a);return mat2(c,-s,s,c)*p;}\nfloat gwpSat(float x){return clamp(x,0.0,1.0);}\nfloat gwpBand(float x,float c,float w){return exp(-pow((x-c)/max(w,0.0001),2.0));}\nfloat gwpLine(float x,float w){return 1.0-smoothstep(w,w*1.8,abs(x));}\nfloat gwpDisk(vec2 p,float r,float soft){return 1.0-smoothstep(r-soft,r,length(p));}\nvoid main(){\nvec2 p=gwPattern(vTextureCoord);float t=uTime*uSpeed*0.5;\nfloat h=sin(p.x*14.0+t)+sin(p.y*9.0-t*0.7)+sin((p.x+p.y)*17.0+t*0.35);\nh/=3.0;\nfloat ridges=pow(abs(h),9.0);\nfloat warp=gwpFbm(p*8.0+vec2(t*0.08));\nfloat spec=pow(gwpSat(0.5+0.5*sin(h*8.0+warp*5.0)),12.0);\nvec4 L=gwLight(vTextureCoord);\nfloat lit=clamp(L.a,0.0,1.0);\nfloat a=gwpSat((0.18+ridges*0.42+spec*0.65)*uIntensity*0.55);\nvec3 c=mix(uColor*0.7,vec3(1.0)+L.rgb*0.25,spec*0.8+lit*0.2);\nfinalColor=vec4(c*a,a);\n}",
    "light_response": 0.8,
    "light_emission": 0
  },
  {
    "opacity": 0.65,
    "intensity": 0.8,
    "scale": 1.8,
    "speed": 1,
    "rotation": 0,
    "radius": 0,
    "enabled": true,
    "id": "weather-1",
    get "category"() {
      return text("Weather");
    },
    get "name"() {
      return text("Light Rain");
    },
    get "description"() {
      return text("Thin, subtle drops tilted by the wind.");
    },
    "color": "#9bc9e8",
    "blend_mode": "screen",
    "source": "float gwpHash(vec2 p){return fract(sin(dot(p,vec2(127.1,311.7)))*43758.5453123);}\nfloat gwpNoise(vec2 p){vec2 i=floor(p),f=fract(p);f=f*f*(3.0-2.0*f);return mix(mix(gwpHash(i),gwpHash(i+vec2(1.0,0.0)),f.x),mix(gwpHash(i+vec2(0.0,1.0)),gwpHash(i+vec2(1.0)),f.x),f.y);}\nfloat gwpFbm(vec2 p){float v=0.0,a=0.5;for(int i=0;i<5;i++){if(i>=int(mix(1.0,5.0,uQuality)))break;v+=a*gwpNoise(p);p=p*2.03+vec2(13.7,9.2);a*=0.5;}return v;}\nvec2 gwpRot(vec2 p,float a){float c=cos(a),s=sin(a);return mat2(c,-s,s,c)*p;}\nfloat gwpSat(float x){return clamp(x,0.0,1.0);}\nfloat gwpBand(float x,float c,float w){return exp(-pow((x-c)/max(w,0.0001),2.0));}\nfloat gwpLine(float x,float w){return 1.0-smoothstep(w,w*1.8,abs(x));}\nfloat gwpDisk(vec2 p,float r,float soft){return 1.0-smoothstep(r-soft,r,length(p));}\nvoid main(){\nvec2 p=gwPattern(vTextureCoord);float t=uTime*uSpeed*0.8;\nvec2 q=gwpRot(p,0.18)*vec2(14.0,8.0)+vec2(t*0.7,-t*3.2);\nvec2 cell=floor(q);vec2 f=fract(q);float h=gwpHash(cell);\nfloat streak=(1.0-smoothstep(0.025,0.06,abs(f.x-h)))*\n             (1.0-smoothstep(0.0,0.55,fract(f.y+h)));\nfloat e=streak*step(0.52,h)*uIntensity;\nfloat a=min(e,0.62);\nvec3 c=mix(uColor,vec3(0.88,0.96,1.0),h*0.25);\nfinalColor=vec4(c*a,a);\n}",
    "light_response": 0.8,
    "light_emission": 0
  },
  {
    "opacity": 0.85,
    "intensity": 0.9,
    "scale": 1.7,
    "speed": 1,
    "rotation": 0,
    "radius": 0,
    "enabled": true,
    "id": "weather-2",
    get "category"() {
      return text("Weather");
    },
    get "name"() {
      return text("Storm");
    },
    get "description"() {
      return text("Heavy rain with clouds and occasional flashes.");
    },
    "color": "#b6d9ef",
    "blend_mode": "screen",
    "source": "float gwpHash(vec2 p){return fract(sin(dot(p,vec2(127.1,311.7)))*43758.5453123);}\nfloat gwpNoise(vec2 p){vec2 i=floor(p),f=fract(p);f=f*f*(3.0-2.0*f);return mix(mix(gwpHash(i),gwpHash(i+vec2(1.0,0.0)),f.x),mix(gwpHash(i+vec2(0.0,1.0)),gwpHash(i+vec2(1.0)),f.x),f.y);}\nfloat gwpFbm(vec2 p){float v=0.0,a=0.5;for(int i=0;i<5;i++){if(i>=int(mix(1.0,5.0,uQuality)))break;v+=a*gwpNoise(p);p=p*2.03+vec2(13.7,9.2);a*=0.5;}return v;}\nvec2 gwpRot(vec2 p,float a){float c=cos(a),s=sin(a);return mat2(c,-s,s,c)*p;}\nfloat gwpSat(float x){return clamp(x,0.0,1.0);}\nfloat gwpBand(float x,float c,float w){return exp(-pow((x-c)/max(w,0.0001),2.0));}\nfloat gwpLine(float x,float w){return 1.0-smoothstep(w,w*1.8,abs(x));}\nfloat gwpDisk(vec2 p,float r,float soft){return 1.0-smoothstep(r-soft,r,length(p));}\nvoid main(){\nvec2 p=gwPattern(vTextureCoord);float t=uTime*uSpeed*1.4;\nvec2 q=gwpRot(p,0.32)*vec2(20.0,6.0)+vec2(t*1.8,-t*5.6);\nvec2 cell=floor(q);vec2 f=fract(q);float h=gwpHash(cell);\nfloat rain=(1.0-smoothstep(0.045,0.1,abs(f.x-h)))*\n           (1.0-smoothstep(0.08,0.8,fract(f.y+h)))*step(0.30,h);\nfloat flash=pow(max(0.0,sin(t*0.37+floor(t*0.37)*4.1)),32.0);\nfloat cloud=smoothstep(0.42,0.72,gwpFbm(p*2.2+vec2(t*0.08)))*0.18;\nfloat a=gwpSat((rain*1.35+cloud+flash*0.28)*uIntensity);\nvec3 c=mix(uColor,vec3(1.0),flash*0.8);\nfinalColor=vec4(c*a,a);\n}",
    "light_response": 0.8,
    "light_emission": 0
  },
  {
    "opacity": 0.8,
    "intensity": 0.8,
    "scale": 1.9,
    "speed": 0.8,
    "rotation": 0,
    "radius": 0,
    "enabled": true,
    "id": "weather-3",
    get "category"() {
      return text("Weather");
    },
    get "name"() {
      return text("Blizzard");
    },
    get "description"() {
      return text("Large flakes and ice crystals blown in a whirlwind.");
    },
    "color": "#edf7ff",
    "blend_mode": "normal",
    "source": "float gwpHash(vec2 p){return fract(sin(dot(p,vec2(127.1,311.7)))*43758.5453123);}\nfloat gwpNoise(vec2 p){vec2 i=floor(p),f=fract(p);f=f*f*(3.0-2.0*f);return mix(mix(gwpHash(i),gwpHash(i+vec2(1.0,0.0)),f.x),mix(gwpHash(i+vec2(0.0,1.0)),gwpHash(i+vec2(1.0)),f.x),f.y);}\nfloat gwpFbm(vec2 p){float v=0.0,a=0.5;for(int i=0;i<5;i++){if(i>=int(mix(1.0,5.0,uQuality)))break;v+=a*gwpNoise(p);p=p*2.03+vec2(13.7,9.2);a*=0.5;}return v;}\nvec2 gwpRot(vec2 p,float a){float c=cos(a),s=sin(a);return mat2(c,-s,s,c)*p;}\nfloat gwpSat(float x){return clamp(x,0.0,1.0);}\nfloat gwpBand(float x,float c,float w){return exp(-pow((x-c)/max(w,0.0001),2.0));}\nfloat gwpLine(float x,float w){return 1.0-smoothstep(w,w*1.8,abs(x));}\nfloat gwpDisk(vec2 p,float r,float soft){return 1.0-smoothstep(r-soft,r,length(p));}\nvoid main(){\nvec2 p=gwPattern(vTextureCoord);float t=uTime*uSpeed*0.45;\nvec2 q=p*9.0;vec2 cell=floor(q);vec2 f=fract(q)-0.5;float h=gwpHash(cell);\nfloat phase=t*(0.25+0.65*h);\nf+=vec2(sin(phase+h*20.0)*0.42,fract(phase*0.45+h)-0.5);\nfloat d=length(f);\nfloat flake=exp(-d*d*(26.0+45.0*h))*step(0.36,h);\nfloat cross=(gwpLine(f.x,0.025)+gwpLine(f.y,0.025))*exp(-d*d*22.0)*step(0.72,h);\nfloat a=gwpSat((flake+cross*0.5)*uIntensity*0.8);\nfinalColor=vec4(uColor*a,a);\n}",
    "light_response": 0.8,
    "light_emission": 0
  },
  {
    "opacity": 0.62,
    "intensity": 0.8,
    "scale": 1.8,
    "speed": 0.6,
    "rotation": 0,
    "radius": 0,
    "enabled": true,
    "id": "weather-4",
    get "category"() {
      return text("Weather");
    },
    get "name"() {
      return text("Ash");
    },
    get "description"() {
      return text("Flat fragments tumbling slowly in dark haze.");
    },
    "color": "#77736e",
    "blend_mode": "multiply",
    "source": "float gwpHash(vec2 p){return fract(sin(dot(p,vec2(127.1,311.7)))*43758.5453123);}\nfloat gwpNoise(vec2 p){vec2 i=floor(p),f=fract(p);f=f*f*(3.0-2.0*f);return mix(mix(gwpHash(i),gwpHash(i+vec2(1.0,0.0)),f.x),mix(gwpHash(i+vec2(0.0,1.0)),gwpHash(i+vec2(1.0)),f.x),f.y);}\nfloat gwpFbm(vec2 p){float v=0.0,a=0.5;for(int i=0;i<5;i++){if(i>=int(mix(1.0,5.0,uQuality)))break;v+=a*gwpNoise(p);p=p*2.03+vec2(13.7,9.2);a*=0.5;}return v;}\nvec2 gwpRot(vec2 p,float a){float c=cos(a),s=sin(a);return mat2(c,-s,s,c)*p;}\nfloat gwpSat(float x){return clamp(x,0.0,1.0);}\nfloat gwpBand(float x,float c,float w){return exp(-pow((x-c)/max(w,0.0001),2.0));}\nfloat gwpLine(float x,float w){return 1.0-smoothstep(w,w*1.8,abs(x));}\nfloat gwpDisk(vec2 p,float r,float soft){return 1.0-smoothstep(r-soft,r,length(p));}\nvoid main(){\nvec2 p=gwPattern(vTextureCoord);float t=uTime*uSpeed*0.18;\nvec2 q=p*10.0;vec2 cell=floor(q);vec2 f=fract(q)-0.5;float h=gwpHash(cell);\nfloat fall=fract(t*0.2+h);\nf.y+=fall-0.5;\nf.x+=sin(t+h*18.0)*0.18;\nfloat angle=t*0.7+h*6.28;\nvec2 r=gwpRot(f,angle);\nfloat shard=exp(-(r.x*r.x*120.0+r.y*r.y*35.0))*step(0.42,h);\nfloat haze=smoothstep(0.56,0.8,gwpFbm(p*2.5+vec2(t*0.04)))*0.18;\nfloat a=gwpSat((shard+haze)*uIntensity*0.62);\nfinalColor=vec4(uColor*a,a);\n}",
    "light_response": 0.8,
    "light_emission": 0
  },
  {
    "opacity": 0.75,
    "intensity": 0.8,
    "scale": 1.7,
    "speed": 1,
    "rotation": 0,
    "radius": 0,
    "enabled": true,
    "id": "weather-5",
    get "category"() {
      return text("Weather");
    },
    get "name"() {
      return text("Arcane Rain");
    },
    get "description"() {
      return text("Magical trails rising and leaving fleeting runes.");
    },
    "color": "#b75cff",
    "blend_mode": "add",
    "source": "float gwpHash(vec2 p){return fract(sin(dot(p,vec2(127.1,311.7)))*43758.5453123);}\nfloat gwpNoise(vec2 p){vec2 i=floor(p),f=fract(p);f=f*f*(3.0-2.0*f);return mix(mix(gwpHash(i),gwpHash(i+vec2(1.0,0.0)),f.x),mix(gwpHash(i+vec2(0.0,1.0)),gwpHash(i+vec2(1.0)),f.x),f.y);}\nfloat gwpFbm(vec2 p){float v=0.0,a=0.5;for(int i=0;i<5;i++){if(i>=int(mix(1.0,5.0,uQuality)))break;v+=a*gwpNoise(p);p=p*2.03+vec2(13.7,9.2);a*=0.5;}return v;}\nvec2 gwpRot(vec2 p,float a){float c=cos(a),s=sin(a);return mat2(c,-s,s,c)*p;}\nfloat gwpSat(float x){return clamp(x,0.0,1.0);}\nfloat gwpBand(float x,float c,float w){return exp(-pow((x-c)/max(w,0.0001),2.0));}\nfloat gwpLine(float x,float w){return 1.0-smoothstep(w,w*1.8,abs(x));}\nfloat gwpDisk(vec2 p,float r,float soft){return 1.0-smoothstep(r-soft,r,length(p));}\nvoid main(){\nvec2 p=gwPattern(vTextureCoord);float t=uTime*uSpeed*0.7;\nvec2 q=gwpRot(p,-0.14)*vec2(15.0,8.0)+vec2(-t*0.45,t*2.6);\nvec2 cell=floor(q);vec2 f=fract(q);float h=gwpHash(cell);\nfloat streak=(1.0-smoothstep(0.03,0.07,abs(f.x-h)))*\n             (1.0-smoothstep(0.0,0.5,fract(1.0-f.y+h)))*step(0.55,h);\nfloat rune=pow(max(0.0,cos((f.x+f.y)*12.0+h*20.0+t)),14.0)*step(0.82,h);\nfloat a=gwpSat((streak+rune*0.5)*uIntensity*0.78);\nvec3 c=mix(uColor,vec3(0.9,0.7,1.0),rune);\nfinalColor=vec4(c*a,a);\n}",
    "light_response": 0.8,
    "light_emission": 0
  },
  {
    "opacity": 1,
    "intensity": 0.8,
    "scale": 1.2,
    "speed": 0.8,
    "rotation": 0,
    "radius": 10,
    "enabled": true,
    "id": "particles-1",
    get "category"() {
      return text("Particles");
    },
    get "name"() {
      return text("Fireflies");
    },
    get "description"() {
      return text("Organic lights wandering and blinking out of phase.");
    },
    "color": "#ffd95a",
    "blend_mode": "add",
    "source": "float gwpHash(vec2 p){return fract(sin(dot(p,vec2(127.1,311.7)))*43758.5453123);}\nfloat gwpNoise(vec2 p){vec2 i=floor(p),f=fract(p);f=f*f*(3.0-2.0*f);return mix(mix(gwpHash(i),gwpHash(i+vec2(1.0,0.0)),f.x),mix(gwpHash(i+vec2(0.0,1.0)),gwpHash(i+vec2(1.0)),f.x),f.y);}\nfloat gwpFbm(vec2 p){float v=0.0,a=0.5;for(int i=0;i<5;i++){if(i>=int(mix(1.0,5.0,uQuality)))break;v+=a*gwpNoise(p);p=p*2.03+vec2(13.7,9.2);a*=0.5;}return v;}\nvec2 gwpRot(vec2 p,float a){float c=cos(a),s=sin(a);return mat2(c,-s,s,c)*p;}\nfloat gwpSat(float x){return clamp(x,0.0,1.0);}\nfloat gwpBand(float x,float c,float w){return exp(-pow((x-c)/max(w,0.0001),2.0));}\nfloat gwpLine(float x,float w){return 1.0-smoothstep(w,w*1.8,abs(x));}\nfloat gwpDisk(vec2 p,float r,float soft){return 1.0-smoothstep(r-soft,r,length(p));}\nvoid main(){\nvec2 p=gwPattern(vTextureCoord);float t=uTime*uSpeed*0.45;\nvec2 q=p*7.0;vec2 cell=floor(q);vec2 f=fract(q)-0.5;float h=gwpHash(cell);\nf+=vec2(sin(t*0.9+h*21.0),cos(t*0.63+h*17.0))*0.28;\nfloat dotv=exp(-dot(f,f)*(55.0+35.0*h))*step(0.48,h);\nfloat blink=pow(0.5+0.5*sin(t*3.0+h*30.0),3.0);\nfloat a=gwpSat(dotv*blink*uIntensity*1.2);\nvec3 c=mix(uColor,vec3(1.0,0.96,0.62),blink*0.7);\nfinalColor=vec4(c*a,a);\n}",
    "light_response": 0,
    "light_emission": 0
  },
  {
    "opacity": 1,
    "intensity": 0.8,
    "scale": 1.2,
    "speed": 0.6,
    "rotation": 0,
    "radius": 10,
    "enabled": true,
    "id": "particles-2",
    get "category"() {
      return text("Particles");
    },
    get "name"() {
      return text("Spores");
    },
    get "description"() {
      return text("Soft spheres rising slowly with occasional halos.");
    },
    "color": "#8dcc73",
    "blend_mode": "screen",
    "source": "float gwpHash(vec2 p){return fract(sin(dot(p,vec2(127.1,311.7)))*43758.5453123);}\nfloat gwpNoise(vec2 p){vec2 i=floor(p),f=fract(p);f=f*f*(3.0-2.0*f);return mix(mix(gwpHash(i),gwpHash(i+vec2(1.0,0.0)),f.x),mix(gwpHash(i+vec2(0.0,1.0)),gwpHash(i+vec2(1.0)),f.x),f.y);}\nfloat gwpFbm(vec2 p){float v=0.0,a=0.5;for(int i=0;i<5;i++){if(i>=int(mix(1.0,5.0,uQuality)))break;v+=a*gwpNoise(p);p=p*2.03+vec2(13.7,9.2);a*=0.5;}return v;}\nvec2 gwpRot(vec2 p,float a){float c=cos(a),s=sin(a);return mat2(c,-s,s,c)*p;}\nfloat gwpSat(float x){return clamp(x,0.0,1.0);}\nfloat gwpBand(float x,float c,float w){return exp(-pow((x-c)/max(w,0.0001),2.0));}\nfloat gwpLine(float x,float w){return 1.0-smoothstep(w,w*1.8,abs(x));}\nfloat gwpDisk(vec2 p,float r,float soft){return 1.0-smoothstep(r-soft,r,length(p));}\nvoid main(){\nvec2 p=gwPattern(vTextureCoord);float t=uTime*uSpeed*0.2;\nvec2 q=p*8.0;vec2 cell=floor(q);vec2 f=fract(q)-0.5;float h=gwpHash(cell);\nf.y+=fract(t*0.18+h)-0.5;\nf.x+=sin(t*0.5+h*12.0)*0.22;\nfloat big=exp(-dot(f,f)*(24.0+24.0*h))*step(0.38,h);\nfloat halo=exp(-dot(f,f)*8.0)*step(0.78,h)*0.22;\nfloat a=gwpSat((big+halo)*uIntensity*0.72);\nvec3 c=mix(uColor,vec3(0.72,1.0,0.65),halo);\nfinalColor=vec4(c*a,a);\n}",
    "light_response": 0,
    "light_emission": 0
  },
  {
    "opacity": 1,
    "intensity": 0.8,
    "scale": 1,
    "speed": 1.15,
    "rotation": 0,
    "radius": 8,
    "enabled": true,
    "id": "particles-3",
    get "category"() {
      return text("Particles");
    },
    get "name"() {
      return text("Sparks");
    },
    get "description"() {
      return text("Ballistic trails with incandescent heads and short tails.");
    },
    "color": "#ff8b24",
    "blend_mode": "add",
    "source": "float gwpHash(vec2 p){return fract(sin(dot(p,vec2(127.1,311.7)))*43758.5453123);}\nfloat gwpNoise(vec2 p){vec2 i=floor(p),f=fract(p);f=f*f*(3.0-2.0*f);return mix(mix(gwpHash(i),gwpHash(i+vec2(1.0,0.0)),f.x),mix(gwpHash(i+vec2(0.0,1.0)),gwpHash(i+vec2(1.0)),f.x),f.y);}\nfloat gwpFbm(vec2 p){float v=0.0,a=0.5;for(int i=0;i<5;i++){if(i>=int(mix(1.0,5.0,uQuality)))break;v+=a*gwpNoise(p);p=p*2.03+vec2(13.7,9.2);a*=0.5;}return v;}\nvec2 gwpRot(vec2 p,float a){float c=cos(a),s=sin(a);return mat2(c,-s,s,c)*p;}\nfloat gwpSat(float x){return clamp(x,0.0,1.0);}\nfloat gwpBand(float x,float c,float w){return exp(-pow((x-c)/max(w,0.0001),2.0));}\nfloat gwpLine(float x,float w){return 1.0-smoothstep(w,w*1.8,abs(x));}\nfloat gwpDisk(vec2 p,float r,float soft){return 1.0-smoothstep(r-soft,r,length(p));}\nvoid main(){\nvec2 p=gwPattern(vTextureCoord);float t=uTime*uSpeed*1.2;\nvec2 q=p*12.0;vec2 cell=floor(q);vec2 f=fract(q)-0.5;float h=gwpHash(cell);\nfloat age=fract(t*0.42+h);\nf.y+=age*1.2-0.62;\nf.x+=sin(age*3.14+h*8.0)*0.18;\nvec2 r=gwpRot(f,-0.28+0.4*h);\nfloat streak=exp(-(r.x*r.x*140.0+r.y*r.y*18.0))*step(0.60,h)*(1.0-age);\nfloat head=exp(-dot(f,f)*120.0)*step(0.6,h);\nfloat a=gwpSat((streak+head*0.7)*uIntensity*1.25);\nvec3 c=mix(uColor,vec3(1.0,0.95,0.55),head);\nfinalColor=vec4(c*a,a);\n}",
    "light_response": 0,
    "light_emission": 0
  },
  {
    "opacity": 1,
    "intensity": 0.8,
    "scale": 1.25,
    "speed": 0.75,
    "rotation": 0,
    "radius": 10,
    "enabled": true,
    "id": "particles-4",
    get "category"() {
      return text("Particles");
    },
    get "name"() {
      return text("Souls");
    },
    get "description"() {
      return text("Floating spectral silhouettes with tails and glowing eyes.");
    },
    "color": "#55bfff",
    "blend_mode": "screen",
    "source": "float gwpHash(vec2 p){return fract(sin(dot(p,vec2(127.1,311.7)))*43758.5453123);}\nfloat gwpNoise(vec2 p){vec2 i=floor(p),f=fract(p);f=f*f*(3.0-2.0*f);return mix(mix(gwpHash(i),gwpHash(i+vec2(1.0,0.0)),f.x),mix(gwpHash(i+vec2(0.0,1.0)),gwpHash(i+vec2(1.0)),f.x),f.y);}\nfloat gwpFbm(vec2 p){float v=0.0,a=0.5;for(int i=0;i<5;i++){if(i>=int(mix(1.0,5.0,uQuality)))break;v+=a*gwpNoise(p);p=p*2.03+vec2(13.7,9.2);a*=0.5;}return v;}\nvec2 gwpRot(vec2 p,float a){float c=cos(a),s=sin(a);return mat2(c,-s,s,c)*p;}\nfloat gwpSat(float x){return clamp(x,0.0,1.0);}\nfloat gwpBand(float x,float c,float w){return exp(-pow((x-c)/max(w,0.0001),2.0));}\nfloat gwpLine(float x,float w){return 1.0-smoothstep(w,w*1.8,abs(x));}\nfloat gwpDisk(vec2 p,float r,float soft){return 1.0-smoothstep(r-soft,r,length(p));}\nvoid main(){\nvec2 p=gwPattern(vTextureCoord);float t=uTime*uSpeed*0.3;\nvec2 q=p*4.5;vec2 cell=floor(q);vec2 f=fract(q)-0.5;float h=gwpHash(cell);\nf+=vec2(sin(t*0.65+h*14.0)*0.32,fract(t*0.12+h)-0.5);\nfloat head=exp(-dot(f-vec2(0.0,-0.08),f-vec2(0.0,-0.08))*26.0)*step(0.42,h);\nfloat tail=exp(-(f.x*f.x*18.0+(f.y-0.22)*(f.y-0.22)*5.0))*step(0.42,h)*(0.6+0.4*sin(t+h*20.0));\nfloat eyes=\n    (exp(-dot(f-vec2(-0.07,-0.11),f-vec2(-0.07,-0.11))*260.0)+\n     exp(-dot(f-vec2(0.07,-0.11),f-vec2(0.07,-0.11))*260.0))*step(0.75,h);\nfloat a=gwpSat((head*0.65+tail*0.5+eyes)*uIntensity);\nvec3 c=mix(uColor,vec3(1.0),eyes);\nfinalColor=vec4(c*a,a);\n}",
    "light_response": 0,
    "light_emission": 0
  },
  {
    "opacity": 1,
    "intensity": 0.8,
    "scale": 1.3,
    "speed": 0.5,
    "rotation": 0,
    "radius": 0,
    "enabled": true,
    "id": "particles-5",
    get "category"() {
      return text("Particles");
    },
    get "name"() {
      return text("Cosmic Dust");
    },
    get "description"() {
      return text("Star field with crosses, twinkling, and a faint nebula.");
    },
    "color": "#a88cff",
    "blend_mode": "add",
    "source": "float gwpHash(vec2 p){return fract(sin(dot(p,vec2(127.1,311.7)))*43758.5453123);}\nfloat gwpNoise(vec2 p){vec2 i=floor(p),f=fract(p);f=f*f*(3.0-2.0*f);return mix(mix(gwpHash(i),gwpHash(i+vec2(1.0,0.0)),f.x),mix(gwpHash(i+vec2(0.0,1.0)),gwpHash(i+vec2(1.0)),f.x),f.y);}\nfloat gwpFbm(vec2 p){float v=0.0,a=0.5;for(int i=0;i<5;i++){if(i>=int(mix(1.0,5.0,uQuality)))break;v+=a*gwpNoise(p);p=p*2.03+vec2(13.7,9.2);a*=0.5;}return v;}\nvec2 gwpRot(vec2 p,float a){float c=cos(a),s=sin(a);return mat2(c,-s,s,c)*p;}\nfloat gwpSat(float x){return clamp(x,0.0,1.0);}\nfloat gwpBand(float x,float c,float w){return exp(-pow((x-c)/max(w,0.0001),2.0));}\nfloat gwpLine(float x,float w){return 1.0-smoothstep(w,w*1.8,abs(x));}\nfloat gwpDisk(vec2 p,float r,float soft){return 1.0-smoothstep(r-soft,r,length(p));}\nvoid main(){\nvec2 p=gwPattern(vTextureCoord);float t=uTime*uSpeed*0.12;\nvec2 q=p*15.0;vec2 cell=floor(q);vec2 f=fract(q)-0.5;float h=gwpHash(cell);\nfloat star=exp(-dot(f,f)*(120.0+120.0*h))*step(0.68,h);\nfloat twinkle=pow(0.5+0.5*sin(t*5.0+h*40.0),5.0);\nfloat cross=(gwpLine(f.x,0.012)+gwpLine(f.y,0.012))*exp(-dot(f,f)*35.0)*step(0.9,h);\nfloat nebula=smoothstep(0.52,0.78,gwpFbm(p*2.1+vec2(t*0.03,-t*0.02)))*0.16;\nfloat a=gwpSat((star*twinkle+cross*0.4+nebula)*uIntensity);\nvec3 c=mix(uColor,vec3(1.0),star*twinkle*0.8);\nfinalColor=vec4(c*a,a);\n}",
    "light_response": 0,
    "light_emission": 0
  },
  {
    "opacity": 0.72,
    "intensity": 0.8,
    "scale": 1,
    "speed": 1,
    "rotation": 0,
    "radius": 0,
    "enabled": true,
    "id": "grid-1",
    get "category"() {
      return text("Patterns");
    },
    get "name"() {
      return text("Arcane Grid");
    },
    get "description"() {
      return text("Hexagonal mesh with pulsing nodes instead of a simple grid.");
    },
    "color": "#655cff",
    "blend_mode": "screen",
    "source": "float gwpHash(vec2 p){return fract(sin(dot(p,vec2(127.1,311.7)))*43758.5453123);}\nfloat gwpNoise(vec2 p){vec2 i=floor(p),f=fract(p);f=f*f*(3.0-2.0*f);return mix(mix(gwpHash(i),gwpHash(i+vec2(1.0,0.0)),f.x),mix(gwpHash(i+vec2(0.0,1.0)),gwpHash(i+vec2(1.0)),f.x),f.y);}\nfloat gwpFbm(vec2 p){float v=0.0,a=0.5;for(int i=0;i<5;i++){if(i>=int(mix(1.0,5.0,uQuality)))break;v+=a*gwpNoise(p);p=p*2.03+vec2(13.7,9.2);a*=0.5;}return v;}\nvec2 gwpRot(vec2 p,float a){float c=cos(a),s=sin(a);return mat2(c,-s,s,c)*p;}\nfloat gwpSat(float x){return clamp(x,0.0,1.0);}\nfloat gwpBand(float x,float c,float w){return exp(-pow((x-c)/max(w,0.0001),2.0));}\nfloat gwpLine(float x,float w){return 1.0-smoothstep(w,w*1.8,abs(x));}\nfloat gwpDisk(vec2 p,float r,float soft){return 1.0-smoothstep(r-soft,r,length(p));}\nvoid main(){\nvec2 p=gwPattern(vTextureCoord);float t=uTime*uSpeed*0.35;\nvec2 q=p*4.5;\nvec2 hq=vec2(q.x+q.y*0.57735,q.y*1.1547);\nvec2 f=abs(fract(hq)-0.5);\nfloat hex=1.0-smoothstep(0.43,0.48,max(f.x,f.y));\nfloat edge=smoothstep(0.31,0.42,max(f.x,f.y))*hex;\nvec2 local=fract(hq)-0.5;\nfloat node=exp(-dot(local,local)*75.0);\nfloat pulse=0.55+0.45*sin(t*2.0+floor(hq.x)+floor(hq.y));\nfloat a=gwpSat((edge*0.52+node*pulse*0.85)*uIntensity*0.72);\nfinalColor=vec4(uColor*a,a);\n}",
    "light_response": 0.8,
    "light_emission": 0
  },
  {
    "opacity": 0.7,
    "intensity": 0.8,
    "scale": 1.1,
    "speed": 1,
    "rotation": 0,
    "radius": 0,
    "enabled": true,
    "id": "grid-2",
    get "category"() {
      return text("Patterns");
    },
    get "name"() {
      return text("Hologram");
    },
    get "description"() {
      return text("Digital grid with scanlines, glitches, and glowing nodes.");
    },
    "color": "#24d9e8",
    "blend_mode": "add",
    "source": "float gwpHash(vec2 p){return fract(sin(dot(p,vec2(127.1,311.7)))*43758.5453123);}\nfloat gwpNoise(vec2 p){vec2 i=floor(p),f=fract(p);f=f*f*(3.0-2.0*f);return mix(mix(gwpHash(i),gwpHash(i+vec2(1.0,0.0)),f.x),mix(gwpHash(i+vec2(0.0,1.0)),gwpHash(i+vec2(1.0)),f.x),f.y);}\nfloat gwpFbm(vec2 p){float v=0.0,a=0.5;for(int i=0;i<5;i++){if(i>=int(mix(1.0,5.0,uQuality)))break;v+=a*gwpNoise(p);p=p*2.03+vec2(13.7,9.2);a*=0.5;}return v;}\nvec2 gwpRot(vec2 p,float a){float c=cos(a),s=sin(a);return mat2(c,-s,s,c)*p;}\nfloat gwpSat(float x){return clamp(x,0.0,1.0);}\nfloat gwpBand(float x,float c,float w){return exp(-pow((x-c)/max(w,0.0001),2.0));}\nfloat gwpLine(float x,float w){return 1.0-smoothstep(w,w*1.8,abs(x));}\nfloat gwpDisk(vec2 p,float r,float soft){return 1.0-smoothstep(r-soft,r,length(p));}\nvoid main(){\nvec2 p=gwPattern(vTextureCoord);float t=uTime*uSpeed*0.8;\nvec2 q=p*8.0;vec2 f=abs(fract(q)-0.5);\nfloat grid=(1.0-smoothstep(0.04,0.08,min(f.x,f.y)))*0.45;\nfloat scan=pow(0.5+0.5*sin((p.y-t)*18.0),12.0);\nfloat glitch=step(0.82,gwpNoise(vec2(floor(p.y*18.0),floor(t*6.0))))*0.22;\nvec2 local=fract(q)-0.5;\nfloat nodes=exp(-dot(local,local)*90.0)*(0.4+0.6*sin(t*4.0));\nfloat a=gwpSat((grid+scan*0.7+glitch+nodes*0.5)*uIntensity*0.72);\nvec3 c=mix(uColor,vec3(0.85,1.0,1.0),scan);\nfinalColor=vec4(c*a,a);\n}",
    "light_response": 0.8,
    "light_emission": 0
  },
  {
    "opacity": 0.62,
    "intensity": 0.8,
    "scale": 1.15,
    "speed": 0.65,
    "rotation": 0,
    "radius": 0,
    "enabled": true,
    "id": "grid-3",
    get "category"() {
      return text("Patterns");
    },
    get "name"() {
      return text("Circuit");
    },
    get "description"() {
      return text("Pseudorandom orthogonal tracks with data pads.");
    },
    "color": "#45e078",
    "blend_mode": "screen",
    "source": "float gwpHash(vec2 p){return fract(sin(dot(p,vec2(127.1,311.7)))*43758.5453123);}\nfloat gwpNoise(vec2 p){vec2 i=floor(p),f=fract(p);f=f*f*(3.0-2.0*f);return mix(mix(gwpHash(i),gwpHash(i+vec2(1.0,0.0)),f.x),mix(gwpHash(i+vec2(0.0,1.0)),gwpHash(i+vec2(1.0)),f.x),f.y);}\nfloat gwpFbm(vec2 p){float v=0.0,a=0.5;for(int i=0;i<5;i++){if(i>=int(mix(1.0,5.0,uQuality)))break;v+=a*gwpNoise(p);p=p*2.03+vec2(13.7,9.2);a*=0.5;}return v;}\nvec2 gwpRot(vec2 p,float a){float c=cos(a),s=sin(a);return mat2(c,-s,s,c)*p;}\nfloat gwpSat(float x){return clamp(x,0.0,1.0);}\nfloat gwpBand(float x,float c,float w){return exp(-pow((x-c)/max(w,0.0001),2.0));}\nfloat gwpLine(float x,float w){return 1.0-smoothstep(w,w*1.8,abs(x));}\nfloat gwpDisk(vec2 p,float r,float soft){return 1.0-smoothstep(r-soft,r,length(p));}\nvoid main(){\nvec2 p=gwPattern(vTextureCoord);float t=uTime*uSpeed*0.2;\nvec2 q=p*10.0;vec2 cell=floor(q);vec2 f=fract(q)-0.5;float h=gwpHash(cell);\nfloat horiz=gwpLine(f.y-(step(0.5,h)-0.5)*0.34,0.035)*step(0.35,h);\nfloat vert=gwpLine(f.x-(step(0.72,h)-0.5)*0.34,0.035)*step(0.52,1.0-h);\nfloat pad=exp(-dot(f,f)*120.0)*step(0.76,h);\nfloat data=0.45+0.55*sin(t*5.0+cell.x*0.7+cell.y*1.3);\nfloat a=gwpSat((horiz*0.55+vert*0.55+pad*data)*uIntensity*0.62);\nfinalColor=vec4(uColor*a,a);\n}",
    "light_response": 0.8,
    "light_emission": 0
  },
  {
    "opacity": 0.82,
    "intensity": 0.8,
    "scale": 1,
    "speed": 1,
    "rotation": 0,
    "radius": 7,
    "enabled": true,
    "id": "grid-4",
    get "category"() {
      return text("Patterns");
    },
    get "name"() {
      return text("Runic Prison");
    },
    get "description"() {
      return text("Concentric rings, radial bars, and pulsing glyphs.");
    },
    "color": "#ed3948",
    "blend_mode": "add",
    "source": "float gwpHash(vec2 p){return fract(sin(dot(p,vec2(127.1,311.7)))*43758.5453123);}\nfloat gwpNoise(vec2 p){vec2 i=floor(p),f=fract(p);f=f*f*(3.0-2.0*f);return mix(mix(gwpHash(i),gwpHash(i+vec2(1.0,0.0)),f.x),mix(gwpHash(i+vec2(0.0,1.0)),gwpHash(i+vec2(1.0)),f.x),f.y);}\nfloat gwpFbm(vec2 p){float v=0.0,a=0.5;for(int i=0;i<5;i++){if(i>=int(mix(1.0,5.0,uQuality)))break;v+=a*gwpNoise(p);p=p*2.03+vec2(13.7,9.2);a*=0.5;}return v;}\nvec2 gwpRot(vec2 p,float a){float c=cos(a),s=sin(a);return mat2(c,-s,s,c)*p;}\nfloat gwpSat(float x){return clamp(x,0.0,1.0);}\nfloat gwpBand(float x,float c,float w){return exp(-pow((x-c)/max(w,0.0001),2.0));}\nfloat gwpLine(float x,float w){return 1.0-smoothstep(w,w*1.8,abs(x));}\nfloat gwpDisk(vec2 p,float r,float soft){return 1.0-smoothstep(r-soft,r,length(p));}\nvoid main(){\nvec2 p=gwPattern(vTextureCoord);float t=uTime*uSpeed*0.5;\nfloat d=length(p);float ang=atan(p.y,p.x);\nfloat rings=gwpBand(d,0.38,0.025)+gwpBand(d,0.68,0.025)+gwpBand(d,0.9,0.018);\nfloat bars=pow(abs(cos(ang*4.0)),24.0)*step(0.32,d)*(1.0-step(0.93,d));\nfloat glyph=pow(max(0.0,cos(ang*8.0+t*0.5)),24.0)*gwpBand(d,0.78,0.055);\nfloat flash=0.65+0.35*sin(t*2.0+d*12.0);\nfloat a=gwpSat((rings+bars*0.55+glyph*0.85)*flash*uIntensity*0.82);\nfinalColor=vec4(uColor*a,a);\n}",
    "light_response": 0.8,
    "light_emission": 0
  },
  {
    "opacity": 0.38,
    "intensity": 0.8,
    "scale": 1.1,
    "speed": 0.45,
    "rotation": 0,
    "radius": 0,
    "enabled": true,
    "id": "grid-5",
    get "category"() {
      return text("Patterns");
    },
    get "name"() {
      return text("Ghost Board");
    },
    get "description"() {
      return text("Alternating spectral squares slowly appearing and disappearing.");
    },
    "color": "#c4d6e8",
    "blend_mode": "normal",
    "source": "float gwpHash(vec2 p){return fract(sin(dot(p,vec2(127.1,311.7)))*43758.5453123);}\nfloat gwpNoise(vec2 p){vec2 i=floor(p),f=fract(p);f=f*f*(3.0-2.0*f);return mix(mix(gwpHash(i),gwpHash(i+vec2(1.0,0.0)),f.x),mix(gwpHash(i+vec2(0.0,1.0)),gwpHash(i+vec2(1.0)),f.x),f.y);}\nfloat gwpFbm(vec2 p){float v=0.0,a=0.5;for(int i=0;i<5;i++){if(i>=int(mix(1.0,5.0,uQuality)))break;v+=a*gwpNoise(p);p=p*2.03+vec2(13.7,9.2);a*=0.5;}return v;}\nvec2 gwpRot(vec2 p,float a){float c=cos(a),s=sin(a);return mat2(c,-s,s,c)*p;}\nfloat gwpSat(float x){return clamp(x,0.0,1.0);}\nfloat gwpBand(float x,float c,float w){return exp(-pow((x-c)/max(w,0.0001),2.0));}\nfloat gwpLine(float x,float w){return 1.0-smoothstep(w,w*1.8,abs(x));}\nfloat gwpDisk(vec2 p,float r,float soft){return 1.0-smoothstep(r-soft,r,length(p));}\nvoid main(){\nvec2 p=gwPattern(vTextureCoord);float t=uTime*uSpeed*0.08;\nvec2 q=floor(p*6.0);\nfloat checker=mod(q.x+q.y,2.0);\nfloat fade=0.28+0.24*sin(t*1.5+q.x*0.7-q.y*0.4);\nvec2 f=abs(fract(p*6.0)-0.5);\nfloat seams=1.0-smoothstep(0.44,0.49,max(f.x,f.y));\nfloat ghost=(checker*0.32+seams*0.18)*fade;\nfloat drift=gwpFbm(p*2.0+vec2(t*0.03))*0.1;\nfloat a=gwpSat((ghost+drift)*uIntensity*0.38);\nfinalColor=vec4(uColor*a,a);\n}",
    "light_response": 0.8,
    "light_emission": 0
  },
  {
    "opacity": 1,
    "intensity": 0.8,
    "scale": 1,
    "speed": 1,
    "rotation": 0,
    "radius": 7,
    "enabled": true,
    "id": "vortex-1",
    get "category"() {
      return text("Vortices");
    },
    get "name"() {
      return text("Whirlpool");
    },
    get "description"() {
      return text("Water spiral with foam and concentric rings.");
    },
    "color": "#3b9fd1",
    "blend_mode": "screen",
    "source": "float gwpHash(vec2 p){return fract(sin(dot(p,vec2(127.1,311.7)))*43758.5453123);}\nfloat gwpNoise(vec2 p){vec2 i=floor(p),f=fract(p);f=f*f*(3.0-2.0*f);return mix(mix(gwpHash(i),gwpHash(i+vec2(1.0,0.0)),f.x),mix(gwpHash(i+vec2(0.0,1.0)),gwpHash(i+vec2(1.0)),f.x),f.y);}\nfloat gwpFbm(vec2 p){float v=0.0,a=0.5;for(int i=0;i<5;i++){if(i>=int(mix(1.0,5.0,uQuality)))break;v+=a*gwpNoise(p);p=p*2.03+vec2(13.7,9.2);a*=0.5;}return v;}\nvec2 gwpRot(vec2 p,float a){float c=cos(a),s=sin(a);return mat2(c,-s,s,c)*p;}\nfloat gwpSat(float x){return clamp(x,0.0,1.0);}\nfloat gwpBand(float x,float c,float w){return exp(-pow((x-c)/max(w,0.0001),2.0));}\nfloat gwpLine(float x,float w){return 1.0-smoothstep(w,w*1.8,abs(x));}\nfloat gwpDisk(vec2 p,float r,float soft){return 1.0-smoothstep(r-soft,r,length(p));}\nvoid main(){\nvec2 p=gwPattern(vTextureCoord);float t=uTime*uSpeed*0.55;\nfloat d=length(p);float ang=atan(p.y,p.x);\nfloat n=gwpFbm(vec2(d*4.0,ang*1.5+t*0.4));\nfloat spiral=pow(0.5+0.5*sin(ang*6.0-d*17.0+t*2.0+n*2.0),3.0);\nfloat basin=smoothstep(0.1,0.22,d)*(1.0-smoothstep(0.72,1.1,d));\nfloat foam=pow(spiral,2.0)*basin;\nfloat rings=(gwpBand(d,0.42,0.025)+gwpBand(d,0.7,0.03))*0.3;\nfloat a=gwpSat((foam+rings)*uIntensity);\nvec3 c=mix(uColor,vec3(0.78,0.96,1.0),foam*0.55);\nfinalColor=vec4(c*a,a);\n}",
    "light_response": 0,
    "light_emission": 0
  },
  {
    "opacity": 0.9,
    "intensity": 0.8,
    "scale": 1,
    "speed": 1,
    "rotation": 0,
    "radius": 7,
    "enabled": true,
    "id": "vortex-2",
    get "category"() {
      return text("Vortices");
    },
    get "name"() {
      return text("Singularity");
    },
    get "description"() {
      return text("Black hole with an accretion disk and gravitational lensing.");
    },
    "color": "#7038c8",
    "blend_mode": "add",
    "source": "float gwpHash(vec2 p){return fract(sin(dot(p,vec2(127.1,311.7)))*43758.5453123);}\nfloat gwpNoise(vec2 p){vec2 i=floor(p),f=fract(p);f=f*f*(3.0-2.0*f);return mix(mix(gwpHash(i),gwpHash(i+vec2(1.0,0.0)),f.x),mix(gwpHash(i+vec2(0.0,1.0)),gwpHash(i+vec2(1.0)),f.x),f.y);}\nfloat gwpFbm(vec2 p){float v=0.0,a=0.5;for(int i=0;i<5;i++){if(i>=int(mix(1.0,5.0,uQuality)))break;v+=a*gwpNoise(p);p=p*2.03+vec2(13.7,9.2);a*=0.5;}return v;}\nvec2 gwpRot(vec2 p,float a){float c=cos(a),s=sin(a);return mat2(c,-s,s,c)*p;}\nfloat gwpSat(float x){return clamp(x,0.0,1.0);}\nfloat gwpBand(float x,float c,float w){return exp(-pow((x-c)/max(w,0.0001),2.0));}\nfloat gwpLine(float x,float w){return 1.0-smoothstep(w,w*1.8,abs(x));}\nfloat gwpDisk(vec2 p,float r,float soft){return 1.0-smoothstep(r-soft,r,length(p));}\nvoid main(){\nvec2 p=gwPattern(vTextureCoord);float t=uTime*uSpeed*0.4;\nfloat d=length(p);float ang=atan(p.y,p.x);\nfloat hole=1.0-smoothstep(0.17,0.33,d);\nfloat disk=gwpBand(d,0.53,0.16)*(0.5+0.5*sin(ang*9.0-d*27.0+t*1.4));\nfloat lens=gwpBand(d,0.36,0.025)+gwpBand(d,0.78,0.018)*0.45;\nfloat sparks=pow(gwpNoise(vec2(ang*8.0,d*15.0+t)),18.0)*gwpBand(d,0.62,0.22);\nfloat e=(disk*1.2+lens+sparks*0.65)*(1.0-hole)*uIntensity;\nfloat a=gwpSat(e);\nvec3 c=mix(uColor,vec3(1.0),lens+sparks*0.5);\nfinalColor=vec4(c*a,a);\n}",
    "light_response": 0,
    "light_emission": 0
  },
  {
    "opacity": 0.82,
    "intensity": 0.8,
    "scale": 1,
    "speed": 1,
    "rotation": 0,
    "radius": 8,
    "enabled": true,
    "id": "vortex-3",
    get "category"() {
      return text("Vortices");
    },
    get "name"() {
      return text("Sand Cyclone");
    },
    get "description"() {
      return text("Tapered sand column with turbulent bands and grains.");
    },
    "color": "#b79058",
    "blend_mode": "multiply",
    "source": "float gwpHash(vec2 p){return fract(sin(dot(p,vec2(127.1,311.7)))*43758.5453123);}\nfloat gwpNoise(vec2 p){vec2 i=floor(p),f=fract(p);f=f*f*(3.0-2.0*f);return mix(mix(gwpHash(i),gwpHash(i+vec2(1.0,0.0)),f.x),mix(gwpHash(i+vec2(0.0,1.0)),gwpHash(i+vec2(1.0)),f.x),f.y);}\nfloat gwpFbm(vec2 p){float v=0.0,a=0.5;for(int i=0;i<5;i++){if(i>=int(mix(1.0,5.0,uQuality)))break;v+=a*gwpNoise(p);p=p*2.03+vec2(13.7,9.2);a*=0.5;}return v;}\nvec2 gwpRot(vec2 p,float a){float c=cos(a),s=sin(a);return mat2(c,-s,s,c)*p;}\nfloat gwpSat(float x){return clamp(x,0.0,1.0);}\nfloat gwpBand(float x,float c,float w){return exp(-pow((x-c)/max(w,0.0001),2.0));}\nfloat gwpLine(float x,float w){return 1.0-smoothstep(w,w*1.8,abs(x));}\nfloat gwpDisk(vec2 p,float r,float soft){return 1.0-smoothstep(r-soft,r,length(p));}\nvoid main(){\nvec2 p=gwPattern(vTextureCoord);float t=uTime*uSpeed*0.7;\nfloat y=p.y;\nfloat taper=0.24+0.52*(1.0-gwpSat((y+1.0)*0.5));\nfloat ang=atan(p.y,p.x);\nfloat bands=pow(0.5+0.5*sin(ang*11.0-length(p)*18.0+t*2.5+gwpFbm(p*5.0)*4.0),2.0);\nfloat column=1.0-smoothstep(taper,taper+0.22,abs(p.x));\nfloat grains=pow(gwpNoise(p*18.0+vec2(t*0.3,-t)),12.0)*column;\nfloat a=gwpSat((bands*column*0.52+grains*0.35)*uIntensity*0.85);\nfinalColor=vec4(uColor*a,a);\n}",
    "light_response": 0,
    "light_emission": 0
  },
  {
    "opacity": 1,
    "intensity": 0.9,
    "scale": 1,
    "speed": 1,
    "rotation": 0,
    "radius": 7,
    "enabled": true,
    "id": "vortex-4",
    get "category"() {
      return text("Vortices");
    },
    get "name"() {
      return text("Green Tempest");
    },
    get "description"() {
      return text("Poisonous vortex with thick arms and internal eddies.");
    },
    "color": "#4fc96b",
    "blend_mode": "screen",
    "source": "float gwpHash(vec2 p){return fract(sin(dot(p,vec2(127.1,311.7)))*43758.5453123);}\nfloat gwpNoise(vec2 p){vec2 i=floor(p),f=fract(p);f=f*f*(3.0-2.0*f);return mix(mix(gwpHash(i),gwpHash(i+vec2(1.0,0.0)),f.x),mix(gwpHash(i+vec2(0.0,1.0)),gwpHash(i+vec2(1.0)),f.x),f.y);}\nfloat gwpFbm(vec2 p){float v=0.0,a=0.5;for(int i=0;i<5;i++){if(i>=int(mix(1.0,5.0,uQuality)))break;v+=a*gwpNoise(p);p=p*2.03+vec2(13.7,9.2);a*=0.5;}return v;}\nvec2 gwpRot(vec2 p,float a){float c=cos(a),s=sin(a);return mat2(c,-s,s,c)*p;}\nfloat gwpSat(float x){return clamp(x,0.0,1.0);}\nfloat gwpBand(float x,float c,float w){return exp(-pow((x-c)/max(w,0.0001),2.0));}\nfloat gwpLine(float x,float w){return 1.0-smoothstep(w,w*1.8,abs(x));}\nfloat gwpDisk(vec2 p,float r,float soft){return 1.0-smoothstep(r-soft,r,length(p));}\nvoid main(){\nvec2 p=gwPattern(vTextureCoord);float t=uTime*uSpeed*0.9;\nfloat d=length(p);float ang=atan(p.y,p.x);\nfloat n=gwpFbm(gwpRot(p,t*0.1)*6.0);\nfloat arms=pow(0.5+0.5*sin(ang*7.0-d*30.0+t*3.2+n*5.0),2.5);\nfloat eddies=pow(gwpFbm(p*10.0+vec2(t*0.12)),2.0);\nfloat body=smoothstep(0.1,0.2,d)*(1.0-smoothstep(0.72,1.2,d));\nfloat a=gwpSat((arms*0.72+eddies*0.32)*body*uIntensity*0.9);\nvec3 c=mix(uColor,vec3(0.7,1.0,0.38),eddies*0.25);\nfinalColor=vec4(c*a,a);\n}",
    "light_response": 0,
    "light_emission": 0
  },
  {
    "opacity": 1,
    "intensity": 0.8,
    "scale": 1,
    "speed": 0.55,
    "rotation": 0,
    "radius": 8,
    "enabled": true,
    "id": "vortex-5",
    get "category"() {
      return text("Vortices");
    },
    get "name"() {
      return text("Galaxy");
    },
    get "description"() {
      return text("Spiral galaxy with arms, a central bulge, stars, and dust.");
    },
    "color": "#826cff",
    "blend_mode": "add",
    "source": "float gwpHash(vec2 p){return fract(sin(dot(p,vec2(127.1,311.7)))*43758.5453123);}\nfloat gwpNoise(vec2 p){vec2 i=floor(p),f=fract(p);f=f*f*(3.0-2.0*f);return mix(mix(gwpHash(i),gwpHash(i+vec2(1.0,0.0)),f.x),mix(gwpHash(i+vec2(0.0,1.0)),gwpHash(i+vec2(1.0)),f.x),f.y);}\nfloat gwpFbm(vec2 p){float v=0.0,a=0.5;for(int i=0;i<5;i++){if(i>=int(mix(1.0,5.0,uQuality)))break;v+=a*gwpNoise(p);p=p*2.03+vec2(13.7,9.2);a*=0.5;}return v;}\nvec2 gwpRot(vec2 p,float a){float c=cos(a),s=sin(a);return mat2(c,-s,s,c)*p;}\nfloat gwpSat(float x){return clamp(x,0.0,1.0);}\nfloat gwpBand(float x,float c,float w){return exp(-pow((x-c)/max(w,0.0001),2.0));}\nfloat gwpLine(float x,float w){return 1.0-smoothstep(w,w*1.8,abs(x));}\nfloat gwpDisk(vec2 p,float r,float soft){return 1.0-smoothstep(r-soft,r,length(p));}\nvoid main(){\nvec2 p=gwPattern(vTextureCoord);float t=uTime*uSpeed*0.12;\nfloat d=length(p);float ang=atan(p.y,p.x);\nfloat arm=pow(0.5+0.5*cos(ang*4.0-d*12.0+t*0.7),7.0)*exp(-d*1.5);\nfloat dust=gwpFbm(vec2(ang*2.0-d*3.0,d*8.0+t*0.15))*arm;\nvec2 q=p*18.0;vec2 cell=floor(q);vec2 f=fract(q)-0.5;float h=gwpHash(cell);\nfloat stars=exp(-dot(f,f)*180.0)*step(0.74,h)*gwpDisk(p,1.05,0.12);\nfloat bulge=exp(-d*d*10.0);\nfloat a=gwpSat((arm*0.75+dust*0.42+stars+bulge*0.65)*uIntensity);\nvec3 c=mix(uColor,vec3(1.0,0.92,0.76),bulge+stars*0.5);\nfinalColor=vec4(c*a,a);\n}",
    "light_response": 0,
    "light_emission": 0
  },
  {
    "opacity": 1,
    "intensity": 0.8,
    "scale": 1,
    "speed": 0.7,
    "rotation": 0,
    "radius": 5,
    "enabled": true,
    "id": "aura-1",
    "category": "Auras",
    get "name"() {
      return text("Sacred Aura");
    },
    get "description"() {
      return text("Golden halo with outer rays and rising motes.");
    },
    "color": "#ffd86a",
    "blend_mode": "screen",
    "source": "float gwpHash(vec2 p){return fract(sin(dot(p,vec2(127.1,311.7)))*43758.5453123);}\nfloat gwpNoise(vec2 p){vec2 i=floor(p),f=fract(p);f=f*f*(3.0-2.0*f);return mix(mix(gwpHash(i),gwpHash(i+vec2(1.0,0.0)),f.x),mix(gwpHash(i+vec2(0.0,1.0)),gwpHash(i+vec2(1.0)),f.x),f.y);}\nfloat gwpFbm(vec2 p){float v=0.0,a=0.5;for(int i=0;i<5;i++){if(i>=int(mix(1.0,5.0,uQuality)))break;v+=a*gwpNoise(p);p=p*2.03+vec2(13.7,9.2);a*=0.5;}return v;}\nvec2 gwpRot(vec2 p,float a){float c=cos(a),s=sin(a);return mat2(c,-s,s,c)*p;}\nfloat gwpSat(float x){return clamp(x,0.0,1.0);}\nfloat gwpBand(float x,float c,float w){return exp(-pow((x-c)/max(w,0.0001),2.0));}\nfloat gwpLine(float x,float w){return 1.0-smoothstep(w,w*1.8,abs(x));}\nfloat gwpDisk(vec2 p,float r,float soft){return 1.0-smoothstep(r-soft,r,length(p));}\nvoid main(){\nvec2 p=gwPattern(vTextureCoord);float t=uTime*uSpeed*0.35;\nfloat d=length(p);float ang=atan(p.y,p.x);\nfloat halo=gwpBand(d,0.72+0.025*sin(t*2.0),0.055);\nfloat rays=pow(max(0.0,cos(ang*6.0+t*0.3)),18.0)*gwpBand(d,0.78,0.24);\nfloat inner=exp(-d*d*3.2)*0.18;\nfloat motes=pow(gwpNoise(p*16.0-vec2(0.0,t*0.3)),20.0)*gwpBand(d,0.6,0.38);\nfloat a=gwpSat((halo+rays*0.5+inner+motes*0.3)*uIntensity*0.78);\nvec3 c=mix(uColor,vec3(1.0,1.0,0.86),halo+rays*0.4);\nfinalColor=vec4(c*a,a);\n}",
    "light_response": 0,
    "light_emission": 0
  },
  {
    "opacity": 0.82,
    "intensity": 0.8,
    "scale": 1,
    "speed": 1,
    "rotation": 0,
    "radius": 5,
    "enabled": true,
    "id": "aura-2",
    "category": "Auras",
    get "name"() {
      return text("Dark Aura");
    },
    get "description"() {
      return text("Smoky outline with inward-facing purple-black tendrils.");
    },
    "color": "#5b337e",
    "blend_mode": "multiply",
    "source": "float gwpHash(vec2 p){return fract(sin(dot(p,vec2(127.1,311.7)))*43758.5453123);}\nfloat gwpNoise(vec2 p){vec2 i=floor(p),f=fract(p);f=f*f*(3.0-2.0*f);return mix(mix(gwpHash(i),gwpHash(i+vec2(1.0,0.0)),f.x),mix(gwpHash(i+vec2(0.0,1.0)),gwpHash(i+vec2(1.0)),f.x),f.y);}\nfloat gwpFbm(vec2 p){float v=0.0,a=0.5;for(int i=0;i<5;i++){if(i>=int(mix(1.0,5.0,uQuality)))break;v+=a*gwpNoise(p);p=p*2.03+vec2(13.7,9.2);a*=0.5;}return v;}\nvec2 gwpRot(vec2 p,float a){float c=cos(a),s=sin(a);return mat2(c,-s,s,c)*p;}\nfloat gwpSat(float x){return clamp(x,0.0,1.0);}\nfloat gwpBand(float x,float c,float w){return exp(-pow((x-c)/max(w,0.0001),2.0));}\nfloat gwpLine(float x,float w){return 1.0-smoothstep(w,w*1.8,abs(x));}\nfloat gwpDisk(vec2 p,float r,float soft){return 1.0-smoothstep(r-soft,r,length(p));}\nvoid main(){\nvec2 p=gwPattern(vTextureCoord);float t=uTime*uSpeed*0.5;\nfloat d=length(p);float ang=atan(p.y,p.x);\nfloat wob=(gwpFbm(vec2(ang*5.0,t*0.4))-0.5)*0.15;\nfloat rim=gwpBand(d,0.68+wob,0.09);\nfloat tendrils=pow(max(0.0,sin(ang*9.0+d*17.0-t*2.0+gwpFbm(p*6.0)*4.0)),5.0)*gwpBand(d,0.55,0.32);\nfloat inner=exp(-d*d*2.0)*0.36;\nfloat a=gwpSat((rim*0.8+tendrils*0.5+inner)*uIntensity*0.82);\nvec3 c=mix(uColor*0.48,uColor,rim);\nfinalColor=vec4(c*a,a);\n}",
    "light_response": 0,
    "light_emission": 0
  },
  {
    "opacity": 1,
    "intensity": 0.8,
    "scale": 1,
    "speed": 0.65,
    "rotation": 0,
    "radius": 5,
    "enabled": true,
    "id": "aura-3",
    "category": "Auras",
    get "name"() {
      return text("Arcane Shield");
    },
    get "description"() {
      return text("Precise hexagonal barrier with scanlines, nodes, and inner rings.");
    },
    "color": "#438cff",
    "blend_mode": "add",
    "source": "float gwpHash(vec2 p){return fract(sin(dot(p,vec2(127.1,311.7)))*43758.5453123);}\nfloat gwpNoise(vec2 p){vec2 i=floor(p),f=fract(p);f=f*f*(3.0-2.0*f);return mix(mix(gwpHash(i),gwpHash(i+vec2(1.0,0.0)),f.x),mix(gwpHash(i+vec2(0.0,1.0)),gwpHash(i+vec2(1.0)),f.x),f.y);}\nfloat gwpFbm(vec2 p){float v=0.0,a=0.5;for(int i=0;i<5;i++){if(i>=int(mix(1.0,5.0,uQuality)))break;v+=a*gwpNoise(p);p=p*2.03+vec2(13.7,9.2);a*=0.5;}return v;}\nvec2 gwpRot(vec2 p,float a){float c=cos(a),s=sin(a);return mat2(c,-s,s,c)*p;}\nfloat gwpSat(float x){return clamp(x,0.0,1.0);}\nfloat gwpBand(float x,float c,float w){return exp(-pow((x-c)/max(w,0.0001),2.0));}\nfloat gwpLine(float x,float w){return 1.0-smoothstep(w,w*1.8,abs(x));}\nfloat gwpDisk(vec2 p,float r,float soft){return 1.0-smoothstep(r-soft,r,length(p));}\nvoid main(){\nvec2 p=gwPattern(vTextureCoord);float t=uTime*uSpeed*0.22;\nfloat d=length(p);float ang=atan(p.y,p.x);\nfloat hexR=0.77/max(abs(cos(mod(ang+0.523599,1.047198)-0.523599)),0.5);\nfloat shell=gwpBand(d,hexR,0.028);\nfloat rings=gwpBand(d,0.58,0.018)*0.45;\nfloat scan=gwpBand(p.y,0.62*sin(t*2.0),0.025)*gwpDisk(p,0.82,0.08);\nfloat nodes=pow(max(0.0,cos(ang*6.0)),28.0)*gwpBand(d,0.77,0.07);\nfloat a=gwpSat((shell+rings+scan*0.55+nodes*0.7)*uIntensity*0.72);\nvec3 c=mix(uColor,vec3(0.9,0.98,1.0),shell+nodes);\nfinalColor=vec4(c*a,a);\n}",
    "light_response": 0,
    "light_emission": 0
  },
  {
    "opacity": 0.68,
    "intensity": 0.8,
    "scale": 1.1,
    "speed": 0.9,
    "rotation": 0,
    "radius": 5,
    "enabled": true,
    "id": "aura-4",
    "category": "Auras",
    get "name"() {
      return text("Poison");
    },
    get "description"() {
      return text("Pulsing toxic cloud with distinct bubbles around its origin.");
    },
    "color": "#6fbf37",
    "blend_mode": "normal",
    "source": "float gwpHash(vec2 p){return fract(sin(dot(p,vec2(127.1,311.7)))*43758.5453123);}\nfloat gwpNoise(vec2 p){vec2 i=floor(p),f=fract(p);f=f*f*(3.0-2.0*f);return mix(mix(gwpHash(i),gwpHash(i+vec2(1.0,0.0)),f.x),mix(gwpHash(i+vec2(0.0,1.0)),gwpHash(i+vec2(1.0)),f.x),f.y);}\nfloat gwpFbm(vec2 p){float v=0.0,a=0.5;for(int i=0;i<5;i++){if(i>=int(mix(1.0,5.0,uQuality)))break;v+=a*gwpNoise(p);p=p*2.03+vec2(13.7,9.2);a*=0.5;}return v;}\nvec2 gwpRot(vec2 p,float a){float c=cos(a),s=sin(a);return mat2(c,-s,s,c)*p;}\nfloat gwpSat(float x){return clamp(x,0.0,1.0);}\nfloat gwpBand(float x,float c,float w){return exp(-pow((x-c)/max(w,0.0001),2.0));}\nfloat gwpLine(float x,float w){return 1.0-smoothstep(w,w*1.8,abs(x));}\nfloat gwpDisk(vec2 p,float r,float soft){return 1.0-smoothstep(r-soft,r,length(p));}\nvoid main(){\nvec2 p=gwPattern(vTextureCoord);float t=uTime*uSpeed*0.65;\nfloat d=length(p);\nfloat cloud=smoothstep(0.4,0.72,gwpFbm(p*5.0+vec2(t*0.18,-t*0.08)))*\n            (1.0-smoothstep(0.58,0.92,d));\nvec2 q=p*7.0;vec2 cell=floor(q);vec2 f=fract(q)-0.5;float h=gwpHash(cell);\nfloat bubble=gwpBand(length(f),0.18+0.15*h,0.05)*step(0.45,h);\nfloat pulse=0.72+0.28*sin(t*2.5+d*7.0);\nfloat a=gwpSat((cloud*0.75+bubble*0.48)*pulse*uIntensity*0.7);\nvec3 c=mix(uColor,vec3(0.82,1.0,0.28),bubble*0.4);\nfinalColor=vec4(c*a,a);\n}",
    "light_response": 0,
    "light_emission": 0
  },
  {
    "opacity": 1,
    "intensity": 0.9,
    "scale": 1,
    "speed": 1,
    "rotation": 0,
    "radius": 5,
    "enabled": true,
    "id": "aura-5",
    "category": "Auras",
    get "name"() {
      return text("Blood Aura");
    },
    get "description"() {
      return text("Crimson halo with radial spikes, drops, and an aggressive pulse.");
    },
    "color": "#d9263c",
    "blend_mode": "screen",
    "source": "float gwpHash(vec2 p){return fract(sin(dot(p,vec2(127.1,311.7)))*43758.5453123);}\nfloat gwpNoise(vec2 p){vec2 i=floor(p),f=fract(p);f=f*f*(3.0-2.0*f);return mix(mix(gwpHash(i),gwpHash(i+vec2(1.0,0.0)),f.x),mix(gwpHash(i+vec2(0.0,1.0)),gwpHash(i+vec2(1.0)),f.x),f.y);}\nfloat gwpFbm(vec2 p){float v=0.0,a=0.5;for(int i=0;i<5;i++){if(i>=int(mix(1.0,5.0,uQuality)))break;v+=a*gwpNoise(p);p=p*2.03+vec2(13.7,9.2);a*=0.5;}return v;}\nvec2 gwpRot(vec2 p,float a){float c=cos(a),s=sin(a);return mat2(c,-s,s,c)*p;}\nfloat gwpSat(float x){return clamp(x,0.0,1.0);}\nfloat gwpBand(float x,float c,float w){return exp(-pow((x-c)/max(w,0.0001),2.0));}\nfloat gwpLine(float x,float w){return 1.0-smoothstep(w,w*1.8,abs(x));}\nfloat gwpDisk(vec2 p,float r,float soft){return 1.0-smoothstep(r-soft,r,length(p));}\nvoid main(){\nvec2 p=gwPattern(vTextureCoord);float t=uTime*uSpeed*0.75;\nfloat d=length(p);float ang=atan(p.y,p.x);\nfloat pulse=0.68+0.12*sin(t*5.0);\nfloat rim=gwpBand(d,0.69+pulse*0.04,0.055);\nfloat spikes=pow(max(0.0,cos(ang*11.0+t*0.8)),10.0)*gwpBand(d,0.75,0.22);\nfloat drops=pow(gwpNoise(vec2(ang*8.0,t*0.2+d*5.0)),14.0)*gwpBand(d,0.62,0.3);\nfloat inner=exp(-d*d*4.0)*0.2;\nfloat a=gwpSat((rim*0.9+spikes*0.55+drops*0.4+inner)*uIntensity*0.8);\nvec3 c=mix(uColor,vec3(0.85,0.05,0.08),drops+spikes*0.25);\nfinalColor=vec4(c*a,a);\n}",
    "light_response": 0,
    "light_emission": 0
  }
];

// gravewright/maps/frontend/features/effects/model/effects.js
function defaults() {
  return { light_response: 0, light_emission: 0, bright_radius: 2, dim_radius: 4, angle: 360, animation: "none", x: 0, y: 0, kind: "smoke", scale: 3, density: 0.6, color: "#9aa3ad", enabled: true, rotation: 0, name: "Shader", source: "void main() { float a = 0.35 * uIntensity; finalColor = vec4(uColor * a, a); }", radius: 0, opacity: 1, intensity: 0.6, speed: 1, blend_mode: "normal" };
}
function effects(state, layer = "effects") {
  if (layer === "lighting")
    return state.lights.map((data) => ({ ...data, kind: "light", key: `light:${data.id}`, data: { ...defaults(), ...data, enabled: Boolean(data.enabled) } }));
  return [...state.particles.map((data) => ({ ...data, kind: "particle", data: { ...defaults(), ...data, enabled: Boolean(data.enabled) } })), ...state.shaders.map((data) => ({ ...data, kind: "shader", data: { ...defaults(), ...data, enabled: Boolean(data.enabled) } }))].map((e) => ({ ...e, key: `${e.kind}:${e.id}` }));
}
function hitEffect(items, point, scale) {
  return [...items].reverse().find((e) => Math.hypot(e.x - point.x, e.y - point.y) <= 13 / scale);
}
function inMarquee(items, from, to) {
  return items.filter((e) => e.x >= Math.min(from.x, to.x) && e.x <= Math.max(from.x, to.x) && e.y >= Math.min(from.y, to.y) && e.y <= Math.max(from.y, to.y)).map((e) => e.key);
}
function payload(kind, data) {
  const keys = kind === "light" ? "x y bright_radius dim_radius angle rotation animation intensity color enabled" : kind === "particle" ? "x y kind scale density color enabled rotation light_response light_emission" : "name source x y radius scale intensity opacity speed color rotation blend_mode enabled light_response light_emission";
  return Object.fromEntries(keys.split(" ").map((key) => [key, data[key]]));
}
function translatedCopies(items, at) {
  const center = { x: items.reduce((n, e) => n + e.x, 0) / items.length, y: items.reduce((n, e) => n + e.y, 0) / items.length };
  return items.map((e) => ({ kind: e.kind, data: payload(e.kind, { ...e.data, x: at.x + e.x - center.x, y: at.y + e.y - center.y }) }));
}

// gravewright/maps/frontend/features/scene-layers/ui/sources.js
var box = (value) => ({ value });
var derive = (read) => ({ get value() {
  return read();
} });
function sourceController(element, options) {
  const props = { ...options.props }, emit = options.emit;
  const api = { state: () => options.read() }, writer = { command: (_a, _b, area2, action2, data) => options.command(area2, action2, data) };
  const lights = props.layer === "lighting";
  const batchArea = lights ? "light-selection" : "effects";
  const lightChoice = box("torch");
  const noun = lights ? text("lights") : text("effects");
  const area = (kind) => kind === "light" ? "lights" : kind === "particle" ? "particles" : "shaders";
  const identityKey = (kind) => kind === "light" ? "light_id" : kind === "particle" ? "emitter_id" : "shader_id";
  const rowKey = (kind) => kind === "light" ? "light" : kind === "particle" ? "emitter" : "shader";
  const root = box();
  const items = derive(() => effects(props.state, props.layer));
  const selection = box([]), clipboard = box([]);
  const selected = derive(() => items.value.filter((e) => selection.value.includes(e.key)));
  const context = box();
  const picker = box(), particleChoice = box("smoke"), shaderChoice = box("orb-1");
  const editor = box(), editing = box();
  const draft = box(defaults()), error = box(""), busy = box(false), clearConfirm = box(false);
  const delta = box({ x: 0, y: 0 });
  const marquee = box();
  let gesture;
  let editorVisit = 0, previewFrame = 0;
  let pendingDelta = { x: 0, y: 0 };
  let lastPoint = { x: 0, y: 0 }, closed = false, queue = Promise.resolve();
  let saveTimer;
  let shaderTimer;
  const validator = new ShaderDraftValidator();
  const abort = new AbortController();
  const containerId = props.containerId, blockId = props.blockId;
  function point(event) {
    const r = root.value.getBoundingClientRect();
    return { x: (event.clientX - r.left - props.viewport.x) / props.viewport.scale, y: (event.clientY - r.top - props.viewport.y) / props.viewport.scale };
  }
  function center() {
    const r = root.value?.getBoundingClientRect();
    return { x: ((r?.width ?? 0) / 2 - props.viewport.x) / props.viewport.scale, y: ((r?.height ?? 0) / 2 - props.viewport.y) / props.viewport.scale };
  }
  function refs(list = selected.value) {
    return list.map((e) => ({ id: e.id, kind: e.kind }));
  }
  function run(area2, action2, data, after) {
    const operation = async () => {
      if (closed)
        return;
      busy.value = true;
      error.value = "";
      options.repaint();
      try {
        const result = await writer.command(containerId, blockId, area2, action2, data);
        if (closed)
          return;
        after?.(result);
        const state = await api.state(containerId, blockId);
        if (!closed) {
          emit("changed", state);
          if (area2 === batchArea && action2 === "transform" && editing.value) {
            const row = effects(state, props.layer).find((e) => e.id === editing.value);
            if (row)
              draft.value = { ...draft.value, x: row.x, y: row.y, rotation: row.data.rotation };
          }
        }
      } catch (reason) {
        if (!closed)
          error.value = text("Could not save the change. Check the data and try again.");
      } finally {
        if (!closed) {
          busy.value = false;
          emit("preview", void 0);
          options.repaint();
        }
      }
    };
    queue = queue.then(operation);
    return queue;
  }
  function open(kind, effect) {
    closePicker();
    flush();
    if (shaderTimer)
      clearTimeout(shaderTimer);
    emit("preview", void 0);
    ++editorVisit;
    context.value = void 0;
    editor.value = kind;
    editing.value = effect.id;
    draft.value = { ...effect.data };
    if (kind === "shader") {
      const match = /^gravewright-preset:\/\/([^/]+)\/v1$/.exec(draft.value.source);
      if (match)
        draft.value.source = shaderPresets.find((p) => p.id === match[1])?.source ?? draft.value.source;
    }
  }
  function closePicker() {
    picker.value = void 0;
    emit("preview", void 0);
  }
  function action(id) {
    const previous = picker.value;
    closePicker();
    closeEditor();
    if (id === "clear-effects" || id === "clear-lights") {
      clearConfirm.value = true;
      return;
    }
    if ((id === "particle" || id === "shader" || id === "light") && previous !== id)
      picker.value = id;
  }
  function choose(id) {
    if (picker.value === "light")
      lightChoice.value = id;
    else if (picker.value === "particle")
      particleChoice.value = id;
    else
      shaderChoice.value = id;
    closePicker();
  }
  function shaderData(id) {
    const preset = shaderPresets.find((p) => p.id === id);
    return { ...defaults(), scale: 1, color: "#8fb6ff", ...preset };
  }
  function save(at) {
    if (!editor.value)
      return;
    if (saveTimer)
      clearTimeout(saveTimer);
    saveTimer = void 0;
    const kind = editor.value;
    if (kind === "shader") {
      error.value = validator.validate(draft.value.source);
      if (error.value)
        return;
    }
    const data = payload(kind, { ...draft.value, ...at });
    const identity = editing.value, visit = editorVisit;
    void run(area(kind), identity ? "update" : "create", identity ? { ...data, [identityKey(kind)]: identity } : data, (result) => {
      const row = result[rowKey(kind)];
      if (row && editor.value === kind && visit === editorVisit) {
        editing.value = row.id;
        selection.value = [`${kind}:${row.id}`];
      }
    });
  }
  function previewShader() {
    if (closed || editor.value !== "shader")
      return;
    error.value = validator.validate(draft.value.source);
    if (error.value)
      return;
    const shader = { ...draft.value, id: editing.value ?? "draft-shader" };
    emit("preview", { ...props.state, shaders: [...props.state.shaders.filter((s) => s.id !== shader.id), shader] });
  }
  function changed() {
    if (editor.value === "light" && draft.value.dim_radius > 0)
      draft.value.dim_radius = Math.max(draft.value.dim_radius, draft.value.bright_radius);
    if (editor.value === "shader") {
      if (shaderTimer)
        clearTimeout(shaderTimer);
      shaderTimer = setTimeout(previewShader, 250);
      return;
    }
    if (editor.value === "light" && editing.value) {
      emit("preview", { ...props.state, lights: props.state.lights.map((light) => light.id === editing.value ? { ...light, ...draft.value } : light) });
      if (!saveTimer) saveTimer = setTimeout(() => save(), 100);
      return;
    }
    if (editor.value && editing.value) {
      if (saveTimer)
        clearTimeout(saveTimer);
      saveTimer = setTimeout(() => save(), 250);
    }
  }
  function flush() {
    if (saveTimer) {
      clearTimeout(saveTimer);
      saveTimer = void 0;
      save();
    }
  }
  function closeEditor() {
    flush();
    if (shaderTimer)
      clearTimeout(shaderTimer);
    emit("preview", void 0);
    validator.dispose();
    ++editorVisit;
    editor.value = void 0;
    editing.value = void 0;
  }
  function createAt(at) {
    const kind = props.tool;
    const data = kind === "light" ? { ...defaults(), ...lightPresets.find((p) => p.id === lightChoice.value), animation: lightChoice.value, ...at } : kind === "particle" ? { ...defaults(), ...PARTICLE_DEFAULTS[particleChoice.value], light_response: ["smoke", "dust", "rain", "snow", "leaves", "bubbles", "ash", "blood"].includes(particleChoice.value) ? 0.8 : 0, light_emission: ["ember", "firefly", "arcane", "runes"].includes(particleChoice.value) ? 0.15 : 0, kind: particleChoice.value, ...at } : { ...shaderData(shaderChoice.value), ...at };
    closePicker();
    void run(area(kind), "create", payload(kind, data), (result) => {
      const row = result[rowKey(kind)];
      if (row)
        selection.value = [`${kind}:${row.id}`];
    });
  }
  function down(event) {
    if (!["select", "light", "particle", "shader"].includes(props.tool))
      return;
    if (event.button === 1)
      return;
    if (event.button === 2 && !hitEffect(items.value, point(event), props.viewport.scale))
      return;
    event.stopPropagation();
    event.preventDefault();
    context.value = void 0;
    closePicker();
    if (event.button !== 0 || busy.value)
      return;
    const from = point(event);
    lastPoint = from;
    const hit = hitEffect(items.value, from, props.viewport.scale);
    if (hit) {
      if (event.shiftKey)
        selection.value = selection.value.includes(hit.key) ? selection.value.filter((k) => k !== hit.key) : [...selection.value, hit.key];
      else if (!selection.value.includes(hit.key))
        selection.value = [hit.key];
    }
    const original = [...selection.value];
    if (!hit && !event.shiftKey && props.tool === "select")
      selection.value = [];
    gesture = { pointer: event.pointerId, from, to: from, hit, original, additive: event.shiftKey };
    root.value?.setPointerCapture(event.pointerId);
  }
  function paintPreview(dx, dy) {
    const move2 = (kind, data) => selection.value.includes(`${kind}:${data.id}`) ? { ...data, x: data.x + dx, y: data.y + dy } : data;
    emit("preview", { ...props.state, particles: props.state.particles.map((p) => move2("particle", p)), shaders: props.state.shaders.map((p) => move2("shader", p)), lights: props.state.lights.map((p) => move2("light", p)) });
  }
  function previewMove(dx, dy) {
    pendingDelta = { x: dx, y: dy };
    if (!previewFrame)
      previewFrame = requestAnimationFrame(() => {
        previewFrame = 0;
        if (!closed)
          paintPreview(pendingDelta.x, pendingDelta.y);
      });
  }
  function move(event) {
    lastPoint = point(event);
    if (!gesture || gesture.pointer !== event.pointerId)
      return;
    event.stopPropagation();
    gesture.to = lastPoint;
    if (gesture.hit) {
      delta.value = { x: lastPoint.x - gesture.from.x, y: lastPoint.y - gesture.from.y };
      previewMove(delta.value.x, delta.value.y);
    } else if (props.tool === "select") {
      marquee.value = { from: gesture.from, to: lastPoint };
      selection.value = [.../* @__PURE__ */ new Set([...gesture.additive ? gesture.original : [], ...inMarquee(items.value, gesture.from, lastPoint)])];
    }
  }
  function up(event) {
    if (!gesture || gesture.pointer !== event.pointerId)
      return;
    event.stopPropagation();
    const g = gesture;
    gesture = void 0;
    marquee.value = void 0;
    cancelAnimationFrame(previewFrame);
    previewFrame = 0;
    if (event.type === "pointercancel") {
      selection.value = g.original;
      delta.value = { x: 0, y: 0 };
      emit("preview", void 0);
      return;
    }
    const to = point(event);
    const moved = Math.hypot(to.x - g.from.x, to.y - g.from.y) * props.viewport.scale > 3;
    if (g.hit && moved) {
      delta.value = { x: to.x - g.from.x, y: to.y - g.from.y };
      paintPreview(delta.value.x, delta.value.y);
      void run(batchArea, "transform", { effects: refs(), dx: delta.value.x, dy: delta.value.y }).finally(() => {
        delta.value = { x: 0, y: 0 };
      });
    } else if (g.hit && !moved && !g.additive)
      selection.value = [g.hit.key];
    else if (!g.hit && (props.tool === "particle" || props.tool === "shader" || props.tool === "light"))
      createAt(to);
    else
      emit("preview", void 0);
    if (!g.hit || !moved)
      delta.value = { x: 0, y: 0 };
  }
  function doubleClick(event) {
    const hit = hitEffect(items.value, point(event), props.viewport.scale);
    if (hit) {
      event.stopPropagation();
      selection.value = [hit.key];
      emit("tool", "select");
      open(hit.kind, hit);
    }
  }
  function menu(event) {
    const world = point(event), hit = hitEffect(items.value, world, props.viewport.scale);
    if (!hit)
      return;
    event.preventDefault();
    event.stopPropagation();
    if (hit && !selection.value.includes(hit.key))
      selection.value = [hit.key];
    context.value = { x: event.clientX, y: event.clientY, world };
  }
  function copy() {
    clipboard.value = selected.value.map((e) => ({ ...e, data: structuredClone({ ...e.data }) }));
    context.value = void 0;
  }
  function paste() {
    if (!clipboard.value.length)
      return;
    const at = context.value?.world ?? lastPoint;
    context.value = void 0;
    void run(batchArea, "paste", { effects: translatedCopies(clipboard.value, at) }, (r) => {
      selection.value = r.effects.map((e) => `${e.kind}:${e.id}`);
    });
  }
  function discardPending() {
    if (saveTimer)
      clearTimeout(saveTimer);
    saveTimer = void 0;
    if (shaderTimer)
      clearTimeout(shaderTimer);
    shaderTimer = void 0;
    ++editorVisit;
  }
  function remove(list = selected.value) {
    if (list.some((e) => e.id === editing.value))
      discardPending();
    context.value = void 0;
    if (!list.length)
      return;
    const ids = refs(list);
    void run(batchArea, "delete", { effects: ids }, () => {
      selection.value = [];
      if (list.some((e) => e.id === editing.value)) {
        editor.value = void 0;
        editing.value = void 0;
      }
    });
  }
  function clear() {
    discardPending();
    clearConfirm.value = false;
    void run(batchArea, "clear", {}, () => {
      selection.value = [];
      editor.value = void 0;
      editing.value = void 0;
    });
  }
  function wheel(event) {
    if (!event.shiftKey)
      return;
    event.preventDefault();
    event.stopPropagation();
    if (selected.value.length)
      void run(batchArea, "transform", { effects: refs(), rotation: event.deltaY > 0 ? 15 : -15 });
  }
  function keyboard(event) {
    if (props.tool === "managed")
      return;
    if (event.target instanceof Element && event.target.closest("input,textarea,select,[contenteditable=true],.gw-window,dialog[open]"))
      return;
    const key2 = event.key.toLowerCase();
    if (event.key === "Escape") {
      if (gesture) {
        cancelAnimationFrame(previewFrame);
        previewFrame = 0;
        gesture = void 0;
        delta.value = { x: 0, y: 0 };
        marquee.value = void 0;
        emit("preview", void 0);
      } else {
        context.value = void 0;
        clearConfirm.value = false;
        closePicker();
        closeEditor();
        selection.value = [];
      }
      event.preventDefault();
      event.stopImmediatePropagation();
      return;
    }
    if (["Delete", "Backspace"].includes(event.key)) {
      event.preventDefault();
      event.stopImmediatePropagation();
      remove();
    }
    if (event.ctrlKey || event.metaKey) {
      if (key2 === "c") {
        event.preventDefault();
        event.stopImmediatePropagation();
        copy();
      }
      if (key2 === "v") {
        event.preventDefault();
        event.stopImmediatePropagation();
        paste();
      }
    }
  }
  root.value = element;
  lastPoint = center();
  const events = { pointerdown: down, pointermove: move, pointerup: up, pointercancel: up, dblclick: doubleClick, contextmenu: menu, wheel };
  const listeners2 = Object.entries(events).map(([name, fn]) => {
    const handler = (e) => {
      fn(e);
      options.repaint();
    };
    element.addEventListener(name, handler);
    return [name, handler];
  });
  const key = (e) => {
    keyboard(e);
    options.repaint();
  };
  document.addEventListener("keydown", key, true);
  return { get view() {
    return { items: items.value, selection: selection.value, selected: selected.value, clipboard: clipboard.value, context: context.value, picker: picker.value, lightChoice: lightChoice.value, editor: editor.value, editing: editing.value, draft: draft.value, error: error.value, busy: busy.value, clearConfirm: clearConfirm.value, delta: delta.value, marquee: marquee.value };
  }, call(name, ...args) {
    const methods = { open, action, choose, closePicker, closeEditor, changed, save, copy, paste, remove, clear, closeMenu: () => context.value = void 0, closeClear: () => clearConfirm.value = false };
    const result = methods[name](...args);
    options.repaint();
    return result;
  }, update(next) {
    Object.assign(props, next);
    const available = new Set(items.value.map((e) => e.key));
    selection.value = selection.value.filter((k) => available.has(k));
    options.repaint();
  }, destroy() {
    if (saveTimer && editor.value === "light" && editing.value) {
      const data = { ...payload("light", draft.value), light_id: editing.value };
      queue = queue.then(() => writer.command(containerId, blockId, "lights", "update", data)).catch(() => {
      });
    }
    closed = true;
    abort.abort();
    clearTimeout(saveTimer);
    clearTimeout(shaderTimer);
    cancelAnimationFrame(previewFrame);
    validator.dispose();
    for (const [name, fn] of listeners2)
      element.removeEventListener(name, fn);
    document.removeEventListener("keydown", key, true);
  } };
}
export {
  sourceController
};
