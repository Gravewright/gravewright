import { ModuleError } from './lifetime.js';

let modalHost;
const mounted = new WeakSet();

// The browser entry point injects the native component. Keeping the adapter
// independent of /static URLs also permits isolated SDK tests without a DOM.
export function setModalHost(mountModal, document) {
  modalHost = { mountModal, document };
}

export function createUiApi(life, ui = {}, host) {
  return Object.freeze({
    ...ui,
    openModal(element, options = {}) {
      life.check();
      const { mountModal, document } = host ?? modalHost ?? {};
      if (typeof mountModal !== 'function' || !document) throw new ModuleError('unavailable');
      if (!element || element.ownerDocument !== document ||
          !(element instanceof document.defaultView.Element) ||
          !['section', 'div', 'form'].includes(element.localName) ||
          options === null || typeof options !== 'object' || Array.isArray(options) ||
          (options.nested !== undefined && typeof options.nested !== 'boolean') ||
          (options.canClose !== undefined && typeof options.canClose !== 'function')) {
        throw new ModuleError('invalid_data', 'A modal requires a section, div or form from this document.');
      }
      if (mounted.has(element)) throw new ModuleError('conflict', 'This modal is already mounted.');
      const { nested = true, canClose = () => true } = options;
      element.classList.add('table-modal-window');
      mounted.add(element);
      let release = () => {}, closed = false;
      const onClose = () => {
        closed = true;
        mounted.delete(element);
        release();
        element.removeEventListener('close', onClose);
      };
      element.addEventListener('close', onClose);
      try {
        mountModal(element, { nested, canClose: () => !life.signal.aborted && canClose() });
        life.check();
        if (!closed) release = life.link(() => element.close(true));
        return element;
      } catch (error) {
        onClose();
        element.close?.(true);
        throw error;
      }
    },
  });
}
