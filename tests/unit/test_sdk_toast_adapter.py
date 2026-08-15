from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]


def test_sdk_toast_uses_the_real_toast_component_api():
    sdk = (ROOT / "static/js/sdk/gravewright-sdk.js").read_text(encoding="utf-8")
    toasts = (ROOT / "static/js/ui/toasts.js").read_text(encoding="utf-8")

    assert "window.GravewrightToasts = { showToast, dismissToast }" in toasts
    assert "toasts?.showToast?.(message, options)" in sdk
