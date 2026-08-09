(() => {













    const UNLIMITED = "∞";

    const rangeFor = (panel, key) => panel?.querySelector(`[data-limit-target="${key}"]`) || null;
    const checkFor = (panel, key) => panel?.querySelector(`[data-limit-for="${key}"]`) || null;



    function paint(panel, key) {
        const range = rangeFor(panel, key);
        const check = checkFor(panel, key);
        if (!range || !check) return;
        const unlimited = Number(range.value) === 0;
        check.checked = unlimited;
        range.disabled = unlimited;
    }


    function next(panel, key) {
        const range = rangeFor(panel, key);
        const check = checkFor(panel, key);
        if (!range || !check) return null;
        if (check.checked) {
            range.value = "0";
            range.disabled = true;
            return 0;
        }
        range.disabled = false;
        if (Number(range.value) === 0) {
            range.value = String(Number(range.dataset.limitDefault || 6));
        }
        return Number(range.value);
    }



    function text(panel, key, value) {
        return checkFor(panel, key) && Number(value) === 0 ? UNLIMITED : null;
    }

    window.GravewrightLimits = { paint, next, text, UNLIMITED };
})();
