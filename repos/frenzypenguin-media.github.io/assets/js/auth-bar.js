/**
 * Shared AI dock — bottom bar with persistent sway + GitHub OAuth.
 * SSOT: template-shared/assets/js/auth-bar.js
 *
 * Scope (narrower than it used to be):
 *   - The dock renders the Assistant tab plus the signed-in state. AI and Contact
 *     are ONE surface now; there is no Contact tab and no dock-local composer.
 *   - The conversation itself is the screenwide sheet mounted by network-ux.js,
 *     and messages are delivered by brain-bridge (see network/brain_bridge/).
 *     Clicking Assistant therefore goes through AuthBar.selectTab(null) to
 *     collapse the dock, not through selectTab('ai').
 *   - Login is triggered from the TOP bar (nav.html) via AuthBar.selectTab('login').
 *
 * Flow:
 *   1. User clicks Login (top bar) → the login panel slides up from the dock.
 *   2. Browser redirects to github.com/login/oauth/authorize.
 *   3. GitHub redirects back to /auth/callback?code=...&state=...
 *   4. Server (functions/api/auth.js) exchanges code → session_id + role.
 *   5. Auth bar reads #session= from URL, stores in localStorage, displays UI.
 *
 * Required:
 *   - auth-bar.html (markup, with id="ai-dock"...)
 *   - auth-bar.css  (styles, .ai-dock...)
 *   - functions/api/auth.js (server endpoint) reachable from this origin
 *
 * Optional globals:
 *   window.OAUTH_CLIENT_ID       — required; configure per host
 *   window.OAUTH_REDIRECT_ORIGIN — override auth callback origin (default: window.location.origin)
 *   window.AUTH_CALLBACK         — override callback path (default: /auth/callback)
 *   window.AUTH_STATE_ENDPOINT   — override state endpoint (default: /auth/state)
 *   window.Auth                  — legacy dashboard Auth object (overrides)
 *
 * Backwards-compat: exposes window.AuthBar.open(panelId) for older callers.
 */
(function () {
  'use strict';

  const GH_USER = 'neohiro';
  const SESSION_KEY = 'neohiro_session_v1';
  const OAUTH_STATE_KEY = 'neohiro_oauth_state_v1';
  const AUTH_CALLBACK = (typeof window !== 'undefined' && window.AUTH_CALLBACK) || '/auth/callback';
  const AUTH_STATE_ENDPOINT = (typeof window !== 'undefined' && window.AUTH_STATE_ENDPOINT) || '/auth/state';
  const SESSION_MAX_AGE_MS = 24 * 60 * 60 * 1000;

  const state = { activeTab: null };

  function $(id) { return document.getElementById(id); }
  function qa(sel, ctx) { return Array.from((ctx || document).querySelectorAll(sel)); }

  function show(panel) {
    if (!panel) return;
    panel.hidden = false;
    panel.removeAttribute('hidden');
    panel.removeAttribute('data-closing');
  }
  function hide(panel) {
    if (!panel) return;
    panel.hidden = true;
    panel.setAttribute('hidden', '');
    panel.removeAttribute('data-closing');
  }

  function closeAll() {
    qa('.ai-dock__panel').forEach(hide);
    qa('.ai-dock__tab').forEach(t => {
      t.setAttribute('aria-selected', 'false');
      t.classList.remove('active');
    });
    hide($('ai-dock__backdrop'));
    state.activeTab = null;
  }

  function selectTab(tabId) {
    if (!tabId) { closeAll(); return; }
    qa('.ai-dock__panel').forEach(hide);
    qa('.ai-dock__tab').forEach(t => {
      t.setAttribute('aria-selected', 'false');
      t.classList.remove('active');
    });
    const tab = $(`ai-dock__tab--${tabId}`);
    const panel = $(`ai-dock__panel--${tabId}`);
    if (!tab || !panel) return;
    tab.setAttribute('aria-selected', 'true');
    tab.classList.add('active');
    show(panel);
    state.activeTab = tabId;

    // The backdrop dims the page behind the dock panels that need focus
    // (login, account). The Assistant tab deliberately does NOT open a panel —
    // it hands off to the screenwide conversation sheet instead.
    const backdrop = $('ai-dock__backdrop');
    if (backdrop) backdrop.hidden = !(tabId === 'login' || tabId === 'user');

    if (tabId === 'login') {
      setTimeout(() => { const btn = $('ai-dock__gh-btn'); if (btn) btn.focus(); }, 350);
    }
  }

  function appendSize(avatarUrl, size) {
    if (!avatarUrl) return '';
    return avatarUrl + (avatarUrl.indexOf('?') >= 0 ? '&' : '?') + 's=' + size;
  }

  function readSessionIdFromUrl() {
    const hash = location.hash || '';
    const m = hash.match(/session=([a-f0-9]+)/i);
    if (m) return m[1];
    const u = new URLSearchParams(location.search);
    return u.get('session');
  }

  async function fetchState() {
    try {
      const r = await fetch(AUTH_STATE_ENDPOINT, { credentials: 'same-origin' });
      if (!r.ok) return null;
      const data = await r.json();
      return data && data.state;
    } catch (_) { return null; }
  }

  function storeSession(sessionId, profile, role) {
    if (!sessionId) return null;
    const record = {
      session_id: sessionId,
      login: profile.login,
      name: profile.name || null,
      avatar_url: profile.avatar_url || null,
      role: role || 'user',
      expiresAt: Date.now() + SESSION_MAX_AGE_MS,
    };
    localStorage.setItem(SESSION_KEY, JSON.stringify(record));
    return record;
  }

  function readStoredSession() {
    try {
      const raw = localStorage.getItem(SESSION_KEY);
      if (!raw) return null;
      const s = JSON.parse(raw);
      if (!s || !s.session_id || !Number.isFinite(s.expiresAt) || s.expiresAt < Date.now()) {
        localStorage.removeItem(SESSION_KEY);
        return null;
      }
      return s;
    } catch (_) { return null; }
  }

  function clearSession() {
    const s = readStoredSession();
    if (s && s.session_id) {
      fetch(`/auth/session?session=${encodeURIComponent(s.session_id)}`, { method: 'DELETE' }).catch(() => {});
    }
    localStorage.removeItem(SESSION_KEY);
  }

  function setUser(session) {
    const loginTab = $('ai-dock__tab--login');
    const dashboardTab = $('ai-dock__tab--dashboard');
    const userTab = $('ai-dock__tab--user');
    const dashboardLink = $('ai-dock__dashboard-link');
    const userDashboardLink = $('ai-dock__user-dashboard-link');

    if (session && session.login) {
      if (loginTab) loginTab.classList.add('hidden');
      if (dashboardTab) dashboardTab.classList.remove('hidden');
      if (userTab) userTab.classList.remove('hidden');

      const avatar = $('ai-dock__avatar');
      const avatarLg = $('ai-dock__user-avatar-lg');
      const username = $('ai-dock__username');
      const userName = $('ai-dock__user-name');
      const userLogin = $('ai-dock__user-login');
      const role = $('ai-dock__role');

      if (avatar) avatar.src = appendSize(session.avatar_url, 40);
      if (avatarLg) avatarLg.src = appendSize(session.avatar_url, 72);
      if (username) username.textContent = session.login;
      if (userName) userName.textContent = session.name || session.login;
      if (userLogin) userLogin.textContent = '@' + session.login;
      if (role) {
        const r = session.role || (session.login === GH_USER ? 'godadmin' : 'user');
        role.textContent = r;
        role.className = 'ai-dock__role-badge ai-dock__role-badge--' + r;
      }

      const dash = `https://neohiro.github.io/dashboard/?user=${encodeURIComponent(session.login)}`;
      if (dashboardLink) dashboardLink.href = dash;
      if (userDashboardLink) userDashboardLink.href = dash;

      syncNavLoginSlot(session);
    } else {
      if (loginTab) loginTab.classList.remove('hidden');
      if (dashboardTab) dashboardTab.classList.add('hidden');
      if (userTab) userTab.classList.add('hidden');
      syncNavLoginSlot(null);
    }
  }

  /**
   * Reflect session into any in-page nav LOGIN slot
   * (.nav-login-slot). The slot accepts either an <a> (when signed out)
   * or a <button>+<span> (when signed in) injected by Jekyll.
   *
   * We never overwrite site-defined nav content — only toggle hidden state
   * and update text labels.
   */
  function syncNavLoginSlot(session) {
    qa('.nav-login-slot').forEach(slot => {
      const out = slot.querySelector('[data-mode="out"]');
      const inn = slot.querySelector('[data-mode="in"]');
      if (session && session.login) {
        if (out) out.hidden = true;
        if (inn) {
          inn.hidden = false;
          const nameEl = inn.querySelector('[data-bind="login"]');
          const roleEl = inn.querySelector('[data-bind="role"]');
          const avatarEl = inn.querySelector('[data-bind="avatar"]');
          if (nameEl) nameEl.textContent = session.login;
          if (roleEl) {
            const r = session.role || (session.login === GH_USER ? 'godadmin' : 'user');
            roleEl.textContent = r;
            roleEl.className = 'nav-login-role nav-login-role--' + r;
          }
          if (avatarEl && session.avatar_url) avatarEl.src = appendSize(session.avatar_url, 32);
        }
      } else {
        if (out) out.hidden = false;
        if (inn) inn.hidden = true;
      }
    });
  }

  async function startOAuth() {
    const clientId = (typeof window !== 'undefined' && window.OAUTH_CLIENT_ID) || '';
    if (!clientId) {
      console.warn('[ai-dock] OAUTH_CLIENT_ID not set — login unavailable on this host');
      return;
    }
    const stateVal = await fetchState();
    if (!stateVal) {
      console.warn('[ai-dock] failed to fetch OAuth state from server');
      return;
    }
    sessionStorage.setItem(OAUTH_STATE_KEY, stateVal);
    const origin = (typeof window !== 'undefined' && window.OAUTH_REDIRECT_ORIGIN) || window.location.origin;
    const redirect = encodeURIComponent(origin + AUTH_CALLBACK);
    const returnTo = encodeURIComponent(location.pathname + location.search);
    const url =
      `https://github.com/login/oauth/authorize?client_id=${encodeURIComponent(clientId)}` +
      `&redirect_uri=${redirect}` +
      `&scope=read:user%20read:org` +
      `&state=${encodeURIComponent(stateVal)}` +
      `&return_to=${returnTo}`;
    location.href = url;
  }

  async function consumeCallback() {
    const sessionId = readSessionIdFromUrl();
    if (!sessionId) return false;
    if (location.hash.includes('session=')) {
      history.replaceState({}, '', location.pathname + location.search);
    } else {
      const u = new URLSearchParams(location.search);
      u.delete('session');
      const q = u.toString();
      history.replaceState({}, '', location.pathname + (q ? '?' + q : ''));
    }
    try {
      const r = await fetch(`/auth/session?session=${encodeURIComponent(sessionId)}`);
      if (!r.ok) return false;
      const profile = await r.json();
      storeSession(sessionId, profile, profile.role);
      return profile;
    } catch (_) { return false; }
  }

  function initBackdrop() {
    const backdrop = $('ai-dock__backdrop');
    if (backdrop) backdrop.addEventListener('click', () => selectTab(null));
  }

  function initEscClose() {
    document.addEventListener('keydown', (e) => {
      if (e.key === 'Escape' && state.activeTab) selectTab(null);
    });
  }

  async function init() {
    await consumeCallback();

    qa('.ai-dock__tab').forEach(tab => {
      tab.addEventListener('click', (e) => {
        // Anchor tabs (dashboard) should still navigate
        if (tab.tagName === 'A' && tab.getAttribute('href')) return;
        e.preventDefault();
        const id = tab.id.replace('ai-dock__tab--', '');
        selectTab(id === state.activeTab ? null : id);
      });
    });

    const ghBtn = $('ai-dock__gh-btn');
    if (ghBtn) ghBtn.addEventListener('click', startOAuth);

    const logoutUser = $('ai-dock__user-logout');
    if (logoutUser) logoutUser.addEventListener('click', () => { clearSession(); setUser(null); closeAll(); });

    initBackdrop();
    initEscClose();
    setUser(readStoredSession());
  }

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', init);
  } else {
    init();
  }

  window.AuthBar = { selectTab };
})();