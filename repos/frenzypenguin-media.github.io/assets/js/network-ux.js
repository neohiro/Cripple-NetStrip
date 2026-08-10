/* ─────────────────────────────────────────────────────────────────────
 * neohiro-network :: Universal cross-site UX module
 *   - AI assistant input bar (fixed to the bottom edge, occupies the dock slot)
 *   - Conversation sheet (screenwide, slides up behind the dock)
 *   - Voicemail triage (durable queue via brain-bridge — see
 *     network/brain_bridge/README.md)
 *   - Previous-button (cross-domain navigation back to last visited site)
 *   - Top-nav auth slot (static markup in nav.html; this only syncs state)
 *   - Starfield parallax background
 *   - Heart/Mouth heartbeat detection (API fetch with local classify fallback)
 *   - Stranger tracking (localStorage + neohiro:stranger event)
 *
 * Loaded by every site in the neohiro network. Self-contained.
 * ───────────────────────────────────────────────────────────────────── */
(function () {
  'use strict';

  var NEohiro = {
    NETWORK: ['neohiro.github.io', 'frenzypenguin-media.github.io', 'transhumanists.github.io', 'openstageisland.github.io'],
    PREV_KEY: 'neohiro.prev.v1',
    init: init
  };

  var _booted = false;

  function init() {
    if (_booted) return;
    _booted = true;
    if (document.readyState === 'loading') {
      document.addEventListener('DOMContentLoaded', boot, { once: true });
    } else {
      boot();
    }
  }

  /* Each step is isolated on purpose. boot() used to be a bare sequence, so a
     throw in the first step (mountStarfield) silently skipped every step after
     it -- including mountConversationModal and wireAITriggers, which is how
     this whole module ended up shipped but dead on all four sites: init() was
     never called at all, and nothing reported it. Cosmetic decoration must not
     be able to take the assistant offline, so a failing step is logged and the
     rest still run. */
  function boot() {
    var steps = [
      ['mountStarfield', mountStarfield],
      ['mountPreviousButton', mountPreviousButton],
      ['mountConversationModal', mountConversationModal],
      ['recordCurrentPage', recordCurrent],
      ['fillAvatarSlots', function () { fillAvatarSlots(document.body); }],
      ['injectNavAuth', injectNavAuth],
      ['wireAITriggers', wireAITriggers],
      ['detectStranger', detectStranger],
      ['wireInteractions', wireInteractions],
      ['runDiagnostics', runDiagnostics]
    ];
    for (var i = 0; i < steps.length; i++) {
      try {
        steps[i][1]();
      } catch (err) {
        if (window.console && console.warn) {
          console.warn('[neohiro-network] boot step "' + steps[i][0] +
            '" failed; continuing with the remaining steps.', err);
        }
      }
    }
  }

  /* ── AI Conversation triggers — unified delegated handler ─────────────────
     Any element matching AI_TRIGGER_SELECTOR opens the conversation sheet, so
     adding a trigger is a markup change (`data-ai-trigger`) and not a second
     listener. Per-site overrides via window.AI_CONV_CONFIG (optional):
       {
         triggers:  '[data-ai-trigger], #ai-dock__tab--ai', // CSS selector list
         onOpen:    function () {},  // after the sheet opens
         onClose:   function () {},  // after the sheet closes
         closeOnEsc: true,
         closeOnOverlayClick: true
       }
     Falls back to AI_TRIGGER_SELECTOR if the config is absent or unusable. */
  var AI_TRIGGER_SELECTOR = '[data-ai-trigger], #ai-dock__tab--ai';

  function wireAITriggers() {
    var cfg = (window.AI_CONV_CONFIG || {});
    var onOpen = typeof cfg.onOpen === 'function' ? cfg.onOpen : function () {};
    var onClose = typeof cfg.onClose === 'function' ? cfg.onClose : function () {};

    /* closest() accepts a selector LIST (verified in Chrome: '#a, #c' matches
       through the chain) but THROWS SyntaxError on a malformed one. That throw
       matters: this runs during module init, so a typo in a per-site
       `triggers` value would abort every later init step, not just the
       conversation. Validate once, loudly enough to be debuggable, then fall
       back to the default rather than taking the page down. */
    var selector = AI_TRIGGER_SELECTOR;
    if (cfg.triggers) {
      try {
        document.querySelector(cfg.triggers);
        selector = cfg.triggers;
      } catch (e) {
        if (window.console && console.warn) {
          console.warn('[ai-conv] AI_CONV_CONFIG.triggers is not a valid CSS ' +
            'selector; falling back to the default. Offending value:', cfg.triggers, e);
        }
      }
    }

    /* e.target is an Element for the click events this handles, but a text
       node has no closest(). One guard rather than a try/catch per listener. */
    function hit(el) {
      return !!(el && typeof el.closest === 'function' && el.closest(selector));
    }

    function openConv() {
      if (window.AuthBar && typeof window.AuthBar.selectTab === 'function') {
        window.AuthBar.selectTab(null);
      }
      if (isConvOpen()) { hideConversationModal(); return; }
      showConversationModal();
      onOpen();
    }

    function closeConv() {
      hideConversationModal();
      onClose();
    }

    /* Single delegated click handler, bound on the document, so it also sees
       triggers added to the DOM after load (the auth slot is populated by a
       fetch and rewrites the nav). */
    document.addEventListener('click', function (e) {
      if (hit(e.target)) {
        // Only swallow the default for real controls. A trigger that happens
        // to be an <a> without its own handler should still be able to
        // navigate; this handler owns the button case.
        if (e.target.closest('button, a')) e.preventDefault();
        openConv();
        return;
      }
      if (cfg.closeOnOverlayClick === false) return;
      if (!isConvOpen()) return;
      var modal = document.getElementById('ai-conv');
      if (!modal) return;
      var chrome = modal.querySelector('.ai-conv__chrome');
      // Click landed on the sheet's own gutter, not its content: dismiss.
      if (chrome && !chrome.contains(e.target)) closeConv();
    });

    if (cfg.closeOnEsc !== false) {
      document.addEventListener('keydown', function (e) {
        if (e.key === 'Escape' && isConvOpen()) closeConv();
      });
    }

    // Legacy flag for CSS stacking
    if (document.getElementById('ai-dock')) {
      document.body.classList.add('ai-dock-present');
    }
  }

  /* ── Universal interaction wiring (ripples, tilt, reveal) ─── */
  function wireInteractions() {
    // Click ripple on any element with [data-ripple] or .btn-primary, .btn-secondary, .btn
    document.addEventListener('click', function (e) {
      const target = e.target.closest('[data-ripple], .btn-primary, .btn-secondary, .btn-themed, .cta-button, .cta-themed, .nav-link, .glide-card, .ai-conv__send, .tool-card, .guide-card, .community-card, .fpm-spotlight, .milestone-card, .feed-item');
      if (!target) return;
      const rect = target.getBoundingClientRect();
      if (rect.width === 0) return;
      const ripple = document.createElement('span');
      ripple.className = 'click-ripple';
      const size = Math.max(rect.width, rect.height) * 1.3;
      ripple.style.width = ripple.style.height = size + 'px';
      ripple.style.left = (e.clientX - rect.left - size / 2) + 'px';
      ripple.style.top = (e.clientY - rect.top - size / 2) + 'px';
      // Make sure target is positioned — avoid getComputedStyle (forces layout)
      // Check inline style first; only fall back to computed if needed.
      if (!target.style.position || target.style.position === 'static') {
        target.style.position = 'relative';
      }
      target.appendChild(ripple);
      setTimeout(() => ripple.remove(), 700);
    });

    // Card 3D tilt on .card-3d
    document.querySelectorAll('.card-3d').forEach(card => {
      card.addEventListener('mousemove', e => {
        const r = card.getBoundingClientRect();
        const x = (e.clientX - r.left) / r.width - 0.5;
        const y = (e.clientY - r.top) / r.height - 0.5;
        card.style.setProperty('--mx', (x * 12) + 'px');
        card.style.setProperty('--my', (y * 12) + 'px');
      });
      card.addEventListener('mouseleave', () => {
        card.style.setProperty('--mx', '0px');
        card.style.setProperty('--my', '0px');
      });
    });

    /* Reveal-on-scroll.
       The class this adds MUST be `is-revealed`, not `reveal-in`.
       assets/css/main.css keys the whole effect off
       `.reveal-ready <selector> { opacity: 0 }` and `.reveal-ready .is-revealed
       { opacity: 1 }`. This block used to add `reveal-in`, a name no
       stylesheet matches, so every element it marked was set to opacity 0 by the
       gate and nothing ever took it back to 1. On this site that silently
       emptied the "All Milestones Cataloged" grid: twelve .milestone-card nodes
       present in the DOM, all at opacity 0.

       Two safeguards, because "the animation must never be load-bearing for
       content being visible" is the rule main.css already states:
         - prefers-reduced-motion reveals everything immediately, no observer.
         - a failsafe timer reveals anything still hidden after 2.5s, so an
           observer that never fires (no IO, a zero-height ancestor, a headless
           run) degrades to "everything visible" instead of "blank page". */
    const auto = document.querySelectorAll('.section, .tool-card, .guide-card, .community-card, .milestone-card, .feature, .glide-card, .fpm-spotlight, .quote-card, .feature-card, .row-card, .step-card, .cta-card, .panel, .lesson-card, .ep-card, .ep-stream-card, .ep-tile, .post-card, .article-card, .commit-card, .metric-card');
    const reduce = window.matchMedia('(prefers-reduced-motion: reduce)').matches;
    const revealAll = () => auto.forEach(el => el.classList.add('is-revealed'));
    if (reduce || !('IntersectionObserver' in window)) {
      revealAll();
    } else {
      const io = new IntersectionObserver(entries => {
        entries.forEach(entry => {
          if (entry.isIntersecting) {
            entry.target.classList.add('is-revealed');
            io.unobserve(entry.target);
          }
        });
      }, { threshold: 0.08, rootMargin: '0px 0px -8% 0px' });
      auto.forEach(el => io.observe(el));
      // Failsafe: never leave content stranded at opacity 0.
      setTimeout(revealAll, 2500);
    }

    // Animated orbs: randomize positions slightly
    try {
      document.documentElement.style.setProperty('--orb1-x', (10 + Math.random() * 20) + '%');
      document.documentElement.style.setProperty('--orb1-y', (10 + Math.random() * 25) + '%');
      document.documentElement.style.setProperty('--orb2-x', (60 + Math.random() * 30) + '%');
      document.documentElement.style.setProperty('--orb2-y', (50 + Math.random() * 35) + '%');
    } catch (_) {}
  }

  /* ── Starfield (parallax deep-space, 3 layers) ───────────── */
  function mountStarfield() {
    if (document.getElementById('starfield')) return;

    // Respect reduced-motion and skip on small screens for performance
    const reduceMotion = window.matchMedia('(prefers-reduced-motion: reduce)').matches;
    const isMobile = window.innerWidth < 600;
    if (reduceMotion || isMobile) return;

    const s = document.createElement('div');
    s.id = 'starfield';
    s.className = 'starfield';
    s.setAttribute('aria-hidden', 'true');
    document.body.appendChild(s);

    // Parallax on scroll: shift the starfield at half speed
    let raf = 0;
    const onScroll = () => {
      if (raf) return;
      raf = requestAnimationFrame(() => {
        s.style.setProperty('--sy', (window.scrollY * 0.4) + 'px');
        raf = 0;
      });
    };
    window.addEventListener('scroll', onScroll, { passive: true });

    // Mouse parallax: rAF-throttled to avoid 100+ writes/sec on hi-DPI
    // trackpads. setProperty on a CSS custom property only invalidates
    // a style subtree, but coalescing to one frame is still ~5x cheaper.
    var mouseRaf = 0;
    var mouseX = 0, mouseY = 0;
    document.addEventListener('mousemove', function (e) {
      mouseX = e.clientX;
      mouseY = e.clientY;
      if (mouseRaf) return;
      mouseRaf = requestAnimationFrame(function () {
        mouseRaf = 0;
        s.style.setProperty('--mx', ((mouseX / window.innerWidth - 0.5) * 16) + 'px');
        s.style.setProperty('--my', ((mouseY / window.innerHeight - 0.5) * 16) + 'px');
      });
    });

    // Third ambient orb (pinky) — additive
    if (!document.querySelector('.ambient-orb')) {
      const orb = document.createElement('div');
      orb.className = 'ambient-orb';
      orb.setAttribute('aria-hidden', 'true');
      document.body.appendChild(orb);
    }
  }

  /* ── Cross-domain Previous button ─────────────────────────────── */
  function mountPreviousButton() {
    if (sessionStorage.getItem('neohiro.prev.skip') === '1') return;
    const last = readLast();
    if (!last) return;
    if (last.url === location.href) return;
    if (hostOf(last.url) === location.hostname) {
      // Same-origin: native back is more useful than this button.
      return;
    }

    const btn = document.createElement('a');
    btn.className = 'prev-btn';
    btn.href = last.url;
    btn.setAttribute('aria-label', `Back to ${last.label}`);
    btn.innerHTML = `
      <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.2" width="14" height="14" aria-hidden="true">
        <path d="M15 18l-6-6 6-6"/>
      </svg>
      <span class="prev-label">Back to ${escapeHtml(last.label)}</span>
      <span class="prev-host" aria-hidden="true">${escapeHtml(hostOf(last.url))}</span>
    `;
    btn.addEventListener('click', () => sessionStorage.setItem('neohiro.prev.skip', '1'));
    document.body.appendChild(btn);
  }

  function recordCurrent() {
    try {
      const existing = readLast();
      if (existing && existing.url === location.href) return; // already recorded
      sessionStorage.setItem(NEohiro.PREV_KEY, JSON.stringify({
        url: location.href,
        label: labelFor(location.hostname),
        ts: Date.now()
      }));
    } catch (_) {}
  }
  function readLast() {
    try {
      const raw = sessionStorage.getItem(NEohiro.PREV_KEY);
      if (!raw) return null;
      const v = JSON.parse(raw);
      if (!v || !v.url) return null;
      if (Date.now() - v.ts > 12 * 3600 * 1000) return null;
      return v;
    } catch (_) { return null; }
  }
  function hostOf(url) { try { return new URL(url).hostname; } catch (_) { return ''; } }
  /* Display name for a host, used by the cross-site "Back to ..." control.
   *
   * Strip one leading "www." and lower-case before matching.
   *
   * The apex of the media site is served both as frenzypenguin.media and as
   * www.frenzypenguin.media, and the github.io form is a third shape. Matching
   * on the "frenzypenguin" prefix covers all three, so the custom domain cannot
   * end up labelled "neohiro" -- the wrong name, on the one host a visitor is
   * most likely to have typed or been sent to.
   *
   * Exactly one "www." is removed, so www.www.example.com cannot be made to
   * look like www.example.com.
   *
   * Known limitation, pre-existing and deliberately unchanged: the prefixes are
   * substring matches, so a lookalike host such as "frenzypenguin-attacker.com"
   * also resolves to this site's label. That is cosmetic rather than a spoofing
   * hole -- this function only chooses which name to display; the link it labels
   * is built elsewhere. Tightening it is not a one-liner, because the
   * legitimate hostnames here have two different shapes ("frenzypenguin.media"
   * and "frenzypenguin-media.github.io") and a plain hostname-boundary match
   * would reject the second.
   */
  function labelFor(host) {
    if (!host) return "Unknown";
    var h = String(host).toLowerCase().replace(/^www\./, "");
    if (h.indexOf("transhumanists") === 0) return "transhumanists";
    if (h.indexOf("frenzypenguin") === 0)   return "FrenzyPenguin Media";
    if (h.indexOf("openstageisland") === 0) return "Open Stage Island";
    return "neohiro";
  }
  function escapeHtml(s) {
    return String(s).replace(/[&<>"']/g, c => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
  }

  /* ── Org avatar (site identity) ───────────────────────────────────
   * Every site in the neohiro network shows its own avatar in the
   * assistant conversation and the AI dock. The self-hosted profile.png
   * is preferred where it exists (neohiro/frenzypenguin enforce
   * `img-src 'self'`), otherwise the GitHub org avatar URL is used
   * (transhumanists/openstageisland allow https:). */
  var SITE_AVATAR = (function () {
    var host = (location.hostname || '').toLowerCase();
    // Exact hostname match to prevent subdomain spoofing (e.g. frenzypenguin-attacker.com)
    var exact = {
      'neohiro.github.io':           '/assets/profile.png',
      'frenzypenguin-media.github.io': '/assets/profile.png',
      'transhumanists.github.io':    'https://github.com/transhumanists.png',
      'openstageisland.github.io':   'https://github.com/openstageisland.png',
    };
    if (exact[host]) return exact[host];
    // Fallback: known subdomains of neohiro org
    if (host.endsWith('.neohiro.github.io') || host === 'neohiro.github.io') return '/assets/profile.png';
    return '/assets/profile.png';
  })();

  function buildAvatarImg(cls) {
    var img = document.createElement('img');
    img.className = cls || 'ai-avatar-img';
    img.src = SITE_AVATAR;
    img.alt = '';
    img.loading = 'lazy';
    img.decoding = 'async';
    img.setAttribute('aria-hidden', 'true');
    img.onerror = function () { if (img.parentNode) img.parentNode.removeChild(img); };
    return img;
  }

  // Injects the org avatar into every assistant avatar slot + the
  // conversation header brand. The slot's existing glyph (✦ / 🤖) stays
  // underneath as a graceful offline fallback: if the image errors out it
  // is removed and the glyph + tinted circle remain.
  function fillAvatarSlots(root) {
    if (!root || typeof root.querySelectorAll !== 'function') return;
    Array.prototype.forEach.call(root.querySelectorAll('.ai-conv__avatar, .ai-dock__chat-avatar'), function (slot) {
      if (!slot || slot.querySelector('img')) return;
      slot.appendChild(buildAvatarImg());
    });
    Array.prototype.forEach.call(root.querySelectorAll('.ai-conv__brand'), function (brand) {
      if (brand.querySelector('.ai-conv__brand-avatar')) return;
      brand.insertBefore(buildAvatarImg('ai-conv__brand-avatar ai-avatar-img'), brand.firstChild);
    });
  }

  function showToast(msg, duration) {
    if (document.getElementById('neohiro-toast')) return;
    var el = document.createElement('div');
    el.id = 'neohiro-toast';
    el.setAttribute('role', 'status');
    el.setAttribute('aria-live', 'polite');
    el.textContent = msg;
    Object.assign(el.style, {
      position: 'fixed', bottom: '120px', left: '50%', transform: 'translateX(-50%)',
      zIndex: '9999', padding: '10px 20px',
      background: 'var(--bg-elevated, #161e26)',
      border: '1px solid var(--accent, #7c4dff)',
      borderRadius: '999px', color: 'var(--fg, #eceff1)',
      fontFamily: 'var(--font-ui, system-ui, sans-serif)',
      fontSize: '0.85rem', fontWeight: '600',
      boxShadow: '0 8px 24px rgba(0,0,0,0.5)',
      pointerEvents: 'none', whiteSpace: 'nowrap',
      animation: 'neohiroToastIn 0.3s ease both'
    });
    document.body.appendChild(el);
    var ms = duration || 3000;
    var outTid = setTimeout(function () {
      el.style.animation = 'neohiroToastOut 0.3s ease both';
      setTimeout(function () { if (el.parentNode) el.remove(); }, 300);
    }, ms);
    // Cancel the timer if the page is hiding (back/forward cache, navigation)
    // so the queued work doesn't fire on a no-longer-attached element.
    var onHide = function () {
      clearTimeout(outTid);
      if (el.parentNode) el.remove();
    };
    window.addEventListener('pagehide', onHide, { once: true });
    document.addEventListener('visibilitychange', function () {
      if (document.visibilityState === 'hidden') onHide();
    }, { once: true });
  }

  /* ── Conversation modal (sway-down, bubbles, typing indicator) ── */
  // Built hidden on first AI-bar mount; activated on submit.
  // Animates down from the AI bar, displays the user's query as a bubble,
  // then a typing indicator while Heart/Mouth is queried for a reply.
  // Now includes inline prompt composer with wide query box, variable menus,
  // and dual checkmarks for sent messages.
  function mountConversationModal() {
    if (document.getElementById('ai-conv')) return;
    const modal = document.createElement('div');
    modal.className = 'ai-conv hidden';
    modal.id = 'ai-conv';
    modal.setAttribute('role', 'dialog');
    modal.setAttribute('aria-modal', 'false');
    modal.setAttribute('aria-label', 'Conversation with the neohiro assistant');
    modal.innerHTML = `
      <div class="ai-conv__chrome">
        <div class="ai-conv__header">
          <span class="ai-conv__brand">
            <span class="ai-conv__pulse" aria-hidden="true"></span>
            neohiro assistant
          </span>
          <span class="ai-conv__heart" id="ai-conv__heart" aria-live="polite" title="Heart status">
            <span class="ai-conv__heart-dot" aria-hidden="true"></span>
            <span id="ai-conv__heart-text">connecting…</span>
          </span>
          <button type="button" class="ai-conv__close" id="ai-conv__close" aria-label="Close conversation">
            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" width="18" height="18" aria-hidden="true">
              <path d="M6 6l12 12M18 6L6 18"/>
            </svg>
          </button>
        </div>
        <div class="ai-conv__messages" id="ai-conv__messages" role="log" aria-live="polite">
          <div class="ai-conv__msg ai-conv__msg--assistant">
            <div class="ai-conv__avatar" aria-hidden="true">✦</div>
            <div class="ai-conv__bubble">
              Hey — I'm the neohiro assistant. I run across all 4 network sites and
              learn more about what you ask, so I can route you faster next time.
            </div>
          </div>
        </div>
        <div class="ai-conv__typing hidden" id="ai-conv__typing" role="status" aria-live="polite">
          <div class="ai-conv__avatar" aria-hidden="true">✦</div>
          <div class="ai-conv__bubble ai-conv__bubble--typing">
            <span class="ai-conv__dots" aria-hidden="true"><span></span><span></span><span></span></span>
            <span id="ai-conv__typing-text">Mouth is composing your reply…</span>
          </div>
        </div>

        <!-- Inline prompt composer (replaces footer toggle flow) -->
        <div class="ai-conv__composer" id="ai-conv__composer">
          <form class="ai-conv__composer-form" id="ai-conv__composer-form" novalidate>
            <div class="ai-conv__input-wrap">
              <span class="ai-conv__input-icon" aria-hidden="true">
                <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" width="20" height="20">
                  <path d="M12 2L9 8l-6 1 4.5 4.5L6 20l6-3.5L18 20l-1.5-6.5L21 9l-6-1z"/>
                </svg>
              </span>
              <input
                type="text"
                id="ai-conv__input"
                class="ai-conv__input"
                name="q"
                placeholder="Ask anything — find a repo, report a bug, get a guide, or describe what you need…"
                aria-label="Ask the neohiro assistant"
                maxlength="600"
                autocomplete="off" />
              <button type="submit" class="ai-conv__send" id="ai-conv__send" aria-label="Send message">
                <span>Send</span>
                <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" width="14" height="14" aria-hidden="true">
                  <path d="M5 12h14M12 5l7 7-7 7"/>
                </svg>
              </button>
            </div>
            <div class="ai-conv__vars" id="ai-conv__vars" hidden>
              <label class="ai-conv__var-row" title="Model">
                <span class="ai-conv__var-label">Model</span>
                <select class="ai-conv__var-select" name="model" aria-label="Model">
                  <option value="low">Low — free-model routing</option>
                  <option value="high">High — higher reasoning models</option>
                </select>
              </label>
              <label class="ai-conv__var-row" title="Site scope">
                <span class="ai-conv__var-label">Scope</span>
                <select class="ai-conv__var-select" name="scope" aria-label="Site scope">
                  <option value="all">All sites</option>
                  <option value="neohiro">neohiro</option>
                  <option value="fpm">frenzypenguin-media</option>
                  <option value="osi">openstageisland</option>
                  <option value="transhumanists">transhumanists</option>
                </select>
              </label>
              <label class="ai-conv__var-row" title="Reply mode">
                <span class="ai-conv__var-label">Reply mode</span>
                <select class="ai-conv__var-select" name="replyMode" aria-label="Reply mode">
                  <option value="assistant">Assistant</option>
                  <option value="voicemail">Human (voicemail)</option>
                </select>
              </label>
              <button type="button" class="ai-conv__vars-toggle" id="ai-conv__vars-toggle" aria-expanded="false" aria-controls="ai-conv__vars">
                <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" width="16" height="16" aria-hidden="true"><path d="M6 9l6 6 6-6"/></svg>
                <span class="ai-conv__vars-toggle-text">Variables</span>
              </button>
            </div>
            <div class="ai-conv__counter" id="ai-conv__counter" aria-live="off" aria-atomic="true">0 / 600</div>
          </form>
        </div>

        <!-- Voicemail triage. Two questions decide where a message ends up, so
           they are asked before the message itself. Hidden until requested, and
           it never blocks reading the conversation above it. -->
        <form class="ai-conv__triage hidden" id="ai-conv__triage" novalidate>
          <p class="ai-conv__triage-lede">
            This goes to a person, not the assistant. Two quick answers so it lands
            in the right place.
          </p>
          <label class="ai-conv__triage-row">
            <span>Who are you?</span>
            <span class="ai-conv__triage-pair">
              <input type="text" name="name" maxlength="120" placeholder="name" aria-label="Your name" autocomplete="name">
              <input type="text" name="contact" maxlength="200" placeholder="email or handle" aria-label="How to reply to you" autocomplete="email">
            </span>
          </label>
          <label class="ai-conv__triage-row">
            <span>What is it about?</span>
            <input type="text" name="about" maxlength="200" placeholder="a bug, access, docs, an idea…" aria-label="What this is about">
          </label>
          <label class="ai-conv__triage-row">
            <span>Message</span>
            <textarea name="message" rows="3" maxlength="4000" required
                      placeholder="Say it here. Nothing is stored in your browser."></textarea>
          </label>
          <div class="ai-conv__triage-actions">
            <button type="submit" class="ai-conv__triage-send" id="ai-conv__triage-send">Send</button>
            <span class="ai-conv__triage-status" id="ai-conv__triage-status" role="status" aria-live="polite"></span>
          </div>
        </form>
      </div>
    `;
    document.body.appendChild(modal);
    fillAvatarSlots(modal); // org avatar in conversation header + welcome bubble
    wireVoicemail(modal);
    wireComposer(modal);
    // Close handlers
    document.getElementById('ai-conv__close').addEventListener('click', hideConversationModal);
    // Esc to close (handler is page-singleton; no leak)
    document.addEventListener('keydown', (e) => {
      if (e.key === 'Escape' && isConvOpen()) hideConversationModal();
    });
    // Tab focus trap: keep focus inside the modal while open
    document.addEventListener('keydown', (e) => {
      if (e.key !== 'Tab' || !isConvOpen()) return;
      var focusables = modal.querySelectorAll(
        'a[href], button:not([disabled]), input:not([disabled]), [tabindex]:not([tabindex="-1"])'
      );
      if (focusables.length === 0) return;
      var first = focusables[0];
      var last = focusables[focusables.length - 1];
      if (e.shiftKey && document.activeElement === first) {
        e.preventDefault();
        last.focus();
      } else if (!e.shiftKey && document.activeElement === last) {
        e.preventDefault();
        first.focus();
      }
    });
    // Click outside the chrome closes the modal too
    modal.addEventListener('click', (e) => {
      if (e.target === modal) hideConversationModal();
    });
  }

  function isConvOpen() {
    const m = document.getElementById('ai-conv');
    return m && !m.classList.contains('hidden');
  }

  /* ── Voicemail triage wiring ────────────────────────────────────────────
     The point of this form is that a message is never lost. brain-bridge
     fsyncs before it acknowledges, so a "queued" receipt means it is on disk;
     on failure we say so plainly and leave the text in the box so the visitor
     can copy it rather than retype it. */
  function wireVoicemail(modal) {
    var toggle = modal.querySelector('#ai-conv__message-toggle');
    var form = modal.querySelector('#ai-conv__triage');
    if (!toggle || !form) return;

    toggle.addEventListener('click', function () {
      var open = form.classList.contains('hidden');
      form.classList.toggle('hidden', !open);
      toggle.setAttribute('aria-expanded', open ? 'true' : 'false');
      if (open) {
        var name = form.querySelector('[name="name"]');
        // Pre-fill from the GitHub session when there is one: signed-in visitors
        // should not have to identify themselves twice.
        var auth = currentAuth();
        if (auth && name && !name.value) name.placeholder = auth.login + ' (signed in)';
        if (name) name.focus();
      }
    });

    form.addEventListener('submit', function (e) {
      e.preventDefault();
      var status = form.querySelector('#ai-conv__triage-status');
      var send = form.querySelector('#ai-conv__triage-send');
      var field = function (n) {
        var el = form.querySelector('[name="' + n + '"]');
        return el ? String(el.value || '').trim() : '';
      };
      var message = field('message');
      if (!message) {
        status.textContent = 'Add a message first.';
        var box = form.querySelector('[name="message"]');
        if (box) box.focus();
        return;
      }

      var who = { name: field('name'), contact: field('contact') };
      var about = field('about');

      send.disabled = true;
      status.textContent = 'Sending…';

      sendVoicemail(message, who, about).then(function (res) {
        send.disabled = false;
        if (res.ok) {
          appendConvMessage('assistant',
            'Queued for a human' + (res.receipt ? ' — reference ' + res.receipt : '') +
            '. It is on disk now, so it will not be lost.');
          form.reset();
          form.classList.add('hidden');
          toggle.setAttribute('aria-expanded', 'false');
          status.textContent = '';
        } else {
          // Do not clear the box. The visitor keeps their words and can retry or
          // copy them out.
          status.textContent = 'Could not reach the inbox — your text is still here. Copy it and try again shortly.';
        }
      });
    });
  }

  /* ── Inline composer wiring ─────────────────────────────────────────── */
  function wireComposer(modal) {
    var form = modal.querySelector('#ai-conv__composer-form');
    var input = modal.querySelector('#ai-conv__input');
    var send = modal.querySelector('#ai-conv__send');
    var counter = modal.querySelector('#ai-conv__counter');
    var varsBox = modal.querySelector('#ai-conv__vars');
    var varsToggle = modal.querySelector('#ai-conv__vars-toggle');
    if (!form || !input || !send || !counter || !varsBox || !varsToggle) return;

    function updateCounter() {
      var n = input.value.length;
      counter.textContent = n + ' / 600';
      counter.classList.toggle('ai-conv__counter--near', n >= 540);
      counter.classList.toggle('ai-conv__counter--over', n > 600);
      form.classList.toggle('has-content', n > 0);
    }
    input.addEventListener('input', updateCounter);
    updateCounter();

    varsToggle.addEventListener('click', function () {
      var open = varsBox.hasAttribute('hidden');
      varsBox.hidden = !open;
      varsToggle.setAttribute('aria-expanded', open ? 'true' : 'false');
      if (open) varsToggle.querySelector('.ai-conv__vars-toggle-text').textContent = 'Hide variables';
      else varsToggle.querySelector('.ai-conv__vars-toggle-text').textContent = 'Variables';
    });

    form.addEventListener('submit', function (e) {
      e.preventDefault();
      var raw = input.value;
      var q = sanitizeQuery(raw);
      if (!q) { input.focus(); return; }
      if (q.length > 600) { input.value = q.slice(0, 600); input.focus(); return; }

      // Read variable menu selections (future: pass to backend)
      var modelSelect = form.querySelector('[name="model"]');
      var scopeSelect = form.querySelector('[name="scope"]');
      var replyModeSelect = form.querySelector('[name="replyMode"]');
      var composerOpts = {
        model: modelSelect ? modelSelect.value : 'low',
        scope: scopeSelect ? scopeSelect.value : 'all',
        replyMode: replyModeSelect ? replyModeSelect.value : 'assistant'
      };
      // Store for potential future use by fetchMouthReply/classify
      window.__aiComposerOpts = composerOpts;

      var wrap = document.getElementById('ai-bar');
      if (wrap) wrap.classList.add('ai-bar--sent');
      input.setAttribute('aria-busy', 'true');
      input.disabled = true;
      send.disabled = true;

      showConversationModal(input);
      appendConvMessage('user', q, true); // true = from composer
      input.value = '';
      updateCounter();

      probeHeart();

      const cycle = [
        'Mouth is reading your question…',
        'Triage: identifying who you are and what you need…',
        'Pulling the right repo / docs / step-by-step…',
        'Composing a helpful reply…'
      ];
      const myVer = ++_inFlightVer;
      let c = 0;
      setConvTyping(true, cycle[0]);
      _inFlightInt = setInterval(() => {
        if (myVer !== _inFlightVer) return;
        c = (c + 1) % cycle.length;
        setConvTyping(true, cycle[c]);
      }, 900);

      const delay = 1500 + Math.random() * 600;
      _inFlightTO = setTimeout(() => {
        _inFlightInt && clearInterval(_inFlightInt);
        _inFlightInt = null;
        _inFlightTO = null;
        if (myVer !== _inFlightVer) return;

        setConvTyping(false);
        const reply = fetchMouthReply(q, composerOpts)
          .then(mouthText => mouthText || classify(q))
          .catch(() => classify(q));

        reply.then(replyHtml => {
          if (myVer !== _inFlightVer) return;
          appendConvMessage('assistant', replyHtml);
          input.removeAttribute('aria-busy');
          input.disabled = false;
          send.disabled = false;
          if (wrap) wrap.classList.remove('ai-bar--sent');
          input.focus();
        });
      }, delay);
    });
  }

  var _prevFocus = null;
  var _closeTid = 0;

  function showConversationModal(focusTarget) {
    var m = document.getElementById('ai-conv');
    if (!m) return;
    // Cancel any in-flight close-timer from a prior hide; otherwise its
    // 240ms callback will fire `m.classList.add('hidden')` on the now-open
    // modal and yank it out of view.
    if (_closeTid) { clearTimeout(_closeTid); _closeTid = 0; }
    m.classList.remove('hidden', 'ai-conv--closing');
    _prevFocus = document.activeElement;
    void m.offsetWidth;
    m.classList.add('ai-conv--open');
    m.setAttribute('aria-modal', 'true');
    // Body-level flag: slides the bottom bar down and keeps the dock out of the way.
    document.body.classList.add('ai-conv-active');
    // Update AI button states
    var aiBtn = document.getElementById('bottom-bar__ai');
    if (aiBtn) aiBtn.setAttribute('aria-expanded', 'true');
    var legacyTab = document.getElementById('ai-dock__tab--ai');
    if (legacyTab) legacyTab.setAttribute('aria-expanded', 'true');
    // Focus: prefer explicit target (e.g., composer input), else close button for Esc-dismiss discoverability.
    var target = focusTarget || m.querySelector('.ai-conv__close');
    if (target && typeof target.focus === 'function') target.focus();
    else {
      var first = m.querySelector('input, textarea, button, [tabindex]:not([tabindex="-1"])');
      if (first) first.focus();
      else m.focus();
    }
  }

  function hideConversationModal() {
    var m = document.getElementById('ai-conv');
    if (!m) return;
    m.classList.remove('ai-conv--open');
    m.classList.add('ai-conv--closing');
    if (_closeTid) clearTimeout(_closeTid);
    _closeTid = setTimeout(function () {
      _closeTid = 0;
      m.classList.add('hidden');
      m.classList.remove('ai-conv--closing');
    }, 240);
    m.setAttribute('aria-modal', 'false');
    document.body.classList.remove('ai-conv-active');
    // Update AI button states
    var aiBtn = document.getElementById('bottom-bar__ai');
    if (aiBtn) aiBtn.setAttribute('aria-expanded', 'false');
    var legacyTab = document.getElementById('ai-dock__tab--ai');
    if (legacyTab) legacyTab.setAttribute('aria-expanded', 'false');
    // Restore focus to the element that was active before the modal opened.
    // Guard: the original element may have been removed from the DOM
    // (e.g. a card that got re-rendered). Only restore if still focusable.
    if (_prevFocus && _prevFocus.isConnected && typeof _prevFocus.focus === 'function') {
      try { _prevFocus.focus(); } catch (_) {}
    }
    _prevFocus = null;
  }

  function appendConvMessage(role, md, fromComposer) {
    const box = document.getElementById('ai-conv__messages');
    if (!box) return;
    // Validate role — only 'user' or 'assistant' allowed to prevent CSS injection via className
    var safeRole = (role === 'user' || role === 'assistant') ? role : 'assistant';
    const row = document.createElement('div');
    row.className = 'ai-conv__msg ai-conv__msg--' + (safeRole === 'user' ? 'user' : 'assistant');
    if (safeRole === 'user') {
      // User text is always escaped — no markdown/HTML allowed.
      const safe = escapeHtml(String(md));
      // Dual checkmarks: top = sent from client (grey→bright), bottom = delivered/processed (grey→blue)
      row.innerHTML = `
        <div class="ai-conv__bubble">${safe}</div>
        <div class="ai-conv__checks" aria-hidden="true">
          <span class="ai-conv__check ai-conv__check--sent" title="Sent from your device">✓</span>
          <span class="ai-conv__check ai-conv__check--delivered" title="Delivered to assistant">✓</span>
        </div>
      `;
      // Animate checkmarks: sent immediately, delivered after processing
      // Guard against row removal (modal close, clear) before timeout fires.
      setTimeout(() => {
        if (!row.isConnected) return;
        const sent = row.querySelector('.ai-conv__check--sent');
        const delivered = row.querySelector('.ai-conv__check--delivered');
        if (sent) sent.classList.add('ai-conv__check--active');
        // Delivered brightens when internal reply is formulated (after delay)
        setTimeout(() => {
          if (!row.isConnected) return;
          if (delivered) delivered.classList.add('ai-conv__check--active');
        }, fromComposer ? 800 : 0);
      }, 0);
    } else {
      // Assistant markdown comes from classify() (trusted) or Mouth API (future).
      // Render via safe markdown→DOM (no HTML passthrough). For Mouth API responses
      // that might contain raw HTML, fall back to renderSafeHtml.
      var safeHtml;
      if (typeof md === 'string' && /[#*_`\[\]]/.test(md)) {
        safeHtml = renderMarkdown(md);
      } else {
        safeHtml = renderSafeHtml(md);
      }
      row.innerHTML = `
        <div class="ai-conv__avatar" aria-hidden="true">✦</div>
        <div class="ai-conv__bubble">${safeHtml}</div>
      `;
    }
    box.appendChild(row);
    fillAvatarSlots(row); // org avatar on assistant replies
    box.scrollTop = box.scrollHeight;
  }

  /* ── Shared input sanitization ───────────────────────────────────────────
     Strips C0/C1 control chars, zero-width/RTL-override chars, collapses whitespace.
     Returns trimmed string, or empty string if input becomes empty after sanitization. */
  function sanitizeQuery(raw) {
    if (!raw) return '';
    return String(raw)
      .replace(/[\u0000-\u001F\u007F-\u009F\u200B-\u200F\u202A-\u202E\u2066-\u2069]+/g, ' ')
      .replace(/\s+/g, ' ')
      .trim();
  }

  // ── Safe HTML renderer ──────────────────────────────────────────
  // Parses `html` with DOMParser (safe, no execution), then walks the
  // tree and returns a sanitized string. Strips:
  //   - All tags except: p b i a div span br strong em ul ol li
  //   - All attributes except: href (whitelisted scheme), target (whitelisted), class (allowlisted prefixes)
  //   - All on* event handlers (onerror, onclick, onload …)
  //   - javascript:, data:, vbscript: URL schemes (with leading whitespace
  //     and HTML-encoded prefixes to defeat obfuscation)
  //   - id attributes (would collide with page IDs and CSS)
  // Notes:
  //   - rel="noopener nofollow" is added programmatically for external https: links
  //   - class attribute values must match ALLOWED_CLASS_PREFIXES (ai-step, ai-conv, ai-bar, role-badge + BEM modifiers)
  // Falls back to plain-text escape if DOMParser is unavailable.
  var ALLOWED_TAGS = {'p':1,'b':1,'i':1,'a':1,'div':1,'span':1,'br':1,'strong':1,'em':1,'ul':1,'ol':1,'li':1};
  var ALLOWED_ATTRS = {'href':1,'target':1};
  // Only allow the ai-step / ai-conv namespaced classes that classify() emits.
  // Reject all other class values to prevent Mouth from injecting arbitrary
  // CSS that could break page layout or override host-site styles.
  // Matches exact class token: "ai-step" or "ai-step other-class" but NOT "ai-step-malicious"
  var ALLOWED_CLASS_PREFIXES = ['ai-step','ai-conv','ai-bar','role-badge'];
  var _allowedClassRx = null;  // lazily built RegExp
  function _allowClass(v) {
    if (!_allowedClassRx) {
      // Each class token must be exactly one of the allowed prefixes, optionally followed by --modifier (BEM)
      // e.g., "ai-step", "ai-step--large", "role-badge role-badge--godadmin"
      // but NOT "ai-step-malicious" or "ai-step evil"
      var tokenPattern = '(' + ALLOWED_CLASS_PREFIXES.map(function (p) { return p.replace('-', '\\-') + '(?:--[a-z0-9-]+)?'; }).join('|') + ')';
      _allowedClassRx = new RegExp('^' + tokenPattern + '(?:\\s+' + tokenPattern + ')*$');
    }
    return _allowedClassRx.test(v);
  }
  // Strip leading whitespace, control chars, and HTML-encoded NULL bytes
  // that some browsers strip before evaluation but only after the regex test
  // would have already run on the raw attribute value.
  function _trimHref(v) {
    return String(v).replace(/[\s\x00-\x1F]+/g, '').replace(/&#x?[0-9a-fA-F]+;?/g, '');
  }
  function _isSafeUrl(v) {
    var t = _trimHref(v);
    if (!t) return false;
    if (/^(javascript|data|vbscript|file):/i.test(t)) return false;
    return /^(https?:|mailto:|\/|#|\?)/i.test(t) || /^[a-z0-9._~!$&'()*+,;=:@\/?%#-]+$/i.test(t);
  }

  // ── Markdown → DOM renderer (safe, no HTML passthrough) ────────────────
// Renders a trusted markdown subset used by classify() and Mouth.
// Supported: paragraphs, **bold**, *italic*, `code`, [links](url),
// unordered lists (- item), ordered lists (1. item), step blocks
// (:::step\n**Title**\nContent\n:::) which become .ai-step with .n badge.
function renderMarkdown(md) {
  var str = String(md || '').trim();
  if (!str) return '';

  // Split into blocks (blank-line separated)
  var blocks = str.split(/\n\s*\n/);
  var frag = document.createDocumentFragment();

  blocks.forEach(function (block) {
    block = block.trim();
    if (!block) return;

    // Step block: :::step\n**Title**\nBody\n:::
    // Closing delimiter must be exactly ::: on its own line (or :::step-end)
    if (/^:::step\b/.test(block)) {
      var lines = block.split('\n');
      var endIdx = lines.findIndex(function (l, i) { return i > 0 && /^:::(?:step-end)?\s*$/i.test(l.trim()); });
      var contentLines = (endIdx > 0) ? lines.slice(1, endIdx) : lines.slice(1);
      var stepHtml = contentLines.join('\n').trim();
      var stepEl = document.createElement('div');
      stepEl.className = 'ai-step';
      // Render inline markdown inside the step
      stepEl.innerHTML = renderInline(stepHtml);
      frag.appendChild(stepEl);
      return;
    }

    // Ordered list: 1. item / 2. item
    if (/^\d+\.\s/.test(block)) {
      var ol = document.createElement('ol');
      block.split('\n').forEach(function (line) {
        var m = line.match(/^\d+\.\s+(.*)$/);
        if (m) {
          var li = document.createElement('li');
          li.innerHTML = renderInline(m[1]);
          ol.appendChild(li);
        }
      });
      frag.appendChild(ol);
      return;
    }

    // Unordered list: - item
    if (/^-\s/.test(block)) {
      var ul = document.createElement('ul');
      block.split('\n').forEach(function (line) {
        var m = line.match(/^-\s+(.*)$/);
        if (m) {
          var li = document.createElement('li');
          li.innerHTML = renderInline(m[1]);
          ul.appendChild(li);
        }
      });
      frag.appendChild(ul);
      return;
    }

    // Regular paragraph
    var p = document.createElement('p');
    p.innerHTML = renderInline(block);
    frag.appendChild(p);
  });

  // Serialize back to string
  var tmp = document.createElement('div');
  tmp.appendChild(frag);
  return tmp.innerHTML;
}

// Inline markdown renderer (no block elements)
  // Handles: **bold**, *italic*, `code`, [text](url)
  // Strategy: tokenize by markdown patterns, escape plain text, keep tokens.
  function renderInline(text) {
    var str = String(text);
    if (!str) return '';

    // Token types: LINK, BOLD, ITALIC, CODE, TEXT
    var tokens = [];
    var pos = 0;

    // Regex for all inline patterns (ordered by precedence)
    var patterns = [
      { type: 'LINK',    re: /\[([^\]]+)\]\(([^)]+)\)/ },
      { type: 'BOLD',    re: /\*\*([^\*]+)\*\*/ },
      { type: 'ITALIC',  re: /\*([^\*]+)\*/ },
      { type: 'CODE',    re: /`([^`]+)`/ }
    ];

    while (pos < str.length) {
      var match = null;
      var matchType = null;
      var matchIndex = -1;

      // Find earliest match among all patterns
      patterns.forEach(function (p) {
        var m = str.slice(pos).match(p.re);
        if (m && (matchIndex === -1 || m.index < matchIndex)) {
          match = m;
          matchType = p.type;
          matchIndex = m.index;
        }
      });

      if (match) {
        // Text before match
        if (match.index > 0) {
          tokens.push({ type: 'TEXT', content: str.slice(pos, pos + match.index) });
        }
        // The match
        if (matchType === 'LINK') {
          var label = match[1];
          var url = match[2];
          var safe = _isSafeUrl(url) ? _trimHref(url) : '#';
          tokens.push({ type: 'LINK', label: label, url: safe });
        } else {
          tokens.push({ type: matchType, content: match[1] });
        }
        pos += match.index + match[0].length;
      } else {
        // No more matches - rest is plain text
        tokens.push({ type: 'TEXT', content: str.slice(pos) });
        break;
      }
    }

    // Render tokens
    return tokens.map(function (t) {
      switch (t.type) {
        case 'LINK':
          return '<a href="' + escapeHtml(t.url) + '" target="_blank" rel="noopener nofollow">' + escapeHtml(t.label) + '</a>';
        case 'BOLD':
          return '<b>' + escapeHtml(t.content) + '</b>';
        case 'ITALIC':
          return '<i>' + escapeHtml(t.content) + '</i>';
        case 'CODE':
          return '<code>' + escapeHtml(t.content) + '</code>';
        case 'TEXT':
        default:
          return escapeHtml(t.content);
      }
    }).join('');
  }

function renderSafeHtml(html) {
    var str = String(html || '');
    if (!str || !/<[a-z]/i.test(str)) return escapeHtml(str);
    try {
      var dp = new DOMParser();
      var doc = dp.parseFromString('<!DOCTYPE html><div xmlns="http://www.w3.org/1999/xhtml">' + str + '</div>', 'application/xhtml+xml');
      var frag = document.createDocumentFragment();
      function walk(n) {
        if (n.nodeType === 3) {
          frag.appendChild(n.cloneNode(false));
          return;
        }
        if (n.nodeType !== 1) return;
        var tag = n.nodeName.toLowerCase();
        if (!ALLOWED_TAGS[tag]) {
          // Non-allowed tag: recurse into children but don't emit the tag.
          Array.prototype.forEach.call(n.childNodes, walk);
          return;
        }
        var el = document.createElement(tag);
        // Copy only allowed attributes; drop event handlers and bad URL schemes.
        Array.prototype.forEach.call(n.attributes, function (attr) {
          var an = attr.name.toLowerCase();
          if (!ALLOWED_ATTRS[an]) return;
          // Defense against namespace confusion: any attribute starting with
          // "on" is an event handler regardless of prefix.
          if (an.indexOf('on') === 0) return;
          var av = attr.value;
          if (an === 'href') {
            if (!_isSafeUrl(av)) return;
            if (/^https?:\/\//i.test(av)) el.setAttribute('rel', 'noopener nofollow');
          }
          if (an === 'class') {
            if (!_allowClass(av)) return;
          }
          if (an === 'target' && !/^(_blank|_self|_parent|_top)$/i.test(av)) return;
          el.setAttribute(an, av);
        });
        Array.prototype.forEach.call(n.childNodes, walk);
        frag.appendChild(el);
      }
      Array.prototype.forEach.call(doc.documentElement.childNodes, walk);
      // Serialize the sanitized fragment back to HTML string.
      var tmp = document.createElement('div');
      tmp.appendChild(frag);
      return tmp.innerHTML;
    } catch (_) {
      // DOMParser unavailable (unlikely) — fall back to escaping all HTML.
      return escapeHtml(str);
    }
  }

  function setConvTyping(on, text) {
    const t = document.getElementById('ai-conv__typing');
    if (!t) return;
    t.classList.toggle('hidden', !on);
    if (on && text) {
      const span = document.getElementById('ai-conv__typing-text');
      if (span) span.textContent = text;
    }
    const box = document.getElementById('ai-conv__messages');
    if (box) box.scrollTop = box.scrollHeight;
  }

  function setConvHeart(state, text) {
    const wrap = document.getElementById('ai-conv__heart');
    const dot  = wrap && wrap.querySelector('.ai-conv__heart-dot');
    const span = document.getElementById('ai-conv__heart-text');
    if (!wrap) return;
    // Validate state — only known states allowed to prevent arbitrary class injection
    var validStates = ['ai-conv__heart--up', 'ai-conv__heart--down', 'ai-conv__heart--probe'];
    var safeState = (state && validStates.indexOf(state) !== -1) ? state : '';
    wrap.classList.remove('ai-conv__heart--up', 'ai-conv__heart--down', 'ai-conv__heart--probe');
    if (safeState) wrap.classList.add(safeState);
    if (span && text) span.textContent = text;
  }

  /* ── Heart/Mouth heartbeat detection ─────────────────────────── */
  // Probes a well-known heart-endpoint to decide whether the body is online.
  // Falls back to local classify() if Heart is unreachable. This is the
  // "goes through heartbeat detection" wire you asked for.
  const HEART_ENDPOINTS = [
    'https://neohiro.github.io/.well-known/heartbeat',
    'https://neohiro.github.io/heartbeats/health.json'
  ];

  /* Where the assistant's traffic actually goes.
   *
   * The four public sites are GitHub Pages — static files with no compute — so
   * nothing on that origin can answer /.well-known/ask. brain-bridge is the
   * process that does: it runs on the mainframe node, calls Brain, falls back to
   * Mouth, and durably queues anything that is really a message to a human.
   * See network/brain_bridge/README.md.
   *
   * A fork can point at its own bridge without editing this file:
   *   <script>window.NEOHIRO_BRIDGE = 'https://brain.example.internal';</script>
   */
  const BRIDGE_URL = (window.NEOHIRO_BRIDGE || 'https://neohiro.github.io').replace(/\/+$/, '');
  const MOUTH_ENDPOINT = BRIDGE_URL + '/.well-known/ask';
  const VOICEMAIL_ENDPOINT = BRIDGE_URL + '/.well-known/voicemail';
  const SITE_KEY = (function () {
    var h = (location.hostname || '').toLowerCase();
    if (h.indexOf('transhumanists') >= 0) return 'transhumanists';
    if (h.indexOf('openstageisland') >= 0) return 'openstageisland';
    if (h.indexOf('frenzypenguin') >= 0) return 'frenzypenguin-media';
    return 'neohiro';
  })();

  // The GitHub session, when the visitor is signed in, so the bridge knows who
  // is writing instead of guessing from an email-shaped string.
  function currentAuth() {
    try {
      var raw = localStorage.getItem('neohiro_session_v1');
      if (!raw) return null;
      var s = JSON.parse(raw);
      if (!s || !s.login || !Number.isFinite(s.expiresAt) || s.expiresAt < Date.now()) return null;
      return { login: s.login, role: s.role || (s.login === 'neohiro' ? 'godadmin' : 'user') };
    } catch (_) { return null; }
  }

  let _heartUp = null;
  let _heartProbed = false;
  let _heartProbePromise = null; // Deduplicate concurrent probes

  function fetchWithTimeout(url, opts, ms) {
    var ctrl = typeof AbortController !== 'undefined' ? new AbortController() : null;
    var signal = ctrl ? ctrl.signal : null;
    var tid = setTimeout(function () { if (ctrl) ctrl.abort(); }, ms);
    return fetch(url, Object.assign({}, opts || {}, { signal: signal }))
      .finally(function () { clearTimeout(tid); })
      .then(function (r) {
        if (!r.ok) throw new Error('HTTP ' + r.status);
        return r;
      })
      .catch(function (err) {
        if (err && err.name === 'AbortError') {
          var e = new Error('Request timeout');
          e.code = 'ETIMEDOUT';
          throw e;
        }
        throw err;
      });
  }

  function probeHeart() {
    if (_heartProbePromise) return _heartProbePromise; // Return existing in-flight probe
    // Allow re-probe if previous attempt failed (_heartUp === false).
    // Only short-circuit if we have a positive result cached.
    if (_heartProbed && _heartUp) return Promise.resolve(_heartUp);
    _heartProbed = true;
    setConvHeart('ai-conv__heart--probe', 'probing heart…');
    // Try each endpoint in sequence until one succeeds
    _heartProbePromise = HEART_ENDPOINTS.reduce(function (promise, url) {
      return promise.catch(function () {
        return fetchWithTimeout(url, { cache: 'no-store', mode: 'cors' }, 8000)
          .then(function (r) { return r && r.ok; });
      });
    }, Promise.reject(new Error('no endpoints')))
      .then(function (up) { _heartUp = up; return up; })
      .catch(function () { _heartUp = false; return false; })
      .then(function (up) {
        setConvHeart(up ? 'ai-conv__heart--up' : 'ai-conv__heart--down',
                     up ? 'heart online' : 'heart offline (local brain)');
        _heartProbePromise = null; // Clear for future probes
        return up;
      });
    return _heartProbePromise;
  }

  /* Fetch and compact the site's README for context grounding.
     Returns a Promise that resolves to a compacted string (max ~2000 chars).
     Memoized: subsequent calls within the session return the cached result.
     Abortable: pass an AbortSignal to cancel in-flight requests. */
  var _readmeCache = null;
  var _readmeInflight = null;
  function fetchReadmeContext(signal) {
    // Return cached result immediately if available
    if (_readmeCache !== null) {
      return Promise.resolve(_readmeCache);
    }
    // If a fetch is already in flight, return that promise (deduplication)
    if (_readmeInflight) {
      // If caller provides a signal, attach abort handling
      if (signal) {
        return new Promise(function (resolve, reject) {
          _readmeInflight.then(resolve, reject);
          signal.addEventListener('abort', function () {
            reject(new DOMException('Aborted', 'AbortError'));
          }, { once: true });
        });
      }
      return _readmeInflight;
    }
    var readmeUrl = location.origin + '/README.md';
    var ctrl = typeof AbortController !== 'undefined' ? new AbortController() : null;
    var fetchSignal = signal || (ctrl ? ctrl.signal : null);
    var fetchPromise = fetchWithTimeout(readmeUrl, { cache: 'no-store', signal: fetchSignal }, 5000)
      .then(function (r) { if (!r.ok) throw new Error('README HTTP ' + r.status); return r.text(); })
      .then(function (text) {
        // Compact: strip frontmatter, code blocks, images, badges, keep headings + first paragraph
        var compact = text
          .replace(/^---[\s\S]*?---/m, '') // frontmatter
          .replace(/```[\s\S]*?```/g, '') // code blocks
          .replace(/!\[.*?\]\(.*?\)/g, '') // images
          .replace(/\[!\[.*?\]\(.*?\)\]\(.*?\)/g, '') // badges
          .replace(/^#+\s+/gm, '') // heading markers
          .replace(/\n{3,}/g, '\n\n') // collapse excessive newlines
          .replace(/\s+/g, ' ') // collapse whitespace
          .trim();
        // Truncate to ~2000 chars for token optimization
        var result = compact.length > 2000 ? compact.slice(0, 2000) + '…' : compact;
        _readmeCache = result;
        _readmeInflight = null;
        return result;
      })
      .catch(function (err) {
        _readmeInflight = null;
        if (err && err.name === 'AbortError') return '';
        return ''; // Silent failure, no context
      });
    _readmeInflight = fetchPromise;
    return fetchPromise;
  }

  function fetchMouthReply(q, opts) {
    // POST JSON with full context grounding: query + site + page + compacted README
    // opts: { model, scope, replyMode }
    var model = (opts && opts.model) || 'low';
    var scope = (opts && opts.scope) || 'all';
    var replyMode = (opts && opts.replyMode) || 'assistant';
    return fetchReadmeContext().then(function (readmeCtx) {
      return fetchWithTimeout(
        MOUTH_ENDPOINT,
        {
          method: 'POST',
          mode: 'cors',
          cache: 'no-store',
          headers: { 'content-type': 'application/json' },
          body: JSON.stringify({
            q: q,
            site: SITE_KEY,
            page: location.pathname,
            model: model,
            scope: scope,
            replyMode: replyMode,
            context: {
              site: SITE_KEY,
              path: location.pathname,
              readme: readmeCtx
            }
          })
        },
        12000
      )
        .then(function (r) { if (!r.ok) throw new Error('Mouth HTTP ' + r.status); return r.json(); })
        .then(function (j) { return j && (j.reply || j.answer || j.text) || null; })
        .catch(function () { return null; });
    });
  }

/* ── Voicemail ──────────────────────────────────────────────────────────
   A question the assistant cannot answer becomes a message for a human, and
   that message must not evaporate. It is POSTed to brain-bridge, which
   fsyncs it before acknowledging, so a "queued" receipt is a promise.
   Returns {ok, receipt} — the caller shows the receipt either way. */
  function sendVoicemail(message, who, about, opts) {
    // opts: { model, scope, replyMode }
    var model = (opts && opts.model) || 'low';
    var scope = (opts && opts.scope) || 'all';
    var replyMode = (opts && opts.replyMode) || 'assistant';
    return fetchReadmeContext().then(function (readmeCtx) {
      return fetchWithTimeout(
        VOICEMAIL_ENDPOINT,
        {
          method: 'POST',
          mode: 'cors',
          cache: 'no-store',
          headers: { 'content-type': 'application/json' },
          body: JSON.stringify({
            message: message,
            site: SITE_KEY,
            page: location.pathname,
            referrer: document.referrer || null,
            about: about || '',
            who: who || {},
            auth: currentAuth(),
            model: model,
            scope: scope,
            replyMode: replyMode,
            context: {
              site: SITE_KEY,
              path: location.pathname,
              readme: readmeCtx
            }
          })
        },
        12000
      )
        .then(function (r) { return r.json().then(function (j) { return { ok: r.ok, body: j }; }); })
        .then(function (res) { return { ok: res.ok, receipt: (res.body && res.body.id) || null }; })
        .catch(function () { return { ok: false, receipt: null }; });
    });
  }

  function detectStranger() {
    try {
      const KEY = 'neohiro.visitor.v1';
      const raw = localStorage.getItem(KEY);
      if (raw) {
        const v = JSON.parse(raw);
        if (v && v.firstSeen) return; // not new
      }
      const stamp = {
        firstSeen: new Date().toISOString(),
        host: location.hostname,
        path: location.pathname,
        ref: document.referrer || null,
        ua: (navigator.userAgent || '').slice(0, 200)
      };
      localStorage.setItem(KEY, JSON.stringify(stamp));
      window.dispatchEvent(new CustomEvent('neohiro:stranger', { detail: stamp }));
    } catch (_) { /* private mode etc. */ }
  }

  /* ── AI assistant input bar (full width) ──────────────────────── */
function mountAssistantBar() {
    if (document.getElementById('ai-bar')) return;

    recordCurrent(); // register this page for the cross-domain back button

    const wrap = document.createElement('div');
    wrap.className = 'ai-bar';
    wrap.id = 'ai-bar';
    wrap.setAttribute('role', 'region');
    wrap.setAttribute('aria-label', 'Ask the neohiro assistant');
    wrap.innerHTML = `
      <div class="ai-bar__inner">
        <span class="ai-bar__hint" aria-hidden="true">ask anything · reports · repo discovery · guided tours</span>
        <form class="ai-bar__form" id="ai-bar__form" autocomplete="off">
          <span class="ai-bar__icon" aria-hidden="true">
            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" width="20" height="20">
              <path d="M12 2L9 8l-6 1 4.5 4.5L6 20l6-3.5L18 20l-1.5-6.5L21 9l-6-1z"/>
            </svg>
          </span>
          <input
            id="ai-bar__input"
            class="ai-bar__input"
            type="text"
            name="q"
            placeholder="Ask the neohiro assistant — find a repo, report a bug, get a guide, or describe what you need…"
            aria-label="Ask the neohiro assistant"
            maxlength="600" />
          <button type="submit" class="ai-bar__send" id="ai-bar__send" aria-label="Send message">
            <span>Send</span>
            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" width="14" height="14" aria-hidden="true">
              <path d="M5 12h14M12 5l7 7-7 7"/>
            </svg>
          </button>
        </form>
        <div class="ai-bar__vars" id="ai-bar__vars" hidden>
          <label class="ai-bar__var-row" title="Model">
            <span class="ai-bar__var-label">Model</span>
            <select class="ai-bar__var-select" name="model" aria-label="Model">
              <option value="low">Low — free-model routing</option>
              <option value="high">High — higher reasoning models</option>
            </select>
          </label>
          <button type="button" class="ai-bar__vars-toggle" id="ai-bar__vars-toggle" aria-expanded="false" aria-controls="ai-bar__vars">
            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" width="14" height="14" aria-hidden="true"><path d="M6 9l6 6 6-6"/></svg>
            <span class="ai-bar__vars-toggle-text">Model</span>
          </button>
        </div>
        <div class="ai-bar__typing hidden" id="ai-bar__typing" role="status" aria-live="polite">
          <span class="ai-bar__dots" aria-hidden="true"><span></span><span></span><span></span></span>
          <span id="ai-bar__typing-text">Mouth is composing your reply…</span>
        </div>
        <div class="ai-bar__response hidden" id="ai-bar__response" role="region" aria-live="polite"></div>
        <div class="ai-bar__counter" id="ai-bar__counter" aria-live="off" aria-atomic="true">0 / 600</div>
      </div>
    `;

    // Mount point. Preference order:
    //   1. an explicit [data-ai-bar-slot] the site provides (full control)
    //   2. the hero CTA row (this is where the ask bar belongs)
    //   3. the live-signal section (legacy fallback)
    // It must NOT land in the live-signal section by default any more: that
    // section is now below the fold behind a full-height hero, and the ask bar
    // is meant to read as the hero's primary action.
    const slot = document.querySelector('[data-ai-bar-slot]');
    const heroCta = document.querySelector('.hero-cta');
    const typewriterWrap = document.querySelector('.typewriter-wrap');
    if (slot) {
      slot.appendChild(wrap);
    } else if (heroCta && heroCta.parentNode) {
      heroCta.parentNode.insertBefore(wrap, heroCta.nextSibling);
    } else if (typewriterWrap) {
      typewriterWrap.parentNode.insertBefore(wrap, typewriterWrap);
    } else {
      document.body.appendChild(wrap);
    }
    document.body.classList.add('ai-bar-mounted');

const form = document.getElementById('ai-bar__form');
    const input = document.getElementById('ai-bar__input');
    const counter = document.getElementById('ai-bar__counter');
    form.addEventListener('submit', onAsk);
    // Live char counter: shows only when near limit (cleaner minimal UI)
function updateCounter() {
        var n = input.value.length;
        counter.textContent = n + ' / 600';
        counter.classList.toggle('ai-bar__counter--visible', n >= 480 || n > 600);
        counter.classList.toggle('ai-bar__counter--near', n >= 540);
        counter.classList.toggle('ai-bar__counter--over', n > 600);
        form.classList.toggle('has-content', n > 0);
      }
    input.addEventListener('input', updateCounter);
    updateCounter();
    // Wire up the model selection vars toggle
    var varsBox = document.getElementById('ai-bar__vars');
    var varsToggle = document.getElementById('ai-bar__vars-toggle');
    if (varsToggle && varsBox) {
      varsToggle.addEventListener('click', function () {
        var open = varsBox.hasAttribute('hidden');
        varsBox.hidden = !open;
        varsToggle.setAttribute('aria-expanded', open ? 'true' : 'false');
        if (open) {
          varsToggle.querySelector('.ai-bar__vars-toggle-text').textContent = 'Hide model';
        } else {
          varsToggle.querySelector('.ai-bar__vars-toggle-text').textContent = 'Model';
        }
      });
    }
    // Cute dynamic cursor: shift placeholder text on focus/blur
    const placeholders = [
      'Ask the neohiro assistant — find a repo, report a bug, get a guide, or describe what you need…',
      'Try: "harden my Windows laptop in 5 minutes"',
      'Try: "show me encryption tools"',
      'Try: "report a bug in Cripple-NetStrip"',
      'Try: "take me to the world map dashboard"',
      'Try: "how do I file a security advisory?"'
    ];
    let pIdx = 0;
    input.addEventListener('focus', () => {
      if (!input.value) {
        pIdx = (pIdx + 1) % placeholders.length;
        input.placeholder = placeholders[pIdx];
      }
    });
  }

  // ── In-flight state (singleton guards) ──
  let _inFlightInt = null;
  let _inFlightTO  = null;
  let _inFlightVer = 0;

  // Cancel any pending AI work on page nav. Bumps _inFlightVer so pending
  // .then() callbacks short-circuit DOM writes; clears the timer + interval
  // so they don't fire on a detached page (browsers usually suppress this,
  // but bfcache restoration can re-run them).
  function _cancelInFlight() {
    if (_inFlightTO) { clearTimeout(_inFlightTO); _inFlightTO = null; }
    if (_inFlightInt) { clearInterval(_inFlightInt); _inFlightInt = null; }
    _inFlightVer++;  // invalidate any in-flight .then() guards
  }
  window.addEventListener('pagehide', _cancelInFlight);

  function onAsk(e) {
    e.preventDefault();
    const input = document.getElementById('ai-bar__input');
    const raw = input.value;
    // Sanitize: strip C0/C1 control chars (incl. \0, \r, \v, \f, ESC) and
    // collapse runs of whitespace. Defends against:
    //   - zero-width / RTL-override chars spoofing intent
    //   - tab/CR injection into the classify() regex subject
    //   - log-spamming via \b\b\b or terminal escapes
    const q = sanitizeQuery(raw);
    if (!q) { input.focus(); return; }
    if (q.length > 600) {
      // Truncate — the live counter already warned at 540+ (amber) and 600+ (red).
      // No toast needed; user self-corrects before submit.
      input.value = q.slice(0, 600);
      input.focus();
      return;
    }

    // If already processing, ignore rapid resubmit (prevents leak + race)
    if (_inFlightTO) return;

    const wrap = document.getElementById('ai-bar');
    if (wrap) wrap.classList.add('ai-bar--sent');

    // Read variable menu selections (future: pass to backend)
    var form = document.getElementById('ai-bar__form');
    var modelSelect = form ? form.querySelector('[name="model"]') : null;
    var composerOpts = {
      model: modelSelect ? modelSelect.value : 'low',
    };
    window.__aiComposerOpts = composerOpts;

    input.setAttribute('aria-busy', 'true');
    input.disabled = true;

    // ── Step 1: show the conversation modal ─────────────────────
    showConversationModal();
    appendConvMessage('user', q, false); // false = from AI bar (not composer)
    input.value = '';
    // Reset char counter (stale after programmatic clear; updateCounter()
    // lives in mountAssistantBar's closure so we write directly).
    var ctr = document.getElementById('ai-bar__counter');
    if (ctr) { ctr.textContent = '0 / 600'; ctr.className = 'ai-bar__counter'; ctr.classList.remove('ai-bar__counter--visible', 'ai-bar__counter--near', 'ai-bar__counter--over'); }

    // ── Step 2: probe Heart while typing indicator starts ─────────
    probeHeart();

    const cycle = [
      'Mouth is reading your question…',
      'Triage: identifying who you are and what you need…',
      'Pulling the right repo / docs / step-by-step…',
      'Composing a helpful reply…'
    ];
    const myVer = ++_inFlightVer;
    let c = 0;
    setConvTyping(true, cycle[0]);
    _inFlightInt = setInterval(() => {
      if (myVer !== _inFlightVer) return;
      c = (c + 1) % cycle.length;
      setConvTyping(true, cycle[c]);
    }, 900);

    // ── Step 3: fetch from Heart/Mouth → fall back to local classify ─
    const delay = 1500 + Math.random() * 600;
    _inFlightTO = setTimeout(() => {
      _inFlightInt && clearInterval(_inFlightInt);
      _inFlightInt = null;
      _inFlightTO = null;
      if (myVer !== _inFlightVer) return;

      setConvTyping(false);
      const reply = fetchMouthReply(q, composerOpts)
        .then(mouthText => mouthText || classify(q))
        .catch(() => classify(q));

      reply.then(replyHtml => {
        if (myVer !== _inFlightVer) return;
        appendConvMessage('assistant', replyHtml);
        input.removeAttribute('aria-busy');
        input.disabled = false;
        if (wrap) wrap.classList.remove('ai-bar--sent');
        input.focus();
      });
    }, delay);
  }

  function classify(q) {
    const t = q.toLowerCase();
    // Word-boundary anchored patterns to avoid false positives like
    //   "I have a security issue"  → NOT harden
    //   "stream of consciousness"  → NOT media hub
    //   "world map" css layout     → still matches dashboard
    // Each branch is ordered by specificity (most specific first).
    const isBugSec = /(security\s+(vuln|issue|advisory|advisories|disclosure|bug)|cve|advisory|vulnerability|exploit|disclosure)/.test(t);
    const isBug    = /(\bbug|\bissue|\bcrash|\bbroken\b|broken\s*link|not\s*working|stopped\s*working|throws?\s+an?\s+error|\berror\s+when)/.test(t);
    const isReport = /(\breport\b|file\s+(a|an|the|this|my)?\s*(bug|issue|advisory|cve|security)|open\s+a\s+ticket|submit\s+(a|an|the|this|my)?\s*(report|bug|issue|advisory|advisories|disclosure))/i.test(t);
    const isHard   = /(harden|hardening|hardened|secure\s+(windows|linux|ubuntu|debian|server|laptop|system|machine)|stig|baseline\s+(config|hardening|security)|lockdown|defend\s+against|mitigat(e|ion))/i.test(t);
    const isDash   = /(dashboard|world\s*map|worldmap|metrics?|chart|graph|gauge)/i.test(t);
    const isMedia  = /(video(\s+(tutorial|guide|deep[-\s]*dive))?|media\s*hub|youtube|frenzypenguin|stream(ing)?\s+(live|server|music|video))/i.test(t);
    const isSponsor = /(sponsor|donate|patreon|fund(ing|raise)?|support\s+(this|the|a|our|your)\s*(project|team|developers|creator|channel)|tip\s+jar)/i.test(t);
    const isRepo   = /(repo|repository|which\s+tool|find\s+(a|me|the|an?)\s+(tool|app|software|repo)|looking\s+for\s+(a|an?)\s+(tool|app|software|repo|replacement|alternative))/i.test(t);
    const isOS     = /(linux|ubuntu|debian|arch|fedora|rhel|suse|manjaro|windows|mac\s*os|osx)/i.test(t);

    if (isBugSec || (isBug && /(security|secure|vuln|advisory|cve)/.test(t))) {
      return stepsForBug();
    }
    // Bug takes priority over report (more specific intent signal).
    if (isBug || isReport) {
      return stepsForBug();
    }
    // Hardening: requires both harden intent AND an OS keyword.
    if (isHard) {
      if (isOS) return stepsForHardening(t);
      // STIG without explicit OS -> assume Linux (STIG is Linux-specific baseline)
      if (/\bstig\b/i.test(t)) return stepsForHardening('linux ' + t);
    }
    if (isDash) {
      return `
**Dashboard** — live ops, world map, and metrics are at the central neohiro dashboard.

:::step
**Step 1** — [Open the dashboard](https://neohiro.github.io/dashboard/)
:::
:::step
**Step 2** — switch to the World Map panel
:::
:::step
**Step 3** — pin the categories you care about
:::

If you want to see heartbeats for the org, open [/heartbeats/](https://neohiro.github.io/heartbeats/) (public/authed/godadmin tiers).
      `.trim();
    }
    if (isMedia) {
      return `
**Media hub:** [FrenzyPenguin Media](https://neohiro.github.io/media/) — music artist recordings and creative content.

**YouTube:** [@FrenzyPenguinMedia](https://www.youtube.com/FrenzyPenguinMedia?sub_confirmation=1)
      `.trim();
    }
    if (isSponsor) {
      return `
Thanks for considering support — every bit keeps the tools free and telemetry-free.

- [Sponsor on GitHub](https://github.com/sponsors/neohiro)
- [Patreon](https://www.patreon.com/frenzypenguin_media)
- [Linktree](https://linktr.ee/frenzypenguin.media)
      `.trim();
    }
    if (isRepo) {
      return stepsForRepo();
    }
    // Default helpful response
    return `
Got it — I can help you with that. To give you the most useful answer, tell me one of these:

:::step
**1** — *"I'm looking for a tool to…"* — e.g. harden Windows, encrypt DNS, monitor a server. I'll match you to the right repo.
:::
:::step
**2** — *"I found a bug / want to report a security issue"* — I'll walk you to the right repo and pre-fill the issue template.
:::
:::step
**3** — *"Take me to the dashboard / world map / media hub / sponsors"* — instant cross-site navigation.
:::
    `.trim();
  }

  function stepsForBug() {
    return `
**Bug / Issue report** — I'll route you to the right repo and pre-fill diagnostics. Pick the project below:

:::step
**1** — **Identify the project.** Browse [all repositories](https://neohiro.github.io/repositories/) with filter/sort. If unsure, I'll suggest based on keywords.
:::
:::step
**2** — **Security vulnerability?** Use the repo's *Security* tab (private disclosure) — not the public issue tracker. [Open neohiro org](https://github.com/neohiro?tab=repositories).
:::
:::step
**3** — **Regular bug?** Open the repo's *Issues* tab, click *New issue*, choose the *Bug report* template, and include: OS, version, steps to reproduce, expected vs actual.
:::
:::step
**4** — **Need a discussion instead?** Use the repo's *Discussions* tab — great for questions, ideas, and showcases.
:::
    `.trim();
  }

  function stepsForRepo() {
    return `
**Repo discovery** — 15+ projects across security, privacy, networking, developer tools, and games.

:::step
**1** — Open the [All Repositories](https://neohiro.github.io/repositories/) page.
:::
:::step
**2** — Use the filter chips (Security & Privacy, Network, Developer, Games, …) and the search box.
:::
:::step
**3** — Sort by stars, recent activity, or year. Each card has Bug / Sec / Discuss quick-links.
:::
    `.trim();
  }

  function stepsForHardening(t) {
    const linux = /(linux|ubuntu|debian|arch|fedora|rhel|suse|manjaro)/.test(t);
    return linux
      ? `
**Linux hardening** — automated post-install path:

:::step
**1** — Run the [neohiro/linux](https://github.com/neohiro/linux) script (UFW + DNSCrypt + Tor + auditd + AppArmor + sysctl + SSH).
:::
:::step
**2** — For Ubuntu: [neohiro/ubuntu](https://github.com/neohiro/ubuntu) with snap/flatpak control + GNOME privacy.
:::
:::step
**3** — Network layer: [Cripple-NetStrip](https://github.com/neohiro/Cripple-NetStrip) (DNS sinkhole + encrypted DNS + firewall).
:::
      `.trim()
      : `
**Windows hardening** — pick a depth:

:::step
**1** — One-command STIG-style: [Harden-Windows](https://github.com/neohiro/windows) (18 modules, 4 profiles, rollback, dry-run).
:::
:::step
**2** — GUI exploit-mitigation catalog: [ExploitProtection](https://github.com/neohiro/ExploitProtection) (ASR + CFG + DEP + SEHOP).
:::
:::step
**3** — Network + DNS: [Cripple-NetStrip](https://github.com/neohiro/Cripple-NetStrip) and [dnscrypt-proxy-gui](https://github.com/neohiro/dnscrypt-proxy-gui).
:::
      `.trim();
  }

  /* ── Universal top-nav auth tabs ──────────────────────────────── */
  function injectNavAuth() {
    const nav = document.querySelector('.site-nav') || document.querySelector('header nav') || document.querySelector('nav');
    if (!nav) return;

    // nav.html now renders the auth slot statically (with data-nav-auth), so the
    // common case is "markup already present". Only build the legacy inline
    // version when it is missing — but ALWAYS run the state sync, otherwise the
    // static buttons would sit on "Login" forever.
    if (nav.querySelector('[data-nav-auth]')) {
      wireNavAuthControls();
      syncAuthFromBar();
      return;
    }

    const frag = document.createDocumentFragment();

    // Login tab
    const login = document.createElement('button');
    login.className = 'nav-auth nav-auth--login';
    login.id = 'nav-auth__login';
    login.type = 'button';
    login.setAttribute('data-nav-auth', 'login');
    login.innerHTML = `
      <svg viewBox="0 0 24 24" fill="currentColor" width="14" height="14" aria-hidden="true">
        <path d="M12 0C5.374 0 0 5.373 0 12c0 5.302 3.438 9.8 8.207 11.387.599.111.793-.261.793-.577v-2.234c-3.338.726-4.033-1.416-4.033-1.416-.546-1.387-1.333-1.756-1.333-1.756-1.089-.745.083-.729.083-.729 1.205.084 1.839 1.237 1.839 1.237 1.07 1.834 2.807 1.304 3.492.997.107-.775.418-1.305.762-1.604-2.665-.305-5.467-1.334-5.467-5.931 0-1.311.469-2.381 1.236-3.221-.124-.303-.535-1.524.117-3.176 0 0 1.008-.322 3.301 1.23A11.509 11.509 0 0112 5.803c1.02.005 2.047.138 3.006.404 2.291-1.552 3.297-1.23 3.297-1.23.653 1.653.242 2.874.118 3.176.77.84 1.235 1.911 1.235 3.221 0 4.609-2.807 5.624-5.479 5.921.43.372.823 1.102.823 2.222v3.293c0 .319.192.694.801.576C20.566 21.797 24 17.3 24 12c0-6.627-5.373-12-12-12z"/>
      </svg>
      <span>Login</span>
    `;
    login.addEventListener('click', () => {
      // Defer to existing auth-bar if present, else trigger OAuth popup hint
      if (window.AuthBar && typeof window.AuthBar.selectTab === 'function') {
        window.AuthBar.selectTab('login');
      } else {
        // Fallback: try to open the bottom AI dock login tab
        const authTab = document.getElementById('ai-dock__tab--login');
        if (authTab) authTab.click();
        else showToast('Sign in: open the Login tab in the AI dock (bottom of the page).');
      }
    });
    frag.appendChild(login);

    // Dashboard tab
    const dash = document.createElement('a');
    dash.className = 'nav-auth nav-auth--dashboard hidden';
    dash.id = 'nav-auth__dashboard';
    dash.setAttribute('data-nav-auth', 'dashboard');
    dash.href = 'https://neohiro.github.io/dashboard/';
    dash.innerHTML = `
      <svg viewBox="0 0 20 20" fill="currentColor" width="14" height="14" aria-hidden="true">
        <path fill-rule="evenodd" d="M3 3a1 1 0 000 2v8a2 2 0 002 2h2.586l-1.293 1.293a1 1 0 101.414 1.414L10 15.414l2.293 2.293a1 1 0 001.414-1.414L12.414 15H15a2 2 0 002-2V5a1 1 0 100-2H3zm11.707 4.707a1 1 0 00-1.414-1.414L10 9.586 8.707 8.293a1 1 0 00-1.414 0l-2 2a1 1 0 101.414 1.414L8 10.414l1.293 1.293a1 1 0 001.414 0l4-4z" clip-rule="evenodd"/>
      </svg>
      <span>Dashboard</span>
    `;
    frag.appendChild(dash);

    // User tab (shown when signed in)
    const user = document.createElement('a');
    user.className = 'nav-auth nav-auth--user hidden';
    user.id = 'nav-auth__user';
    user.setAttribute('data-nav-auth', 'user');
    user.href = 'https://neohiro.github.io/dashboard/';
    user.innerHTML = `
      <img id="nav-auth__avatar" src="" alt="" />
      <span id="nav-auth__name"></span>
      <span id="nav-auth__role" class="role-badge"></span>
    `;
    frag.appendChild(user);

    // Insert before the sponsor link if present, else at the end
    const sponsor = nav.querySelector('.nav-sponsor');
    if (sponsor) nav.insertBefore(frag, sponsor);
    else nav.appendChild(frag);

    wireNavAuthControls();

    // Sync with auth-bar's existing session if any
    syncAuthFromBar();
  }

  // One delegated handler for the Login control, whether it was just injected or
  // came from nav.html. Guarded by a data flag so repeated boots cannot stack
  // duplicate listeners on the same element.
  function wireNavAuthControls() {
    var login = document.getElementById('nav-auth__login');
    if (login && !login.dataset.navAuthWired) {
      login.dataset.navAuthWired = '1';
      login.addEventListener('click', function () {
        if (window.AuthBar && typeof window.AuthBar.selectTab === 'function') {
          window.AuthBar.selectTab('login');
        } else {
          var authTab = document.getElementById('ai-dock__tab--login');
          if (authTab) authTab.click();
          else showToast('Sign in with the Login button in the top bar.');
        }
      });
    }
  }

  function syncAuthFromBar() {
    try {
      const raw = localStorage.getItem('neohiro_session_v1');
      if (!raw) { showLoggedOutNav(); return; }
      const s = JSON.parse(raw);
      if (!s || !s.login || !Number.isFinite(s.expiresAt) || s.expiresAt < Date.now()) {
        localStorage.removeItem('neohiro_session_v1');
        showLoggedOutNav();
        return;
      }
      showUserNav(s);
    } catch (_) { showLoggedOutNav(); }
  }

  function showUserNav(s) {
    const login = document.getElementById('nav-auth__login');
    const dash = document.getElementById('nav-auth__dashboard');
    const user = document.getElementById('nav-auth__user');
    if (login) login.classList.add('hidden');
    if (dash) dash.classList.remove('hidden');
    if (user) {
      user.classList.remove('hidden');
      const av = document.getElementById('nav-auth__avatar');
      const nm = document.getElementById('nav-auth__name');
      const ro = document.getElementById('nav-auth__role');
      if (av) {
        var avUrl = s.avatar_url || '';
        if (avUrl) {
          av.src = avUrl + (avUrl.indexOf('?') >= 0 ? '&' : '?') + 's=40';
          av.alt = (s.login || 'user') + ' avatar';
        } else {
          av.removeAttribute('src');
          av.alt = '';
        }
      }
      if (nm) nm.textContent = s.login || 'user';
      if (ro) {
        const r = s.role || (s.login === 'neohiro' ? 'godadmin' : 'user');
        ro.textContent = r;
        ro.className = 'role-badge role-badge--' + r;
      }
    }
    _navAuthSuppress = 1;
    window.dispatchEvent(new CustomEvent('neohiro:nav-auth', { detail: { session: s } }));
  }

  // ── Cross-script hook: allow auth-bar to trigger nav update ──
  // Guard against feedback: showUserNav/showLoggedOutNav dispatch this same
  // event after mutating DOM, so the listener must suppress self-dispatches.
  var _navAuthSuppress = 0;
  window.addEventListener('neohiro:nav-auth', (e) => {
    if (_navAuthSuppress) { _navAuthSuppress = 0; return; }
    if (e.detail && e.detail.session) showUserNav(e.detail.session);
    else showLoggedOutNav();
  });
  // Auth-bar stores session in localStorage under 'neohiro_session_v1'.
  // Sync on `storage` events (cross-tab) and on focus/visibility (same-tab after OAuth).
  try {
    window.addEventListener('storage', (e) => {
      if (e.key === 'neohiro_session_v1') syncAuthFromBar();
    });
    document.addEventListener('visibilitychange', () => {
      if (document.visibilityState === 'visible') syncAuthFromBar();
    });
    window.addEventListener('pageshow', () => syncAuthFromBar());
  } catch (_) { /* older browsers */ }

  function showLoggedOutNav() {
    const login = document.getElementById('nav-auth__login');
    const dash  = document.getElementById('nav-auth__dashboard');
    const user  = document.getElementById('nav-auth__user');
    if (login) login.classList.remove('hidden');
    if (dash)  dash.classList.add('hidden');
    if (user)  user.classList.add('hidden');
    _navAuthSuppress = 1;
    window.dispatchEvent(new CustomEvent('neohiro:nav-auth', { detail: { session: null } }));
  }

  // ── Diagnostics probe ─────────────────────────────────────────
  // Fires once on boot, logs a structured health block to the console,
  // and exposes NEohiro.diagnose() so godadmins can call it from the
  // devtools console without inspecting network tab.
  //
  // Probes: localStorage, sessionStorage, Heart endpoint, Mouth endpoint,
  // GH Pages branch, Tailscale, network-ux.js self-integrity.
  // Results are written to window.NEohiro._lastDiag for tab-inspection.
  // If running on neohiro.github.io with godadmin session, also injects
  // a one-line [Diagnostics] status into the nav-auth area.
  function runDiagnostics() {
    var d = {
      ts: new Date().toISOString(),
      host: location.hostname,
      version: '1.0.0',
      storage: { local: false, session: false },
      network: { heart: null, mouth: null, ghPages: null, tailscale: null, uxSelf: null }
    };
    try { localStorage.setItem('_diag', '1'); localStorage.removeItem('_diag'); d.storage.local = true; } catch (_) {}
    try { sessionStorage.setItem('_diag', '1'); sessionStorage.removeItem('_diag'); d.storage.session = true; } catch (_) {}
    function probe(label, url, ms) {
      return fetchWithTimeout(url, { cache: 'no-store' }, ms)
        .then(function (r) { return { label: label, ok: r.ok, status: r.status }; })
        .catch(function (e) { return { label: label, ok: false, status: 0, err: e.message }; });
    }
    Promise.all([
      probe('heart', HEART_ENDPOINTS[0], 5000),
      probe('mouth', MOUTH_ENDPOINT + '?q=test', 5000),
      probe('gh-pages', 'https://neohiro.github.io/', 5000),
      probe('tailscale', 'https://neohiro.github.io/.well-known/tailscale', 5000),
      // ux-self: probe the current page's network-ux.js (relative) to detect CDN staleness
      probe('ux-self', 'assets/js/network-ux.js', 5000)
    ]).then(function (results) {
      d.network.heart = results[0];
      d.network.mouth = results[1];
      d.network.ghPages = results[2];
      d.network.tailscale = results[3];
      d.network.uxSelf = results[4];
      NEohiro._lastDiag = d;
      if (typeof console !== 'undefined' && console.groupCollapsed) {
        var lines = ['[NEohiro Diagnostics] ' + d.ts];
        lines.push('  localStorage : ' + (d.storage.local ? 'OK' : 'BLOCKED'));
        lines.push('  sessionStorage: ' + (d.storage.session ? 'OK' : 'BLOCKED'));
        lines.push('  Heart        : ' + (d.network.heart.ok ? 'UP ' + d.network.heart.status : 'DOWN (' + (d.network.heart.err || d.network.heart.status) + ')'));
        lines.push('  Mouth        : ' + (d.network.mouth.ok ? 'UP ' + d.network.mouth.status : 'DOWN (' + (d.network.mouth.err || d.network.mouth.status) + ')'));
        lines.push('  GH Pages     : ' + (d.network.ghPages.ok ? 'UP ' + d.network.ghPages.status : 'DOWN (' + (d.network.ghPages.err || d.network.ghPages.status) + ')'));
        lines.push('  Tailscale    : ' + (d.network.tailscale.ok ? 'UP ' + d.network.tailscale.status : 'DOWN (' + (d.network.tailscale.err || d.network.tailscale.status) + ')'));
        lines.push('  UX Self      : ' + (d.network.uxSelf.ok ? 'UP ' + d.network.uxSelf.status : 'DOWN (' + (d.network.uxSelf.err || d.network.uxSelf.status) + ')'));
        lines.push('  Full report : NEohiro.diagnose() in console');
        console.groupCollapsed.apply(console, lines);
        console.log('NEohiro diagnostic payload:', JSON.stringify(d, null, 2));
        console.groupEnd();
      }
      // Godadmin inline status (only on neohiro.github.io with godadmin session)
      try {
        var raw = localStorage.getItem('neohiro_session_v1');
        if (raw && location.hostname === 'neohiro.github.io') {
          var s = JSON.parse(raw);
          if (s && s.role === 'godadmin') {
            injectDiagStatus(d);
          }
        }
      } catch (_) {}
    });
  }

  function injectDiagStatus(d) {
    var wrap = document.getElementById('nav-auth__user') || document.getElementById('nav-auth__dashboard') || document.getElementById('nav-auth__login');
    if (!wrap) return;
    var up = [d.network.heart, d.network.mouth, d.network.ghPages, d.network.tailscale, d.network.uxSelf].filter(function (r) { return r && r.ok; }).length;
    var total = 5;
    var el = document.createElement('span');
    el.className = 'diag-status';
    el.style.cssText = 'margin-left:8px;font-family:var(--font-mono,monospace);font-size:0.65rem;padding:2px 6px;border-radius:4px;background:' + (up === total ? 'var(--green,#66bb6a)' : up >= 3 ? 'var(--amber,#ffb74d)' : 'var(--red,#ef5350)') + ';color:#fff;';
    el.textContent = '[Diagnostics: ' + up + '/' + total + ' up]';
    el.title = 'Full report: NEohiro.diagnose() in console';
    wrap.parentNode.insertBefore(el, wrap.nextSibling);
  }

  NEohiro.diagnose = function () { return NEohiro._lastDiag || null; };

  /* ── Mainframe status indicator (bottom bar) ────────────────────────
     Probes the Heart endpoint to determine if the mainframe is online.
     Updates the status dot in the bottom bar every 30 seconds.
     Uses the same fallback logic as probeHeart() for robustness. */
  function startMainframeStatusProbe() {
    var dot = document.getElementById('bottom-bar__status-dot');
    var text = document.getElementById('bottom-bar__status-text');
    if (!dot || !text) return;

    var _statusProbed = false;
    var _statusUp = null;
    var _statusProbePromise = null;
    var _statusInterval = null;

    function probe() {
      if (_statusProbePromise) return _statusProbePromise;
      // Allow re-probe if previous attempt failed (_statusUp === false).
      // Only short-circuit if we have a positive result cached.
      if (_statusProbed && _statusUp) return Promise.resolve(_statusUp);
      _statusProbed = true;
      _statusProbePromise = HEART_ENDPOINTS.reduce(function (promise, url) {
        return promise.catch(function () {
          return fetchWithTimeout(url, { cache: 'no-store', mode: 'cors' }, 8000)
            .then(function (r) { return r && r.ok; });
        });
      }, Promise.reject(new Error('no endpoints')))
        .then(function (up) { _statusUp = up; return up; })
        .catch(function () { _statusUp = false; return false; })
        .finally(function () { _statusProbePromise = null; });
      return _statusProbePromise;
    }

    function updateUI(online) {
      if (online) {
        dot.style.background = 'var(--green, #66bb6a)';
        dot.style.boxShadow = '0 0 6px var(--green, #66bb6a)';
        text.textContent = 'Mainframe online';
      } else {
        dot.style.background = 'var(--red, #ef5350)';
        dot.style.boxShadow = '0 0 6px var(--red, #ef5350)';
        text.textContent = 'Mainframe offline';
      }
    }

    function scheduleNext() {
      if (_statusInterval) clearInterval(_statusInterval);
      _statusInterval = setInterval(function () {
        probe().then(updateUI);
      }, 30000);
    }

    // Initial probe
    probe().then(updateUI).then(scheduleNext);

    // Cleanup on page unload
    window.addEventListener('pagehide', function cleanup() {
      if (_statusInterval) clearInterval(_statusInterval);
      window.removeEventListener('pagehide', cleanup);
    }, { once: true });
  }

  // Start the mainframe status probe after a short delay
  setTimeout(startMainframeStatusProbe, 2000);

  // Expose
  window.NEohiro = NEohiro;

  // Self-start.
  //
  // This line is the one the module shipped without: init() was defined and
  // exposed on window.NEohiro, and nothing -- not the layout, not another
  // script -- ever called it. Every feature below therefore never mounted on
  // any of the four sites: no conversation sheet, no assistant/voicemail bar,
  // no nav auth slot, no ripples. It failed silently because the absence of an
  // element is not an error.
  //
  // Scripts are loaded with `defer`, so readyState is normally 'interactive' by
  // the time this runs; init() also handles the 'loading' case by waiting for
  // DOMContentLoaded, and is idempotent, so a second call is harmless.
  init();
})();

