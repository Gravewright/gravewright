import { ModuleError } from "./lifetime.js";
let defaultLocale;
const catalogs = /* @__PURE__ */ new Map();
function render() {
  defaultLocale ??= document.documentElement.lang || "en";
  const current = [...catalogs.values()].at(-1);
  document.documentElement.lang = current?.id ?? defaultLocale;
  window.gravewrightLocale = current ?? { id: defaultLocale, messages: {} };
  window.dispatchEvent(new CustomEvent("gravewright:locale", { detail: window.gravewrightLocale }));
}
function applyLocale(life, id, messages) {
  life.check();
  if (!messages || Array.isArray(messages) || typeof messages !== "object" || !/^[a-z]{2,3}(?:-[A-Za-z0-9]{2,8})*$/.test(id)) throw new ModuleError("invalid_data");
  if (!catalogs.has(life)) life.onDispose(() => {
    catalogs.delete(life);
    render();
  });
  catalogs.delete(life);
  catalogs.set(life, { id, messages: structuredClone(messages) });
  render();
  return null;
}
export {
  applyLocale
};
