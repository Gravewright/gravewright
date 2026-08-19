/* Core Input Runtime: binding resolution, typing suppression, rebind, disposal. */
const fs=require("fs"),vm=require("vm"),assert=require("assert");
const listeners=new Map();let active=null;
const invocations=[];
const element=(matches,contentEditable=false)=>({matches:selector=>matches,isContentEditable:contentEditable});
const document={activeElement:null,getElementById:()=>({textContent:JSON.stringify({inputBindings:[{package_id:"seeded",command_id:"preset",binding:"Alt+B"}]})}),addEventListener:(n,f)=>listeners.set(n,f)};
const sandbox={console,document,performance:{now:()=>0},window:{},addEventListener:(n,f)=>listeners.set(n,f)};
vm.createContext(sandbox);
vm.runInContext(fs.readFileSync("static/js/input/core-input-runtime.js","utf8"),sandbox);
const api=sandbox.window.GravewrightInputRuntime;
const key=value=>({ctrlKey:false,altKey:false,shiftKey:false,metaKey:false,repeat:false,preventDefault(){},...value});

// Bindings persisted for the session are seeded from the game context, not guessed.
const seeded=[];api.registerCommand("seeded",{id:"preset",defaultBindings:["Alt+Z"]},value=>seeded.push(value));
listeners.get("keydown")(key({key:"z",altKey:true}));
assert.equal(seeded.length,0,"a stored binding replaces the default, it does not add to it");
listeners.get("keydown")(key({key:"b",altKey:true}));
assert.equal(seeded.length,1,"the stored binding invokes the command");

// A default binding invokes exactly once and carries semantic metadata only.
const dispose=api.registerCommand("pkg",{id:"open-operations",defaultBindings:["Alt+O"]},value=>invocations.push(value));
listeners.get("keydown")(key({key:"o",altKey:true}));
assert.equal(invocations.length,1);
assert.deepEqual(Object.keys(invocations[0]).sort(),["binding","commandId","context","packageId","source"]);
assert.equal(invocations[0].commandId,"open-operations");
assert.equal(invocations[0].packageId,"pkg");
assert.equal(invocations[0].binding,"Alt+O");
assert.equal(invocations[0].source,"binding");
assert(!("key" in invocations[0])&&!("target" in invocations[0]),"no raw browser event reaches the package");

// Auto-repeat is one physical press.
listeners.get("keydown")(key({key:"o",altKey:true,repeat:true}));
assert.equal(invocations.length,1,"a held key must not re-invoke the command");

// A different key does nothing.
listeners.get("keydown")(key({key:"p",altKey:true}));
assert.equal(invocations.length,1);

// Typing suppression is core-owned: the package filters nothing itself.
document.activeElement=element(true);
listeners.get("keydown")(key({key:"o",altKey:true}));
assert.equal(invocations.length,1,"a global command must not fire while typing");
document.activeElement=element(false,true);
listeners.get("keydown")(key({key:"o",altKey:true}));
assert.equal(invocations.length,1,"contenteditable suppresses just like an input");
document.activeElement=null;
listeners.get("keydown")(key({key:"o",altKey:true}));
assert.equal(invocations.length,2,"leaving the field restores the command");

// A command that opts in still fires while typing; one that opts out never does.
const typed=[],excluded=[];
api.registerCommand("pkg",{id:"in-text",contexts:["text-input"],defaultBindings:["Alt+T"]},value=>typed.push(value));
api.registerCommand("pkg",{id:"never-text",contexts:["text-input","text-input-excluded"],defaultBindings:["Alt+E"]},value=>excluded.push(value));
document.activeElement=element(true);
listeners.get("keydown")(key({key:"t",altKey:true}));
listeners.get("keydown")(key({key:"e",altKey:true}));
assert.equal(typed.length,1,"an explicit text-input context allows invocation");
assert.equal(excluded.length,0,"text-input-excluded always wins");
document.activeElement=null;

// Hot rebind: the old binding goes inert and the new one works with no reload.
api.updateBinding("pkg","open-operations","Alt+K");
listeners.get("keydown")(key({key:"o",altKey:true}));
assert.equal(invocations.length,2,"the previous binding stops immediately");
listeners.get("keydown")(key({key:"k",altKey:true}));
assert.equal(invocations.length,3,"the new binding works immediately");
assert.equal(invocations[2].binding,"Alt+K");

// Modifiers are part of the binding identity.
listeners.get("keydown")(key({key:"k",altKey:true,shiftKey:true}));
assert.equal(invocations.length,3,"Alt+Shift+K is not Alt+K");

// Disposal removes the command; no zombie listener is left behind.
const listenerCount=listeners.size;
dispose();
listeners.get("keydown")(key({key:"k",altKey:true}));
assert.equal(invocations.length,3,"a disposed command no longer runs");
assert.equal(listeners.size,listenerCount,"disposal adds and removes no global listeners");
dispose();
assert.equal(invocations.length,3,"disposing twice is harmless");

// Only one command runs per press, even when two share a binding.
const first=[],second=[];
api.registerCommand("a",{id:"one",defaultBindings:["Alt+M"]},value=>first.push(value));
api.registerCommand("b",{id:"two",defaultBindings:["Alt+M"]},value=>second.push(value));
listeners.get("keydown")(key({key:"m",altKey:true}));
assert.equal(first.length+second.length,1,"exactly one command may claim a press");

// Gestures carry the same semantic shape and never a pointer event.
const gestures=[];
api.registerGesture("pkg",{id:"sweep",gesture:"tap",commandId:"open-operations"},value=>gestures.push(value));
listeners.get("pointerdown")({pointerId:1,clientX:0,clientY:0,pointerType:"touch"});
listeners.get("pointerup")({pointerId:1,clientX:0,clientY:0,pointerType:"touch"});
assert.equal(gestures.length,1);
assert.equal(gestures[0].commandId,"open-operations");
assert.equal(gestures[0].packageId,"pkg");
assert.equal(gestures[0].source,"gesture");
assert.equal(gestures[0].gesture,"tap");

void active;
console.log("input command runtime harness: ok");
