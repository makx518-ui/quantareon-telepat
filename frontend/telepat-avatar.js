/**
 * TELEPAT Avatar Controller
 * -------------------------
 * Presentation-only controller for the fixed TELEPAT character.
 *
 * It knows nothing about astrology, LLMs or TTS. It reacts to TELEPAT browser
 * state events and plays a small library of compatible avatar clips.
 *
 * Later the GPU transport can call setLiveMedia() without changing the rest
 * of the page.
 */
(function (global) {
  'use strict';

  function dispatch(name, detail) {
    global.dispatchEvent(new CustomEvent('telepat:avatar-' + name, {
      detail: detail || {}
    }));
  }

  class TelepatAvatarController {
    constructor(options) {
      options = options || {};

      this.video = typeof options.video === 'string'
        ? document.querySelector(options.video)
        : options.video;

      if (!this.video) {
        throw new Error('TELEPAT avatar video element was not found');
      }

      this.clips = Object.assign({
        idle: '',
        listening: '',
        thinking: '',
        nod: '',
        hand_chin: '',
        light_gesture: '',
        lean_forward: '',
        soft_smile: ''
      }, options.clips || {});

      this.fallbackState = options.fallbackState || 'idle';
      this.currentState = '';
      this.liveMode = false;
      this.liveUrl = null;

      this.video.playsInline = true;
      this.video.preload = 'auto';

      this._onState = (event) => {
        const state = (event.detail && event.detail.state) || this.fallbackState;
        this.setState(state);
      };

      global.addEventListener('telepat:state', this._onState);
    }

    destroy() {
      global.removeEventListener('telepat:state', this._onState);
      this._releaseLiveUrl();
    }

    async setState(state) {
      if (this.liveMode && state === 'speaking') {
        return;
      }

      const normalized = this.clips[state] ? state : this.fallbackState;
      const src = this.clips[normalized];
      if (!src) return;
      if (this.currentState === normalized && this.video.src) return;

      this.liveMode = false;
      this._releaseLiveUrl();
      this.currentState = normalized;

      this.video.loop = normalized === 'idle' || normalized === 'listening';
      this.video.muted = true;

      const absolute = new URL(src, global.location.href).href;
      if (this.video.src !== absolute) {
        this.video.src = absolute;
        this.video.load();
      }

      try {
        await this.video.play();
        dispatch('state', { state: normalized });
      } catch (error) {
        dispatch('error', {
          state: normalized,
          error: String(error)
        });
      }
    }

    async setLiveMedia(media, options) {
      options = options || {};
      this._releaseLiveUrl();

      let src;
      if (media instanceof Blob) {
        this.liveUrl = URL.createObjectURL(media);
        src = this.liveUrl;
      } else if (media instanceof ArrayBuffer) {
        this.liveUrl = URL.createObjectURL(
          new Blob([media], { type: options.type || 'video/mp4' })
        );
        src = this.liveUrl;
      } else {
        src = String(media || '');
      }

      if (!src) return;

      this.liveMode = true;
      this.currentState = 'speaking';
      this.video.loop = false;
      this.video.muted = options.muted !== undefined ? options.muted : false;
      this.video.src = src;
      this.video.load();

      this.video.onended = () => {
        this.liveMode = false;
        this.setState('listening');
      };

      try {
        await this.video.play();
        dispatch('live-start', {});
      } catch (error) {
        dispatch('error', {
          state: 'speaking',
          error: String(error)
        });
      }
    }

    _releaseLiveUrl() {
      if (this.liveUrl) {
        try { URL.revokeObjectURL(this.liveUrl); } catch (_) {}
        this.liveUrl = null;
      }
    }
  }

  global.TelepatAvatar = {
    Controller: TelepatAvatarController,
    create: function (options) {
      return new TelepatAvatarController(options || {});
    }
  };
})(window);
