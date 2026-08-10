#!/usr/bin/env python3
"""test_chrome_contract.py -- shared chrome regressions that are invisible in a build.

Every check here corresponds to a bug that shipped to the live sites and produced
no build error, no Liquid exception and no failing build output. All four sites
share the chrome, so all four regressed together and all four are covered here.

Two ways to run it:

    # whole workspace, all four sites at once
    python test_chrome_contract.py

    # a single site -- this is what CI runs, because a per-site checkout has no
    # siblings to compare against. Accepts a site directory, a workspace root
    # containing the site, or nothing (defaults to the layout around this file).
    python test_chrome_contract.py --site /path/to/neohiro.github.io

Single-site mode still catches every bug this file was written for: they are all
"this site's own copy of a shared file is wrong", which is exactly the failure
mode when four hand-copied copies drift apart. What it cannot do is compare the
copies against each other, so the cross-site diff is a separate check
(--diff) that only the workspace run can perform.

Exit code 0 = pass, 1 = at least one failure.
"""

from __future__ import print_function

import io
import os
import re
import sys

# This file lives at <workspace>/template-shared/tests/, and the four sites are
# its siblings. So the workspace root is two levels above template-shared, i.e.
# three levels above this file.
_HERE = os.path.dirname(os.path.abspath(__file__))
TEMPLATE_SHARED = os.path.dirname(_HERE)
WORKSPACE = os.path.dirname(TEMPLATE_SHARED)

KNOWN_SITES = [
    "frenzypenguin-media.github.io",
    "neohiro.github.io",
    "openstageisland.github.io",
    "transhumanists.github.io",
]

# The files that must be byte-identical across all four sites. They are hand-copied
# rather than generated, and they drifted silently more than once: a `display: flex`
# left after a `display: none` fix landed on three of four copies, and line endings
# differed so hash-based comparison reported drift on five of six files that were in
# fact identical once EOLs were normalised. So the comparison is on normalised
# content, and it is reported separately from the per-site rules below.
SHARED_FILES = [
    os.path.join("assets", "js", "network-ux.js"),
    os.path.join("assets", "css", "network-ux.css"),
    os.path.join("assets", "css", "ai-seal.css"),
    os.path.join("assets", "css", "bottom-bar.css"),
    os.path.join("assets", "js", "bottom-bar.js"),
    os.path.join("_includes", "bottom-bar.html"),
]


def _resolve_sites(argv):
    """Return (root, [site dirs]) for the requested mode.

    --site X   -> (parent-of-X-if-it-is-a-workspace, [X]) so `read()` still works
                  with a site-relative path.
    --diff     -> (workspace, all known sites) and only the shared-file check runs.
    default    -> (workspace, all known sites) when they are siblings, else a
                  single-site run against the directory holding this file.
    """
    diff_only = False
    site_arg = None
    i = 1
    while i < len(argv):
        if argv[i] == "--site" and i + 1 < len(argv):
            site_arg = argv[i + 1]
            i += 2
            continue
        if argv[i] == "--diff":
            diff_only = True
            i += 1
            continue
        i += 1

    if site_arg:
        site_arg = os.path.abspath(site_arg)
        if not os.path.isdir(site_arg):
            print("no such site directory: %s" % site_arg)
            sys.exit(1)
        return os.path.dirname(site_arg), [site_arg], diff_only

    present = [os.path.join(WORKSPACE, s) for s in KNOWN_SITES
               if os.path.isdir(os.path.join(WORKSPACE, s))]
    if len(present) > 1:
        return WORKSPACE, present, diff_only

    # Standalone: this file is at <site>/scripts/, so the site is two levels up.
    guess = os.path.dirname(_HERE)
    if os.path.isfile(os.path.join(guess, "_layouts", "default.html")):
        return os.path.dirname(guess), [guess], diff_only

    print("cannot locate any site to check; pass --site <dir>")
    sys.exit(1)


ROOT, SITES, DIFF_ONLY = _resolve_sites(sys.argv)

# Every unreadable file, recorded once, as (site_dir, rel_path, exception_name).
#
# The site has to be carried alongside the path. The first version stored only the
# absolute path and then, at report time, looped over every site computing a
# relpath against each one -- so an unreadable file in neohiro was also reported
# against openstageisland, as "../neohiro.github.io/assets/css/ai-seal.css". A
# file that is fine on three sites gets three failures naming a path that does not
# exist on any of them, which is worse than not reporting it at all.
UNREADABLE = []


def _read_text(path, site=None, rel=None):
    """Return file text, or None if missing or not decodable as UTF-8.

    `site`/`rel` are the site-relative coordinates of `path`, when the caller has
    them, so an encoding failure can be reported against the site it belongs to
    rather than against whichever site is being examined at the time.
    """
    if not os.path.isfile(path):
        return None
    try:
        with io.open(path, encoding="utf-8") as handle:
            return handle.read()
    except (UnicodeDecodeError, IOError, OSError) as exc:
        UNREADABLE.append((site, rel or path, type(exc).__name__))
        return None


def read(site, rel):
    """Read a site-relative file, or None if it is absent or unreadable.

    Decoding errors are swallowed rather than raised. A gate that dies with a
    UnicodeDecodeError reports a traceback and no verdicts, which reads as "the
    gate is broken" and invites disabling it. The specific complaint is
    registered on UNREADABLE and reported by its own check at the end, so an
    encoding problem is named once instead of masquerading as every rule that
    reads the file being missing.
    """
    return _read_text(os.path.join(ROOT, site, rel), site, rel)


def normalised_bytes(site, rel):
    """File content with CRLF collapsed to LF, so EOL style is not 'drift'.

    Five of the six shared files reported as different by a plain hash when their
    content was identical and only the line endings differed (two sites on CRLF, two
    on LF). That is exactly the false alarm that teaches people to ignore a gate.

    `site` is an absolute path, so this does not silently depend on the current
    working directory the way a bare relative join would -- which it did, and which
    only worked when the gate happened to be run from the workspace root.
    """
    path = os.path.join(site, rel)
    if not os.path.isfile(path):
        return None
    with open(path, "rb") as handle:
        return handle.read().replace(b"\r\n", b"\n")


def check_shared_files():
    """All copies of each shared file must be identical.

    Only meaningful when more than one site is in scope; a single-site CI run has
    nothing to compare against, so the check is skipped rather than reported as a
    pass -- "the check ran and found nothing" must never be confused with "the
    check could not run".
    """
    if len(SITES) < 2:
        return
    for rel in SHARED_FILES:
        groups = {}   # normalised content -> [site names]
        missing = []  # site names with no such file
        for site in SITES:
            name = os.path.basename(os.path.normpath(site))
            data = normalised_bytes(site, rel)
            if data is None:
                missing.append(name)
                continue
            groups.setdefault(data, []).append(name)
        label = "shared file identical across sites: %s" % rel.replace(os.sep, "/")
        if missing:
            check(sites_label(), label, False, "absent from %s" % ", ".join(missing))
            continue
        if len(groups) == 1:
            check(sites_label(), label, True, "")
            continue
        # Name each variant and its size, so the message says which copy is the
        # odd one out rather than just that something differs.
        parts = []
        for data, names in groups.items():
            parts.append("%s (%d bytes)" % (", ".join(names), len(data)))
        check(sites_label(), label, False, "differs: " + " vs ".join(parts))


def sites_label():
    return SITES[0]


def strip_css_comments(css):
    """Remove /* ... */ so the gate reads declarations, not prose.

    Several of these rules carry a comment explaining the value they *replaced*
    ("Was `color: #ffffff` ..."). Matching declarations against the raw file
    would then fail on the very fix that was made, and a gate that cries wolf on
    a correct file is a gate people disable.
    """
    return re.sub(r"/\*.*?\*/", "", css, flags=re.DOTALL)


def block_of(css, selector, exact=True):
    """Return the first declaration block whose selector list contains `selector`.

    `exact` requires the selector to *begin* the compound selector it appears in,
    so `.ai-totop` matches `.ai-totop { ... }` and `.ai-totop.is-visible { ... }`
    but NOT `body:has(.bottom-bar) .ai-totop { ... }`, which is a different rule
    with different declarations. Matching the descendant form would silently
    assert against the wrong block -- which is how this gate briefly reported a
    correct `.ai-totop` rule as missing its bottom anchor.
    """
    needle = selector.lstrip(".")
    if exact:
        # The selector must start the compound it is in: only whitespace,
        # combinators, or a comma may precede it on the line, and it must not be
        # followed by more class/id/attribute syntax.
        token = re.compile(
            r"^(?:[\s,>+~]*)\.%s(?![\w-])(?![:\.\[])" % re.escape(needle))
    else:
        token = re.compile(re.escape(needle))
    lines = css.splitlines()
    for i, line in enumerate(lines):
        stripped = line.strip()
        if not stripped or stripped.startswith("/*"):
            continue
        if not token.search(stripped):
            continue
        # Reject a declaration line that merely mentions the class in a value
        # (e.g. a comment inside a block).
        if stripped.startswith("--") or stripped.startswith("*"):
            continue

        # Two shapes are in use across these sheets:
        #   .selector {            <- opening brace on the selector line
        #   .selector,
        #   .other {              <- comma-continued selector list
        brace_on_line = stripped.endswith("{")
        prelude = stripped[:-1].strip() if brace_on_line else stripped
        if not brace_on_line:
            # Must be a selector fragment: no declaration colon unless it ends
            # in a comma, and not a property/value pair.
            if ":" in prelude and not prelude.endswith(","):
                continue

        # Collect the block: from the opening brace to its matching close. When the
        # brace is not on this line (comma list), walk forward to the line that has it.
        j = i
        if not brace_on_line:
            while j < len(lines) and not lines[j].rstrip().endswith("{"):
                # Stop if we leave the selector list.
                if lines[j].strip() == "}":
                    break
                j += 1
            if j >= len(lines) or not lines[j].rstrip().endswith("{"):
                continue

        end = j
        while end < len(lines) and lines[end].strip() != "}":
            end += 1
        if end >= len(lines):
            return None
        return "\n".join(lines[i:end + 1])
    return None


results = []


def check(site, name, ok, detail=""):
    results.append((site, name, bool(ok), detail))


def check_unreadable_files():
    """Every file this gate read must have decoded as UTF-8.

    Reported separately from the per-site rules because the symptom it causes is
    a lie: an undecodable bottom-bar.css made the gate report that the grid rules
    were missing, which invites someone to go and "fix" a file that is fine.
    """
    # Deduped, because the same file is read once per rule that needs it and a
    # stylesheet with forty checks against it would otherwise be reported forty
    # times. Keyed on the path as recorded, not on a relpath recomputed per site:
    # a file belongs to exactly one site, and recomputing that relation for every
    # site in scope was what produced cross-site nonsense before.
    seen = set()
    for site, rel, exc in UNREADABLE:
        key = (site, rel)
        if key in seen:
            continue
        seen.add(key)
        check(site if site else "workspace",
              "shared file decodes as UTF-8: %s" % rel.replace(os.sep, "/"),
              False, "%s -- the gate cannot verify rules in this file" % exc)


# Mojibake signatures: what UTF-8 bytes look like after being decoded as cp1252
# and re-encoded. UTF-8 puts every multi-byte sequence in the E2-E3 lead range,
# which cp1252 maps to â and Ã, so these two characters immediately followed by
# another cp1252-mapped byte are a reliable marker.
#
# This corruption shipped. A mis-set PowerShell encoding rewrote files in place,
# and it reached published markup: the bottom bar's `title=` read "Talk to the
# neohiro assistant â€” questions", and 30 sequences sat in FPM's home.css. It was
# invisible to every other check here, because the files still parsed, still
# hashed consistently across three of four sites, and still rendered -- just with
# â€” where an em dash belonged. Two things made it hard to see: the damaged
# characters are valid Unicode, so a "does this file decode as UTF-8" check passes,
# and once three of four copies were corrupted the byte-identity comparison
# reported them as agreeing.
_MOJIBAKE = re.compile(r"[\u00e2\u00c3][\u20ac\u0080-\u009f]")


def check_mojibake():
    # The shared files, plus the three prose-carrying files that are per-site and so
    # are not covered by the byte-identity comparison at all.
    for site in SITES:
        for rel in list(SHARED_FILES) + ["assets/css/home.css", "index.html",
                                         "_includes/footer-button-row.html"]:
            text = read(site, rel)
            if text is None:
                continue
            hits = _MOJIBAKE.findall(text)
            if not hits:
                continue
            first = _MOJIBAKE.search(text)
            line = text[:first.start()].count("\n") + 1
            check(site,
                  "no mojibake in %s" % rel.replace(os.sep, "/"),
                  False,
                  "%d sequence(s), first at line %d: %r"
                  % (len(hits), line, text[first.start():first.start() + 12]))


def report():
    """Print every check, then exit non-zero if any failed."""
    check_unreadable_files()
    check_mojibake()
    fails = [r for r in results if not r[2]]
    cur = None
    label = lambda s: os.path.basename(os.path.normpath(s))  # noqa: E731
    for site, name, ok, detail in results:
        if site != cur:
            print("\n-- %s --" % label(site))
            cur = site
        print("  %s    %s%s" % ("ok  " if ok else "FAIL", name,
                               ("  -> %s" % detail) if detail and not ok else ""))

    print("\n== summary ==")
    if fails:
        print("  FAILED: %d of %d checks" % (len(fails), len(results)))
        for site, name, _ok, detail in fails:
            print("    %s: %s%s" % (site, name, (" -> %s" % detail) if detail else ""))
        sys.exit(1)

    print("  OK: %d checks passed across %d sites" % (len(results), len(SITES)))
    sys.exit(0)


# `--diff` asks only "did the hand-copied files drift apart?", which is a
# question about file bytes, not about any one site's CSS being correct. Run
# only that check and stop: the per-site rules are ~500 lines of parsing and are
# answered by the single-site run in each repo's CI, so a diff check that also
# reported all of them would bury the one line the caller asked for. The flag used
# to be parsed and then ignored, which meant `--diff` silently ran and reported
# all 150 checks -- indistinguishable from a plain run, and a real risk of
# someone reading a green --diff as proof the shared files match when the check
# had been skipped for want of a second site.
if DIFF_ONLY:
    check_shared_files()
    report()


# ---------------------------------------------------------------------------
# 1. The retired dock must never paint.
# ---------------------------------------------------------------------------
for site in SITES:
    css = strip_css_comments(read(site, "assets/css/auth-bar.css") or "")
    dock = block_of(css, ".ai-dock", exact=True)
    if dock is None:
        check(site, "retired .ai-dock rule exists", False, "no .ai-dock block found")
    else:
        # `display: flex` here overrode the `hidden` attribute in the markup: an
        # author-level `display` beats the UA stylesheet's `[hidden] {display:none}`,
        # so the dock painted an empty panel strip on every live page and its
        # `.ai-dock__panels { pointer-events: auto }` swallowed clicks.
        bad_display = re.search(r"display\s*:\s*(flex|block|grid|inline-flex)\s*;", dock)
        check(site, "retired .ai-dock is not display:flex/block/grid", not bad_display,
              (bad_display.group(0) if bad_display else ""))
        check(site, "retired .ai-dock honours the hidden attribute",
              ".ai-dock[hidden]" in css, "")

    panel = block_of(css, ".ai-dock__panel[hidden]", exact=True)
    if panel is None:
        check(site, ".ai-dock__panel[hidden] rule exists", False, "not found")
    else:
        # Was `display: block !important`, which inverts `hidden`: every panel in
        # auth-bar.html ships hidden, so all of them painted at once. That was the
        # placeholder panel on the live sites.
        forced = re.search(r"display\s*:\s*block\s*!important", panel)
        check(site, "hidden panels are display:none, not display:block", not forced,
              (forced.group(0) if forced else ""))

    pe = re.search(r"\.ai-dock__rail,\s*\.ai-dock__panels\s*\{([^}]*)\}", css)
    if pe:
        check(site, "retired dock panels do not capture pointer events",
              "pointer-events: auto" not in pe.group(1), "")


# ---------------------------------------------------------------------------
# 2. The AI seal and the back-up arrow must share one slot and one size.
# ---------------------------------------------------------------------------
for site in SITES:
    css = strip_css_comments(read(site, "assets/css/ai-seal.css") or "")

    size = re.search(r"--ai-totop-size\s*:\s*([^;]+);", css)
    check(site, "arrow size tracks the seal size (they crossfade in place)",
          bool(size) and "var(--ai-seal-size)" in size.group(1),
          (size.group(1).strip() if size else "no --ai-totop-size"))

    arrow = block_of(css, ".ai-totop", exact=True)
    if arrow is None:
        check(site, ".ai-totop rule exists", False, "not found")
    else:
        # The arrow used to be pinned to `top: 50%`, so it and the bottom-right
        # seal were both on screen at once. They now share the seal's corner.
        check(site, "arrow is not pinned to a vertical % offset",
              not re.search(r"top\s*:\s*\d+%", arrow), "")
        check(site, "arrow is bottom-anchored like the seal",
              "bottom: var(--ai-seal-lift)" in arrow, "")
        check(site, "arrow is not absolutely positioned off-centre",
              "translate: 0 -50%" not in arrow, "")

    # Both must be lifted by the same amount or the swap jumps.
    lift = re.search(r"body:has\(\.bottom-bar\)\s+\.ai-seal-dock,\s*\n?\s*body:has\(\.bottom-bar\)\s+\.ai-totop", css)
    check(site, "bottom-bar lift applies to both seal and arrow",
          bool(lift), "")

    check(site, "arrow crossfades the seal out when visible",
          re.search(r"\.ai-arrow-visible\s+\.ai-seal\s*\{", css) is not None, "")

    # The crossfade must NOT be driven off `:has()` again. ai-seal.js mirrors the
    # arrow's state onto <html>, and that is the only form that works everywhere:
    # `:has()` is unsupported on Firefox before 121 and an unsupported selector is
    # dropped whole rather than degraded, which left the seal painted underneath
    # the arrow -- the exact defect the crossfade was added to fix.
    check(site, "seal crossfade does not depend on :has()",
          ":has(.ai-totop.is-visible)" not in css, "")

    js = read(site, "assets/js/ai-seal.js")
    check(site, "ai-seal.js mirrors the arrow state onto <html>",
          bool(js) and 'classList.toggle("ai-arrow-visible"' in js, "")

    # The sheet is z-index 910 and fills 87% of the viewport from the bottom, so
    # the bottom-right corner is inside it. This sheet is 940, which put the
    # arrow and the seal on top of the open conversation. Verified before the
    # fix: elementFromPoint at the arrow's centre returned the arrow.
    check(site, "seal and arrow stand down while a conversation is open",
          re.search(r"body\.ai-conv-active\s+\.ai-totop\s*\{[^}]*visibility\s*:\s*hidden",
                    css) is not None, "")


# ---------------------------------------------------------------------------
# 3. Page text must follow the colour scheme.
# ---------------------------------------------------------------------------
# `#fff` on an element that sits on the page background is invisible in light
# mode. Measured on neohiro: .hero-title at rgb(255,255,255) on rgb(248,250,252)
# = 1.05:1. White on a coloured button/pill/badge is fine and expected, so only
# the known text-on-background selectors are asserted.
THEME_FOLLOWS = [
    ("assets/css/main.css", ".hero-title"),
    ("assets/css/main.css", ".typewriter"),
    ("assets/css/network-ux.css", ".typewriter"),
]
for site in SITES:
    for rel, selector in THEME_FOLLOWS:
        css = read(site, rel)
        if css is not None:
            css = strip_css_comments(css)
        if css is None:
            # Not every site ships every sheet, and not every sheet defines every
            # selector: OSI has no main.css at all, and the typewriter belongs to
            # neohiro's quotes section. The contract is "if this rule exists here,
            # it must use a token" -- not "every site must have it".
            continue
        block = block_of(css, selector, exact=True)
        if block is None:
            # Selector absent on this site: nothing to assert.
            continue
        hard = re.search(r"color\s*:\s*(#fff\b|#ffffff\b|\bwhite\b)", block)
        check(site, "%s %s uses a theme token, not a fixed colour" % (rel, selector),
              not hard, (hard.group(0) if hard else ""))

# The "live signal" badge was accent text on an accent tint: 1.00:1 in light mode.
for site in SITES:
    css = strip_css_comments(read(site, "assets/css/network-ux.css") or "")
    badge = block_of(css, ".typewriter-prefix", exact=True)
    if badge is None:
        check(site, ".typewriter-prefix rule exists", False, "not found")
    else:
        decl = badge[badge.index("{") + 1:]
        check(site, "live-signal badge is solid fill, not accent-on-tint",
              not re.search(r"color\s*:\s*var\(--accent", decl)
              and not re.search(r"background\s*:\s*var\(--accent-dim", decl), "")


# ---------------------------------------------------------------------------
# 4. The bottom bar must centre the AI button and offer overflow arrows.
# ---------------------------------------------------------------------------
for site in SITES:
    css = strip_css_comments(read(site, "assets/css/bottom-bar.css") or "")
    check(site, "bottom-bar.css is linked by the layout",
          "/assets/css/bottom-bar.css" in (read(site, "_layouts/default.html") or ""),
          "")
    # Grid auto-placement put the AI button in column 1 on the three sites with no
    # section chips, because it was the first child. Explicit columns fix it.
    for child, col in ((".bottom-bar__left", "1"), (".bottom-bar__ai", "2"),
                       (".bottom-bar__right", "3")):
        block = block_of(css, child)
        if block is None:
            check(site, "%s rule exists" % child, False, "not found")
        else:
            check(site, "%s is pinned to grid column %s" % (child, col),
                  re.search(r"grid-column\s*:\s*%s\b" % col, block) is not None, "")

    check(site, "chip strip is the measured scroll container",
          re.search(r"\.bottom-bar__list\s*\{[^}]*overflow-x\s*:\s*auto", css,
                    re.IGNORECASE) is not None, "")

    # The strip sets `scroll-behavior: smooth`, so a reduced-motion user clicking
    # an arrow would still get an animated scroll unless this overrides it.
    # `scrollTo({behavior: 'auto'})` does not help: `auto` defers to the CSS value.
    check(site, "reduced-motion disables the smooth chip scroll",
          re.search(r"@media\s*\(prefers-reduced-motion:\s*reduce\)\s*\{"
                    r"[^{}]*\.bottom-bar__list\s*\{[^}]*scroll-behavior\s*:\s*auto",
                    css, re.IGNORECASE) is not None, "")

    # No bare --color-* read: those tokens only exist in assets/style.css, which
    # three of the four layouts do not link, so an unresolvable var() silently
    # paints a transparent background. Covered in detail by the token-resolution
    # check below; this keeps the failure legible at the rule that caused it.
    bare_colour = set(m.group(1) for m in
                      re.finditer(r"var\((--color-[a-z-]+)\s*\)", css))
    check(site, "bottom-bar.css has no bare --color-* read", not bare_colour,
          ", ".join(sorted(bare_colour)))

    js = read(site, "assets/js/bottom-bar.js")
    check(site, "bottom-bar.js is linked by the layout",
          "/assets/js/bottom-bar.js" in (read(site, "_layouts/default.html") or ""), "")
    if js:
        check(site, "bottom-bar.js measures the list it scrolls",
              "data-bar-scroller" in js, "")
    include = read(site, "_includes/bottom-bar.html") or ""
    check(site, "chip strip carries data-bar-scroller",
          'class="bottom-bar__list" data-bar-scroller' in include
          or ("data-bar-scroller" in include and "bottom-bar__list" in include), "")

    # The scroll buttons shipped with tabindex="-1" to stay out of the tab order.
    # That is redundant while they are `display: none` (which already removes an
    # element from the tab order) and harmful once the strip overflows: the
    # buttons become visible and enabled while still being unreachable by
    # keyboard, with :focus-visible styling that could never fire.
    buttons = re.findall(r"<button[^>]*data-bar-scroll[^>]*>", include, re.IGNORECASE)
    check(site, "chip scroll buttons exist and are keyboard reachable",
          len(buttons) == 2 and not any("tabindex" in b for b in buttons),
          ("%d button(s); tabindex on: %s"
           % (len(buttons),
              ", ".join(b[:60] for b in buttons if "tabindex" in b))
           if buttons and any("tabindex" in b for b in buttons) else ""))


# ---------------------------------------------------------------------------
# 5. The conversation frame must be a real size, not a ceiling.
# ---------------------------------------------------------------------------
for site in SITES:
    css = strip_css_comments(read(site, "assets/css/network-ux.css") or "")
    chrome = block_of(css, ".ai-conv__chrome", exact=True)
    if chrome is None:
        check(site, ".ai-conv__chrome rule exists", False, "not found")
    else:
        # `max-height` alone could never make the frame tall: the flex column's
        # only height was its content, so a fresh conversation measured ~220px
        # (29% of the viewport) and read as a small bar sliding up.
        check(site, "conversation frame has a real height, not only max-height",
              re.search(r"(?<!max-)height\s*:\s*min\(\s*8\d\s*vh", chrome) is not None, "")

    msgs = block_of(css, ".ai-conv__messages", exact=True)
    if msgs is None:
        check(site, ".ai-conv__messages rule exists", False, "not found")
    else:
        # Without flex + min-height:0 the thread refuses to shrink, so opening the
        # triage form overflowed the frame and pushed the composer off screen.
        check(site, "thread flexes and can shrink (min-height:0)",
              "flex: 1" in msgs and "min-height: 0" in msgs, "")

    triage = block_of(css, ".ai-conv__triage", exact=True)
    if triage is not None:
        check(site, "triage form yields instead of pushing the composer out",
              "min-height: 0" in triage and "overflow-y" in triage, "")


# ---------------------------------------------------------------------------
# 6. No Liquid comment syntax may sit inside a JS template literal.
# ---------------------------------------------------------------------------
for site in SITES:
    js = read(site, "assets/js/network-ux.js")
    if js is None:
        check(site, "network-ux.js present", False, "missing")
        continue
    # This file has no front matter, so Jekyll copies it verbatim and never
    # evaluates Liquid: a `{# ... #}` inside the markup template literal is
    # literal output that renders as visible text in the conversation modal.
    offenders = [i + 1 for i, line in enumerate(js.splitlines()) if "{#" in line]
    check(site, "no Liquid comment syntax inside network-ux.js",
          not offenders, ("lines %s" % offenders if offenders else ""))


# ---------------------------------------------------------------------------
# 7. The hand-copied shared files must not have drifted apart.
# ---------------------------------------------------------------------------
check_shared_files()


# ---------------------------------------------------------------------------
# 7b. Internal tooling notes must not reach the rendered page.
# ---------------------------------------------------------------------------
# neohiro's layout carried `<!-- fonts: managed by template-shared/site_forge.py
# from sites.yaml -->` as an HTML comment while the other three used
# `{% comment %}`. An HTML comment renders as nothing, so it looks fine in
# review, but it ships: 26 built pages carried the note, disclosing the internal
# tooling and the repo layout to anyone reading page source. A Liquid comment is
# stripped at build time and costs nothing.
_INTERNAL_NOTE = re.compile(
    r"<!--[^>]*\bmanaged by template-shared\b[^>]*-->", re.IGNORECASE)
for site in SITES:
    for rel in (os.path.join("_layouts", "default.html"),
                os.path.join("_includes", "theme.html")):
        txt = read(site, rel)
        if txt is None:
            continue
        found = _INTERNAL_NOTE.findall(txt)
        check(site, "internal tooling note is a Liquid comment, not HTML (%s)"
              % rel.replace(os.sep, "/"),
              not found, "; ".join(found[:2]))


# ---------------------------------------------------------------------------
# 8. Every custom property the shared CSS reads must actually resolve.
# ---------------------------------------------------------------------------
# This is the check that would have caught the invisible bar.
#
# bottom-bar.css reads --color-stage for the AI button and the CTA. Those
# properties are defined in assets/style.css, which exists in all four repos --
# and which three of the four layouts never link. A var() with no fallback and no
# *loaded* definition resolves to nothing, and for `background` that means
# transparent, so the central AI button and the primary CTA rendered as invisible
# white text. It was invisible to review because the token was defined on disk and
# a grep-based check would have found it there.
#
# So the resolution set is built from the stylesheets the page actually links,
# parsed out of the layout, not from every .css file in the repo.


def _linked_stylesheets(site):
    """Stylesheet hrefs the site's default layout links, as repo-relative paths.

    Parsed tag by tag rather than with one combined regex, and with a greedy href
    capture. Two real shapes in these layouts defeat the obvious parser:

      href="{{ '/assets/css/main.css' | relative_url }}"
      href="{{ "/assets/css/site-tokens.css" | relative_url }}"

    The second embeds double quotes inside a double-quoted attribute, so a
    non-greedy `[^"]+` stops at the inner quote and captures `{{ "`. That is how
    three stylesheets silently dropped out of the linked set here, which in turn
    made every token they define look unresolved. Attribute order also varies
    between the four layouts, hence tag-by-tag.
    """
    layout = read(site, os.path.join("_layouts", "default.html"))
    if layout is None:
        return None
    out = []
    for tag in re.finditer(r"<link\b[^>]*>", layout):
        blob = tag.group(0)
        if not re.search(r"rel\s*=\s*[\"']?stylesheet[\"']?", blob):
            continue
        href = re.search(r"href\s*=\s*\"(.*)\"", blob) or \
            re.search(r"href\s*=\s*'(.*)'", blob)
        if not href:
            continue
        value = href.group(1).split("?")[0].strip()
        # The href is normally `{{ '/assets/css/main.css' | relative_url }}`, so
        # the whole thing is a Liquid tag and stripping the braces would leave an
        # empty string. Pull the quoted path out of the expression instead.
        if "{{" in value:
            inner = re.search(r"['\"]([^'\"]+\.css)['\"]", value)
            if not inner:
                continue
            value = inner.group(1)
        value = value.lstrip("/").strip()
        if value.endswith(".css"):
            out.append(value)
    return out


def _defined_props(path):
    txt = read_from(path)
    if txt is None:
        return set()
    return set(re.findall(r"(--[A-Za-z0-9_-]+)\s*:", txt))


def read_from(path):
    """Read a filesystem path, or None if absent or unreadable.

    Same swallowing as `read()`, and for the same reason: an undecodable
    stylesheet must produce a reported failure, not a traceback. `site`/`rel` are
    supplied by the caller where it has them, so a failure here is still attributed
    to the right site -- this function is reached from token resolution, which
    walks each site's linked stylesheets by absolute path.
    """
    return _read_text(path, *_coords(path))


def _coords(path):
    """(site, rel) for an absolute path under one of the sites, else (None, path).

    A path can only be attributed if it lies inside a site being checked; anything
    else is reported against the workspace with its path as-is, rather than being
    forced into some site's relpath.
    """
    for site in SITES:
        root = os.path.join(ROOT, site)
        try:
            common = os.path.commonpath([os.path.abspath(path), os.path.abspath(root)])
        except ValueError:
            continue     # different drives on Windows
        if os.path.normcase(common) == os.path.normcase(os.path.abspath(root)):
            return (os.path.basename(os.path.normpath(site)),
                    os.path.relpath(path, root))
    return (None, path)


def check_token_resolution():
    for site in SITES:
        linked = _linked_stylesheets(site)
        if not linked:
            check(site, "layout links stylesheets (token resolution is checkable)",
                  False, "could not find any <link rel=stylesheet> in _layouts/default.html")
            continue
        available = set()
        for rel in linked:
            available |= _defined_props(os.path.join(site, rel))
        for rel in SHARED_FILES:
            if not rel.endswith(".css"):
                continue
            path = os.path.join(site, rel)
            css = read_from(path)
            if css is None:
                continue
            css = strip_css_comments(css)
            # var(--x) with nothing after it -> no fallback, so it must resolve.
            bare = set(m.group(1) for m in
                       re.finditer(r"var\((--[A-Za-z0-9_-]+)\s*\)", css))
            unresolved = sorted(p for p in bare if p not in available)
            label = "shared CSS tokens resolve: %s" % rel.replace(os.sep, "/")
            check(site, label, not unresolved,
                  ("no fallback and not defined by any linked stylesheet: %s"
                   % ", ".join(unresolved)) if unresolved else "")


check_token_resolution()


# ---------------------------------------------------------------------------
# Report
# ---------------------------------------------------------------------------
report()