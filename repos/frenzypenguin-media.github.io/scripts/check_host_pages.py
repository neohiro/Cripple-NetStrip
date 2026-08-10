"""Verify the host-directory build against a built _site.

Checks that fail loudly, in order of how much they would hurt:

  1. Every host in _data/hosts.yml has a rendered page at the right path.
  2. Every rendered page carries the swirl markup with a REAL id, and every
     aria-controls points at an id that exists on the same page. A dangling
     aria-controls is a screen-reader dead end.
  3. No id appears twice on a page. The directory renders 34 cards with the same
     eid prefix, so a slug typo would silently collide.
  4. The /hosts/ page groups by category and each group holds exactly its own
     members, deadest first.
  5. The navbar hosts menu rendered, with one row per host and the right dot.
  6. The raw link and the live URL are both present on every host page.
  7. No Liquid ever leaked into the output.
  8. No page references an asset the build did not produce.
"""

import collections
import os
import re
import sys

import yaml

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
# -1 lets this run against a build output wherever it lives:
#     python scripts/check_host_pages.py --site ./_site
SITE = os.path.join(REPO, "_site")
DATA = os.path.join(REPO, "_data", "hosts.yml")

fails = []
notes = []


def fail(msg):
    fails.append(msg)


def read(path):
    with open(path, encoding="utf-8", errors="replace") as fh:
        return fh.read()


data = yaml.safe_load(read(DATA))
hosts = data["hosts"]
by_slug = {h["slug"]: h for h in hosts}


# ── 1. routes ───────────────────────────────────────────────────────────────
def route_for(h):
    return "/artists/%s/" % h["slug"] if h["category"] == "artists" else "/%s/" % h["slug"]


def file_for(url):
    return os.path.join(SITE, url.strip("/").replace("/", os.sep), "index.html")


for h in hosts:
    for url in (route_for(h), "/%s/" % h["slug"]):
        p = file_for(url)
        if not os.path.isfile(p):
            fail("no page at %s (for %s)" % (url, h["slug"]))
for extra in ("/hosts/", "/artists/"):
    if not os.path.isfile(file_for(extra)):
        fail("no page at %s" % extra)

print(
    "routes: %d host pages + %d aliases + 2 indexes checked"
    % (len(hosts), len([h for h in hosts if h["category"] == "artists"]))
)

# ── 2/3. swirl markup, aria wiring, duplicate ids ───────────────────────────
pages = [
    ("/", file_for("/")),
    ("/hosts/", file_for("/hosts/")),
    ("/artists/", file_for("/artists/")),
]
for h in hosts:
    pages.append((route_for(h), file_for(route_for(h))))
    if h["category"] == "artists":
        pages.append(("/%s/" % h["slug"], file_for("/%s/" % h["slug"])))

checked_controls = 0
for label, path in pages:
    if not os.path.isfile(path):
        continue
    html = read(path)

    if "{%" in html or "{{" in html:
        for m in re.finditer(r"\{[%{].{0,60}", html):
            fail("%s: unrendered Liquid %r" % (label, m.group(0)[:50]))
            break

    ids = re.findall(r'\sid="([^"]+)"', html)
    dupes = [i for i, n in collections.Counter(ids).items() if n > 1]
    if dupes:
        fail("%s: duplicate id(s) %s" % (label, sorted(dupes)[:6]))

    controls = re.findall(r'aria-controls="([^"]+)"', html)
    for cid in controls:
        checked_controls += 1
        if ('id="%s"' % cid) not in html:
            fail("%s: aria-controls=%s has no matching id" % (label, cid))

    expands = re.findall(r'aria-expanded="([^"]*)"', html)
    bad = sorted(set(e for e in expands if e not in ("true", "false")))
    if bad:
        fail("%s: aria-expanded not true/false: %s" % (label, bad))

print("aria: %d aria-controls references, all resolve; no duplicate ids" % checked_controls)

# ── 4. category grouping on /hosts/ ─────────────────────────────────────────
hosts_html = read(file_for("/hosts/"))
sections = re.findall(
    r'<section class="host-group" id="([a-z-]+)"(.*?)</section>', hosts_html, re.S
)
if len(sections) != len(data["categories"]):
    fail("/hosts/: %d group sections, expected %d" % (len(sections), len(data["categories"])))

rank = {"broken-dns": 0, "down": 1, "guarded": 2, "ok": 3}
seen_total = 0
for cat_slug, body in sections:
    if cat_slug not in data["categories"]:
        fail("/hosts/: unknown category section %r" % cat_slug)
        continue
    found = re.findall(r'data-slug="([a-z0-9]+)"', body)
    expected = sorted([h["slug"] for h in hosts if h["category"] == cat_slug])
    if sorted(found) != expected:
        fail(
            "/hosts/%s: has %d cards, expected %d (%s)"
            % (
                cat_slug,
                len(found),
                len(expected),
                "extra=%s missing=%s"
                % (sorted(set(found) - set(expected))[:4], sorted(set(expected) - set(found))[:4]),
            )
        )
    seen_total += len(found)

    # The documented order is: every broken-dns first, then every down, then the
    # remainder - and the remainder ALPHABETICALLY, which interleaves ok and
    # guarded by title. A strict rank sort is the wrong assertion here: it would
    # fail on a page that is behaving exactly as specified.
    def titles(slugs):
        return [by_slug[s]["title"] for s in slugs]

    dead = [s for s in found if by_slug[s]["status"] == "broken-dns"]
    down = [s for s in found if by_slug[s]["status"] == "down"]
    rest = [s for s in found if by_slug[s]["status"] not in ("broken-dns", "down")]

    for name, block in (("broken-dns", dead), ("down", down), ("the remainder", rest)):
        if titles(block) != sorted(titles(block)):
            fail("/hosts/%s: %s not alphabetical by title: %s" % (cat_slug, name, titles(block)))

    # Positional contract: the broken-dns records are a prefix, the down records
    # follow, and the remainder comes last. Asserting the shape beats inferring a
    # split point, which is how the previous version of this check ended up
    # failing on pages that were correct.
    statuses = [by_slug[s]["status"] for s in found]
    expected_shape = (
        ["broken-dns"] * len(dead)
        + ["down"] * len(down)
        + [s for s in statuses[len(dead) + len(down) :]]
    )
    if statuses != expected_shape:
        fail(
            "/hosts/%s: order is not broken-dns, then down, then the rest: %s"
            % (cat_slug, statuses)
        )

    # the category heading must be the real title, not a stringified hash
    if ('<h2 class="host-group-title" id="%s-heading">' % cat_slug) not in body:
        fail("/hosts/%s: heading id/title mismatch" % cat_slug)
    if "=&gt;" in body or '"title"=&gt;' in body or '{"title"' in body:
        fail("/hosts/%s: a stringified hash leaked into the markup" % cat_slug)

if seen_total != len(hosts):
    fail("/hosts/: %d cards total, expected %d" % (seen_total, len(hosts)))
print(
    "grouping: %d groups, %d cards, every host exactly once, deadest-first"
    % (len(sections), seen_total)
)

# ── 5. navbar hosts menu ────────────────────────────────────────────────────
if "nav-hosts-btn" not in hosts_html:
    fail("navbar: the Hosts dropdown did not render")
else:
    rows = re.findall(r"nav-dropdown-item nav-hosts-item", hosts_html)
    raw_dots = collections.Counter(re.findall(r'nav-host-dot--([a-z-]+)"', hosts_html))
    # Class names, not statuses. nav.html maps broken-dns -> broken before it
    # becomes a class, so comparing the rendered classes against the raw statuses
    # in hosts.yml compares two different vocabularies and reports every
    # broken-dns record as a mismatch. The same mapping has to be applied here or
    # the check is meaningless; nav.html owns it and this mirrors it.
    expected_dots = collections.Counter(
        "broken" if h["status"] == "broken-dns" else h["status"] for h in hosts
    )

    # `dir` is the "All N hosts" link at the top of the menu, not a status. It is
    # counted separately and asserted separately: it is the menu's only guaranteed
    # escape hatch, and losing it would leave a 34-item dropdown with no way out
    # to the directory that explains any of it.
    if raw_dots.pop("dir", 0) != 1:
        fail("navbar: expected exactly one directory link, saw %d" % raw_dots.get("dir", 0))
    if len(rows) != len(hosts):
        fail("navbar: %d host rows, expected %d" % (len(rows), len(hosts)))
    if dict(raw_dots) != dict(expected_dots):
        fail("navbar: dots %s, expected %s" % (dict(raw_dots), dict(expected_dots)))

    # And every dot the menu emits must actually resolve to a rule somewhere.
    # This is the half that catches the real bug: a modifier that renders but
    # matches no selector leaves the row unstyled, which on this menu means the
    # eight most broken records in the zone look the calmest.
    emitted_dot_classes = set(re.findall(r"nav-host-dot nav-host-dot--([a-z0-9-]+)", hosts_html))
    defined_dot_classes = set()
    for css_rel in ("assets/css/main.css", "assets/css/hosts.css", "assets/css/network-ux.css"):
        css_path = os.path.join(SITE, *css_rel.split("/"))
        if os.path.isfile(css_path):
            defined_dot_classes |= set(re.findall(r"\.nav-host-dot--([a-z0-9-]+)", read(css_path)))
    orphans = sorted(emitted_dot_classes - defined_dot_classes)
    if orphans:
        fail("navbar: dot class(es) emitted with no matching rule: %s" % orphans)
    menu = re.search(
        r'(?s)<div class="nav-dropdown-menu" id="nav-hosts-menu">(.*?)</div>\s*</div>', hosts_html
    )
    hrefs = re.findall(r'href="([^"]+)"', menu.group(1)) if menu else []
    bad_links = []
    for h in hosts:
        want = "/artists/%s/" % h["slug"] if h["category"] == "artists" else "/%s/" % h["slug"]
        if want not in hrefs:
            bad_links.append((h["slug"], want))
    if bad_links:
        fail("navbar: %d hosts not linked to their page: %s" % (len(bad_links), bad_links[:4]))
    print(
        "navbar: Hosts menu, %d rows + 1 directory link, dots %s, "
        "every host linked to its page" % (len(rows), dict(raw_dots))
    )

# the menu must NOT render on a site that did not opt in
for site_dir in (
    r"C:\Users\Wout\Documents\Default Project\neohiro.github.io",
    r"C:\Users\Wout\Documents\Default Project\openstageisland.github.io",
):
    cfg = os.path.join(site_dir, "_config.yml")
    if os.path.isfile(cfg) and "show_host_menu: true" in read(cfg):
        fail(
            "%s: opted into the host menu without shipping a hosts.yml" % os.path.basename(site_dir)
        )

# ── 6. raw link + live url on every host page ───────────────────────────────
missing_raw, missing_url = [], []
for h in hosts:
    html = read(file_for(route_for(h)))
    if h.get("raw") and h["raw"] not in html:
        missing_raw.append(h["slug"])
    if h["url"] not in html:
        missing_url.append(h["slug"])
if missing_raw:
    fail("raw link missing on: %s" % missing_raw)
if missing_url:
    fail("live url missing on: %s" % missing_url)
print("links: raw + live URL present on all %d host pages" % len(hosts))

# ── 6b. every emitted modifier has a matching CSS rule ───────────────────────
# host-swirl.html once emitted `raw--broken-dns` while the stylesheet only knew
# `.raw--down` and `.raw--broken`. Nothing failed, so the strikethrough marking a
# dead raw link only ever fired for `down` - and the eight broken-dns records,
# the largest failure class in the zone, rendered as if healthy.
stylesheets = {}
for css_rel in ("assets/css/hosts.css", "assets/css/network-ux.css", "assets/css/main.css"):
    css_path = os.path.join(SITE, *css_rel.split("/"))
    if os.path.isfile(css_path):
        stylesheets[css_rel] = read(css_path)

if not stylesheets:
    fail("no stylesheets found in _site to cross-reference against")

for family in ("pill", "raw", "nav-host-dot", "host-action", "swirl-field", "host-dl-row"):
    emitted = set()
    for label, path in pages:
        if not os.path.isfile(path):
            continue
        emitted |= set(re.findall(r'class="[^"]*?\b%s--([a-z0-9-]+)' % family, read(path)))
    defined = set()
    for css in stylesheets.values():
        defined |= set(re.findall(r"\.%s--([a-z0-9-]+)" % family, css))
    orphaned = sorted(emitted - defined)
    if orphaned:
        fail("%s-- modifiers emitted but never defined in CSS: %s" % (family, orphaned))
print(
    "classes: every emitted <family>--<modifier> has a rule "
    "(%d stylesheets cross-referenced)" % len(stylesheets)
)

# ── 6c. an off-site link must not also be a swirl trigger ───────────────────
# hosts.js calls preventDefault() when the swirl target has zero height, which a
# collapsed card always does. So an anchor that carries both an external href and
# data-swirl-open never navigates, whatever it is labelled.
traps = []
for label, path in pages:
    if not os.path.isfile(path):
        continue
    for m in re.finditer(r"<a\b[^>]*>", read(path)):
        tag = m.group(0)
        if "data-swirl-open" not in tag:
            continue
        href = re.search(r'href="([^"]*)"', tag)
        if href and (href.group(1).startswith("http") or "://" in href.group(1)):
            traps.append("%s -> %s" % (label, href.group(1)[:60]))
if traps:
    fail(
        "%d off-site anchors also carry data-swirl-open and would never "
        "navigate: %s" % (len(traps), traps[:4])
    )
print("links: no off-site anchor is hijacked by the swirl opener")

# ── 7. asset references resolve ─────────────────────────────────────────────
assets = set()
for dp, dn, fn in os.walk(SITE):
    dn[:] = [d for d in dn if d not in (".git",)]
    for f in fn:
        assets.add(os.path.relpath(os.path.join(dp, f), SITE).replace(os.sep, "/"))

broken = set()
for label, path in pages:
    if not os.path.isfile(path):
        continue
    html = read(path)
    for m in re.findall(r'(?:href|src)="(/[^"#?]+)"', html):
        target = m.lstrip("/")
        if target in ("",) or target.endswith("/"):
            continue
        if target not in assets:
            broken.add("%s -> %s" % (label, m))
if broken:
    fail("%d asset refs resolve to nothing: %s" % (len(broken), sorted(broken)[:6]))
print("assets: every internal href/src resolves in _site")

# ── 8. status distribution matches the data ─────────────────────────────────
tally = collections.Counter(h["status"] for h in hosts)
hero = read(file_for("/hosts/"))
for status, count in tally.items():
    if ('pill pill--%s"' % ("broken" if status == "broken-dns" else status)) not in hero:
        fail("summary pills: no pill for %s" % status)
print("status: %s" % dict(tally))

# ── report ──────────────────────────────────────────────────────────────────
print()
if fails:
    print("FAILURES (%d):" % len(fails))
    for f in fails:
        print("  - %s" % f)
    sys.exit(1)
print("ALL CHECKS PASSED")
