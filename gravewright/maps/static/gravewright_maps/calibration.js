import {
  calculateCalibration,
  calibrationSettings,
} from "./calibration-model.js";
export function calibrate(surface, board, map, imageScale, done) {
  const root = document
      .getElementById("map-calibration")
      .content.firstElementChild.cloneNode(true),
    svg = root.querySelector("svg"),
    panel = root.querySelector("section");
  surface.append(svg);
  document.body.append(panel);
  let samples = [],
    draft,
    drawing,
    result,
    closed = false;
  const node = (tag, attrs = {}) => {
    const el = document.createElementNS("http://www.w3.org/2000/svg", tag);
    for (const [key, value] of Object.entries(attrs))
      el.setAttribute(key, value);
    return el;
  };
  const point = (e) => {
    const r = surface.getBoundingClientRect(),
      v = board.viewport();
    return {
      x: (e.clientX - r.left - v.x) / v.scale,
      y: (e.clientY - r.top - v.y) / v.scale,
    };
  };
  function paint() {
    const v = board.viewport(),
      g = svg.querySelector("g");
    g.replaceChildren();
    g.setAttribute("transform", `translate(${v.x} ${v.y}) scale(${v.scale})`);
    result = undefined;
    let error = "";
    if (samples.length === 3)
      try {
        result = calculateCalibration(samples);
      } catch (e) {
        error = e.message;
      }
    if (result) {
      const paths = [],
        stride =
          Math.max(
            1,
            Math.ceil(Math.max(map.width, map.height) / result.size / 1000),
          ) * result.size;
      for (let x = result.offsetX; x <= map.width; x += stride)
        paths.push(`M${x} 0V${map.height}`);
      for (let y = result.offsetY; y <= map.height; y += stride)
        paths.push(`M0 ${y}H${map.width}`);
      g.append(
        node("path", {
          d: paths.join(" "),
          class: "grid-calibration__preview",
          "vector-effect": "non-scaling-stroke",
        }),
      );
    }
    for (const [i, s] of [...samples, ...(draft ? [draft] : [])].entries()) {
      g.append(
        node("rect", {
          ...s,
          class: "grid-calibration__sample",
          "vector-effect": "non-scaling-stroke",
        }),
      );
      const text = node("text", {
        x: s.x + 5 / v.scale,
        y: s.y + 16 / v.scale,
        "font-size": 13 / v.scale,
      });
      text.textContent = i + 1;
      g.append(text);
    }
    panel.querySelector("header b").textContent = `${samples.length} / 3`;
    panel.querySelector("[aria-live]").textContent =
      samples.length === 3
        ? "Check the preview alignment over the map."
        : [
            "Outline a cell near the top-left corner.",
            "Outline a cell near the center of the map.",
            "Outline a cell near the bottom-right corner.",
          ][samples.length];
    for (const [i, step] of [...panel.querySelectorAll("i")].entries())
      step.classList.toggle(
        "grid-calibration-panel__step--done",
        samples.length > i,
      );
    panel.querySelector("[data-calibration=undo]").disabled = !samples.length;
    panel.querySelector("[data-calibration=apply]").disabled = !result;
    panel.querySelector(".grid-calibration-panel__error").hidden = !error;
    panel.querySelector(".grid-calibration-panel__error").textContent = error;
    panel.querySelector(".grid-calibration-panel__result").hidden = !result;
    if (result) {
      panel.querySelector("[data-cell]").textContent =
        (result.size / imageScale).toFixed(4).replace(/\.?0+$/, "") + " px";
      panel.querySelector("[data-origin]").textContent =
        `${(result.offsetX / imageScale).toFixed(2)}, ${(result.offsetY / imageScale).toFixed(2)}`;
    }
  }
  svg.onpointerdown = (e) => {
    if (e.button !== 0) return;
    e.stopPropagation();
    e.preventDefault();
    if (samples.length === 3) return;
    const p = point(e);
    if (p.x < 0 || p.y < 0 || p.x > map.width || p.y > map.height) return;
    drawing = { id: e.pointerId, ...p };
    svg.setPointerCapture(e.pointerId);
    draft = { ...p, width: 0, height: 0 };
    paint();
  };
  svg.onpointermove = (e) => {
    if (!drawing || drawing.id !== e.pointerId) return;
    e.stopPropagation();
    const p = point(e);
    p.x = Math.max(0, Math.min(map.width, p.x));
    p.y = Math.max(0, Math.min(map.height, p.y));
    draft = {
      x: Math.min(p.x, drawing.x),
      y: Math.min(p.y, drawing.y),
      width: Math.abs(p.x - drawing.x),
      height: Math.abs(p.y - drawing.y),
    };
    paint();
  };
  const up = (e) => {
    if (!drawing || drawing.id !== e.pointerId) return;
    e.stopPropagation();
    if (e.type !== "pointercancel" && draft?.width >= 8 && draft?.height >= 8)
      samples.push(draft);
    drawing = undefined;
    draft = undefined;
    if (svg.hasPointerCapture(e.pointerId))
      svg.releasePointerCapture(e.pointerId);
    paint();
  };
  svg.onpointerup = up;
  svg.onpointercancel = up;
  const close = (value) => {
    if (closed) return;
    closed = true;
    svg.remove();
    panel.remove();
    window.removeEventListener("gravewright:map-viewport", paint);
    window.removeEventListener("keydown", escape, true);
    done(value);
  };
  const escape = (e) => {
    if (e.key === "Escape") {
      e.stopImmediatePropagation();
      e.preventDefault();
      close();
    }
  };
  for (const button of panel.querySelectorAll("[data-calibration]"))
    button.onclick = () => {
      if (button.dataset.calibration === "undo") {
        samples.pop();
        paint();
      } else
        close(
          button.dataset.calibration === "apply" && result
            ? calibrationSettings(result, imageScale)
            : undefined,
        );
    };
  window.addEventListener("keydown", escape, true);
  window.addEventListener("gravewright:map-viewport", paint);
  paint();
  return () => close();
}
