/* PolarOps front-end helpers: charts, station map, live polling. */
const POLAR_COLORS = ["#2563eb", "#0d9488", "#d97706", "#7c3aed", "#dc2626"];

function polarFmtTime(ms) {
  const d = new Date(ms);
  return d.toLocaleDateString(undefined, { day: "2-digit", month: "short" }) + " " +
         d.toLocaleTimeString(undefined, { hour: "2-digit", minute: "2-digit" });
}

/* Threshold line drawn as a dashed horizontal rule. */
const polarThresholdPlugin = {
  id: "polarThreshold",
  afterDatasetsDraw(chart, args, opts) {
    if (opts.value === undefined || opts.value === null) return;
    const { ctx, chartArea, scales } = chart;
    const y = scales.y.getPixelForValue(opts.value);
    if (y < chartArea.top || y > chartArea.bottom) return;
    ctx.save();
    ctx.strokeStyle = "#dc2626";
    ctx.setLineDash([6, 4]);
    ctx.lineWidth = 1.5;
    ctx.beginPath();
    ctx.moveTo(chartArea.left, y);
    ctx.lineTo(chartArea.right, y);
    ctx.stroke();
    ctx.restore();
  },
};

function polarLineChart(id, series, opts = {}) {
  const el = document.getElementById(id);
  if (!el || !window.Chart) return null;
  const hasData = series.some(s => s.points.length);
  if (!hasData) {
    el.parentElement.innerHTML = '<div class="chart-empty"><i class="bi bi-graph-down"></i> No readings in this period</div>';
    return null;
  }
  const datasets = series.map((s, i) => {
    const color = s.color || opts.color || POLAR_COLORS[i % POLAR_COLORS.length];
    return {
      label: s.label,
      data: s.points.map(p => ({ x: p[0], y: p[1] })),
      borderColor: color,
      backgroundColor: color + (opts.stacked ? "99" : "1f"),
      fill: opts.stacked ? (i === 0 ? "origin" : "-1") : !!opts.fill,
      tension: 0.3,
      pointRadius: 0,
      pointHoverRadius: 4,
      borderWidth: 2,
    };
  });
  return new Chart(el, {
    type: "line",
    data: { datasets },
    plugins: [polarThresholdPlugin],
    options: {
      responsive: true,
      maintainAspectRatio: false,
      interaction: { mode: "nearest", axis: "x", intersect: false },
      plugins: {
        legend: { display: series.length > 1, labels: { boxWidth: 12, usePointStyle: true } },
        tooltip: {
          callbacks: {
            title: items => polarFmtTime(items[0].parsed.x),
            label: c => `${c.dataset.label}: ${c.parsed.y.toFixed(1)} ${opts.unit || ""}`,
          },
        },
        polarThreshold: { value: opts.threshold },
      },
      scales: {
        x: { type: "linear", ticks: { callback: v => polarFmtTime(v), maxTicksLimit: 6, color: "#64748b" }, grid: { display: false } },
        y: { stacked: !!opts.stacked, min: opts.min, max: opts.max, ticks: { color: "#64748b" }, grid: { color: "#e2e8f0" } },
      },
    },
  });
}

const POLAR_STATUS_COLORS = { ACTIVE: "#16a34a", SEASONAL: "#d97706", INACTIVE: "#64748b" };

function polarEsc(value) {
  return String(value ?? "").replace(/[&<>"']/g, c => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" })[c]);
}

function polarPopupHtml(p) {
  if (p.url) {
    const temp = p.temp === null || p.temp === undefined ? "—" : p.temp.toFixed(1) + " °C";
    return `<strong><a href="${polarEsc(p.url)}">${polarEsc(p.name)}</a></strong> (${polarEsc(p.code)})<br>` +
      `${polarEsc(p.status_label)}<br>Crew: ${polarEsc(p.crew)} · Temp: ${temp}<br>Open incidents: ${polarEsc(p.incidents)}`;
  }
  // public landing page: only public facts
  return `<strong>${polarEsc(p.name)}</strong> (${polarEsc(p.code)})<br>${polarEsc(p.status_label)}` +
    (p.established ? `<br>Established ${polarEsc(p.established)}` : "");
}

/* Station map: Google Maps when a key is configured, otherwise (or if Google fails) OpenStreetMap via Leaflet. */
function polarStationMap(id, points) {
  const el = document.getElementById(id);
  if (!el || !points.length) return;
  if (window.POLAR_GMAPS_KEY) {
    polarLoadGoogleMaps(window.POLAR_GMAPS_KEY)
      .then(() => polarGoogleMap(el, points))
      .catch(() => polarLeafletMap(el, points));
    // invalid / restricted key: Google calls this global hook after loading
    window.gm_authFailure = () => {
      console.warn("Google Maps rejected the API key - falling back to OpenStreetMap.");
      polarLeafletMap(el, points);
    };
  } else {
    polarLeafletMap(el, points);
  }
}

let polarGoogleLoader = null;
function polarLoadGoogleMaps(key) {
  if (window.google && window.google.maps && window.google.maps.marker) return Promise.resolve();
  if (!polarGoogleLoader) {
    polarGoogleLoader = new Promise((resolve, reject) => {
      window.__polarGmapsReady = resolve;
      const s = document.createElement("script");
      s.src = `https://maps.googleapis.com/maps/api/js?key=${encodeURIComponent(key)}` +
              "&v=weekly&libraries=marker&loading=async&callback=__polarGmapsReady";
      s.async = true;
      s.onerror = reject;
      document.head.appendChild(s);
      setTimeout(() => reject(new Error("Google Maps load timeout")), 15000);
    });
  }
  return polarGoogleLoader;
}

function polarGoogleMap(el, points) {
  const map = new google.maps.Map(el, {
    center: { lat: -70, lng: 44 },
    zoom: 3,
    mapId: "DEMO_MAP_ID",          // required for advanced markers; replace with your own Map ID in production
    mapTypeId: "hybrid",
    gestureHandling: "cooperative",
    streetViewControl: false,
    fullscreenControl: true,
    mapTypeControlOptions: { mapTypeIds: ["hybrid", "terrain", "roadmap"] },
  });
  const info = new google.maps.InfoWindow();
  const bounds = new google.maps.LatLngBounds();
  const placed = [];
  points.forEach(p => {
    const crowded = placed.some(b => Math.abs(b[0] - p.lat) < 2 && Math.abs(b[1] - p.lng) < 4);
    const pin = document.createElement("div");
    pin.className = "gmap-pin" + (crowded ? " gmap-pin-left" : "");
    pin.innerHTML = `<span class="gmap-dot" style="background:${POLAR_STATUS_COLORS[p.status] || "#2563eb"}"></span>` +
                    `<span class="gmap-label">${polarEsc(p.name)}</span>`;
    const marker = new google.maps.marker.AdvancedMarkerElement({
      map, position: { lat: p.lat, lng: p.lng }, content: pin, title: p.name, gmpClickable: true,
    });
    marker.addEventListener("gmp-click", () => {
      info.setContent(`<div class="gmap-info">${polarPopupHtml(p)}</div>`);
      info.open({ map, anchor: marker });
    });
    bounds.extend({ lat: p.lat, lng: p.lng });
    placed.push([p.lat, p.lng]);
  });
  if (points.length > 1) {
    map.fitBounds(bounds, { top: 60, bottom: 60, left: 130, right: 130 });   // room for the name labels
    google.maps.event.addListenerOnce(map, "idle", () => { if (map.getZoom() > 4) map.setZoom(4); });
  } else {
    map.setCenter({ lat: points[0].lat, lng: points[0].lng });
    map.setZoom(6);
  }
  el.dataset.mapEngine = "google";
}

function polarLeafletMap(el, points) {
  if (!window.L) return;
  if (el._leaflet_id) return;                       // already drawn
  el.innerHTML = "";
  el.removeAttribute("style");
  const map = L.map(el, { scrollWheelZoom: false, worldCopyJump: true }).setView([-70, 44], 3);
  // CARTO basemap (OpenStreetMap data). tile.openstreetmap.org blocks app traffic, so it is not used directly.
  L.tileLayer("https://{s}.basemaps.cartocdn.com/rastertiles/voyager/{z}/{x}/{y}{r}.png", {
    maxZoom: 12,
    subdomains: "abcd",
    attribution: '&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors &copy; <a href="https://carto.com/attributions">CARTO</a>',
  }).addTo(map);
  const bounds = [];
  points.forEach(p => {
    const marker = L.circleMarker([p.lat, p.lng], {
      radius: 9, color: "#fff", weight: 2, fillColor: POLAR_STATUS_COLORS[p.status] || "#2563eb", fillOpacity: 0.95,
    }).addTo(map);
    marker.bindPopup(polarPopupHtml(p));
    // stations very close together (Maitri / Dakshin Gangotri) get labels on opposite sides
    const crowded = bounds.some(b => Math.abs(b[0] - p.lat) < 2 && Math.abs(b[1] - p.lng) < 4);
    marker.bindTooltip(p.name, { permanent: true, direction: crowded ? "left" : "right", className: "map-label" });
    bounds.push([p.lat, p.lng]);
  });
  if (bounds.length > 1) map.fitBounds(bounds, { padding: [50, 50], maxZoom: 4 });
  el.dataset.mapEngine = "leaflet";
}

function startLivePolling(url, everyMs = 60000) {
  const set = (key, value, digits, suffix = "") => {
    document.querySelectorAll(`[data-live="${key}"]`).forEach(el => {
      el.textContent = value === null || value === undefined ? "—" : Number(value).toFixed(digits) + suffix;
    });
  };
  const bar = (key, value) => {
    document.querySelectorAll(`[data-live-bar="${key}"]`).forEach(el => {
      if (value !== null && value !== undefined) el.style.width = Math.max(0, Math.min(100, value)) + "%";
    });
  };
  async function tick() {
    if (document.hidden) return;   // don't spend satellite bandwidth on a background tab
    try {
      const r = await fetch(url, { headers: { Accept: "application/json" }, credentials: "same-origin" });
      if (!r.ok) return;
      const data = await r.json();
      data.stations.forEach(s => {
        if (s.weather) {
          set(`temp-${s.id}`, s.weather.temperature_c, 1);
          set(`wind-${s.id}`, s.weather.wind_speed_kmh, 0);
          set(`pressure-${s.id}`, s.weather.pressure_hpa, 0);
          const mins = Math.round((Date.now() - new Date(s.weather.recorded_at)) / 60000);
          document.querySelectorAll(`[data-live="seen-${s.id}"]`).forEach(el => {
            el.textContent = mins < 1 ? "just now" : mins < 60 ? `${mins} min ago` : `${Math.floor(mins / 60)} h ago`;
          });
        }
        if (s.power) {
          set(`fuel-${s.id}`, s.power.fuel_level_pct, 0, "%");
          set(`renew-${s.id}`, s.power.renewable_pct, 0, "%");
          bar(`fuel-${s.id}`, s.power.fuel_level_pct);
          bar(`renew-${s.id}`, s.power.renewable_pct);
        }
      });
      const stamp = document.getElementById("live-updated");
      if (stamp) stamp.textContent = new Date().toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" });
    } catch (e) {
      /* satellite link down - keep showing last known values */
    }
  }
  setInterval(tick, everyMs);
  // refresh straight away when the user comes back to the tab
  document.addEventListener("visibilitychange", () => { if (!document.hidden) tick(); });
}
