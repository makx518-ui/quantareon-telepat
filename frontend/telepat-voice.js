/**
 * TELEPAT Voice Client
 * --------------------
 * Clean browser transport extracted from the proven QUANTAREON voice module.
 *
 * Responsibilities only:
 *   microphone -> PCM16/16kHz -> /ws/voice
 *   server events -> CustomEvents
 *   MP3 reply playback
 *   barge-in stops current playback
 *
 * No astrology, prompts, VAD model, search UI, admin controls or greeting logic.
 */
(function (global) {
  'use strict';

  const AudioCtx = global.AudioContext || global.webkitAudioContext;

  function dispatch(name, detail) {
    global.dispatchEvent(new CustomEvent('telepat:' + name, { detail: detail || {} }));
  }

  function getOrCreateUserId() {
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
      return 'tp-session-' + Math.random().toString(36).slice(2, 12);
    }
  }

  function saveIdentity(userId, sessionId) {
    try {
      if (userId) localStorage.setItem('telepat_user_id', userId);
      if (sessionId) sessionStorage.setItem('telepat_session_id', sessionId);
    } catch (_) {}
  }

  function loadSessionId() {
    try {
      return sessionStorage.getItem('telepat_session_id') || '';
    } catch (_) {
      return '';
    }
  }

  function resample(data, fromRate) {
    if (fromRate === 16000) return data;

    // Same linear interpolation used by the proven QUANTAREON site client.
    const ratio = fromRate / 16000;
    const length = Math.round(data.length / ratio);
    const out = new Float32Array(length);

    for (let i = 0; i < length; i++) {
      const idx = i * ratio;
      const floor = Math.floor(idx);
      const ceil = Math.min(floor + 1, data.length - 1);
      const t = idx - floor;
      out[i] = data[floor] * (1 - t) + data[ceil] * t;
    }
    return out;
  }

  function floatToPcm16(data) {
    const out = new Int16Array(data.length);
    for (let i = 0; i < data.length; i++) {
      const s = Math.max(-1, Math.min(1, data[i]));
      out[i] = s < 0 ? s * 0x8000 : s * 0x7fff;
    }
    return out;
  }

  function defaultWsUrl() {
    if (global.TELEPAT_WS_URL) return global.TELEPAT_WS_URL;

    const protocol = global.location.protocol === 'https:' ? 'wss:' : 'ws:';
    return protocol + '//' + global.location.host + '/ws/voice';
  }

  class TelepatVoiceClient {
    constructor(options) {
      options = options || {};

      this.language = options.language || document.documentElement.lang || 'ru';
      this.wsUrl = options.wsUrl || defaultWsUrl();

      this.userId = options.userId || getOrCreateUserId();
      this.sessionId = options.sessionId || loadSessionId();

      this.ws = null;
      this.stream = null;
      this.audioContext = null;
      this.source = null;
      this.processor = null;
      this.silenceGain = null;

      this.playback = null;
      this.playbackUrl = null;
      this.playbackTurnId = null;
      this.pendingAudioTurnId = null;
      this.currentTurnId = 0;
      this.cancelledThroughTurnId = 0;

      this.active = false;
      this.starting = false;
    }

    async start() {
      if (this.active || this.starting) return;
      if (!AudioCtx) throw new Error('Web Audio API is unavailable');

      this.starting = true;
      this.currentTurnId = 0;
      this.cancelledThroughTurnId = 0;
      this.pendingAudioTurnId = null;
      this.playbackTurnId = null;
      dispatch('state', { state: 'connecting' });

      try {
        await this._connectSocket();
        await this._openMicrophone();
        this.active = true;
        dispatch('state', { state: 'listening' });
      } catch (error) {
        await this.stop();
        dispatch('error', { stage: 'start', error: String(error) });
        throw error;
      } finally {
        this.starting = false;
      }
    }

    async stop() {
      this.active = false;
      this.starting = false;
      this.stopPlayback();

      await this._cleanupMedia();

      if (this.ws) {
        const ws = this.ws;
        this.ws = null;
        try { ws.close(1000, 'client stop'); } catch (_) {}
      }

      dispatch('state', { state: 'stopped' });
    }

    async _cleanupMedia() {
      if (this.processor) {
        try { this.processor.disconnect(); } catch (_) {}
        this.processor.onaudioprocess = null;
        this.processor = null;
      }
      if (this.source) {
        try { this.source.disconnect(); } catch (_) {}
        this.source = null;
      }
      if (this.silenceGain) {
        try { this.silenceGain.disconnect(); } catch (_) {}
        this.silenceGain = null;
      }
      if (this.stream) {
        this.stream.getTracks().forEach(function (track) { track.stop(); });
        this.stream = null;
      }
      if (this.audioContext) {
        const ctx = this.audioContext;
        this.audioContext = null;
        try { await ctx.close(); } catch (_) {}
      }
    }

    finalize() {
      this._sendJson({ type: 'finalize' });
    }

    stopPlayback() {
      if (this.playback) {
        try {
          this.playback.pause();
          this.playback.currentTime = 0;
        } catch (_) {}
        this.playback = null;
      }
      this.playbackTurnId = null;
      if (this.playbackUrl) {
        try { URL.revokeObjectURL(this.playbackUrl); } catch (_) {}
        this.playbackUrl = null;
      }
    }

    async _connectSocket() {
      const url = new URL(this.wsUrl, global.location.href);
      url.searchParams.set('user_id', this.userId);
      if (this.sessionId) url.searchParams.set('session_id', this.sessionId);
      url.searchParams.set('language', this.language);

      await new Promise((resolve, reject) => {
        const ws = new WebSocket(url.toString());
        ws.binaryType = 'blob';
        this.ws = ws;

        let settled = false;
        const fail = (error) => {
          if (settled) return;
          settled = true;
          global.clearTimeout(timeout);
          reject(error);
        };

        const timeout = global.setTimeout(() => {
          if (this.ws === ws) this.ws = null;
          try { ws.close(); } catch (_) {}
          fail(new Error('TELEPAT WebSocket timeout'));
        }, 15000);

        ws.onopen = () => {
          if (settled) return;
          settled = true;
          global.clearTimeout(timeout);
          resolve();
        };

        ws.onerror = () => {
          fail(new Error('TELEPAT WebSocket connection failed'));
        };

        ws.onmessage = (event) => this._onMessage(event);
        ws.onclose = (event) => {
          const unexpected = this.ws === ws && (this.active || this.starting);
          if (this.ws === ws) this.ws = null;

          this.active = false;
          this.starting = false;
          this.stopPlayback();

          this._cleanupMedia().finally(() => {
            if (unexpected) {
              dispatch('state', {
                state: 'disconnected',
                code: event.code,
                reason: event.reason || ''
              });
            }
          });

          if (!settled) {
            fail(new Error(
              'TELEPAT WebSocket closed before connection was ready'
            ));
          }
        };
      });
    }

    async _openMicrophone() {
      this.stream = await navigator.mediaDevices.getUserMedia({
        audio: {
          echoCancellation: true,
          noiseSuppression: true,
          // Keep enabled: this was proven necessary on mobile in QUANTAREON.
          autoGainControl: true,
          sampleRate: 16000,
          channelCount: 1
        }
      });

      try {
        this.audioContext = new AudioCtx({ sampleRate: 16000 });
      } catch (_) {
        this.audioContext = new AudioCtx();
      }

      if (this.audioContext.state === 'suspended') {
        await this.audioContext.resume();
      }

      this.source = this.audioContext.createMediaStreamSource(this.stream);

      // ScriptProcessor is intentionally retained for the first integration
      // because the donor implementation is battle-tested. It can later be
      // replaced by AudioWorklet without changing the server protocol.
      this.processor = this.audioContext.createScriptProcessor(4096, 1, 1);

      // Keep the processor alive without routing microphone sound to speakers.
      this.silenceGain = this.audioContext.createGain();
      this.silenceGain.gain.value = 0;

      this.source.connect(this.processor);
      this.processor.connect(this.silenceGain);
      this.silenceGain.connect(this.audioContext.destination);

      this.processor.onaudioprocess = (event) => {
        if (!this.ws || this.ws.readyState !== WebSocket.OPEN) return;
        if (!this.audioContext) return;

        const input = event.inputBuffer.getChannelData(0);
        if (!input || !input.length) return;

        const pcmFloat = this.audioContext.sampleRate === 16000
          ? input
          : resample(input, this.audioContext.sampleRate);

        const pcm16 = floatToPcm16(pcmFloat);
        this.ws.send(pcm16.buffer);
      };
    }

    _onMessage(event) {
      if (typeof event.data !== 'string') {
        const turnId = this.pendingAudioTurnId;
        this.pendingAudioTurnId = null;

        if (turnId && this._isStaleTurn(turnId)) {
          return;
        }

        this._playMp3(event.data, turnId || this.currentTurnId || null);
        return;
      }

      let message;
      try {
        message = JSON.parse(event.data);
      } catch (_) {
        return;
      }

      const type = message.type || '';

      if (type === 'ready') {
        dispatch('ready', message);
        return;
      }

      if (type === 'transcript') {
        if (message.final && message.turn_id) {
          if (this._isStaleTurn(message.turn_id)) return;
          this.currentTurnId = Math.max(
            this.currentTurnId,
            Number(message.turn_id) || 0
          );
        }
        dispatch('transcript', message);
        return;
      }

      if (type === 'state') {
        if (message.turn_id && this._isStaleTurn(message.turn_id)) return;
        dispatch('state', message);
        return;
      }

      if (type === 'barge_in') {
        const interrupted = Number(message.turn_id) || 0;
        if (interrupted) {
          this.cancelledThroughTurnId = Math.max(
            this.cancelledThroughTurnId,
            interrupted
          );
        }
        if (
          this.pendingAudioTurnId &&
          this._isStaleTurn(this.pendingAudioTurnId)
        ) {
          this.pendingAudioTurnId = null;
        }
        this.stopPlayback();
        dispatch('barge-in', message);
        dispatch('state', { state: 'listening' });
        return;
      }

      if (type === 'reply') {
        if (message.turn_id && this._isStaleTurn(message.turn_id)) return;
        if (message.turn_id) {
          this.currentTurnId = Math.max(
            this.currentTurnId,
            Number(message.turn_id) || 0
          );
        }
        if (message.user_id || message.session_id) {
          this.userId = message.user_id || this.userId;
          this.sessionId = message.session_id || this.sessionId;
          saveIdentity(this.userId, this.sessionId);
        }
        dispatch('reply', message);
        dispatch('state', {
          state: message.avatar_state || 'thinking',
          intent: message.intent || ''
        });
        return;
      }

      if (type === 'audio_start') {
        const turnId = Number(message.turn_id) || 0;
        this.pendingAudioTurnId = turnId || null;
        if (turnId && this._isStaleTurn(turnId)) return;
        if (turnId) {
          this.currentTurnId = Math.max(this.currentTurnId, turnId);
        }
        dispatch('audio-start', message);
        dispatch('state', {
          state: 'speaking',
          avatarState: message.avatar_state || 'speaking'
        });
        return;
      }

      if (type === 'audio_end') {
        if (message.turn_id && this._isStaleTurn(message.turn_id)) return;
        dispatch('audio-end', message);
        return;
      }

      if (type === 'session_end') {
        this.active = false;
        this.starting = false;
        this.stopPlayback();
        this._cleanupMedia();
        dispatch('session-end', message);
        dispatch('state', {
          state: 'stopped',
          reason: message.reason || 'session_end'
        });
        return;
      }

      if (type === 'audio_unavailable' || type === 'error') {
        if (message.turn_id && this._isStaleTurn(message.turn_id)) return;
        dispatch(type === 'error' ? 'error' : 'audio-unavailable', message);
        return;
      }

      dispatch('message', message);
    }

    _isStaleTurn(turnId) {
      const id = Number(turnId) || 0;
      if (!id) return false;
      return (
        id <= this.cancelledThroughTurnId ||
        (this.currentTurnId > 0 && id < this.currentTurnId)
      );
    }

    _playMp3(blobLike, turnId) {
      if (turnId && this._isStaleTurn(turnId)) return;

      this.stopPlayback();

      const blob = blobLike instanceof Blob
        ? blobLike
        : new Blob([blobLike], { type: 'audio/mpeg' });

      this.playbackUrl = URL.createObjectURL(blob);
      const audio = new Audio(this.playbackUrl);
      this.playback = audio;
      this.playbackTurnId = turnId || null;

      audio.onended = () => {
        if (this.playback !== audio) return;
        this._sendJson({
          type: 'playback_end',
          turn_id: this.playbackTurnId
        });
        this.stopPlayback();
        dispatch('state', { state: 'listening' });
      };
      audio.onerror = () => {
        if (this.playback !== audio) return;
        this._sendJson({
          type: 'playback_end',
          turn_id: this.playbackTurnId
        });
        this.stopPlayback();
        dispatch('error', { stage: 'playback', error: 'audio playback failed' });
      };

      audio.play().catch((error) => {
        if (this.playback !== audio) return;
        this._sendJson({
          type: 'playback_end',
          turn_id: this.playbackTurnId
        });
        this.stopPlayback();
        dispatch('error', {
          stage: 'playback',
          error: String(error),
          hint: 'Start voice mode from a user gesture to satisfy browser autoplay rules.'
        });
      });
    }

    _sendJson(payload) {
      if (this.ws && this.ws.readyState === WebSocket.OPEN) {
        this.ws.send(JSON.stringify(payload));
      }
    }
  }

  global.TelepatVoice = {
    Client: TelepatVoiceClient,
    create: function (options) {
      return new TelepatVoiceClient(options || {});
    }
  };
})(window);
