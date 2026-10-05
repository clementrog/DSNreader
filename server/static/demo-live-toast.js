// Toast « Démo publique de Linc » (bottom right, desktop only).
//
// Reads the next group demo from www.linc.fr. Served through the path-mode
// rewrite (www.linc.fr/ressources/controle-dsn/simulateur) the request is
// same-origin. On the raw Koyeb URL it is cross-origin and not granted by
// linc.fr's CORS rule (*.linc.fr only), so the toast simply never shows there.
// Any failure (network, timeout, no open session) renders nothing.
//
// While the toast is pending or visible it re-reads the API every minute (and
// when the tab comes back), and hides when the session starts, is cancelled,
// replaced or paused. Under 768 px it never shows: it would cover the tool.
(function () {
  "use strict";

  var API_URL = "https://www.linc.fr/api/demo-live";
  // The sign-up link (www.linc.fr/demo-live?utm_source=controle-dsn…) lives in index.html.
  var TOOL = "controle-dsn";
  var STORAGE_KEY = "linc-demo-live-toast";
  var FETCH_TIMEOUT_MS = 4000;
  var SHOW_DELAY_MS = 4000;
  var RECHECK_MS = 60000;
  var MAX_TIMER_MS = 2147483647;
  var PHONE_QUERY = "(max-width: 767px)";
  var TIME_ZONE = "Europe/Paris";

  var $toast = document.getElementById("demo-live-toast");
  if (!$toast || typeof fetch !== "function") return;
  var $title = document.getElementById("demo-live-toast-title");
  var $date = document.getElementById("demo-live-toast-date");
  var $link = document.getElementById("demo-live-toast-link");
  var $close = document.getElementById("demo-live-toast-close");

  // ── Pure rules ──────────────────────────────────────────

  function firstSession(body) {
    if (!body || body.status !== "open" || !Array.isArray(body.sessions)) return null;
    var s = body.sessions[0];
    if (!s || !s.id || !s.start || isNaN(Date.parse(s.start))) return null;
    return s;
  }

  // The session to announce on load: open, not started, not dismissed.
  function pickSession(body, dismissed, now) {
    var s = firstSession(body);
    if (!s || Date.parse(s.start) <= now || s.id === dismissed) return null;
    return s;
  }

  // After a recheck: the announced session as it now reads, or null to hide.
  // Same id means same calendar occurrence, even when the organiser moved it
  // or changed its length ("this occurrence only" keeps the id).
  function refreshAnnouncement(body, announced, now) {
    var s = firstSession(body);
    if (!s || s.id !== announced.id || Date.parse(s.start) <= now) return null;
    return s;
  }

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

  // ── Side effects ────────────────────────────────────────

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

  // `session_id` is reserved by GA4 (the browsing session), hence `demo_session_id`.
  function track(name, demoSessionId) {
    if (typeof window.gtag === "function") {
      window.gtag("event", name, { tool: TOOL, demo_session_id: demoSessionId });
    }
  }

  function readApi() {
    var controller = typeof AbortController === "function" ? new AbortController() : null;
    var timer = controller ? window.setTimeout(function () { controller.abort(); }, FETCH_TIMEOUT_MS) : null;
    return fetch(API_URL, controller ? { signal: controller.signal } : undefined)
      .then(function (res) {
        if (!res.ok) throw new Error("demo-live " + res.status);
        return res.json();
      })
      .then(
        function (body) {
          if (timer) window.clearTimeout(timer);
          return body;
        },
        function (err) {
          if (timer) window.clearTimeout(timer);
          throw err;
        }
      );
  }

  // ── Lifecycle: pending (4 s delay) → visible → done ─────

  var announced = null;
  var done = false;
  var showTimer = null;
  var startTimer = null;
  var recheckTimer = null;

  function stop() {
    done = true;
    window.clearTimeout(showTimer);
    window.clearTimeout(startTimer);
    window.clearInterval(recheckTimer);
    document.removeEventListener("visibilitychange", onVisibility);
    $toast.classList.remove("demo-toast--visible");
    $toast.hidden = true;
  }

  function render(session) {
    $title.textContent = titleFor(Number(session.durationMin) || 0);
    $date.textContent = dateLabel(session.start);
  }

  // Hide exactly when the session starts (longer delays: the recheck covers it).
  function scheduleStart(session) {
    window.clearTimeout(startTimer);
    var untilStart = Date.parse(session.start) - Date.now();
    if (untilStart <= MAX_TIMER_MS) startTimer = window.setTimeout(stop, untilStart);
  }

  function recheck() {
    if (done || document.visibilityState !== "visible") return;
    readApi().then(
      function (body) {
        if (done) return;
        var fresh = refreshAnnouncement(body, announced, Date.now());
        if (!fresh) {
          stop();
          return;
        }
        if (fresh.start !== announced.start || fresh.durationMin !== announced.durationMin) {
          // Moved or resized: update in place, no new view event.
          announced = fresh;
          render(fresh);
          scheduleStart(fresh);
        }
      },
      function () {
        // Transient failure: keep the current state.
      }
    );
  }

  function onVisibility() {
    if (document.visibilityState === "visible") recheck();
  }

  function show() {
    if (done) return;
    if (window.matchMedia && window.matchMedia(PHONE_QUERY).matches) {
      stop();
      return;
    }
    $toast.hidden = false;
    // Next frame, so the transition runs from the hidden state.
    window.requestAnimationFrame(function () {
      if (!done) $toast.classList.add("demo-toast--visible");
    });
    track("demo_live_toast_view", announced.id);
  }

  function announce(session) {
    announced = session;
    render(session);

    // The id never changes for an announcement (a different id hides it).
    $close.addEventListener("click", function () {
      rememberDismissed(announced.id);
      track("demo_live_toast_dismiss", announced.id);
      stop();
    });
    $link.addEventListener("click", function () {
      rememberDismissed(announced.id);
      track("demo_live_toast_click", announced.id);
      stop();
    });

    scheduleStart(session);
    recheckTimer = window.setInterval(recheck, RECHECK_MS);
    document.addEventListener("visibilitychange", onVisibility);
    showTimer = window.setTimeout(show, SHOW_DELAY_MS);
  }

  readApi().then(
    function (body) {
      var session = pickSession(body, dismissedId(), Date.now());
      if (session) announce(session);
    },
    function () {
      // Nothing to announce: stay hidden.
    }
  );
})();
