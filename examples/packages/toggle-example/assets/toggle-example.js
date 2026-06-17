window.GravewrightSDK.register({
  id: "toggle-example",
  ready(sdk) {
    if (sdk.setting("enabled") !== false) {
      sdk.toast("Toggle Example enabled");
    }
  },
});
