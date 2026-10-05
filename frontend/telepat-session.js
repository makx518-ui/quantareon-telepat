/**
 * TELEPAT Session Bootstrap
 * -------------------------
 * Runs while the greeting video is playing:
 *   1. restore/generate TELEPAT user identity
 *   2. create/resume backend session
 *   3. optionally prepare Astrofractal context
 */
(function (global) {
  'use strict';

  function apiBase(override) {
    if (override) {
      return String(override).replace(/\/$/, '');
    }
    if (global.TELEPAT_API_URL) {
      return String(global.TELEPAT_API_URL).replace(/\/$/, '');
    }
    return global.location.origin;
  }

  function localUserId() {
    try {
      let id = localStorage.getItem('telepat_user_id');
      if (!id) {
        id = global.crypto && crypto.randomUUID
          ? crypto.randomUUID()
          : 'tp-' + Date.now().toString(36) + '-' + Math.random().toString(36).slice(2, 12);
        localStorage.setItem('telepat_user_id', id);
      }
      return id;
    } catch (_) {
      return '';
    }
  }

  function currentSessionId() {
    try {
      return sessionStorage.getItem('telepat_session_id') || '';
    } catch (_) {
      return '';
    }
  }

  function saveIdentity(data) {
    try {
      if (data.user_id) localStorage.setItem('telepat_user_id', data.user_id);
      if (data.session_id) sessionStorage.setItem('telepat_session_id', data.session_id);
    } catch (_) {}
  }

  async function post(path, payload, apiUrl) {
    const response = await fetch(apiBase(apiUrl) + path, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(payload)
    });

    if (!response.ok) {
      const text = await response.text();
      throw new Error('TELEPAT ' + path + ' failed: ' + response.status + ' ' + text);
    }
    return response.json();
  }

  async function bootstrap(options) {
    options = options || {};
    const payload = {
      user_id: options.userId || localUserId() || null,
      session_id: options.sessionId || currentSessionId() || null,
      language: options.language || document.documentElement.lang || 'ru'
    };

    if (options.birth) {
      payload.birth = options.birth;
    }

    const data = await post('/session/bootstrap', payload, options.apiUrl);

    saveIdentity(data);
    global.dispatchEvent(new CustomEvent('telepat:session-ready', { detail: data }));
    return data;
  }

  async function prepareAstro(birth, options) {
    options = options || {};
    const session = options.session || await bootstrap(
      Object.assign({}, options, { birth: birth })
    );

    const data = await post('/session/astro', {
      birth: birth,
      user_id: session.user_id,
      session_id: session.session_id,
      language: options.language || session.language || 'ru'
    }, options.apiUrl);

    saveIdentity(data);
    global.dispatchEvent(new CustomEvent('telepat:astro-ready', { detail: data }));
    return data;
  }

  global.TelepatSession = {
    bootstrap: bootstrap,
    prepareAstro: prepareAstro,
    userId: localUserId,
    sessionId: currentSessionId
  };
})(window);
