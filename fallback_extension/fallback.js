// NFA Fallback Autofill - loaded only when Python automation fails
(() => {
  if (window.nfaFallback) {
    console.info("[nfaFallback] already initialized");
    return;
  }

  const OVERLAY_TTL_MS = 1500;
  const EVENT_TYPES = ["focus", "input", "change", "blur"];

  const log = (...args) => console.info("[nfaFallback]", ...args);
  const warn = (...args) => console.warn("[nfaFallback]", ...args);

  function createOverlay(target, color = "#00c853") {
    try {
      const rect = target.getBoundingClientRect();
      const overlay = document.createElement("div");
      overlay.style.position = "fixed";
      overlay.style.pointerEvents = "none";
      overlay.style.border = `2px solid ${color}`;
      overlay.style.borderRadius = "4px";
      overlay.style.background = `${color}22`;
      overlay.style.zIndex = "999999";
      overlay.style.left = `${rect.left + window.scrollX}px`;
      overlay.style.top = `${rect.top + window.scrollY}px`;
      overlay.style.width = `${rect.width}px`;
      overlay.style.height = `${rect.height}px`;
      document.body.appendChild(overlay);
      setTimeout(() => overlay.remove(), OVERLAY_TTL_MS);
    } catch (err) {
      warn("overlay error", err);
    }
  }

  function dispatchAll(el) {
    EVENT_TYPES.forEach((type) => {
      el.dispatchEvent(new Event(type, { bubbles: true, cancelable: true }));
    });
  }

  function findInDocument(doc, selector) {
    try {
      const direct = doc.querySelector(selector);
      if (direct) return direct;
    } catch (err) {
      warn("selector error", selector, err);
    }

    const iframes = Array.from(doc.querySelectorAll("iframe, frame"));
    for (const frame of iframes) {
      let childDoc;
      try {
        childDoc = frame.contentDocument || frame.contentWindow?.document;
      } catch (err) {
        continue; // cross-origin
      }
      if (!childDoc) continue;
      const found = findInDocument(childDoc, selector);
      if (found) return found;
    }
    return null;
  }

  function queryDeep(selector) {
    return findInDocument(document, selector);
  }

  function fill(selector, value) {
    const el = queryDeep(selector);
    if (!el) {
      warn("element not found", selector);
      return { ok: false, selector, reason: "not_found" };
    }
    try {
      if ("value" in el) {
        el.focus();
        el.value = value;
        dispatchAll(el);
      } else {
        el.textContent = value;
      }
      createOverlay(el);
      log("filled", selector, "=>", value);
      return { ok: true, selector };
    } catch (err) {
      warn("fill error", selector, err);
      return { ok: false, selector, reason: "error", error: String(err) };
    }
  }

  async function tryFillAll(fields) {
    if (!fields || typeof fields !== "object") {
      warn("invalid fields payload", fields);
      return { ok: false, filled: [], failed: [] };
    }
    const filled = [];
    const failed = [];
    for (const [selector, value] of Object.entries(fields)) {
      const res = fill(selector, value);
      (res.ok ? filled : failed).push({ selector, value, reason: res.reason });
    }
    const ok = failed.length === 0;
    if (ok) {
      log("all fields filled via fallback");
    } else {
      warn("fallback missed fields", failed);
    }
    return { ok, filled, failed };
  }

  window.nfaFallback = {
    fill,
    queryDeep,
    tryFillAll,
  };

  log("initialized");
})();
