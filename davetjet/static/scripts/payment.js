// Billing toggle switch
document.querySelectorAll(".toggle-option").forEach((btn) => {
  btn.addEventListener("click", (e) => {
    document
      .querySelectorAll(".toggle-option")
      .forEach((b) => b.classList.remove("active"));
    btn.classList.add("active");

    const selected = btn.dataset.plan;
    const isYearly = e.target.dataset.plan === "yearly";
    document.querySelectorAll(".plan-card .price").forEach((priceEl) => {
      priceEl.textContent = isYearly
        ? priceEl.getAttribute("data-yearly")
        : priceEl.getAttribute("data-monthly");
    });
  });
});

// Modal handling
document.querySelectorAll(".choose-btn").forEach((btn) =>
  btn.addEventListener("click", () => {
    toggleModal(true);
  })
);

function toggleModal(show) {
  document.getElementById("paymentModal").classList.toggle("hidden", !show);
  if (show) {
    // Reset form and virtual card
    paymentForm.reset();
    resetVirtualCard();
    paymentForm.classList.remove("loading", "error");
    clearErrors();
    document.getElementById("cardholderName").focus();
  }
}

const paymentForm = document.querySelector(".payment-form");
const cardNumberInput = paymentForm.querySelector("#cardNumber");
const cardNameInput = paymentForm.querySelector("#cardholderName");
const expiryInput = paymentForm.querySelector("#expiryDate");
const cvvInput = paymentForm.querySelector("#cvv");

const cardNumberDisplay = document.getElementById("cardNumberDisplay");
const cardNameDisplay = document.getElementById("cardNameDisplay");
const cardExpiryDisplay = document.getElementById("cardExpiryDisplay");
const cardCvvDisplay = document.getElementById("cardCvvDisplay");

const cardInner = document.querySelector(".card-inner");

// Update virtual card in real time
cardNumberInput.addEventListener("input", () => {
  let val = cardNumberInput.value.replace(/\D/g, "").substring(0, 16);
  let formatted = val.replace(/(.{4})/g, "$1 ").trim();
  cardNumberInput.value = formatted;
  cardNumberDisplay.textContent = formatted || "#### #### #### ####";
});

cardNameInput.addEventListener("input", () => {
  cardNameDisplay.textContent =
    cardNameInput.value.toUpperCase() || "CARDHOLDER NAME";
});

expiryInput.addEventListener("input", () => {
  let val = expiryInput.value.replace(/[^\d\/]/g, "").substring(0, 5);
  if (val.length === 2 && !val.includes("/")) {
    val = val + "/";
  }
  expiryInput.value = val;
  cardExpiryDisplay.textContent = val || "MM/YY";
});

cvvInput.addEventListener("input", () => {
  let val = cvvInput.value.replace(/\D/g, "").substring(0, 4);
  cvvInput.value = val;
  cardCvvDisplay.textContent = val ? "*".repeat(val.length) : "***";
});

// Flip card on focus expiry/cvv
expiryInput.addEventListener("focus", () => {
  cardInner.classList.add("flipped");
});
cvvInput.addEventListener("focus", () => {
  cardInner.classList.add("flipped");
});
expiryInput.addEventListener("blur", () => {
  cardInner.classList.remove("flipped");
});
cvvInput.addEventListener("blur", () => {
  cardInner.classList.remove("flipped");
});

// Reset virtual card display to defaults
function resetVirtualCard() {
  cardNumberDisplay.textContent = "#### #### #### ####";
  cardNameDisplay.textContent = "CARDHOLDER NAME";
  cardExpiryDisplay.textContent = "MM/YY";
  cardCvvDisplay.textContent = "***";
  cardInner.classList.remove("flipped");
}

// Simple UI validation and loading simulation
paymentForm.addEventListener("submit", (e) => {
  e.preventDefault();
  clearErrors();
  let valid = true;

  if (!cardNameInput.value.trim()) {
    setError(cardNameInput, "Please enter cardholder name");
    valid = false;
  }
  if (cardNumberInput.value.replace(/\s/g, "").length < 13) {
    setError(cardNumberInput, "Invalid card number");
    valid = false;
  }
  if (!/^\d{2}\/\d{2}$/.test(expiryInput.value)) {
    setError(expiryInput, "Invalid expiry date");
    valid = false;
  }
  if (cvvInput.value.length < 3) {
    setError(cvvInput, "Invalid CVC");
    valid = false;
  }

  if (!valid) return;

  paymentForm.classList.add("loading");
  document.querySelector(".pay-btn").textContent = "Processing...";

  // Simulate payment delay
  setTimeout(() => {
    paymentForm.classList.remove("loading");
    document.querySelector(".pay-btn").textContent = "Pay";
    alert("Payment processed (simulated)");
    toggleModal(false);
  }, 2000);
});

function setError(input, message) {
  input.classList.add("error");
  input.nextElementSibling.textContent = message;
}
function clearErrors() {
  paymentForm
    .querySelectorAll(".error")
    .forEach((i) => i.classList.remove("error"));
  paymentForm
    .querySelectorAll(".error-message")
    .forEach((msg) => (msg.textContent = ""));
}

// FS Subscription Modal
