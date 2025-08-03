import CountdownModel from "../model/CountdownModel.js";
import CountdownView from "../view/CountdownView.js";
import initCursor from "../view/CursorView.js";
import initContextMenu from "../view/ContextMenuView.js";
import initCustomSelects from "../view/CustomSelect.js";
import initRegisterForm from "../view/FormView.js";

export default class AppController {
  constructor({ selector, targetDate }) {
    this.model = new CountdownModel(targetDate);
    this.view = new CountdownView(selector);
    this.interval = null;
  }

  startCountdown() {
    const update = () => {
      const time = this.model.getTimeRemaining();
      if (time.isPast) {
        this.view.showMessage("🚀 Geri Sayım Tamamlandı!");
        clearInterval(this.interval);
      } else {
        this.view.render(time);
      }
    };

    update();
    this.interval = setInterval(update, 1000);
  }

  init() {
    initCursor();
    initContextMenu();
    initCustomSelects();
    initRegisterForm();
    this.startCountdown();
  }
}
