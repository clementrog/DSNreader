// Toast « Démo publique de Linc » (bottom right).
//
// Reads the next group demo from www.linc.fr. Served through the path-mode
// rewrite (www.linc.fr/ressources/controle-dsn/simulateur) the request is
// same-origin. On the raw Koyeb URL it is cross-origin and not granted by
// linc.fr's CORS rule (*.linc.fr only), so the toast simply never shows there.
// Any failure (network, timeout, no open session) renders nothing.
(function () {
  "use strict";

  var API_URL = "https://www.linc.fr/api/demo-live";
  // The sign-up link (www.linc.fr/demo-live?utm_source=controle-dsn…) lives in index.html.
  var TOOL = "controle-dsn";
  var STORAGE_KEY = "linc-demo-live-toast";
  var FETCH_TIMEOUT_MS = 4000;
  var SHOW_DELAY_MS = 4000;
  var TIME_ZONE = "Europe/Paris";

  var $toast = document.getElementById("demo-live-toast");
  if (!$toast || typeof fetch !== "function") return;
  var $title = document.getElementById("demo-live-toast-title");
  var $date = document.getElementById("demo-live-toast-date");
  var $link = document.getElementById("demo-live-toast-link");
  var $close = document.getElementById("demo-live-toast-close");

  // "Jeudi 8 octobre à 11h" / "Jeudi 5 novembre à 10h30", Paris time.
  function dateLabel(startIso) {
    var d = new Date(startIso);
    var day = new Intl.DateTimeFormat("fr-FR", {
      timeZone: TIME_ZONE,
      weekday: "long",
      day: "numeric",
      month: "long",
    }).format(d);
    var parts = new Intl.DateTimeFormat("fr-FR", {
      timeZone: TIME_ZONE,
      hour: "2-digit",
      minute: "2-digit",
    })
      .format(d)
      .split(":");
    var time = Number(parts[0]) + "h" + (parts[1] === "00" ? "" : parts[1]);
    return day.charAt(0).toUpperCase() + day.slice(1) + " à " + time;
  }

  function titleFor(durationMin) {
    var base = "Démo publique de Linc";
    return durationMin > 0 ? base + " (" + durationMin + " min)" : base;
  }

  function dismissedId() {
    try {
      return window.localStorage.getItem(STORAGE_KEY);
    } catch (e) {
      return null;
    }
  }

  function rememberDismissed(id) {
    try {
      window.localStorage.setItem(STORAGE_KEY, id);
    } catch (e) {
      // Private mode or blocked storage: the toast may come back next visit.
    }
  }

  function track(name, sessionId) {
    if (typeof window.gtag === "function") {
      window.gtag("event", name, { tool: TOOL, session_id: sessionId });
    }
  }

  function hide() {
    $toast.classList.remove("demo-toast--visible");
    $toast.hidden = true;
  }

  function show(session) {
    $title.textContent = titleFor(Number(session.durationMin) || 0);
    $date.textContent = dateLabel(session.start);

    $close.addEventListener("click", function () {
      rememberDismissed(session.id);
      track("demo_live_toast_dismiss", session.id);
      hide();
    });
    $link.addEventListener("click", function () {
      rememberDismissed(session.id);
      track("demo_live_toast_click", session.id);
      hide();
    });

    $toast.hidden = false;
    // Next frame, so the transition runs from the hidden state.
    window.requestAnimationFrame(function () {
      $toast.classList.add("demo-toast--visible");
    });
    track("demo_live_toast_view", session.id);
  }

  function load() {
    var controller = typeof AbortController === "function" ? new AbortController() : null;
    var timer = controller ? window.setTimeout(function () { controller.abort(); }, FETCH_TIMEOUT_MS) : null;

    fetch(API_URL, controller ? { signal: controller.signal } : undefined)
      .then(function (res) {
        if (!res.ok) throw new Error("demo-live " + res.status);
        return res.json();
      })
      .then(function (body) {
        if (timer) window.clearTimeout(timer);
        var session = body && body.status === "open" && Array.isArray(body.sessions) ? body.sessions[0] : null;
        if (!session || !session.id || !session.start || isNaN(Date.parse(session.start))) return;
        if (dismissedId() === session.id) return;
        window.setTimeout(function () { show(session); }, SHOW_DELAY_MS);
      })
      .catch(function () {
        if (timer) window.clearTimeout(timer);
        // Nothing to announce: stay hidden.
      });
  }

  load();
})();
