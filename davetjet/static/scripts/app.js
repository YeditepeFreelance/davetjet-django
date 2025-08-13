class App {
  constructor({ selector, targetDate }) {
    this.container = document.querySelector(selector);
    this.targetDate = new Date(targetDate);
    this.interval = null;

    // Form elements
    this.form = document.querySelector("form");
    this.steps = document.querySelectorAll(".form-step");
    this.nextButtons = document.querySelectorAll(".btn-next");
    this.csrfToken = document.querySelector(
      "[name=csrfmiddlewaretoken]"
    )?.value;

    this.usernameInput = document.querySelector('input[name="username"]');
    this.emailInput = document.querySelector('input[name="email"]');
    this.pass1Input = document.querySelector('input[name="password1"]');
    this.pass2Input = document.querySelector('input[name="password2"]');

    this.currentStep = 0;

    // Initialize features
    this.setupCursor();
    this.createContextMenu();
    this.initContextMenu();
    this.initCustomSelects();
    this.initRegisterForm(); // register.js logic
  }

  // ----------- COUNTDOWN -----------
  getTimeRemaining() {
    const now = new Date();
    const diff = this.targetDate - now;

    return {
      days: Math.max(0, Math.floor(diff / (1000 * 60 * 60 * 24))),
      hours: Math.max(0, Math.floor((diff / (1000 * 60 * 60)) % 24)),
      minutes: Math.max(0, Math.floor((diff / (1000 * 60)) % 60)),
      seconds: Math.max(0, Math.floor((diff / 1000) % 60)),
      isPast: diff < 0,
    };
  }

  renderCountdown({ days, hours, minutes, seconds }) {
    const currentValues = { days, hours, minutes, seconds };

    const units = [
      { key: "days", value: days, label: "Gün" },
      { key: "hours", value: hours, label: "Saat" },
      { key: "minutes", value: minutes, label: "Dakika" },
      { key: "seconds", value: seconds, label: "Saniye" },
    ];

    this.container.innerHTML = units
      .map((unit) => {
        const changed = this.previousValues?.[unit.key] !== unit.value;
        return `
        <div class="countdown-item">
          <div class="digit ${changed ? "flip" : ""}">${unit.value}</div>
          <div class="countdown-label">${unit.label}</div>
        </div>
      `;
      })
      .join("");

    this.previousValues = currentValues;
  }

  renderMessage(message) {
    this.container.innerHTML = `<div class="launch-message">${message}</div>`;
  }

  update() {
    const time = this.getTimeRemaining();
    if (time.isPast) {
      this.renderMessage("🚀 Geri Sayım Tamamlandı!");
      clearInterval(this.interval);
    } else {
      this.renderCountdown(time);
    }
  }

  start() {
    this.update();
    this.interval = setInterval(() => this.update(), 1000);
  }

  // ----------- CURSOR -----------
  setupCursor() {
    const cursor = document.querySelector(".custom-cursor");
    let mouseX = 0,
      mouseY = 0;
    let currentX = 0,
      currentY = 0;
    const speed = 0.15; // lower is smoother, slower

    window.addEventListener("mousemove", (e) => {
      mouseX = e.clientX;
      mouseY = e.clientY;
    });

    const animate = () => {
      currentX += mouseX - currentX;
      currentY += mouseY - currentY;
      cursor.style.transform = `translate(${currentX}px, ${currentY}px) translate(-50%, -50%)`;
      requestAnimationFrame(animate);
    };
    animate();

    const hoverables = document.querySelectorAll("button, a, .hover-target");
    hoverables.forEach((el) => {
      el.addEventListener("mouseenter", () => cursor.classList.add("hovered"));
      el.addEventListener("mouseleave", () =>
        cursor.classList.remove("hovered")
      );
    });
  }

  // ----------- CONTEXT MENU -----------
  createContextMenu() {
    const menu = document.createElement("div");
    menu.className = "custom-context-menu";
    menu.innerHTML = `
      <ul>
        <li><a href="#" data-action="reload">Sayfayı Yenile</a></li>
        <li><a href="#" data-action="scrollTop">Sayfanın Üstüne Git</a></li>
        <li><a href="#" data-action="goHome">Anasayfaya Git</a></li>
      </ul>
    `;
    document.body.appendChild(menu);
    this.contextMenu = menu;
  }

  initContextMenu() {
    const menu = this.contextMenu;

    window.addEventListener("contextmenu", (e) => {
      e.preventDefault();
      this.showContextMenu(e.clientX, e.clientY);
    });

    window.addEventListener("click", () => this.hideContextMenu());
    window.addEventListener("keydown", (e) => {
      if (e.key === "Escape") this.hideContextMenu();
    });

    menu.querySelectorAll("a[data-action]").forEach((item) => {
      item.addEventListener("click", (e) => {
        e.preventDefault();
        this.handleMenuAction(item.dataset.action);
        this.hideContextMenu();
      });
    });
  }

  showContextMenu(x, y) {
    const menu = this.contextMenu;
    menu.style.display = "block";
    const { innerWidth, innerHeight } = window;
    const rect = menu.getBoundingClientRect();
    const left = x + rect.width > innerWidth ? x - rect.width : x;
    const top = y + rect.height > innerHeight ? y - rect.height : y;
    menu.style.left = `${left}px`;
    menu.style.top = `${top}px`;

    const elementAtPoint = document.elementFromPoint(x, y);
    let isDark = false;
    let el = elementAtPoint;
    while (el) {
      if (
        el.classList &&
        (el.classList.contains("dark") || el.classList.contains("darktt"))
      ) {
        isDark = true;
        break;
      }
      el = el.parentElement;
    }

    if (isDark) {
      menu.classList.add("darkt");
      menu.classList.remove("lightt");
    } else {
      menu.classList.add("lightt");
      menu.classList.remove("darkt");
    }
  }

  hideContextMenu() {
    if (this.contextMenu) this.contextMenu.style.display = "none";
  }

  handleMenuAction(action) {
    switch (action) {
      case "reload":
        location.reload();
        break;
      case "scrollTop":
        window.scrollTo({ top: 0, behavior: "smooth" });
        break;
      case "goHome":
        window.location.href = "/";
        break;
      default:
        console.warn("Unknown action:", action);
    }
  }

  // ----------- CUSTOM SELECT DROPDOWN -----------
  initCustomSelects() {
    const wrappers = document.querySelectorAll(".custom-select-wrapper");

    wrappers.forEach((wrapper) => {
      const select = wrapper.querySelector("select");
      const trigger = wrapper.querySelector(".custom-select-trigger");
      const optionsContainer = wrapper.querySelector(".custom-options");
      const options = optionsContainer.querySelectorAll(".custom-option");

      trigger.addEventListener("click", () => {
        const isOpen = optionsContainer.classList.contains("open");
        this.closeAllCustomSelects();
        if (!isOpen) {
          optionsContainer.classList.add("open");
          trigger.setAttribute("aria-expanded", "true");
          options[0]?.focus();
        }
      });

      document.addEventListener("click", (e) => {
        if (!wrapper.contains(e.target)) {
          optionsContainer.classList.remove("open");
          trigger.setAttribute("aria-expanded", "false");
        }
      });

      options.forEach((option) => {
        option.addEventListener("click", () => {
          this.selectOption(option, trigger, select, optionsContainer);
        });

        option.addEventListener("keydown", (e) => {
          switch (e.key) {
            case "Enter":
            case " ":
              e.preventDefault();
              this.selectOption(option, trigger, select, optionsContainer);
              break;
            case "ArrowDown":
              e.preventDefault();
              option.nextElementSibling?.focus();
              break;
            case "ArrowUp":
              e.preventDefault();
              if (option.previousElementSibling)
                option.previousElementSibling.focus();
              else trigger.focus();
              break;
            case "Escape":
              optionsContainer.classList.remove("open");
              trigger.setAttribute("aria-expanded", "false");
              trigger.focus();
              break;
          }
        });
      });

      const initialValue = select.value || select.options[0]?.value;
      const initialOption = Array.from(options).find(
        (opt) => opt.dataset.value === initialValue
      );
      if (initialOption) {
        trigger.textContent = initialOption.textContent;
        initialOption.classList.add("selected");
        select.value = initialValue;
      }
    });
  }

  selectOption(option, trigger, select, optionsContainer) {
    trigger.textContent = option.textContent;

    option.parentElement
      .querySelectorAll(".custom-option")
      .forEach((opt) => opt.classList.remove("selected"));

    option.classList.add("selected");
    select.value = option.dataset.value;
    optionsContainer.classList.remove("open");
    trigger.setAttribute("aria-expanded", "false");
    trigger.focus();

    select.dispatchEvent(new Event("change"));
  }

  closeAllCustomSelects() {
    document
      .querySelectorAll(".custom-options.open")
      .forEach((openDropdown) => {
        openDropdown.classList.remove("open");
        openDropdown.parentElement
          .querySelector(".custom-select-trigger")
          .setAttribute("aria-expanded", "false");
      });
  }

  // ----------- REGISTER FORM LOGIC -----------
  initRegisterForm() {
    this.showStep(this.currentStep);

    this.nextButtons.forEach((btn) => {
      btn.addEventListener("click", async (e) => {
        e.preventDefault();

        const targetStep = parseInt(btn.dataset.nextStep);

        if (this.currentStep === 1) {
          const valid = await this.validateStep1();
          if (!valid) return;
        }

        this.currentStep = targetStep - 1;
        this.showStep(this.currentStep);
      });
    });

    // Real-time checks
    this.usernameInput.addEventListener("blur", () => {
      console.log("Username input blurred");
      if (document.querySelector("body.register")) {
        console.log("Checking username on blur");
        this.checkUsername();
      }
    });
    this.emailInput.addEventListener("blur", () => {
      if (document.querySelector("body.register")) {
        this.checkEmail();
      }
    });
    this.pass1Input.addEventListener("blur", () => {
      if (document.querySelector("body.register")) {
        this.checkPassword1();
      }
    });
    this.pass2Input.addEventListener("blur", () => {
      if (document.querySelector("body.register")) {
        this.checkPassword2();
      }
    });

    // Remove empty error divs on load
    document.querySelectorAll(".field-error").forEach((el) => {
      if (!el.textContent.trim()) {
        el.remove();
      }
    });
  }

  showStep(index) {
    this.steps.forEach((step, i) => {
      step.classList.toggle("active", i === index);
    });
  }

  showError(input, message) {
    let errorDiv = input.parentNode.querySelector(".field-error");

    if (!errorDiv && message) {
      errorDiv = document.createElement("div");
      errorDiv.className = "field-error";
      input.parentNode.appendChild(errorDiv);
    }

    if (errorDiv) {
      if (message) {
        errorDiv.innerHTML = `<p>${message}</p>`;
        input.classList.add("error");
      } else {
        errorDiv.remove();
        input.classList.remove("error");
      }
    }
  }

  clearErrors(inputs) {
    inputs.forEach((input) => {
      this.showError(input, "");
      input.setCustomValidity("");
    });
  }

  async checkUsername() {
    const username = this.usernameInput.value.trim();

    if (!username) {
      this.showError(this.usernameInput, "Bu alan boş bırakılamaz.");
      this.usernameInput.setCustomValidity("Bu alan boş bırakılamaz.");
      return;
    }

    try {
      console.log("Checking username:", username);
      const res = await fetch(
        `/users/ajax/check-username/?username=${encodeURIComponent(username)}`,
        {
          method: "GET",
          headers: {
            Accept: "application/json",
          },
        }
      );
      const data = await res.json();
      if (data.is_taken) {
        this.showError(this.usernameInput, "Bu kullanıcı adı zaten alınmış.");
        this.usernameInput.setCustomValidity("Bu kullanıcı adı zaten alınmış.");
      } else {
        this.showError(this.usernameInput, "");
        this.usernameInput.setCustomValidity("");
      }
    } catch {
      this.showError(this.usernameInput, "");
      this.usernameInput.setCustomValidity("");
    }
  }

  async checkEmail() {
    const email = this.emailInput.value.trim();

    if (!email) {
      this.showError(this.emailInput, "Bu alan boş bırakılamaz.");
      this.emailInput.setCustomValidity("Bu alan boş bırakılamaz.");
      return;
    }

    try {
      const res = await fetch(
        `/users/ajax/check-email/?email=${encodeURIComponent(email)}`,
        {
          method: "GET",
          headers: {
            Accept: "application/json",
          },
        }
      );
      const data = await res.json();
      if (data.is_taken) {
        this.showError(this.emailInput, "Bu email zaten kullanımda.");
        this.emailInput.setCustomValidity("Bu email zaten kullanımda.");
      } else {
        this.showError(this.emailInput, "");
        this.emailInput.setCustomValidity("");
      }
    } catch {
      this.showError(this.emailInput, "");
      this.emailInput.setCustomValidity("");
    }
  }

  async checkPassword1() {
    const password = this.pass1Input.value;

    if (!password) {
      this.showError(this.pass1Input, "");
      this.pass1Input.setCustomValidity("");
      return;
    }

    try {
      const res = await fetch("/users/ajax/check-password/", {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          "X-CSRFToken": this.csrfToken,
        },
        body: JSON.stringify({
          password: this.pass1Input.value,
          username: this.usernameInput.value.trim(),
        }),
      });

      if (!res.ok) throw new Error(`HTTP error! status: ${res.status}`);
      const data = await res.json();

      if (!data.valid) {
        const message = data.errors.join(" ");
        this.showError(this.pass1Input, message);
        this.pass1Input.setCustomValidity(message);
      } else {
        this.showError(this.pass1Input, "");
        this.pass1Input.setCustomValidity("");
      }
    } catch (error) {
      console.error("Password validation error:", error);
      this.showError(this.pass1Input, "");
      this.pass1Input.setCustomValidity("");
    }
  }

  checkPassword2() {
    if (
      this.pass1Input.value &&
      this.pass2Input.value &&
      this.pass1Input.value !== this.pass2Input.value
    ) {
      this.showError(this.pass2Input, "Şifreler eşleşmiyor.");
      this.pass2Input.setCustomValidity("Şifreler eşleşmiyor.");
    } else {
      this.showError(this.pass2Input, "");
      this.pass2Input.setCustomValidity("");
    }
  }

  async validateStep1() {
    let hasError = false;

    const username = this.usernameInput.value.trim();
    const email = this.emailInput.value.trim();
    const pass1 = this.pass1Input.value;
    const pass2 = this.pass2Input.value;

    this.clearErrors([
      this.usernameInput,
      this.emailInput,
      this.pass1Input,
      this.pass2Input,
    ]);

    if (!username) {
      this.showError(this.usernameInput, "Bu alan boş bırakılamaz.");
      this.usernameInput.setCustomValidity("Bu alan boş bırakılamaz.");
      hasError = true;
    }

    if (!email) {
      this.showError(this.emailInput, "Bu alan boş bırakılamaz.");
      this.emailInput.setCustomValidity("Bu alan boş bırakılamaz.");
      hasError = true;
    }

    if (!pass1) {
      this.showError(this.pass1Input, "Bu alan boş bırakılamaz.");
      this.pass1Input.setCustomValidity("Bu alan boş bırakılamaz.");
      hasError = true;
    }

    if (!pass2) {
      this.showError(this.pass2Input, "Bu alan boş bırakılamaz.");
      this.pass2Input.setCustomValidity("Bu alan boş bırakılamaz.");
      hasError = true;
    }

    if (pass1 && pass2 && pass1 !== pass2) {
      this.showError(this.pass2Input, "Şifreler eşleşmiyor.");
      this.pass2Input.setCustomValidity("Şifreler eşleşmiyor.");
      hasError = true;
    }

    return !hasError;
  }
}

// Logo span animation
document.querySelectorAll(".logo span").forEach((el, idx) => {
  el.style.setProperty("--i", idx);
});

document.addEventListener("DOMContentLoaded", () => {
  const app = new App({
    selector: "#countdown",
    targetDate: "2025-08-08T20:00:00",
  });
  app.start();
});

document.addEventListener("click", (e) => {
  const btn = e.target.closest(".btn--csv");
  if (!btn) return;
  btn.classList.add("is-loading");
  btn.setAttribute("aria-busy", "true");
  // export tamamlanınca:
  // btn.classList.remove('is-loading'); btn.removeAttribute('aria-busy');
});

document.addEventListener("DOMContentLoaded", () => {
  const burger = document.getElementById("hamburger");
  const menu = document.getElementById("siteMenu");
  const closer = menu?.querySelector(".menu-close");
  const backdrop = document.getElementById("navBackdrop");

  const toggle = (open) => {
    const willOpen = open ?? !menu.classList.contains("is-open");
    menu.classList.toggle("is-open", willOpen);
    burger?.classList.toggle("is-open", willOpen);
    burger?.setAttribute("aria-expanded", willOpen ? "true" : "false");
    backdrop?.classList.toggle("is-show", willOpen);
    if (willOpen) backdrop?.removeAttribute("hidden");
    else backdrop?.setAttribute("hidden", "");
    document.body.classList.toggle("no-scroll", willOpen);
  };

  burger?.addEventListener("click", () => toggle());
  closer?.addEventListener("click", () => toggle(false));
  backdrop?.addEventListener("click", () => toggle(false));
  menu?.addEventListener("click", (e) => {
    if (e.target.closest("a")) toggle(false);
  });
  document.addEventListener("keydown", (e) => {
    if (e.key === "Escape") toggle(false);
  });
  window.addEventListener("resize", () => {
    if (window.innerWidth > 992) toggle(false);
  });
});

(function () {
  function fitPreview(frame) {
    const baseW = Number(frame.dataset.baseW || 390); // şablonun tasarım genişliği
    const maxH = Number(frame.dataset.maxH || 260); // izin verilen maksimum yükseklik
    const canvas = frame.querySelector(".inv-preview-canvas");
    if (!canvas) return;

    // önce reset
    canvas.style.transform = "scale(1)";
    frame.style.height = "";

    // genişliğe göre ölçek: frame %100 genişliğe yayılıyor
    const scale = frame.clientWidth / baseW;
    canvas.style.transform = `scale(${scale})`;

    // oluşan gerçek yükseklik
    const contentH =
      (canvas.scrollHeight || canvas.getBoundingClientRect().height) * scale;

    // yükseklik sınırı: maxH’ı aşarsa kırp (overflow: hidden sayesinde)
    frame.style.height = Math.min(contentH, maxH) + "px";
  }

  function init() {
    const frames = document.querySelectorAll(".inv-preview-frame");
    const rerun = () => frames.forEach(fitPreview);

    // ilk
    rerun();

    // görseller yüklendikçe
    frames.forEach((f) => {
      f.querySelectorAll("img,video").forEach((m) => {
        m.addEventListener("load", () => fitPreview(f));
      });
    });

    // resize
    window.addEventListener("resize", rerun);

    // font/render sonrası 1 tick
    requestAnimationFrame(rerun);
    window.addEventListener("load", rerun);
  }

  document.addEventListener("DOMContentLoaded", init);
})();
