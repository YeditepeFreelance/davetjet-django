(function () {
  const bar = document.getElementById("msgbar");
  if (!bar) return;

  // İkon seti (FA varsa onu, yoksa emoji)
  const hasFA = !!document.querySelector(
    'link[href*="fontawesome"], link[href*="font-awesome"], script[src*="fontawesome"]'
  );
  const icons = {
    info: hasFA ? '<i class="fas fa-info-circle"></i>' : "ℹ️",
    success: hasFA ? '<i class="fas fa-check-circle"></i>' : "✅",
    warning: hasFA ? '<i class="fas fa-exclamation-triangle"></i>' : "⚠️",
    error: hasFA ? '<i class="fas fa-times-circle"></i>' : "❌",
  };

  const queue = Array.from(bar.querySelectorAll(".dj-msg"));
  let showing = false;

  function showNext() {
    if (showing) return;
    const item = queue.shift();
    if (!item) return;
    showing = true;

    // ikon
    const cls = (item.className.match(/\b(info|success|warning|error)\b/) || [
      "info",
    ])[0];
    const iconEl = item.querySelector(".icon");
    if (iconEl) iconEl.innerHTML = icons[cls];

    // progress
    const timeout = parseInt(item.getAttribute("data-timeout") || "5000", 10);
    const progress = item.querySelector(".progress");
    let t0;
    if (timeout > 0 && progress) {
      progress.style.transition = `transform ${timeout}ms linear`;
      // Reflow:
      progress.getBoundingClientRect();
      progress.style.transform = "scaleX(0)";
    }

    // kapatma
    const close = () => {
      item.style.transition = "opacity .2s ease, transform .2s ease";
      item.style.opacity = "0";
      item.style.transform = "translateY(-6px)";
      setTimeout(() => {
        item.remove();
        showing = false;
        showNext();
      }, 200);
    };
    item.querySelector(".close")?.addEventListener("click", close);
    document.addEventListener(
      "keydown",
      (e) => {
        if (e.key === "Escape") close();
      },
      { once: true }
    );

    // auto-dismiss
    if (timeout > 0) {
      setTimeout(close, timeout);
    }

    // Göster
    item.style.willChange = "transform,opacity";
    // (CSS animasyonu zaten var; burada sıraya alıyoruz)
    // Birden fazla varsa sırayla görünsün:
    if (queue.length > 0) {
      // Sonrakini, bu kaybolduktan sonra göstereceğiz
    }
  }

  // Hepsini sıraya sok: birer birer göster
  // İlkini hemen göster, bitince sıradaki…
  function runQueue() {
    // Tüm mesajları üst üste koymak yerine sırala:
    const items = Array.from(bar.children);
    // İlk dışındaki elemanları gizle (DOM’da dursun)
    items.slice(1).forEach((el) => (el.style.display = "none"));
    // İlkini göster; kapanınca sıradakini display:block yapıp showNext()
    // Ancak biz daha basit bir kuyruk kullanacağız:
    // -> display:block yapalım ki ölçüler alınsın, görsel geçiş CSS ile zaten.
    queue.forEach((el) => (el.style.display = "block"));
    showing = false;
    // İlk mesajı tetikle
    showNext();
    // Her kapanışta showNext tekrar çağrılacak.
  }

  runQueue();
})();
