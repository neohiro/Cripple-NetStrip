/* ==========================================================================
   nav-rail.js — decides between the raster bar and the two-row rail.

   Contract (shared across neohiro / frenzypenguin-media / openstageisland /
   transhumanists): this file and nav-raster.css are byte-identical in all four
   sites and are the only things that should need editing to change how the top
   bar fits. They are additive: main.css and nav.html are untouched, so a site
   that does not load them keeps its current bar, and with no JS at all the bar
   stays in raster mode, which fits.

   WHAT IT DOES
   1. Splits the bar into two buckets inside .site-nav:
        .nav-rail__track   the plain section links. The only thing that pans.
        .nav-rail__fixed   Hosts, Community, the auth slot, Sponsor and the
                           GitHub glyph. Never pans.
      In raster mode both buckets are display:contents, so .site-nav keeps
      behaving exactly as it did, every existing .site-nav selector in main.css
      and network-ux.css still matches, and the wrappers cost nothing.

   2. Chooses a mode:
        RAIL   when the visible links reach RAIL_MIN_ITEMS, or when the raster
               would need more than one row.
        RASTER otherwise.

   3. Re-evaluates on resize, on webfont load, and whenever the auth slot
      changes shape, because login / avatar / dashboard swap widths and can be
      what tips the bar over.

   4. Keeps the arrows honest: disabled at each end, one tile per press.

   WHY THE MENUS ARE NOT IN THE TRACK
   The obvious design scrolls the whole nav. It does not work.
   .nav-dropdown-menu in main.css is position:absolute; top:calc(100% + 8px), so
   putting it inside an overflow-x:auto box breaks it twice over: overflow-y is
   forced to clip the menu, which makes Hosts and Community impossible to open,
   and the menu's width is counted into scrollWidth, which invented over a
   thousand pixels of empty track past the last real tile. A first attempt made
   the menus position:fixed and placed them from JS; that works, but it has to
   re-place on every pan and fights the sticky header for coordinate space.

   Keeping the dropdown wrappers out of the scroller sidesteps all of it. The
   track then holds only leaf anchors with no positioned descendants, so its
   scrollWidth is exact and nothing is ever clipped. The price is that Hosts and
   Community do not pan, which is the right trade anyway: they are menus, not
   destinations, and a menu that pans off-screen is a menu nobody can use.
   ========================================================================== */
(function () {
  'use strict';

  /* Seven visible links is where the raster stops reading as a row of tabs and
   * starts reading as a list. Below that, wrapping is kinder than panning. */
  var RAIL_MIN_ITEMS = 7;

  /* px of extra height tolerated before calling a second row a wrap. Guards
   * against subpixel row heights reporting a wrap that is not there. */
  var WRAP_SLACK = 4;

  /* px of slack when deciding whether an end has been reached. Fractional
   * layout widths otherwise leave the arrow disabled at the end even though
   * there is a subpixel or two left to move. */
  var END_SLACK = 2;

  var reduceMotion = window.matchMedia
    ? window.matchMedia('(prefers-reduced-motion: reduce)')
    : { matches: false };

  function isShown(el) {
    var cs = window.getComputedStyle(el);
    return cs.display !== 'none' && !el.classList.contains('hidden');
  }

  function shown(list) {
    return Array.prototype.filter.call(list, isShown);
  }

  /* Plain section links pan. Everything else stays pinned: a menu has to stay
   * reachable, and the nav.html contract pins auth, Sponsor and the GitHub
   * glyph to the right end. */
  function pans(el) {
    if (el.classList.contains('nav-dropdown')) return false;
    if (el.classList.contains('nav-auth')) return false;
    return isShown(el);
  }

  function makeArrow(modifier, label) {
    var b = document.createElement('button');
    b.type = 'button';
    b.className = 'nav-rail__arrow nav-rail__arrow--' + modifier;
    b.setAttribute('aria-label', label);
    return b;
  }

  function build(navEl) {
    if (navEl.__railBuilt) return;
    var trackWrapper = document.createElement('div');
    trackWrapper.className = 'nav-rail__track-wrapper';
    var track = document.createElement('div');
    track.className = 'nav-rail__track';
    trackWrapper.appendChild(track);
    var fixed = document.createElement('div');
    fixed.className = 'nav-rail__fixed';

    var prev = makeArrow('prev', 'Scroll navigation left');
    var next = makeArrow('next', 'Scroll navigation right');

    /* Partition first, so each bucket keeps the order nav.html specifies. */
    var kids = [];
    Array.prototype.forEach.call(navEl.childNodes, function (node) {
      if (node.nodeType === 1) kids.push(node);
    });
    var pan = [];
    var pin = [];
    kids.forEach(function (node) { (pans(node) ? pan : pin).push(node); });

    navEl.insertBefore(prev, navEl.firstChild);
    navEl.appendChild(trackWrapper);
    navEl.appendChild(fixed);
    navEl.appendChild(next);
    /* appendChild moves the node, so this empties .site-nav into the buckets. */
    pan.forEach(function (n) { track.appendChild(n); });
    pin.forEach(function (n) { fixed.appendChild(n); });

    navEl.__trackWrapper = trackWrapper;
    navEl.__track = track;
    navEl.__fixed = fixed;
    navEl.__railBuilt = true;

    prev.addEventListener('click', function () { step(navEl, -1); });
    next.addEventListener('click', function () { step(navEl, 1); });
  }

  function tiles(navEl) {
    return shown(navEl.__track.children);
  }

   /* One tile per press: the next tile that is not already fully visible.
      Forward looks for the first tile whose right edge is past the viewport;
      backward looks for the last tile already behind the left edge, or zero.

      Returns a pixel scrollLeft value (relative to the wrapper), or null when
      there is nothing to scroll in that direction. An earlier version looked
      for "the first tile whose left edge is past scrollLeft", which returned
      the tile already sitting at offsetLeft and so looked like a no-op:
      scroll-snap saw that tile as in view and pulled the track straight back.
      Asking for the first tile you cannot already see cannot no-op, and still
      cannot overshoot past it. */
  function targetFor(navEl, dir) {
    var items = tiles(navEl);
    var wrapper = navEl.__trackWrapper;
    var wrapperRect = wrapper.getBoundingClientRect();
    var left = wrapper.scrollLeft;
    var right = left + wrapper.clientWidth;
    if (dir > 0) {
      for (var i = 0; i < items.length; i++) {
        var itemRight = items[i].getBoundingClientRect().right - wrapperRect.left;
        if (itemRight > right + 1) {
          return items[i].getBoundingClientRect().left - wrapperRect.left;
        }
      }
      return null;
    }
    for (var j = items.length - 1; j >= 0; j--) {
      var itemLeft = items[j].getBoundingClientRect().left - wrapperRect.left;
      if (itemLeft < left - 1) {
        return itemLeft;
      }
    }
    return 0;
  }

  function step(navEl, dir) {
    if (!navEl.classList.contains('site-nav--rail')) return;
    var t = targetFor(navEl, dir);
    if (t === null) return;
    var wrapper = navEl.__trackWrapper;
    wrapper.scrollTo({
      left: t,
      behavior: reduceMotion.matches ? 'auto' : 'smooth'
    });
    window.requestAnimationFrame(function () { sync(navEl); });
  }

  function sync(navEl) {
    if (!navEl.classList.contains('site-nav--rail')) return;
    var wrapper = navEl.__trackWrapper;
    var max = wrapper.scrollWidth - wrapper.clientWidth;
    navEl.querySelector('.nav-rail__arrow--prev').disabled = wrapper.scrollLeft <= END_SLACK;
    navEl.querySelector('.nav-rail__arrow--next').disabled =
      max <= END_SLACK || wrapper.scrollLeft >= max - END_SLACK;
  }

  /* Raster wraps, so "would this need a second row" is answerable by measuring
   * the raster: if the bar is taller than its tallest single tile, it wrapped.
   * Callers drop rail mode before asking, so the buckets are display:contents
   * here and .site-nav really is the wrapping box. */
  function needsRail(navEl) {
    var items = tiles(navEl).concat(shown(navEl.__fixed.children));
    if (!items.length) return false;
    if (items.length >= RAIL_MIN_ITEMS) return true;
    var tallest = 0;
    items.forEach(function (el) {
      if (el.offsetHeight > tallest) tallest = el.offsetHeight;
    });
    return navEl.offsetHeight > tallest + WRAP_SLACK;
  }

  function apply(navEl) {
    var wrapper = navEl.__trackWrapper;
    var wasRail = navEl.classList.contains('site-nav--rail');
    if (wasRail) navEl.classList.remove('site-nav--rail');

    var rail = needsRail(navEl);
    if (rail) navEl.classList.add('site-nav--rail');

    /* Entering or leaving the rail resets the offset; coming out of it at a
     * stale scrollLeft would silently hide the first links. */
    if (wasRail !== rail) wrapper.scrollLeft = 0;
    sync(navEl);
  }

  function init() {
    var navEl = document.querySelector('.site-nav');
    if (!navEl) return;
    build(navEl);

    var pending = false;
    function schedule() {
      if (pending) return;
      pending = true;
      window.requestAnimationFrame(function () {
        pending = false;
        apply(navEl);
      });
    }

    window.addEventListener('resize', schedule, { passive: true });
    navEl.__trackWrapper.addEventListener('scroll', function () { sync(navEl); },
                                           { passive: true });

    /* The auth slot swaps between login, avatar and dashboard, which changes the
     * item count and the widths. Watch for it. */
    if (window.MutationObserver) {
      new window.MutationObserver(schedule).observe(navEl, {
        attributes: true, attributeFilter: ['class'],
        childList: true, subtree: true
      });
    }

    /* Keyboard panning, without hijacking normal tabbing: only the horizontal
     * arrows act, and only when the bar really is a rail. */
    navEl.__trackWrapper.addEventListener('keydown', function (e) {
      if (!navEl.classList.contains('site-nav--rail')) return;
      if (e.key === 'ArrowRight') { step(navEl, 1); e.preventDefault(); }
      else if (e.key === 'ArrowLeft') { step(navEl, -1); e.preventDefault(); }
    });

    schedule();

    /* Webfonts change tile widths after first paint, which can be the difference
     * between one row and two. Re-test once they have landed. */
    if (document.fonts && document.fonts.ready) {
      document.fonts.ready.then(schedule).catch(function () {});
    }
  }

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', init);
  } else {
    init();
  }
})();