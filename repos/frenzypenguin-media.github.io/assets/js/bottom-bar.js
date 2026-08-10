/* bottom-bar.js -- scroll affordances for the persistent bottom bar's chip strip.
 *
 * Open Stage Island ships fifteen in-page section chips, which is wider than a
 * phone viewport and wider than a laptop at 100% zoom. The strip therefore has to
 * scroll, and a strip that scrolls with no visible affordance is
 * indistinguishable from a nav that has been cut off -- which is exactly how it
 * read: the first few sections looked like the complete list.
 *
 * This adds the two arrow buttons that `_includes/bottom-bar.html` ships in a
 * disabled state, and reveals them only while the strip actually overflows. So:
 *
 *   - the three sites with no chips (FPM, neohiro, transhumanists) never show
 *     them, because there is no scroller to drive;
 *   - a strip that fits never shows them either, so wide viewports keep the
 *     plain chip row they had;
 *   - whichever arrow points past the end of the strip is disabled rather than
 *     hidden, so the row does not reflow as you reach either end.
 *
 * Everything is measured at runtime rather than guessed from the chip count: chip
 * labels change with the site's locale strings and the viewport changes with the
 * user's zoom, so a hard-coded "overflows if more than N chips" would be wrong
 * both ways.
 *
 * Degrades to nothing if the markup is absent (the three chipless sites) and
 * cannot throw past its own call sites, because a scroll convenience must never
 * be the reason the bar stops working.
 */
(function () {
  "use strict";

  /* Roughly one chip plus its gap. Scrolling by this much leaves a visible
     remainder, which makes the control feel responsive instead of inert. */
  var STEP = 220;

  function setupBar(bar) {
    var scroller = bar.querySelector("[data-bar-scroller]");
    var left = bar.querySelector(".bottom-bar__left");
    var prev = bar.querySelector('[data-bar-scroll="prev"]');
    var next = bar.querySelector('[data-bar-scroll="next"]');
    if (!scroller || !left || !prev || !next) return;

    var raf = 0;

/* Scroll offset from the strip's start.
   *
   * LTR only, and deliberately so: no page in this network declares `dir="rtl"`,
   * so an RTL path here would be code that has never run against a rendered page.
   * An earlier version of this comment claimed to normalise RTL by taking the
   * absolute value of `scrollLeft`, which was only half true -- the disabled
   * state would have been right, but `step()` scrolls to a positive target, and
   * that moves the wrong way in RTL. A misleading comment about a direction the
   * code does not handle is worse than an honest assumption, so if an RTL page is
   * ever added this needs a direction check on both `offset()` and `step()`, plus
   * a test for it. */
  function offset() {
    return scroller.scrollLeft;
  }

    function update() {
      raf = 0;
      var max = scroller.scrollWidth - scroller.clientWidth;
      /* Fractional layout means this is rarely exactly 0; anything under a
       * pixel is not worth an arrow. */
      var overflows = max > 1;
      left.setAttribute("data-bar-overflow", overflows ? "true" : "false");

      if (!overflows) {
        prev.disabled = true;
        next.disabled = true;
        return;
      }
      /* 1px of slack so sub-pixel rounding at the very end does not leave the
       * forward arrow enabled with nowhere to go. */
      prev.disabled = offset() <= 1;
      next.disabled = offset() >= max - 1;
    }

    function schedule() {
      if (raf) return;
      raf = window.requestAnimationFrame(update);
    }

    function step(dir) {
      var max = scroller.scrollWidth - scroller.clientWidth;
      var target = offset() + STEP * dir;
      /* Clamp. Browsers ignore an out-of-range scrollTo, but clamping here keeps
       * the disabled state and the visual position in agreement even when a
       * resize happens between the click and the scroll landing. */
      target = Math.max(0, Math.min(max, target));
      var reduced = window.matchMedia &&
        window.matchMedia("(prefers-reduced-motion: reduce)").matches;
      scroller.scrollTo({
        left: target,
        behavior: reduced ? "auto" : "smooth"
      });
      /* `scroll` does not fire for a programmatic scroll that is a no-op, so
       * update on a timer as well as on the event. The smooth case needs the
       * longer delay: the scroll event lands on the first frame of the
       * animation, well before the strip has finished travelling, so refreshing
       * the arrows at that point would disable the arrow the visitor is about to
       * need again. */
      window.setTimeout(schedule, reduced ? 60 : 450);
    }

    prev.addEventListener("click", function () { step(-1); });
    next.addEventListener("click", function () { step(1); });

    scroller.addEventListener("scroll", schedule, { passive: true });

    /* Chip count, label length and zoom all change the answer, so re-measure on
     * resize. Debounced, because a drag-resize fires continuously. */
    var timer = 0;
    window.addEventListener("resize", function () {
      window.clearTimeout(timer);
      timer = window.setTimeout(schedule, 150);
    });

    /* Re-measure once webfonts land: the chips are text, so a font swap changes
     * the strip width after first paint. */
    if (document.fonts && document.fonts.ready) {
      document.fonts.ready.then(schedule).catch(function () { /* ignore */ });
    }

    update();
  }

  function init() {
    Array.prototype.forEach.call(
      document.querySelectorAll(".bottom-bar"),
      function (bar) {
        try {
          setupBar(bar);
        } catch (err) {
          /* Never let the convenience layer take the bar down with it. */
          if (window.console && console.warn) {
            console.warn("[bottom-bar] scroll affordances unavailable", err);
          }
        }
      }
    );
  }

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", init, { once: true });
  } else {
    init();
  }
})();