---
layout: default
title: All Repositories
description: "Complete index of neohiro public repositories — security tools, privacy utilities, games, and developer tools"
permalink: /repositories/
---

<div class="repos-page" id="repositories">
  <div class="container">
    <nav class="repos-breadcrumb" aria-label="Breadcrumb">
      <a href="{{ '/' | relative_url }}">neohiro</a>
      <span aria-hidden="true">/</span>
      <span aria-current="page">All Repositories</span>
    </nav>

    <header class="repos-header">
      <h1>All Repositories</h1>
      <p class="repos-subtitle">{{ site.tools | size }} public projects — security, privacy, games, and developer tools</p>
    </header>

    <div class="repos-toolbar">
      <div class="repos-filters" role="group" aria-label="Filter repositories">
        <button class="filter-btn active" data-filter="all">All</button>
        <button class="filter-btn" data-filter="security">Security & Privacy</button>
        <button class="filter-btn" data-filter="developer">Developer Tools</button>
        <button class="filter-btn" data-filter="games">Games</button>
        <button class="filter-btn" data-filter="utilities">Utilities</button>
        <button class="filter-btn" data-filter="guides">Guides</button>
      </div>
      
      <input type="search" class="repo-search" placeholder="Search repositories..." aria-label="Search repositories">
    </div>

    <div class="repos-stats" aria-live="polite">
      <span class="stat"><strong id="count-all">{{ site.tools | size }}</strong> repositories</span>
      <span class="stat"><strong id="count-featured">{{ site.tools | where: "featured", true | size }}</strong> featured</span>
      <span class="stat"><strong id="count-stars">—</strong> total stars</span>
    </div>

    <div class="repos-grid" id="repos-grid">
      {% assign sorted_tools = site.tools | sort: "weight" %}
      {% for tool in sorted_tools %}
        {% assign categories = tool.category | split: ", " %}
        <article class="repo-card" 
                 data-category="{{ categories | join: ' ' }}"
                 data-name="{{ tool.title | downcase }}"
                 data-language="{{ tool.language | downcase }}"
                 itemscope itemtype="https://schema.org/SoftwareApplication">
          <div class="repo-card-icon" aria-hidden="true">
            {% if tool.icon %}
              {{ tool.icon }}
            {% else %}
              <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5">
                <rect x="3" y="3" width="18" height="18" rx="3"/>
                <path d="M9 12h6M12 9v6"/>
              </svg>
            {% endif %}
          </div>
          <h3 class="repo-card-name" itemprop="name">
            <a href="{{ tool.repo_url }}" target="_blank" rel="noopener">{{ tool.title }}</a>
            {% if tool.featured %}
              <span class="featured-badge" title="Featured">★</span>
            {% endif %}
          </h3>
          <p class="repo-card-desc" itemprop="description">{{ tool.tagline }}</p>
          <div class="repo-card-meta">
            <span class="repo-platform" itemprop="operatingSystem">{{ tool.platform }}</span>
            {% if tool.language %}
              <span class="repo-lang">{{ tool.language }}</span>
            {% endif %}
            {% if tool.category %}
              <span class="repo-category">{{ tool.category }}</span>
            {% endif %}
          </div>
          <div class="repo-card-links">
            <a href="{{ tool.permalink | relative_url }}" class="repo-link" itemprop="url">
              <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" width="14" height="14"><path d="M5 12h14M12 5l7 7-7 7"/></svg>
              Details
            </a>
            <a href="{{ tool.repo_url }}" class="repo-link repo-link-external" target="_blank" rel="noopener">
              <svg viewBox="0 0 24 24" fill="currentColor" width="14" height="14"><path d="M12 0C5.374 0 0 5.373 0 12c0 5.302 3.438 9.8 8.207 11.387.599.111.793-.261.793-.577v-2.234c-3.338.726-4.033-1.416-4.033-1.416-.546-1.387-1.333-1.756-1.333-1.756-1.089-.745.083-.729.083-.729 1.205.084 1.839 1.237 1.839 1.237 1.07 1.834 2.807 1.304 3.492.997.107-.775.418-1.305.762-1.604-2.665-.305-5.467-1.334-5.467-5.931 0-1.311.469-2.381 1.236-3.221-.124-.303-.535-1.524.117-3.176 0 0 1.008-.322 3.301 1.23A11.509 11.509 0 0112 5.803c1.02.005 2.047.138 3.006.404 2.291-1.552 3.297-1.23 3.297-1.23.653 1.653.242 2.874.118 3.176.77.84 1.235 1.911 1.235 3.221 0 4.609-2.807 5.624-5.479 5.921.43.372.823 1.102.823 2.222v3.293c0 .319.192.694.801.576C20.566 21.797 24 17.3 24 12c0-6.627-5.373-12-12-12z"/></svg>
              GitHub
            </a>
          </div>
          <div class="repo-card-actions">
            <a href="{{ tool.repo_url }}/issues" class="repo-action-btn repo-action-bug" target="_blank" rel="noopener" title="Bug Reports">
              <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" width="12" height="12"><path d="M12 2a10 10 0 0 1 10 10c0 5.52-4.48 10-10 10S2 17.52 2 12h2a8 8 0 1 0 16 0H2c0-4.41 3.59-8 8-8z"/></svg>
              Bug
            </a>
            <a href="{{ tool.repo_url }}/security" class="repo-action-btn repo-action-sec" target="_blank" rel="noopener" title="Security / Vulnerabilities">
              <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" width="12" height="12"><path d="M12 2L3 7v6c0 5.55 3.84 10.74 9 12 5.16-1.26 9-6.45 9-12V7l-9-5z"/></svg>
              Sec
            </a>
            <a href="{{ tool.repo_url }}/discussions" class="repo-action-btn repo-action-disc" target="_blank" rel="noopener" title="Discussions">
              <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" width="12" height="12"><path d="M21 15a2 2 0 0 1-2 2H7l-4 4V5a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2z"/></svg>
              Discuss
            </a>
          </div>
        </article>
      {% endfor %}
    </div>

    <footer class="repos-footer">
      <p>Part of <a href="https://github.com/neohiro" target="_blank" rel="noopener">neohiro</a> — {{ site.description }}</p>
      <p><a href="{{ '/' | relative_url }}">← Back to Home</a></p>
    </footer>
  </div>
</div>

<script>
document.addEventListener('DOMContentLoaded', function() {
  const grid = document.getElementById('repos-grid');
  const cards = grid.querySelectorAll('.repo-card');
  const filterBtns = document.querySelectorAll('.filter-btn');
  const searchInput = document.querySelector('.repo-search');
  const countAll = document.getElementById('count-all');
  const countFeatured = document.getElementById('count-featured');
  
  // Update counts
  if (countAll) countAll.textContent = cards.length;
  if (countFeatured) {
    const featured = document.querySelectorAll('.repo-card .featured-badge').length;
    countFeatured.textContent = featured;
  }

  // Filter functionality
  filterBtns.forEach(btn => {
    btn.addEventListener('click', function() {
      const filter = this.dataset.filter;
      
      filterBtns.forEach(b => b.classList.remove('active'));
      this.classList.add('active');
      
      cards.forEach(card => {
        const categories = card.dataset.category || '';
        const show = filter === 'all' || categories.includes(filter);
        card.style.display = show ? 'flex' : 'none';
        if (show) card.style.animation = 'fadeInUp 0.4s ease forwards';
      });
      
      const visible = document.querySelectorAll('.repo-card[style*="flex"], .repo-card:not([style*="none"])').length;
      if (countAll) countAll.textContent = visible;
    });
  });

  // Search functionality
  if (searchInput) {
    let debounce;
    searchInput.addEventListener('input', function() {
      clearTimeout(debounce);
      debounce = setTimeout(() => {
        const query = this.value.toLowerCase().trim();
        cards.forEach(card => {
          const name = card.dataset.name || '';
          const desc = card.querySelector('.repo-card-desc')?.textContent.toLowerCase() || '';
          const lang = card.dataset.language || '';
          const category = card.dataset.category || '';
          
          const match = !query || 
            name.includes(query) || 
            desc.includes(query) || 
            lang.includes(query) || 
            category.includes(query);
          
          const currentlyHidden = card.style.display === 'none';
          if (match && !currentlyHidden) {
            card.style.display = 'flex';
            card.style.animation = 'fadeInUp 0.3s ease forwards';
          } else if (!match) {
            card.style.display = 'none';
          }
        });
      }, 150);
    });
  }
});
</script>

<style>
.repos-page { padding: 40px 0 80px; }
.repos-breadcrumb { display: flex; align-items: center; gap: 8px; font-size: 0.875rem; color: var(--fg-subtle); margin-bottom: 40px; }
.repos-breadcrumb a { color: var(--fg-subtle); }
.repos-breadcrumb a:hover { color: var(--accent); }
.repos-breadcrumb span[aria-current] { color: var(--fg); font-weight: 500; }

.repos-header { text-align: center; margin-bottom: 32px; }
.repos-header h1 { margin-bottom: 12px; }
.repos-subtitle { font-size: 1.125rem; color: var(--fg-muted); max-width: 600px; margin: 0 auto; }

.repos-toolbar { display: flex; justify-content: space-between; align-items: center; gap: 20px; margin-bottom: 24px; flex-wrap: wrap; }
.repos-filters { display: flex; gap: 10px; flex-wrap: wrap; }
.filter-btn { padding: 8px 18px; font-size: 0.8125rem; font-weight: 500; color: var(--fg-muted); background: var(--bg-card); border: 1px solid var(--border); border-radius: 999px; cursor: pointer; transition: all var(--transition); }
.filter-btn:hover { color: var(--fg); border-color: var(--border-hover); }
.filter-btn.active { color: white; background: var(--accent); border-color: var(--accent); }

.repo-search { padding: 10px 16px; font-size: 0.875rem; color: var(--fg); background: var(--bg-card); border: 1px solid var(--border); border-radius: 999px; min-width: 240px; }
.repo-search:focus { outline: none; border-color: var(--accent); box-shadow: 0 0 0 3px var(--accent-dim); }
.repo-search::placeholder { color: var(--fg-subtle); }

.repos-stats { display: flex; justify-content: center; gap: 32px; margin-bottom: 32px; font-size: 0.875rem; color: var(--fg-subtle); flex-wrap: wrap; }
.repos-stats .stat { display: flex; align-items: center; gap: 6px; }
.repos-stats strong { color: var(--fg); font-family: var(--font-mono); }

.repos-grid { display: grid; grid-template-columns: repeat(auto-fill, minmax(300px, 1fr)); gap: 20px; }
.repo-card { display: flex; flex-direction: column; padding: 24px; background: var(--bg-card); border: 1px solid var(--border); border-radius: var(--radius); transition: all var(--transition); position: relative; opacity: 0; }
.repo-card.visible { opacity: 1; }
.repo-card::before { content: ''; position: absolute; top: 0; left: 0; right: 0; height: 3px; background: linear-gradient(90deg, var(--accent), var(--accent-strong)); border-radius: var(--radius) var(--radius) 0 0; opacity: 0; transition: opacity var(--transition); }
.repo-card:hover { border-color: var(--accent); transform: translateY(-4px); box-shadow: var(--shadow-lg); }
.repo-card:hover::before { opacity: 1; }

.repo-card-icon { display: inline-flex; align-items: center; justify-content: center; width: 48px; height: 48px; border-radius: var(--radius-sm); background: var(--accent-dim); color: var(--accent); margin-bottom: 16px; }
.repo-card-icon svg { width: 24px; height: 24px; }

.repo-card-name { margin-bottom: 10px; font-size: 1.0625rem; display: flex; align-items: baseline; gap: 8px; flex-wrap: wrap; }
.repo-card-name a { color: var(--fg); text-decoration: none; transition: color var(--transition); }
.repo-card-name a:hover { color: var(--accent); }
.featured-badge { font-size: 0.75rem; color: var(--orange); animation: pulse 2s ease-in-out infinite; }
@keyframes pulse { 0%, 100% { transform: scale(1); } 50% { transform: scale(1.15); } }

.repo-card-desc { font-size: 0.875rem; line-height: 1.5; color: var(--fg-muted); margin-bottom: 16px; flex: 1; }

.repo-card-meta { display: flex; flex-wrap: wrap; gap: 8px; margin-bottom: 16px; font-size: 0.75rem; font-family: var(--font-mono); }
.repo-platform, .repo-lang, .repo-category { padding: 3px 8px; background: var(--bg); border: 1px solid var(--border); border-radius: 4px; color: var(--fg-subtle); }

.repo-card-links { display: flex; gap: 10px; margin-top: auto; }
.repo-link { display: inline-flex; align-items: center; gap: 6px; padding: 10px 16px; font-size: 0.8125rem; font-weight: 600; border-radius: var(--radius-sm); background: var(--accent-dim); color: var(--accent); border: 1px solid transparent; transition: all var(--transition); text-decoration: none; }
.repo-link:hover { background: var(--accent); color: white; }
.repo-link-external { background: transparent; color: var(--fg-muted); border-color: var(--border); }
.repo-link-external:hover { background: var(--bg); color: var(--fg); border-color: var(--border-hover); }

.repo-card-actions { display: flex; gap: 6px; margin-top: 10px; }
.repo-action-btn { display: inline-flex; align-items: center; gap: 4px; padding: 4px 10px; font-size: 0.72rem; font-weight: 600; border-radius: 4px; text-decoration: none; border: 1px solid; transition: all var(--transition); }
.repo-action-bug { color: var(--orange); border-color: var(--orange); background: rgba(255,167,38,0.06); }
.repo-action-bug:hover { background: rgba(255,167,38,0.15); }
.repo-action-sec { color: var(--red); border-color: var(--red); background: rgba(239,83,80,0.06); }
.repo-action-sec:hover { background: rgba(239,83,80,0.15); }
.repo-action-disc { color: var(--green); border-color: var(--green); background: rgba(102,187,106,0.06); }
.repo-action-disc:hover { background: rgba(102,187,106,0.15); }

.repos-footer { text-align: center; margin-top: 48px; padding-top: 24px; border-top: 1px solid var(--border); color: var(--fg-subtle); font-size: 0.875rem; }
.repos-footer a { color: var(--fg-subtle); }
.repos-footer a:hover { color: var(--accent); }

@keyframes fadeInUp { from { opacity: 0; transform: translateY(20px); } to { opacity: 1; transform: translateY(0); } }

@media (max-width: 768px) {
  .repos-grid { grid-template-columns: 1fr; }
  .repos-toolbar { flex-direction: column; align-items: stretch; }
  .repos-filters { justify-content: center; }
  .repo-search { width: 100%; min-width: 0; }
  .repos-stats { gap: 16px; font-size: 0.8125rem; }
}
</style>