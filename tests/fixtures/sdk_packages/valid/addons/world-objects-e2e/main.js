(() => {
  window.GravewrightSDK.register({
    id: "world-objects-e2e",
    async ready(sdk) {
      await sdk.scene.objectTypes.register({
        typeId: "world-objects-e2e.lever", schemaVersion: 1, displayName: "Lever",
        dataSchema: {type: "object"}, geometryKinds: ["point"],
        visualDefinition: [{kind: "icon"}, {kind: "label"}],
        interactionDefinitions: [{id: "activate", label: "Activate"}],
        editorDefinition: {movable: true}, searchableFields: ["label"],
      });
      sdk.ui.slots.register("dock.actions", host => {
        const root=document.createElement("section");root.dataset.testid="world-objects-controls";
        const recipient=document.createElement("input");recipient.dataset.testid="world-objects-recipient";
        const create=document.createElement("button");create.type="button";create.dataset.testid="world-objects-create-object";create.textContent="Place lever";
        const show=document.createElement("button");show.type="button";show.dataset.testid="world-objects-show-title";show.textContent="Show title";
        const status=document.createElement("output");status.dataset.testid="world-objects-status";
        create.addEventListener("click",async()=>{const made=await sdk.scene.objects.create(sdk.game.scene().id,{typeId:"world-objects-e2e.lever",geometry:{kind:"point",x:350,y:350},presentation:{icon:"⚙",label:"Crypt lever"},data:{label:"Crypt lever"},audience:{kind:"campaign"}});status.textContent=`created:${made.id}`;});
        show.addEventListener("click",async()=>{const made=await sdk.ui.presentations.show({mode:"title-card",content:{title:"THE CRYPT",subtitle:"Below"},audience:{kind:"users",ids:[recipient.value]},duration:6,sceneId:sdk.game.scene().id});status.textContent=`shown:${made.id}`;});
        sdk.events.on("scene.object.interacted",event=>{status.textContent=`interacted:${event.resourceId}`;});
        root.append(recipient,create,show,status);host.append(root);
      });
    },
  });
})();
