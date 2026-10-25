/** Parameters accepted by the native shader validator; authored GLSL stays in its editor. */
export const shaderProperties = Object.freeze({
    enabled:{label:'Enabled',type:'boolean',value:true}, color:{label:'Color',type:'text',value:'#ffffff'},
    intensity:{label:'Intensity',type:'number',min:0,max:1,value:1}, opacity:{label:'Opacity',type:'number',min:0,max:1,value:1},
    speed:{label:'Speed',type:'number',min:0,max:8,value:1}, scale:{label:'Scale',type:'number',min:.1,max:20,value:1},
    radius:{label:'Radius',type:'number',min:0,max:1000000,value:0}, rotation:{label:'Rotation',type:'number',min:-36000,max:36000,value:0},
    light_response:{label:'Light response',type:'number',min:0,max:1,value:0}, light_emission:{label:'Light emission',type:'number',min:0,max:2,value:0},
});
export function validateShaderValue(property,value){
    const field=Object.hasOwn(shaderProperties,property)?shaderProperties[property]:undefined;
    if(!field || field.type==='boolean'&&typeof value!=='boolean'
        || field.type==='text'&&(typeof value!=='string'||!/^#[0-9a-f]{6}$/i.test(value))
        || field.type==='number'&&(typeof value!=='number'||!Number.isFinite(value)||value<field.min||value>field.max))throw Error('Invalid shader control value.');
    return value;
}
