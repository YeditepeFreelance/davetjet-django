// static/scripts/utils/cooldown.js
// Basit, kalıcı (localStorage) cooldown yöneticisi + buton geri sayımı.

(function () {
  "use strict";
  if (window.Cooldown) return;

  const LS_KEY = "dj:cooldown:v1";
  function load() {
    try {
      return JSON.parse(localStorage.getItem(LS_KEY)) || {};
    } catch {
      return {};
    }
  }
  function save(db) {
    try {
      localStorage.setItem(LS_KEY, JSON.stringify(db));
    } catch {}
  }
  let db = load();

  const now = () => Date.now();
  const remaining = (key) => Math.max(0, (db[key] || 0) - now());
  const isCooling = (key) => remaining(key) > 0;
  const set = (key, ms) => {
    db[key] = now() + Math.max(0, ms | 0);
    save(db);
  };
  const clear = (key) => {
    delete db[key];
    save(db);
  };

  function toastOnce(level, msg, opts) {
    if (typeof window.toast !== "function") return;
    const k = `cd:${level}:${msg}`;
    window.__CD_SEEN__ = window.__CD_SEEN__ || new Set();
    if (window.__CD_SEEN__.has(k)) return;
    window.__CD_SEEN__.add(k);
    (toast[level] || toast.info)(
      String(msg || ""),
      Object.assign({ duration: 3000 }, opts || {})
    );
    setTimeout(() => window.__CD_SEEN__.delete(k), 4000);
  }

  // Bir işi cooldown ile sarmalar
  function guard(key, ms, run) {
    return async function (...args) {
      const left = remaining(key);
      if (left > 0) {
        toastOnce("warning", `Lütfen bekleyin: ${Math.ceil(left / 1000)} sn`);
        const err = new Error("cooldown");
        err.cooldown = true;
        err.remaining = left;
        throw err;
      }
      set(key, ms);
      return run.apply(this, args);
    };
  }

  // Buton üstünde geri sayım gösterir
  function bindButtonCountdown(
    btn,
    key,
    { text = "Gönder", whileText, disable = true } = {}
  ) {
    let iv = null;
    const baseText = btn.textContent;
    function tick() {
      const left = remaining(key);
      if (left > 0) {
        if (disable) btn.disabled = true;
        const sec = Math.ceil(left / 1000);
        btn.textContent = whileText
          ? whileText.replace("%s", sec)
          : `${sec} sn`;
      } else {
        if (disable) btn.disabled = false;
        btn.textContent = text || baseText;
        stop();
      }
    }
    function start() {
      stop();
      tick();
      iv = setInterval(tick, 1000);
    }
    function stop() {
      if (iv) {
        clearInterval(iv);
        iv = null;
      }
    }
    return { start, stop, tick };
  }

  // Retry-After: "120" saniye veya HTTP tarih
  function parseRetryAfter(v) {
    if (!v) return null;
    const n = parseInt(v, 10);
    if (!Number.isNaN(n)) return n * 1000;
    const t = Date.parse(v);
    return Number.isNaN(t) ? null : Math.max(0, t - now());
  }

  window.Cooldown = {
    set,
    clear,
    remaining,
    isCooling,
    guard,
    bindButtonCountdown,
    parseRetryAfter,
  };
})();
