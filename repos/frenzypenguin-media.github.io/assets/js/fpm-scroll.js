/* fpm-scroll.js — the frenzypenguin.media hero + scroll-narrative controller.
 *
 * Opt-in: loaded only by the homepage, via `extra_js` in its front matter.
 * Everything degrades. With JavaScript off, the page is still a complete,
 * readable document: the CSS gives every beat its final state, the canvas is
 * simply an empty frame, and the hero line falls back to its static text.
 *
 * WHAT IS HERE AND WHY IT IS NOT A SCROLL LISTENER
 *   The narrative entrance and the progress rail are pure CSS scroll-driven
 *   animations (see assets/css/fpm-hero.css). Those run on the compositor and
 *   need no JavaScript at all. What genuinely cannot be done in CSS is:
 *     - deciding WHICH beat is active, because that requires knowing when a
 *       beat crosses the viewport centre, and
 *     - swapping one shared <video> element's source per beat.
 *   So this file does exactly those two things, plus the typewriter and the
 *   canvas. It reads position from an IntersectionObserver rather than from
 *   scroll events, which means zero scroll handlers and no forced reflow.
 *
 * PERFORMANCE RULES HELD HERE
 *   - The canvas is capped at 1.5x DPR and only redraws while the narrative is
 *     on screen and the tab is visible.
 *   - Video is loaded lazily on first activation only, never eagerly: four
 *     autoplaying videos on a portfolio page is how a page loses its
 *     performance budget.
 *   - Nothing is fetched cross-origin. No analytics, no telemetry — that claim
 *     is made in the hero and it has to be true here too.
 */
(function () {
  'use strict';

  var reduceMotion = window.matchMedia
    ? window.matchMedia('(prefers-reduced-motion: reduce)')
    : { matches: false };

  function $(sel, root) { return (root || document).querySelector(sel); }
  function $$(sel, root) {
    return Array.prototype.slice.call((root || document).querySelectorAll(sel));
  }

  /* ----------------------------------------------------------------------
   * 1. Hero typewriter.
   *
   * Separate from assets/js/fpm-typing.js on purpose: that module's
   * autoAttach() mirrors text into an <input> placeholder, which is the right
   * shape for a search box and the wrong shape for a headline. Both can
   * coexist on the site; only one of them runs on this page.
   * -------------------------------------------------------------------- */
  function initTypewriter() {
    var out = $('#fpm-typed');
    if (!out) return;

    var lines = $$('[data-fpm-line]').map(function (el) {
      return el.getAttribute('data-fpm-line');
    }).filter(Boolean);

    // Static fallback first, so no-JS and reduced-motion both read correctly.
    if (!lines.length) return;
    out.textContent = lines[0];

    if (reduceMotion.matches) return;

    var caret = document.createElement('span');
    caret.className = 'fpm-hero__caret';
    caret.setAttribute('aria-hidden', 'true');

    var i = 0;
    var chars = 0;
    var erasing = false;
    var timer = null;

    function step() {
      var line = lines[i];
      if (!erasing) {
        chars += 1;
        out.textContent = line.slice(0, chars);
        if (chars >= line.length) {
          erasing = true;
          timer = window.setTimeout(step, 2600);
          return;
        }
        // Slight jitter so it reads as typing rather than a fixed metronome.
        timer = window.setTimeout(step, 22 + Math.random() * 26);
        return;
      }
      chars -= 1;
      out.textContent = line.slice(0, chars);
      if (chars <= 0) {
        erasing = false;
        i = (i + 1) % lines.length;
        timer = window.setTimeout(step, 320);
        return;
      }
      timer = window.setTimeout(step, 9);
    }

    out.parentNode.appendChild(caret);
    out.setAttribute('aria-live', 'polite');
    timer = window.setTimeout(step, 900);

    // Stop on interaction with anything focusable: an animation that keeps
    // moving while someone is trying to read is a bug, not a flourish.
    function halt() {
      if (!timer) return;
      window.clearTimeout(timer);
      timer = null;
      out.textContent = lines[0];
      caret.remove();
    }
    out.addEventListener('focusin', halt);
    document.addEventListener('visibilitychange', function () {
      if (document.hidden) halt();
    });
  }

  /* ----------------------------------------------------------------------
   * 2. Signal field.
   *
   * The panel under the video. It exists so the media column is never an empty
   * rectangle: whether or not a video is present, and whether or not the
   * visitor's browser can decode one, there is always something moving.
   *
   * Drawn as a horizon grid plus a travelling waveform, both in one pass. Cost
   * is a few dozen line segments, so it stays cheap on a phone.
   * -------------------------------------------------------------------- */
  function initSignalField() {
    var canvas = $('#fpm-signal');
    if (!canvas || !canvas.getContext) return;

    var media = canvas.closest('.fpm-stage__media');
    var ctx = canvas.getContext('2d');
    var w = 0, h = 0, dpr = 1, raf = null, visible = false;

    var COLS = 26;
    var ROWS = 16;
    var t = 0;

    function resize() {
      var r = canvas.getBoundingClientRect();
      if (!r.width || !r.height) return;
      dpr = Math.min(window.devicePixelRatio || 1, 1.5);
      w = r.width;
      h = r.height;
      canvas.width = Math.round(w * dpr);
      canvas.height = Math.round(h * dpr);
      ctx.setTransform(dpr, 0, 0, dpr, 0, 0);
    }

    function frame() {
      raf = null;
      if (!visible || document.hidden) return;

      t += 0.016;

      ctx.clearRect(0, 0, w, h);

      // Horizon grid, receding.
      ctx.lineWidth = 1;
      for (var r = 0; r <= ROWS; r++) {
        var p = r / ROWS;
        var y = h * (0.34 + Math.pow(p, 2.1) * 0.66);
        ctx.strokeStyle = 'rgba(124,77,255,' + (0.05 + p * 0.16).toFixed(3) + ')';
        ctx.beginPath();
        ctx.moveTo(0, Math.round(y) + 0.5);
        ctx.lineTo(w, Math.round(y) + 0.5);
        ctx.stroke();
      }
      for (var c = 0; c <= COLS; c++) {
        var x = (c / COLS) * w;
        ctx.strokeStyle = 'rgba(0,229,255,0.07)';
        ctx.beginPath();
        ctx.moveTo(x, h * 0.34);
        ctx.lineTo(w * 0.5 + (x - w * 0.5) * 2.6, h);
        ctx.stroke();
      }

      // Travelling waveform, two summed sines so it never looks periodic.
      var mid = h * 0.55;
      ctx.lineWidth = 1.5;
      ctx.strokeStyle = 'rgba(102,255,204,0.75)';
      ctx.beginPath();
      for (var x2 = 0; x2 <= w; x2 += 3) {
        var u = x2 / w;
        var amp = h * 0.09 * (0.35 + u * 0.65);
        var y2 = mid
          + Math.sin(u * 9 + t * 1.6) * amp
          + Math.sin(u * 21 - t * 2.3) * amp * 0.35;
        if (x2 === 0) ctx.moveTo(x2, y2); else ctx.lineTo(x2, y2);
      }
      ctx.stroke();

      // Leading node.
      var head = w * ((t * 0.18) % 1);
      ctx.fillStyle = 'rgba(0,229,255,0.9)';
      ctx.beginPath();
      ctx.arc(head, mid, 2, 0, Math.PI * 2);
      ctx.fill();

      raf = window.requestAnimationFrame(frame);
    }

    function play() {
      if (raf === null && visible && !document.hidden && !reduceMotion.matches) {
        raf = window.requestAnimationFrame(frame);
      }
    }
    function stop() {
      if (raf !== null) { window.cancelAnimationFrame(raf); raf = null; }
    }

    if (window.ResizeObserver) {
      new window.ResizeObserver(resize).observe(canvas);
    } else {
      window.addEventListener('resize', resize);
    }

    if ('IntersectionObserver' in window && media) {
      new window.IntersectionObserver(function (entries) {
        visible = entries[0].isIntersecting;
        visible ? play() : stop();
      }, { threshold: 0.02 }).observe(media);
    } else {
      visible = true;
    }

    document.addEventListener('visibilitychange', function () {
      document.hidden ? stop() : play();
    });
    if (reduceMotion.addEventListener) {
      reduceMotion.addEventListener('change', function () {
        reduceMotion.matches ? stop() : play();
      });
    }

    resize();
    // One static frame even under reduced motion, so the panel is never blank.
    if (reduceMotion.matches) {
      visible = true;
      t = 0;
      resize();
      window.requestAnimationFrame(function () {
        frame();
        stop();
      });
    }
    play();
  }

  /* ----------------------------------------------------------------------
   * 3. The narrative.
   *
   * One <video> is shared by every beat. When a beat becomes the active one the
   * source is swapped and the caption updated, so the paragraphs read as
   * sharing a single moving image rather than as four separate embeds.
   *
   * If a beat declares no `data-video`, or the file is missing, the video is
   * simply never promoted to visible and the canvas keeps playing underneath.
   * There is no error state to design around, because nothing failed.
   * -------------------------------------------------------------------- */
  function initNarrative() {
    var media = $('.fpm-stage__media');
    var beats = $$('.fpm-beat');
    if (!beats.length) return;

    var video = $('#fpm-video');
    var caption = $('#fpm-caption-text');
    var active = null;
    var sweepTimer = null;

    function setActive(beat) {
      if (beat === active) return;
      active = beat;

      beats.forEach(function (b) {
        b.setAttribute('data-active', b === beat ? '1' : '0');
      });

      if (caption) {
        var label = beat.getAttribute('data-caption');
        if (label) caption.textContent = label;
      }

      if (!media) return;

      // Restart the scanline sweep on every change.
      media.classList.remove('is-sweeping');
      if (sweepTimer) window.clearTimeout(sweepTimer);
      // Force a reflow so the animation restarts rather than being ignored as
      // a no-op because the class was already absent.
      void media.offsetWidth;
      media.classList.add('is-sweeping');
      sweepTimer = window.setTimeout(function () {
        media.classList.remove('is-sweeping');
      }, 1600);

      if (!video) return;
      var src = beat.getAttribute('data-video');
      if (!src) return;

      // Only the first activation triggers a network request; after that the
      // same element has a decoded buffer to work with.
      if (video.getAttribute('src') === src) {
        try { video.play(); } catch (e) { /* autoplay refused; poster stays */ }
        return;
      }

      video.setAttribute('src', src);
      media.setAttribute('data-video-ready', '0');

      var reveal = function () {
        media.setAttribute('data-video-ready', '1');
        if (reduceMotion.matches) return;
        var p = video.play();
        if (p && typeof p.catch === 'function') {
          p.catch(function () { /* keep the canvas showing */ });
        }
      };
      var fail = function () {
        media.setAttribute('data-video-ready', '0');
      };

      video.addEventListener('loadeddata', reveal, { once: true });
      video.addEventListener('error', fail, { once: true });
      video.load();
    }

    if ('IntersectionObserver' in window) {
      // rootMargin pulls the trigger line up to the viewport centre so the beat
      // you are reading is the beat driving the panel.
      var io = new IntersectionObserver(function (entries) {
        var best = null;
        entries.forEach(function (e) {
          if (!e.isIntersecting) return;
          // Highest intersection ratio wins; ties break toward the later entry.
          if (!best || e.intersectionRatio >= best.intersectionRatio) best = e;
        });
        if (best) setActive(best.target);

        // Entrance state, for engines without scroll-driven animations.
        entries.forEach(function (e) {
          if (e.isIntersecting) e.target.classList.add('is-in');
        });
      }, {
        rootMargin: '-45% 0px -45% 0px',
        threshold: [0, 0.01, 0.25, 0.5, 0.75, 1]
      });
      beats.forEach(function (b) { io.observe(b); });
    } else {
      beats.forEach(function (b) { b.classList.add('is-in'); });
      setActive(beats[0]);
    }
  }

  /* ----------------------------------------------------------------------
   * 4. Progress rail fallback.
   *
   * In every current engine the rail is a scroll() timeline in CSS and this
   * does nothing. The branch exists so an older browser still gets a rail
   * rather than a stuck 2px line, and it is rAF-throttled so it can never
   * outrun the compositor.
   * -------------------------------------------------------------------- */
  function initRail() {
    var rail = $('#fpm-rail');
    if (!rail) return;

    var supported = window.CSS && CSS.supports
      && CSS.supports('animation-timeline: scroll()');
    if (supported) return;

    var ticking = false;
    function update() {
      ticking = false;
      var max = document.documentElement.scrollHeight - window.innerHeight;
      var p = max > 0 ? Math.min(1, Math.max(0, window.pageYOffset / max)) : 0;
      rail.style.transform = 'scaleX(' + p.toFixed(4) + ')';
    }
    window.addEventListener('scroll', function () {
      if (ticking) return;
      ticking = true;
      window.requestAnimationFrame(update);
    }, { passive: true });
    update();
  }

  function boot() {
    initTypewriter();
    initSignalField();
    initNarrative();
    initRail();
  }

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', boot);
  } else {
    boot();
  }
})();