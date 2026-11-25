/* PolarOps front-end helpers: charts, station map, live polling.
 * Colours follow the "snow paper" palette in polarops.css: ink, glacier, aurora, ochre, signal. */
const POLAR_INK = "#0d1117";
const POLAR_COLORS = ["#2a5bff", "#0e7c76", "#0d1117", "#d99a00", "#ff5a1f"];
const POLAR_MONO = '"JetBrains Mono", ui-monospace, monospace';

if (window.Chart) {
  Chart.defaults.font.family = '"Instrument Sans", system-ui, sans-serif';
  Chart.defaults.color = "#4d535b";
}

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
    ctx.strokeStyle = "#ff5a1f";
    ctx.setLineDash([5, 4]);
    ctx.lineWidth = 1.25;
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
    el.parentElement.innerHTML = '<div class="chart-empty">No readings in this period</div>';
    return null;
  }
  const datasets = series.map((s, i) => {
    const color = s.color || opts.color || POLAR_COLORS[i % POLAR_COLORS.length];
    return {
      label: s.label,
      data: s.points.map(p => ({ x: p[0], y: p[1] })),
      borderColor: color,
      backgroundColor: color + (opts.stacked ? "40" : "14"),
      fill: opts.stacked ? (i === 0 ? "origin" : "-1") : !!opts.fill,
      tension: 0.25,
      pointRadius: 0,
      pointHoverRadius: 4,
      pointHoverBackgroundColor: color,
      pointHoverBorderColor: "#fbfcfb",
      pointStyle: "rect",
      borderWidth: 1.6,
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
        legend: {
          display: series.length > 1, align: "start",
          labels: { boxWidth: 8, boxHeight: 8, usePointStyle: true, pointStyle: "rect", font: { family: POLAR_MONO, size: 10 }, color: POLAR_INK },
        },
        tooltip: {
          backgroundColor: POLAR_INK, cornerRadius: 0, padding: 10, displayColors: true, boxWidth: 8, boxHeight: 8, usePointStyle: true,
          titleFont: { family: POLAR_MONO, size: 10, weight: "500" }, bodyFont: { family: POLAR_MONO, size: 11 },
          callbacks: {
            title: items => polarFmtTime(items[0].parsed.x),
            label: c => `${c.dataset.label}: ${c.parsed.y.toFixed(1)} ${opts.unit || ""}`,
          },
        },
        polarThreshold: { value: opts.threshold },
      },
      scales: {
        x: {
          type: "linear", border: { color: POLAR_INK }, grid: { display: false },
          ticks: { callback: v => polarFmtTime(v), maxTicksLimit: 6, color: "#4d535b", font: { family: POLAR_MONO, size: 10 } },
        },
        y: {
          stacked: !!opts.stacked, min: opts.min, max: opts.max, border: { display: false },
          ticks: { color: "#4d535b", font: { family: POLAR_MONO, size: 10 }, padding: 6 },
          grid: { color: "rgba(13, 17, 23, .07)", tickLength: 0 },
        },
      },
    },
  });
}

const POLAR_STATUS_COLORS = { ACTIVE: "#2a5bff", SEASONAL: "#d99a00", INACTIVE: "#7c828a" };

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
    pin.innerHTML = `<span class="gmap-dot" style="background:${POLAR_STATUS_COLORS[p.status] || "#2a5bff"}"></span>` +
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
  // Esri basemaps need no API key (CARTO's tiles now do). Satellite by default, topographic as an option.
  const esri = (service, source) => L.tileLayer(
    `https://server.arcgisonline.com/ArcGIS/rest/services/${service}/MapServer/tile/{z}/{y}/{x}`,
    { maxZoom: 12, attribution: `Tiles &copy; <a href="https://www.esri.com/">Esri</a> &mdash; ${source}` },
  );
  const layers = {
    Satellite: esri("World_Imagery", "Source: Esri, Maxar, Earthstar Geographics, and the GIS User Community"),
    Map: esri("World_Topo_Map", "Sources: Esri, HERE, Garmin, USGS, NGA and other contributors"),
  };
  layers.Satellite.addTo(map);
  L.control.layers(layers, null, { position: "topright" }).addTo(map);
  const bounds = [];
  el.polarMarkers = {};
  points.forEach(p => {
    const marker = L.circleMarker([p.lat, p.lng], {
      radius: 7, color: "#fbfcfb", weight: 2, fillColor: POLAR_STATUS_COLORS[p.status] || "#2a5bff", fillOpacity: 1,
    }).addTo(map);
    marker.bindPopup(polarPopupHtml(p));
    // stations very close together (Maitri / Dakshin Gangotri) get labels on opposite sides
    const crowded = bounds.some(b => Math.abs(b[0] - p.lat) < 2 && Math.abs(b[1] - p.lng) < 4);
    marker.bindTooltip(p.name, { permanent: true, direction: crowded ? "left" : "right", className: "map-label" });
    marker.on("mouseover", () => el.dispatchEvent(new CustomEvent("station-hover", { detail: { code: p.code, on: true } })));
    marker.on("mouseout", () => el.dispatchEvent(new CustomEvent("station-hover", { detail: { code: p.code, on: false } })));
    el.polarMarkers[p.code] = marker;
    bounds.push([p.lat, p.lng]);
  });
  if (bounds.length > 1) map.fitBounds(bounds, { padding: [50, 50], maxZoom: 4 });
  el.dataset.mapEngine = "leaflet";
}

/* Emphasise one station's marker (landing page: hovering a station datasheet). */
function polarFocusStation(id, code, on) {
  const el = document.getElementById(id);
  const marker = el && el.polarMarkers && el.polarMarkers[code];
  if (!marker) return;
  marker.setRadius(on ? 11 : 7);
  marker.setStyle({ color: on ? POLAR_INK : "#fbfcfb", weight: on ? 3 : 2 });
  const tip = marker.getTooltip();
  if (tip && tip.getElement()) tip.getElement().classList.toggle("is-hot", on);
  if (on) marker.bringToFront();
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
