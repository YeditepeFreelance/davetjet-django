document.addEventListener("DOMContentLoaded", () => {
  const modalOverlay = document.getElementById("app-modal");
  const modalContent = document.getElementById("modal-content");
  const closeBtn = document.getElementById("modal-close");
  const modalExits = document.querySelectorAll(".exit-modal");

  const openModal = (type = "info", content = {}) => {
    modalContent.className = "modal modal--" + type;
    if (content.title)
      modalContent.querySelector(".modal__title").innerText = content.title;
    if (content.body)
      modalContent.querySelector(".modal__body").innerHTML = content.body;
    if (content.footer)
      modalContent.querySelector(".modal__footer").innerHTML = content.footer;

    modalOverlay.classList.add("is-active");
    modalContent.focus();
  };

  const closeModal = () => {
    modalOverlay.classList.remove("is-active");
  };

  closeBtn.addEventListener("click", closeModal);
  modalOverlay.addEventListener("click", (e) => {
    if (e.target === modalOverlay) closeModal();
  });

  document.addEventListener("keydown", (e) => {
    if (e.key === "Escape") closeModal();
  });

  // Optional: expose for global use
  window.AppModal = { open: openModal, close: closeModal };
});
