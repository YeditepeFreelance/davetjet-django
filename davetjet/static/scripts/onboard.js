/* =========================================================================
   Onboard v2 — estetik, erişilebilir, vanilla JS tur motoru
   ========================================================================*/
(function () {
  "use strict";

  function clamp(v, min, max) {
    return Math.max(min, Math.min(max, v));
  }
  function isInViewport(rect, pad) {
    var vw = window.innerWidth,
      vh = window.innerHeight;
    return (
      rect.top >= -pad &&
      rect.left >= -pad &&
      rect.bottom <= vh + pad &&
      rect.right <= vw + pad
    );
  }
  function tabbables(root) {
    return root.querySelectorAll(
      'a[href], button:not([disabled]), textarea, input, select, [tabindex]:not([tabindex="-1"])'
    );
  }

  class Onboard {
    static create(steps, options) {
      return new Onboard(steps, options);
    }

    constructor(steps, options) {
      this.steps = Array.isArray(steps) ? steps.filter(Boolean) : [];
      this.opts = Object.assign(
        {
          accentColor: "#3c8f52",
          zIndex: 9999,
          padding: 10,
          gap: 10,
          closeOnOverlayClick: false,
          allowScroll: false,
          storageKey: null,
          autoStartOnce: false,
          flowId: null,
          showDots: true,
        },
        options || {}
      );
      this._idx = -1;
      this._built = false;
      this._cleanupFns = [];
      this._observers = [];
      this._veilEls = [];
      this._focusRestore = null;
    }

    start(i) {
      var startIndex = typeof i === "number" ? i : 0;
      if (!this.steps.length) return this;
      if (
        this.opts.autoStartOnce &&
        this.opts.storageKey &&
        localStorage.getItem(this.opts.storageKey) === "done"
      )
        return this;

      if (!this._built) this._build();
      document.body.classList.add("onb-open");
      this._applyTheme();

      this._focusRestore =
        document.activeElement && document.activeElement.focus
          ? document.activeElement
          : null;

      this.go(startIndex);
      this._bindGlobal();
      return this;
    }

    go(i) {
      var idx = clamp(i, 0, this.steps.length - 1);
      this._idx = idx;
      var step = this.steps[idx];
      this._renderStep(step, idx);
      if (typeof this.opts.onStep === "function") this.opts.onStep(idx, step);
    }

    next() {
      this._idx < this.steps.length - 1
        ? this.go(this._idx + 1)
        : this.end(false);
    }
    prev() {
      if (this._idx > 0) this.go(this._idx - 1);
    }

    end(skipped) {
      var isSkipped = !!skipped;
      document.body.classList.remove("onb-open");
      this._teardownObservers();

      this._veilEls.forEach(function (el) {
        if (el) el.style.cssText = "";
      });
      if (this._ring) this._ring.style.cssText = "display:none;";
      if (this._pop) this._pop.style.cssText = "display:none;";

      if (this.opts.storageKey && !isSkipped) {
        try {
          localStorage.setItem(this.opts.storageKey, "done");
        } catch (e) {}
      }
      if (!isSkipped && typeof this.opts.onFinish === "function")
        this.opts.onFinish();
      if (isSkipped && typeof this.opts.onSkip === "function")
        this.opts.onSkip();

      if (this._focusRestore && this._focusRestore.focus) {
        try {
          this._focusRestore.focus();
        } catch (e) {}
      }

      this._cleanupFns.forEach(function (fn) {
        try {
          fn();
        } catch (e) {}
      });
      this._cleanupFns = [];
      return this;
    }

    _build() {
      var root = document.createElement("div");
      root.className = "onb-root";
      root.style.setProperty("--onb-z", String(this.opts.zIndex));

      var veil = document.createElement("div");
      veil.className = "onb-veil";
      var bTop = document.createElement("div");
      bTop.className = "onb-block onb-block--top";
      var bLeft = document.createElement("div");
      bLeft.className = "onb-block onb-block--left";
      var bRight = document.createElement("div");
      bRight.className = "onb-block onb-block--right";
      var bBottom = document.createElement("div");
      bBottom.className = "onb-block onb-block--bottom";
      veil.appendChild(bTop);
      veil.appendChild(bLeft);
      veil.appendChild(bRight);
      veil.appendChild(bBottom);

      var ring = document.createElement("div");
      ring.className = "onb-focus-ring";

      var pop = document.createElement("div");
      pop.className = "onb-pop";
      pop.setAttribute("role", "dialog");
      pop.setAttribute("aria-modal", "true");
      pop.innerHTML =
        '<button class="onb-close" aria-label="Kapat">×</button>' +
        '<div class="onb-pop__inner">' +
        '  <div class="onb-pop__title" id="onb-title"></div>' +
        '  <div class="onb-pop__desc"  id="onb-desc"></div>' +
        '  <div class="onb-pop__progress"><div class="onb-pop__bar" id="onb-bar"></div></div>' +
        '  <div class="onb-pop__dots" id="onb-dots" aria-hidden="true"></div>' +
        '  <div class="onb-pop__footer">' +
        '    <span class="onb-steps" id="onb-steps"></span>' +
        '    <div class="onb-actions">' +
        '      <button class="onb-btn onb-btn--ghost" id="onb-prev">Geri</button>' +
        '      <button class="onb-btn onb-btn--pri"   id="onb-next">İleri</button>' +
        '      <button class="onb-btn onb-btn--ghost" id="onb-skip">Atla</button>' +
        "    </div>" +
        "  </div>" +
        "</div>";
      var arrow = document.createElement("div");
      arrow.className = "onb-arrow onb-arrow--top";
      pop.appendChild(arrow);

      root.appendChild(veil);
      root.appendChild(ring);
      root.appendChild(pop);
      document.body.appendChild(root);

      this._root = root;
      this._veil = veil;
      this._veilEls = [bTop, bLeft, bRight, bBottom];
      this._ring = ring;
      this._pop = pop;
      this._arrow = arrow;
      this._title = pop.querySelector("#onb-title");
      this._desc = pop.querySelector("#onb-desc");
      this._bar = pop.querySelector("#onb-bar");
      this._dots = pop.querySelector("#onb-dots");
      this._stepsEl = pop.querySelector("#onb-steps");
      this._btnPrev = pop.querySelector("#onb-prev");
      this._btnNext = pop.querySelector("#onb-next");
      this._btnSkip = pop.querySelector("#onb-skip");
      this._btnClose = pop.querySelector(".onb-close");

      var self = this;
      this._btnPrev.addEventListener("click", function () {
        self.prev();
      });
      this._btnNext.addEventListener("click", function () {
        self.next();
      });
      this._btnSkip.addEventListener("click", function () {
        self.end(true);
      });
      this._btnClose.addEventListener("click", function () {
        self.end(true);
      });

      if (!this.opts.closeOnOverlayClick) {
        this._veil.addEventListener("click", function (e) {
          e.stopPropagation();
        });
        this._veil.addEventListener("mousedown", function (e) {
          e.preventDefault();
        });
      } else {
        this._veil.addEventListener("click", function () {
          self.end(true);
        });
      }

      var trap = (e) => {
        if (e.key !== "Tab") return;
        var elts = tabbables(this._pop);
        if (!elts.length) return;
        var first = elts[0],
          last = elts[elts.length - 1];
        if (e.shiftKey && document.activeElement === first) {
          e.preventDefault();
          last.focus();
        } else if (!e.shiftKey && document.activeElement === last) {
          e.preventDefault();
          first.focus();
        }
      };
      this._pop.addEventListener("keydown", trap);

      this._built = true;
    }

    _applyTheme() {
      this._root.style.setProperty("--onb-accent", this.opts.accentColor);
    }

    _bindGlobal() {
      var self = this;
      function onKey(e) {
        if (e.key === "Escape") self.end(true);
        else if (e.key === "ArrowRight") self.next();
        else if (e.key === "ArrowLeft") self.prev();
        else if (e.key === "Enter") self.next();
      }
      window.addEventListener("keydown", onKey);
      this._cleanupFns.push(function () {
        window.removeEventListener("keydown", onKey);
      });

      if (!this.opts.allowScroll) {
        function prevent(e) {
          e.preventDefault();
        }
        window.addEventListener("wheel", prevent, { passive: false });
        window.addEventListener("touchmove", prevent, { passive: false });
        this._cleanupFns.push(function () {
          window.removeEventListener("wheel", prevent);
          window.removeEventListener("touchmove", prevent);
        });
      }
    }

    _renderStep(step, index) {
      var tgt =
        step && step.target ? document.querySelector(step.target) : null;
      var pad = step && step.padding != null ? step.padding : this.opts.padding;

      if (this._title)
        this._title.textContent = step && step.title ? step.title : "";
      if (this._desc)
        this._desc.textContent = step && step.content ? step.content : "";
      if (this._stepsEl)
        this._stepsEl.textContent = index + 1 + " / " + this.steps.length;
      if (this._bar)
        this._bar.style.width =
          Math.round(((index + 1) / this.steps.length) * 100) + "%";

      if (this._dots) {
        if (this.opts.showDots) {
          var html = "";
          for (var d = 0; d < this.steps.length; d++)
            html +=
              '<span class="onb-pop__dot' +
              (d === index ? " onb-pop__dot--active" : "") +
              '"></span>';
          this._dots.innerHTML = html;
        } else this._dots.innerHTML = "";
      }

      if (this._btnPrev) this._btnPrev.disabled = index === 0;
      if (this._btnNext) {
        var isLast = index === this.steps.length - 1;
        this._btnNext.textContent = isLast
          ? (step && step.finishText) || "Bitir"
          : (step && step.nextText) || "İleri";
      }

      this._teardownObservers();

      if (!tgt) {
        this._placeVeil(null);
        if (this._ring) this._ring.style.display = "none";
        this._placePopCentered();
        this._btnNext && this._btnNext.focus();
        return;
      }

      var self = this;
      function place() {
        var rect = tgt.getBoundingClientRect();
        var r = {
          top: Math.max(0, rect.top - pad),
          left: Math.max(0, rect.left - pad),
          width: rect.width + pad * 2,
          height: rect.height + pad * 2,
        };
        r.right = r.left + r.width;
        r.bottom = r.top + r.height;
        self._placeVeil(r);
        self._placeRing(r);
        self._placePop(r, (step && step.placement) || "auto");
      }

      var rectNow = tgt.getBoundingClientRect();
      if (!isInViewport(rectNow, 24)) {
        try {
          tgt.scrollIntoView({
            behavior: "smooth",
            block: "center",
            inline: "center",
          });
        } catch (e) {
          window.scrollTo({
            top: rectNow.top + window.scrollY - 120,
            behavior: "smooth",
          });
        }
        setTimeout(place, 220);
      } else place();

      var hasRO = typeof window.ResizeObserver !== "undefined";
      var ro = null;
      if (hasRO) {
        ro = new window.ResizeObserver(place);
        ro.observe(document.documentElement);
        ro.observe(tgt);
        this._observers.push(function () {
          ro && ro.disconnect();
        });
      }
      function onScroll() {
        place();
      }
      window.addEventListener("scroll", onScroll, { passive: true });
      window.addEventListener("resize", onScroll, { passive: true });
      this._cleanupFns.push(function () {
        window.removeEventListener("scroll", onScroll);
        window.removeEventListener("resize", onScroll);
      });

      setTimeout(() => {
        this._btnNext && this._btnNext.focus();
      }, 0);
    }

    _placeVeil(r) {
      var blocks = this._veilEls;
      var vw = window.innerWidth,
        vh = window.innerHeight;
      var top = blocks[0],
        left = blocks[1],
        right = blocks[2],
        bottom = blocks[3];
      if (!r) {
        top.style.cssText = "inset:0 auto auto 0; width:100vw; height:100vh;";
        left.style.cssText =
          right.style.cssText =
          bottom.style.cssText =
            "display:none;";
        return;
      }
      top.style.cssText = "top:0; left:0; width:100vw; height:" + r.top + "px;";
      bottom.style.cssText =
        "top:" +
        r.bottom +
        "px; left:0; width:100vw; height:" +
        (vh - r.bottom) +
        "px;";
      left.style.cssText =
        "top:" +
        r.top +
        "px; left:0; width:" +
        r.left +
        "px; height:" +
        r.height +
        "px; display:block;";
      right.style.cssText =
        "top:" +
        r.top +
        "px; left:" +
        r.right +
        "px; width:" +
        (vw - r.right) +
        "px; height:" +
        r.height +
        "px; display:block;";
    }

    _placeRing(r) {
      if (!this._ring) return;
      this._ring.style.display = "block";
      this._ring.style.top = r.top + "px";
      this._ring.style.left = r.left + "px";
      this._ring.style.width = r.width + "px";
      this._ring.style.height = r.height + "px";
      this._ring.style.borderRadius = "14px";
    }

    _placePopCentered() {
      if (!this._pop || !this._arrow) return;
      this._pop.style.display = "block";
      this._arrow.className = "onb-arrow onb-arrow--top";
      var vw = window.innerWidth,
        vh = window.innerHeight;
      var rect = this._pop.getBoundingClientRect();
      var x = (vw - rect.width) / 2,
        y = (vh - rect.height) / 2;
      this._pop.style.left =
        clamp(x, 12, Math.max(12, vw - rect.width - 12)) + "px";
      this._pop.style.top =
        clamp(y, 12, Math.max(12, vh - rect.height - 12)) + "px";
    }

    _placePop(r, placement) {
      if (!this._pop || !this._arrow) return;
      this._pop.style.display = "block";
      var vw = window.innerWidth,
        vh = window.innerHeight;
      var gap = this.opts.gap;
      var rect = this._pop.getBoundingClientRect();

      function posBottom() {
        return {
          x: clamp(r.left, 12, vw - rect.width - 12),
          y: clamp(r.bottom + gap, 12, vh - rect.height - 12),
          arrow: "top",
        };
      }
      function posTop() {
        return {
          x: clamp(r.left, 12, vw - rect.width - 12),
          y: clamp(r.top - rect.height - gap, 12, vh - rect.height - 12),
          arrow: "bottom",
        };
      }
      function posRight() {
        return {
          x: clamp(r.right + gap, 12, vw - rect.width - 12),
          y: clamp(r.top, 12, vh - rect.height - 12),
          arrow: "left",
        };
      }
      function posLeft() {
        return {
          x: clamp(r.left - rect.width - gap, 12, vw - rect.width - 12),
          y: clamp(r.top, 12, vh - rect.height - 12),
          arrow: "right",
        };
      }

      var order =
        placement === "auto" ? ["bottom", "top", "right", "left"] : [placement];
      var pos = null;
      for (var i = 0; i < order.length; i++) {
        var p = order[i];
        pos =
          p === "bottom"
            ? posBottom()
            : p === "top"
            ? posTop()
            : p === "right"
            ? posRight()
            : posLeft();
        if (
          pos.x >= 12 &&
          pos.x <= vw - rect.width - 12 &&
          pos.y >= 12 &&
          pos.y <= vh - rect.height - 12
        )
          break;
      }
      if (!pos) pos = posBottom();

      this._pop.style.left = pos.x + "px";
      this._pop.style.top = pos.y + "px";
      this._arrow.className = "onb-arrow onb-arrow--" + pos.arrow;
    }

    _teardownObservers() {
      this._observers.forEach(function (fn) {
        try {
          fn();
        } catch (e) {}
      });
      this._observers = [];
    }
  }

  window.Onboard = Onboard;
})();

/* =========================================================================
   dashboard-init.js — Onboard entegrasyonu (v2)
   ========================================================================*/
(function () {
  "use strict";

  function getPageKey() {
    var body = document.body;
    return body && body.dataset && body.dataset.page
      ? body.dataset.page
      : "page";
  }

  function collectOnboardSteps(pageKey) {
    function getCurrentWizardStepRoot() {
      return document.querySelector(".wizard-step:not(.hidden)");
    }
    function isVisibleDeep(el) {
      if (!el) return false;
      if (el.hidden || el.getAttribute("aria-hidden") === "true") return false;
      var rects = el.getClientRects();
      if (!rects || rects.length === 0) return false;
      var cur = el;
      while (cur && cur !== document.body) {
        var cs = window.getComputedStyle(cur);
        if (
          cs.display === "none" ||
          cs.visibility === "hidden" ||
          cs.opacity === "0"
        )
          return false;
        cur = cur.parentElement;
      }
      return true;
    }

    var nodesAll = document.querySelectorAll("[data-onb]");
    var currentStepRoot = getCurrentWizardStepRoot();

    var nodes = [];
    if (currentStepRoot) {
      nodesAll.forEach(function (el) {
        var ownerStep = el.closest(".wizard-step");
        if (ownerStep === currentStepRoot && isVisibleDeep(el)) nodes.push(el);
      });
      if (nodes.length === 0) {
        nodesAll.forEach(function (el) {
          if (isVisibleDeep(el)) nodes.push(el);
        });
      }
    } else {
      nodesAll.forEach(function (el) {
        if (isVisibleDeep(el)) nodes.push(el);
      });
    }

    var scoped = [],
      unscoped = [],
      rest = [];
    nodes.forEach(function (el, i) {
      var key = el.getAttribute("data-onb");
      var title = el.getAttribute("data-onb-title") || "";
      var desc = el.getAttribute("data-onb-desc") || "";
      var place = el.getAttribute("data-onb-place") || "auto";
      var padAttr = el.getAttribute("data-onb-pad");
      var pad =
        padAttr !== null && padAttr !== "" ? parseInt(padAttr, 10) : undefined;
      var targetOverride = el.getAttribute("data-onb-target");
      var targetSel = targetOverride || '[data-onb="' + key + '"]';
      var orderAttr = el.getAttribute("data-onb-order");
      var order =
        orderAttr !== null && orderAttr !== "" ? parseInt(orderAttr, 10) : i;
      var scope = el.getAttribute("data-onb-scope");

      var step = {
        target: targetSel,
        title: title,
        content: desc,
        placement: place,
        padding: pad,
        _order: isNaN(order) ? i : order,
      };
      if (!scope) unscoped.push(step);
      else if (scope === pageKey) scoped.push(step);
      else rest.push(step);
    });

    var result = scoped.length
      ? scoped
      : unscoped.length
      ? unscoped
      : rest.length
      ? rest
      : [];
    result.sort(function (a, b) {
      return a._order - b._order;
    });

    return result;
  }

  // public
  window.startPageTour = function () {
    if (typeof window.Onboard !== "function") return null;
    var page = getPageKey();
    var steps = collectOnboardSteps(page);
    if (!steps.length) {
      console.warn("[tour] no steps for page:", page);
      return null;
    }
    var tour = window.Onboard.create(steps, {
      accentColor: "#3c8f52",
      storageKey: "onb:" + page + ":v2",
      autoStartOnce: false,
      showDots: true,
    });
    window.__CURRENT_TOUR__ = tour;
    tour.start(0);
    return tour;
  };

  document.addEventListener("DOMContentLoaded", function () {
    var btn = document.getElementById("navHelpTour");
    if (btn)
      btn.addEventListener("click", function (e) {
        e.preventDefault();
        window.startPageTour();
      });
  });
})();

// Onboard yeniden aç/kapat patch + event publish
(function () {
  if (!window.Onboard || !Onboard.prototype) return;
  var _start = Onboard.prototype.start;
  var _end = Onboard.prototype.end;

  Onboard.prototype.start = function (i) {
    if (this._root) {
      this._root.style.display = "block";
      this._root.style.pointerEvents = "auto";
    }
    if (this._veil) {
      this._veil.style.display = "block";
    }
    return _start.call(this, i);
  };

  Onboard.prototype.end = function (skipped) {
    var r = _end.call(this, skipped);
    // TaskBus olayı (varsa)
    try {
      if (window.TaskBus) {
        var page =
          (document.body &&
            document.body.dataset &&
            document.body.dataset.page) ||
          "page";
        window.TaskBus.emit("onb:ended", { skipped: !!skipped, page: page });
      }
    } catch (_) {}
    if (this._veil) this._veil.style.display = "none";
    if (this._ring) this._ring.style.display = "none";
    if (this._pop) this._pop.style.display = "none";
    if (this._root) {
      this._root.style.pointerEvents = "none";
      this._root.style.display = "none";
    }
    return r;
  };
})();

/* =========================================================================
   Görev Sistemi v2 — redirect + gating + çekmece entegrasyonu
   ========================================================================*/
(function () {
  "use strict";

  // ---- Event Bus
  const TaskBus = window.TaskBus || {
    _h: Object.create(null),
    on(t, cb) {
      (this._h[t] || (this._h[t] = [])).push(cb);
    },
    emit(t, d) {
      (this._h[t] || []).forEach((f) => {
        try {
          f(d);
        } catch (e) {}
      });
    },
  };
  window.TaskBus = TaskBus;

  // ---- Global helpers
  function getPageKey() {
    const b = document.body;
    return b && b.dataset && b.dataset.page ? b.dataset.page : "page";
  }

  // ---- App URL helper (redirect hedefleri)
  const URLS = {
    create:
      document.querySelector('meta[name="url-create"]')?.content ||
      "/dashboard/invitations/create-new",
    send:
      document.querySelector('meta[name="url-send"]')?.content ||
      "/dashboard/sending",
    analytics:
      document.querySelector('meta[name="url-analytics"]')?.content ||
      "/dashboard/analytics",
  };

  // ---- State
  const LS_KEY = "dj:tasks:v2";
  function loadState() {
    try {
      return (
        JSON.parse(localStorage.getItem(LS_KEY)) || {
          done: {},
          snooze: {},
          mutedBadgeUntil: 0,
        }
      );
    } catch (_) {
      return { done: {}, snooze: {}, mutedBadgeUntil: 0 };
    }
  }
  function saveState(s) {
    localStorage.setItem(LS_KEY, JSON.stringify(s));
  }
  let state = loadState();

  // ---- TASKS (tek kaynak)
  const TASKS = [
    // WIZARD (sayfa-özel)
    {
      id: "wiz_template",
      title: "Şablon seç",
      desc: "Sihirbazda şablon seçimini tamamla.",
      page: "wizard",
      tourKey: "template",
      type: "tour",
      crit: false,
      reco: true,
    },
    {
      id: "wiz_info",
      title: "Temel bilgileri doldur",
      desc: "Başlık, tarih/saat ve konum alanlarını tamamla.",
      page: "wizard",
      tourKey: "basic-info",
      type: "tour",
      crit: true,
      reco: false,
    },

    // 1) Davet oluştur (ön şart)
    {
      id: "create_invitation",
      title: "Yeni davet oluştur",
      desc: "Sihirbazı kullanarak ilk davetini oluştur.",
      page: null,
      type: "redirect",
      href: URLS.create,
      crit: true,
      reco: true,
    },

    // 2) Gönderim — her sayfada görünür, ancak create tamamlanmadan saklı
    {
      id: "sending_setup",
      title: "Davetini gönder",
      desc: "E-posta/SMS seç ve planla.",
      page: null,
      type: "redirect",
      href: URLS.send,
      crit: false,
      reco: false,
    },

    // 3) Analiz — her sayfada görünür, ancak create tamamlanmadan saklı
    {
      id: "analytics_overview",
      title: "Davetini analiz et",
      desc: "RSVP, huni ve timeline ile performansı incele.",
      page: null,
      type: "redirect",
      href: URLS.analytics,
      crit: false,
      reco: false,
    },

    // Analitik sayfadayken tur
    {
      id: "analytics_view",
      title: "Analytics filtrelerini kullan",
      desc: "Davet/kanal/tarih filtreleri ile özetlere bak.",
      page: "analytics",
      tourKey: "filters",
      type: "tour",
      crit: false,
      reco: true,
    },
  ];

  // ---- Gating
  const BLOCKED_UNTIL_CREATE = new Set([
    "sending_setup",
    "analytics_overview",
    "analytics_view",
  ]);

  function isDue(task) {
    const until = state.snooze[task.id];
    return !until || Date.now() >= until;
  }
  function actionable(tasks) {
    const page = getPageKey();
    return tasks.filter((t) => {
      if (t.page && t.page !== page) return false; // sayfa eşleşmesi (page=null -> her yer)
      if (state.done[t.id]) return false; // tamamlandıysa gösterme
      if (!isDue(t)) return false; // snooze aktifse gösterme
      if (!state.done["create_invitation"] && BLOCKED_UNTIL_CREATE.has(t.id))
        return false; // gating
      return true;
    });
  }

  // ---- UI refs
  const drawer = document.getElementById("taskDrawer");
  const trigger = document.getElementById("taskTrigger");
  const closeBtn = document.getElementById("taskDrawerClose");
  const listEl = document.getElementById("taskList");
  const progFill = document.getElementById("tdProgressFill");
  const progTxt = document.getElementById("tdProgressText");
  const startTourBtn = document.getElementById("tdStartPageTour");
  const badge = document.getElementById("notificationBadge");

  // overlay (yoksa ekle)
  let overlay = document.querySelector(".td-overlay");
  if (!overlay) {
    overlay = document.createElement("div");
    overlay.className = "td-overlay";
    overlay.setAttribute("aria-hidden", "true");
    document.body.appendChild(overlay);
  }

  // ---- Drawer open/close
  let lastFocus = null;
  function applyOpenState(isOpen) {
    if (!drawer) return;
    drawer.setAttribute("aria-hidden", isOpen ? "false" : "true");
    drawer.classList.toggle("open", isOpen);
    overlay.classList.toggle("open", isOpen);
    trigger && trigger.setAttribute("aria-expanded", isOpen ? "true" : "false");
    document.body.classList.toggle("modal-open", isOpen);
    if (isOpen) {
      const head = drawer.querySelector(".td-title strong");
      head && head.focus && head.focus();
      if (getComputedStyle(drawer).display === "none")
        drawer.style.display = "block";
    } else {
      lastFocus && lastFocus.focus && lastFocus.focus();
    }
  }
  function openDrawer() {
    lastFocus = document.activeElement;
    applyOpenState(true);
  }
  function closeDrawer() {
    applyOpenState(false);
  }
  window.TaskDrawer = {
    open: openDrawer,
    close: closeDrawer,
    toggle() {
      drawer.getAttribute("aria-hidden") !== "false"
        ? openDrawer()
        : closeDrawer();
    },
  };

  trigger &&
    trigger.addEventListener("click", (e) => {
      e.preventDefault();
      window.TaskDrawer.toggle();
    });
  closeBtn && closeBtn.addEventListener("click", closeDrawer);
  overlay.addEventListener("click", closeDrawer);
  window.addEventListener("keydown", (e) => {
    if (e.key === "Escape" && drawer.getAttribute("aria-hidden") === "false")
      closeDrawer();
  });

  // ---- Snooze hesaplayıcı
  function computeSnoozeUntil(code) {
    if (code === "1h") return Date.now() + 60 * 60 * 1000;
    if (code === "1d") return Date.now() + 24 * 60 * 60 * 1000;
    if (code === "7d") return Date.now() + 7 * 24 * 60 * 60 * 1000;
    if (code === "pre7") {
      try {
        const iso = window.INV_META?.invitation_date || null;
        if (iso) {
          const t = new Date(iso).getTime() - 7 * 24 * 60 * 60 * 1000;
          return Math.max(Date.now() + 60 * 60 * 1000, t);
        }
      } catch (_) {}
      return Date.now() + 7 * 24 * 60 * 60 * 1000;
    }
    return Date.now() + 24 * 60 * 60 * 1000;
  }

  // ---- Kart şablonu
  function cardHTML(t) {
    const chips = [];
    if (t.crit)
      chips.push('<span class="td-chip td-chip--crit">Öncelik</span>');
    if (t.reco) chips.push('<span class="td-chip td-chip--reco">Öneri</span>');
    if (t.page)
      chips.push(`<span class="td-chip td-chip--page">${t.page}</span>`);

    const startBtn =
      t.type === "tour"
        ? '<button class="btn btn--dark" data-act="start">Başlat</button>'
        : t.type === "redirect"
        ? `<button class="btn btn--dark" data-act="redirect" data-href="${
            t.href || "#"
          }">Başla</button>`
        : "";

    return `
      <li class="td-item" data-id="${t.id}" data-tour-key="${t.tourKey || ""}">
        <div class="td-main">
          <div class="td-item__title">${t.title}</div>
          <div class="td-item__desc">${t.desc || ""}</div>
          <div class="td-item__meta">${chips.join("")}</div>
        </div>
        <div class="td-actions">
          ${startBtn}
          <button class="btn btn--ghost" data-act="done">Tamamla</button>
          <div class="td-menu">
            <button class="td-menu__btn" aria-label="Diğer"><i class="fa-solid fa-ellipsis"></i></button>
            <div class="td-menu__pop">
              <button data-snooze="1h">1 saat ertele</button>
              <button data-snooze="1d">1 gün ertele</button>
              <button data-snooze="7d">7 gün ertele</button>
              <button data-snooze="pre7">Etkinlikten 7 gün önce</button>
            </div>
          </div>
        </div>
      </li>
    `;
  }

  // ---- Liste & ilerleme
  function renderList() {
    const page = getPageKey();
    const pageTasks = TASKS.filter((t) => !t.page || t.page === page); // sayfaya ait tüm görevler
    const visible = actionable(pageTasks); // gating + snooze + done uygulanmış
    const completed = pageTasks.filter((t) => state.done[t.id]).length;
    const total = pageTasks.length || 1;

    listEl.innerHTML = visible.length
      ? visible.map(cardHTML).join("")
      : '<li class="td-empty">Görev yok 🎉</li>';

    const pct = Math.round((completed / total) * 100);
    if (progFill) progFill.style.width = pct + "%";
    if (progTxt) progTxt.textContent = `${completed} / ${total} tamamlandı`;

    refreshBadge();
  }

  // ---- Rozet
  function refreshBadge() {
    if (!badge) return;
    const allVisibleEverywhere = actionable(TASKS); // page filtresi yok -> tüm sayfalardaki due
    const cnt = allVisibleEverywhere.length;
    if (cnt > 0) {
      badge.textContent = String(cnt);
      badge.classList.remove("hidden");
      if (Date.now() > (state.mutedBadgeUntil || 0)) {
        badge.style.animationPlayState = "running";
        setTimeout(() => (badge.style.animationPlayState = "paused"), 8000);
        state.mutedBadgeUntil = Date.now() + 60 * 60 * 1000;
        saveState(state);
      }
    } else {
      badge.classList.add("hidden");
      badge.textContent = "";
    }
  }

  // ---- Delegasyon (kart içi aksiyonlar)
  listEl.addEventListener("click", (e) => {
    const li = e.target.closest(".td-item");
    if (!li) return;
    const id = li.dataset.id;

    const menuBtn = e.target.closest(".td-menu__btn");
    if (menuBtn) {
      const pop = li.querySelector(".td-menu__pop");
      document
        .querySelectorAll(".td-menu__pop.open")
        .forEach((p) => p !== pop && p.classList.remove("open"));
      pop && pop.classList.toggle("open");
      return;
    }
    const sno = e.target.closest("[data-snooze]");
    if (sno) {
      state.snooze[id] = computeSnoozeUntil(sno.dataset.snooze);
      saveState(state);
      renderList();
      return;
    }

    const act = e.target.closest("[data-act]");
    if (!act) return;

    if (act.dataset.act === "done") {
      state.done[id] = true;
      saveState(state);
      renderList();
      return;
    }
    if (act.dataset.act === "start") {
      const key = li.dataset.tourKey || "";
      closeDrawer();
      startPageTourAt(key);
      return;
    }
    if (act.dataset.act === "redirect") {
      const to = act.getAttribute("data-href") || "#";
      closeDrawer();
      setTimeout(() => {
        window.location.href = to;
      }, 80);
      return;
    }
  });

  // dışarı tıklayınca 3 nokta menüsünü kapat
  document.addEventListener("click", (e) => {
    if (!e.target.closest(".td-menu")) {
      document
        .querySelectorAll(".td-menu__pop.open")
        .forEach((p) => p.classList.remove("open"));
    }
  });

  // ---- Bu sayfanın turunu başlat
  startTourBtn &&
    startTourBtn.addEventListener("click", () => {
      closeDrawer();
      startPageTourAt(""); // baştan
    });

  // ---- Onboard bitince ilgili tour görevlerini tamamla
  TaskBus.on("onb:ended", (detail) => {
    if (!detail || detail.skipped) return;
    const page = detail.page || getPageKey();
    TASKS.forEach((t) => {
      if (t.type === "tour" && (t.page || "") === page && !state.done[t.id]) {
        state.done[t.id] = true;
      }
    });
    saveState(state);
    renderList();
  });

  // ---- fetch patch: otomatik event
  (function patchFetch() {
    if (window.__TASK_FETCH_PATCHED__ || !window.fetch) return;
    const _fetch = window.fetch.bind(window);
    window.fetch = async function (input, init) {
      const res = await _fetch(input, init);
      try {
        const url = typeof input === "string" ? input : input?.url || "";
        const method = (init?.method || "GET").toUpperCase();
        if (res.ok) {
          if (/\/create-invitation-api/i.test(url) && method === "POST")
            TaskBus.emit("inv:created_published");
          if (
            /\/invitation-draft-promote\/\d+\/?$/i.test(url) &&
            method === "POST"
          )
            TaskBus.emit("inv:promoted");
          if (/\/api\/schedule-send\/\d+\/?$/i.test(url) && method === "POST")
            TaskBus.emit("send:scheduled");
          if (/\/recipients\/[^/]+\/?$/i.test(url) && method === "POST")
            TaskBus.emit("recipients:added");
        }
      } catch (_) {}
      return res;
    };
    window.__TASK_FETCH_PATCHED__ = true;
  })();

  // Bu olaylar gelince ilgili görevleri otomatik tamamla
  TaskBus.on("inv:created_published", () => {
    state.done["create_invitation"] = true;
    saveState(state);
    renderList();
  });
  TaskBus.on("inv:promoted", () => {
    state.done["create_invitation"] = true;
    saveState(state);
    renderList();
  });
  TaskBus.on("send:scheduled", () => {
    state.done["sending_setup"] = true;
    saveState(state);
    renderList();
  });

  // ---- Tour’u belirli key’den başlatma
  window.startPageTourAt = function (key) {
    const tour =
      typeof window.startPageTour === "function"
        ? window.startPageTour()
        : null;
    if (!tour) {
      const u = new URL(location.href);
      u.searchParams.set("tour", key || "1");
      location.href = u.toString();
      return;
    }
    if (!key) return;
    setTimeout(() => {
      try {
        const sel =
          key.startsWith("#") || key.startsWith(".")
            ? key
            : `[data-onb="${key}"]`;
        const i = tour.steps.findIndex((s) => s.target === sel);
        if (i >= 0 && typeof tour.go === "function") tour.go(i);
      } catch (_) {}
    }, 30);
  };

  // URL ?tour= ile otomatik tetikleme
  document.addEventListener("DOMContentLoaded", () => {
    const sp = new URLSearchParams(location.search);
    if (sp.has("tour")) {
      const k = sp.get("tour");
      setTimeout(() => startPageTourAt(k === "1" ? "" : k), 300);
    }
  });

  // ---- İlk render + periyodik kontrol
  document.addEventListener("DOMContentLoaded", () => {
    renderList();
    setInterval(renderList, 60000);
  });
})();
