import { Controller } from "@hotwired/stimulus"

export default class extends Controller {
  static values = { delay: { type: Number, default: 4000 } }

  connect() {
    requestAnimationFrame(() => {
      this.element.classList.remove("translate-y-4", "opacity-0")
      this.element.classList.add("translate-y-0", "opacity-100")
    })

    this._timeout = setTimeout(() => this.dismiss(), this.delayValue)
  }

  disconnect() {
    if (this._timeout) clearTimeout(this._timeout)
    if (this._dismissFallback) clearTimeout(this._dismissFallback)
  }

  dismiss() {
    if (this._timeout) clearTimeout(this._timeout)
    this._timeout = null

    this.element.style.pointerEvents = "none"

    this.element.classList.remove("translate-y-0", "opacity-100")
    this.element.classList.add("translate-y-4", "opacity-0")

    let finished = false
    const removeFromDom = () => {
      if (finished) return
      finished = true
      if (this._dismissFallback) clearTimeout(this._dismissFallback)
      this._dismissFallback = null
      this.element.remove()
    }

    this.element.addEventListener(
      "transitionend",
      (event) => {
        if (event.target !== this.element) return
        removeFromDom()
      },
      { once: true }
    )

    this._dismissFallback = setTimeout(removeFromDom, 400)
  }
}
