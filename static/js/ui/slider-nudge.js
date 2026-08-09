(() => {













    const FINE_STEP = 0.1;

    function stepOf(input) {
        const own = Number(input.dataset?.baseStep ?? input.step);
        if (!Number.isFinite(own) || own <= 0) return FINE_STEP;


        return Math.min(own, FINE_STEP);
    }










    function prepare(input) {
        if (!input || input.dataset?.baseStep) return input;
        const own = Number(input.step);
        if (Number.isFinite(own) && own > FINE_STEP) {
            input.dataset.baseStep = input.step;
            input.step = String(FINE_STEP);
        }
        return input;
    }



    function round(value, step) {
        const decimals = String(step).includes(".") ? String(step).split(".")[1].length : 0;
        return Number(value.toFixed(decimals));
    }

    function nudge(input, direction) {
        if (!input || input.disabled) return null;
        const step = stepOf(input);
        const min = Number.isFinite(Number(input.min)) ? Number(input.min) : -Infinity;
        const max = Number.isFinite(Number(input.max)) ? Number(input.max) : Infinity;
        const next = Math.min(max, Math.max(min, round(Number(input.value) + direction * step, step)));
        if (next === Number(input.value)) return null;
        input.value = String(next);


        input.dispatchEvent(new Event("input", { bubbles: true }));
        input.dispatchEvent(new Event("change", { bubbles: true }));
        return next;
    }

    function button(direction) {
        const element = document.createElement("button");
        element.type = "button";
        element.className = "slider-nudge";
        element.dataset.sliderNudge = direction > 0 ? "up" : "down";
        element.tabIndex = -1;
        element.setAttribute("aria-hidden", "true");
        element.textContent = direction > 0 ? "+" : "−";
        return element;
    }


    function decorate(root = document) {
        root.querySelectorAll?.(".slider-row").forEach((row) => {
            if (row.dataset.nudged === "true") return;
            const input = row.querySelector('input[type="range"]');
            if (!input) return;
            row.dataset.nudged = "true";
            prepare(input);
            row.insertBefore(button(-1), input);
            const output = row.querySelector("output");
            row.insertBefore(button(1), output || null);
        });
    }

    document.addEventListener("click", (event) => {
        const pressed = event.target.closest?.("[data-slider-nudge]");
        if (!pressed) return;
        event.preventDefault();
        nudge(pressed.closest(".slider-row")?.querySelector('input[type="range"]'),
              pressed.dataset.sliderNudge === "up" ? 1 : -1);
    });

    if (document.readyState === "loading") {
        document.addEventListener("DOMContentLoaded", () => decorate());
    } else {
        decorate();
    }





    if (typeof MutationObserver === "function") {
        new MutationObserver((records) => {
            records.forEach((record) => {
                record.addedNodes.forEach((node) => {
                    if (node.nodeType !== 1) return;
                    if (node.matches?.(".slider-row") || node.querySelector?.(".slider-row")) {
                        decorate(node.matches?.(".slider-row") ? node.parentNode || document : node);
                    }
                });
            });
        }).observe(document.documentElement, { childList: true, subtree: true });
    }

    window.GravewrightSliderNudge = { decorate, nudge, stepOf, prepare };
})();
