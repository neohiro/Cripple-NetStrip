---
layout: default
title: Onboarding
description: "Triage popup for the FrenzyPenguin Media assistant"
permalink: /onboard/
---

<!--
  /onboard/ — Slide-in popup triage.

  Designed to be embedded in an iframe on the main site
  (https://frenzypenguin.media/onboard/?embed=1) or opened as a full page.

  When ?embed=1 is set, the chrome is hidden so only the slide-in panel shows.
  The triage flow is the same as the request-access page, but compressed
  (3 steps instead of 6) and visually framed as a popup.
-->

<div class="onboard-stage" id="onboard-stage" data-mode="full">
  <div class="onboard-backdrop" id="onboard-backdrop" aria-hidden="true"></div>

  <main class="onboard-panel" id="onboard-panel" role="dialog" aria-modal="false"
        aria-labelledby="onboard-title">
    <header class="onboard-header">
      <div class="onboard-brand">
        <span class="onboard-pulse" aria-hidden="true"></span>
        <span class="onboard-brand-text">FrenzyPenguin Media</span>
      </div>
      <button class="onboard-close" id="onboard-close" aria-label="Close onboarding">
        <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" width="20" height="20">
          <path d="M18 6L6 18M6 6l12 12"/>
        </svg>
      </button>
    </header>

    <div class="onboard-body">
      <div class="onboard-step" data-step="welcome">
        <div class="onboard-illustration" aria-hidden="true">
          <!-- A penguin (waddle motif) -->
          <svg viewBox="0 0 200 200" width="120" height="120">
            <ellipse cx="100" cy="170" rx="65" ry="8" fill="rgba(0,0,0,0.2)"/>
            <path d="M100 30 C 60 30 50 70 50 110 C 50 160 75 180 100 180 C 125 180 150 160 150 110 C 150 70 140 30 100 30 Z" fill="#0a0e14" stroke="#1a2030" stroke-width="2"/>
            <path d="M100 50 C 80 50 70 75 70 110 C 70 145 85 160 100 160 C 115 160 130 145 130 110 C 130 75 120 50 100 50 Z" fill="#f5f5f5"/>
            <circle cx="100" cy="100" r="32" fill="#0a0e14"/>
            <path d="M70 95 C 75 88 80 85 85 88 L 88 100 L 80 105 Z" fill="#fff"/>
            <path d="M130 95 C 125 88 120 85 115 88 L 112 100 L 120 105 Z" fill="#fff"/>
            <circle cx="84" cy="97" r="4" fill="#0a0e14"/>
            <circle cx="116" cy="97" r="4" fill="#0a0e14"/>
            <path d="M92 110 L 100 118 L 108 110 Z" fill="#ffaa44"/>
            <path d="M85 135 C 75 145 75 155 85 160" stroke="#ffaa44" stroke-width="6" fill="none" stroke-linecap="round"/>
            <path d="M115 135 C 125 145 125 155 115 160" stroke="#ffaa44" stroke-width="6" fill="none" stroke-linecap="round"/>
          </svg>
        </div>
        <h1 id="onboard-title" class="onboard-title">Welcome, waddler.</h1>
        <p class="onboard-lede">
          The assistant lives behind a quiet triage gate. Three quick steps
          and we know enough to route you. No accounts, no telemetry, no email
          unless you want one.
        </p>
        <p class="onboard-meta">
          ⏱ ~ 90 seconds · 🔒 hashed identifiers only · 🩺 your answers are reviewed by a real human
        </p>
        <div class="onboard-actions">
          <button class="btn btn-primary" id="onboard-begin">Begin triage →</button>
          <a href="{{ '/request-access/' | relative_url }}" class="btn btn-ghost">Open full questionnaire</a>
        </div>
      </div>

      <div class="onboard-step" data-step="profile" hidden>
        <div class="onboard-progress" aria-hidden="true">
          <span class="onboard-pip onboard-pip-on"></span>
          <span class="onboard-pip"></span>
          <span class="onboard-pip"></span>
        </div>
        <h2 class="onboard-h2">What's your handle?</h2>
        <p class="onboard-hint">GitHub, Mastodon, LinkedIn — anything we can match publicly.</p>
        <div class="onboard-field">
          <input type="text" id="onboard-handle" autocomplete="off" placeholder="@your-handle" maxlength="64">
        </div>
        <div class="onboard-field onboard-choices">
          <label class="onboard-choice">
            <input type="radio" name="role" value="personal" checked>
            <span>Personal use</span>
          </label>
          <label class="onboard-choice">
            <input type="radio" name="role" value="org">
            <span>Organisation / team</span>
          </label>
          <label class="onboard-choice">
            <input type="radio" name="role" value="research">
            <span>Research / audit</span>
          </label>
        </div>
        <div class="onboard-actions">
          <button class="btn btn-secondary" data-back>← Back</button>
          <button class="btn btn-primary" id="onboard-next-1">Next →</button>
        </div>
      </div>

      <div class="onboard-step" data-step="verify" hidden>
        <div class="onboard-progress" aria-hidden="true">
          <span class="onboard-pip onboard-pip-on"></span>
          <span class="onboard-pip onboard-pip-on"></span>
          <span class="onboard-pip"></span>
        </div>
        <h2 class="onboard-h2">Verify you're real</h2>
        <p class="onboard-hint">Pick one. We never share your contact info.</p>
        <div class="onboard-field onboard-choices">
          <label class="onboard-choice">
            <input type="radio" name="verify" value="public-github" checked>
            <span>My handle is a public, &gt; 30-day-old GitHub account</span>
          </label>
          <label class="onboard-choice">
            <input type="radio" name="verify" value="email">
            <span>Send a one-time code to a corporate / academic email</span>
          </label>
          <label class="onboard-choice">
            <input type="radio" name="verify" value="referral">
            <span>An existing user can vouch for me</span>
          </label>
        </div>
        <div class="onboard-actions">
          <button class="btn btn-secondary" data-back>← Back</button>
          <button class="btn btn-primary" id="onboard-next-2">Next →</button>
        </div>
      </div>

      <div class="onboard-step" data-step="done" hidden>
        <div class="onboard-progress" aria-hidden="true">
          <span class="onboard-pip onboard-pip-on"></span>
          <span class="onboard-pip onboard-pip-on"></span>
          <span class="onboard-pip onboard-pip-on"></span>
        </div>
        <div class="onboard-check" aria-hidden="true">
          <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" width="48" height="48">
            <circle cx="12" cy="12" r="11" stroke="currentColor" fill="rgba(120, 200, 120, 0.1)"/>
            <path d="M8 12l3 3 5-6"/>
          </svg>
        </div>
        <h2 class="onboard-h2">Routed for triage</h2>
        <p class="onboard-hint" id="onboard-routed-summary">
          Your request is in the queue. The God Admin will review it within 24 hours.
          You'll be notified via your chosen channel.
        </p>
        <div class="onboard-actions">
          <button class="btn btn-primary" id="onboard-finish">Done</button>
          <a href="{{ '/request-access/' | relative_url }}" class="btn btn-ghost">Open full questionnaire for more detail</a>
        </div>
      </div>
    </div>

    <div class="onboard-footer">
      <span>Triage powered by the neohiro cadence engine.</span>
      <span>
        <a href="{{ '/privacy/' | relative_url }}">Privacy</a> ·
        <a href="{{ '/tos/' | relative_url }}">Terms</a>
      </span>
    </div>
  </main>
</div>

<script>
(function() {
  const params = new URLSearchParams(location.search);
  const embed = params.get("embed") === "1";
  const stage = document.getElementById("onboard-stage");
  if (embed) {
    stage.dataset.mode = "embed";
    document.documentElement.classList.add("onboard-embed");
  }

  const steps = ["welcome", "profile", "verify", "done"];
  let i = 0;
  const $ = (id) => document.getElementById(id);
  const show = (name) => {
    document.querySelectorAll(".onboard-step").forEach(el => {
      el.hidden = el.dataset.step !== name;
    });
    i = steps.indexOf(name);
    // Slide-in animation
    const panel = $("onboard-panel");
    panel.classList.remove("onboard-slide-in");
    void panel.offsetWidth;
    panel.classList.add("onboard-slide-in");
  };

  $("onboard-begin").addEventListener("click", () => show("profile"));
  $("onboard-next-1").addEventListener("click", () => {
    if (!$("onboard-handle").value.trim()) {
      flash("Please enter a handle so we can match you.");
      return;
    }
    show("verify");
  });
  $("onboard-next-2").addEventListener("click", () => show("done"));
  document.querySelectorAll("[data-back]").forEach(b => {
    b.addEventListener("click", () => show(steps[Math.max(0, i - 1)]));
  });
  $("onboard-close").addEventListener("click", () => {
    if (embed) {
      // Send a message to parent (if iframe) and try to close
      try { parent.postMessage({type: "neohiro:onboard:close"}, "*"); } catch (e) {}
    } else {
      history.back();
    }
  });
  $("onboard-backdrop").addEventListener("click", () => $("onboard-close").click());
  $("onboard-finish").addEventListener("click", () => {
    try { parent.postMessage({type: "neohiro:onboard:done"}, "*"); } catch (e) {}
    if (embed) {
      try { parent.postMessage({type: "neohiro:onboard:close"}, "*"); } catch (e) {}
    } else {
      location.href = "{{ '/' | relative_url }}";
    }
  });

  function flash(msg) {
    const status = document.createElement("div");
    status.className = "onboard-flash";
    status.textContent = msg;
    document.querySelector(".onboard-body").appendChild(status);
    setTimeout(() => status.remove(), 3000);
  }

  // Listen for parent messages asking to open
  window.addEventListener("message", (e) => {
    if (e.data && e.data.type === "neohiro:onboard:open") {
      show("welcome");
    }
  });

  // ESC closes
  document.addEventListener("keydown", (e) => {
    if (e.key === "Escape") $("onboard-close").click();
  });

  show("welcome");
})();
</script>

<style>
  /* Onboard stage: when embed=1, hide the backdrop and center the panel */
  .onboard-stage {
    position: relative;
    min-height: 100vh;
    display: flex;
    align-items: center;
    justify-content: center;
  }
  html.onboard-embed .onboard-stage {
    min-height: auto;
    padding: 0;
  }
  html.onboard-embed body { background: transparent; }
  html.onboard-embed .onboard-backdrop { display: none; }

  .onboard-backdrop {
    position: fixed;
    inset: 0;
    background: radial-gradient(circle at 30% 20%, rgba(120, 200, 200, 0.08), transparent 60%),
                rgba(0, 0, 0, 0.6);
    backdrop-filter: blur(6px);
    z-index: 0;
  }
  .onboard-panel {
    position: relative;
    z-index: 1;
    width: min(420px, 92vw);
    max-height: 90vh;
    background: var(--card-bg, #0a0e14);
    border: 1px solid var(--border, rgba(255, 255, 255, 0.1));
    border-radius: 16px;
    box-shadow: 0 30px 80px rgba(0, 0, 0, 0.5);
    display: flex;
    flex-direction: column;
    overflow: hidden;
  }
  .onboard-panel.onboard-slide-in {
    animation: onboard-slide-in 0.45s cubic-bezier(0.16, 1, 0.3, 1);
  }
  @keyframes onboard-slide-in {
    from { transform: translateX(40px) scale(0.98); opacity: 0; }
    to   { transform: translateX(0) scale(1); opacity: 1; }
  }
  @media (prefers-reduced-motion: reduce) {
    .onboard-panel.onboard-slide-in { animation: none; }
  }

  .onboard-header {
    display: flex;
    justify-content: space-between;
    align-items: center;
    padding: 16px 20px;
    border-bottom: 1px solid var(--border, rgba(255, 255, 255, 0.08));
  }
  .onboard-brand {
    display: flex;
    align-items: center;
    gap: 8px;
    font-weight: 600;
    letter-spacing: 0.5px;
  }
  .onboard-pulse {
    width: 10px;
    height: 10px;
    border-radius: 50%;
    background: var(--accent);
    box-shadow: 0 0 0 0 var(--accent);
    animation: onboard-pulse 2s ease-in-out infinite;
  }
  @keyframes onboard-pulse {
    0%, 100% { box-shadow: 0 0 0 0 rgba(120, 200, 200, 0.5); }
    50%      { box-shadow: 0 0 0 6px rgba(120, 200, 200, 0); }
  }
  .onboard-close {
    background: none;
    border: none;
    color: var(--fg-muted, #aaa);
    cursor: pointer;
    padding: 4px;
    border-radius: 6px;
    transition: background 0.2s ease, color 0.2s ease;
  }
  .onboard-close:hover { background: rgba(255, 255, 255, 0.08); color: var(--fg, #f0f0f0); }

  .onboard-body {
    padding: 24px 20px;
    overflow-y: auto;
    flex: 1;
  }
  .onboard-step { text-align: center; }
  .onboard-illustration { display: flex; justify-content: center; margin-bottom: 12px; }
  .onboard-title, .onboard-h2 {
    font-size: 1.4em;
    margin: 0 0 12px;
    color: var(--fg, #f0f0f0);
  }
  .onboard-lede {
    color: var(--fg-muted, #aaa);
    line-height: 1.6;
    margin: 0 0 12px;
  }
  .onboard-hint {
    color: var(--fg-muted, #aaa);
    line-height: 1.5;
    margin: 0 0 12px;
  }
  .onboard-meta {
    font-size: 0.85em;
    color: var(--fg-muted, #888);
    margin: 0 0 16px;
  }
  .onboard-field { margin: 12px 0; }
  .onboard-field input[type="text"] {
    width: 100%;
    padding: 10px 12px;
    border: 1px solid var(--border, rgba(255, 255, 255, 0.15));
    border-radius: 8px;
    background: var(--input-bg, rgba(0, 0, 0, 0.2));
    color: var(--fg, #f0f0f0);
    font: inherit;
    box-sizing: border-box;
  }
  .onboard-field input:focus { outline: 2px solid var(--accent); }

  .onboard-choices {
    display: flex;
    flex-direction: column;
    gap: 8px;
    text-align: left;
  }
  .onboard-choice {
    display: flex;
    align-items: center;
    gap: 10px;
    padding: 10px 12px;
    border: 1px solid var(--border, rgba(255, 255, 255, 0.1));
    border-radius: 10px;
    cursor: pointer;
    transition: border-color 0.2s ease, background 0.2s ease;
  }
  .onboard-choice:hover { border-color: var(--accent); }
  .onboard-choice input { margin: 0; }

  .onboard-actions {
    display: flex;
    flex-direction: column;
    gap: 8px;
    margin-top: 16px;
  }
  .onboard-actions .btn { width: 100%; }
  @media (min-width: 480px) {
    .onboard-actions { flex-direction: row; }
    .onboard-actions .btn { flex: 1; }
  }

  .onboard-progress {
    display: flex;
    justify-content: center;
    gap: 6px;
    margin: 0 0 16px;
  }
  .onboard-pip {
    width: 24px;
    height: 4px;
    border-radius: 999px;
    background: var(--border, rgba(255, 255, 255, 0.1));
  }
  .onboard-pip.onboard-pip-on {
    background: var(--accent);
  }
  .onboard-check {
    display: flex;
    justify-content: center;
    color: #78c878;
    margin: 0 0 12px;
  }
  .onboard-flash {
    background: rgba(255, 180, 0, 0.1);
    border: 1px solid rgba(255, 180, 0, 0.3);
    color: var(--fg, #f0f0f0);
    padding: 8px 12px;
    border-radius: 8px;
    margin-top: 12px;
    text-align: left;
    font-size: 0.9em;
  }
  .onboard-footer {
    display: flex;
    justify-content: space-between;
    padding: 10px 20px;
    font-size: 0.8em;
    color: var(--fg-muted, #888);
    border-top: 1px solid var(--border, rgba(255, 255, 255, 0.08));
  }
  .onboard-footer a { color: var(--accent); text-decoration: none; }
</style>
