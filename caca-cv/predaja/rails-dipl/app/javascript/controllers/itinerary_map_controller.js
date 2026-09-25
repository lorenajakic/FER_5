import { Controller } from "@hotwired/stimulus"

export default class extends Controller {
  static values = {
    days: { type: Array, default: [] },
    places: { type: Array, default: [] },
    accommodation: { type: Object, default: {} },
    accommodationLabel: { type: String, default: "Accommodation" },
    persistKey: { type: String, default: "" },
    dayLabel: { type: String, default: "Day" },
    transportLabel: { type: String, default: "Transport to next" },
    travelMethods: { type: Object, default: {} },
    locale: { type: String, default: "en" }
  }

  static targets = ["mapContainer", "dayList", "dayHeader", "prevBtn", "nextBtn"]

  connect() {
    this.currentIndex = this.restoreDay()
    this.markers = []
    this.routeLine = null
    this._activeDays = null
    this._modal = null
    this.initMap()

    this.handleTabShown = (e) => {
      if (!e.target.contains(this.element)) return
      ;[50, 150, 350, 700].forEach(ms => setTimeout(() => this.map?.invalidateSize(), ms))
    }
    document.addEventListener("tab:shown", this.handleTabShown)

    this.handleReorder = (e) => {
      this._activeDays = e.detail.days
      this.updateMap()
    }
    this.element.addEventListener("itinerary:reordered", this.handleReorder)
  }

  disconnect() {
    if (this.resizeObserver) this.resizeObserver.disconnect()
    if (this.map) this.map.remove()
    document.removeEventListener("tab:shown", this.handleTabShown)
    this.element.removeEventListener("itinerary:reordered", this.handleReorder)
    this._modal?.remove()
  }

  async initMap() {
    const L = await import("leaflet")
    this.L = L

    this.map = L.map(this.mapContainerTarget, {
      zoomControl: true,
      scrollWheelZoom: true
    }).setView([48.8566, 2.3522], 4)

    L.tileLayer("https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png", {
      attribution: '&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a>',
      maxZoom: 19
    }).addTo(this.map)

    this.resizeObserver = new ResizeObserver(() => this.map?.invalidateSize())
    this.resizeObserver.observe(this.mapContainerTarget)

    this.map.whenReady(() => {
      ;[50, 150, 350, 700].forEach(ms => setTimeout(() => this.map.invalidateSize(), ms))
      this.renderCurrentDay()
    })
  }

  prevDay() {
    if (this.currentIndex > 0) {
      this.currentIndex--
      this.persistDay()
      this.renderCurrentDay()
    }
  }

  nextDay() {
    if (this.currentIndex < this.daysValue.length - 1) {
      this.currentIndex++
      this.persistDay()
      this.renderCurrentDay()
    }
  }

  renderCurrentDay() {
    this.updateNav()
    this.showCurrentDayList()
    this.updateMap()
  }

  updateNav() {
    const total = this.daysValue.length
    const day = this.daysValue[this.currentIndex]
    if (!day || !this.hasDayHeaderTarget) return

    this.dayHeaderTarget.innerHTML = `
      <p class="text-sm font-semibold text-gray-800">${this.dayLabelValue} ${day.day_number} / ${total}</p>
      <p class="text-xs text-gray-500">${this.formatDate(day.date)}</p>
    `

    if (this.hasPrevBtnTarget) this.prevBtnTarget.disabled = this.currentIndex === 0
    if (this.hasNextBtnTarget) this.nextBtnTarget.disabled = this.currentIndex === total - 1
  }

  showCurrentDayList() {
    this.dayListTargets.forEach((list, i) => {
      list.classList.toggle("hidden", i !== this.currentIndex)
    })
  }

  updateMap() {
    if (!this.map || !this.L) return

    this.markers.forEach(m => m.remove())
    this.markers = []
    if (this.routeLine) {
      this.map.removeLayer(this.routeLine)
      this.routeLine = null
    }

    const days = this._activeDays || this.daysValue
    const day = days[this.currentIndex]
    if (!day) return

    const activities = day.activities || []
    const lookup = this.buildPlaceLookup()
    const coords = []
    const placedKeys = new Map()

    activities.forEach((activity, index) => {
      let lat = parseFloat(activity.latitude)
      let lng = parseFloat(activity.longitude)

      if (isNaN(lat) || isNaN(lng)) {
        const place = lookup[(activity.place_name || "").toLowerCase().trim()]
        if (!place) return
        lat = place.latitude
        lng = place.longitude
      }

      const key = `${lat.toFixed(4)},${lng.toFixed(4)}`
      const collisions = placedKeys.get(key) || 0
      if (collisions > 0) {
        const angle = (collisions - 1) * (Math.PI / 3)
        const offsetMeters = 14 + collisions * 4
        const dLat = (offsetMeters / 111000) * Math.cos(angle)
        const dLng = (offsetMeters / (111000 * Math.cos(lat * Math.PI / 180))) * Math.sin(angle)
        lat += dLat
        lng += dLng
      }
      placedKeys.set(key, collisions + 1)

      const latlng = [lat, lng]

      const marker = this.L.marker(latlng, {
        riseOnHover: true,
        icon: this.L.divIcon({
          className: "",
          html: `<div style="background:#6366f1;color:white;width:28px;height:28px;border-radius:50%;display:flex;align-items:center;justify-content:center;font-size:12px;font-weight:700;border:2px solid white;box-shadow:0 2px 6px rgba(0,0,0,0.3);">${index + 1}</div>`,
          iconSize: [28, 28],
          iconAnchor: [14, 14]
        })
      })

      marker.bindPopup(`
        <div style="font-size:13px;">
          <strong>${this.escapeHtml(activity.place_name)}</strong>
          ${activity.start_time ? `<br><span style="color:#6366f1;font-weight:600;">${activity.start_time}</span>` : ""}
          ${activity.duration_minutes ? `<br><span style="color:#9ca3af;">${activity.duration_minutes} min</span>` : ""}
        </div>
      `)

      marker.addTo(this.map)
      this.markers.push(marker)
      coords.push(latlng)
    })

    if (coords.length > 1) {
      this.routeLine = this.L.polyline(coords, {
        color: "#6366f1",
        weight: 2.5,
        opacity: 0.65,
        dashArray: "8, 6"
      }).addTo(this.map)
    }

    const acc = this.accommodationValue
    if (acc && acc.latitude && acc.longitude) {
      const accLatLng = [parseFloat(acc.latitude), parseFloat(acc.longitude)]
      const accMarker = this.L.marker(accLatLng, {
        icon: this.L.divIcon({
          className: "",
          html: `<div style="background:#ef4444;color:white;width:32px;height:32px;border-radius:50%;display:flex;align-items:center;justify-content:center;border:2px solid white;box-shadow:0 2px 6px rgba(0,0,0,0.35);"><svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2"><path stroke-linecap="round" stroke-linejoin="round" d="M3 12l2-2m0 0l7-7 7 7M5 10v10a1 1 0 001 1h3m10-11l2 2m-2-2v10a1 1 0 01-1 1h-3m-6 0a1 1 0 001-1v-4a1 1 0 011-1h2a1 1 0 011 1v4a1 1 0 001 1m-6 0h6"/></svg></div>`,
          iconSize: [32, 32],
          iconAnchor: [16, 16]
        })
      })
      accMarker.bindPopup(`
        <div style="font-size:13px;">
          <strong style="color:#ef4444;">${this.escapeHtml(this.accommodationLabelValue)}</strong>
          <br>${this.escapeHtml(acc.address || "")}
        </div>
      `)
      accMarker.addTo(this.map)
      this.markers.push(accMarker)
      coords.push(accLatLng)
    }

    if (coords.length > 0) {
      this.map.fitBounds(coords, { padding: [50, 50], maxZoom: 15 })
    }
  }

  showDetail(event) {
    const li = event.currentTarget.closest("li")
    if (!li) return
    const activity = JSON.parse(li.dataset.activity)

    const rows = []
    if (activity.start_time || activity.duration_minutes) {
      rows.push(`<div style="display:flex;align-items:center;gap:10px;flex-wrap:wrap;">
        ${activity.start_time ? `<span style="font-weight:600;color:#6366f1;">${this.escapeHtml(activity.start_time)}</span>` : ""}
        ${activity.duration_minutes ? `<span style="color:#9ca3af;">${activity.duration_minutes} min</span>` : ""}
        ${activity.time_block ? `<span style="background:#f3f4f6;padding:2px 8px;border-radius:999px;font-size:11px;color:#6b7280;text-transform:capitalize;">${this.escapeHtml(activity.time_block)}</span>` : ""}
      </div>`)
    }
    if (activity.notes) {
      rows.push(`<p style="color:#374151;line-height:1.6;margin:0;">${this.escapeHtml(activity.notes)}</p>`)
    }
    if (activity.travel_method_to_next && activity.travel_method_to_next !== "none") {
      const td = activity.transit_details
      const hasTransit = td && (td.line || td.boarding_station || td.exit_station || td.direction)
      const transitRows = []
      if (hasTransit) {
        if (td.line) {
          transitRows.push(`<div style="display:flex;align-items:center;gap:6px;"><span style="background:#eef2ff;color:#4f46e5;font-weight:600;padding:2px 8px;border-radius:6px;font-size:11px;">${this.escapeHtml(td.line)}</span>${td.direction ? `<span style="color:#6b7280;font-size:12px;">→ ${this.escapeHtml(td.direction)}</span>` : ""}</div>`)
        } else if (td.direction) {
          transitRows.push(`<div style="color:#6b7280;font-size:12px;">→ ${this.escapeHtml(td.direction)}</div>`)
        }
        if (td.boarding_station || td.exit_station) {
          transitRows.push(`<div style="display:flex;align-items:center;gap:6px;color:#374151;font-size:12px;">
            ${td.boarding_station ? `<span>🚉 ${this.escapeHtml(td.boarding_station)}</span>` : ""}
            ${td.boarding_station && td.exit_station ? `<span style="color:#9ca3af;">→</span>` : ""}
            ${td.exit_station ? `<span>${this.escapeHtml(td.exit_station)}</span>` : ""}
          </div>`)
        }
      }
      const methodLabel = this.travelMethodsValue[activity.travel_method_to_next] || activity.travel_method_to_next
      rows.push(`<div style="padding-top:8px;border-top:1px solid #f3f4f6;display:flex;flex-direction:column;gap:6px;">
        <p style="color:#9ca3af;font-size:12px;margin:0;">${this.escapeHtml(this.transportLabelValue)}: ${this.escapeHtml(methodLabel)}${activity.travel_duration_to_next_minutes ? ` · ${activity.travel_duration_to_next_minutes} min` : ""}</p>
        ${transitRows.join("")}
      </div>`)
    }

    const modal = document.createElement("div")
    modal.style.cssText = "position:fixed;inset:0;z-index:9999;display:flex;align-items:center;justify-content:center;padding:24px;background:rgba(0,0,0,0.45);"
    modal.innerHTML = `
      <div style="background:white;border-radius:16px;width:100%;max-width:400px;padding:24px;box-shadow:0 25px 50px rgba(0,0,0,0.25);position:relative;">
        <div style="display:flex;align-items:flex-start;justify-content:space-between;margin-bottom:16px;gap:12px;">
          <h3 style="font-size:15px;font-weight:600;color:#111827;line-height:1.4;margin:0;">${this.escapeHtml(activity.place_name || "")}</h3>
          <button id="_detail_close" style="flex-shrink:0;width:28px;height:28px;border-radius:8px;border:none;background:none;cursor:pointer;color:#9ca3af;display:flex;align-items:center;justify-content:center;font-size:18px;line-height:1;">✕</button>
        </div>
        <div style="display:flex;flex-direction:column;gap:10px;font-size:13px;max-height:260px;overflow-y:auto;">
          ${rows.join("")}
        </div>
      </div>
    `
    modal.addEventListener("click", (e) => { if (e.target === modal) this.hideDetail() })
    modal.querySelector("#_detail_close").addEventListener("click", () => this.hideDetail())

    this._modal?.remove()
    this._modal = modal
    document.body.appendChild(modal)
  }

  hideDetail() {
    this._modal?.remove()
    this._modal = null
  }

  buildPlaceLookup() {
    const lookup = {}
    this.placesValue.forEach(p => {
      if (p.latitude && p.longitude) {
        lookup[(p.name || "").toLowerCase().trim()] = p
      }
    })
    return lookup
  }

  restoreDay() {
    const key = this.sessionKey()
    if (!key) return 0
    try {
      const val = parseInt(sessionStorage.getItem(key), 10)
      const max = this.daysValue.length - 1
      if (!isNaN(val) && val >= 0 && val <= max) return val
    } catch {}
    return 0
  }

  persistDay() {
    const key = this.sessionKey()
    if (!key) return
    try { sessionStorage.setItem(key, String(this.currentIndex)) } catch {}
  }

  sessionKey() {
    const k = (this.persistKeyValue || "").trim()
    return k ? `itinerary-day:${k}` : null
  }

  formatDate(dateStr) {
    try {
      const d = new Date(dateStr + "T00:00:00")
      return d.toLocaleDateString(this.localeValue, { weekday: "long", day: "numeric", month: "long" })
    } catch {
      return dateStr
    }
  }

  escapeHtml(text) {
    const div = document.createElement("div")
    div.textContent = text || ""
    return div.innerHTML
  }
}
