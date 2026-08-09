(() => {
    const header = `float gwpHash(vec2 p){return fract(sin(dot(p,vec2(127.1,311.7)))*43758.5453123);}
float gwpNoise(vec2 p){vec2 i=floor(p),f=fract(p);f=f*f*(3.0-2.0*f);return mix(mix(gwpHash(i),gwpHash(i+vec2(1.0,0.0)),f.x),mix(gwpHash(i+vec2(0.0,1.0)),gwpHash(i+vec2(1.0)),f.x),f.y);}
float gwpFbm(vec2 p){float v=0.0,a=0.5;for(int i=0;i<5;i++){v+=a*gwpNoise(p);p=p*2.03+vec2(13.7,9.2);a*=0.5;}return v;}
vec2 gwpRot(vec2 p,float a){float c=cos(a),s=sin(a);return mat2(c,-s,s,c)*p;}
float gwpSat(float x){return clamp(x,0.0,1.0);}
float gwpBand(float x,float c,float w){return exp(-pow((x-c)/max(w,0.0001),2.0));}
float gwpLine(float x,float w){return 1.0-smoothstep(w,w*1.8,abs(x));}
float gwpDisk(vec2 p,float r,float soft){return 1.0-smoothstep(r-soft,r,length(p));}
`;

    const shader = (body) => `${header}${body}`;



    const sources = {





        solArcano: shader(`void main(){
vec2 p=gwPattern(vTextureCoord);float t=uTime*uSpeed*0.75;float d=length(p);float a0=atan(p.y,p.x);
float corona=gwpFbm(vec2(a0*3.4,t*0.22)+vec2(d*5.0,-t*0.11));
float core=exp(-d*d*6.2);float rim=gwpBand(d,0.61+0.035*sin(t*1.7),0.055);
float rayMask=pow(max(0.0,cos(a0*9.0+t*0.9+corona*2.7)),10.0);
float rays=rayMask*exp(-d*1.45)*(1.0-smoothstep(0.18,0.95,d));
float sparks=pow(gwpNoise(p*18.0+vec2(t,-t*0.7)),16.0)*(1.0-smoothstep(0.28,1.0,d));
float e=(core*1.15+rim*0.9+rays*0.72+sparks*0.45)*(0.78+0.32*corona)*uIntensity;
float a=gwpSat(e);
vec3 c=mix(uColor,vec3(1.0,0.92,0.72),gwpSat(core+rim+rays*0.4));
finalColor=vec4(c*a,a);
}`),

        estrelaSolar: shader(`void main(){
vec2 p=gwPattern(vTextureCoord);float t=uTime*uSpeed;float d=length(p);float ang=atan(p.y,p.x);
float disk=exp(-d*d*9.0);float pulse=0.82+0.18*sin(t*3.0);
float flareA=pow(max(0.0,cos(ang*14.0-t*1.6)),22.0)*exp(-d*1.8);
float flareB=pow(max(0.0,cos(ang*5.0+t*0.8)),12.0)*exp(-d*2.4);
float crown=gwpBand(d,0.48+0.03*sin(ang*7.0+t*2.0),0.035);
float grain=0.7+0.45*gwpFbm(p*7.0+vec2(t*0.25));
float e=(disk*1.35*pulse+crown+flareA*0.9+flareB*0.45)*grain*uIntensity;
float a=gwpSat(e);
vec3 hot=mix(uColor,vec3(1.0,0.98,0.82),gwpSat(disk*1.5+crown));
finalColor=vec4(hot*a,a);
}`),

        nucleoGlacial: shader(`void main(){
vec2 p=gwPattern(vTextureCoord);float t=uTime*uSpeed*0.45;float d=length(p);float ang=atan(p.y,p.x);
float facets=abs(cos(ang*3.0));
float crystalR=0.52+0.13*facets;
float shell=gwpBand(d,crystalR,0.035);
float spokes=pow(abs(cos(ang*6.0)),18.0)*(1.0-smoothstep(0.08,0.82,d));
float inner=exp(-d*d*13.0)*(0.8+0.2*sin(t*2.0));
float frost=pow(gwpNoise(p*16.0-vec2(t*0.2)),10.0)*gwpDisk(p,0.75,0.2);
float e=(shell*1.15+spokes*0.52+inner+frost*0.28)*uIntensity;
float a=gwpSat(e);
vec3 c=mix(uColor,vec3(0.92,1.0,1.0),gwpSat(shell+inner+frost*0.4));
finalColor=vec4(c*a,a);
}`),

        olhoCarmesim: shader(`void main(){
vec2 p=gwPattern(vTextureCoord);float t=uTime*uSpeed*0.6;
p=gwpRot(p,0.08*sin(t*0.7));
float d=length(p);
float eye=1.0-smoothstep(0.0,0.055,abs(length(vec2(p.x,p.y*1.8))-0.63));
float iris=gwpBand(d,0.34+0.025*sin(t*1.7),0.12)*(0.65+0.35*gwpFbm(p*8.0+vec2(t*0.2)));
float pupil=1.0-smoothstep(0.035,0.11,abs(p.x));
pupil*=gwpDisk(vec2(p.x,p.y*1.5),0.31,0.07);
float veins=pow(max(0.0,sin(atan(p.y,p.x)*11.0+d*24.0+gwpFbm(p*5.0)*4.0)),12.0)*gwpDisk(p,0.62,0.12);
float e=(eye*0.85+iris*0.9+veins*0.42)*(1.0-pupil*0.8)*uIntensity;
float a=gwpSat(e);
vec3 c=mix(uColor,vec3(1.0,0.55,0.32),iris*0.65);
c*=1.0-pupil*0.75;
finalColor=vec4(c*a,a);
}`),

        luaEspectral: shader(`void main(){
vec2 p=gwPattern(vTextureCoord);float t=uTime*uSpeed*0.25;
float d1=length(p-vec2(-0.06,0.0));
float moon=gwpDisk(p-vec2(-0.06,0.0),0.58,0.08)*(1.0-gwpDisk(p-vec2(0.18,0.02),0.52,0.08));
float halo=gwpBand(d1,0.61,0.13)*0.65;
float ghosts=gwpFbm(p*4.5+vec2(t*0.18,-t*0.08))*gwpBand(d1,0.54,0.34);
float motes=pow(gwpNoise(p*14.0+vec2(0.0,t*0.2)),18.0)*gwpDisk(p,0.9,0.2);
float e=(moon+halo+ghosts*0.24+motes*0.38)*uIntensity;
float a=gwpSat(e);
vec3 c=mix(uColor,vec3(0.94,0.98,1.0),moon+halo*0.45);
finalColor=vec4(c*a,a);
}`),





        portalVioleta: shader(`void main(){
vec2 p=gwPattern(vTextureCoord);float t=uTime*uSpeed*0.7;float d=length(p);float ang=atan(p.y,p.x);
float warp=(gwpFbm(p*4.0+vec2(t))-0.5)*0.16;
float ring=gwpBand(d,0.69+warp,0.06);
float spiral=0.5+0.5*sin(ang*5.0-d*15.0+t*3.0+warp*10.0);
float inner=(1.0-smoothstep(0.08,0.67,d))*(0.25+0.75*gwpFbm(gwpRot(p,t*0.15)*4.0));
float e=(ring*(0.65+0.75*spiral)+inner*0.5)*uIntensity;
float a=gwpSat(e);
vec3 c=mix(uColor,vec3(1.0),ring*0.9);
finalColor=vec4(c*a,a);
}`),

        fendaInfernal: shader(`void main(){
vec2 p=gwPattern(vTextureCoord);float t=uTime*uSpeed*1.1;
vec2 q=gwpRot(p,0.17*sin(t*0.3));
float jag=(gwpFbm(vec2(q.y*5.0,t*0.35))-0.5)*0.28;
float crack=gwpLine(q.x+jag,0.055+0.018*sin(q.y*18.0+t*2.0));
float body=crack*(1.0-smoothstep(0.82,1.05,abs(q.y)));
float glow=exp(-abs(q.x+jag)*7.0)*(1.0-smoothstep(0.76,1.05,abs(q.y)));
float teeth=pow(max(0.0,sin(q.y*19.0+t*1.7+gwpFbm(q*4.0)*3.0)),10.0)*glow;
float e=(body*1.2+glow*0.65+teeth*0.38)*uIntensity;
float a=gwpSat(e);
vec3 c=mix(uColor,vec3(1.0,0.72,0.22),body+teeth*0.5);
finalColor=vec4(c*a,a);
}`),

        passagemFeerica: shader(`void main(){
vec2 p=gwPattern(vTextureCoord);float t=uTime*uSpeed*0.35;float d=length(p);float ang=atan(p.y,p.x);
float petals=0.56+0.11*cos(ang*7.0+t*0.7);
float wreath=gwpBand(d,petals,0.055);
float runes=pow(max(0.0,cos(ang*14.0-t*0.4)),16.0)*gwpBand(d,0.73,0.09);
float shimmer=(1.0-smoothstep(0.12,0.7,d))*(0.3+0.7*gwpFbm(p*5.0+vec2(t*0.15,-t*0.2)));
float e=(wreath+runes*0.65+shimmer*0.34)*uIntensity;
float a=gwpSat(e);
vec3 c=mix(uColor,vec3(0.95,1.0,0.82),wreath+runes*0.5);
finalColor=vec4(c*a,a);
}`),

        buracoAstral: shader(`void main(){
vec2 p=gwPattern(vTextureCoord);float t=uTime*uSpeed*0.5;float d=length(p);float ang=atan(p.y,p.x);
float hole=1.0-smoothstep(0.22,0.36,d);
float lens=gwpBand(d,0.48+0.03*sin(ang*4.0+t),0.055);
float acc=pow(0.5+0.5*sin(ang*4.0-d*22.0+t*2.2),5.0)*gwpBand(d,0.62,0.25);
float stars=pow(gwpNoise(p*22.0+vec2(t*0.03)),24.0)*gwpDisk(p,0.88,0.12)*(1.0-hole);
float e=(lens*1.15+acc*0.7+stars*0.7)*(1.0-hole*0.92)*uIntensity;
float a=gwpSat(e);
vec3 c=mix(uColor,vec3(0.88,0.95,1.0),lens+stars);
finalColor=vec4(c*a,a);
}`),

        seloDourado: shader(`void main(){
vec2 p=gwPattern(vTextureCoord);float t=uTime*uSpeed*0.2;float d=length(p);float ang=atan(p.y,p.x);
float r1=gwpBand(d,0.35,0.018);
float r2=gwpBand(d,0.58,0.022);
float r3=gwpBand(d,0.76,0.018);
float spokes=pow(abs(cos(ang*6.0+t*0.25)),30.0)*step(0.34,d)*(1.0-step(0.76,d));
float glyph=pow(max(0.0,cos(ang*12.0+t*0.15)),28.0)*gwpBand(d,0.67,0.065);
vec2 q1=gwpRot(p,3.14159/6.0);
vec2 q2=gwpRot(p,-3.14159/6.0);
float triangle=gwpLine(max(abs(q1.x)*0.866+q1.y*0.5,q2.x*0.866-q2.y*0.5)-0.38,0.018);
float e=(r1+r2+r3+spokes*0.45+glyph*0.8+triangle*0.3)*uIntensity;
float a=gwpSat(e);
vec3 c=mix(uColor,vec3(1.0,0.96,0.7),gwpSat(r1+r2+r3+glyph));
finalColor=vec4(c*a,a);
}`),





        nevoaPantano: shader(`void main(){
vec2 p=gwPattern(vTextureCoord);float t=uTime*uSpeed*0.18;
vec2 q=p*2.4+vec2(t*0.7,t*0.16);
float low=gwpFbm(q+vec2(0.0,p.y*0.4));
float high=gwpFbm(q*2.1-vec2(t*0.22,0.0));
float bank=smoothstep(0.42,0.78,low+high*0.35);
float strata=0.58+0.42*sin(p.y*5.0+low*4.0);
vec4 L=gwLight(vTextureCoord);
float lit=clamp(L.a,0.0,1.0);
float a=bank*strata*uIntensity*0.7*mix(0.55,1.0,lit);
vec3 c=mix(uColor,uColor+L.rgb*0.45,lit);
finalColor=vec4(c*a,a);
}`),

        fumacaNegra: shader(`void main(){
vec2 p=gwPattern(vTextureCoord);float t=uTime*uSpeed*0.28;
vec2 q=vec2(p.x*2.2,p.y*1.25+t*0.55);
float curl=gwpFbm(q*2.0+vec2(gwpFbm(q+3.0),-gwpFbm(q-4.0)));
float columns=gwpFbm(vec2(p.x*4.0,p.y*1.2+t*0.45));
float smoke=smoothstep(0.32,0.74,curl*0.7+columns*0.5);
float feather=1.0-smoothstep(0.65,1.12,length(vec2(p.x*0.9,p.y*0.6)));
vec4 L=gwLight(vTextureCoord);
float a=smoke*feather*uIntensity*0.82;
vec3 c=mix(uColor*0.55,uColor+L.rgb*0.12,clamp(L.a,0.0,1.0));
finalColor=vec4(c*a,a);
}`),

        brumaGelida: shader(`void main(){
vec2 p=gwPattern(vTextureCoord);float t=uTime*uSpeed*0.12;
float floorBand=1.0-smoothstep(-0.95,0.65,p.y);
float curls=gwpFbm(vec2(p.x*3.0+t*0.3,p.y*5.0)+vec2(sin(p.y*5.0+t)*0.3,0.0));
float mist=smoothstep(0.46,0.77,curls)*floorBand;
float crystals=pow(gwpNoise(p*18.0+vec2(t*0.12,0.0)),20.0)*floorBand;
vec4 L=gwLight(vTextureCoord);
float lit=clamp(L.a,0.0,1.0);
float a=(mist*0.55+crystals*0.28)*uIntensity*mix(0.65,1.0,lit);
vec3 c=mix(uColor,vec3(0.94,1.0,1.0),crystals+lit*0.18);
finalColor=vec4(c*a,a);
}`),

        miasmaPurpura: shader(`void main(){
vec2 p=gwPattern(vTextureCoord);float t=uTime*uSpeed*0.32;
vec2 q=p*4.0+vec2(-t*0.5,t*0.22);
vec2 cell=floor(q);vec2 f=fract(q)-0.5;
float h=gwpHash(cell);
vec2 drift=vec2(sin(t+h*8.0),cos(t*0.7+h*11.0))*0.18;
float bubble=exp(-dot(f+drift,f+drift)*(12.0+18.0*h));
float cloud=smoothstep(0.4,0.72,gwpFbm(p*3.0+vec2(t*0.16)));
float veins=pow(max(0.0,sin((p.x-p.y)*9.0+t*1.6+cloud*4.0)),8.0);
float e=(bubble*0.7+cloud*0.65+veins*cloud*0.15)*uIntensity;
float a=min(e,0.76);
vec3 c=mix(uColor,vec3(0.65,1.0,0.45),bubble*0.12);
finalColor=vec4(c*a,a);
}`),

        poeiraAntiga: shader(`void main(){
vec2 p=gwPattern(vTextureCoord);float t=uTime*uSpeed*0.08;
vec2 q=p*12.0;vec2 cell=floor(q);vec2 f=fract(q)-0.5;float h=gwpHash(cell);
f.y+=fract(t*0.18+h)-0.5;
f.x+=sin(t*0.7+h*20.0)*0.12;
float mote=exp(-dot(f,f)*(75.0+90.0*h))*step(0.56,h);
float haze=smoothstep(0.52,0.82,gwpFbm(p*2.1+vec2(t*0.05,0.0)));
float shafts=pow(max(0.0,0.5+0.5*sin((p.x+p.y*0.35)*7.0+t*0.15)),10.0)*0.12;
vec4 L=gwLight(vTextureCoord);float lit=clamp(L.a,0.0,1.0);
float a=(mote*0.85+haze*0.22+shafts)*uIntensity*mix(0.35,1.0,lit);
vec3 c=mix(uColor,uColor+L.rgb*0.7,lit);
finalColor=vec4(c*a,a);
}`),





        fogueira: shader(`void main(){
vec2 p=gwPattern(vTextureCoord);float t=uTime*uSpeed;float y=p.y+0.72;
float sway=(gwpFbm(vec2(y*3.0,t*0.8))-0.5)*0.35;
float width=max(0.08,0.68-(y+0.1)*0.5);
float body=1.0-smoothstep(width*0.35,width,abs(p.x+sway));
body*=smoothstep(-0.35,-0.05,y)*(1.0-smoothstep(0.1,1.12,y));
float tongues=0.55+0.55*gwpFbm(vec2((p.x+sway)*5.0,y*4.0-t*1.8));
float ember=pow(gwpNoise(p*16.0-vec2(0.0,t*2.0)),18.0)*smoothstep(-0.3,0.9,y);
float a=gwpSat((body*tongues+ember*0.25)*uIntensity);
vec3 c=mix(uColor,vec3(1.0,0.95,0.55),gwpSat(body*(1.0-y*0.45)));
finalColor=vec4(c*a,a);
}`),

        chamaAzul: shader(`void main(){
vec2 p=gwPattern(vTextureCoord);float t=uTime*uSpeed*1.25;float y=p.y+0.78;
float wiggle=sin(y*7.0-t*2.2)*0.05+(gwpNoise(vec2(y*5.0,t))-0.5)*0.12;
float cone=max(0.045,0.34-(y+0.15)*0.2);
float outer=1.0-smoothstep(cone*0.55,cone,abs(p.x+wiggle));
outer*=smoothstep(-0.3,-0.05,y)*(1.0-smoothstep(0.12,1.18,y));
float core=1.0-smoothstep(cone*0.12,cone*0.42,abs(p.x+wiggle*0.4));
core*=1.0-smoothstep(0.05,0.82,y);
float a=gwpSat((outer*0.7+core)*uIntensity);
vec3 c=mix(uColor,vec3(0.92,0.98,1.0),core);
finalColor=vec4(c*a,a);
}`),

        fogoVerde: shader(`void main(){
vec2 p=gwPattern(vTextureCoord);float t=uTime*uSpeed*0.8;float y=p.y+0.65;
float bubbling=0.18*sin(p.x*12.0+t*3.0)+0.12*sin(p.x*23.0-t*2.0);
float w=max(0.09,0.56-(y+0.12)*0.4+bubbling*0.18);
float flame=1.0-smoothstep(w*0.45,w,abs(p.x+(gwpFbm(vec2(y*5.0,t))-0.5)*0.28));
flame*=smoothstep(-0.42,-0.08,y)*(1.0-smoothstep(0.0,0.9,y));
float bubbles=pow(gwpNoise(p*12.0+vec2(t*0.3,-t*1.4)),14.0)*gwpDisk(vec2(p.x,y-0.05),0.72,0.22);
float a=gwpSat((flame*(0.6+0.7*gwpFbm(p*6.0-vec2(0.0,t)))+bubbles*0.35)*uIntensity);
vec3 c=mix(uColor,vec3(0.85,1.0,0.35),bubbles+flame*0.25);
finalColor=vec4(c*a,a);
}`),

        brasaSombria: shader(`void main(){
vec2 p=gwPattern(vTextureCoord);float t=uTime*uSpeed*0.55;float y=p.y+0.7;
float drift=(gwpFbm(vec2(y*3.0,t*0.4))-0.5)*0.42;
float w=max(0.07,0.5-(y+0.2)*0.38);
float silhouette=1.0-smoothstep(w*0.4,w,abs(p.x+drift));
silhouette*=smoothstep(-0.38,-0.05,y)*(1.0-smoothstep(0.0,0.82,y));
float holes=smoothstep(0.48,0.8,gwpFbm(p*7.0-vec2(0.0,t*0.7)));
float ember=pow(gwpNoise(p*18.0+vec2(t*0.2,-t)),20.0)*silhouette;
float a=gwpSat((silhouette*(0.48+0.35*holes)+ember*0.7)*uIntensity);
vec3 c=mix(uColor*0.38,vec3(1.0,0.16,0.04),ember+silhouette*(1.0-holes)*0.2);
finalColor=vec4(c*a,a);
}`),

        fogoSagrado: shader(`void main(){
vec2 p=gwPattern(vTextureCoord);float t=uTime*uSpeed*0.6;float y=p.y+0.72;
float w=max(0.08,0.45-(y+0.05)*0.3);
float flame=1.0-smoothstep(w*0.36,w,abs(p.x+sin(y*6.0+t)*0.06));
flame*=smoothstep(-0.35,-0.08,y)*(1.0-smoothstep(0.0,1.05,y));
float halo=gwpBand(length(p-vec2(0.0,-0.18)),0.62,0.12)*0.35;
float rays=pow(max(0.0,cos(atan(p.y,p.x)*8.0+t*0.35)),22.0)*exp(-length(p)*2.1)*0.5;
float a=gwpSat((flame+halo+rays)*uIntensity);
vec3 c=mix(uColor,vec3(1.0,1.0,0.86),flame+halo*0.4);
finalColor=vec4(c*a,a);
}`),





        reflexoAgua: shader(`void main(){
vec2 p=gwPattern(vTextureCoord);float t=uTime*uSpeed*0.4;
float w1=sin(p.x*8.0+t*1.7+p.y*2.3);
float w2=sin(p.y*11.0-t*1.2+p.x*3.4);
float w3=sin((p.x+p.y)*6.5+t*0.7);
float caustic=pow(abs(w1+w2+w3)*0.333,5.0);
float ripples=gwpBand(abs(sin(length(p-vec2(sin(t)*0.2,cos(t)*0.2))*18.0-t*2.0)),0.0,0.12);
vec4 L=gwLight(vTextureCoord);
float lit=clamp(L.a,0.0,1.0);
float a=(caustic*0.72+ripples*0.15)*uIntensity*0.65;
vec3 c=mix(uColor,vec3(0.78,0.96,1.0)+L.rgb*0.35,gwpSat(caustic+lit*0.25));
finalColor=vec4(c*a,a);
}`),

        abismoOceanico: shader(`void main(){
vec2 p=gwPattern(vTextureCoord);float t=uTime*uSpeed*0.22;
float swell=0.5+0.5*sin(p.x*3.2+t*0.55+sin(p.y*2.4-t*0.2));
float cross=0.5+0.5*sin(p.y*4.1-t*0.42+p.x*1.6);
float trenches=smoothstep(0.38,0.72,gwpFbm(p*2.3+vec2(t*0.07,-t*0.04)));
float foam=pow(abs(swell-cross),5.0)*0.32;
float a=gwpSat((swell*0.3+cross*0.22+trenches*0.45+foam)*uIntensity*0.72);
vec3 c=mix(uColor*0.45,uColor*1.15,foam+0.15*swell);
finalColor=vec4(c*a,a);
}`),

        pocaAcida: shader(`void main(){
vec2 p=gwPattern(vTextureCoord);float t=uTime*uSpeed*0.65;
vec2 q=p*6.0;vec2 cell=floor(q);vec2 f=fract(q)-0.5;
float h=gwpHash(cell);float r=0.12+0.28*h;
float bubble=gwpBand(length(f+vec2(sin(t+h*8.0),cos(t*0.6+h*10.0))*0.12),r,0.055);
float film=gwpFbm(p*5.0+vec2(t*0.18));
float veins=pow(max(0.0,sin((p.x-p.y)*10.0+t+film*4.0)),9.0);
float a=gwpSat((bubble*0.9+film*0.25+veins*0.18)*uIntensity*0.7);
vec3 c=mix(uColor,vec3(0.9,1.0,0.18),bubble+veins*0.25);
finalColor=vec4(c*a,a);
}`),

        lavaFluida: shader(`void main(){
vec2 p=gwPattern(vTextureCoord);float t=uTime*uSpeed*0.32;
float n=gwpFbm(p*3.2+vec2(t*0.18,-t*0.06));
float n2=gwpFbm(p*7.0-vec2(t*0.1,t*0.12));
float veins=pow(gwpSat(1.0-abs(n-n2)*3.2),6.0);
float plates=smoothstep(0.43,0.62,n);
float glow=veins*(0.75+0.25*sin(t*1.4+n*8.0));
float a=gwpSat((plates*0.42+glow*1.1)*uIntensity*0.9);
vec3 c=mix(vec3(0.22,0.025,0.01),uColor,plates);
c=mix(c,vec3(1.0,0.82,0.22),glow);
finalColor=vec4(c*a,a);
}`),

        mercurio: shader(`void main(){
vec2 p=gwPattern(vTextureCoord);float t=uTime*uSpeed*0.5;
float h=sin(p.x*14.0+t)+sin(p.y*9.0-t*0.7)+sin((p.x+p.y)*17.0+t*0.35);
h/=3.0;
float ridges=pow(abs(h),9.0);
float warp=gwpFbm(p*8.0+vec2(t*0.08));
float spec=pow(gwpSat(0.5+0.5*sin(h*8.0+warp*5.0)),12.0);
vec4 L=gwLight(vTextureCoord);
float lit=clamp(L.a,0.0,1.0);
float a=gwpSat((0.18+ridges*0.42+spec*0.65)*uIntensity*0.55);
vec3 c=mix(uColor*0.7,vec3(1.0)+L.rgb*0.25,spec*0.8+lit*0.2);
finalColor=vec4(c*a,a);
}`),





        chuvaFina: shader(`void main(){
vec2 p=gwPattern(vTextureCoord);float t=uTime*uSpeed*0.8;
vec2 q=gwpRot(p,0.18)*vec2(14.0,8.0)+vec2(t*0.7,-t*3.2);
vec2 cell=floor(q);vec2 f=fract(q);float h=gwpHash(cell);
float streak=(1.0-smoothstep(0.025,0.06,abs(f.x-h)))*
             (1.0-smoothstep(0.0,0.55,fract(f.y+h)));
float e=streak*step(0.52,h)*uIntensity;
float a=min(e,0.62);
vec3 c=mix(uColor,vec3(0.88,0.96,1.0),h*0.25);
finalColor=vec4(c*a,a);
}`),

        tempestade: shader(`void main(){
vec2 p=gwPattern(vTextureCoord);float t=uTime*uSpeed*1.4;
vec2 q=gwpRot(p,0.32)*vec2(20.0,6.0)+vec2(t*1.8,-t*5.6);
vec2 cell=floor(q);vec2 f=fract(q);float h=gwpHash(cell);
float rain=(1.0-smoothstep(0.045,0.1,abs(f.x-h)))*
           (1.0-smoothstep(0.08,0.8,fract(f.y+h)))*step(0.30,h);
float flash=pow(max(0.0,sin(t*0.37+floor(t*0.37)*4.1)),32.0);
float cloud=smoothstep(0.42,0.72,gwpFbm(p*2.2+vec2(t*0.08)))*0.18;
float a=gwpSat((rain*1.35+cloud+flash*0.28)*uIntensity);
vec3 c=mix(uColor,vec3(1.0),flash*0.8);
finalColor=vec4(c*a,a);
}`),

        nevasca: shader(`void main(){
vec2 p=gwPattern(vTextureCoord);float t=uTime*uSpeed*0.45;
vec2 q=p*9.0;vec2 cell=floor(q);vec2 f=fract(q)-0.5;float h=gwpHash(cell);
float phase=t*(0.25+0.65*h);
f+=vec2(sin(phase+h*20.0)*0.42,fract(phase*0.45+h)-0.5);
float d=length(f);
float flake=exp(-d*d*(26.0+45.0*h))*step(0.36,h);
float cross=(gwpLine(f.x,0.025)+gwpLine(f.y,0.025))*exp(-d*d*22.0)*step(0.72,h);
float a=gwpSat((flake+cross*0.5)*uIntensity*0.8);
finalColor=vec4(uColor*a,a);
}`),

        cinzas: shader(`void main(){
vec2 p=gwPattern(vTextureCoord);float t=uTime*uSpeed*0.18;
vec2 q=p*10.0;vec2 cell=floor(q);vec2 f=fract(q)-0.5;float h=gwpHash(cell);
float fall=fract(t*0.2+h);
f.y+=fall-0.5;
f.x+=sin(t+h*18.0)*0.18;
float angle=t*0.7+h*6.28;
vec2 r=gwpRot(f,angle);
float shard=exp(-(r.x*r.x*120.0+r.y*r.y*35.0))*step(0.42,h);
float haze=smoothstep(0.56,0.8,gwpFbm(p*2.5+vec2(t*0.04)))*0.18;
float a=gwpSat((shard+haze)*uIntensity*0.62);
finalColor=vec4(uColor*a,a);
}`),

        chuvaArcana: shader(`void main(){
vec2 p=gwPattern(vTextureCoord);float t=uTime*uSpeed*0.7;
vec2 q=gwpRot(p,-0.14)*vec2(15.0,8.0)+vec2(-t*0.45,t*2.6);
vec2 cell=floor(q);vec2 f=fract(q);float h=gwpHash(cell);
float streak=(1.0-smoothstep(0.03,0.07,abs(f.x-h)))*
             (1.0-smoothstep(0.0,0.5,fract(1.0-f.y+h)))*step(0.55,h);
float rune=pow(max(0.0,cos((f.x+f.y)*12.0+h*20.0+t)),14.0)*step(0.82,h);
float a=gwpSat((streak+rune*0.5)*uIntensity*0.78);
vec3 c=mix(uColor,vec3(0.9,0.7,1.0),rune);
finalColor=vec4(c*a,a);
}`),





        vagalumes: shader(`void main(){
vec2 p=gwPattern(vTextureCoord);float t=uTime*uSpeed*0.45;
vec2 q=p*7.0;vec2 cell=floor(q);vec2 f=fract(q)-0.5;float h=gwpHash(cell);
f+=vec2(sin(t*0.9+h*21.0),cos(t*0.63+h*17.0))*0.28;
float dotv=exp(-dot(f,f)*(55.0+35.0*h))*step(0.48,h);
float blink=pow(0.5+0.5*sin(t*3.0+h*30.0),3.0);
float a=gwpSat(dotv*blink*uIntensity*1.2);
vec3 c=mix(uColor,vec3(1.0,0.96,0.62),blink*0.7);
finalColor=vec4(c*a,a);
}`),

        esporos: shader(`void main(){
vec2 p=gwPattern(vTextureCoord);float t=uTime*uSpeed*0.2;
vec2 q=p*8.0;vec2 cell=floor(q);vec2 f=fract(q)-0.5;float h=gwpHash(cell);
f.y+=fract(t*0.18+h)-0.5;
f.x+=sin(t*0.5+h*12.0)*0.22;
float big=exp(-dot(f,f)*(24.0+24.0*h))*step(0.38,h);
float halo=exp(-dot(f,f)*8.0)*step(0.78,h)*0.22;
float a=gwpSat((big+halo)*uIntensity*0.72);
vec3 c=mix(uColor,vec3(0.72,1.0,0.65),halo);
finalColor=vec4(c*a,a);
}`),

        faiscas: shader(`void main(){
vec2 p=gwPattern(vTextureCoord);float t=uTime*uSpeed*1.2;
vec2 q=p*12.0;vec2 cell=floor(q);vec2 f=fract(q)-0.5;float h=gwpHash(cell);
float age=fract(t*0.42+h);
f.y+=age*1.2-0.62;
f.x+=sin(age*3.14+h*8.0)*0.18;
vec2 r=gwpRot(f,-0.28+0.4*h);
float streak=exp(-(r.x*r.x*140.0+r.y*r.y*18.0))*step(0.60,h)*(1.0-age);
float head=exp(-dot(f,f)*120.0)*step(0.6,h);
float a=gwpSat((streak+head*0.7)*uIntensity*1.25);
vec3 c=mix(uColor,vec3(1.0,0.95,0.55),head);
finalColor=vec4(c*a,a);
}`),

        almas: shader(`void main(){
vec2 p=gwPattern(vTextureCoord);float t=uTime*uSpeed*0.3;
vec2 q=p*4.5;vec2 cell=floor(q);vec2 f=fract(q)-0.5;float h=gwpHash(cell);
f+=vec2(sin(t*0.65+h*14.0)*0.32,fract(t*0.12+h)-0.5);
float head=exp(-dot(f-vec2(0.0,-0.08),f-vec2(0.0,-0.08))*26.0)*step(0.42,h);
float tail=exp(-(f.x*f.x*18.0+(f.y-0.22)*(f.y-0.22)*5.0))*step(0.42,h)*(0.6+0.4*sin(t+h*20.0));
float eyes=
    (exp(-dot(f-vec2(-0.07,-0.11),f-vec2(-0.07,-0.11))*260.0)+
     exp(-dot(f-vec2(0.07,-0.11),f-vec2(0.07,-0.11))*260.0))*step(0.75,h);
float a=gwpSat((head*0.65+tail*0.5+eyes)*uIntensity);
vec3 c=mix(uColor,vec3(1.0),eyes);
finalColor=vec4(c*a,a);
}`),

        poeiraCosmica: shader(`void main(){
vec2 p=gwPattern(vTextureCoord);float t=uTime*uSpeed*0.12;
vec2 q=p*15.0;vec2 cell=floor(q);vec2 f=fract(q)-0.5;float h=gwpHash(cell);
float star=exp(-dot(f,f)*(120.0+120.0*h))*step(0.68,h);
float twinkle=pow(0.5+0.5*sin(t*5.0+h*40.0),5.0);
float cross=(gwpLine(f.x,0.012)+gwpLine(f.y,0.012))*exp(-dot(f,f)*35.0)*step(0.9,h);
float nebula=smoothstep(0.52,0.78,gwpFbm(p*2.1+vec2(t*0.03,-t*0.02)))*0.16;
float a=gwpSat((star*twinkle+cross*0.4+nebula)*uIntensity);
vec3 c=mix(uColor,vec3(1.0),star*twinkle*0.8);
finalColor=vec4(c*a,a);
}`),





        gradeArcana: shader(`void main(){
vec2 p=gwPattern(vTextureCoord);float t=uTime*uSpeed*0.35;
vec2 q=p*4.5;
vec2 hq=vec2(q.x+q.y*0.57735,q.y*1.1547);
vec2 f=abs(fract(hq)-0.5);
float hex=1.0-smoothstep(0.43,0.48,max(f.x,f.y));
float edge=smoothstep(0.31,0.42,max(f.x,f.y))*hex;
vec2 local=fract(hq)-0.5;
float node=exp(-dot(local,local)*75.0);
float pulse=0.55+0.45*sin(t*2.0+floor(hq.x)+floor(hq.y));
float a=gwpSat((edge*0.52+node*pulse*0.85)*uIntensity*0.72);
finalColor=vec4(uColor*a,a);
}`),

        holograma: shader(`void main(){
vec2 p=gwPattern(vTextureCoord);float t=uTime*uSpeed*0.8;
vec2 q=p*8.0;vec2 f=abs(fract(q)-0.5);
float grid=(1.0-smoothstep(0.04,0.08,min(f.x,f.y)))*0.45;
float scan=pow(0.5+0.5*sin((p.y-t)*18.0),12.0);
float glitch=step(0.82,gwpNoise(vec2(floor(p.y*18.0),floor(t*6.0))))*0.22;
vec2 local=fract(q)-0.5;
float nodes=exp(-dot(local,local)*90.0)*(0.4+0.6*sin(t*4.0));
float a=gwpSat((grid+scan*0.7+glitch+nodes*0.5)*uIntensity*0.72);
vec3 c=mix(uColor,vec3(0.85,1.0,1.0),scan);
finalColor=vec4(c*a,a);
}`),

        circuito: shader(`void main(){
vec2 p=gwPattern(vTextureCoord);float t=uTime*uSpeed*0.2;
vec2 q=p*10.0;vec2 cell=floor(q);vec2 f=fract(q)-0.5;float h=gwpHash(cell);
float horiz=gwpLine(f.y-(step(0.5,h)-0.5)*0.34,0.035)*step(0.35,h);
float vert=gwpLine(f.x-(step(0.72,h)-0.5)*0.34,0.035)*step(0.52,1.0-h);
float pad=exp(-dot(f,f)*120.0)*step(0.76,h);
float data=0.45+0.55*sin(t*5.0+cell.x*0.7+cell.y*1.3);
float a=gwpSat((horiz*0.55+vert*0.55+pad*data)*uIntensity*0.62);
finalColor=vec4(uColor*a,a);
}`),

        prisaoRunica: shader(`void main(){
vec2 p=gwPattern(vTextureCoord);float t=uTime*uSpeed*0.5;
float d=length(p);float ang=atan(p.y,p.x);
float rings=gwpBand(d,0.38,0.025)+gwpBand(d,0.68,0.025)+gwpBand(d,0.9,0.018);
float bars=pow(abs(cos(ang*4.0)),24.0)*step(0.32,d)*(1.0-step(0.93,d));
float glyph=pow(max(0.0,cos(ang*8.0+t*0.5)),24.0)*gwpBand(d,0.78,0.055);
float flash=0.65+0.35*sin(t*2.0+d*12.0);
float a=gwpSat((rings+bars*0.55+glyph*0.85)*flash*uIntensity*0.82);
finalColor=vec4(uColor*a,a);
}`),

        tabuleiroFantasma: shader(`void main(){
vec2 p=gwPattern(vTextureCoord);float t=uTime*uSpeed*0.08;
vec2 q=floor(p*6.0);
float checker=mod(q.x+q.y,2.0);
float fade=0.28+0.24*sin(t*1.5+q.x*0.7-q.y*0.4);
vec2 f=abs(fract(p*6.0)-0.5);
float seams=1.0-smoothstep(0.44,0.49,max(f.x,f.y));
float ghost=(checker*0.32+seams*0.18)*fade;
float drift=gwpFbm(p*2.0+vec2(t*0.03))*0.1;
float a=gwpSat((ghost+drift)*uIntensity*0.38);
finalColor=vec4(uColor*a,a);
}`),





        redemoinho: shader(`void main(){
vec2 p=gwPattern(vTextureCoord);float t=uTime*uSpeed*0.55;
float d=length(p);float ang=atan(p.y,p.x);
float n=gwpFbm(vec2(d*4.0,ang*1.5+t*0.4));
float spiral=pow(0.5+0.5*sin(ang*6.0-d*17.0+t*2.0+n*2.0),3.0);
float basin=smoothstep(0.1,0.22,d)*(1.0-smoothstep(0.72,1.1,d));
float foam=pow(spiral,2.0)*basin;
float rings=(gwpBand(d,0.42,0.025)+gwpBand(d,0.7,0.03))*0.3;
float a=gwpSat((foam+rings)*uIntensity);
vec3 c=mix(uColor,vec3(0.78,0.96,1.0),foam*0.55);
finalColor=vec4(c*a,a);
}`),

        singularidade: shader(`void main(){
vec2 p=gwPattern(vTextureCoord);float t=uTime*uSpeed*0.4;
float d=length(p);float ang=atan(p.y,p.x);
float hole=1.0-smoothstep(0.17,0.33,d);
float disk=gwpBand(d,0.53,0.16)*(0.5+0.5*sin(ang*9.0-d*27.0+t*1.4));
float lens=gwpBand(d,0.36,0.025)+gwpBand(d,0.78,0.018)*0.45;
float sparks=pow(gwpNoise(vec2(ang*8.0,d*15.0+t)),18.0)*gwpBand(d,0.62,0.22);
float e=(disk*1.2+lens+sparks*0.65)*(1.0-hole)*uIntensity;
float a=gwpSat(e);
vec3 c=mix(uColor,vec3(1.0),lens+sparks*0.5);
finalColor=vec4(c*a,a);
}`),

        cicloneAreia: shader(`void main(){
vec2 p=gwPattern(vTextureCoord);float t=uTime*uSpeed*0.7;
float y=p.y;
float taper=0.24+0.52*(1.0-gwpSat((y+1.0)*0.5));
float ang=atan(p.y,p.x);
float bands=pow(0.5+0.5*sin(ang*11.0-length(p)*18.0+t*2.5+gwpFbm(p*5.0)*4.0),2.0);
float column=1.0-smoothstep(taper,taper+0.22,abs(p.x));
float grains=pow(gwpNoise(p*18.0+vec2(t*0.3,-t)),12.0)*column;
float a=gwpSat((bands*column*0.52+grains*0.35)*uIntensity*0.85);
finalColor=vec4(uColor*a,a);
}`),

        tormentaVerde: shader(`void main(){
vec2 p=gwPattern(vTextureCoord);float t=uTime*uSpeed*0.9;
float d=length(p);float ang=atan(p.y,p.x);
float n=gwpFbm(gwpRot(p,t*0.1)*6.0);
float arms=pow(0.5+0.5*sin(ang*7.0-d*30.0+t*3.2+n*5.0),2.5);
float eddies=pow(gwpFbm(p*10.0+vec2(t*0.12)),2.0);
float body=smoothstep(0.1,0.2,d)*(1.0-smoothstep(0.72,1.2,d));
float a=gwpSat((arms*0.72+eddies*0.32)*body*uIntensity*0.9);
vec3 c=mix(uColor,vec3(0.7,1.0,0.38),eddies*0.25);
finalColor=vec4(c*a,a);
}`),

        galaxia: shader(`void main(){
vec2 p=gwPattern(vTextureCoord);float t=uTime*uSpeed*0.12;
float d=length(p);float ang=atan(p.y,p.x);
float arm=pow(0.5+0.5*cos(ang*4.0-d*12.0+t*0.7),7.0)*exp(-d*1.5);
float dust=gwpFbm(vec2(ang*2.0-d*3.0,d*8.0+t*0.15))*arm;
vec2 q=p*18.0;vec2 cell=floor(q);vec2 f=fract(q)-0.5;float h=gwpHash(cell);
float stars=exp(-dot(f,f)*180.0)*step(0.74,h)*gwpDisk(p,1.05,0.12);
float bulge=exp(-d*d*10.0);
float a=gwpSat((arm*0.75+dust*0.42+stars+bulge*0.65)*uIntensity);
vec3 c=mix(uColor,vec3(1.0,0.92,0.76),bulge+stars*0.5);
finalColor=vec4(c*a,a);
}`),





        auraSagrada: shader(`void main(){
vec2 p=gwPattern(vTextureCoord);float t=uTime*uSpeed*0.35;
float d=length(p);float ang=atan(p.y,p.x);
float halo=gwpBand(d,0.72+0.025*sin(t*2.0),0.055);
float rays=pow(max(0.0,cos(ang*6.0+t*0.3)),18.0)*gwpBand(d,0.78,0.24);
float inner=exp(-d*d*3.2)*0.18;
float motes=pow(gwpNoise(p*16.0-vec2(0.0,t*0.3)),20.0)*gwpBand(d,0.6,0.38);
float a=gwpSat((halo+rays*0.5+inner+motes*0.3)*uIntensity*0.78);
vec3 c=mix(uColor,vec3(1.0,1.0,0.86),halo+rays*0.4);
finalColor=vec4(c*a,a);
}`),

        auraSombria: shader(`void main(){
vec2 p=gwPattern(vTextureCoord);float t=uTime*uSpeed*0.5;
float d=length(p);float ang=atan(p.y,p.x);
float wob=(gwpFbm(vec2(ang*5.0,t*0.4))-0.5)*0.15;
float rim=gwpBand(d,0.68+wob,0.09);
float tendrils=pow(max(0.0,sin(ang*9.0+d*17.0-t*2.0+gwpFbm(p*6.0)*4.0)),5.0)*gwpBand(d,0.55,0.32);
float inner=exp(-d*d*2.0)*0.36;
float a=gwpSat((rim*0.8+tendrils*0.5+inner)*uIntensity*0.82);
vec3 c=mix(uColor*0.48,uColor,rim);
finalColor=vec4(c*a,a);
}`),

        escudoArcano: shader(`void main(){
vec2 p=gwPattern(vTextureCoord);float t=uTime*uSpeed*0.22;
float d=length(p);float ang=atan(p.y,p.x);
float hexR=0.77/max(abs(cos(mod(ang+0.523599,1.047198)-0.523599)),0.5);
float shell=gwpBand(d,hexR,0.028);
float rings=gwpBand(d,0.58,0.018)*0.45;
float scan=gwpBand(p.y,0.62*sin(t*2.0),0.025)*gwpDisk(p,0.82,0.08);
float nodes=pow(max(0.0,cos(ang*6.0)),28.0)*gwpBand(d,0.77,0.07);
float a=gwpSat((shell+rings+scan*0.55+nodes*0.7)*uIntensity*0.72);
vec3 c=mix(uColor,vec3(0.9,0.98,1.0),shell+nodes);
finalColor=vec4(c*a,a);
}`),

        veneno: shader(`void main(){
vec2 p=gwPattern(vTextureCoord);float t=uTime*uSpeed*0.65;
float d=length(p);
float cloud=smoothstep(0.4,0.72,gwpFbm(p*5.0+vec2(t*0.18,-t*0.08)))*
            (1.0-smoothstep(0.58,0.92,d));
vec2 q=p*7.0;vec2 cell=floor(q);vec2 f=fract(q)-0.5;float h=gwpHash(cell);
float bubble=gwpBand(length(f),0.18+0.15*h,0.05)*step(0.45,h);
float pulse=0.72+0.28*sin(t*2.5+d*7.0);
float a=gwpSat((cloud*0.75+bubble*0.48)*pulse*uIntensity*0.7);
vec3 c=mix(uColor,vec3(0.82,1.0,0.28),bubble*0.4);
finalColor=vec4(c*a,a);
}`),

        auraSangue: shader(`void main(){
vec2 p=gwPattern(vTextureCoord);float t=uTime*uSpeed*0.75;
float d=length(p);float ang=atan(p.y,p.x);
float pulse=0.68+0.12*sin(t*5.0);
float rim=gwpBand(d,0.69+pulse*0.04,0.055);
float spikes=pow(max(0.0,cos(ang*11.0+t*0.8)),10.0)*gwpBand(d,0.75,0.22);
float drops=pow(gwpNoise(vec2(ang*8.0,t*0.2+d*5.0)),14.0)*gwpBand(d,0.62,0.3);
float inner=exp(-d*d*4.0)*0.2;
float a=gwpSat((rim*0.9+spikes*0.55+drops*0.4+inner)*uIntensity*0.8);
vec3 c=mix(uColor,vec3(0.85,0.05,0.08),drops+spikes*0.25);
finalColor=vec4(c*a,a);
}`),
    };

    const defaults = {
        opacity: 1,
        intensity: 0.8,
        scale: 1,
        speed: 1,
        rotation: 0,
        radius: 8,
        enabled: true,
    };

    const catalog = [

        ["orb-1","Energia","Sol Arcano","Disco radiante com coroa turbulenta, raios longos e fagulhas.","#8f6bff","add","solArcano",{radius:6,scale:1.0}],
        ["orb-2","Energia","Estrela Solar","Estrela pulsante com duas famílias de flares e coroa viva.","#ff9a32","screen","estrelaSolar",{radius:6,scale:1.0,speed:1.1}],
        ["orb-3","Energia","Núcleo Glacial","Cristal hexagonal com facetas, espinhos e geada cintilante.","#58cfff","add","nucleoGlacial",{radius:5,scale:0.9,speed:0.7}],
        ["orb-4","Energia","Olho Carmesim","Olho arcano vivo com íris, pupila vertical e veios pulsantes.","#ff253a","screen","olhoCarmesim",{radius:5,scale:1.1,intensity:0.9}],
        ["orb-5","Energia","Lua Espectral","Crescente espectral com halo, motes e bruma fantasmagórica.","#b9d5ff","screen","luaEspectral",{radius:6,scale:1.0,speed:0.6}],


        ["portal-1","Portais","Portal Violeta","Anel espiralado com superfície interna turbulenta.","#9b55ff","add","portalVioleta",{radius:6,scale:1.0}],
        ["portal-2","Portais","Fenda Infernal","Rasgo vertical serrilhado, luminoso e instável.","#ff3b18","screen","fendaInfernal",{radius:5,scale:1.0,intensity:0.95}],
        ["portal-3","Portais","Passagem Feérica","Coroa de pétalas e runas com interior cintilante.","#55e89b","screen","passagemFeerica",{radius:6,scale:1.1,speed:0.7}],
        ["portal-4","Portais","Buraco Astral","Núcleo vazio com lente gravitacional, disco e estrelas.","#467cff","add","buracoAstral",{radius:6,scale:1.0,opacity:0.9}],
        ["portal-5","Portais","Selo Dourado","Geometria ritual precisa com anéis, glifos e raios simétricos.","#ffc95b","screen","seloDourado",{radius:5,scale:1.0,speed:0.5}],


        ["fog-1","Atmosfera","Névoa de Pântano","Bancos estratificados de névoa úmida que respondem à luz.","#708f68","normal","nevoaPantano",{radius:0,scale:2.2,opacity:0.72,speed:0.65}],
        ["fog-2","Atmosfera","Fumaça Negra","Colunas turbulentas de fumaça densa que sobem e se enrolam.","#30343d","multiply","fumacaNegra",{radius:10,scale:1.8,opacity:0.82,intensity:0.9}],
        ["fog-3","Atmosfera","Bruma Gélida","Bruma rasteira com cristais de gelo suspensos.","#a8dcf0","screen","brumaGelida",{radius:0,scale:2.5,opacity:0.58,speed:0.55}],
        ["fog-4","Atmosfera","Miasma Púrpura","Gás tóxico celular com bolhas e veios internos.","#9a45b8","normal","miasmaPurpura",{radius:9,scale:1.6,opacity:0.76,intensity:0.9}],
        ["fog-5","Atmosfera","Poeira Antiga","Motes suspensos, haze e fachos tênues em contraluz.","#b69a70","screen","poeiraAntiga",{radius:0,scale:2.0,opacity:0.5,speed:0.45}],


        ["flame-1","Fogo","Fogueira","Chama larga com línguas irregulares e brasas ascendentes.","#ff6a18","add","fogueira",{radius:4,scale:1.0,speed:1.0}],
        ["flame-2","Fogo","Chama Azul","Jato azul estreito com núcleo branco e oscilação rápida.","#299cff","screen","chamaAzul",{radius:4,scale:0.9,speed:1.1}],
        ["flame-3","Fogo","Fogo Verde","Combustão alquímica borbulhante com labaredas verdes.","#52e858","add","fogoVerde",{radius:4,scale:1.0,intensity:0.9}],
        ["flame-4","Fogo","Brasa Sombria","Fogo escuro perfurado por carvão e pontos de brasa vermelha.","#d52b20","screen","brasaSombria",{radius:4,scale:1.05,opacity:0.85}],
        ["flame-5","Fogo","Fogo Sagrado","Chama simétrica com halo e raios dourados.","#ffd35a","add","fogoSagrado",{radius:5,scale:1.0,speed:0.7}],


        ["liquid-1","Água","Reflexo de Água","Caustics de ondas cruzadas com pequenas ondulações concêntricas.","#45a8d8","screen","reflexoAgua",{radius:0,scale:1.4,opacity:0.65}],
        ["liquid-2","Água","Abismo Oceânico","Ondas largas, cruzadas e profundas com vales escuros.","#164f83","multiply","abismoOceanico",{radius:0,scale:1.8,opacity:0.72,speed:0.65}],
        ["liquid-3","Água","Poça Ácida","Filme corrosivo com bolhas celulares e veios brilhantes.","#78d934","screen","pocaAcida",{radius:6,scale:1.1,opacity:0.7,speed:0.9}],
        ["liquid-4","Água","Lava Fluida","Placas escuras separadas por veios incandescentes móveis.","#ff4b18","add","lavaFluida",{radius:8,scale:1.3,opacity:0.9,intensity:0.95}],
        ["liquid-5","Água","Mercúrio","Superfície metálica com cristas especulares e interferência líquida.","#b9c5d2","screen","mercurio",{radius:0,scale:1.2,opacity:0.55,speed:0.8}],


        ["weather-1","Clima","Chuva Fina","Gotas delgadas e discretas inclinadas pelo vento.","#9bc9e8","screen","chuvaFina",{radius:0,scale:1.8,opacity:0.65}],
        ["weather-2","Clima","Tempestade","Chuva pesada com nuvens e clarões ocasionais.","#b6d9ef","screen","tempestade",{radius:0,scale:1.7,opacity:0.85,intensity:0.9}],
        ["weather-3","Clima","Nevasca","Flocos grandes e cruzes de gelo soprados em turbilhão.","#edf7ff","normal","nevasca",{radius:0,scale:1.9,opacity:0.8,speed:0.8}],
        ["weather-4","Clima","Cinzas","Fragmentos achatados que tombam lentamente em haze escuro.","#77736e","multiply","cinzas",{radius:0,scale:1.8,opacity:0.62,speed:0.6}],
        ["weather-5","Clima","Chuva Arcana","Traços mágicos que sobem e deixam runas efêmeras.","#b75cff","add","chuvaArcana",{radius:0,scale:1.7,opacity:0.75}],


        ["particles-1","Partículas","Vagalumes","Luzes orgânicas que vagam e piscam fora de fase.","#ffd95a","add","vagalumes",{radius:10,scale:1.2,speed:0.8}],
        ["particles-2","Partículas","Esporos","Esferas macias que sobem lentamente com halos raros.","#8dcc73","screen","esporos",{radius:10,scale:1.2,speed:0.6}],
        ["particles-3","Partículas","Faíscas","Traços balísticos com cabeça incandescente e cauda curta.","#ff8b24","add","faiscas",{radius:8,scale:1.0,speed:1.15}],
        ["particles-4","Partículas","Almas","Silhuetas espectrais flutuantes com cauda e olhos luminosos.","#55bfff","screen","almas",{radius:10,scale:1.25,speed:0.75}],
        ["particles-5","Partículas","Poeira Cósmica","Campo de estrelas com cruzes, twinkle e nébula tênue.","#a88cff","add","poeiraCosmica",{radius:0,scale:1.3,speed:0.5}],


        ["grid-1","Padrões","Grade Arcana","Malha hexagonal com nós pulsantes em vez de quadrícula simples.","#655cff","screen","gradeArcana",{radius:0,scale:1.0,opacity:0.72}],
        ["grid-2","Padrões","Holograma","Grid digital com scanline, glitches e nós luminosos.","#24d9e8","add","holograma",{radius:0,scale:1.1,opacity:0.7,speed:1.0}],
        ["grid-3","Padrões","Circuito","Trilhas ortogonais pseudoaleatórias com pads de dados.","#45e078","screen","circuito",{radius:0,scale:1.15,opacity:0.62,speed:0.65}],
        ["grid-4","Padrões","Prisão Rúnica","Anéis concêntricos, barras radiais e glifos pulsantes.","#ed3948","add","prisaoRunica",{radius:7,scale:1.0,opacity:0.82}],
        ["grid-5","Padrões","Tabuleiro Fantasma","Casas espectrais alternadas que aparecem e desaparecem lentamente.","#c4d6e8","normal","tabuleiroFantasma",{radius:0,scale:1.1,opacity:0.38,speed:0.45}],


        ["vortex-1","Vórtices","Redemoinho","Espiral aquática com espuma e anéis concêntricos.","#3b9fd1","screen","redemoinho",{radius:7,scale:1.0}],
        ["vortex-2","Vórtices","Singularidade","Buraco negro com disco de acreção e lente gravitacional.","#7038c8","add","singularidade",{radius:7,scale:1.0,opacity:0.9}],
        ["vortex-3","Vórtices","Ciclone de Areia","Coluna afunilada de areia com bandas e grãos turbulentos.","#b79058","multiply","cicloneAreia",{radius:8,scale:1.0,opacity:0.82,speed:1.0}],
        ["vortex-4","Vórtices","Tormenta Verde","Vórtice venenoso com braços grossos e eddies internos.","#4fc96b","screen","tormentaVerde",{radius:7,scale:1.0,intensity:0.9}],
        ["vortex-5","Vórtices","Galáxia","Galáxia espiral com braços, bojo central, estrelas e poeira.","#826cff","add","galaxia",{radius:8,scale:1.0,speed:0.55}],


        ["aura-1","Auras","Aura Sagrada","Halo dourado com raios externos e motes ascendentes.","#ffd86a","screen","auraSagrada",{radius:5,scale:1.0,speed:0.7}],
        ["aura-2","Auras","Aura Sombria","Contorno fumegante com tendrils púrpura-negros voltados para dentro.","#5b337e","multiply","auraSombria",{radius:5,scale:1.0,opacity:0.82}],
        ["aura-3","Auras","Escudo Arcano","Barreira hexagonal precisa com scanline, nós e anéis internos.","#438cff","add","escudoArcano",{radius:5,scale:1.0,speed:0.65}],
        ["aura-4","Auras","Veneno","Nuvem tóxica pulsante com bolhas distintas ao redor da origem.","#6fbf37","normal","veneno",{radius:5,scale:1.1,opacity:0.68,speed:0.9}],
        ["aura-5","Auras","Aura de Sangue","Halo carmesim com espinhos radiais, gotas e pulso agressivo.","#d9263c","screen","auraSangue",{radius:5,scale:1.0,intensity:0.9}],
    ];

    const EN_CATEGORY_BY_PREFIX = { orb:"Energy", portal:"Portals", fog:"Atmosphere",
        flame:"Fire", liquid:"Water", weather:"Weather", particles:"Particles",
        grid:"Patterns", vortex:"Vortices", aura:"Auras" };
    const EN_BY_ID = {
        "orb-1":["Arcane Sun","Radiant disc with a turbulent corona, long rays, and sparks."],
        "orb-2":["Solar Star","Pulsing star with two flare families and a living corona."],
        "orb-3":["Glacial Core","Hexagonal crystal with facets, spikes, and glittering frost."],
        "orb-4":["Crimson Eye","Living arcane eye with an iris, vertical pupil, and pulsing veins."],
        "orb-5":["Spectral Moon","Ghostly crescent with a halo, motes, and pale mist."],
        "portal-1":["Violet Portal","Spiralling ring with a turbulent inner surface."],
        "portal-2":["Infernal Rift","Jagged, luminous, unstable vertical tear."],
        "portal-3":["Fey Passage","A crown of petals and runes around a sparkling interior."],
        "portal-4":["Astral Void","Empty core with gravitational lensing, a disc, and stars."],
        "portal-5":["Golden Seal","Precise ritual geometry with rings, glyphs, and symmetric rays."],
        "fog-1":["Swamp Mist","Layered banks of damp mist that react to light."],
        "fog-2":["Black Smoke","Dense turbulent smoke columns that rise and curl."],
        "fog-3":["Frost Mist","Low mist with suspended ice crystals."],
        "fog-4":["Purple Miasma","Cellular toxic gas with bubbles and inner veins."],
        "fog-5":["Ancient Dust","Suspended motes, haze, and faint backlit shafts."],
        "flame-1":["Bonfire","Wide flame with irregular tongues and rising embers."],
        "flame-2":["Blue Flame","Narrow blue jet with a white core and fast oscillation."],
        "flame-3":["Green Fire","Bubbling alchemical combustion with green flames."],
        "flame-4":["Dark Ember","Dark fire pierced by coal and red ember points."],
        "flame-5":["Sacred Fire","Symmetric flame with a golden halo and rays."],
        "liquid-1":["Water Reflection","Crossed-wave caustics with small concentric ripples."],
        "liquid-2":["Ocean Abyss","Broad, crossed, deep waves with dark troughs."],
        "liquid-3":["Acid Pool","Corrosive film with cellular bubbles and bright veins."],
        "liquid-4":["Flowing Lava","Dark plates separated by moving incandescent veins."],
        "liquid-5":["Mercury","Metallic surface with specular ridges and liquid interference."],
        "weather-1":["Light Rain","Fine, subtle drops slanted by the wind."],
        "weather-2":["Storm","Heavy rain with clouds and occasional flashes."],
        "weather-3":["Blizzard","Large flakes and ice crosses blown in a swirl."],
        "weather-4":["Ashfall","Flattened fragments tumbling through dark haze."],
        "weather-5":["Arcane Rain","Magical rising streaks that leave fleeting runes."],
        "particles-1":["Fireflies","Organic lights that wander and blink out of phase."],
        "particles-2":["Spores","Soft spheres rising slowly with occasional halos."],
        "particles-3":["Sparks","Ballistic streaks with hot heads and short tails."],
        "particles-4":["Souls","Floating spectral silhouettes with tails and glowing eyes."],
        "particles-5":["Cosmic Dust","Star field with crosses, twinkle, and faint nebulae."],
        "grid-1":["Arcane Grid","Hexagonal mesh with pulsing nodes."],
        "grid-2":["Hologram","Digital grid with scanlines, glitches, and glowing nodes."],
        "grid-3":["Circuit","Pseudo-random orthogonal tracks with data pads."],
        "grid-4":["Runic Prison","Concentric rings, radial bars, and pulsing glyphs."],
        "grid-5":["Ghost Board","Spectral squares that slowly appear and disappear."],
        "vortex-1":["Whirlpool","Aquatic spiral with foam and concentric rings."],
        "vortex-2":["Singularity","Black hole with an accretion disc and gravitational lens."],
        "vortex-3":["Sand Cyclone","Tapered sand column with turbulent bands and grains."],
        "vortex-4":["Green Tempest","Poisonous vortex with thick arms and inner eddies."],
        "vortex-5":["Galaxy","Spiral galaxy with arms, central bulge, stars, and dust."],
        "aura-1":["Sacred Aura","Golden halo with outer rays and rising motes."],
        "aura-2":["Dark Aura","Smoky outline with inward purple-black tendrils."],
        "aura-3":["Arcane Shield","Precise hexagonal barrier with scanlines, nodes, and rings."],
        "aura-4":["Poison","Pulsing toxic cloud with distinct bubbles around its origin."],
        "aura-5":["Blood Aura","Crimson halo with radial spikes, drops, and an aggressive pulse."],
    };
    const useEnglish = String(globalThis.document?.documentElement?.lang || "").toLowerCase().startsWith("en");

    const presets = catalog.map(
        ([id, category, name, description, color, blend_mode, sourceKey, controls]) => ({
            ...defaults,
            ...controls,
            id,
            category: useEnglish ? (EN_CATEGORY_BY_PREFIX[id.split("-")[0]] || category) : category,
            name: useEnglish ? (EN_BY_ID[id]?.[0] || name) : name,
            description: useEnglish ? (EN_BY_ID[id]?.[1] || description) : description,
            color,
            blend_mode,
            source: sources[sourceKey],
        })
    );

    if (presets.length !== 50) {
        throw new Error(
            `Shader preset catalog expected 50 entries, got ${presets.length}`
        );
    }

    if (new Set(presets.map((p) => p.source)).size !== 50) {
        throw new Error(
            "Every Gravewright shader preset must have a unique GLSL source."
        );
    }

    if (new Set(presets.map((p) => p.id)).size !== 50) {
        throw new Error(
            "Every Gravewright shader preset must have a unique id."
        );
    }

    window.GravewrightShaderPresets = Object.freeze(
        presets.map(Object.freeze)
    );
})();
