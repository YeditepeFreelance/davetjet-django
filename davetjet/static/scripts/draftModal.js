document.addEventListener("DOMContentLoaded", () => {
  const openDraftBtn = document.getElementById("openDraftsBtn");
  const modal = document.querySelector(".draft-modal");
  const closeBtns = modal.querySelectorAll(
    ".close-btn, #closeModalBtn, #closeDrafts"
  );
  const draftList = modal.querySelector(".draft-list");
  const emptyMsg = modal.querySelector(".empty-message");

  // Örnek veri - backend bağlanana kadar
  let drafts = [
    {
      id: 1,
      title: "Ayşe & Ahmet - Düğün",
      date: "2025-08-06",
    },
    {
      id: 2,
      title: "Doğum Günü 2025",
      date: "2025-07-22",
    },
  ];

  // Modal Aç
  openDraftBtn?.addEventListener("click", () => {
    modal.classList.remove("hidden");
    document.body.classList.add("modal-open"); // arkaplan blur JS ile yapılacaksa
    renderDrafts();
  });

  // Modal Kapat
  closeBtns.forEach((btn) => {
    btn.addEventListener("click", () => {
      modal.classList.add("hidden");
      document.body.classList.remove("modal-open");
    });
  });

  // ESC ile modal kapat
  document.addEventListener("keydown", (e) => {
    if (e.key === "Escape") {
      modal.classList.add("hidden");
      document.body.classList.remove("modal-open");
    }
  });

  // Taslakları listele
  function renderDrafts() {
    draftList.innerHTML = "";

    if (drafts.length === 0) {
      emptyMsg.classList.remove("hidden");
      return;
    }

    emptyMsg.classList.add("hidden");

    drafts.forEach((draft) => {
      const card = document.createElement("div");
      card.classList.add("draft-card");

      card.innerHTML = `
        <div class="draft-header">
          <h4>${draft.title}</h4>
          <div class="draft-actions">
            <button class="delete-draft" data-id="${draft.id}">&times;</button>
            <button class="load-draft" data-id="${draft.id}">Yükle</button>
          </div>
        </div>
        <p class="draft-date">${draft.date}</p>
      `;

      // Taslak kartına tıklanabilir alan
      card.addEventListener("click", () => {
        alert(`"${draft.title}" taslağı yüklendi (simülasyon).`);
        modal.classList.add("hidden");
        document.body.classList.remove("modal-open");
        // Burada form dolumu yapılabilir
      });

      // Sadece sil butonu tıklanınca silsin
      const deleteBtn = card.querySelector(".delete-draft");
      deleteBtn.addEventListener("click", (e) => {
        e.stopPropagation(); // kart tıklanmasını engeller
        const id = Number(deleteBtn.dataset.id);
        drafts = drafts.filter((d) => d.id !== id);
        renderDrafts();
      });

      draftList.appendChild(card);
    });
  }
});
