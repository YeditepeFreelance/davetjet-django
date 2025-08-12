"use strict";
document.addEventListener("DOMContentLoaded", () => {
  const body = document.body;
  const sidebar = document.getElementById("sidebar");
  const backdrop = document.getElementById("sidebarBackdrop"); // <div id="sidebarBackdrop" hidden>
  const burger =
    document.getElementById("hamburger") ||
    document.getElementById("dashHamburger");
  const collapse = document.getElementById("sbCollapse"); // (opsiyonel)
  const closeBtn =
    document.getElementById("sbClose") ||
    document.getElementById("sidebarClose");
  const MQ_DESKTOP = 992;

  // ---- Desktop collapse (persist) ------------------------------------------
  const applyCollapsed = (v) =>
    sidebar?.setAttribute("data-collapsed", v ? "true" : "false");
  try {
    applyCollapsed(localStorage.getItem("sb_collapsed") === "1");
  } catch {}

  collapse?.addEventListener("click", () => {
    const next = sidebar?.getAttribute("data-collapsed") !== "true";
    applyCollapsed(next);
    try {
      localStorage.setItem("sb_collapsed", next ? "1" : "0");
    } catch {}
  });

  // ---- Mobile open/close ----------------------------------------------------
  function toggleMobile(open) {
    const willOpen = open ?? !body.classList.contains("sidebar-open");

    body.classList.toggle("sidebar-open", willOpen); // scroll lock (CSS)
    sidebar?.classList.toggle("is-open", willOpen); // off-canvas anim (CSS)
    burger?.classList.toggle("is-open", willOpen); // X animasyonu
    burger?.setAttribute("aria-expanded", willOpen ? "true" : "false");
    sidebar?.setAttribute("aria-hidden", willOpen ? "false" : "true");

    if (backdrop) {
      if (willOpen) {
        backdrop.classList.add("is-show");
        backdrop.removeAttribute("hidden");
      } else {
        backdrop.classList.remove("is-show");
        backdrop.setAttribute("hidden", "");
      }
    }

    // küçük a11y dokunuşu
    if (willOpen) (closeBtn || sidebar)?.focus?.();
  }

  burger?.addEventListener("click", () => toggleMobile());
  closeBtn?.addEventListener("click", () => toggleMobile(false));
  backdrop?.addEventListener("click", () => toggleMobile(false));
  document.addEventListener("keydown", (e) => {
    if (e.key === "Escape") toggleMobile(false);
  });

  // ---- Resize: desktop’a dönünce kapat -------------------------------------
  function handleResize() {
    if (
      window.innerWidth >= MQ_DESKTOP &&
      body.classList.contains("sidebar-open")
    ) {
      toggleMobile(false);
    }
  }
  window.addEventListener("resize", handleResize);
  handleResize(); // initial
});
