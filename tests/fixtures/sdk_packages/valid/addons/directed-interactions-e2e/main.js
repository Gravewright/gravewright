(() => {
  window.GravewrightSDK.register({
    id: "directed-interactions-e2e",
    ready(sdk) {
      let currentId = "";
      const refresh = async (status) => {
        if (!currentId) return;
        const interaction = await sdk.interactions.get(currentId);
        status.textContent = JSON.stringify({
          id: interaction.id,
          title: interaction.prompt.title,
          status: interaction.status,
          responders: Object.keys(interaction.responses),
          responses: interaction.responses,
        });
      };
      sdk.ui.slots.register("dock.actions", (host) => {
        const root = document.createElement("section");
        root.dataset.testid = "directed-interactions-e2e-controls";
        const recipient = document.createElement("input");
        recipient.dataset.testid = "directed-interactions-recipient";
        recipient.setAttribute("aria-label", "Directed interaction recipient");
        const title = document.createElement("input");
        title.dataset.testid = "directed-interactions-title";
        title.setAttribute("aria-label", "Directed interaction title");
        const prompt = document.createElement("input");
        prompt.dataset.testid = "directed-interactions-prompt";
        prompt.setAttribute("aria-label", "Directed interaction prompt");
        const create = document.createElement("button");
        create.type = "button";
        create.dataset.testid = "directed-interactions-create";
        create.textContent = "Create directed interaction";
        const status = document.createElement("output");
        status.dataset.testid = "directed-interactions-state";
        create.addEventListener("click", async () => {
          const interaction = await sdk.interactions.request({
            kind: "e2e",
            recipients: [recipient.value],
            title: title.value,
            text: prompt.value,
            responseSchema: {type: "boolean"},
            deadline: Math.floor(Date.now() / 1000) + 120,
          });
          currentId = interaction.id;
          await refresh(status);
        });
        sdk.events.on("interaction.changed", () => void refresh(status));
        root.append(recipient, title, prompt, create, status);
        host.append(root);
      });
    },
  });
})();
