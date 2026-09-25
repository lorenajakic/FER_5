import { Controller } from "@hotwired/stimulus"
import Sortable from "sortablejs"

export default class extends Controller {
  static values = { url: String }

  connect() {
    this.sortables = []
    this.element.querySelectorAll(".sortable-activities").forEach(list => {
      const s = Sortable.create(list, {
        group: "activities",
        animation: 150,
        handle: "li",
        filter: "[data-no-drag]",
        preventOnFilter: false,
        ghostClass: "opacity-40",
        onEnd: () => {
          const days = this.buildDays()
          this.renumberBadges()
          this.element.dispatchEvent(new CustomEvent("itinerary:reordered", {
            bubbles: true,
            detail: { days }
          }))
          this.persistDays(days)
        }
      })
      this.sortables.push(s)
    })
  }

  disconnect() {
    this.sortables.forEach(s => s.destroy())
  }

  buildDays() {
    const days = []
    this.element.querySelectorAll(".sortable-activities").forEach(list => {
      const activities = Array.from(list.querySelectorAll("li")).map((li, idx) => {
        const activity = JSON.parse(li.dataset.activity)
        return { ...activity, position: idx + 1 }
      })
      days.push({
        day_number: parseInt(list.dataset.day),
        date: list.dataset.date,
        activities
      })
    })
    return days
  }

  renumberBadges() {
    this.element.querySelectorAll(".sortable-activities").forEach(list => {
      list.querySelectorAll("li").forEach((li, idx) => {
        const badge = li.querySelector("[data-activity-badge]")
        if (badge) badge.textContent = idx + 1
      })
    })
  }

  persistDays(days) {
    fetch(this.urlValue, {
      method: "PATCH",
      headers: {
        "Content-Type": "application/x-www-form-urlencoded",
        "X-CSRF-Token": document.querySelector('meta[name="csrf-token"]')?.content,
        "Accept": "text/vnd.turbo-stream.html"
      },
      body: new URLSearchParams({ plan_json: JSON.stringify({ plan: { days } }) })
    })
  }
}
