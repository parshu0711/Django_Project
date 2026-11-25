/* PolarOps interface helpers (replaces what Bootstrap's JS used to do).
 *
 *   [data-menu-toggle="<id>"]  toggles .is-open on #<id>; Esc and outside click close it
 *   [data-clock]               live HH:MM in data-tz (IANA zone), refreshed every 15 s
 */
(function () {
  "use strict";

  function menus() {
    document.querySelectorAll("[data-menu-toggle]").forEach(btn => {
      const host = document.getElementById(btn.dataset.menuToggle);
      if (!host) return;
      const set = open => {
        host.classList.toggle("is-open", open);
        btn.setAttribute("aria-expanded", String(open));
        const icon = btn.querySelector("i");
        if (icon) icon.className = open ? "ph-light ph-x" : "ph-light ph-list";
      };
      btn.addEventListener("click", e => {
        e.stopPropagation();
        set(!host.classList.contains("is-open"));
      });
      document.addEventListener("click", e => {
        if (host.classList.contains("is-open") && !host.contains(e.target)) set(false);
      });
      document.addEventListener("keydown", e => {
        if (e.key === "Escape" && host.classList.contains("is-open")) { set(false); btn.focus(); }
      });
      host.querySelectorAll("a[href^='#']").forEach(a => a.addEventListener("click", () => set(false)));
    });
  }

  function clocks() {
    const els = document.querySelectorAll("[data-clock]");
    if (!els.length) return;
    const fmt = {};
    const tick = () => {
      const now = new Date();
      els.forEach(el => {
        const tz = el.dataset.tz || "UTC";
        try {
          fmt[tz] = fmt[tz] || new Intl.DateTimeFormat("en-GB", { hour: "2-digit", minute: "2-digit", hour12: false, timeZone: tz });
          el.textContent = fmt[tz].format(now);
        } catch (e) {
          el.textContent = "--:--";
        }
      });
    };
    tick();
    setInterval(tick, 15000);
  }

  /* [data-dropdown]: the first button toggles .is-open on the host; one open at a time */
  function dropdowns() {
    const hosts = [...document.querySelectorAll("[data-dropdown]")];
    if (!hosts.length) return;
    const close = (host, focusBtn) => {
      host.classList.remove("is-open");
      const btn = host.querySelector("button");
      btn.setAttribute("aria-expanded", "false");
      if (focusBtn) btn.focus();
    };
    const items = host => [...host.querySelectorAll(".menu-panel a, .menu-panel button:not([disabled])")];
    hosts.forEach(host => {
      const btn = host.querySelector("button");
      btn.addEventListener("click", e => {
        e.stopPropagation();
        const open = !host.classList.contains("is-open");
        hosts.forEach(h => h !== host && close(h));
        host.classList.toggle("is-open", open);
        btn.setAttribute("aria-expanded", String(open));
      });
      btn.addEventListener("keydown", e => {
        if (e.key === "ArrowDown") {
          e.preventDefault();
          if (!host.classList.contains("is-open")) btn.click();
          const first = items(host)[0];
          if (first) first.focus();
        }
      });
      host.addEventListener("keydown", e => {
        if (!host.classList.contains("is-open")) return;
        const list = items(host), i = list.indexOf(document.activeElement);
        if (e.key === "Escape") { e.preventDefault(); close(host, true); }
        else if (e.key === "ArrowDown" && i > -1) { e.preventDefault(); list[(i + 1) % list.length].focus(); }
        else if (e.key === "ArrowUp" && i > -1) { e.preventDefault(); (i === 0 ? btn : list[i - 1]).focus(); }
      });
    });
    document.addEventListener("click", e => hosts.forEach(h => !h.contains(e.target) && close(h)));
  }

  /* [data-dismiss] removes its notice */
  function dismissers() {
    document.querySelectorAll("[data-dismiss]").forEach(b => b.addEventListener("click", () => {
      const n = b.closest(".notice");
      if (n) n.remove();
    }));
  }

  function init() { menus(); dropdowns(); dismissers(); clocks(); }
  if (document.readyState === "loading") document.addEventListener("DOMContentLoaded", init);
  else init();
})();
