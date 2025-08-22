(function () {
  const ICONS = { success: "✓", info: "i", warning: "!", error: "!" };

  function ensureStack() {
    let stack = document.querySelector(".toast-stack");
    if (!stack) {
      stack = document.createElement("div");
      stack.className = "toast-stack"; // .toast-stack.center istersen ortala
      document.body.appendChild(stack);
    }
    return stack;
  }

  function escapeHtml(s) {
    return String(s).replace(
      /[&<>"']/g,
      (m) =>
        ({
          "&": "&amp;",
          "<": "&lt;",
          ">": "&gt;",
          '"': "&quot;",
          "'": "&#039;",
        }[m])
    );
  }

  function toast(message, opts = {}) {
    const {
      type = "info", // success | info | warning | error
      title = "", // opsiyonel başlık (bold)
      duration = 3500, // ms, 0 = otomatik kapanma yok
      dismissible = true, // kapat butonu
      center = false, // üst-orta konum
      html = false, // message HTML ise true
    } = opts;

    const stack = ensureStack();
    stack.classList.toggle("center", !!center);

    const el = document.createElement("div");
    el.className = `toast toast--${type}`;
    el.setAttribute(
      "role",
      type === "error" || type === "warning" ? "alert" : "status"
    );
    el.setAttribute(
      "aria-live",
      type === "error" || type === "warning" ? "assertive" : "polite"
    );

    const icon = `<div class="toast__icon" aria-hidden="true">${
      ICONS[type] || "i"
    }</div>`;
    const body = `<div class="toast__body">${
      title ? `<strong>${escapeHtml(title)}</strong><br>` : ""
    }${html ? message : escapeHtml(message)}</div>`;
    const close = dismissible
      ? `<button class="toast__close" aria-label="Kapat">×</button>`
      : "";

    el.innerHTML = icon + body + close;
    stack.appendChild(el);

    requestAnimationFrame(() => el.classList.add("show"));

    let timer;
    const start = () => {
      if (duration > 0) timer = setTimeout(hide, duration);
    };
    const stop = () => {
      if (timer) clearTimeout(timer);
    };

    function hide() {
      stop();
      el.classList.remove("show");
      el.addEventListener("transitionend", () => el.remove(), { once: true });
    }

    el.addEventListener("mouseenter", stop);
    el.addEventListener("mouseleave", start);
    if (dismissible)
      el.querySelector(".toast__close")?.addEventListener("click", hide);

    start();
    return { el, hide };
  }

  // Şeker fonksiyonlar
  toast.success = (m, o) => toast(m, { ...o, type: "success" });
  toast.info = (m, o) => toast(m, { ...o, type: "info" });
  toast.warning = (m, o) => toast(m, { ...o, type: "warning" });
  toast.error = (m, o) => toast(m, { ...o, type: "error" });

  // (Opsiyonel) Django messages JSON’u otomatik göster:
  // <script id="dj-messages" type="application/json">[{"level":"success","message":"Kaydedildi"}]</script>
  function bootFromDjango() {
    const tag = document.getElementById("dj-messages");
    if (!tag) return;
    try {
      const arr = JSON.parse(tag.textContent || "[]");
      arr.forEach((m) => {
        const level = (m.level || "info").toLowerCase();
        toast(m.message || "", { type: level, duration: m.duration ?? 4000 });
      });
    } catch {}
  }

  window.toast = toast;

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", bootFromDjango);
  } else {
    bootFromDjango();
  }
})();
