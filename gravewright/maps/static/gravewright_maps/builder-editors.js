// gravewright/maps/frontend/native/builder-editors.js
import LightEditor from "./runtime/features/lighting/ui/LightEditor.native.js";
import EffectEditor from "./runtime/features/effects/ui/EffectEditor.native.js";
import { ShaderDraftValidator } from "./runtime/features/effects/model/shader-validation.js";
import { text as gwText } from "./runtime/shared/config/i18n/text.js";
import { builderNativeDraft, builderNativeItem } from "./runtime/native/builder-editor-model.js";
import { mountModal } from "/static/gravewright_table/modal.js";
function openBuilderNativeEditor({ kind, item, onSave, onPreview, onClose, t = gwText }) {
  const original = structuredClone(item);
  let draft = builderNativeDraft(kind, original), closed = false, busy = false, previewTimer, validator;
  const wrapper = document.createElement("section");
  wrapper.className = "table-modal-window map-builder-native-editor";
  wrapper.dataset.builderNativeEditor = kind;
  wrapper.setAttribute("aria-label", t({ lights: "Light source", particles: "Particles", shaders: "Scene shader" }[kind]));
  const host = document.createElement("div");
  host.className = "map-builder-native-editor__host";
  wrapper.append(host);
  const widget = kind === "lights" ? LightEditor : EffectEditor;
  const editor = widget(host, { props: { modelValue: draft, kind: kind.slice(0, -1), existing: true, transactional: true, busy: false, error: "" }, emit });
  function issue(error) {
    if (!closed) editor.update({ error: t(error?.message || "Could not save the change.") });
  }
  function candidate() {
    const next = builderNativeItem(kind, original, draft);
    if (kind === "shaders") {
      validator ??= new ShaderDraftValidator();
      const error = validator.validate(draft.source);
      if (error) throw new Error(error);
    }
    return next;
  }
  function preview() {
    clearTimeout(previewTimer);
    if (closed || busy || !onPreview) return;
    previewTimer = setTimeout(() => {
      if (closed || busy) return;
      try {
        const next = candidate();
        editor.update({ error: "" });
        Promise.resolve(onPreview(next)).catch(issue);
      } catch (error) {
        issue(error);
      }
    }, kind === "shaders" ? 250 : 50);
  }
  async function save() {
    if (closed || busy) return;
    clearTimeout(previewTimer);
    let next;
    try {
      next = candidate();
    } catch (error) {
      issue(error);
      return;
    }
    busy = true;
    editor.update({ busy: true, error: "" });
    try {
      await onSave(next);
      if (!closed) wrapper.close(true);
    } catch (error) {
      busy = false;
      if (!closed) {
        editor.update({ busy: false });
        issue(error);
      }
    }
  }
  function emit(type, value) {
    if (closed || busy) return;
    if (type === "update:modelValue") draft = value;
    else if (type === "change") {
      if (kind === "lights" && draft.dim_radius > 0) draft.dim_radius = Math.max(draft.dim_radius, draft.bright_radius);
      preview();
    } else if (type === "save") void save();
    else if (type === "close") wrapper.close();
  }
  wrapper.addEventListener("close", () => {
    if (closed) return;
    closed = true;
    clearTimeout(previewTimer);
    validator?.dispose();
    editor.destroy();
    try {
      Promise.resolve(onPreview?.(null)).catch(() => {
      });
    } finally {
      onClose?.();
    }
  }, { once: true });
  mountModal(wrapper, { canClose: () => !busy });
  return { close(force = false) {
    if (!closed && (!busy || force)) wrapper.close(force);
  } };
}
export {
  openBuilderNativeEditor
};
