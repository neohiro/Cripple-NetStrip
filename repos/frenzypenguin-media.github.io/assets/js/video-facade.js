/* video-facade.js — turns the server-rendered cards in
 * _includes/video-facade.html into players, on click only.
 *
 * Loaded deferred on pages that carry a video wall. Does nothing until a card
 * is activated, and does nothing at all if the DOM has no cards, so pages
 * without a wall pay only the request.
 *
 * Progressive enhancement by construction: each card is a real <a href> to
 * youtube.com before this file runs. Everything here is an upgrade, so a JS
 * failure leaves working links rather than dead boxes.
 */
(function () {
  'use strict';

  var CARDS = '.vfacade__hit';

  /* How long to wait for the embed to prove it can actually play.
     The iframe fires `load` even when the content is refused -- a blocked
     frame-src, a captive portal, a YouTube outage -- so `load` alone cannot be
     trusted to mean "the video is playing". */
  var MOUNT_GRACE_MS = 1200;

  function mount(card) {
    var iframe = document.createElement('iframe');
    var src = card.getAttribute('data-embed-src');
    var title = card.getAttribute('data-video-title') || 'YouTube video';

    iframe.src = src;
    iframe.title = title;
    iframe.className = 'vfacade__iframe';
    iframe.allow = 'accelerometer; autoplay; clipboard-write; encrypted-media; gyroscope; picture-in-picture; web-share';
    iframe.setAttribute('allowfullscreen', '');
    iframe.setAttribute('loading', 'lazy');
    // youtube-nocookie still runs first-party storage in some paths; tell the
    // browser to keep it out of third-party storage.
    iframe.referrerPolicy = 'strict-origin-when-cross-origin';

    var frame = card.querySelector('.vfacade__frame');
    if (frame) frame.appendChild(iframe);

    // Do NOT strip href yet. An earlier version removed it immediately, which
    // was a one-way door: if the embed then failed to play -- blocked by CSP, a
    // network that drops YouTube, an outage -- the card had been converted from
    // a working link into a dead box with no way back to the video. The link is
    // only given up once the frame has had a moment to render, and a persistent
    // "watch on YouTube" escape hatch is added so the visitor is never trapped.
    var settled = false;
    var grace = window.setTimeout(function () { settle(); }, MOUNT_GRACE_MS);
    iframe.addEventListener('load', function () { settle(); }, { once: true });

    function settle() {
      if (settled) return;
      settled = true;
      window.clearTimeout(grace);

      // The card is now a player, not a link. Leaving an <a href> on top would
      // put a link over the video that swallows the first click on the controls.
      card.setAttribute('aria-expanded', 'true');
      card.classList.add('vfacade__hit--playing');
      card.removeAttribute('href');
      card.setAttribute('role', 'button');
      // Stop the click that activated the card from reaching the freshly
      // inserted iframe, and stop the browser treating a bare <a> as a link.
      card.addEventListener('click', function (e) { e.preventDefault(); }, { passive: false });

      addEscapeHatch(card, title);
    }
  }

  /* A real link out, always present once a card is playing.
     If the embed is refused or stalls, this is the only way back to the video,
     and it is also the honest affordance for a visitor who does not want an
     embedded player at all. */
  function addEscapeHatch(card, title) {
    if (card.querySelector('.vfacade__escape')) return;
    var watch = card.getAttribute('data-watch-url');
    if (!watch) return;

    var a = document.createElement('a');
    a.className = 'vfacade__escape';
    a.href = watch;
    a.target = '_blank';
    a.rel = 'noopener noreferrer';
    a.textContent = 'Watch on YouTube';
    // Distinguishable by assistive tech from the player controls it sits over.
    a.setAttribute('aria-label', 'Open "' + title + '" on YouTube in a new tab');
    card.appendChild(a);
  }

  /* Closest ancestor matching `selector`, or null.
     `e.target` for a click is normally an Element, but it is not guaranteed to
     be one across every engine and every synthetic event, and a bare `.closest`
     call on something without the method throws inside the handler. One helper,
     used for every lookup, so the guard cannot be forgotten on one path. */
  function ancestorOf(node, selector) {
    return node && typeof node.closest === 'function' ? node.closest(selector) : null;
  }

  function activate(e) {
    // Let the visitor open it on YouTube instead: middle-click,
    // ctrl/cmd-click, shift-click.
    if (e.metaKey || e.ctrlKey || e.shiftKey || e.altKey || e.button !== 0) return;

    // The escape hatch lives INSIDE the card and is a real <a href> to
    // youtube.com. It has to be excluded before the card is considered, or the
    // card's preventDefault below would swallow the navigation and the one
    // remaining route out of a failed embed would stop working. Specific before
    // general, on purpose.
    if (ancestorOf(e.target, '.vfacade__escape')) return;

    var card = ancestorOf(e.target, CARDS);
    if (!card) return;
    // Already playing: do not stack iframes if the card is re-activated.
    if (card.getAttribute('aria-expanded') === 'true') return;

    e.preventDefault();
    mount(card);
  }

  function init() {
    /* Delegated on the document, once, rather than one listener per card.
       Two reasons, both learned the hard way:
         - Cards added to the DOM after this runs would otherwise stay dead.
           network-ux.js rewrites the nav from a fetch, so "the cards that exist
           now" is not a safe assumption on this site.
         - A per-card loop that runs before the cards are parsed silently loses
           the visitor's first click. Delegation has no ordering dependency:
           the cards are in the static HTML, so by the time anyone can click one
           this listener is already attached. */
    document.addEventListener('click', activate);

    // Keyboard: a focused card is an <a href>, so Enter and Space already work
    // natively and this listener must not double-handle them -- it exists only
    // for the case where the card has already been settled into a player and
    // its href is gone, so the key would otherwise do nothing at all. Same
    // ancestorOf helper, and the same escape-hatch exclusion.
    document.addEventListener('keydown', function (e) {
      if (e.key !== 'Enter' && e.key !== ' ' && e.key !== 'Spacebar') return;
      if (ancestorOf(e.target, '.vfacade__escape')) return;
      var card = ancestorOf(e.target, CARDS);
      if (!card || card.getAttribute('aria-expanded') === 'true') return;
      e.preventDefault();
      mount(card);
    });
  }

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', init, { once: true });
  } else {
    init();
  }
})();
