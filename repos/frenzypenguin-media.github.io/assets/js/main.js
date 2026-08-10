// neohiro.github.io - Main JavaScript
// Matrix rain, glitch transitions, parallax, card animations, video embeds

(function() {
  'use strict';

  // Module-scoped reference to the GlitchTransition instance, so the
  // visibility-reset helper (registered before DOMContentLoaded) can clear its
  // internal `active` latch after a bfcache restore. Without this, the restored
  // page keeps active === true and silently stops animating page transitions.
  let glitchInstance = null;

  // ============================================
  // MATRIX RAIN BACKGROUND
  // ============================================
  class MatrixRain {
    constructor() {
      this.canvas = document.getElementById('matrix-canvas');
      if (!this.canvas) return;
      this.ctx = this.canvas.getContext('2d');
      this.chars = 'ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789$#@%&*';
      this.fontSize = 14;
      this.columns = 0;
      this.drops = [];
      this.running = false;
      this.init();
    }

    init() {
      this.resize();
      window.addEventListener('resize', () => this.resize());
      this.running = true;
      this.animate();
    }

    resize() {
      this.canvas.width = window.innerWidth;
      this.canvas.height = window.innerHeight;
      this.columns = Math.floor(this.canvas.width / this.fontSize);
      this.drops = Array(this.columns).fill(1);
    }

    animate() {
      if (!this.running) return;
      
      this.ctx.fillStyle = 'rgba(11, 14, 18, 0.05)';
      this.ctx.fillRect(0, 0, this.canvas.width, this.canvas.height);
      
      this.ctx.font = `${this.fontSize}px 'JetBrains Mono', monospace`;
      this.ctx.fillStyle = '#7c4dff';
      
      for (let i = 0; i < this.drops.length; i++) {
        const char = this.chars[Math.floor(Math.random() * this.chars.length)];
        const x = i * this.fontSize;
        const y = this.drops[i] * this.fontSize;
        
        this.ctx.fillText(char, x, y);
        
        if (y > this.canvas.height && Math.random() > 0.975) {
          this.drops[i] = 0;
        }
        this.drops[i]++;
      }
      
      requestAnimationFrame(() => this.animate());
    }

    destroy() {
      this.running = false;
    }
  }

  // ============================================
  // GLITCH TRANSITION OVERLAY
  // ============================================
  class GlitchTransition {
    constructor() {
      this.overlay = document.getElementById('glitch-overlay');
      this.active = false;
    }

    trigger(targetUrl, isInternal = true) {
      if (this.active) return;
      this.active = true;
      
      const text = this.overlay.querySelector('.glitch-text');
      text.textContent = isInternal ? 'NEOHIRO' : 'REDIRECTING';
      
      this.overlay.classList.add('active');
      
      // Glitch animation
      let glitchCount = 0;
      const glitchInterval = setInterval(() => {
        text.style.transform = `translate(${Math.random() * 4 - 2}px, ${Math.random() * 4 - 2}px) skew(${Math.random() * 4 - 2}deg)`;
        text.style.textShadow = `${Math.random() * 10 - 5}px ${Math.random() * 10 - 5}px 0 #ff00ff, ${Math.random() * 10 - 5}px ${Math.random() * 10 - 5}px 0 #00ffff`;
        glitchCount++;
        if (glitchCount > 8) clearInterval(glitchInterval);
      }, 50);
      
      setTimeout(() => {
        clearInterval(glitchInterval);
        text.style.transform = '';
        text.style.textShadow = '';
        
        if (isInternal) {
          // Navigate behind the opaque overlay. We deliberately do NOT fade
          // document.body here: that inline `opacity: 0` is captured by the
          // bfcache entry for this page and is exactly what left the page blank
          // on Back/Forward until a manual refresh. The full-screen overlay is
          // the transition, so the body fade added nothing but the bug.
          setTimeout(() => {
            window.location.href = targetUrl;
          }, 150);
        } else {
          // External links - brief pause then redirect
          setTimeout(() => {
            window.open(targetUrl, '_blank', 'noopener,noreferrer');
            this.overlay.classList.remove('active');
            this.active = false;
          }, 300);
        }
      }, 400);
    }
  }

  // ============================================
  // PARALLAX BACKGROUND
  // ============================================
  class ParallaxBackground {
    constructor() {
      this.hero = document.querySelector('.hero');
      this.ticking = false;
      if (this.hero) this.init();
    }

    init() {
      window.addEventListener('mousemove', (e) => {
        if (!this.ticking) {
          window.requestAnimationFrame(() => {
            this.update(e.clientX, e.clientY);
            this.ticking = false;
          });
          this.ticking = true;
        }
      });
    }

    update(x, y) {
      const centerX = window.innerWidth / 2;
      const centerY = window.innerHeight / 2;
      const deltaX = (x - centerX) / centerX;
      const deltaY = (y - centerY) / centerY;
      
      const cards = document.querySelectorAll('.tool-card, .guide-card, .community-card');
      cards.forEach((card, i) => {
        const factor = (i % 3 + 1) * 2;
        card.style.transform = `translate(${deltaX * factor}px, ${deltaY * factor}px)`;
      });
    }
  }

  // ============================================
  // CARD INTERACTIONS & NEON EFFECTS
  // ============================================
  class CardEffects {
    constructor() {
      this.cards = document.querySelectorAll('.tool-card, .guide-card, .community-card, .repo-card');
      this.init();
    }

    init() {
      this.cards.forEach(card => {
        card.addEventListener('mouseenter', (e) => this.onEnter(e, card));
        card.addEventListener('mouseleave', (e) => this.onLeave(e, card));
        card.addEventListener('mousemove', (e) => this.onMove(e, card));
        card.addEventListener('click', (e) => this.onClick(e, card));
      });
    }

    onEnter(e, card) {
      card.style.transition = 'transform 0.3s cubic-bezier(0.25, 0.46, 0.45, 0.94), box-shadow 0.3s ease';
      card.style.transform = 'translateY(-8px) scale(1.02)';
      card.style.boxShadow = '0 20px 60px rgba(124, 77, 255, 0.25), 0 0 40px rgba(124, 77, 255, 0.1)';
      
      // Neon border pulse
      card.style.animation = 'neon-pulse 2s ease-in-out infinite';
      
      // Add glow to icon
      const icon = card.querySelector('.tool-icon, .guide-icon, .repo-card-icon');
      if (icon) {
        icon.style.boxShadow = '0 0 30px var(--accent)';
        icon.style.transform = 'scale(1.1) rotate(5deg)';
      }
    }

    onLeave(e, card) {
      card.style.transition = 'transform 0.5s cubic-bezier(0.25, 0.46, 0.45, 0.94), box-shadow 0.5s ease';
      card.style.transform = '';
      card.style.boxShadow = '';
      card.style.animation = '';
      
      const icon = card.querySelector('.tool-icon, .guide-icon, .repo-card-icon');
      if (icon) {
        icon.style.boxShadow = '';
        icon.style.transform = '';
      }
    }

    onMove(e, card) {
      const rect = card.getBoundingClientRect();
      const x = e.clientX - rect.left;
      const y = e.clientY - rect.top;
      const centerX = rect.width / 2;
      const centerY = rect.height / 2;
      
      const rotateX = (y - centerY) / centerY * 5;
      const rotateY = (centerX - x) / centerX * 5;
      
      card.style.transform = `perspective(1000px) rotateX(${rotateX}deg) rotateY(${rotateY}deg) translateY(-8px) scale(1.02)`;
    }

    onClick(e, card) {
      // Ripple effect
      const ripple = document.createElement('div');
      ripple.className = 'ripple';
      const rect = card.getBoundingClientRect();
      ripple.style.left = `${e.clientX - rect.left}px`;
      ripple.style.top = `${e.clientY - rect.top}px`;
      card.appendChild(ripple);
      
      setTimeout(() => ripple.remove(), 600);
    }
  }

  // ============================================
  // YOUTUBE VIDEO EMBED MANAGER
  // ============================================
  // DEPRECATED — no longer builds a video wall. Kept as a no-op shim so that a
  // stale `new VideoEmbedManager()` elsewhere cannot resurrect the old
  // behaviour, and so the removal is greppable.
  //
  // What it used to do, and why it is gone: init() built #video-grid from a
  // hard-coded array in which all six entries shared the id dQw4w9WgXcQ —
  // which YouTube's oEmbed resolves to "Rick Astley – Never Gonna Give You Up".
  // Each card paired that placeholder with an invented title, an invented
  // duration and an invented view count, so the page presented six convincing
  // "Windows Hardening Deep Dive · 124K views" cards that were entirely
  // fictional. It also meant the media wall was invisible to search engines and
  // to any visitor without JavaScript, since the markup only ever existed at
  // runtime.
  //
  // The wall is now rendered at build time by _includes/video-facade.html from
  // _data/videos.yml, where every id is a real upload verified through YouTube's
  // oEmbed API, and assets/js/video-facade.js only swaps an iframe in on click.
  // That is server-rendered (indexable, works without JS), ships no YouTube
  // JavaScript until the visitor presses play, and cannot invent a title.
  class VideoEmbedManager {
    constructor() {
      this.retired = true;
      // init() is called from the constructor on purpose. The shim exists so a
      // stale `new VideoEmbedManager()` elsewhere cannot resurrect the old
      // behaviour, and a deprecation notice only earns its keep if it actually
      // reaches the console. Leaving init() uncalled made the shim dead code
      // that still looked live, which is the same failure this class was written
      // to remove.
      this.init();
    }

    init() {
      if (window.console && window.console.info) {
        window.console.info(
          '[fpm] VideoEmbedManager is retired and does nothing. The video wall ' +
          'is server-rendered by _includes/video-facade.html from _data/videos.yml; ' +
          'click-to-play lives in assets/js/video-facade.js.'
        );
      }
    }
  }

  // ============================================
  // SMOOTH SCROLL & INTERSECTION OBSERVER
  // ============================================
  class ScrollAnimations {
    constructor() {
      this.observer = null;
      this.init();
    }

    init() {
      this.observer = new IntersectionObserver((entries) => {
        entries.forEach(entry => {
          if (entry.isIntersecting) {
            entry.target.classList.add('visible');
            this.observer.unobserve(entry.target);
          }
        });
      }, {
        threshold: 0.1,
        rootMargin: '0px 0px -50px 0px'
      });

      document.querySelectorAll('.tool-card, .guide-card, .community-card, .repo-card, .section-header, .video-card').forEach(el => {
        el.classList.add('fade-in');
        this.observer.observe(el);
      });
    }
  }

  // ============================================
  // TYPING ANIMATION (Enhanced)
  // ============================================
  class TypingAnimation {
    constructor() {
      this.element = document.querySelector('.typing-prefix');
      this.cursor = document.querySelector('.typing-cursor');
      if (!this.element || !this.cursor) return;
      
      this.phrases = [
        "Open-source security hardening for Windows & Linux.",
        "Exploit mitigation catalogs that actually work.",
        "Encrypted DNS, firewalls, honeypots — zero fluff.",
        "STIG-style Windows hardening in one command.",
        "Network visibility. Traffic control. Zero trust.",
        "Built by FrenzyPenguin Media. No telemetry. Ever.",
        "Auditd, AppArmor, Tor — Linux post-install automated.",
        "Your system. Your rules. Our tooling.",
        "Defense is the best defense.",
        "One command. Zero compromise."
      ];
      
      this.index = 0;
      this.charIndex = 0;
      this.deleting = false;
      this.typeSpeed = 45;
      this.deleteSpeed = 15;
      this.holdTime = 2500;
      this.pauseTime = 500;
      
      this.start();
    }

    start() {
      this.type();
    }

    type() {
      const phrase = this.phrases[this.index];
      
      if (this.deleting) {
        this.element.textContent = phrase.substring(0, this.charIndex - 1);
        this.charIndex--;
      } else {
        this.element.textContent = phrase.substring(0, this.charIndex + 1);
        this.charIndex++;
      }
      
      let delay = this.deleting ? this.deleteSpeed : this.typeSpeed;
      
      if (!this.deleting && this.charIndex === phrase.length) {
        delay = this.holdTime;
        this.deleting = true;
      } else if (this.deleting && this.charIndex === 0) {
        this.deleting = false;
        this.index = (this.index + 1) % this.phrases.length;
        delay = this.pauseTime;
      }
      
      setTimeout(() => this.type(), delay);
    }
  }

  // ============================================
  // REPOSITORY FILTER & SEARCH
  // ============================================
  class RepoFilter {
    constructor() {
      this.grid = document.getElementById('repos-grid');
      this.buttons = document.querySelectorAll('.filter-btn');
      this.search = document.querySelector('.repo-search');
      this.init();
    }

    init() {
      this.buttons.forEach(btn => {
        btn.addEventListener('click', () => this.filter(btn.dataset.filter));
      });
      
      if (this.search) {
        let debounce;
        this.search.addEventListener('input', () => {
          clearTimeout(debounce);
          debounce = setTimeout(() => this.searchRepos(this.search.value), 200);
        });
      }
    }

    filter(category) {
      this.buttons.forEach(b => b.classList.remove('active'));
      document.querySelector(`[data-filter="${category}"]`)?.classList.add('active');
      
      const cards = this.grid.querySelectorAll('.repo-card');
      cards.forEach(card => {
        const cats = card.dataset.category || '';
        const show = category === 'all' || cats.includes(category);
        card.style.display = show ? 'flex' : 'none';
        if (show) card.style.animation = 'fadeInUp 0.4s ease forwards';
      });
    }

    searchRepos(query) {
      const q = query.toLowerCase().trim();
      const cards = this.grid.querySelectorAll('.repo-card');
      
      cards.forEach(card => {
        const name = card.dataset.name || '';
        const desc = card.querySelector('.repo-card-desc')?.textContent.toLowerCase() || '';
        const lang = card.dataset.language || '';
        const cat = card.dataset.category || '';
        
        const match = !q || name.includes(q) || desc.includes(q) || lang.includes(q) || cat.includes(q);
        card.style.display = match ? 'flex' : 'none';
      });
    }
  }

  // ============================================
  // LINK GUARD (Confirmation + Repo Tabs + Iframe Embed)
  // ============================================
  // Catches clicks to GitHub/external destinations, shows a confirmation
  // popup with information about the destination, a quick repo-tab jump
  // selector, and an in-page iframe preview. Visitors can open in a new
  // tab, open directly, or jump to a specific tab (Issues, Discussions,
  // Security, Wiki, Pulse, etc.) without leaving the site first.

  const REPO_CATALOG = [
    { name: 'windows',            desc: 'Windows hardening (STIG)' },
    { name: 'Cripple-NetStrip',   desc: 'Network hardening & debloater' },
    { name: 'ExploitProtection',  desc: 'Exploit Protection GUI' },
    { name: 'metapod',            desc: 'Windows 10/11 hardening GUI' },
    { name: 'tailscale-exit',     desc: 'Tailscale exit / SOCKS / Funnel' },
    { name: 'opencode',           desc: 'Open source coding agent' },
    { name: 'opencode-config',    desc: 'OpenCode plugin / agent pipeline' },
    { name: 'auto-resume',        desc: 'Self-healing OpenCode sessions' },
        { name: 'opencode-hub',       desc: 'Cross-device OpenCode sync' },
    { name: 'wingman-hub',        desc: 'Private assistant hub' },
    { name: 'dashboard',          desc: 'Live ops dashboard' },
    { name: 'LLM',                desc: 'Free models router' },
    { name: 'frenzypenguin-media',desc: 'FrenzyPenguin Media site' },
    { name: 'neohiro',            desc: 'Org profile README' },
    { name: 'linux',              desc: 'Linux hardening' },
    { name: 'ubuntu',             desc: 'Ubuntu install/hardening' },
    { name: 'openstage-island.github.io', desc: 'Virtual events space' },
    { name: 'dnscrypt-proxy-gui', desc: 'dnscrypt-proxy GUI' },
    { name: 'BlackGlass',         desc: 'Second Life chat viewer' },
    { name: 'HoneyScan',          desc: 'Passive honeypot' },
    { name: 'SystemMonitor',      desc: 'System health monitor' },
    { name: 'NewsAggregator',     desc: 'Global news feed' },
    { name: 'LANScan',            desc: 'ARP/ICMP network scanner' },
    { name: 'NetMatrix',          desc: 'Connections monitor' },
    { name: 'DNSLookup',          desc: 'DNS lookup tool' },
    { name: 'ShadowSocks',        desc: 'ShadowSocks client' },
    { name: 'MoodTracker',        desc: 'Wellbeing diary' },
    { name: 'MusicPlay',          desc: 'Audio player' },
    { name: 'ClockWidget',        desc: 'Desktop clock widget' },
    { name: 'FileManager',        desc: 'File manager' },
    { name: 'Calculator',         desc: 'Python calculator' },
    { name: 'Godmode',            desc: 'Windows God Mode activator' },
    { name: 'htmlinfo',           desc: 'HTML info scraper' },
    { name: 'GoogleCommand',      desc: 'TTS Google Assistant' },
    { name: 'ZombieShoot',        desc: 'Zombie shooter game' },
    { name: 'TristarMania',       desc: 'Space shooter' },
    { name: 'Tetris',             desc: 'Retro Tetris' },
    { name: 'GhostMaze',          desc: '2D RPG' },
    { name: 'SecondLife',         desc: 'LSL snippets' },
    { name: 'rcv',                desc: 'Recovery tokens' },
    { name: 'private-assistant',  desc: 'Private assistant' }
  ];

  const REPO_TABS = [
    { id: 'overview',  label: 'Overview',          icon: '📖', path: '' },
    { id: 'issues',    label: 'Bug Reports',       icon: '🐞', path: '/issues' },
    { id: 'security',  label: 'Security Vulns',    icon: '🛡️', path: '/security' },
    { id: 'discussions', label: 'Discussions',     icon: '💬', path: '/discussions' },
    { id: 'pulse',     label: 'Pulse',             icon: '📊', path: '/pulse' },
    { id: 'wiki',      label: 'Wiki',              icon: '📚', path: '/wiki' },
    { id: 'releases',  label: 'Releases',          icon: '🚀', path: '/releases' },
    { id: 'code',      label: 'Code',              icon: '⌨️', path: '' },
    { id: 'pulls',     label: 'Pull Requests',     icon: '🔀', path: '/pulls' },
    { id: 'actions',   label: 'Actions',           icon: '⚙️', path: '/actions' }
  ];

  class LinkGuard {
    constructor() {
      this.owner = 'neohiro';
      this.overlay = null;
      this.iframe = null;
      this.lastTrigger = null;
      this.init();
    }

    init() {
      // Build a static overlay element once
      this.overlay = document.createElement('div');
      this.overlay.className = 'link-guard';
      this.overlay.setAttribute('role', 'dialog');
      this.overlay.setAttribute('aria-modal', 'true');
      this.overlay.setAttribute('aria-labelledby', 'link-guard-title');
      this.overlay.innerHTML = `
        <div class="link-guard-backdrop" data-close></div>
        <div class="link-guard-card">
          <header class="link-guard-header">
            <div class="link-guard-icon" aria-hidden="true">🔗</div>
            <div class="link-guard-heading">
              <h2 id="link-guard-title">Leaving neohiro</h2>
              <p class="link-guard-sub" id="link-guard-sub">External destination</p>
            </div>
            <button class="link-guard-close" data-close aria-label="Close">×</button>
          </header>
          <section class="link-guard-body">
            <div class="link-guard-meta" id="link-guard-meta"></div>
            <div class="link-guard-url" id="link-guard-url"></div>
            <div class="link-guard-frame" id="link-guard-frame" hidden>
              <iframe id="link-guard-iframe" title="Destination preview"
                      loading="lazy" referrerpolicy="no-referrer"></iframe>
            </div>
          </section>
          <section class="link-guard-tabs" id="link-guard-tabs" hidden>
            <label class="link-guard-section-label">Quick jump to repository section</label>
            <div class="link-guard-row">
              <select class="link-guard-repo" id="link-guard-repo" aria-label="Repository"></select>
              <select class="link-guard-tab" id="link-guard-tab" aria-label="Section">
                ${REPO_TABS.map(t => `<option value="${t.id}">${t.icon} ${t.label}</option>`).join('')}
              </select>
              <button class="link-guard-go" id="link-guard-go" type="button">Open</button>
            </div>
            <p class="link-guard-hint">Opens the chosen tab of the chosen repo in a new tab — no extra clicks.</p>
          </section>
          <footer class="link-guard-actions">
            <button class="link-guard-btn link-guard-btn-ghost" data-close>Stay here</button>
            <button class="link-guard-btn link-guard-btn-primary" id="link-guard-open">Open in new tab</button>
          </footer>
        </div>
      `;
      document.body.appendChild(this.overlay);

      this.iframe = this.overlay.querySelector('#link-guard-iframe');

      // Populate repo catalog
      const repoSel = this.overlay.querySelector('#link-guard-repo');
      REPO_CATALOG.forEach(r => {
        const opt = document.createElement('option');
        opt.value = r.name;
        opt.textContent = `${r.name} — ${r.desc}`;
        repoSel.appendChild(opt);
      });

      // Bind events
      this.overlay.addEventListener('click', (e) => {
        if (e.target.matches('[data-close]')) this.close();
      });
      this.overlay.querySelector('#link-guard-open').addEventListener('click', () => this.openInNewTab());
      this.overlay.querySelector('#link-guard-go').addEventListener('click', () => this.openRepoTab());

      document.addEventListener('keydown', (e) => {
        if (e.key === 'Escape' && this.overlay.classList.contains('active')) this.close();
      });

      this.bindTriggers();
    }

    bindTriggers() {
      // Re-bind on every card/repo render
      const wire = (link) => {
        if (link.__linkGuardBound) return;
        link.__linkGuardBound = true;
        link.addEventListener('click', (e) => {
          if (e.metaKey || e.ctrlKey || e.shiftKey || e.altKey) return;
          const href = link.href;
          if (!href) return;
          if (this.shouldIntercept(href, link)) {
            e.preventDefault();
            this.open(href, link);
          }
        });
      };

      // Catch external links and github.com/* links
      const all = document.querySelectorAll('a[href]');
      all.forEach(wire);

      // Watch for dynamically added links
      const obs = new MutationObserver((muts) => {
        muts.forEach(m => m.addedNodes.forEach(n => {
          if (n.nodeType !== 1) return;
          if (n.matches && n.matches('a[href]')) wire(n);
          if (n.querySelectorAll) n.querySelectorAll('a[href]').forEach(wire);
        }));
      });
      obs.observe(document.body, { childList: true, subtree: true });
    }

    shouldIntercept(href, link) {
      // Skip in-page anchors and internal site links
      if (href.startsWith('#')) return false;
      const u = new URL(href, window.location.href);
      if (u.hostname === window.location.hostname && !u.hostname.includes('github.com')) return false;

      // Skip sponsor and a few friendly external links
      if (link && (link.dataset.linkGuard === 'off')) return false;

      // Intercept github.com and unknown external links
      if (u.hostname === 'github.com' || u.hostname.endsWith('.github.com')) return true;
      if (u.hostname === 'linktr.ee' || u.hostname === 'youtube.com' || u.hostname === 'www.youtube.com') return true;

      // Default: intercept anything that opens in new tab OR anything external
      if (link && link.target === '_blank') return true;
      if (u.hostname !== window.location.hostname) return true;
      return false;
    }

    inferRepo(url) {
      try {
        const u = new URL(url);
        if (u.hostname === 'github.com' || u.hostname === 'www.github.com') {
          const m = u.pathname.match(/^\/([^\/]+)\/([^\/]+)/);
          if (m && m[1].toLowerCase() === this.owner) return m[2];
        }
      } catch (e) {}
      return null;
    }

    isIssuesPage(url) {
      return /\/issues(\?|\/|$|#)/.test(url);
    }
    isSecurityPage(url) {
      return /\/security(\?|\/|$|#)/.test(url);
    }
    isDiscussionsPage(url) {
      return /\/discussions(\?|\/|$|#)/.test(url);
    }

    describe(url) {
      const u = new URL(url);
      const host = u.hostname;
      const repo = this.inferRepo(url);
      const desc = (() => {
        if (host.includes('github.com')) {
          if (this.isIssuesPage(url))    return 'Bug reports & open issues for the repository.';
          if (this.isSecurityPage(url))  return 'Security advisories for the repository — please disclose privately when possible.';
          if (this.isDiscussionsPage(url)) return 'Community discussions for the repository.';
          if (/\/releases(\?|\/|$|#)/.test(url)) return 'Releases / downloads for the repository.';
          if (/\/actions(\?|\/|$|#)/.test(url))  return 'CI / Actions runs for the repository.';
          if (/\/wiki(\?|\/|$|#)/.test(url))     return 'Project wiki.';
          if (/\/sponsors/.test(u.pathname))     return 'Sponsor the project via GitHub Sponsors.';
          if (/\/[^\/]+\/[^\/]+$/.test(u.pathname)) {
            return `GitHub repository page${repo ? ` for ${repo}` : ''}.`;
          }
          return 'A page on github.com.';
        }
        if (host.includes('youtube.com')) return 'A YouTube page — video / channel / playlist.';
        if (host.includes('linktr.ee'))   return 'Linktree — all public links for the project.';
        if (host.includes('sponsor'))     return 'Sponsor page.';
        return `External destination on ${host}.`;
      })();

      const isIssues = this.isIssuesPage(url);
      const isSecurity = this.isSecurityPage(url);
      const isDisc = this.isDiscussionsPage(url);
      const isRepo = !!repo && /^\/[^\/]+\/[^\/]+(\/)?$/.test(u.pathname);

      return { repo, isIssues, isSecurity, isDisc, isRepo, desc };
    }

    open(url, trigger) {
      this.lastTrigger = trigger;
      this.lastUrl = url;
      let info, u;
      try {
        info = this.describe(url);
        u = new URL(url);
      } catch (e) {
        // Malformed URL — bypass modal and open directly
        this.close();
        if (url) window.open(url, '_blank', 'noopener,noreferrer');
        return;
      }

      // Title + sub
      this.overlay.querySelector('#link-guard-title').textContent =
        (u.hostname.includes('github.com') ? 'Open on GitHub' :
         u.hostname.includes('youtube')    ? 'Open on YouTube' :
         u.hostname.includes('linktr')     ? 'Open Linktree' :
         'Open external page');
      this.overlay.querySelector('#link-guard-sub').textContent = info.desc;

      // Meta chips
      const meta = this.overlay.querySelector('#link-guard-meta');
      const chips = [];
      chips.push(`<span class="link-guard-chip"><strong>Host</strong> ${this.escape(u.hostname)}</span>`);
      if (info.isRepo) chips.push(`<span class="link-guard-chip"><strong>Repo</strong> ${this.escape(info.repo)}</span>`);
      if (info.isIssues) chips.push(`<span class="link-guard-chip chip-warn">Bug reports</span>`);
      if (info.isSecurity) chips.push(`<span class="link-guard-chip chip-alert">Security</span>`);
      if (info.isDisc) chips.push(`<span class="link-guard-chip">Discussions</span>`);
      meta.innerHTML = chips.join('');

      // URL display
      this.overlay.querySelector('#link-guard-url').textContent = u.href;

      // Iframe preview (blocked for github.com and youtube.com)
      const frame = this.overlay.querySelector('#link-guard-frame');
      const tryIframe = this.isEmbeddable(u);
      if (tryIframe) {
        this.iframe.src = u.href;
        frame.hidden = false;
      } else {
        frame.hidden = true;
        this.iframe.src = 'about:blank';
      }

      // Quick jump: only for github.com/<owner>/<repo> base paths
      const tabsEl = this.overlay.querySelector('#link-guard-tabs');
      const repoSel = this.overlay.querySelector('#link-guard-repo');
      const tabSel = this.overlay.querySelector('#link-guard-tab');
      if (info.isRepo) {
        repoSel.value = info.repo;
        if (info.isIssues) tabSel.value = 'issues';
        else if (info.isSecurity) tabSel.value = 'security';
        else if (info.isDisc) tabSel.value = 'discussions';
        else tabSel.value = 'overview';
        tabsEl.hidden = false;
      } else {
        tabsEl.hidden = true;
      }

      this.overlay.classList.add('active');
      this.overlay.querySelector('#link-guard-open').focus();
    }

    isEmbeddable(u) {
      if (u.hostname.includes('github.com')) return false;
      if (u.hostname.includes('youtube.com')) return false;
      if (u.protocol !== 'https:') return false;
      return true;
    }

    openInNewTab() {
      if (this.lastUrl) window.open(this.lastUrl, '_blank', 'noopener,noreferrer');
      this.close();
    }

    openRepoTab() {
      const repo = this.overlay.querySelector('#link-guard-repo').value;
      const tabId = this.overlay.querySelector('#link-guard-tab').value;
      const tab = REPO_TABS.find(t => t.id === tabId) || REPO_TABS[0];
      const url = `https://github.com/${this.owner}/${repo}${tab.path}`;
      window.open(url, '_blank', 'noopener,noreferrer');
      this.close();
    }

    close() {
      this.overlay.classList.remove('active');
      this.iframe.src = 'about:blank';
    }

    escape(s) {
      return String(s).replace(/[&<>"']/g, c => ({
        '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;'
      }[c]));
    }
  }

  // ============================================
  // INITIALIZATION
  // ============================================
  function init() {
    // Initialize all components
    new MatrixRain();
    const glitchTx = new GlitchTransition();
    glitchInstance = glitchTx;
    resetVisibility(); // fade out any stale overlay on load/refresh/back
    new ParallaxBackground();
    new CardEffects();
    new ScrollAnimations();
    new TypingAnimation();
    new RepoFilter();
    new VideoEmbedManager();
    new LinkGuard();
    
    // Bind glitch transitions to internal links
    document.querySelectorAll('a[href^="/"], a[href^="#"], a[href^="./"]').forEach(link => {
      if (link.hostname === window.location.hostname || link.href.startsWith('/') || link.href.startsWith('#')) {
        link.addEventListener('click', (e) => {
          if (!e.metaKey && !e.ctrlKey && !e.shiftKey) {
            e.preventDefault();
            glitchTx.trigger(link.href, true);
          }
        });
      }
    });
    
    // External links
    document.querySelectorAll('a[target="_blank"]').forEach(link => {
      link.addEventListener('click', (e) => {
        glitchTx.trigger(link.href, false);
      });
    });
    
    // Add ripple CSS
    const style = document.createElement('style');
    style.textContent = `
      .ripple {
        position: absolute;
        width: 20px; height: 20px;
        background: radial-gradient(circle, rgba(124,77,255,0.4) 0%, transparent 70%);
        border-radius: 50%;
        transform: translate(-50%, -50%) scale(0);
        animation: ripple 0.6s ease-out;
        pointer-events: none;
        z-index: 10;
      }
      @keyframes ripple { to { transform: translate(-50%, -50%) scale(20); opacity: 0; } }
      
      .fade-in { opacity: 0; transform: translateY(30px); transition: opacity 0.6s ease, transform 0.6s ease; }
      .fade-in.visible { opacity: 1; transform: translateY(0); }
      
      .video-card { opacity: 0; transform: translateY(20px); animation: fadeInUp var(--delay) ease forwards; }
      @keyframes fadeInUp { to { opacity: 1; transform: translateY(0); } }
      
      .video-thumbnail { position: relative; border-radius: var(--radius); overflow: hidden; }
      .video-thumbnail img { width: 100%; height: auto; display: block; transition: transform 0.3s ease; }
      .video-card:hover .video-thumbnail img { transform: scale(1.05); }
      .video-overlay { position: absolute; inset: 0; background: rgba(11,14,18,0.8); display: flex; align-items: center; justify-content: center; opacity: 0; transition: opacity 0.3s ease; }
      .video-card:hover .video-overlay { opacity: 1; }
      .play-btn { background: linear-gradient(135deg, var(--accent), var(--accent-strong)); border: none; border-radius: 50%; width: 72px; height: 72px; cursor: pointer; transition: transform 0.2s, box-shadow 0.2s; box-shadow: 0 8px 32px rgba(124,77,255,0.4); }
      .play-btn:hover { transform: scale(1.15); box-shadow: 0 12px 48px rgba(124,77,255,0.6); }
      .duration { position: absolute; bottom: 12px; right: 12px; background: rgba(0,0,0,0.8); color: #fff; padding: 4px 8px; border-radius: 4px; font-size: 0.75rem; font-family: var(--font-mono); }
      .video-info { padding: 12px; }
      .video-info h4 { font-size: 0.9375rem; margin-bottom: 4px; color: var(--fg); }
      .video-meta { font-size: 0.75rem; color: var(--fg-subtle); font-family: var(--font-mono); }
      
      .video-modal { position: fixed; inset: 0; background: rgba(0,0,0,0.95); z-index: 10000; display: flex; align-items: center; justify-content: center; opacity: 0; visibility: hidden; transition: opacity 0.3s ease, visibility 0.3s ease; }
      .video-modal.active { opacity: 1; visibility: visible; }
      .video-modal-content { position: relative; width: 90%; max-width: 900px; aspect-ratio: 16/9; }
      .video-close { position: absolute; top: -50px; right: 0; background: none; border: none; color: var(--fg-muted); font-size: 2rem; cursor: pointer; transition: color 0.2s; }
      .video-close:hover { color: var(--accent); }
      .video-wrapper { width: 100%; height: 100%; border-radius: var(--radius); overflow: hidden; }
      .video-wrapper iframe { width: 100%; height: 100%; border: none; }
      
      @keyframes neon-pulse { 0%,100% { box-shadow: 0 20px 60px rgba(124,77,255,0.25), 0 0 40px rgba(124,77,255,0.1); } 50% { box-shadow: 0 20px 80px rgba(124,77,255,0.4), 0 0 80px rgba(124,77,255,0.2); } }
      
      /* pointer-events is the load-bearing part of the idle state.
         This overlay is position:fixed; inset:0 at z-index 9999, above the back-to-top
         control (z-index 940) and the bottom dock (900). Relying on
         "visibility: hidden already removes it from hit-testing" was not enough:
         elementFromPoint at the arrow's centre returned this div, so every click on
         the arrow was swallowed and the control looked permanently dead. This CSS is
         also injected at runtime, so for the moment before injection the element is an
         unstyled div with no positioning and no pointer-events rule at all.
         pointer-events:none closes both gaps; the .active state turns it back on. */
      .glitch-overlay { position: fixed; inset: 0; background: var(--bg); z-index: 9999; display: flex; align-items: center; justify-content: center; opacity: 0; visibility: hidden; pointer-events: none; transition: opacity 0.2s, visibility 0.2s; }
      .glitch-overlay.active { opacity: 1; visibility: visible; pointer-events: auto; }
      .glitch-text { font-family: var(--font-ui); font-size: clamp(3rem, 10vw, 8rem); font-weight: 700; color: var(--fg); letter-spacing: 0.1em; text-transform: uppercase; }
    `;
    document.head.appendChild(style);
  }

  // ============================================
  // PROMPT FIELD — animated placeholder + dynamic strings polling
  // ============================================
  //   Any input/textarea with [data-fpm-typing-placeholder] gets:
  //     - a typing animation of brand quotes (until the user starts typing)
  //     - a 60s poller that swaps in admin-triggered dynamic strings
  //   See fpm-typing.js for the engine. The endpoint defaults to /api/strings;
  //   override with <body data-fpm-strings-endpoint="https://render.example.com/api/strings">.
  function initPromptField() {
    if (!window.FpmTyping) return;
    // Defensive: stop any pre-existing poller / observers before re-attach
    // (this can happen on soft-navigations or hot-reload).
    if (window.__fpmPromptFieldCleanup) window.__fpmPromptFieldCleanup();

    const attach = () => {
      const instances = window.FpmTyping.autoAttach({ mirrorClass: 'fpm-typing-mirror' });
      instances.forEach(({ el }) => {
        if (!el) return;
        const wrapper = el.parentNode;
        if (wrapper) wrapper.classList.add('fpm-prompt-field');
        const update = () => {
          if (wrapper) wrapper.classList.toggle('has-content', !!(el.value && el.value.length));
        };
        el.addEventListener('input', update);
        el.addEventListener('focus', update);
        el.addEventListener('blur', update);
        update();
      });
      return instances;
    };

    let instances = attach();
    // Start the dynamic-strings poller pointing at the render service.
    const endpoint = (document.body && document.body.dataset.fpmStringsEndpoint)
      || (window.FPM_STRINGS_ENDPOINT)
      || 'https://wingman-hub-api.onrender.com/api/strings';
    let poller = window.FpmTyping.startPoller ? window.FpmTyping.startPoller({ endpoint, instances }) : null;

    // Throttled re-attach on DOM mutations: only when new elements with
    // the data-attr appear. We avoid the chatty "re-attach every mutation"
    // anti-pattern that would leak timers and replace mirrors constantly.
    let scheduledAttach = false;
    const obs = new MutationObserver(() => {
      if (scheduledAttach) return;
      scheduledAttach = true;
      // rAF debounce: at most one attach per frame
      requestAnimationFrame(() => {
        scheduledAttach = false;
        const fresh = document.querySelectorAll('[data-fpm-typing-placeholder]');
        // Only re-attach if there are NEW elements we haven't already mirrored
        const known = new Set(instances.map(({ el }) => el));
        let changed = false;
        fresh.forEach(el => { if (!known.has(el)) changed = true; });
        if (changed) {
          instances = attach();
          if (poller && poller.setInstances) poller.setInstances(instances);
        }
      });
    });
    obs.observe(document.body, { childList: true, subtree: true });

    window.__fpmPromptFieldCleanup = () => {
      try { obs.disconnect(); } catch (_) {}
      if (poller && poller.stop) { try { poller.stop(); } catch (_) {} }
      instances.forEach(({ inst }) => { if (inst && inst.stop) { try { inst.stop(); } catch (_) {} } });
    };
  }

  // Both scripts use `defer`, so they parse in document order before
  // DOMContentLoaded. We just need to wait for the DOM.
  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', initPromptField);
  } else { initPromptField(); }

  // Defensive visibility reset. Registered at module scope so it is guaranteed
  // to exist even if init() throws, and wired to both 'pageshow' (covers bfcache
  // restores, where event.persisted === true) and 'visibilitychange'. Clears any
  // stale inline opacity/transition a previous navigation may have left on
  // <body> and deactivates the full-screen glitch overlay. Idempotent.
  function resetVisibility() {
    try {
      if (document.body) {
        document.body.style.opacity = '1';
        document.body.style.transition = '';
      }
      const overlay = document.getElementById('glitch-overlay');
      if (overlay) overlay.classList.remove('active');
      if (glitchInstance) glitchInstance.active = false;
    } catch (e) {}
  }
  window.addEventListener('pageshow', resetVisibility);
  document.addEventListener('visibilitychange', () => {
    if (document.visibilityState === 'visible') resetVisibility();
  });

  // Start when DOM is ready
  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', init);
  } else {
    init();
  }
})();