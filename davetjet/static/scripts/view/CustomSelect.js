export default function initCustomSelects() {
  const selects = document.querySelectorAll(".custom-select");

  selects.forEach((select) => {
    const input = select.querySelector("input");
    const options = select.querySelectorAll(".custom-option");

    options.forEach((option) => {
      option.addEventListener("click", () => {
        input.value = option.textContent;
        select.classList.remove("open");
      });
    });

    input.addEventListener("focus", () => select.classList.add("open"));
    input.addEventListener("blur", () => {
      setTimeout(() => select.classList.remove("open"), 200);
    });
  });
}
