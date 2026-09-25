import { Controller } from "@hotwired/stimulus"

export default class extends Controller {
  static targets = ["input", "results"]

  connect() {
    this.selectedIndex = -1
    this._closeOnClickOutside = this.closeResults.bind(this)
    document.addEventListener("click", this._closeOnClickOutside)
  }

  disconnect() {
    document.removeEventListener("click", this._closeOnClickOutside)
    if (this.timeout) clearTimeout(this.timeout)
  }

  search() {
    const query = this.inputTarget.value.trim()
    if (query.length < 2) {
      this.hideResults()
      return
    }

    if (this.timeout) clearTimeout(this.timeout)
    this.timeout = setTimeout(() => this.fetchSuggestions(query), 300)
  }

  keydown(event) {
    if (!this.hasResultsTarget || this.resultsTarget.classList.contains("hidden")) return

    const items = this.resultsTarget.querySelectorAll("[data-index]")
    if (!items.length) return

    switch (event.key) {
      case "ArrowDown":
        event.preventDefault()
        this.selectedIndex = Math.min(this.selectedIndex + 1, items.length - 1)
        this.highlightItem(items)
        break
      case "ArrowUp":
        event.preventDefault()
        this.selectedIndex = Math.max(this.selectedIndex - 1, 0)
        this.highlightItem(items)
        break
      case "Enter":
        event.preventDefault()
        if (this.selectedIndex >= 0 && items[this.selectedIndex]) {
          this.selectItem(items[this.selectedIndex].dataset.value)
        }
        break
      case "Escape":
        this.hideResults()
        break
    }
  }

  async fetchSuggestions(query) {
    try {
      const url = `https://photon.komoot.io/api?q=${encodeURIComponent(query)}&limit=5&layer=city&lang=en`
      const response = await fetch(url)
      if (!response.ok) return

      const data = await response.json()
      this.renderResults(data.features || [])
    } catch {
      this.hideResults()
    }
  }

  renderResults(features) {
    if (!features.length) {
      this.hideResults()
      return
    }

    const seen = new Set()
    const items = features
      .map(f => {
        const props = f.properties || {}
        const parts = [props.name, props.state, props.country].filter(Boolean)
        const label = parts.join(", ")
        if (seen.has(label)) return null
        seen.add(label)
        return label
      })
      .filter(Boolean)

    if (!items.length) {
      this.hideResults()
      return
    }

    this.selectedIndex = -1
    this.resultsTarget.innerHTML = items
      .map((label, i) =>
        `<button type="button" data-index="${i}" data-value="${label}"
                class="block w-full text-left px-4 py-2.5 text-sm text-gray-700 hover:bg-indigo-50 hover:text-indigo-700 transition cursor-pointer"
                data-action="click->destination-autocomplete#pick">${label}</button>`
      )
      .join("")
    this.resultsTarget.classList.remove("hidden")
  }

  pick(event) {
    this.selectItem(event.currentTarget.dataset.value)
  }

  selectItem(value) {
    this.inputTarget.value = value
    this.hideResults()
  }

  highlightItem(items) {
    items.forEach((item, i) => {
      item.classList.toggle("bg-indigo-50", i === this.selectedIndex)
      item.classList.toggle("text-indigo-700", i === this.selectedIndex)
    })
  }

  hideResults() {
    this.resultsTarget.classList.add("hidden")
    this.resultsTarget.innerHTML = ""
    this.selectedIndex = -1
  }

  closeResults(event) {
    if (!this.element.contains(event.target)) {
      this.hideResults()
    }
  }
}
