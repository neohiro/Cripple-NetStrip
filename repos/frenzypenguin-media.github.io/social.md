---
layout: default
title: Social — neohiro
description: "GitHub Social — the decentralized social layer for the neohiro ecosystem."
permalink: /social/
---

<section class="section" id="social">
  <div class="container">
    <header class="section-header">
      <h1>Social</h1>
      <p class="section-subtitle">Everywhere the network is reachable, and what each one is for.</p>
    </header>
  </div>
</section>

<section class="section" id="github-social">
  <div class="container">
    <header class="section-header">
      <h2>GitHub Social</h2>
      <p class="section-subtitle">The decentralized social layer for neohiro. React to profiles, send invites, track journey — all backed by GitHub.</p>
    </header>

    <div class="social-widget-wrapper" data-gh-social="neohiro" data-mode="tab" data-theme="auto">
      <div class="social-loading">
        <span class="spinner"></span>
        <span>Loading GitHub Social for <code>neohiro</code>…</span>
      </div>
    </div>

    <p class="social-fallback">
      Not on neohiro? Search any GitHub user:
      <input type="text" id="social-search" placeholder="e.g. octocat" maxlength="256" class="social-search-input" />
      <button id="social-search-btn" class="btn btn-secondary btn-sm">Render</button>
    </p>

    <div id="social-other-wrapper" class="social-widget-wrapper" style="display:none"></div>

    <details class="social-embed-help">
      <summary>Embed on your own site</summary>
      <p>Add this anywhere — works as a Web Component, data-attribute, or programmatic API:</p>
      <pre><code>&lt;script src="https://frenzypenguin-media.github.io/github-social/embed.js"&gt;&lt;/script&gt;

&lt;!-- Web Component --&gt;
&lt;gh-social-tab login="octocat"&gt;&lt;/gh-social-tab&gt;

&lt;!-- or compact embed --&gt;
&lt;div data-gh-social="octocat" data-mode="embed"&gt;&lt;/div&gt;

&lt;!-- or graph only --&gt;
&lt;div data-gh-social="octocat" data-mode="graph"&gt;&lt;/div&gt;</code></pre>
    </details>
  </div>
</section>

<script type="module">
  import { GHSocialWidget } from "https://frenzypenguin-media.github.io/embed.js";

  const searchBtn = document.getElementById("social-search-btn");
  const searchInput = document.getElementById("social-search");
  const otherWrapper = document.getElementById("social-other-wrapper");

  function renderOther() {
    const login = (searchInput.value || "").trim();
    if (!login || !/^[A-Za-z0-9][A-Za-z0-9-]{0,38}$/.test(login)) {
      alert("Enter a valid GitHub login");
      return;
    }
    otherWrapper.dataset.ghSocial = login;
    otherWrapper.dataset.mode = "tab";
    otherWrapper.style.display = "block";
    GHSocialWidget.mount(otherWrapper, login, { mode: "tab" });
    otherWrapper.scrollIntoView({ behavior: "smooth", block: "start" });
  }

  if (searchBtn) searchBtn.addEventListener("click", renderOther);
  if (searchInput) searchInput.addEventListener("keydown", e => { if (e.key === "Enter") renderOther(); });

  // Auto-mount the primary widget (data-gh-social="neohiro") once the module loads.
  // The embed.js module's own auto-mount handles it, but the static import ensures
  // the script is loaded for users who arrived on /social/ before the embed script
  // tag in <head> had a chance to run.
  const main = document.querySelector('[data-gh-social="neohiro"]');
  if (main) GHSocialWidget.mount(main, "neohiro", { mode: "tab" });
</script>

<style>
.social-widget-wrapper {
  position: relative;
  width: 100%;
  border-radius: 12px;
  overflow: hidden;
  border: 1px solid var(--border);
  background: var(--bg-alt);
  box-shadow: 0 4px 24px rgba(0, 0, 0, 0.3);
  margin-bottom: 1.5rem;
  padding: 1.25rem;
  min-height: 200px;
}

.social-loading {
  display: flex;
  align-items: center;
  gap: 0.75rem;
  color: var(--fg-muted);
  font-size: 0.9rem;
  justify-content: center;
  padding: 2rem 0;
}

.spinner {
  width: 18px;
  height: 18px;
  border: 2px solid var(--border);
  border-top-color: var(--accent);
  border-radius: 50%;
  animation: social-spin 0.8s linear infinite;
}

@keyframes social-spin {
  to { transform: rotate(360deg); }
}

.social-fallback {
  text-align: center;
  font-size: 0.875rem;
  color: var(--fg-muted);
  margin-bottom: 1.5rem;
  display: flex;
  gap: 0.5rem;
  align-items: center;
  justify-content: center;
  flex-wrap: wrap;
}

.social-search-input {
  background: var(--bg);
  border: 1px solid var(--border);
  color: var(--fg);
  padding: 6px 10px;
  border-radius: 6px;
  font-size: 13px;
  font-family: monospace;
  outline: none;
  min-width: 180px;
}

.social-search-input:focus {
  border-color: var(--accent);
}

.social-embed-help {
  background: var(--bg-alt);
  border: 1px solid var(--border);
  border-radius: 8px;
  padding: 1rem 1.25rem;
  font-size: 0.875rem;
  color: var(--fg-muted);
}

.social-embed-help summary {
  cursor: pointer;
  font-weight: 600;
  color: var(--fg);
  font-size: 0.95rem;
  margin-bottom: 0.5rem;
}

.social-embed-help pre {
  background: var(--bg);
  border: 1px solid var(--border);
  border-radius: 6px;
  padding: 0.75rem 1rem;
  overflow-x: auto;
  margin: 0.5rem 0;
}

.social-embed-help code {
  font-family: "JetBrains Mono", "SFMono-Regular", Consolas, monospace;
  font-size: 0.8rem;
  color: var(--fg);
  white-space: pre;
}
</style>
