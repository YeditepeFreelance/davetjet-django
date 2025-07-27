class App {
  constructor({ selector, targetDate }) {
    this.container = document.querySelector(selector);
    this.targetDate = new Date(targetDate);
    this.interval = null;

    this.setupCursor();
    this.createContextMenu();
    this.initContextMenu();
  }

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

  // --- CURSOR ---
  setupCursor() {
    const cursor = document.querySelector(".custom-cursor");
    let mouseX = 0,
      mouseY = 0;
    let currentX = 0,
      currentY = 0;
    const speed = 0.15; // lower is smoother, slower

    // Track real mouse position
    window.addEventListener("mousemove", (e) => {
      mouseX = e.clientX;
      mouseY = e.clientY;
    });

    // Animate trailing motion
    const animate = () => {
      currentX += (mouseX - currentX) * speed;
      currentY += (mouseY - currentY) * speed;
      cursor.style.transform = `translate(${currentX}px, ${currentY}px) translate(-50%, -50%)`;
      requestAnimationFrame(animate);
    };
    animate();

    // Handle hover states
    const hoverables = document.querySelectorAll("button, a, .hover-target");
    hoverables.forEach((el) => {
      el.addEventListener("mouseenter", () => cursor.classList.add("hovered"));
      el.addEventListener("mouseleave", () =>
        cursor.classList.remove("hovered")
      );
    });
  }

  // --- RIGHT CLICK ---
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

    // Show menu on right-click
    window.addEventListener("contextmenu", (e) => {
      e.preventDefault();
      this.showContextMenu(e.clientX, e.clientY);
    });

    // Hide on click outside or ESC
    window.addEventListener("click", () => this.hideContextMenu());
    window.addEventListener("keydown", (e) => {
      if (e.key === "Escape") this.hideContextMenu();
    });

    // Add functionality
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
}

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
