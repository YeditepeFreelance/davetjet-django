const notificationTrigger = document.querySelector(".notification-trigger");
const notificationWrapper = document.getElementById("notificationWrapper");
const notificationList = document.getElementById("notificationList");
const badge = document.getElementById("notificationBadge");
const notificationSound = document.getElementById("notificationSound");
let userHasInteracted = false;

// Track if user has interacted
document.addEventListener("click", () => {
  userHasInteracted = true;
});

function playNotificationSound() {
  if (!userHasInteracted || !notificationSound) return;
  notificationSound.currentTime = 0;
  notificationSound.play().catch((err) => {
    console.warn("Notification sound blocked:", err);
  });
}

notificationTrigger.addEventListener("click", () => {
  notificationWrapper.classList.toggle("hidden");
  badge.classList.add("hidden");
});

document.addEventListener("click", function (e) {
  if (e.target.classList.contains("notification-close-btn")) {
    const notif = e.target.closest(".notification");
    notif.classList.add("fade-out");
    setTimeout(() => notif.remove(), 300);
  }
});

function addNotification(title, content, time = "Just now") {
  const div = document.createElement("div");
  div.className = "notification unread";
  div.innerHTML = `
    <span class="icon">🔔</span>
    <div class="message">
      <p><strong>${title}</strong> ${content}</p>
      <small>${time}</small>
    </div>
    <button class="notification-close-btn">&times;</button>
  `;

  // Animate in
  requestAnimationFrame(() => {
    div.classList.add("slide-in");
  });

  notificationList.prepend(div);

  // Limit to 3 notifications
  if (notificationList.children.length > 3) {
    notificationList.removeChild(notificationList.lastElementChild);
  }

  // Show pulse badge
  badge.classList.remove("hidden");

  // Play sound
  playNotificationSound();
}

// Example call
setTimeout(() => {
  addNotification("New Message", "from Admin", "1 min ago");
}, 1500);
