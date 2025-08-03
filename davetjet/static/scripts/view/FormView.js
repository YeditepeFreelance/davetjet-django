export default function initRegisterForm() {
  const form = document.querySelector("form");
  if (!form) return;

  form.addEventListener("submit", (e) => {
    const email = form.querySelector('input[type="email"]');
    const password = form.querySelector('input[type="password"]');

    if (!email.value || !password.value) {
      e.preventDefault();
      alert("Lütfen tüm alanları doldurun.");
    }

    // Optionally add client-side feedback styling here
  });
}
