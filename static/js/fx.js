/* PolarOps text + hover effects (vanilla ports in the spirit of reactbits.dev).
 *
 *   data-fx="split"    words rise out of a mask, staggered          (data-delay = ms)
 *   data-fx="decrypt"  glyph scramble that resolves to the text     (data-delay, data-hover)
 *   data-fx="rotate"   cycles words with a per-letter slide         (data-words = JSON list)
 *   data-fx="count"    counts up from zero when scrolled into view  (data-to, data-pad)
 *   data-fx="magnet"   element drifts toward the cursor
 *   data-fx="fade"     fade + rise when scrolled into view          (data-delay)
 *   data-fx="tilt"     card tilts toward the cursor with a soft glare (data-tilt = max degrees)
 *   data-fx="reveal"   adds .is-in once scrolled into view (CSS decides what that animates)
 *
 * Real text always stays available to screen readers, and everything resolves to its final
 * state immediately when the visitor prefers reduced motion.
 */
(function () {
  "use strict";

  const REDUCED = window.matchMedia("(prefers-reduced-motion: reduce)").matches;
  const FINE_POINTER = window.matchMedia("(pointer: fine)").matches;
  const GLYPHS = "ABCDEFGHJKLMNPQRSTUVWXYZ0123456789/\\-_+#%";

  function onceInView(el, cb, threshold = 0.2) {
    if (!("IntersectionObserver" in window)) { cb(); return; }
    const io = new IntersectionObserver(entries => {
      entries.forEach(e => {
        if (e.isIntersecting) { io.disconnect(); cb(); }
      });
    }, { threshold });
    io.observe(el);
  }

  const delayOf = el => parseInt(el.dataset.delay || "0", 10) || 0;
  const srWrap = (el, text) => {
    el.textContent = "";
    const sr = document.createElement("span");
    sr.className = "sr-only";
    sr.textContent = text;
    const vis = document.createElement("span");
    vis.setAttribute("aria-hidden", "true");
    el.append(sr, vis);
    return vis;
  };

  /* ---------------------------------------------------------------- split */
  function split(el) {
    let i = 0;
    const walk = node => {
      [...node.childNodes].forEach(child => {
        if (child.nodeType === Node.TEXT_NODE) {
          const parts = child.textContent.split(/(\s+)/);
          const frag = document.createDocumentFragment();
          parts.forEach(part => {
            if (!part) return;
            if (/^\s+$/.test(part)) { frag.append(document.createTextNode(part)); return; }
            const w = document.createElement("span");
            w.className = "w";
            const inner = document.createElement("span");
            inner.textContent = part;
            inner.style.setProperty("--i", i++);
            w.append(inner);
            frag.append(w);
          });
          child.replaceWith(frag);
        } else if (child.nodeType === Node.ELEMENT_NODE) {
          if (child.classList.contains("sr-only")) return;
          if (child.hasAttribute("data-split-skip")) {
            child.style.setProperty("--i", i++);
            return;
          }
          walk(child);
        }
      });
    };
    walk(el);
    el.classList.add("fx-split");
    el.style.setProperty("--d", delayOf(el) + "ms");
    if (REDUCED) { el.classList.add("is-in"); return; }
    onceInView(el, () => requestAnimationFrame(() => el.classList.add("is-in")), 0.1);
  }

  /* -------------------------------------------------------------- decrypt */
  function decrypt(el) {
    const finalText = (el.dataset.text || el.textContent).trim();
    const vis = srWrap(el, finalText);
    el.classList.add("fx-decrypt");
    vis.textContent = finalText;
    if (REDUCED) return;

    let running = false;
    const run = (duration = 1100) => {
      if (running) return;
      running = true;
      const chars = [...finalText];
      const start = performance.now();
      const revealAt = chars.map((_, k) => (k / chars.length) * duration * 0.7 + Math.random() * duration * 0.3);
      let lastSwap = 0;
      let scrambled = chars.map(c => c);
      const frame = now => {
        const t = now - start;
        if (now - lastSwap > 45) {
          scrambled = chars.map(c => (/\s/.test(c) ? c : GLYPHS[(Math.random() * GLYPHS.length) | 0]));
          lastSwap = now;
        }
        let done = "", enc = "";
        chars.forEach((c, k) => {
          if (t >= revealAt[k]) {
            if (enc) { done += `<span class="enc">${enc}</span>`; enc = ""; }
            done += escapeHtml(c);
          } else {
            enc += escapeHtml(scrambled[k]);
          }
        });
        if (enc) done += `<span class="enc">${enc}</span>`;
        vis.innerHTML = done;
        if (t < duration) requestAnimationFrame(frame);
        else { vis.textContent = finalText; running = false; }
      };
      requestAnimationFrame(frame);
    };

    onceInView(el, () => setTimeout(() => run(), delayOf(el)));
    if (el.dataset.hover !== undefined) {
      const target = el.closest("a, button, [data-decrypt-host]") || el;
      target.addEventListener("mouseenter", () => run(650));
      target.addEventListener("focus", () => run(650));
    }
  }

  function escapeHtml(s) {
    return s.replace(/[&<>"']/g, c => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" })[c]);
  }

  /* --------------------------------------------------------------- rotate */
  function rotate(el) {
    let words;
    try { words = JSON.parse(el.dataset.words || "[]"); } catch (e) { words = []; }
    if (words.length < 2) return;
    const label = words.length > 2
      ? words.slice(0, -1).join(", ") + " and " + words[words.length - 1]
      : words.join(" and ");
    const vis = srWrap(el, label);
    if (REDUCED) { vis.textContent = words.join(" / "); return; }

    el.classList.add("fx-rotate");
    const render = (word, cls) => {
      vis.innerHTML = "";
      [...word].forEach((c, k) => {
        const s = document.createElement("span");
        s.className = "ch" + (cls ? " " + cls : "");
        s.style.setProperty("--i", k);
        s.textContent = c === " " ? " " : c;
        vis.append(s);
      });
    };
    let idx = 0;
    render(words[0]);
    el.style.width = vis.scrollWidth + "px";

    const interval = parseInt(el.dataset.interval || "2800", 10);
    setInterval(() => {
      if (document.hidden) return;
      vis.querySelectorAll(".ch").forEach(s => s.classList.add("out"));
      const outFor = 320 + vis.children.length * 22;
      setTimeout(() => {
        idx = (idx + 1) % words.length;
        render(words[idx], "in");
        el.style.width = vis.scrollWidth + "px";
        void vis.offsetWidth;   // reflow so the "in" state is painted before it is removed
        requestAnimationFrame(() => vis.querySelectorAll(".ch").forEach(s => s.classList.remove("in")));
      }, outFor);
    }, interval);
  }

  /* ---------------------------------------------------------------- count */
  function count(el) {
    const to = parseFloat(el.dataset.to);
    if (Number.isNaN(to)) return;
    const pad = parseInt(el.dataset.pad || "0", 10);
    const decimals = parseInt(el.dataset.decimals || "0", 10);
    const fmt = v => {
      const s = v.toFixed(decimals);
      return pad ? s.padStart(pad, "0") : s;
    };
    if (REDUCED) { el.textContent = fmt(to); return; }
    el.textContent = fmt(0);
    onceInView(el, () => {
      const start = performance.now() + delayOf(el);
      const dur = parseInt(el.dataset.dur || "1600", 10);
      const ease = t => (t === 1 ? 1 : 1 - Math.pow(2, -10 * t));
      const frame = now => {
        const t = Math.min(1, Math.max(0, (now - start) / dur));
        el.textContent = fmt(to * ease(t));
        if (t < 1) requestAnimationFrame(frame);
      };
      requestAnimationFrame(frame);
    });
  }

  /* --------------------------------------------------------------- magnet */
  function magnet(el) {
    if (REDUCED || !FINE_POINTER) return;
    const strength = parseFloat(el.dataset.strength || "0.25");
    const pad = 36;
    window.addEventListener("pointermove", e => {
      const r = el.getBoundingClientRect();
      const inside = e.clientX > r.left - pad && e.clientX < r.right + pad && e.clientY > r.top - pad && e.clientY < r.bottom + pad;
      if (inside) {
        const dx = (e.clientX - (r.left + r.width / 2)) * strength;
        const dy = (e.clientY - (r.top + r.height / 2)) * strength;
        el.style.setProperty("--mx", dx.toFixed(1) + "px");
        el.style.setProperty("--my", dy.toFixed(1) + "px");
      } else if (el.style.getPropertyValue("--mx")) {
        el.style.setProperty("--mx", "0px");
        el.style.setProperty("--my", "0px");
      }
    }, { passive: true });
  }

  /* ----------------------------------------------------------------- fade */
  function fade(el) {
    el.classList.add("fx-fade");
    el.style.setProperty("--d", delayOf(el) + "ms");
    if (REDUCED) { el.classList.add("is-in"); return; }
    onceInView(el, () => requestAnimationFrame(() => el.classList.add("is-in")), 0.15);
  }

  /* ----------------------------------------------------------------- tilt */
  function tilt(el) {
    el.classList.add("fx-tilt");
    if (REDUCED || !FINE_POINTER) return;
    const max = parseFloat(el.dataset.tilt || "3.5");
    el.addEventListener("pointermove", e => {
      const r = el.getBoundingClientRect();
      const px = (e.clientX - r.left) / r.width, py = (e.clientY - r.top) / r.height;
      el.classList.add("is-tilting");
      el.style.setProperty("--ry", ((px - 0.5) * max * 2).toFixed(2) + "deg");
      el.style.setProperty("--rx", ((0.5 - py) * max * 2).toFixed(2) + "deg");
      el.style.setProperty("--gx", (px * 100).toFixed(1) + "%");
      el.style.setProperty("--gy", (py * 100).toFixed(1) + "%");
      el.style.setProperty("--glare", "1");
    });
    el.addEventListener("pointerleave", () => {
      el.classList.remove("is-tilting");
      el.style.setProperty("--rx", "0deg");
      el.style.setProperty("--ry", "0deg");
      el.style.setProperty("--glare", "0");
    });
  }

  /* --------------------------------------------------------------- reveal */
  function reveal(el) {
    if (REDUCED) { el.classList.add("is-in"); return; }
    onceInView(el, () => el.classList.add("is-in"), 0.3);
  }

  const EFFECTS = { split, decrypt, rotate, count, magnet, fade, tilt, reveal };

  function init(root = document) {
    root.querySelectorAll("[data-fx]").forEach(el => {
      if (el.dataset.fxReady) return;
      el.dataset.fxReady = "1";
      el.dataset.fx.split(/\s+/).forEach(name => EFFECTS[name] && EFFECTS[name](el));
    });
  }

  window.PolarFX = { init, reduced: REDUCED };
  if (document.readyState === "loading") document.addEventListener("DOMContentLoaded", () => init());
  else init();
})();
