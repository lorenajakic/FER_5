import { Controller } from "@hotwired/stimulus"

export default class extends Controller {
  static targets = ["input", "results", "name", "address", "latitude", "longitude", "form", "manualFields"]
  static values = { url: { type: String, default: "/geocoding/autocomplete" } }

  connect() {
    this.selectedIndex = -1
    this.debounceTimer = null
    this.mapCenterLat = null
    this.mapCenterLng = null
    this.onMapCenter = (e) => {
      this.mapCenterLat = e.detail.lat
      this.mapCenterLng = e.detail.lng
    }
    document.addEventListener("places-map:center", this.onMapCenter)
    document.addEventListener("click", this.closeResults)
  }

  disconnect() {
    document.removeEventListener("places-map:center", this.onMapCenter)
    document.removeEventListener("click", this.closeResults)
    if (this.debounceTimer) clearTimeout(this.debounceTimer)
  }

  clearAfterSubmit() {
    if (this.hasInputTarget) this.inputTarget.value = ""
    if (this.hasNameTarget) this.nameTarget.value = ""
    if (this.hasAddressTarget) this.addressTarget.value = ""
    if (this.hasLatitudeTarget) this.latitudeTarget.value = ""
    if (this.hasLongitudeTarget) this.longitudeTarget.value = ""
    this.hideResults()
  }

  search() {
    const query = this.inputTarget.value.trim()
    if (query.length < 2) {
      this.hideResults()
      return
    }

    if (this.debounceTimer) clearTimeout(this.debounceTimer)
    this.debounceTimer = setTimeout(() => this.fetchResults(query), 300)
  }

  async fetchResults(query) {
    try {
      const params = new URLSearchParams({ q: query })
      if (this.mapCenterLat != null && this.mapCenterLng != null &&
          Number.isFinite(this.mapCenterLat) && Number.isFinite(this.mapCenterLng)) {
        params.set("lat", String(this.mapCenterLat))
        params.set("lon", String(this.mapCenterLng))
      }
      const response = await fetch(`${this.urlValue}?${params}`)
      if (!response.ok) return

      const results = await response.json()
      this.renderResults(results)
    } catch {
      this.hideResults()
    }
  }

  renderResults(results) {
    if (results.length === 0) {
      this.hideResults()
      return
    }

    this.selectedIndex = -1
    const html = results.map((result, i) => {
      const display = [result.name, result.city, result.country].filter(Boolean).join(", ")
      return `
        <button type="button"
                class="w-full text-left px-4 py-2.5 text-sm hover:bg-indigo-50 transition cursor-pointer"
                data-action="click->autocomplete#selectResult"
                data-autocomplete-index-param="${i}"
                data-result='${JSON.stringify(result).replace(/'/g, "&#39;")}'>
          <span class="font-medium text-gray-900">${this.escapeHtml(result.name || '')}</span>
          <span class="block text-xs text-gray-500 mt-0.5">${this.escapeHtml(result.address || '')}</span>
        </button>
      `
    }).join("")

    this.resultsTarget.innerHTML = html
    this.resultsTarget.classList.remove("hidden")
    this.results = results
  }

  selectResult(event) {
    const index = event.params.index
    const result = this.results[index]
    if (!result) return

    this.nameTarget.value = result.name || ""
    this.addressTarget.value = result.address || ""
    this.latitudeTarget.value = result.latitude || ""
    this.longitudeTarget.value = result.longitude || ""
    this.inputTarget.value = [result.name, result.city, result.country].filter(Boolean).join(", ")

    this.hideResults()
    this.formTarget.requestSubmit()
  }

  onKeydown(event) {
    if (!this.resultsTarget || this.resultsTarget.classList.contains("hidden")) return

    const buttons = this.resultsTarget.querySelectorAll("button")
    if (buttons.length === 0) return

    switch (event.key) {
      case "ArrowDown":
        event.preventDefault()
        this.selectedIndex = Math.min(this.selectedIndex + 1, buttons.length - 1)
        this.highlightItem(buttons)
        break
      case "ArrowUp":
        event.preventDefault()
        this.selectedIndex = Math.max(this.selectedIndex - 1, 0)
        this.highlightItem(buttons)
        break
      case "Enter":
        event.preventDefault()
        if (this.selectedIndex >= 0 && buttons[this.selectedIndex]) {
          buttons[this.selectedIndex].click()
        }
        break
      case "Escape":
        this.hideResults()
        break
    }
  }

  highlightItem(buttons) {
    buttons.forEach((btn, i) => {
      btn.classList.toggle("bg-indigo-50", i === this.selectedIndex)
    })
  }

  hideResults() {
    if (this.hasResultsTarget) {
      this.resultsTarget.classList.add("hidden")
      this.resultsTarget.innerHTML = ""
    }
    this.selectedIndex = -1
  }

  closeResults = (event) => {
    if (!this.element.contains(event.target)) {
      this.hideResults()
    }
  }

  escapeHtml(text) {
    const div = document.createElement("div")
    div.textContent = text
    return div.innerHTML
  }
}
