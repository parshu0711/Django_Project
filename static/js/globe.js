/* PolarOps "ice dome": a hand-drawn wireframe of the Antarctic ice sheet seen from above the
 * South Pole, with the stations at their real coordinates, a VSAT satellite linking the active
 * ones, and a radar sweep. Canvas 2D, no 3D library.
 *
 *   PolarGlobe.mount(container, points, { hud: true, onSelect(point) {} })
 *
 * points: [{name, code, lat, lng, status, status_label, established}] (public facts only).
 * Draws one static frame when the visitor prefers reduced motion, and only animates while the
 * globe is on screen and the tab is visible.
 */
(function () {
  "use strict";

  const REDUCED = window.matchMedia("(prefers-reduced-motion: reduce)").matches;
  const DEG = Math.PI / 180;

  /* Approximate Antarctic coastline: [longitude °E (0-360), latitude °S]. Hand-tuned so the dome
   * reads as Antarctica (Ross and Weddell embayments, the Peninsula) and every Indian station sits
   * just inside the edge. ρ = (90 - lat) / 30, so 60°S lies on the unit circle. */
  const COAST = [
    [0, 69.6], [15, 69.5], [30, 69.0], [45, 68.0], [60, 67.2], [70, 68.2], [77, 69.1], [85, 66.8],
    [100, 66.0], [115, 66.2], [130, 66.4], [145, 67.5], [160, 69.5], [170, 72.0], [180, 78.0], [195, 78.0],
    [210, 76.0], [225, 74.5], [240, 73.8], [255, 73.5], [270, 73.0], [280, 71.5], [288, 68.0], [295, 64.2],
    [300, 63.4], [304, 64.8], [309, 70.0], [316, 75.5], [326, 77.5], [336, 76.0], [346, 72.0], [354, 70.4],
  ];

  const coastTable = (() => {
    const t = new Float32Array(360);
    for (let d = 0; d < 360; d++) {
      let i = COAST.findIndex(p => p[0] > d);
      if (i === -1) i = COAST.length;
      const a = COAST[(i - 1 + COAST.length) % COAST.length];
      const b = COAST[i % COAST.length];
      const a0 = a[0], b0 = i === COAST.length ? b[0] + 360 : b[0];
      const f = (d - a0) / (b0 - a0 || 1);
      t[d] = ((90 - a[1]) + ((90 - b[1]) - (90 - a[1])) * f) / 30;
    }
    for (let pass = 0; pass < 2; pass++) {     // soften the polygon corners
      const c = t.slice();
      for (let d = 0; d < 360; d++) {
        let s = 0;
        for (let k = -2; k <= 2; k++) s += c[(d + k + 360) % 360];
        t[d] = s / 5;
      }
    }
    return t;
  })();

  const coastAt = lngDeg => {
    const d = ((lngDeg % 360) + 360) % 360;
    const i = Math.floor(d), f = d - i;
    return coastTable[i] * (1 - f) + coastTable[(i + 1) % 360] * f;
  };

  /* Ice-sheet surface height for normalised radius s (0 = pole, 1 = coast). East Antarctica is
   * higher, and a few gentle ridges keep the mesh from looking like a perfect bowl. */
  const heightAt = (s, lngDeg) => {
    const th = lngDeg * DEG;
    const dome = 0.19 * Math.pow(Math.max(0, 1 - s * s), 0.55) * (1 + 0.24 * Math.cos(th - 80 * DEG));
    const ridge = 0.012 * Math.sin(5 * th + 9 * s) * s * (1 - s) * 4 + 0.008 * Math.sin(11 * th - 4 * s) * s;
    return dome + ridge;
  };

  /* Map display angle: viewed from above the South Pole, east longitudes run clockwise. */
  const angleOf = lngDeg => -lngDeg * DEG;

  function hexToRgb(hex) {
    const m = hex.trim().replace("#", "");
    const n = parseInt(m.length === 3 ? m.split("").map(c => c + c).join("") : m, 16);
    return [(n >> 16) & 255, (n >> 8) & 255, n & 255];
  }

  function mount(container, points, opts = {}) {
    const css = getComputedStyle(document.documentElement);
    const color = name => hexToRgb(css.getPropertyValue(name) || "#000");
    const C = {
      ink: color("--ink"), ink40: color("--ink-40"), glacier: color("--glacier"),
      signal: color("--signal"), aurora: color("--aurora"),
    };
    const rgba = (c, a) => `rgba(${c[0]},${c[1]},${c[2]},${Math.max(0, Math.min(1, a)).toFixed(3)})`;

    const canvas = document.createElement("canvas");
    canvas.setAttribute("role", "img");
    canvas.setAttribute("aria-label", opts.label || "Wireframe map of Antarctica with India's research stations marked");
    container.prepend(canvas);
    const ctx = canvas.getContext("2d");

    /* ---- static geometry ---- */
    const NR = 15, NS = 144;
    const rings = [];
    for (let k = 1; k <= NR; k++) {
      const s = k / NR, ring = [];
      for (let j = 0; j < NS; j++) {
        const lng = (j / NS) * 360;
        const rho = s * coastAt(lng);
        ring.push({ a: angleOf(lng), rho, z: heightAt(s, lng) });
      }
      rings.push(ring);
    }
    const spokes = [];
    for (let lng = 0; lng < 360; lng += 10) {
      const sp = [];
      for (let k = 0; k <= 24; k++) {
        const s = k / 24;
        sp.push({ a: angleOf(lng), rho: s * coastAt(lng), z: heightAt(s, lng) });
      }
      spokes.push(sp);
    }
    const stations = (points || []).map(p => {
      const lng = ((p.lng % 360) + 360) % 360;
      const rho = (90 - Math.abs(p.lat)) / 30;
      const s = Math.min(0.98, rho / coastAt(lng));
      return { ...p, a: angleOf(lng), rho, z: heightAt(s, lng), active: p.status === "ACTIVE", phase: Math.random() * 3 };
    });

    /* ---- HUD tag + keyboard targets ---- */
    const tag = document.createElement("div");
    tag.className = "globe-tag";
    tag.setAttribute("aria-hidden", "true");
    container.append(tag);

    const buttons = stations.map(st => {
      const b = document.createElement("button");
      b.type = "button";
      b.className = "globe-beacon";
      b.setAttribute("aria-label", `${st.name} (${st.code}), ${fmtCoord(st.lat, "S", "N")} ${fmtCoord(st.lng, "E", "W")}, ${st.status_label}`);
      b.addEventListener("focus", () => { focused = st; showTag(st); draw(); });
      b.addEventListener("blur", () => { focused = null; if (!hovered) hideTag(); draw(); });
      b.addEventListener("click", () => select(st));
      container.append(b);
      st.button = b;
      return b;
    });

    /* ---- state ---- */
    let W = 0, H = 0, dpr = 1;
    let spin = opts.frontLng !== undefined ? (opts.frontLng - 90) * DEG : -47 * DEG;   // stations start front-right
    const elev = 50 * DEG;                   // camera height: high enough to read as a map
    const target = { x: 0, y: 0 }, tilt = { x: 0, y: 0 };
    let mouse = null;                        // canvas-relative pointer, for the ripple
    let hovered = null, focused = null, shown = null;
    let running = false, visible = true;
    const t0 = performance.now();
    let last = t0;

    function resize() {
      const r = container.getBoundingClientRect();
      W = r.width; H = r.height;
      dpr = Math.min(2, window.devicePixelRatio || 1);
      canvas.width = Math.round(W * dpr);
      canvas.height = Math.round(H * dpr);
      ctx.setTransform(dpr, 0, 0, dpr, 0, 0);
      draw();
    }

    /* world (rho, angle, z) -> screen; floor points pass spinFor = 0 */
    function project(rho, a, z, spinFor, out) {
      const ang = a + spinFor + tilt.x * 10 * DEG;
      const x = rho * Math.cos(ang), y = rho * Math.sin(ang);
      const e = elev - tilt.y * 6 * DEG;
      const up = y * Math.sin(e) + z * Math.cos(e);
      const depth = y * Math.cos(e) - z * Math.sin(e);
      const S = Math.min(W, H) * 0.355;
      const k = 4.2 / (4.2 + depth);
      out.x = W * 0.5 + x * S * k;
      out.y = H * 0.57 - up * S * k;
      out.d = depth;
      return out;
    }
    const P = { x: 0, y: 0, d: 0 }, Q = { x: 0, y: 0, d: 0 };
    const depthAlpha = d => 1 - Math.min(1, Math.max(0, (d + 1.1) / 2.2)) * 0.62;

    /* cursor ripple: a small lens (scaled to the globe) that lifts and re-inks the mesh */
    function ripple(px, py) {
      if (!mouse || REDUCED) return 0;
      const radius = Math.min(W, H) * 0.13;
      const dx = px - mouse.x, dy = py - mouse.y;
      const dist = Math.sqrt(dx * dx + dy * dy);
      return dist < radius ? Math.pow(1 - dist / radius, 2) : 0;
    }
    const liftPx = () => Math.min(W, H) * 0.018;

    function draw(now = performance.now()) {
      if (!W || !H) return;
      const t = now - t0;
      const reveal = REDUCED ? 1 : Math.min(1, t / 1700);
      const easeReveal = 1 - Math.pow(1 - reveal, 3);
      ctx.clearRect(0, 0, W, H);
      ctx.lineCap = "round";
      ctx.lineJoin = "round";

      /* floor: a fixed perspective grid clipped to a disc, like a turntable */
      ctx.lineWidth = 1;
      const R = 1.32;
      for (let g = -R; g <= R + 1e-6; g += 0.22) {
        const half = Math.sqrt(Math.max(0, R * R - g * g));
        for (const dir of [0, 1]) {
          const ax = dir ? g : -half, ay = dir ? -half : g, bx = dir ? g : half, by = dir ? half : g;
          project(Math.hypot(ax, ay), Math.atan2(ay, ax), 0, 0, P);
          project(Math.hypot(bx, by), Math.atan2(by, bx), 0, 0, Q);
          const grad = ctx.createLinearGradient(P.x, P.y, Q.x, Q.y);
          grad.addColorStop(0, rgba(C.glacier, 0.05 * easeReveal));
          grad.addColorStop(0.5, rgba(C.glacier, 0.13 * easeReveal));
          grad.addColorStop(1, rgba(C.glacier, 0.05 * easeReveal));
          ctx.strokeStyle = grad;
          ctx.beginPath(); ctx.moveTo(P.x, P.y); ctx.lineTo(Q.x, Q.y); ctx.stroke();
        }
      }

      /* bezel: graduated longitude ring that turns with the ice */
      ctx.lineWidth = 1;
      ctx.strokeStyle = rgba(C.ink, 0.28 * easeReveal);
      ctx.beginPath();
      for (let j = 0; j <= 180; j++) {
        project(1.14, (j / 180) * Math.PI * 2, 0, spin, P);
        j ? ctx.lineTo(P.x, P.y) : ctx.moveTo(P.x, P.y);
      }
      ctx.stroke();
      ctx.font = `500 ${Math.max(9, Math.round(W / 70))}px "JetBrains Mono", monospace`;
      ctx.textAlign = "center";
      ctx.textBaseline = "middle";
      for (let lng = 0; lng < 360; lng += 10) {
        const major = lng % 30 === 0;
        project(1.14, angleOf(lng), 0, spin, P);
        project(major ? 1.21 : 1.175, angleOf(lng), 0, spin, Q);
        const a = depthAlpha(P.d) * easeReveal;
        ctx.strokeStyle = rgba(C.ink, (major ? 0.55 : 0.3) * a);
        ctx.beginPath(); ctx.moveTo(P.x, P.y); ctx.lineTo(Q.x, Q.y); ctx.stroke();
        if (major) {
          project(1.29, angleOf(lng), 0, spin, Q);
          const label = lng === 0 ? "0°" : lng === 180 ? "180°" : lng < 180 ? `${lng}°E` : `${360 - lng}°W`;
          ctx.fillStyle = rgba(C.ink, 0.5 * a);
          ctx.fillText(label, Q.x, Q.y);
        }
      }

      /* radar sweep across the floor */
      const sweep = REDUCED ? -1.2 : (t / 5200) * Math.PI * 2;
      const slices = 16, width = 38 * DEG;
      for (let i = 0; i < slices; i++) {
        const a0 = sweep - width + (i / slices) * width, a1 = sweep - width + ((i + 1) / slices) * width;
        project(0, 0, 0, 0, P);
        ctx.fillStyle = rgba(C.glacier, 0.11 * (i / slices) * easeReveal);
        ctx.beginPath();
        ctx.moveTo(P.x, P.y);
        for (let k = 0; k <= 4; k++) {
          project(1.12, a0 + (a1 - a0) * (k / 4), 0, 0, Q);
          ctx.lineTo(Q.x, Q.y);
        }
        ctx.closePath(); ctx.fill();
      }
      project(0, 0, 0, 0, P); project(1.12, sweep, 0, 0, Q);
      ctx.strokeStyle = rgba(C.glacier, 0.5 * easeReveal);
      ctx.beginPath(); ctx.moveTo(P.x, P.y); ctx.lineTo(Q.x, Q.y); ctx.stroke();

      /* ice dome: contour rings (follow the coastline) + meridian spokes */
      const ringsShown = Math.ceil(easeReveal * NR);
      const lift = liftPx();
      const lifted = [];
      for (let k = 0; k < ringsShown; k++) {
        const ring = rings[k], pts = [];
        for (let j = 0; j < NS; j++) {
          const v = ring[j];
          project(v.rho, v.a, v.z, spin, P);
          const f = ripple(P.x, P.y);
          pts.push({ x: P.x, y: P.y - f * lift, d: P.d, f });
        }
        lifted.push(pts);
        const coast = k === NR - 1;
        const chunk = 12;
        for (let c = 0; c < NS; c += chunk) {
          const mid = pts[(c + chunk / 2) % NS];
          ctx.strokeStyle = rgba(C.ink, (coast ? 0.85 : 0.18 + 0.26 * (k / NR)) * depthAlpha(mid.d));
          ctx.lineWidth = coast ? 1.4 : 1;
          ctx.beginPath();
          for (let j = c; j <= c + chunk; j++) {
            const p = pts[j % NS];
            j === c ? ctx.moveTo(p.x, p.y) : ctx.lineTo(p.x, p.y);
          }
          ctx.stroke();
        }
      }
      ctx.lineWidth = 1;
      for (const sp of spokes) {
        const n = Math.max(1, Math.round(sp.length * easeReveal));
        project(sp[Math.min(n, sp.length - 1)].rho, sp[0].a, sp[Math.min(n, sp.length - 1)].z, spin, Q);
        ctx.strokeStyle = rgba(C.ink, 0.16 * depthAlpha(Q.d));
        ctx.beginPath();
        for (let k = 0; k < n; k++) {
          const v = sp[k];
          project(v.rho, v.a, v.z, spin, P);
          const f = ripple(P.x, P.y);
          k ? ctx.lineTo(P.x, P.y - f * lift) : ctx.moveTo(P.x, P.y - f * lift);
        }
        ctx.stroke();
      }
      /* the ripple: re-ink the segments under the cursor in glacier blue */
      if (mouse && !REDUCED) {
        for (const pts of lifted) {
          for (let j = 0; j < NS; j++) {
            const p = pts[j], q = pts[(j + 1) % NS];
            const f = (p.f + q.f) / 2;
            if (f < 0.02) continue;
            ctx.strokeStyle = rgba(C.glacier, f * 0.8);
            ctx.lineWidth = 1 + f;
            ctx.beginPath(); ctx.moveTo(p.x, p.y); ctx.lineTo(q.x, q.y); ctx.stroke();
          }
        }
        ctx.lineWidth = 1;
      }
      /* pole marker */
      project(0, 0, heightAt(0, 0), spin, P);
      ctx.strokeStyle = rgba(C.ink, 0.6 * easeReveal);
      ctx.beginPath();
      ctx.moveTo(P.x - 5, P.y); ctx.lineTo(P.x + 5, P.y); ctx.moveTo(P.x, P.y - 5); ctx.lineTo(P.x, P.y + 5);
      ctx.stroke();

      /* stations: pylon, pulsing ground ring, square beacon */
      const stationAlpha = Math.max(0, (reveal - 0.55) / 0.45);
      const screen = [];
      stations.forEach(st => {
        const base = project(st.rho, st.a, st.z, spin, { x: 0, y: 0, d: 0 });
        const top = project(st.rho, st.a, st.z + 0.15, spin, { x: 0, y: 0, d: 0 });
        screen.push({ st, base, top });
      });
      screen.forEach(({ st, base, top }) => {
        const hot = st === hovered || st === focused;
        const c = st.active ? C.glacier : C.ink40;
        const swept = Math.cos(st.a + spin - sweep);
        const boost = swept > 0.96 ? (swept - 0.96) / 0.04 : 0;

        if (!REDUCED || hot) {
          for (let r = 0; r < 2; r++) {
            const ph = ((t / 2600 + st.phase + r * 0.5) % 1);
            const rad = 0.02 + ph * (0.09 + boost * 0.05);
            ctx.strokeStyle = rgba(c, (1 - ph) * 0.7 * stationAlpha);
            ctx.beginPath();
            for (let k = 0; k <= 24; k++) {
              const ang = (k / 24) * Math.PI * 2;
              const x = st.rho * Math.cos(st.a) + rad * Math.cos(ang), y = st.rho * Math.sin(st.a) + rad * Math.sin(ang);
              project(Math.hypot(x, y), Math.atan2(y, x), st.z, spin, P);
              k ? ctx.lineTo(P.x, P.y) : ctx.moveTo(P.x, P.y);
            }
            ctx.stroke();
          }
        }
        ctx.strokeStyle = rgba(hot ? C.glacier : C.ink, 0.85 * stationAlpha);
        ctx.lineWidth = hot ? 1.6 : 1;
        ctx.beginPath(); ctx.moveTo(base.x, base.y); ctx.lineTo(top.x, top.y); ctx.stroke();
        const s = hot ? 9 : 6 + boost * 2;
        ctx.fillStyle = rgba(c, stationAlpha);
        ctx.fillRect(top.x - s / 2, top.y - s / 2, s, s);
        ctx.strokeStyle = rgba(C.ink, 0.8 * stationAlpha);
        ctx.lineWidth = 1;
        ctx.strokeRect(top.x - s / 2 - 3.5, top.y - s / 2 - 3.5, s + 7, s + 7);
      });

      /* station codes with short leaders. Labels are placed greedily (top to bottom) in the first
       * slot that collides with neither an earlier label nor another beacon, so Maitri and
       * Dakshin Gangotri, which sit almost on top of each other, stay readable. */
      const fontPx = Math.max(9, Math.round(W / 64));
      ctx.font = `500 ${fontPx}px "JetBrains Mono", monospace`;
      ctx.textBaseline = "middle";
      const placed = [];
      const SLOTS = [[1, -1], [-1, -1], [1, 1], [-1, 1], [1, -2.3], [-1, -2.3], [1, 2.3], [-1, 2.3]];
      [...screen].sort((a, b) => a.top.y - b.top.y).forEach(item => {
        const w = ctx.measureText(item.st.code).width, h = fontPx + 2;
        let pick = null;
        for (const [dx, dy] of SLOTS) {
          const lx = item.top.x + dx * 24, ly = item.top.y + dy * 13;
          const rect = dx > 0 ? [lx, ly - h / 2, lx + w, ly + h / 2] : [lx - w, ly - h / 2, lx, ly + h / 2];
          const hitsLabel = placed.some(r => !(rect[2] < r[0] - 5 || rect[0] > r[2] + 5 || rect[3] < r[1] - 2 || rect[1] > r[3] + 2));
          const hitsBeacon = screen.some(o => o !== item && o.top.x > rect[0] - 9 && o.top.x < rect[2] + 9 && o.top.y > rect[1] - 9 && o.top.y < rect[3] + 9);
          if (!hitsLabel && !hitsBeacon) { pick = { dx, lx, ly, rect }; break; }
        }
        pick = pick || { dx: 1, lx: item.top.x + 24, ly: item.top.y - 13, rect: [0, 0, 0, 0] };
        placed.push(pick.rect);
        ctx.strokeStyle = rgba(C.ink, 0.5 * stationAlpha);
        ctx.beginPath();
        ctx.moveTo(item.top.x + pick.dx * 8, item.top.y + (pick.ly < item.top.y ? -5 : 5));
        ctx.lineTo(pick.lx - pick.dx * 3, pick.ly);
        ctx.stroke();
        ctx.textAlign = pick.dx > 0 ? "left" : "right";
        ctx.fillStyle = rgba(C.ink, 0.9 * stationAlpha);
        ctx.fillText(item.st.code, pick.lx, pick.ly);
      });
      screen.forEach(item => {
        item.st.button.style.transform = `translate(${item.top.x.toFixed(1)}px, ${item.top.y.toFixed(1)}px)`;
      });

      /* VSAT satellite with dashed links to the active stations */
      const satA = REDUCED ? 0.4 : (t / 42000) * Math.PI * 2 + 0.4;
      const sat = project(0.58, satA, 1.02, 0, { x: 0, y: 0, d: 0 });
      const satAlpha = Math.max(0, (reveal - 0.75) / 0.25);
      if (satAlpha > 0) {
        screen.filter(s => s.st.active).forEach((item, i) => {
          const cx = (sat.x + item.top.x) / 2 + (sat.x < item.top.x ? -30 : 30), cy = Math.min(sat.y, item.top.y) - 34;
          ctx.setLineDash([3, 5]);
          ctx.lineDashOffset = REDUCED ? 0 : -t / 60;
          ctx.strokeStyle = rgba(C.glacier, 0.55 * satAlpha);
          ctx.beginPath(); ctx.moveTo(sat.x, sat.y); ctx.quadraticCurveTo(cx, cy, item.top.x, item.top.y); ctx.stroke();
          ctx.setLineDash([]);
          if (!REDUCED) {
            const u = ((t / 2300) + i * 0.45) % 1;
            const px = (1 - u) * (1 - u) * sat.x + 2 * (1 - u) * u * cx + u * u * item.top.x;
            const py = (1 - u) * (1 - u) * sat.y + 2 * (1 - u) * u * cy + u * u * item.top.y;
            ctx.fillStyle = rgba(C.signal, satAlpha);
            ctx.fillRect(px - 2, py - 2, 4, 4);
          }
        });
        drawSatellite(sat, satA, satAlpha);
      }

      /* keep the HUD tag glued to its beacon */
      const active = focused || hovered;
      if (active) {
        const item = screen.find(s => s.st === active);
        if (item) placeTag(item.top);
      }
    }

    function drawSatellite(pos, satA, alpha) {
      const s = Math.min(W, H) * 0.018;
      const tx = -Math.sin(satA), ty = Math.cos(satA) * Math.sin(elev);   // rough orbital tangent on screen
      const len = Math.hypot(tx, ty) || 1;
      const ux = tx / len, uy = ty / len;
      ctx.strokeStyle = rgba(C.ink, 0.9 * alpha);
      ctx.lineWidth = 1;
      // body: a small isometric cube
      const pts = [[-1, -1], [1, -1], [1, 1], [-1, 1]].map(([a, b]) => [pos.x + a * s * 0.6, pos.y + b * s * 0.6]);
      ctx.fillStyle = rgba([246, 248, 246], alpha);
      ctx.beginPath(); pts.forEach((p, i) => (i ? ctx.lineTo(p[0], p[1]) : ctx.moveTo(p[0], p[1]))); ctx.closePath();
      ctx.fill(); ctx.stroke();
      ctx.beginPath(); ctx.moveTo(pts[0][0], pts[0][1]); ctx.lineTo(pts[0][0] + s * 0.4, pts[0][1] - s * 0.4);
      ctx.lineTo(pts[1][0] + s * 0.4, pts[1][1] - s * 0.4); ctx.lineTo(pts[1][0], pts[1][1]);
      ctx.moveTo(pts[1][0] + s * 0.4, pts[1][1] - s * 0.4); ctx.lineTo(pts[2][0] + s * 0.4, pts[2][1] - s * 0.4);
      ctx.lineTo(pts[2][0], pts[2][1]); ctx.stroke();
      // solar panels along the tangent, hatched
      [-1, 1].forEach(side => {
        const x0 = pos.x + ux * side * s * 0.9, y0 = pos.y + uy * side * s * 0.9;
        const x1 = pos.x + ux * side * s * 2.6, y1 = pos.y + uy * side * s * 2.6;
        const nx = -uy * s * 0.55, ny = ux * s * 0.55;
        ctx.beginPath();
        ctx.moveTo(x0 + nx, y0 + ny); ctx.lineTo(x1 + nx, y1 + ny); ctx.lineTo(x1 - nx, y1 - ny); ctx.lineTo(x0 - nx, y0 - ny); ctx.closePath();
        ctx.stroke();
        for (let h = 1; h < 4; h++) {
          const f = h / 4;
          const hx = x0 + (x1 - x0) * f, hy = y0 + (y1 - y0) * f;
          ctx.beginPath(); ctx.moveTo(hx + nx, hy + ny); ctx.lineTo(hx - nx, hy - ny); ctx.stroke();
        }
      });
      ctx.font = `500 ${Math.max(9, Math.round(W / 72))}px "JetBrains Mono", monospace`;
      ctx.textAlign = "left";
      ctx.fillStyle = rgba(C.ink, 0.6 * alpha);
      ctx.fillText("VSAT-1", pos.x + s * 1.4, pos.y + s * 1.6);
    }

    /* ---- HUD tag ---- */
    function fmtCoord(v, pos, neg) {
      const a = Math.abs(v), d = Math.floor(a), m = Math.round((a - d) * 60);
      return `${d}°${String(m).padStart(2, "0")}′${v < 0 ? neg === "N" ? pos : neg : pos === "S" ? neg : pos}`;
    }
    function showTag(st) {
      if (!opts.hud) return;
      if (shown !== st) {
        shown = st;
        const lat = fmtCoord(st.lat, "S", "N"), lng = fmtCoord(st.lng, "E", "W");
        tag.innerHTML =
          `<span class="t-name" data-fx="decrypt">${esc(st.name)}</span>` +
          `<span class="t-row"><span>Code</span><b>${esc(st.code)}</b></span>` +
          `<span class="t-row"><span>Position</span><b>${lat} ${lng}</b></span>` +
          (st.established ? `<span class="t-row"><span>Established</span><b>${esc(String(st.established))}</b></span>` : "") +
          `<span class="t-row"><span>Status</span><b class="t-status${st.active ? "" : " off"}">${esc(st.active ? "Year-round" : st.status_label)}</b></span>` +
          (opts.onSelect ? `<span class="t-hint">Click for the datasheet ▸</span>` : "");
        if (window.PolarFX) window.PolarFX.init(tag);
      }
      tag.classList.add("is-on");
    }
    function hideTag() { tag.classList.remove("is-on"); shown = null; }
    function placeTag(p) {
      const flip = p.x > W * 0.58;
      tag.classList.toggle("flip", flip);
      tag.style.left = p.x + "px";
      tag.style.top = p.y + "px";
    }
    function esc(s) { return String(s).replace(/[&<>"']/g, c => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" })[c]); }

    function select(st) {
      if (opts.onSelect) opts.onSelect(st);
    }

    /* ---- pointer ---- */
    container.addEventListener("pointermove", e => {
      const r = container.getBoundingClientRect();
      mouse = { x: e.clientX - r.left, y: e.clientY - r.top };
      target.x = (mouse.x / r.width - 0.5) * 2;
      target.y = (mouse.y / r.height - 0.5) * 2;
      let best = null, bestD = 22;
      stations.forEach(st => {
        const m = /translate\(([-\d.]+)px, ([-\d.]+)px\)/.exec(st.button.style.transform);
        if (!m) return;
        const d = Math.hypot(+m[1] - mouse.x, +m[2] - mouse.y);
        if (d < bestD) { bestD = d; best = st; }
      });
      if (best !== hovered) {
        hovered = best;
        container.style.cursor = best && opts.onSelect ? "pointer" : "";
        if (best) showTag(best); else if (!focused) hideTag();
      }
      if (REDUCED) draw();
    }, { passive: true });
    container.addEventListener("pointerleave", () => {
      mouse = null; target.x = 0; target.y = 0; hovered = null; container.style.cursor = "";
      if (!focused) hideTag();
      if (REDUCED) draw();
    });
    container.addEventListener("click", e => {
      if (hovered && e.target === canvas) select(hovered);
    });

    /* ---- loop ---- */
    function frame(now) {
      if (!running) return;
      const dt = Math.min(64, now - last);
      last = now;
      spin += dt * 0.0000524;                  // about one turn every two minutes
      tilt.x += (target.x - tilt.x) * 0.05;
      tilt.y += (target.y - tilt.y) * 0.05;
      draw(now);
      requestAnimationFrame(frame);
    }
    function start() {
      if (running || REDUCED || !visible || document.hidden) return;
      running = true;
      last = performance.now();
      requestAnimationFrame(frame);
    }
    function stop() { running = false; }

    new ResizeObserver(resize).observe(container);
    if ("IntersectionObserver" in window) {
      new IntersectionObserver(([e]) => {
        visible = e.isIntersecting;
        visible ? start() : stop();
      }).observe(container);
    }
    document.addEventListener("visibilitychange", () => (document.hidden ? stop() : start()));

    const ready = document.fonts && document.fonts.ready ? document.fonts.ready : Promise.resolve();
    ready.then(() => {
      resize();
      container.classList.add("is-ready");
      start();
    });

    return { redraw: draw, stop, start, stations };
  }

  window.PolarGlobe = { mount };
})();
