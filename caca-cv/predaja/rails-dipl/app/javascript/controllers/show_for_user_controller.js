import { Controller } from "@hotwired/stimulus"

export default class extends Controller {
  static values = { userId: Number }

  connect() {
    const currentId = document.body.dataset.currentUserId
    if (!currentId || String(this.userIdValue) !== String(currentId)) {
      this.element.classList.add("hidden")
    }
  }
}
