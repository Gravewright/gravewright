(() => {
  let dispose = () => {};
  window.GravewrightSDK.register({
    id: "minimal-addon",
    setup(sdk) {
      dispose = sdk.events.on("scene.updated", () => sdk.ui.toast("Scene updated"));
    },
    unload() { dispose(); },
  });
})();
