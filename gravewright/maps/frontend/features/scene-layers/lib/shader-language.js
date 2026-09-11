// Shader vocabulary retained from the legacy renderer. Apache-2.0.
export const PREAMBLE = `#version 300 es
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
export const MESH_VERTEX = `#version 300 es
precision highp float;
in vec2 aPosition;
in vec2 aUV;
out vec2 vTextureCoord;
uniform mat3 uProjectionMatrix;
uniform mat3 uWorldTransformMatrix;
uniform mat3 uTransformMatrix;
void main() {
    vTextureCoord = aUV;
    gl_Position = vec4((uProjectionMatrix * uWorldTransformMatrix * uTransformMatrix * vec3(aPosition, 1.0)).xy, 0.0, 1.0);
}`;
export const USER_PREFIX = `#define uTexture gwUTexture
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
export const USER_SUFFIX = "\n#undef main\nvoid main() { gwUserMain(); finalColor *= gwUOpacity; finalColor = gwIlluminate(finalColor, vTextureCoord, gwULightResponse); }\n";
