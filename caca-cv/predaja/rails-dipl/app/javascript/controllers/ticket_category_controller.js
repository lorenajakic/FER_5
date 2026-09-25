import { Controller } from "@hotwired/stimulus"

export default class extends Controller {
  static targets = ["tab", "input"]
  static classes = ["activeTab", "inactiveTab"]

  connect() {
    this.updateStyles()
  }

  select(event) {
    this.inputTarget.value = event.params.value
    this.updateStyles()
  }

  updateStyles() {
    const current = this.inputTarget.value

    this.tabTargets.forEach((tab) => {
      const value = tab.dataset.ticketCategoryValueParam
      if (value === current) {
        tab.classList.add(...this.activeTabClasses)
        tab.classList.remove(...this.inactiveTabClasses)
      } else {
        tab.classList.remove(...this.activeTabClasses)
        tab.classList.add(...this.inactiveTabClasses)
      }
    })
  }
}
