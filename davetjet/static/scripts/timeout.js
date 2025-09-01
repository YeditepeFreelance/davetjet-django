/* RequestX v1.1 — Timeout + Retry + Toast + Global Patch (güvenli) */
(function () {
  "use strict";

  const AppEvents = (window.AppEvents = window.AppEvents || new EventTarget());
  const hasToast = () => typeof window.toast === "function";
  const showToast = (type, msg, opts) => {
    if (!hasToast()) return null;
    try {
      return window.toast[type]
        ? window.toast[type](msg, opts)
        : window.toast(msg, { ...opts, type });
    } catch (_) {
      return null;
    }
  };
  const sleep = (ms) => new Promise((r) => setTimeout(r, ms));

  function parseDjMessagesFromHTML(html) {
    try {
      const doc = new DOMParser().parseFromString(html, "text/html");
      const tag = doc.getElementById("dj-messages");
      if (!tag) return [];
      const arr = JSON.parse(tag.textContent || "[]");
      return Array.isArray(arr) ? arr : [];
    } catch {
      return [];
    }
  }

  const defaults = {
    timeoutMs: 12000,
    retries: 0,
    retryOn: [408, 425, 429, 500, 502, 503, 504],
    retryBackoffBase: 450,
    slowThresholdMs: 4000,
    showSlowToast: true,
    slowToastCooldownMs: 15000, // YENİ: slow toast tekrar gösterim aralığı
    autoToastDjMessages: true,
  };

  // slow toast tekilleştirme
  let SLOW_ACTIVE = false;
  let SLOW_COOLDOWN_UNTIL = 0;

  const pending = new Map();
  let _id = 0;
  const nextId = () => (++_id).toString();

  async function fetchWithCtl(url, options, meta) {
    const id = nextId();
    const {
      timeoutMs = defaults.timeoutMs,
      retries = defaults.retries,
      retryOn = defaults.retryOn,
      retryBackoffBase = defaults.retryBackoffBase,
      slowThresholdMs = defaults.slowThresholdMs,
      showSlowToast = defaults.showSlowToast,
      slowToastCooldownMs = defaults.slowToastCooldownMs,
      label = "",
      silent = false,
      parse: parseMode,
      autoToastDjMessages = defaults.autoToastDjMessages,
    } = meta || {};

    const controller = new AbortController();
    const userSignal = options && options.signal;
    if (userSignal) {
      if (userSignal.aborted) controller.abort();
      else
        userSignal.addEventListener("abort", () => controller.abort(), {
          once: true,
        });
    }

    let slowToast = null;
    let timeoutTimer = null;
    let slowTimer = null;

    function clearTimers() {
      if (timeoutTimer) clearTimeout(timeoutTimer);
      if (slowTimer) clearTimeout(slowTimer);
      if (slowToast && slowToast.hide) slowToast.hide();
      slowToast = null;
    }

    if (timeoutMs > 0) {
      timeoutTimer = setTimeout(() => {
        try {
          controller.abort("timeout");
        } catch (_) {}
      }, timeoutMs);
    }

    // slow toast — TEKİL + COOLDOWN
    if (showSlowToast && slowThresholdMs > 0 && !silent) {
      slowTimer = setTimeout(() => {
        const now = Date.now();
        if (!SLOW_ACTIVE && now > SLOW_COOLDOWN_UNTIL) {
          SLOW_ACTIVE = true;
          slowToast = showToast(
            "info",
            (label ? `${label}: ` : "") + "Bağlantı yavaş görünüyor…",
            { duration: 0 }
          );
          SLOW_COOLDOWN_UNTIL = now + slowToastCooldownMs;
        }
      }, slowThresholdMs);
    }

    pending.set(id, { abort: () => controller.abort("manual") });

    let attempt = 0;
    let lastError;

    while (attempt <= retries) {
      try {
        const res = await fetch(url, { ...options, signal: controller.signal });

        // HTTP retry
        if (retryOn.includes(res.status) && attempt < retries) {
          const backoff = retryBackoffBase * Math.pow(2, attempt++);
          await sleep(backoff);
          continue;
        }

        clearTimers();
        SLOW_ACTIVE = false;

        if (parseMode === "json") {
          const data = await res.json().catch(() => ({}));
          if (!res.ok) {
            const msg =
              data?.message ||
              data?.detail ||
              res.statusText ||
              "İstek başarısız";
            if (!silent)
              showToast("error", (label ? `${label}: ` : "") + msg, {
                duration: 5500,
              });
            const err = new Error(msg);
            err.response = res;
            err.data = data;
            throw err;
          }
          return data;
        }

        if (parseMode === "text") {
          const text = await res.text();
          if (!res.ok) {
            if (!silent)
              showToast(
                "error",
                (label ? `${label}: ` : "") +
                  (res.statusText || "İstek başarısız"),
                { duration: 5500 }
              );
            const err = new Error(res.statusText || "HTTP Error");
            err.response = res;
            err.text = text;
            throw err;
          }
          if (autoToastDjMessages && !silent) {
            parseDjMessagesFromHTML(text).forEach((m) => {
              const lvl = (m.level || "info").toLowerCase();
              showToast(lvl, m.message || "", { duration: 5000 });
            });
          }
          return text;
        }

        if (parseMode === "html") {
          const text = await res.text();
          const doc = new DOMParser().parseFromString(text, "text/html");
          if (!res.ok) {
            if (!silent)
              showToast(
                "error",
                (label ? `${label}: ` : "") +
                  (res.statusText || "İstek başarısız"),
                { duration: 5500 }
              );
            const err = new Error(res.statusText || "HTTP Error");
            err.response = res;
            err.doc = doc;
            err.html = text;
            throw err;
          }
          if (autoToastDjMessages && !silent) {
            parseDjMessagesFromHTML(text).forEach((m) => {
              const lvl = (m.level || "info").toLowerCase();
              showToast(lvl, m.message || "", { duration: 5000 });
            });
          }
          return doc;
        }

        // raw Response
        if (!res.ok && !silent) {
          showToast(
            "error",
            (label ? `${label}: ` : "") +
              (res.statusText || `HTTP ${res.status}`),
            { duration: 5500 }
          );
        }
        return res;
      } catch (err) {
        lastError = err;
        const aborted = err?.name === "AbortError";
        const timeout = aborted && controller.signal.reason === "timeout";

        if (timeout) {
          clearTimers();
          SLOW_ACTIVE = false;
          if (!silent)
            showToast(
              "error",
              (label ? `${label}: ` : "") +
                `Zaman aşımı (${Math.round(timeoutMs / 1000)} sn)`,
              { duration: 6000 }
            );
          AppEvents.dispatchEvent(
            new CustomEvent("request:timeout", {
              detail: { url, timeoutMs, label },
            })
          );
          throw err;
        }
        if (aborted && controller.signal.reason === "manual") {
          clearTimers();
          SLOW_ACTIVE = false;
          throw err;
        }

        if (attempt < retries) {
          const backoff = retryBackoffBase * Math.pow(2, attempt++);
          await sleep(backoff);
          continue;
        }
        clearTimers();
        SLOW_ACTIVE = false;
        if (!silent)
          showToast(
            "error",
            (label ? `${label}: ` : "") + "Ağ hatası. Lütfen tekrar deneyin.",
            { duration: 6000 }
          );
        throw err;
      }
    }
    throw lastError || new Error("Bilinmeyen hata");
  }

  // ---- Global patch (güvenli) ----
  let globalPatched = false;
  let globalDefaultsForPatch = { silent: true, showSlowToast: false }; // YENİ

  function isStaticAsset(pathname) {
    return /\.(css|js|png|jpg|jpeg|gif|svg|ico|webp|woff2?|ttf|map)$/i.test(
      pathname
    );
  }

  const RequestX = {
    setDefaults(partial) {
      Object.assign(defaults, partial || {});
    },
    fetch(url, fetchOpts = {}, meta = {}) {
      return fetchWithCtl(url, fetchOpts, meta);
    },
    withTimeout(
      promise,
      { timeoutMs = defaults.timeoutMs, label = "", silent = false } = {}
    ) {
      let to;
      return new Promise((resolve, reject) => {
        to = setTimeout(() => {
          if (!silent)
            showToast(
              "error",
              (label ? `${label}: ` : "") +
                `Zaman aşımı (${Math.round(timeoutMs / 1000)} sn)`,
              { duration: 6000 }
            );
          AppEvents.dispatchEvent(
            new CustomEvent("request:timeout", { detail: { label, timeoutMs } })
          );
          reject(new Error("timeout"));
        }, timeoutMs);
        promise
          .then((v) => {
            clearTimeout(to);
            resolve(v);
          })
          .catch((e) => {
            clearTimeout(to);
            reject(e);
          });
      });
    },
    enableGlobalPatch(opts = {}) {
      if (globalPatched || !window.fetch) return;
      const _fetch = window.fetch.bind(window);
      window.__nativeFetch = _fetch;

      const { defaultMeta = {}, filter } = opts;
      globalDefaultsForPatch = { ...globalDefaultsForPatch, ...defaultMeta };

      window.fetch = function (input, init = {}) {
        const url =
          typeof input === "string" ? input : (input && input.url) || "";
        const u = new URL(url, location.origin);

        // Varsayılan BYPASS: cross-origin veya statik asset
        let bypass = u.origin !== location.origin || isStaticAsset(u.pathname);
        let metaOverride = null;

        if (typeof filter === "function") {
          try {
            const res = filter(url, init, u);
            if (res === false) bypass = true;
            else if (res && typeof res === "object") {
              bypass = false;
              metaOverride = res;
            }
          } catch (_) {}
        } else {
          // Otomatik allowlist: sadece /api/ altında patch’le
          if (!/^\/api\//.test(u.pathname)) bypass = true;
        }

        if (bypass) return _fetch(input, init);

        // Header tabanlı ipuçları
        const hdrs = new Headers(init.headers || {});
        const labelHdr = hdrs.get("X-RequestX-Label");
        const verboseHdr = hdrs.get("X-RequestX-Verbose");
        const slowHdr = hdrs.get("X-RequestX-Slow");

        const meta = {
          ...globalDefaultsForPatch, // sessiz default
          ...(metaOverride || {}),
        };
        if (labelHdr) meta.label = labelHdr;
        if (verboseHdr) meta.silent = false;
        if (slowHdr)
          meta.showSlowToast = !(slowHdr === "0" || slowHdr === "false");

        return fetchWithCtl(url, init, meta);
      };

      globalPatched = true;
    },
    disableGlobalPatch() {
      if (globalPatched && window.__nativeFetch) {
        window.fetch = window.__nativeFetch;
        delete window.__nativeFetch;
        globalPatched = false;
      }
    },
  };

  window.RequestX = RequestX;
})();

RequestX.enableGlobalPatch({
  defaultMeta: {
    silent: true,
    showSlowToast: false,
    timeoutMs: 15000,
    retries: 1,
  },
  filter: (url, init, u) => {
    // cross-origin & statik dosyaları BYPASS
    if (u.origin !== location.origin) return false;
    if (!/^\/api\//.test(u.pathname)) return false;
    if (
      /\.(css|js|png|jpg|jpeg|gif|svg|ico|webp|woff2?|ttf|map)$/i.test(
        u.pathname
      )
    )
      return false;
    // /api/ istekleri için patch aktif ama sessiz
    return { silent: true, showSlowToast: false };
  },
});
