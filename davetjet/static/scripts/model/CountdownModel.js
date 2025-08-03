export default class CountdownModel {
  constructor(targetDate) {
    this.targetDate = new Date(targetDate);
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
}
