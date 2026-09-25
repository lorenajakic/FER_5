import { Controller } from "@hotwired/stimulus"

const ALLOWED_TYPES = [
  "application/pdf",
  "image/jpeg",
  "image/png",
  "image/webp"
]

export default class extends Controller {
  static targets = ["input", "filename", "error"]
  static values = {
    maxBytes: Number,
    imageOnly: { type: Boolean, default: false }
  }

  pick() {
    this.clearError()
    const file = this.inputTarget.files[0]
    if (!file) {
      this.filenameTarget.textContent = this.inputTarget.dataset.defaultLabel || ""
      return
    }
    this.filenameTarget.textContent = file.name
  }

  validateSubmit(event) {
    this.clearError()
    const file = this.inputTarget.files[0]
    if (!file) {
      if (this.inputTarget.dataset.isRequired === "true") {
        event.preventDefault()
        this.showError(this.inputTarget.dataset.requiredMessage)
      }
      return
    }

    if (this.imageOnlyValue) {
      if (!file.type.startsWith("image/")) {
        event.preventDefault()
        this.showError(this.inputTarget.dataset.invalidTypeMessage)
        return
      }
    } else if (!ALLOWED_TYPES.includes(file.type)) {
      event.preventDefault()
      this.showError(this.inputTarget.dataset.invalidTypeMessage)
      return
    }

    if (this.hasMaxBytesValue && file.size > this.maxBytesValue) {
      event.preventDefault()
      this.showError(this.inputTarget.dataset.tooLargeMessage)
    }
  }

  showError(message) {
    if (this.hasErrorTarget) {
      this.errorTarget.textContent = message
      this.errorTarget.classList.remove("hidden")
    }
  }

  clearError() {
    if (this.hasErrorTarget) {
      this.errorTarget.textContent = ""
      this.errorTarget.classList.add("hidden")
    }
  }
}
