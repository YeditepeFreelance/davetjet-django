document.addEventListener("DOMContentLoaded", () => {
  // Elements
  const subscribeBtns = document.querySelectorAll(".fs-choose-btn");
  const triggerBtns = document.querySelectorAll(".fs-trigger-btn");
  const subscriptionModal = document.getElementById("fsSubscriptionModal");
  const paymentModal = subscriptionModal.querySelector(".fs-payment-modal");
  const paymentModalContent = paymentModal.querySelector(
    ".fs-payment-modal-content"
  );
  const cardInner = paymentModal.querySelector(".fs-card-inner");
  const paymentForm = paymentModal.querySelector(".fs-payment-form");

  // Card display elements
  const cardNumberDisplay = paymentModal.querySelector("#fsCardNumberDisplay");
  const cardNameDisplay = paymentModal.querySelector("#fsCardNameDisplay");
  const cardExpiryDisplay = paymentModal.querySelector("#fsCardExpiryDisplay");
  const cardCvvDisplay = paymentModal.querySelector("#fsCardCvvDisplay");

  // Inputs
  const inputCardNumber = paymentForm.querySelector("#fsCardNumber");
  const inputCardName = paymentForm.querySelector("#fsCardholderName");
  const inputExpiry = paymentForm.querySelector("#fsExpiryDate");
  const inputCvv = paymentForm.querySelector("#fsCvv");

  // Open subscription modal when .fs-trigger-btn clicked
  triggerBtns.forEach((btn) => {
    btn.addEventListener("click", (e) => {
      e.preventDefault();
      toggleSubscriptionModal(true);
      // Reset payment modal state
      hidePaymentModal();
    });
  });

  // Open payment modal from clicked subscribe button position inside subscription modal
  subscribeBtns.forEach((btn) => {
    btn.addEventListener("click", (e) => {
      e.preventDefault();

      // Get button position for animation origin
      const btnRect = btn.getBoundingClientRect();

      // Position payment modal content on button
      paymentModalContent.style.transformOrigin = "top left";
      paymentModalContent.style.position = "fixed";
      paymentModalContent.style.top = `${btnRect.top}px`;
      paymentModalContent.style.left = `${btnRect.left}px`;
      paymentModalContent.style.width = `${btnRect.width}px`;
      paymentModalContent.style.height = `${btnRect.height}px`;
      paymentModalContent.style.opacity = "0";
      paymentModalContent.style.transition = "opacity 0.5s ease";

      // Show payment modal background
      paymentModal.classList.remove("hidden");

      // Force reflow to apply styles before animating
      void paymentModalContent.offsetWidth;

      // Animate payment modal content to center and full size
      paymentModalContent.style.top = "50%";
      paymentModalContent.style.left = "50%";
      paymentModalContent.style.width = "700px";
      paymentModalContent.style.height = "auto";
      paymentModalContent.style.opacity = "1";
      paymentModalContent.style.transform = "translate(-50%, -50%) scale(1)";

      // Reset form and card visuals
      paymentForm.reset();
      cardNumberDisplay.textContent = "#### #### #### ####";
      cardNameDisplay.textContent = "CARDHOLDER NAME";
      cardExpiryDisplay.textContent = "MM/YY";
      cardCvvDisplay.textContent = "***";

      // Reset card flip
      cardInner.classList.remove("flipped");

      // Focus cardholder name input
      inputCardName.focus();
    });
  });

  // Close payment modal
  paymentModal
    .querySelector(".fs-payment-close-btn")
    .addEventListener("click", () => {
      hidePaymentModal();
    });

  function hidePaymentModal() {
    paymentModalContent.style.transform = "scale(0.8)";
    paymentModal.classList.add("hidden");
    // Reset styles after animation
    paymentModalContent.style.position = "";
    paymentModalContent.style.top = "";
    paymentModalContent.style.left = "";
    paymentModalContent.style.width = "";
    paymentModalContent.style.height = "";
    paymentModalContent.style.transform = "";
    paymentModalContent.style.transition = "";
  }

  // Card input formatting and display updates
  function formatCardNumber(value) {
    return value
      .replace(/\D/g, "")
      .replace(/(.{4})/g, "$1 ")
      .trim();
  }

  inputCardNumber.addEventListener("input", () => {
    const formatted = formatCardNumber(inputCardNumber.value);
    inputCardNumber.value = formatted;
    cardNumberDisplay.textContent = formatted || "#### #### #### ####";
  });

  inputCardName.addEventListener("input", () => {
    cardNameDisplay.textContent =
      inputCardName.value.toUpperCase() || "CARDHOLDER NAME";
  });

  inputExpiry.addEventListener("input", () => {
    cardExpiryDisplay.textContent = inputExpiry.value || "MM/YY";
  });

  inputCvv.addEventListener("input", () => {
    cardCvvDisplay.textContent = "***";
  });

  // Flip card front/back on CVV and expiry focus/blur
  function flipCard(flip) {
    if (flip) {
      cardInner.classList.add("flipped");
    } else {
      cardInner.classList.remove("flipped");
    }
  }

  inputCvv.addEventListener("focus", () => flipCard(true));
  inputExpiry.addEventListener("focus", () => flipCard(true));
  inputCardNumber.addEventListener("focus", () => flipCard(false));
  inputCardName.addEventListener("focus", () => flipCard(false));

  [inputCvv, inputExpiry].forEach((input) => {
    input.addEventListener("blur", () => {
      setTimeout(() => {
        if (
          document.activeElement !== inputCvv &&
          document.activeElement !== inputExpiry
        ) {
          flipCard(false);
        }
      }, 100);
    });
  });

  // Submit handler (replace alert with real payment logic)
  paymentForm.addEventListener("submit", (e) => {
    e.preventDefault();
    alert("Payment submitted!");
    paymentModal.querySelector(".fs-payment-close-btn").click();
  });

  // Billing toggle buttons
  const billingToggleOptions = document.querySelectorAll(".fs-toggle-option");
  billingToggleOptions.forEach((option) => {
    option.addEventListener("click", () => {
      billingToggleOptions.forEach((opt) => opt.classList.remove("active"));
      option.classList.add("active");
      const selectedBilling = option.dataset.plan; // "monthly" or "yearly"
      updatePrices(selectedBilling);
    });
  });

  function updatePrices(billingType) {
    const priceEls = document.querySelectorAll(".fs-price");
    priceEls.forEach((el) => {
      const price = el.dataset[billingType] || "";
      el.textContent = price;
    });
  }

  // Function to show/hide subscription modal
  function toggleSubscriptionModal(show = false) {
    if (show) {
      subscriptionModal.classList.remove("hidden");
      document.body.style.overflow = "hidden";
      subscriptionModal.focus();
    } else {
      subscriptionModal.classList.add("hidden");
      document.body.style.overflow = "";
      // Also close payment modal if open
      hidePaymentModal();
    }
  }

  // Close subscription modal close button
  document
    .querySelector(".fs-subscription-close-btn")
    .addEventListener("click", () => {
      toggleSubscriptionModal(false);
    });

  // Expose toggle function globally for .fs-trigger-btn usage if needed
  window.toggleSubscriptionModal = toggleSubscriptionModal;
});
