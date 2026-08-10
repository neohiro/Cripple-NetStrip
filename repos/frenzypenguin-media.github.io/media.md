---
layout: default
title: Media - FrenzyPenguin Media
description: "The real FrenzyPenguin Media back catalogue: DJ-set livestreams, hardware and analogue Goa Trance sets, techno guest slots, the YPCR radio series and a pyro short. Every entry is a real upload."
permalink: /media/
---

{%- comment -%}
media.md — the full back catalogue.

REWRITTEN, and the reason is worth keeping in the file. This page used to ship
an empty <div id="video-grid"> and let assets/js/main.js fill it at runtime from
a hard-coded array. All six of those entries shared one YouTube id,
dQw4w9WgXcQ, which resolves to "Rick Astley – Never Gonna Give You Up". Each was
labelled with an invented title, an invented duration and an invented view count
("Windows Hardening Deep Dive · 124K views"). The header promised "Security
hardening deep-dives, exploit mitigation tutorials and privacy engineering" and
the footer asked readers to "Subscribe for weekly security engineering content".
None of that exists on the channel.

What does exist is here now: twenty-two real uploads, rendered at build time from
_data/videos.yml, each id verified through YouTube's oEmbed API. The set is DJ
lives — Goa Trance mostly, plus techno, house, drum and bass, one psytrance set
from this year, a showreel, the numbered YPCR radio series and one short film
about fire. The copy below describes that instead of the thing that would have
been more impressive to claim.
{%- endcomment -%}

{%- assign featured = site.data.videos.videos | where: "featured", true -%}

<div class="media-page" id="media">
  <div class="container">
    <nav class="media-breadcrumb" aria-label="Breadcrumb">
      <a href="{{ '/' | relative_url }}">frenzypenguin.media</a>
      <span aria-hidden="true">/</span>
      <span aria-current="page">Media</span>
    </nav>

    <header class="media-header">
      <div class="media-brand">
        <span class="media-logo" aria-hidden="true">◍</span>
        <div>
          <h1>The back catalogue</h1>
          <p class="media-tagline">
            Everything we have published, in the order we would show it to you.
          </p>
        </div>
      </div>
    </header>

    {%- comment -%}
      Lead card. Large, and the showreel, because it is the only minute on the
      channel that represents the studio rather than one night of it.
    {%- endcomment -%}
    {%- assign lead = site.data.videos.videos | where: "id", "tULwnXVgHug" | first -%}
    {%- if lead %}
    <section class="media-lead" aria-label="Showreel">
      <ul class="vfacade-grid vfacade-grid--lead">
        {% include video-facade.html video=lead lead=true %}
      </ul>
    </section>
    {%- endif %}

    <section aria-labelledby="media-latest-h">
      <h2 id="media-latest-h" class="media-h2">Where to start</h2>
      <p class="media-lede">
        If you have never heard us, the reel above is the shortest honest answer.
        If you want the thing we are actually known for, it is a Triquetra set
        played on hardware &mdash; no laptop in sight, which in 2019 and 2020 was
        still an unusual thing to do on a virtual stage.
      </p>
      <ul class="vfacade-grid vfacade-grid--lead">
        {%- for v in featured -%}
          {%- unless v.id == "tULwnXVgHug" -%}
        {% include video-facade.html video=v %}
        {%- endunless -%}
        {%- endfor -%}
      </ul>
    </section>

    {%- comment -%}
      Everything else, grouped by genre. The groups are built from the data
      rather than hand-listed, so adding a row to _data/videos.yml is enough to
      have it appear here in the right place.
    {%- endcomment -%}
    {%- assign rest = site.data.videos.videos | where_exp: "v", "v.featured != true" -%}
    {%- assign genres = rest | map: "genre" | compact | uniq | sort -%}
    {%- for g in genres -%}
      {%- assign in_genre = rest | where: "genre", g -%}
      {%- if in_genre.size > 0 %}
    <section class="media-genre" aria-labelledby="genre-{{ forloop.index }}">
      <h2 id="genre-{{ forloop.index }}" class="media-h2">
        <span class="media-h2__genre">{{ g }}</span>
        <span class="media-h2__count">{{ in_genre.size }} {% if in_genre.size == 1 %}set{% else %}sets{% endif %}</span>
      </h2>
      <ul class="vfacade-grid">
        {%- for v in in_genre -%}
        {% include video-facade.html video=v %}
        {%- endfor -%}
      </ul>
    </section>
      {%- endif -%}
    {%- endfor %}

    <footer class="media-footer">
      <p>
        Channel: <a href="{{ site.data.videos.channel.handle }}" target="_blank" rel="noopener">youtube.com/@FrenzyPenguinMedia</a>
        {%- if site.data.videos.channel.gaming_handle %}
        &middot; <a href="{{ site.data.videos.channel.gaming_handle }}" target="_blank" rel="noopener">@FrenzyPenguinGaming</a>
        {%- endif %}
      </p>
      <p>
        <a href="{{ site.data.videos.channel.bluesky }}" target="_blank" rel="noopener">Bluesky</a>
        &middot;
        <a href="{{ site.data.videos.channel.linkedin }}" target="_blank" rel="noopener">LinkedIn</a>
        &middot;
        <a href="{{ '/artists/' | relative_url }}">Artists we have hosted</a>
      </p>
      {%- comment -%}
        Deliberately no subscribe button and no "new video every week". The
        channel has not published weekly since 2020 and we would rather say
        nothing than promise a cadence we do not keep.
      {%- endcomment -%}
      <p class="media-footer__note">
        Press play on any card to watch it here, or open it on YouTube. Nothing
        loads from YouTube until you choose to.
      </p>
    </footer>
  </div>
</div>

<style>
.media-page { padding: 40px 0 80px; }
.media-breadcrumb { display: flex; align-items: center; gap: 8px; font-size: 0.875rem; color: var(--fg-subtle); margin-bottom: 40px; }
.media-breadcrumb a { color: var(--fg-subtle); }
.media-breadcrumb a:hover { color: var(--accent); }
.media-breadcrumb span[aria-current] { color: var(--fg); font-weight: 500; }

.media-header { display: flex; align-items: center; gap: 24px; margin-bottom: 48px; padding-bottom: 32px; border-bottom: 1px solid var(--border); }
.media-logo { font-size: 3rem; line-height: 1; }
.media-brand h1 { font-size: clamp(2rem, 4vw, 3rem); margin-bottom: 8px; }
.media-tagline { font-size: 1.125rem; color: var(--fg-muted); margin: 0; }

.media-h2 {
  display: flex; align-items: baseline; gap: 12px; flex-wrap: wrap;
  font-size: 1.25rem; letter-spacing: -0.01em; margin: 56px 0 6px;
}
.media-h2__genre { color: var(--fg); }
.media-h2__count {
  font-family: var(--font-mono); font-size: 0.75rem; font-weight: 400;
  color: var(--fg-subtle); letter-spacing: 0.06em; text-transform: uppercase;
}
.media-lede {
  max-width: 62ch; color: var(--fg-muted); margin: 0 0 28px; line-height: 1.65;
}
.media-genre:first-of-type .media-h2 { margin-top: 40px; }

.media-footer {
  text-align: center; margin-top: 64px; padding-top: 32px;
  border-top: 1px solid var(--border); color: var(--fg-subtle);
}
.media-footer a { color: var(--accent); }
.media-footer a:hover { color: var(--accent-strong); }
.media-footer p { margin: 8px 0; }
.media-footer__note { max-width: 52ch; margin-inline: auto; font-size: 0.875rem; }

@media (max-width: 768px) {
  .media-header { flex-direction: column; text-align: center; gap: 16px; }
}
</style>
