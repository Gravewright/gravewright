window.GravewrightSDK.register({
  id: "user-presentation-reader",
  async ready(sdk) {
    await sdk.users.presentation.list();
  },
});
