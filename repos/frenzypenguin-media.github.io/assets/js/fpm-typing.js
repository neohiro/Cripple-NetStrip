// Copyright (c) 2026 FrenzyPenguin Media. All rights reserved.
//
// ═══════════════════════════════════════════════════════════════════════
//  TYPING ANIMATION — creative FPM/neohiro quote rotator
// ═══════════════════════════════════════════════════════════════════════
//
// Renders a "thinking" placeholder that:
//   • types out a creative FPM/neohiro-flavored quote (relatively fast)
//   • dwells (slow + long) so the visitor can read it
//   • deletes quickly (snap)
//   • types a different "correction" quote in (variation)
//
// This is the prompt-field placeholder used on neohiro.github.io and
// frenzypenguin-media.github.io. Visitors see one of these rotating
// blurbs until they start typing.
//
// Dynamic strings (admin-triggered via /strings) are layered ON TOP of
// this list — see dynamic_strings.js for the cooldown + persistence.
//
// Zero dependencies. Works in any modern browser.
// ═══════════════════════════════════════════════════════════════════════

(function (global) {
    'use strict';

    // ─── Brand quotes ────────────────────────────────────────────────
    // All in the FPM / neohiro voice: short, intentional, slightly weird.
    // Punctuation stripped to keep the typing speed consistent.
    const QUOTES = [
        'Tell me what you like',
        'Ask me about your day',
        'Wonder out loud — I am listening',
        'Make a wish — I will sort it',
        'Say the awkward thing',
        'Type the question you would never ask',
        'Brain is online — go ahead',
        'Mouth is warming up',
        'What did you forget',
        'A thought is a small adventure',
        'Type the first thing that bothers you',
        'There is no wrong prompt here',
        'Ask anything — even the silly stuff',
        'Make today slightly less heavy',
        'Curiosity is always welcome',
        'Type the thing on your mind',
        'A quick yes-or-no is fine too',
        'Your day — summarised in one line',
        'What would be useful right now',
        'Speak the words you have been chewing on',
        'Your heartbeat has a question — type it',
        'The Mouth is ready when you are',
        'Even a one-word prompt counts',
        'What is the next brave step',
        'Type the request you have been postponing',
    ];

    // ─── "Corrections" — the second-typed quote (a deliberate misdirect) ──
    // Cycle matches QUOTES index. Each "correction" is the polished restatement
    // of the typed-out line. Kept short so the retyping finishes quickly.
    const CORRECTIONS = [
        'Tell me what you like',
        'Ask me about your day',
        'Wonder out loud — I am listening',
        'Make a wish — I will sort it',
        'Say the awkward thing',
        'Type the question you would never ask',
        'Brain is online — go ahead',
        'Mouth is warming up',
        'What did you forget',
        'A thought is a small adventure',
        'Type the first thing that bothers you',
        'There is no wrong prompt here',
        'Ask anything — even the silly stuff',
        'Make today slightly less heavy',
        'Curiosity is always welcome',
        'Type the thing on your mind',
        'A quick yes-or-no is fine too',
        'Your day — summarised in one line',
        'What would be useful right now',
        'Speak the words you have been chewing on',
        'Your heartbeat has a question — type it',
        'The Mouth is ready when you are',
        'Even a one-word prompt counts',
        'What is the next brave step',
        'Type the request you have been postponing',
    ];

    // ─── Timing (ms) — tuned for "relatively fast type / slow long stay / quick delete" ──
    const TYPING_DELAY = 32;     // per character when typing
    const DELETE_DELAY = 14;     // per character when deleting
    const DWELL_MIN = 4200;      // how long the typed quote stays
    const DWELL_JITTER = 1200;   // +/- random extra dwell
    const RETYPE_DELAY = 180;    // pause between delete and re-typing the correction
    const INITIAL_DELAY = 240;   // before the very first quote starts typing

    // ─── Public API ───────────────────────────────────────────────────
    function startTypingAnimation(target, opts) {
        if (typeof target === 'string') target = document.querySelector(target);
        if (!target) return null;
        opts = opts || {};

        const dynamic = Array.isArray(opts.dynamicQuotes) ? opts.dynamicQuotes : null;
        const dynamicCorrections = Array.isArray(opts.dynamicCorrections) ? opts.dynamicCorrections : null;

        let active = true;
        let charIndex = 0;
        let quoteIndex = Math.floor(Math.random() * QUOTES.length);
        let timer = null;
        let currentFull = '';
        let currentCorrection = '';
        let mode = 'type'; // 'type' | 'dwell' | 'delete' | 'retype' | 'dwell2'

        function pickQuote(i) {
            if (dynamic && dynamic.length) {
                return dynamic[i % dynamic.length];
            }
            return QUOTES[i % QUOTES.length];
        }
        function pickCorrection(i) {
            if (dynamicCorrections && dynamicCorrections.length) {
                return dynamicCorrections[i % dynamicCorrections.length];
            }
            return CORRECTIONS[i % CORRECTIONS.length];
        }

        function setText(s) {
            // Cheap, idempotent — only writes if changed.
            if (target.textContent !== s) target.textContent = s;
        }

        function tick() {
            if (!active) return;
            if (mode === 'type') {
                if (charIndex <= currentFull.length) {
                    setText(currentFull.slice(0, charIndex));
                    charIndex++;
                    timer = setTimeout(tick, TYPING_DELAY);
                } else {
                    mode = 'dwell';
                    const dwell = DWELL_MIN + Math.floor(Math.random() * DWELL_JITTER);
                    timer = setTimeout(tick, dwell);
                }
            } else if (mode === 'dwell') {
                mode = 'delete';
                charIndex = currentFull.length;
                timer = setTimeout(tick, DELETE_DELAY);
            } else if (mode === 'delete') {
                if (charIndex > 0) {
                    charIndex--;
                    setText(currentFull.slice(0, charIndex));
                    timer = setTimeout(tick, DELETE_DELAY);
                } else {
                    mode = 'retype';
                    charIndex = 0;
                    currentFull = currentCorrection;
                    timer = setTimeout(tick, RETYPE_DELAY);
                }
            } else if (mode === 'retype') {
                if (charIndex <= currentFull.length) {
                    setText(currentFull.slice(0, charIndex));
                    charIndex++;
                    timer = setTimeout(tick, TYPING_DELAY);
                } else {
                    mode = 'dwell2';
                    const dwell = (DWELL_MIN * 0.7) + Math.floor(Math.random() * DWELL_JITTER);
                    timer = setTimeout(tick, dwell);
                }
            } else if (mode === 'dwell2') {
                // Move to the next quote pair, restart
                quoteIndex = (quoteIndex + 1 + Math.floor(Math.random() * 3)) % (dynamic ? dynamic.length : QUOTES.length);
                currentFull = pickQuote(quoteIndex);
                currentCorrection = pickCorrection(quoteIndex);
                charIndex = 0;
                mode = 'type';
                timer = setTimeout(tick, TYPING_DELAY * 2);
            }
        }

        // Initial state
        currentFull = pickQuote(quoteIndex);
        currentCorrection = pickCorrection(quoteIndex);
        charIndex = 0;
        mode = 'type';
        setText('');
        timer = setTimeout(tick, INITIAL_DELAY);

        return {
            stop: function () {
                active = false;
                if (timer) { clearTimeout(timer); timer = null; }
            },
            refresh: function (newDynamicQuotes, newDynamicCorrections) {
                opts.dynamicQuotes = newDynamicQuotes || opts.dynamicQuotes;
                opts.dynamicCorrections = newDynamicCorrections || opts.dynamicCorrections;
                // Force-rotate to the new set on next dwell2
                if (mode === 'dwell2' || mode === 'dwell') {
                    mode = 'dwell2';
                }
            },
        };
    }

    // ─── Auto-attach ────────────────────────────────────────────────
    //   <input data-fpm-typing-placeholder>  or
    //   <textarea data-fpm-typing-placeholder>
    // The element's `placeholder` attr is replaced with a live-typing span.
    function autoAttach(opts) {
        opts = opts || {};
        const els = document.querySelectorAll('[data-fpm-typing-placeholder]');
        const instances = [];
        els.forEach((el) => {
            // Create a span mirror placed just before the input, or
            // attach the typing to the element's own value via a data attr
            // so screen readers still see the static placeholder.
            if (!el.dataset.fpmStatic) el.dataset.fpmStatic = el.placeholder || '';
            const id = el.id || ('fpm-typing-' + Math.random().toString(36).slice(2, 8));
            el.id = id;
            let mirror = document.getElementById(id + '-mirror');
            if (!mirror) {
                mirror = document.createElement('span');
                mirror.id = id + '-mirror';
                mirror.className = (opts.mirrorClass || 'fpm-typing-mirror');
                mirror.setAttribute('aria-hidden', 'true');
                el.setAttribute('aria-label', el.dataset.fpmStatic);
                el.placeholder = '';
                // Position the mirror in the same wrapper as the input
                const wrapper = el.parentNode;
                wrapper.insertBefore(mirror, el);
            }
            const inst = startTypingAnimation(mirror, opts);
            if (inst) instances.push({ el, inst });
        });
        return instances;
    }

    // ─── Expose ──────────────────────────────────────────────────────
    global.FpmTyping = {
        start: startTypingAnimation,
        autoAttach: autoAttach,
        QUOTES: QUOTES,
        CORRECTIONS: CORRECTIONS,
    };

    // ─── Dynamic Strings Poller ─────────────────────────────────────
    //   Fetches the admin's active strings for this scope and pushes them
    //   into every active typing animation via .refresh(). Falls back to
    //   the static list if the endpoint is unavailable.
    //   The scope is read from <body data-fpm-scope="..."> or window.FPM_SCOPE.
    function startDynamicPoller(opts) {
        opts = opts || {};
        const endpoint = opts.endpoint || '/api/strings';
        const scope = opts.scope
            || (document.body && document.body.dataset.fpmScope)
            || (typeof window !== 'undefined' && window.FPM_SCOPE)
            || 'fpm';
        const baseInterval = Math.max(30_000, parseInt(opts.intervalMs, 10) || 60_000);
        let currentInterval = baseInterval;
        let lastSig = '';
        let activeInstances = opts.instances || [];
        let backoff = 1; // exponent for transient fetch failures

        async function tick() {
            try {
                const r = await fetch(endpoint + '?scope=' + encodeURIComponent(scope), {
                    method: 'GET',
                    credentials: 'omit',
                    cache: 'no-store',
                });
                if (!r.ok) { backoff = Math.min(backoff + 1, 6); currentInterval = baseInterval * backoff; return; }
                const data = await r.json();
                backoff = 1; // reset on success
                currentInterval = baseInterval;
                if (!data || !data.ok || !Array.isArray(data.strings) || !data.strings.length) {
                    if (lastSig !== '__static__') {
                        lastSig = '__static__';
                        activeInstances.forEach(({ inst }) => inst && inst.refresh(null, null));
                    }
                    return;
                }
                const quotes = data.strings.map(s => s.quote);
                const corrections = data.strings.map(s => s.correction || s.quote);
                const sig = quotes.join('|');
                if (sig === lastSig) return;
                lastSig = sig;
                activeInstances.forEach(({ inst }) => inst && inst.refresh(quotes, corrections));
            } catch (_) {
                // Offline / CORS: back off so we don't hammer the endpoint
                backoff = Math.min(backoff + 1, 6);
                currentInterval = baseInterval * backoff;
            }
        }

        async function schedule() {
            await tick();
            if (!_stopped) nextTimer = setTimeout(schedule, currentInterval);
        }

        // Initial + interval. Errors are silent; the poller retries.
        let nextTimer = null;
        let _stopped = false;
        schedule();
        return {
            stop: () => { _stopped = true; if (nextTimer) { clearTimeout(nextTimer); nextTimer = null; } },
            setInstances: (arr) => { activeInstances = arr || []; },
        };
    }

    global.FpmTyping.startPoller = startDynamicPoller;
})(typeof window !== 'undefined' ? window : globalThis);
