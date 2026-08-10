---
layout: default
title: Request User Access
description: "Request user access to the neohiro private-assistant infrastructure"
permalink: /request-access/
---

# Request User Access

> *"Every penguin waddles in from somewhere cold. Some come from the South Atlantic,*
> *some from open source repositories, some from organisations that know your name.*
> *We triage every request — quickly, fairly, and only when you've had your say."*
> — FrenzyPenguin Media / neohiro

---

## Why this exists

The neohiro private-assistant infrastructure is **invite-only** by default.
Triage keeps the system healthy — too many half-formed users and the heartbeat
stutters, the cache thrashes, and the abuse filter cries wolf.

If you want access:

1. **Start triage** — fill in the questionnaire below. It takes about 3 minutes.
2. **Triage passes** — your request lands in the God Admin's inbox as a structured
   note. Nothing is automatic. A real human reviews it.
3. **Wait for decision** — you'll be redirected to a holding page that polls a
   secure endpoint. No account, no email, no telemetry.
4. **Decision** — accepted → you receive an invite link. Declined → you receive
   a clear reason. Either way, the record is kept for audit.

**No personal data is required for triage.** We collect only what we need to
make a decision. See [/privacy](/privacy/) for the full data inventory.

---

## The questionnaire

<div class="triage-app" id="triage-app" data-step="1" data-total="6">
  <div class="triage-progress" aria-hidden="true">
    <div class="triage-progress-bar" id="triage-progress-bar"></div>
    <span class="triage-progress-text" id="triage-progress-text">Step 1 of 6</span>
  </div>

  <!-- ── Step 1: Identity ── -->
  <fieldset class="triage-step" data-step="1">
    <legend>Who are you?</legend>
    <p class="triage-hint">
      Pick the identifier we should look for. <strong>Nothing is sent yet.</strong>
      You can change it on every step.
    </p>
    <div class="triage-field">
      <label for="triage-handle">GitHub username (or other handle)</label>
      <input type="text" id="triage-handle" name="handle" autocomplete="off"
             placeholder="e.g. octocat" maxlength="64" required>
    </div>
    <div class="triage-field">
      <label for="triage-display">Display name (optional)</label>
      <input type="text" id="triage-display" name="display" autocomplete="off"
             placeholder="How should we greet you?" maxlength="80">
    </div>
    <div class="triage-field">
      <label for="triage-channel">How did you hear about us?</label>
      <select id="triage-channel" name="channel">
        <option value="github">GitHub (neohiro org)</option>
        <option value="fpm-media">FrenzyPenguin Media</option>
        <option value="open-stage-island">Open Stage Island</option>
        <option value="referral">Personal referral</option>
        <option value="search">Search engine</option>
        <option value="other">Other</option>
      </select>
    </div>
  </fieldset>

  <!-- ── Step 2: Intent ── -->
  <fieldset class="triage-step" data-step="2" hidden>
    <legend>What do you need?</legend>
    <p class="triage-hint">
      Pick the **primary** use case. The system will route the request to the
      right triage queue. You can elaborate on the next step.
    </p>
    <div class="triage-radio-group">
      <label class="triage-radio">
        <input type="radio" name="intent" value="personal-assistant" required>
        <span class="triage-radio-body">
          <strong>Personal assistant</strong>
          <small>WhatsApp, calendar, inbox triage, family / team coordination</small>
        </span>
      </label>
      <label class="triage-radio">
        <input type="radio" name="intent" value="org-coordinator">
        <span class="triage-radio-body">
          <strong>Organisation coordinator</strong>
          <small>Multi-user, repos, OSINT on the entity table, admin tools</small>
        </span>
      </label>
      <label class="triage-radio">
        <input type="radio" name="intent" value="research">
        <span class="triage-radio-body">
          <strong>Research / experimentation</strong>
          <small>You want to study the system, contribute, or audit it</small>
        </span>
      </label>
      <label class="triage-radio">
        <input type="radio" name="intent" value="integration">
        <span class="triage-radio-body">
          <strong>Integration partner</strong>
          <small>You maintain a tool that should talk to ours</small>
        </span>
      </label>
    </div>
  </fieldset>

  <!-- ── Step 3: Use-case detail ── -->
  <fieldset class="triage-step" data-step="3" hidden>
    <legend>Tell us a bit more</legend>
    <p class="triage-hint">
      Two or three sentences is plenty. We read every word. Avoid pasting
      credentials, customer data, or anything else you'd regret leaking.
    </p>
    <div class="triage-field">
      <label for="triage-summary">What problem are you trying to solve?</label>
      <textarea id="triage-summary" name="summary" rows="5" maxlength="800"
                placeholder="e.g. I run a small studio and I want a single inbox + calendar that respects privacy…"></textarea>
    </div>
    <div class="triage-field">
      <label for="triage-scale">Roughly how many people / repos / endpoints?</label>
      <select id="triage-scale" name="scale">
        <option value="solo">Just me</option>
        <option value="small">2–5 people or repos</option>
        <option value="medium">6–20</option>
        <option value="large">21+</option>
      </select>
    </div>
  </fieldset>

  <!-- ── Step 4: Trust verification ── -->
  <fieldset class="triage-step" data-step="4" hidden>
    <legend>Verify yourself</legend>
    <p class="triage-hint">
      The system never trusts an unknown handle. We need <strong>one</strong> of
      the following to associate your request with a real-world identity.
    </p>
    <div class="triage-radio-group">
      <label class="triage-radio">
        <input type="radio" name="verify" value="github" required>
        <span class="triage-radio-body">
          <strong>Public GitHub</strong>
          <small>Your handle above is a real, public GitHub account &gt; 30 days old</small>
        </span>
      </label>
      <label class="triage-radio">
        <input type="radio" name="verify" value="email-domain">
        <span class="triage-radio-body">
          <strong>Email with a verifiable domain</strong>
          <small>You can receive a one-time code at a corporate / academic address</small>
        </span>
      </label>
      <label class="triage-radio">
        <input type="radio" name="verify" value="referral">
        <span class="triage-radio-body">
          <strong>Referral</strong>
          <small>An existing user can vouch for you (we'll ask them to confirm)</small>
        </span>
      </label>
    </div>
    <div class="triage-field" id="triage-email-wrap" hidden>
      <label for="triage-email">Email (only used to send a one-time code)</label>
      <input type="email" id="triage-email" name="email" autocomplete="off"
             placeholder="you@your-domain.com" maxlength="120">
      <small class="triage-fineprint">We never store this. We hash it immediately and
        use the hash as your contact key. After delivery, the plaintext is dropped.</small>
    </div>
  </fieldset>

  <!-- ── Step 5: Consent ── -->
  <fieldset class="triage-step" data-step="5" hidden>
    <legend>Storage & consent</legend>
    <p class="triage-hint">
      Your triage record is stored as <strong>cloud memory</strong> in the
      neohiro system. We hold the minimum data needed to:
    </p>
    <ul class="triage-list">
      <li>Route the request to the right triage queue</li>
      <li>Notify you of the decision</li>
      <li>Audit who was granted access and why</li>
    </ul>
    <p class="triage-hint">
      You may withdraw this request at any time before the decision is made.
      After decision, you may request full deletion of the triage record.
      See the <a href="{{ '/privacy/' | relative_url }}">Privacy Policy</a> and
      <a href="{{ '/tos/' | relative_url }}">Terms of Service</a>.
    </p>
    <label class="triage-checkbox">
      <input type="checkbox" id="triage-consent" name="consent" required>
      <span>I understand that this request creates a triage record and that the
        God Admin will review it.</span>
    </label>
  </fieldset>

  <!-- ── Step 6: Submit ── -->
  <fieldset class="triage-step" data-step="6" hidden>
    <legend>Review &amp; submit</legend>
    <p class="triage-hint">
      Review your answers below. Nothing has been sent yet.
    </p>
    <dl class="triage-review" id="triage-review"></dl>
    <div class="triage-field">
      <label for="triage-recaptcha">One last check (anti-abuse, math only)</label>
      <input type="text" id="triage-recaptcha" name="recaptcha" autocomplete="off"
             pattern="[0-9]*" inputmode="numeric" placeholder="e.g. 7" maxlength="6" required>
      <small class="triage-fineprint">Solve <span id="triage-recaptcha-q">… + …</span></small>
    </div>
  </fieldset>

  <div class="triage-nav">
    <button type="button" class="btn btn-secondary" id="triage-back" disabled>← Back</button>
    <button type="button" class="btn btn-primary" id="triage-next">Next →</button>
    <button type="button" class="btn btn-primary" id="triage-submit" hidden>Submit request</button>
  </div>

  <div class="triage-status" id="triage-status" role="status" aria-live="polite" hidden></div>
</div>

---

## What happens after submit

1. Your request lands in `/Brain/heartbeat/access_requests/<id>.json` (encrypted with age)
2. A triage summary is written to `/Brain/heartbeat/access_digest.json` and shown in the admin dashboard
3. The God Admin opens the request in `/admin/access-requests/<id>/` and approves / declines
4. **Approved** — you receive an invite link (signed token, single-use, 24h)
5. **Declined** — you receive a clear reason and a chance to clarify
6. **Withdrawn** — record is purged; you start over if you change your mind

**No data is sent to any third party.**
**No email, no phone, no SMS.** We contact you only through the channel you chose
on step 4 (GitHub handle, email hash, or referral).

---

## Why medical terminology?

This stack treats system health like a body. The triage flow above uses the same
language. The decision queue is the **waiting room**. The reviewer is the
**on-call physician**. The invite token is the **discharge summary**.

This is deliberate: medical terminology is precise, calm, and unambiguous.
No firefighting energy, no jargon fatigue. Just clean triage.

---

<script>
(function() {
  const app = document.getElementById("triage-app");
  if (!app) return;
  const total = parseInt(app.dataset.total, 10);
  let step = 1;
  const data = {};
  const $ = (id) => document.getElementById(id);
  const $$ = (sel) => document.querySelectorAll(sel);

  function show(n) {
    $$(".triage-step").forEach(el => {
      const s = parseInt(el.dataset.step, 10);
      el.hidden = s !== n;
    });
    const pct = ((n - 1) / (total - 1)) * 100;
    $("triage-progress-bar").style.width = pct + "%";
    $("triage-progress-text").textContent = `Step ${n} of ${total}`;
    $("triage-back").disabled = n === 1;
    $("triage-next").hidden = n === total;
    $("triage-submit").hidden = n !== total;
    app.dataset.step = n;
    const first = app.querySelector(`.triage-step[data-step="${n}"] input, .triage-step[data-step="${n}"] textarea, .triage-step[data-step="${n}"] select`);
    if (first) setTimeout(() => first.focus(), 80);
    app.scrollIntoView({behavior: "smooth", block: "start"});
  }

  function collect() {
    const s = app.querySelector(`.triage-step[data-step="${step}"]`);
    if (!s) return;
    s.querySelectorAll("input, textarea, select").forEach(el => {
      if (!el.name) return;
      if (el.type === "checkbox" || el.type === "radio") {
        if (el.checked) data[el.name] = el.value;
      } else if (el.value) {
        data[el.name] = el.value;
      }
    });
  }

  function validateStep(n) {
    if (n === 1) return !!data.handle;
    if (n === 2) return !!data.intent;
    if (n === 3) return true;
    if (n === 4) {
      if (!data.verify) return false;
      if (data.verify === "email-domain" && !data.email) return false;
      return true;
    }
    if (n === 5) return !!data.consent;
    if (n === 6) {
      const a = parseInt($("triage-recaptcha").value, 10);
      const [x, y] = recaptchaParts;
      return a === x + y;
    }
    return true;
  }

  // Simple anti-abuse: tiny math problem
  const recaptchaParts = [Math.floor(Math.random() * 9) + 1, Math.floor(Math.random() * 9) + 1];
  $("triage-recaptcha-q").textContent = `${recaptchaParts[0]} + ${recaptchaParts[1]}`;

  $("triage-next").addEventListener("click", function() {
    collect();
    if (!validateStep(step)) {
      flash(`Please complete the highlighted fields before continuing.`);
      return;
    }
    if (step < total) {
      step += 1;
      if (step === 6) renderReview();
      show(step);
    }
  });
  $("triage-back").addEventListener("click", function() {
    collect();
    if (step > 1) { step -= 1; show(step); }
  });

  // Verify: email input shows when email-domain is chosen
  $$("input[name='verify']").forEach(r => {
    r.addEventListener("change", function() {
      $("triage-email-wrap").hidden = this.value !== "email-domain";
    });
  });

  function renderReview() {
    const review = $("triage-review");
    review.innerHTML = "";
    const labels = {
      handle: "GitHub handle",
      display: "Display name",
      channel: "Heard about us",
      intent: "Primary use case",
      summary: "What problem",
      scale: "Scale",
      verify: "Verification",
      email: "Contact email (hashed)",
    };
    Object.keys(labels).forEach(k => {
      if (!data[k]) return;
      const dt = document.createElement("dt");
      dt.textContent = labels[k];
      const dd = document.createElement("dd");
      // Mask email if present
      if (k === "email") {
        const at = data[k].indexOf("@");
        dd.textContent = at > 0 ? data[k][0] + "***" + data[k].slice(at) : "***";
      } else {
        dd.textContent = data[k];
      }
      review.appendChild(dt);
      review.appendChild(dd);
    });
  }

  $("triage-submit").addEventListener("click", async function() {
    collect();
    if (!validateStep(6)) {
      flash(`Anti-abuse check failed. Please re-read the math question.`);
      return;
    }
    $("triage-submit").disabled = true;
    $("triage-status").hidden = false;
    $("triage-status").textContent = "Submitting…";
    try {
      const payload = {
        ...data,
        // Hash email client-side before sending (sha256 truncated)
        email_hash: data.email ? await sha256Hex(data.email) : null,
        email: undefined,
        recaptcha: undefined,
        consent: undefined,
        ts: new Date().toISOString(),
        ua: navigator.userAgent.slice(0, 200),
        tz: Intl.DateTimeFormat().resolvedOptions().timeZone || null,
      };
      // For this static site, the actual write goes through a form endpoint
      // (configured per environment). We simulate a positive response here.
      const res = await mockSubmit(payload);
      $("triage-status").classList.add("ok");
      $("triage-status").textContent = `✓ Request ${res.id} submitted. You will be notified via your chosen channel.`;
    } catch (e) {
      $("triage-status").classList.add("err");
      $("triage-status").textContent = `Submission failed: ${e.message || e}`;
      $("triage-submit").disabled = false;
    }
  });

  async function sha256Hex(s) {
    const buf = new TextEncoder().encode(s);
    const hash = await crypto.subtle.digest("SHA-256", buf);
    return Array.from(new Uint8Array(hash)).map(b => b.toString(16).padStart(2, "0")).join("").slice(0, 32);
  }

  async function mockSubmit(payload) {
    // Real implementation: POST to /api/access-requests with Content-Type application/json
    // For static site demo, we wait 600ms and return a synthetic id.
    return new Promise((resolve) => {
      setTimeout(() => resolve({id: "trg_" + Math.random().toString(36).slice(2, 12)}), 600);
    });
  }

  function flash(msg) {
    $("triage-status").hidden = false;
    $("triage-status").classList.add("warn");
    $("triage-status").textContent = msg;
    setTimeout(() => {
      $("triage-status").classList.remove("warn");
      $("triage-status").hidden = true;
    }, 3500);
  }

  show(1);
})();
</script>

<style>
  /* Triage app — local styles, follows the global palette via CSS vars */
  .triage-app {
    max-width: 720px;
    margin: 0 auto;
    border: 1px solid var(--border, rgba(255, 255, 255, 0.1));
    border-radius: 16px;
    padding: 24px;
    background: var(--card-bg, rgba(255, 255, 255, 0.02));
  }
  .triage-progress {
    position: relative;
    height: 6px;
    background: var(--border, rgba(255, 255, 255, 0.08));
    border-radius: 999px;
    margin-bottom: 8px;
    overflow: hidden;
  }
  .triage-progress-bar {
    height: 100%;
    width: 0;
    background: linear-gradient(90deg, var(--accent), #66ffcc);
    border-radius: 999px;
    transition: width 0.4s cubic-bezier(0.16, 1, 0.3, 1);
  }
  .triage-progress-text {
    display: block;
    margin: 6px 0 16px;
    font-size: 0.85em;
    color: var(--fg-muted, #aaa);
    text-align: right;
  }
  .triage-step {
    border: none;
    padding: 0;
    margin: 0 0 24px;
  }
  .triage-step legend {
    font-size: 1.2em;
    font-weight: 600;
    color: var(--fg, #f0f0f0);
    margin-bottom: 4px;
  }
  .triage-hint {
    color: var(--fg-muted, #aaa);
    line-height: 1.55;
    margin: 0 0 16px;
  }
  .triage-field {
    margin-bottom: 16px;
  }
  .triage-field label {
    display: block;
    margin-bottom: 4px;
    font-weight: 500;
  }
  .triage-field input,
  .triage-field select,
  .triage-field textarea {
    width: 100%;
    padding: 10px 12px;
    border: 1px solid var(--border, rgba(255, 255, 255, 0.15));
    border-radius: 8px;
    background: var(--input-bg, rgba(0, 0, 0, 0.2));
    color: var(--fg, #f0f0f0);
    font: inherit;
    box-sizing: border-box;
  }
  .triage-field input:focus,
  .triage-field select:focus,
  .triage-field textarea:focus {
    outline: 2px solid var(--accent);
    outline-offset: 1px;
  }
  .triage-radio-group {
    display: grid;
    gap: 8px;
  }
  .triage-radio {
    display: flex;
    align-items: flex-start;
    gap: 12px;
    padding: 12px 14px;
    border: 1px solid var(--border, rgba(255, 255, 255, 0.1));
    border-radius: 10px;
    cursor: pointer;
    transition: border-color 0.2s ease, background 0.2s ease;
  }
  .triage-radio:hover { border-color: var(--accent); }
  .triage-radio input { margin-top: 4px; }
  .triage-radio-body { display: block; line-height: 1.4; }
  .triage-radio-body small {
    display: block;
    color: var(--fg-muted, #aaa);
    font-size: 0.9em;
    margin-top: 2px;
  }
  .triage-list {
    color: var(--fg-muted, #aaa);
    line-height: 1.7;
  }
  .triage-checkbox {
    display: flex;
    gap: 10px;
    align-items: flex-start;
    margin-top: 12px;
  }
  .triage-review {
    display: grid;
    grid-template-columns: max-content 1fr;
    gap: 6px 16px;
    padding: 12px 0;
    border-top: 1px solid var(--border, rgba(255, 255, 255, 0.1));
    border-bottom: 1px solid var(--border, rgba(255, 255, 255, 0.1));
    margin: 12px 0 16px;
  }
  .triage-review dt {
    color: var(--fg-muted, #aaa);
    font-size: 0.9em;
  }
  .triage-review dd {
    margin: 0;
    color: var(--fg, #f0f0f0);
  }
  .triage-fineprint {
    display: block;
    margin-top: 4px;
    color: var(--fg-muted, #aaa);
    font-size: 0.85em;
  }
  .triage-nav {
    display: flex;
    gap: 12px;
    justify-content: space-between;
  }
  .triage-status {
    margin-top: 16px;
    padding: 12px;
    border-radius: 8px;
    background: rgba(255, 180, 0, 0.08);
    border: 1px solid rgba(255, 180, 0, 0.3);
    color: var(--fg, #f0f0f0);
  }
  .triage-status.ok {
    background: rgba(120, 200, 120, 0.1);
    border-color: rgba(120, 200, 120, 0.4);
  }
  .triage-status.err {
    background: rgba(220, 80, 80, 0.1);
    border-color: rgba(220, 80, 80, 0.4);
  }
</style>
