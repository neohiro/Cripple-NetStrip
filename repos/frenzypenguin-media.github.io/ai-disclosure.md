---
layout: default
title: "AI disclosure"
description: "What the AI-assisted seal on this site means, what it does not mean, and how to check the work rather than take it on trust."
permalink: /ai-disclosure/
---

{%- comment -%}
This page had no <h1> at all: it opened straight into <h2>What the seal means</h2>.
A document with no top-level heading is a real accessibility and SEO defect — the
reader has no programmatic page title to navigate by, and crawlers have nothing
to treat as the page heading. The layout's <title> is not a substitute: it is
document metadata, not document structure. Restored here, matching the pattern
the other pages in this site use.
{%- endcomment -%}

<section class="section" id="ai-disclosure">
  <div class="container">
    <header class="section-header">
      <h1>AI disclosure</h1>
      <p class="section-lede">
        What the AI-assisted seal means, what it does not, and how to check the
        work instead of taking it on trust.
      </p>
    </header>
  </div>
</section>

<section class="section" id="what-the-seal-means">
  <div class="container">
    <header class="section-header">
      <h2>What the seal means</h2>
      <p>
        The <b>AI&#8209;assisted</b> mark in the corner of every page is an
        honesty notice, not a badge. It says that AI tooling was involved in
        producing or editing text on this site &mdash; drafting, rewriting,
        tightening prose, generating code, or checking it.
      </p>
      <p>
        It is on every page rather than buried on this one because a disclosure
        you have to go looking for is not a disclosure. If a page here was
        written without assistance, the mark still appears; the mark describes
        the site, not the individual article.
      </p>
    </header>
  </div>
</section>

<section class="section" id="what-it-does-not-mean">
  <div class="container">
    <header class="section-header">
      <h2>What it does not mean</h2>
      <p>
        The seal is not a quality rating, an accuracy guarantee, or a
        substitute for reading the thing. Concretely:
      </p>
      <dl class="host-dl">
        <div class="host-dl-row">
          <dt>Not verified by definition</dt>
          <dd>
            AI output is fluent and frequently wrong. Anything technical on
            this site should be treated as a draft until you have tried it.
          </dd>
        </div>
        <div class="host-dl-row">
          <dt>Not a substitute for sources</dt>
          <dd>
            Where a claim matters, the underlying source is linked. Follow the
            link rather than trusting the summary above it.
          </dd>
        </div>
        <div class="host-dl-row">
          <dt>Not a claim of independence</dt>
          <dd>
            Nothing here is generated to push you anywhere. There is no
            telemetry, no tracking pixel and no advertising on this site.
          </dd>
        </div>
      </dl>
    </header>
  </div>
</section>

<section class="section" id="how-to-check">
  <div class="container">
    <header class="section-header">
      <h2>How to check instead of trusting</h2>
      <p>
        This is the part that matters. Every claim above is checkable without
        taking anyone's word for it:
      </p>
      <ul>
        <li>
          <b>The hardening guides cite control references.</b> STIG and CIS
          identifiers are given so a claim can be checked against the published
          control rather than against this page's interpretation of it.
        </li>
        <li>
          <b>The code is public.</b> Everything described here lives in public
          repositories under
          <a href="https://github.com/neohiro" target="_blank" rel="noopener">github.com/neohiro</a>,
          with public history. Read it, fork it, or run it.
        </li>
        <li>
          <b>The corrections are public too.</b> An error that has been fixed
          leaves a trace in the history. If something here is wrong, the fix is
          a pull request, not a quiet edit.
        </li>
      </ul>
      <p>
        <a class="btn" href="{{ '/repositories/' | relative_url }}">Browse the repositories</a>
      </p>
    </header>
  </div>
</section>

<section class="section" id="report-a-problem">
  <div class="container">
    <header class="section-header">
      <h2>Report a problem</h2>
      <p>
        If a page states something false &mdash; a broken mitigation, an
        invented control reference, a security claim that does not hold
        &mdash; that is a bug and it is worth reporting. Security findings go
        through the private advisory channel described in
        <code>SECURITY.md</code>; everything else is an issue on the relevant
        repository.
      </p>
      <p>
        <a class="btn" href="{{ '/contact/' | relative_url }}">Contact</a>
        <a class="btn" href="{{ '/repositories/' | relative_url }}">Repositories</a>
      </p>
    </header>
  </div>
</section>
