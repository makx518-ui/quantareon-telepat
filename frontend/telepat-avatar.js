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
      this.currentTurnId = 0;
      this.cancelledThroughTurnId = 0;
      this.liveTurnId = null;

      this.video.playsInline = true;
      this.video.preload = 'auto';

      this._onState = (event) => {
        const detail = (event && event.detail) || {};
        const turnId = Number(detail.turnId || detail.turn_id) || 0;
        if (turnId && this._isStaleTurn(turnId)) return;
        if (turnId) {
          this.currentTurnId = Math.max(this.currentTurnId, turnId);
        }

        const transportState = detail.state || this.fallbackState;

        // During speech keep the semantic pose selected by the orchestrator
        // until real GPU media arrives. Do not fall back to idle just because
        // the transport state is named "speaking".
        if (transportState === 'speaking') {
          const semantic = detail.avatarState || this.currentState || 'thinking';
          if (this.clips[semantic]) {
            this.setState(semantic);
          }
          return;
        }

        this.setState(transportState);
      };

      this._onBargeIn = (event) => {
        const detail = (event && event.detail) || {};
        const turnId = Number(detail.turn_id || detail.turnId) || 0;
        if (turnId) {
          this.cancelledThroughTurnId = Math.max(
            this.cancelledThroughTurnId,
            turnId
          );
        }

        if (
          this.liveMode &&
          this.liveTurnId &&
          this._isStaleTurn(this.liveTurnId)
        ) {
          try {
            this.video.pause();
            this.video.currentTime = 0;
          } catch (_) {}
          this.liveMode = false;
          this.liveTurnId = null;
          this._releaseLiveUrl();
          this.setState('listening');
        }
      };

      global.addEventListener('telepat:state', this._onState);
      global.addEventListener('telepat:barge-in', this._onBargeIn);
    }

    destroy() {
      global.removeEventListener('telepat:state', this._onState);
      global.removeEventListener('telepat:barge-in', this._onBargeIn);
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

    _isStaleTurn(turnId) {
      const id = Number(turnId) || 0;
      if (!id) return false;
      return (
        id <= this.cancelledThroughTurnId ||
        (this.currentTurnId > 0 && id < this.currentTurnId)
      );
    }

    async setLiveMedia(media, options) {
      options = options || {};
      const turnId = Number(
        options.turnId || options.turn_id
      ) || 0;

      if (turnId && this._isStaleTurn(turnId)) {
        return false;
      }
      if (turnId) {
        this.currentTurnId = Math.max(this.currentTurnId, turnId);
      }

      this.video.onended = null;
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
      this.liveTurnId = turnId || null;
      this.currentState = 'speaking';
      this.video.loop = false;
      this.video.muted = options.muted !== undefined ? options.muted : false;
      this.video.src = src;
      this.video.load();

      const expectedTurnId = this.liveTurnId;
      this.video.onended = () => {
        if (this.liveTurnId !== expectedTurnId) return;
        this.liveMode = false;
        this.liveTurnId = null;
        this.setState('listening');
      };

      try {
        await this.video.play();
        dispatch('live-start', {
          turnId: this.liveTurnId
        });
        return true;
      } catch (error) {
        dispatch('error', {
          state: 'speaking',
          turnId: this.liveTurnId,
          error: String(error)
        });
        return false;
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
