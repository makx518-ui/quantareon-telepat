/**
 * TELEPAT Browser Runtime
 * -----------------------
 * Thin integration facade for quantareon-site.
 *
 * Dependencies (load before this file):
 *   telepat-session.js
 *   telepat-voice.js
 *   telepat-avatar.js (optional when no avatar element is configured)
 */
(function (global) {
  'use strict';

  function dispatch(name, detail) {
    global.dispatchEvent(new CustomEvent('telepat:runtime-' + name, {
      detail: detail || {}
    }));
  }

  function normalizeBase(url) {
    return String(url || '').replace(/\/$/, '');
  }

  function deriveWsUrl(apiUrl) {
    const base = normalizeBase(apiUrl);
    if (!base) return '';

    const url = new URL(base, global.location.href);
    url.protocol = url.protocol === 'https:' ? 'wss:' : 'ws:';
    url.pathname = url.pathname.replace(/\/$/, '') + '/ws/voice';
    url.search = '';
    url.hash = '';
    return url.toString();
  }

  class TelepatRuntime {
    constructor(options) {
      options = options || {};

      if (!global.TelepatSession) {
        throw new Error('TelepatSession must be loaded before TelepatRuntime');
      }
      if (!global.TelepatVoice) {
        throw new Error('TelepatVoice must be loaded before TelepatRuntime');
      }

      this.apiUrl = normalizeBase(
        options.apiUrl || global.TELEPAT_API_URL || global.location.origin
      );
      this.wsUrl = options.wsUrl
        || global.TELEPAT_WS_URL
        || deriveWsUrl(this.apiUrl);
      this.language = options.language
        || document.documentElement.lang
        || 'ru';
      this.birth = options.birth || null;

      this.session = null;
      this.voice = null;
      this.avatar = null;
      this.destroyed = false;

      if (options.avatar) {
        if (!global.TelepatAvatar) {
          throw new Error(
            'TelepatAvatar must be loaded when avatar options are supplied'
          );
        }
        this.avatar = global.TelepatAvatar.create(options.avatar);
      }

      this._onReply = (event) => {
        const detail = (event && event.detail) || {};
        if (!this.session) return;
        if (detail.user_id) this.session.user_id = detail.user_id;
        if (detail.session_id) this.session.session_id = detail.session_id;
      };

      global.addEventListener('telepat:reply', this._onReply);
    }

    setBirth(birth) {
      this.birth = birth || null;
    }

    async readiness() {
      const response = await fetch(this.apiUrl + '/health/readiness', {
        headers: { 'Accept': 'application/json' }
      });
      if (!response.ok) {
        throw new Error(
          'TELEPAT readiness failed: ' + response.status
        );
      }
      return response.json();
    }

    async bootstrap(options) {
      options = options || {};
      if (this.destroyed) {
        throw new Error('TELEPAT runtime has been destroyed');
      }

      if (Object.prototype.hasOwnProperty.call(options, 'birth')) {
        this.birth = options.birth || null;
      }

      const previous = this.session || {};
      const session = await global.TelepatSession.bootstrap({
        apiUrl: this.apiUrl,
        userId: options.userId || previous.user_id || undefined,
        sessionId: options.sessionId || previous.session_id || undefined,
        language: options.language || this.language,
        birth: this.birth || undefined
      });

      this.session = session;

      if (this.voice) {
        this.voice.userId = session.user_id;
        this.voice.sessionId = session.session_id;
        this.voice.language = session.language || this.language;
      }

      dispatch('ready', {
        session: session,
        astroReady: !!session.astro_ready,
        memoryReady: !!session.memory_ready
      });
      return session;
    }

    async prepareAstro(birth) {
      if (birth) this.birth = birth;
      if (!this.birth) {
        throw new Error('Birth data is required for Astrofractal preparation');
      }

      if (!this.session) {
        await this.bootstrap({ birth: this.birth });
      }

      const result = await global.TelepatSession.prepareAstro(
        this.birth,
        {
          apiUrl: this.apiUrl,
          language: this.language,
          session: this.session
        }
      );

      if (result.user_id) this.session.user_id = result.user_id;
      if (result.session_id) this.session.session_id = result.session_id;
      return result;
    }

    _ensureVoice() {
      if (this.voice) return this.voice;

      const session = this.session || {};
      this.voice = global.TelepatVoice.create({
        language: session.language || this.language,
        wsUrl: this.wsUrl,
        userId: session.user_id || undefined,
        sessionId: session.session_id || undefined
      });
      return this.voice;
    }

    async startVoice() {
      if (this.destroyed) {
        throw new Error('TELEPAT runtime has been destroyed');
      }
      if (!this.session) {
        await this.bootstrap();
      }

      const voice = this._ensureVoice();
      voice.userId = this.session.user_id;
      voice.sessionId = this.session.session_id;
      voice.language = this.session.language || this.language;

      await voice.start();
      return voice;
    }

    async stopVoice() {
      if (this.voice) {
        await this.voice.stop();
      }
    }

    async reconnectVoice() {
      await this.stopVoice();
      return this.startVoice();
    }

    async destroy() {
      if (this.destroyed) return;
      this.destroyed = true;

      global.removeEventListener('telepat:reply', this._onReply);

      if (this.voice) {
        await this.voice.stop();
        this.voice = null;
      }
      if (this.avatar) {
        this.avatar.destroy();
        this.avatar = null;
      }

      dispatch('destroyed', {});
    }
  }

  global.TelepatRuntime = {
    Client: TelepatRuntime,
    create: function (options) {
      return new TelepatRuntime(options || {});
    }
  };
})(window);
