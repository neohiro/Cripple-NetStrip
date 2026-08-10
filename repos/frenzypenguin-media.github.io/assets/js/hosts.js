/* =============================================================================
   assets/js/hosts.js — the swirl-open card controller.

   Contract with the markup (see assets/css/hosts.css §2):

     [data-swirl]                 the wrapper. Gets .swirl--open when opened.
     [data-swirl-toggle]          the source disc. Toggles its own card.
       aria-expanded              MUST track the real state, not the animation.
       aria-controls              id of the card in the SAME wrapper.
     [data-swirl-open="ID"]       any other element that opens the card whose
                                  id is ID. This is the "opens from another
                                  source" path: a link in the directory, a
                                  button in the page header, a deep link.

   Design rules, in order of importance:

     1. IT WORKS WITHOUT JS. The card's open state is also expressible in CSS
        (:target), and every trigger is a real control. If this file fails to
        load, the directory still renders and every link still navigates.
     2. STATE LIVES IN THE DOM, NOT IN A VARIABLE. .swirl--open is the single
        source of truth. Anything else can drift out of sync with the class.
     3. NO INJECTION. Everything here is textContent / setAttribute on nodes
        that already exist. Nothing is built from a string.
     4. A FRAGMENT (#swirl-<slug>) OPENS THAT CARD on load, so the open state
        is linkable and survives a reload.
     5. prefers-reduced-motion is honoured by adding .swirl--swirling only when
        motion is welcome; the CSS also hard-stops the animation, so this is
        belt and braces.
   ========================================================================== */

(function () {
  'use strict';

  var SWIRL_MS = 720;
  var reduceMotion = window.matchMedia
    ? window.matchMedia('(prefers-reduced-motion: reduce)')
    : { matches: false };

  /* ── helpers ─────────────────────────────────────────────────────────────── */

  function toggleFor(wrapper) {
    return wrapper ? wrapper.querySelector('[data-swirl-toggle]') : null;
  }

  /* aria-expanded is the promise made to assistive tech. If it ever disagrees
     with .swirl--open the two have drifted, so it is re-derived from the class
     rather than tracked separately. */
  function syncAria(wrapper) {
    var t = toggleFor(wrapper);
    if (!t) return;
    t.setAttribute('aria-expanded', wrapper.classList.contains('swirl--open') ? 'true' : 'false');
  }

  function open(wrapper) {
    if (!wrapper || wrapper.classList.contains('swirl--open')) return;
    wrapper.classList.add('swirl--swirling');
    wrapper.classList.add('swirl--open');
    syncAria(wrapper);
    if (reduceMotion.matches) {
      wrapper.classList.remove('swirl--swirling');
    } else {
      window.setTimeout(function () {
        wrapper.classList.remove('swirl--swirling');
      }, SWIRL_MS);
    }
  }

  function close(wrapper) {
    if (!wrapper || !wrapper.classList.contains('swirl--open')) return;
    wrapper.classList.remove('swirl--open');
    syncAria(wrapper);
  }

  /* ── 1. the source disc toggles its own card ────────────────────────────── */

  function bindToggles(root) {
    var toggles = root.querySelectorAll('[data-swirl-toggle]');
    for (var i = 0; i < toggles.length; i++) {
      toggles[i].addEventListener('click', function (ev) {
        var wrapper = ev.currentTarget.closest('[data-swirl]');
        if (!wrapper) return;
        if (wrapper.classList.contains('swirl--open')) {
          close(wrapper);
        } else {
          open(wrapper);
        }
      });
    }
  }

  /* ── 2. anything else on the page can open a card ───────────────────────── */

  function bindOpeners(root) {
    var openers = root.querySelectorAll('[data-swirl-open]');
    for (var i = 0; i < openers.length; i++) {
      openers[i].addEventListener('click', function (ev) {
        var card = document.getElementById(ev.currentTarget.getAttribute('data-swirl-open'));
        var wrapper = card ? card.closest('[data-swirl]') : null;
        if (!wrapper) return;
        // Only swallow the click when the card is not already on screen. If the
        // trigger lives on another page it is a plain link and must navigate.
        if (!card.getBoundingClientRect().height) {
          ev.preventDefault();
          open(wrapper);
          var toggle = toggleFor(wrapper);
          if (toggle) toggle.focus();
        }
      });
    }
  }

  /* ── 3. a #fragment opens the card it names ──────────────────────────────── */

  function openFromHash() {
    var id = (window.location.hash || '').replace(/^#/, '');
    if (!id || id === 'main' || id === 'content') return;
    var card = document.getElementById(id);
    if (!card || !card.closest('[data-swirl]')) return;
    open(card.closest('[data-swirl]'));
  }

  /* ── 4. open the cards on the way into view ───────────────────────────────
     The swirl is the page's arrival animation: a directory scrolls, and each
     card swirls open as it comes into view. One-shot — a card never closes
     again on scroll-out, because content that vanishes when you look away is
     worse than content that does not animate. */
  function bindReveal() {
    if (!('IntersectionObserver' in window)) return;
    var cards = document.querySelectorAll('[data-swirl]');
    if (!cards.length) return;
    var io = new IntersectionObserver(function (entries) {
      for (var i = 0; i < entries.length; i++) {
        if (!entries[i].isIntersecting) continue;
        open(entries[i].target);
        io.unobserve(entries[i].target);
      }
    }, { rootMargin: '0px 0px -8% 0px', threshold: 0.18 });
    for (var j = 0; j < cards.length; j++) io.observe(cards[j]);
  }

  /* ── boot ────────────────────────────────────────────────────────────────── */

  function init() {
    /* Seed every toggle's aria-expanded from the DOM, so a card opened by CSS
       (:target / a fragment) is announced correctly before any click. */
    var wrappers = document.querySelectorAll('[data-swirl]');
    for (var i = 0; i < wrappers.length; i++) {
      syncAria(wrappers[i]);
    }

    bindToggles(document);
    bindOpeners(document);
    bindReveal();
    openFromHash();

    /* #fragment navigation on the same page does not fire hashchange, so a
       link to another card on the current page needs this. */
    window.addEventListener('hashchange', openFromHash);
  }

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', init);
  } else {
    init();
  }
})();