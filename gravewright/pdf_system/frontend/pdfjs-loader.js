let cached;
export function loadPdfjs(url) {
    if (!cached) {
        cached = import(/* @vite-ignore */ url('vendor/pdf.mjs')).then((lib) => {
            lib.GlobalWorkerOptions.workerSrc = url('vendor/pdf.worker.mjs');
            return lib;
        }).catch(error => { cached = undefined; throw error; });
    }
    return cached;
}
