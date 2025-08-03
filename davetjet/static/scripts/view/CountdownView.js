export default class CountdownView {
  constructor(containerSelector) {
    this.container = document.querySelector(containerSelector);
    this.previousValues = null;
  }

  render({ days, hours, minutes, seconds }) {
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
          </div>`;
      })
      .join("");

    this.previousValues = { days, hours, minutes, seconds };
  }

  showMessage(message) {
    this.container.innerHTML = `<div class="launch-message">${message}</div>`;
  }
}
